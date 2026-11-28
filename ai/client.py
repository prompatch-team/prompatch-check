"""AI API를 부르는 곳은 이 파일 하나예요 (조건 뽑기와 정성 판단이 같이 써요).

- 시간 제한: 기본 20초, .env의 PROMPATCH_AI_TIMEOUT(초)으로 바꿔요.
- 재시도: 1회. 시간 초과, 연결 오류, 429, 5xx는 SDK가 한 번 더 불러요.
- 프롬프트 캐싱: system 지침에 cache_control을 붙여요. 응답의 cache_read_input_tokens를 usage에 담아요.
- 실패하면 이유 코드(AI_*)를 단 AIError를 내요. 메시지에 가이드·원고 글을 넣지 않아요.
"""
from __future__ import annotations

import collections
import json
import os

TIMEOUT_ENV = "PROMPATCH_AI_TIMEOUT"
DEFAULT_TIMEOUT = 60.0          # 2026-11-27 실제 시험: 20초면 실제 가이드 조건 뽑기의 절반쯤이 끊겼어요
RETRIES = 1

# 이유 코드. 기록에는 이 코드만 남겨요.
AI_TIMEOUT = "AI_TIMEOUT"          # 시간 초과
AI_4XX = "AI_4XX"                  # 요청 쪽 문제(키, 모델 이름, 형식, 한도)
AI_5XX = "AI_5XX"                  # AI 서버 쪽 문제
AI_CONNECTION = "AI_CONNECTION"    # 연결 못 함
AI_TRUNCATED = "AI_TRUNCATED"      # 응답이 max_tokens에서 잘림
AI_NOT_JSON = "AI_NOT_JSON"        # 응답이 JSON이 아님
AI_REFUSAL = "AI_REFUSAL"          # AI가 거절함


class AIError(Exception):
    """AI를 부르지 못했거나 응답을 쓸 수 없을 때. code는 위의 이유 코드예요."""

    def __init__(self, code: str, message: str, status: int | None = None):
        super().__init__(message)
        self.code, self.status = code, status


# 1M 토큰당 달러: 입력, 출력, 캐시 읽기, 캐시 쓰기(5분, 입력의 1.25배). claude-api 문서 기준 (2026-11-27)
PRICES = {"claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125), "claude-sonnet-5-5": (2.0, 10.0, 0.20, 2.5),
          "claude-opus-5-5": (4.0, 20.0, 0.20, 5.0)}
KRW_ENV = "PROMPATCH_KRW_PER_USD"
DEFAULT_KRW = 1400.0              # 환율은 바뀌어요. 원 단위는 어림값이에요 (docs/metrics.md)


def cost_krw(usage: dict | None, model: str) -> float | None:
    """AI 한 번 부른 비용(원). 토큰 수로 계산해요. 모르는 모델이나 사용량이 없으면 None."""
    price = PRICES.get(model)
    if not price or not usage:
        return None
    try:
        krw = float(os.environ.get(KRW_ENV, "").strip() or DEFAULT_KRW)
    except ValueError:
        krw = DEFAULT_KRW
    n = lambda k: usage.get(k) or 0
    usd = (n("input_tokens") * price[0] + n("output_tokens") * price[1]
           + n("cache_read_input_tokens") * price[2] + n("cache_creation_input_tokens") * price[3]) / 1e6
    return round(usd * krw, 3)


def timeout() -> float:
    try:
        value = float(os.environ.get(TIMEOUT_ENV, "").strip())
        return value if value > 0 else DEFAULT_TIMEOUT
    except ValueError:
        return DEFAULT_TIMEOUT


def cached_system(text: str) -> list[dict]:
    """system 지침을 캐시해요. 지침은 요청마다 같아서, 두 번째부터는 캐시에서 읽어요."""
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def usage_of(response) -> dict | None:
    """토큰 수만 꺼내요 (숫자뿐)."""
    u = getattr(response, "usage", None)
    if not u:
        return None
    return {k: getattr(u, k, None) for k in
            ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")}


def call(request: dict) -> tuple[dict, dict | None]:
    """Messages API를 한 번(실패하면 한 번 더) 불러 JSON 응답과 토큰 수를 돌려줘요."""
    import anthropic   # 테스트는 이 함수를 부르지 않아서, SDK 없이도 돌아가요

    try:
        response = anthropic.Anthropic(timeout=timeout(), max_retries=RETRIES).messages.create(**request)
    except anthropic.APITimeoutError as e:
        raise AIError(AI_TIMEOUT, f"AI 응답이 {timeout():.0f}초 안에 오지 않았어요") from e
    except anthropic.AuthenticationError as e:
        raise AIError(AI_4XX, "API 키가 맞지 않아요. .env의 ANTHROPIC_API_KEY를 확인해 주세요", 401) from e
    except anthropic.NotFoundError as e:
        raise AIError(AI_4XX, f"모델 이름을 찾지 못했어요: {request.get('model')}", 404) from e
    except anthropic.RateLimitError as e:
        raise AIError(AI_4XX, "요청이 많아서 잠시 막혔어요. 조금 뒤에 다시 해 주세요", 429) from e
    except anthropic.APIStatusError as e:
        code = AI_5XX if e.status_code >= 500 else AI_4XX
        # API가 돌려준 오류 설명(형식 문제 등)을 그대로 보여 줘요. 가이드·원고 글은 들어 있지 않아요.
        raise AIError(code, f"AI API가 오류를 돌려줬어요 (상태 {e.status_code}): {getattr(e, 'message', '')}",
                      e.status_code) from e
    except anthropic.APIConnectionError as e:
        raise AIError(AI_CONNECTION, "AI API에 연결하지 못했어요. 네트워크를 확인해 주세요") from e
    return parse(response), usage_of(response)


# ── AI를 부르기 전에 막기 ────────────────────────────────────────────────

TOO_LONG = "TOO_LONG"              # 기준보다 긴 글
MEANINGLESS = "MEANINGLESS"        # 글자가 거의 없거나 같은 글자만 반복
SAME_AS_GUIDE = "SAME_AS_GUIDE"    # 원고 칸에 가이드를 넣은 것 같음
MIN_CHARS = 20                     # 공백을 뺀 글자가 이보다 적으면 의미 없는 글로 봐요 (우리 기준)
MIN_DISTINCT = 5                   # 서로 다른 글자가 이보다 적으면 (우리 기준)
TOP_CHAR_SHARE = 0.5               # 한 글자가 공백 뺀 글의 절반을 넘으면 (우리 기준)


def refuse(text: str, max_chars: int) -> tuple[str, str] | None:
    """AI를 부르지 않을 이유(코드, 화면 문구). 부를 만하면 None. 글은 돌려주지 않아요."""
    if len(text) > max_chars:
        return TOO_LONG, f"글이 너무 길어요. {max_chars:,}자까지 AI로 살펴봐요"
    letters = [ch for ch in text if not ch.isspace()]
    if len(letters) < MIN_CHARS or len(set(letters)) < MIN_DISTINCT:
        return MEANINGLESS, "글자가 거의 없어서 살펴볼 수 없어요"
    top = max(collections.Counter(letters).values())          # 한 번만 훑어요 (긴 글로 서버를 붙잡지 않게)
    if top / len(letters) > TOP_CHAR_SHARE:
        return MEANINGLESS, "같은 글자만 반복돼서 살펴볼 수 없어요"
    return None


def looks_like_guide(draft: str, quotes: list[str]) -> bool:
    """조건의 가이드 인용이 거의 다 원고에 그대로 있으면, 원고 칸에 가이드를 넣은 것으로 봐요 (우리 기준: 3개 이상, 80% 이상)."""
    quotes = [q for q in quotes if len(q.strip()) >= 8]
    return len(quotes) >= 3 and sum(q in draft for q in quotes) >= 0.8 * len(quotes)


def parse(response) -> dict:
    """응답에서 JSON을 꺼내요. 잘렸거나 거절했거나 JSON이 아니면 AIError."""
    if response.stop_reason == "refusal":
        raise AIError(AI_REFUSAL, "AI가 이 요청을 거절했어요")
    if response.stop_reason == "max_tokens":
        raise AIError(AI_TRUNCATED, "AI 응답이 길어서 잘렸어요")
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise AIError(AI_NOT_JSON, "AI 응답이 JSON이 아니에요") from e
    if not isinstance(data, dict):
        raise AIError(AI_NOT_JSON, "AI 응답이 JSON 객체가 아니에요")
    return data
