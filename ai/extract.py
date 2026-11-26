"""가이드 원문 → 조건 목록 (contracts conditions 0.2).

LLM은 조건을 뽑기만 해요. 아래는 전부 코드가 해요.
- 인용 문구(quote)가 가이드 원문에 실제로 있는지 확인하고, 없으면 그 조건을 버려요.
- 위치(start, end)는 코드가 원문에서 다시 찾아 계산해요 (코드 포인트).
- 키워드·금지어·필수 문구 같은 글자가 원문에 있는지 확인하고, 없으면 그 조건을 버려요.
- 기준 숫자가 인용 문구에 안 보이면 조건은 남기고 needs_review 표시를 달아요.
- 셀 수 있는 조건인지(countable), 가이드 형식(platform)도 코드가 정해요.

이 파일은 가이드 글을 화면이나 로그에 찍지 않아요. 파일에 남기는 것은 cache_dir를 줬을 때뿐이에요
(개발용 ai/cache/, 저장소에 올라가지 않음). 서버에서는 cache_dir 없이 불러요.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from .prompt import OUTPUT_SCHEMA, SYSTEM_PROMPT, TYPES

VERSION = "0.2"
ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = Path(__file__).resolve().parent / "cache"
PRIVATE_CACHE_DIR = CACHE_DIR / "private"     # 실제 가이드(private 샘플)의 AI 결과는 여기에 따로 둬요
DEFAULT_MODEL = "claude-haiku-5-5"      # 개발 중 기본. .env의 PROMPATCH_MODEL로 바꿔요
MODEL_ENV = "PROMPATCH_MODEL"
PROMPT_VERSION = hashlib.sha256(
    (SYSTEM_PROMPT + json.dumps(OUTPUT_SCHEMA, ensure_ascii=False, sort_keys=True)).encode("utf-8")
).hexdigest()[:12]

REVIEWPLACE_HEADS = ("제목키워드", "본문키워드", "캠페인 안내", "리뷰어 미션")
NOT_COUNTABLE = ("outside_draft", "judgment")


last_usage: dict | None = None      # 마지막 AI 호출의 토큰 수 (숫자만)


class ExtractError(Exception):
    """API를 부르지 못했거나 응답을 쓸 수 없을 때. 메시지에 가이드 글을 넣지 않아요."""


# 조건을 버린 이유 코드. 기록(서버 로그, 측정 결과)에는 이 코드와 조건 종류, 개수만 남겨요. 가이드 글은 남기지 않아요.
QUOTE_NOT_FOUND = "QUOTE_NOT_FOUND"            # 인용 문구가 가이드 원문에 없음
VALUE_NOT_IN_GUIDE = "VALUE_NOT_IN_GUIDE"      # 키워드·금지어·문구·태그·주소가 가이드 원문에 없음
SCHEMA_INVALID = "SCHEMA_INVALID"              # 조건 모양이 아니거나, 모르는 종류거나, 꼭 있어야 하는 값이 비었음
LIMIT_EXCEEDED = "LIMIT_EXCEEDED"              # 개수·길이·숫자가 상한을 넘음
MISSION_KEYWORD_LINE = "MISSION_KEYWORD_LINE"  # 리뷰어 미션의 "키워드" 줄 (위의 키워드 조건과 같은 조건)
DUP_EXACT_PHRASE = "DUP_EXACT_PHRASE"          # 표기 조건과 같은 문장에서 나온, 조건이 붙은 필수 문구
DUPLICATE = "DUPLICATE"                        # 똑같은 조건이 두 번 나옴
DROP_CODES = (QUOTE_NOT_FOUND, VALUE_NOT_IN_GUIDE, SCHEMA_INVALID, LIMIT_EXCEEDED, MISSION_KEYWORD_LINE,
              DUP_EXACT_PHRASE, DUPLICATE)


class Drop(Exception):
    """이 조건은 버려요. 이유 코드와, 사람이 읽을 이유를 담아요."""

    def __init__(self, code: str, reason: str):
        super().__init__(reason)
        self.code = code


# ── 설정 ─────────────────────────────────────────────────────────────────

def load_env(path: Path = ROOT / ".env") -> None:
    """.env의 KEY=VALUE를 환경 변수로 읽어요. 이미 있는 값은 건드리지 않고, 아무것도 출력하지 않아요."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def model_name() -> str:
    return os.environ.get(MODEL_ENV, "").strip() or DEFAULT_MODEL


# ── LLM 부르기 ───────────────────────────────────────────────────────────

def as_data(guide: str) -> str:
    """가이드 속의 <guide>, </guide>가 우리 태그를 닫고 나오지 못하게 한 칸 띄워요 (프롬프트 주입 막기).

    AI에게 보내는 사본에만 해요. 인용 확인과 위치 계산은 원래 가이드로 해요.
    """
    return re.sub(r"<(/?)\s*(guide)", r"<\1 \2", guide, flags=re.IGNORECASE)


def build_request(guide: str) -> dict:
    """Messages API에 보낼 값. 가이드는 <guide> 태그 안에 자료로만 넣어요."""
    return {
        "model": model_name(),
        "max_tokens": 16000,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": f"<guide>\n{as_data(guide)}\n</guide>"}],
        "output_config": {"effort": "medium", "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
    }


def call_llm(guide: str) -> dict:
    """AI API를 한 번 불러 LLM이 뽑은 조건(가공 전)을 받아요. 서버가 밖으로 보내는 요청은 이것뿐이에요."""
    import anthropic   # 테스트는 이 함수를 부르지 않아서, SDK 없이도 돌아가요

    try:
        response = anthropic.Anthropic().messages.create(**build_request(guide))
    except anthropic.AuthenticationError as e:
        raise ExtractError("API 키가 맞지 않아요. .env의 ANTHROPIC_API_KEY를 확인해 주세요") from e
    except anthropic.NotFoundError as e:
        raise ExtractError(f"모델 이름을 찾지 못했어요: {model_name()} (.env의 {MODEL_ENV})") from e
    except anthropic.RateLimitError as e:
        raise ExtractError("요청이 많아서 잠시 막혔어요. 조금 뒤에 다시 해 주세요") from e
    except anthropic.APIStatusError as e:
        # API가 돌려준 오류 설명(형식 문제 등)을 그대로 보여 줘요. 가이드 글은 들어 있지 않아요.
        raise ExtractError(f"AI API가 오류를 돌려줬어요 (상태 {e.status_code}): {getattr(e, 'message', '')}") from e
    except anthropic.APIConnectionError as e:
        raise ExtractError("AI API에 연결하지 못했어요. 네트워크를 확인해 주세요") from e

    if response.stop_reason == "refusal":
        raise ExtractError("AI가 이 가이드 분석을 거절했어요")
    if response.stop_reason == "max_tokens":
        raise ExtractError("AI 응답이 길어서 잘렸어요")
    global last_usage
    usage = getattr(response, "usage", None)
    # ponytail: 마지막 호출의 토큰 수만 기억해요 (숫자뿐). 동시에 여러 요청이 오면 섞일 수 있어요. 비용을 정확히 재려면 호출마다 돌려주게 바꿔요.
    last_usage = {"input_tokens": getattr(usage, "input_tokens", None),
                  "output_tokens": getattr(usage, "output_tokens", None)} if usage else None
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ExtractError("AI 응답이 JSON이 아니에요") from e


# ── 코드로 확인하고 형식 맞추기 ──────────────────────────────────────────

# 따옴표는 종류가 달라도 같은 글자로 봐요 (“ ” ‘ ’ ' " 등)
QUOTE_MARKS = str.maketrans({c: '"' for c in "“”„‟＂«»‘’‚‛＇'`´"})


def _flat(text: str) -> tuple[str, list[int]]:
    """띄어쓰기·줄바꿈을 빼고 따옴표 종류를 하나로 맞춘 글자와, 그 글자들의 원래 위치."""
    keep = [(i, ch) for i, ch in enumerate(text) if not ch.isspace()]
    return "".join(ch for _, ch in keep).translate(QUOTE_MARKS), [i for i, _ in keep]


def find_quote(guide: str, quote: str) -> tuple[int, int] | None:
    """인용 문구의 원문 위치.

    띄어쓰기·줄바꿈, 따옴표 종류, 줄 맨 앞의 번호나 "# "만 다르면 같은 인용으로 보고 원문 쪽 글자를 찾아 줘요.
    돌려주는 위치는 언제나 원문의 글자예요 (guide[start:end]가 가이드에 그대로 있어요).
    """
    quote = quote.strip()
    if not quote:
        return None
    start = guide.find(quote)
    if start != -1:
        end = start + len(quote)
    else:
        flat, where = _flat(guide)
        for candidate in (quote, re.sub(r"^(\d+[.)]|#)\s*", "", quote)):
            needle = _flat(candidate)[0]
            at = flat.find(needle) if needle else -1
            if at != -1:
                start, end = where[at], where[at + len(needle) - 1] + 1
                break
        else:
            return None
    # 리뷰플레이스 안내 줄("# 키워드 중 1개를 ...")은 줄 맨 앞의 "# "까지 인용에 넣어요
    if guide[max(start - 2, 0):start] == "# " and (start == 2 or guide[start - 3] == "\n"):
        start -= 2
    # 줄 맨 앞의 번호("4. ", "2) ")는 인용에서 빼요
    number = re.match(r"\d+[.)]\s+", guide[start:end])
    if number and (start == 0 or guide[start - 1] == "\n") and number.end() < end - start:
        start += number.end()
    return start, end


# AI가 낸 값의 상한. AI 응답은 믿을 수 없는 입력이에요 (가이드 속 문장이 AI를 조종했을 수 있어요).
MAX_CONDITIONS = 60       # 조건 개수
MAX_LIST = 30             # 키워드·태그·금지어 개수
MAX_VALUE = 100           # 키워드·문구·표기 하나의 글자 수
MAX_QUOTE = 400           # 인용 문구 글자 수
MAX_LABEL = 80            # 라벨 글자 수
MAX_NOTE = 120            # 풀어 쓴 설명(물음, 사진 내용 등) 글자 수
MAX_MIN = 1_000_000       # 기준 숫자
MAX_DROPPED = 100


def _text(rc: dict, key: str) -> str:
    v = rc.get(key)
    return v.strip() if isinstance(v, str) else ""


def _short(rc: dict, key: str, limit: int = MAX_NOTE) -> str:
    """AI가 풀어 쓴 글: 한 줄로 만들고 길이를 잘라요."""
    return " ".join(_text(rc, key).split())[:limit]


def _list(rc: dict, key: str) -> list[str]:
    v = rc.get(key)
    out = [x.strip() for x in v if isinstance(x, str) and x.strip()] if isinstance(v, list) else []
    if len(out) > MAX_LIST or any(len(x) > MAX_VALUE for x in out):
        raise Drop(LIMIT_EXCEEDED, "값이 너무 많거나 길어요")
    return out


def _min(rc: dict, default: int | None = 1) -> int:
    v = rc.get("min")
    if isinstance(v, int) and not isinstance(v, bool) and v > MAX_MIN:
        raise Drop(LIMIT_EXCEEDED, "기준 숫자가 너무 커요")
    if isinstance(v, int) and not isinstance(v, bool) and v > 0:
        return v
    if default is None:
        raise Drop(SCHEMA_INVALID, "기준 숫자가 없어요")
    return default


def _choice(rc: dict, key: str, allowed: tuple, default):
    return rc.get(key) if rc.get(key) in allowed else default


def _need(values, what: str):
    if not values:
        raise Drop(SCHEMA_INVALID, f"{what}가 비어 있어요")
    return values


SCOPES = ("title", "body", "title_and_body")

PARAMS = {
    "title_keyword": lambda rc: {
        "keywords": _need(_list(rc, "keywords"), "키워드"),
        "pick": _choice(rc, "pick", ("any", "each"), "any"),
    },
    "keyword_count": lambda rc: {
        "keywords": _need(_list(rc, "keywords"), "키워드"),
        "min": _min(rc),
        "pick": _choice(rc, "pick", ("any", "each"), "any"),
        "scope": _choice(rc, "scope", SCOPES, "body"),
    },
    "length": lambda rc: {
        "min": _min(rc, default=None),
        "count_spaces": {"yes": True, "no": False}.get(rc.get("count_spaces")),
    },
    "photo_count": lambda rc: {"min": _min(rc), **({"subject": _short(rc, "subject")} if _short(rc, "subject") else {})},
    "video_count": lambda rc: {"min": _min(rc)},
    "link": lambda rc: {"min": _min(rc), "url": _text(rc, "url") or None},
    "map": lambda rc: {"position": _choice(rc, "position", ("bottom",), None)},
    "hashtag": lambda rc: {
        # 해시태그에는 띄어쓰기가 없어요: 키워드 "솔바람 찻집" → "#솔바람찻집"
        "tags": ["#" + re.sub(r"\s+", "", t.lstrip("#")) for t in _need(_list(rc, "tags"), "태그")],
        "pick": _choice(rc, "pick", ("any", "each"), "each"),
    },
    "exact_phrase": lambda rc: {
        "allowed": _text(rc, "allowed") or None,
        "forbidden": _list(rc, "forbidden"),
        "scope": _choice(rc, "scope", SCOPES, "title_and_body"),
    },
    "banned_terms": lambda rc: {
        "terms": _list(rc, "terms"),
        "category": _short(rc, "category") or None,
        "scope": _choice(rc, "scope", SCOPES, "title_and_body"),
    },
    "required_phrase": lambda rc: {
        "phrase": _need(_text(rc, "phrase"), "필수 문구"),
        "scope": _choice(rc, "scope", SCOPES, "body"),
        **({"after": _short(rc, "after")} if _short(rc, "after") else {}),
    },
    "disclosure": lambda rc: {
        "phrase": _text(rc, "phrase") or None,
        "position": _choice(rc, "position", ("top",), None),
    },
    "outside_draft": lambda rc: {"what": _short(rc, "what") or _short(rc, "label") or "원고 밖 조건"},
    "judgment": lambda rc: {"question": _need(_short(rc, "question") or _short(rc, "label"), "물음")},
}
assert set(PARAMS) == set(TYPES)


def _literals(params: dict) -> list[str]:
    """가이드에 글자 그대로 있어야 하는 값들."""
    out = list(params.get("keywords") or []) + list(params.get("terms") or []) + list(params.get("forbidden") or [])
    out += [params[k] for k in ("phrase", "allowed", "url") if params.get(k)]
    return out


def make_condition(guide: str, rc: dict) -> dict:
    kind = rc.get("type")
    if kind not in PARAMS:
        raise Drop(SCHEMA_INVALID, "모르는 조건 종류예요")
    found = find_quote(guide, _text(rc, "quote"))
    if found is None:
        raise Drop(QUOTE_NOT_FOUND, "인용 문구가 가이드 원문에 없어요")
    start, end = found
    quote = guide[start:end]
    if quote.strip() == "키워드":
        raise Drop(MISSION_KEYWORD_LINE, '리뷰어 미션의 "키워드" 줄은 위의 키워드 조건과 같은 조건이에요')
    if kind == "required_phrase" and re.fullmatch(r"#[^\s#]+(\s+#[^\s#]+)*", _text(rc, "phrase")):
        # "#태그"만 든 필수 문구("#가 #나")는 해시태그 조건이에요
        kind, rc = "hashtag", {**rc, "tags": _text(rc, "phrase").split(), "pick": "each"}
    params = PARAMS[kind](rc)
    for key, default in (("keywords", "any"), ("tags", "each")):
        if len(params.get(key) or []) == 1 and "pick" in params:
            params["pick"] = default          # 하나뿐이면 any와 each가 같은 뜻이라 기본값으로 맞춰요

    if kind == "exact_phrase" and not (params["allowed"] or params["forbidden"]):
        raise Drop(SCHEMA_INVALID, "표기가 비어 있어요")
    if kind == "banned_terms" and not (params["terms"] or params["category"]):
        raise Drop(SCHEMA_INVALID, "금지어가 비어 있어요")
    if end - start > MAX_QUOTE:
        raise Drop(LIMIT_EXCEEDED, "인용 문구가 너무 길어요")
    for value in _literals(params):
        if len(value) > MAX_VALUE * 2:
            raise Drop(LIMIT_EXCEEDED, "값이 너무 길어요")
        if value not in guide:
            raise Drop(VALUE_NOT_IN_GUIDE, f'"{value[:MAX_VALUE]}"가 가이드 원문에 없어요')
    squeezed = re.sub(r"\s+", "", guide)
    for tag in params.get("tags") or []:           # 태그는 띄어쓰기를 빼고 맞춰 봐요 ("솔바람 찻집" ↔ "#솔바람찻집")
        if tag.lstrip("#") not in squeezed:
            raise Drop(VALUE_NOT_IN_GUIDE, f'"{tag}"가 가이드 원문에 없어요')
    # 기준 숫자가 인용 문구에 아라비아 숫자로 안 보이면("다섯 번" 등) 버리지 않고 확인 표시를 달아요.
    # 조건표 화면에서 블로거가 숫자를 확인·수정해요.
    digits = re.sub(r"(?<=\d),(?=\d)", "", quote)
    if params.get("min", 1) > 1 and not re.search(rf"(?<!\d){params['min']}(?!\d)", digits):
        params["needs_review"] = True

    countable = kind not in NOT_COUNTABLE
    if kind == "photo_count" and params.get("subject"):
        countable = False            # 사진 내용은 셀 수 없어요
    if kind == "banned_terms" and not params["terms"]:
        countable = False            # 단어 없이 종류만 있으면 셀 수 없어요
    return {
        "id": "",
        "type": kind,
        "label": _short(rc, "label", MAX_LABEL) or kind,
        "countable": countable,
        "params": params,
        "guide_quote": {"text": quote, "start": start, "end": end},
    }


def detect_platform(guide: str) -> str | None:
    lines = {line.strip() for line in guide.splitlines()}
    return "reviewplace" if sum(h in lines for h in REVIEWPLACE_HEADS) >= 2 else None


# "기자단"은 원칙 점검 p6을 켜기 때문에, 근거 낱말이 가이드에 있을 때만 받아요. 근거가 없으면 "체험"으로 둬요.
# "체험"은 LLM이 고른 대로 받아요. LLM이 모른다고 한 경우만 null이에요.
PRESS_WORDS = ("기자단", "체험한 것처럼")


def check_campaign_type(guide: str, claimed) -> str | None:
    if claimed == "기자단":
        return "기자단" if any(w in guide for w in PRESS_WORDS) else "체험"
    return "체험" if claimed == "체험" else None


# "쓴다면 이렇게"라는 뜻의 조건이 붙은 문장인지: "언급할 경우", "언급 시", "쓸 때", "작성하실 때" ...
CONDITIONAL = re.compile(r"(할|하실|하는|쓸|쓰실|적을|넣을)\s*경우|(언급|표기|작성|사용|기재)\s*시(?=에|엔|는|,|\s|$)|(쓸|쓰실|적을|적으실|넣을|[가-힣]+할|[가-힣]+하실)\s*때")


def tidy_overlaps(kept: list[dict], dropped: list[dict]) -> None:
    """같은 것을 두 번 말하는 조건을 정리해요."""
    def overlap(a: dict, b: dict) -> bool:
        return a["guide_quote"]["start"] < b["guide_quote"]["end"] and b["guide_quote"]["start"] < a["guide_quote"]["end"]

    # 필수 문구(required_phrase)를 버리는 건 두 가지가 다 맞을 때뿐이에요.
    # (a) 표기 조건(exact_phrase)과 같은 가이드 문장에서 나왔고
    # (b) 그 문장이 "언급할 경우", "언급 시", "쓸 때"처럼 조건이 붙은 문장일 때.
    # "언급할 경우 반드시 ~로"는 쓸 때의 표기 조건이지, 꼭 넣으라는 조건이 아니에요.
    # "반드시 X를 넣고 Y라고는 쓰지 마세요"처럼 조건 없이 둘 다 요구하면 둘 다 남겨요.
    exact = [c for c in kept if c["type"] == "exact_phrase"]
    for c in [c for c in kept if c["type"] == "required_phrase" and any(overlap(c, e) for e in exact)
              and CONDITIONAL.search(c["guide_quote"]["text"])]:
        kept.remove(c)
        dropped.append({"code": DUP_EXACT_PHRASE,
                        "reason": "\"~할 경우\"처럼 조건이 붙은 표기 문장에서 나온 필수 문구예요 (표기 조건으로만 봐요)",
                        "type": c["type"], "label": c["label"], "quote": c["guide_quote"]["text"]})

    # 주소가 있는 링크 조건과 주소 없는 링크 조건("링크 삽입")이 같이 나오면 하나로 합쳐요.
    # 주소가 있는 쪽을 남기고, 다른 쪽의 가이드 원문은 extra_quotes에 둬요.
    links = [c for c in kept if c["type"] == "link"]
    with_url = [c for c in links if c["params"].get("url")]
    if with_url:
        for c in [c for c in links if not c["params"].get("url")]:
            kept.remove(c)
            with_url[0].setdefault("extra_quotes", []).append(c["guide_quote"])
        if "extra_quotes" in with_url[0]:
            with_url[0]["extra_quotes"].sort(key=lambda q: q["start"])


# ── 리뷰플레이스 고정 칸을 코드로 읽기 (AI 결과의 안전망) ────────────────
# 리뷰플레이스 가이드의 이 칸들은 모양이 정해져 있어요. AI가 빠뜨리거나 값을 다르게 내도 코드가 읽은 것을 써요.
# 리뷰플레이스 모양이 아닌 가이드에서는 아무것도 하지 않아요.

RP_TITLE = re.compile(r"#\s*키워드\s*중\s*1개를\s*선택하여\s*제목(?P<tag>\s*및\s*#?\s*태그)?에\s*넣어\s*주세요\.?")
RP_BODY = re.compile(r"#\s*키워드\s*중\s*1개를\s*선택하여\s*본문에\s*(?P<n>\d+)\s*(번|회)\s*이상\s*넣어\s*주세요\.?")
RP_PERIOD = re.compile(r"리뷰\s*등록\s*기간\s*\S.*")
RP_DISCLOSURE = re.compile(r"공정위\s*대가성\s*문구")
RP_TOP = re.compile(r"상단|첫\s*부분|맨\s*위")


def _number(m: re.Match) -> int:
    return int(m["n"].replace(",", ""))


RP_MISSIONS = (      # 리뷰어 미션의 한 줄 전체가 이 모양일 때만 읽어요
    (re.compile(r"링크\s*삽입"), lambda m: {"type": "link", "label": "링크 삽입", "min": 1}),
    (re.compile(r"(?P<n>\d[\d,]*)\s*자\s*이상"),
     lambda m: {"type": "length", "label": f"{_number(m):,}자 이상", "min": _number(m), "count_spaces": "unspecified"}),
    (re.compile(r"(?P<n>\d+)\s*장\s*이상"),
     lambda m: {"type": "photo_count", "label": f"사진 {_number(m)}장 이상", "min": _number(m)}),
    (re.compile(r"동영상\s*첨부"), lambda m: {"type": "video_count", "label": "동영상 첨부", "min": 1}),
)
RP_MISSION_LINES = 12            # 리뷰어 미션 칸에서 읽는 줄 수
FIXED_VALUES = ("keywords", "tags", "min", "pick", "scope")     # 고정 칸에서 코드가 읽는 기준값


def _guide_lines(guide: str) -> list[tuple[int, int, str]]:
    """빈 줄을 뺀 줄마다 (시작, 끝, 글자). 앞뒤 공백은 빼고, 위치는 원문 기준이에요."""
    out, pos = [], 0
    for raw in guide.splitlines(keepends=True):
        text = raw.strip()
        if text:
            start = pos + len(raw) - len(raw.lstrip())
            out.append((start, start + len(text), text))
        pos += len(raw)
    return out


def read_fixed(guide: str) -> list[tuple[dict, tuple[int, int]]]:
    """리뷰플레이스 고정 칸에서 코드가 직접 만든 조건과, 그 조건이 차지하는 칸의 범위."""
    if detect_platform(guide) != "reviewplace":
        return []
    lines = _guide_lines(guide)
    found = []        # (AI 응답과 같은 모양의 조건, 인용할 줄, 칸의 범위)
    for i, (start, end, text) in enumerate(lines):
        # 키워드 칸: 칸 이름, 쉼표로 나뉜 키워드 줄, "# 키워드 중 1개를 ..." 안내 줄이 차례로 있어요
        words = [w.strip() for w in lines[i + 1][2].split(",") if w.strip()] if i + 2 < len(lines) else []
        note = lines[i + 2] if i + 2 < len(lines) else None
        if text == "제목키워드" and words and (m := RP_TITLE.fullmatch(note[2])):
            block = (start, note[1])
            found.append(({"type": "title_keyword", "label": "제목에 키워드 1개 이상", "keywords": words, "pick": "any"}, note, block))
            if m["tag"]:
                found.append(({"type": "hashtag", "label": "#태그에 키워드 1개 이상", "tags": ["#" + w for w in words],
                               "pick": "any"}, note, block))
        elif text == "본문키워드" and words and (m := RP_BODY.fullmatch(note[2])):
            found.append(({"type": "keyword_count", "label": f"본문 키워드 1개를 {_number(m)}번 이상", "keywords": words,
                           "min": _number(m), "pick": "any", "scope": "body"}, note, (start, note[1])))
        elif text == "리뷰어 미션":
            for line in lines[i + 1:i + 1 + RP_MISSION_LINES]:
                if line[2] in REVIEWPLACE_HEADS or RP_PERIOD.fullmatch(line[2]):
                    break
                for pattern, make in RP_MISSIONS:
                    if m := pattern.fullmatch(line[2]):
                        found.append((make(m), line, line[:2]))
                        break
        elif RP_PERIOD.fullmatch(text):
            found.append(({"type": "outside_draft", "label": "리뷰 등록기간", "what": "기간"}, lines[i], (start, end)))
        elif RP_DISCLOSURE.search(text):
            found.append(({"type": "disclosure", "label": "대가성 문구를 리뷰 상단에" if RP_TOP.search(text) else "대가성 문구",
                           "position": "top" if RP_TOP.search(text) else ""}, lines[i], (start, end)))
    out, made = [], set()
    for rc, (qs, qe, text), block in found:
        if rc["type"] in made:
            continue                  # 같은 칸이 또 나와도 조건 종류마다 하나만 만들어요 (처음 것). 많아야 9개예요
        made.add(rc["type"])
        try:
            cond = make_condition(guide, {**rc, "quote": text})
        except Drop:
            continue                  # 칸의 값이 상한을 넘는 등 모양이 예상과 다르면 코드가 만들지 않아요
        cond["guide_quote"] = {"text": guide[qs:qe], "start": qs, "end": qe}
        cond["source"] = "rule"
        out.append((cond, block))
    return out


def apply_fixed(guide: str, kept: list[dict], dropped: list[dict]) -> list[tuple[int, int]]:
    """코드가 읽은 고정 칸 조건을 AI 결과에 맞춰 넣어요. 고정 칸의 범위들을 돌려줘요.

    - AI 결과에 같은 조건(같은 종류, 같은 칸)이 없으면 코드가 만든 것을 넣어요 (source: "rule").
    - 있으면 AI 것을 쓰되, 기준값(키워드, 태그, 숫자, pick, scope)과 인용 줄은 코드가 읽은 것으로 맞춰요.
      이 칸은 모양이 정해져 있어서 needs_review는 달지 않아요.
    """
    blocks = []
    for rule, (bs, be) in read_fixed(guide):
        blocks.append((bs, be))
        inside = lambda q: q["start"] < be and bs < q["end"]
        same = [c for c in kept if c["type"] == rule["type"] and any(inside(q) for q in (c["guide_quote"], *c.get("extra_quotes", [])))]
        if not same:
            kept.append(rule)
            continue
        mine = same[0]
        for again in same[1:]:           # 같은 칸에서 같은 종류가 두 번 나왔으면 하나만 남겨요
            kept.remove(again)
            dropped.append({"code": DUPLICATE, "reason": "같은 칸에서 같은 조건이 두 번 나왔어요", "type": again["type"],
                            "label": again["label"], "quote": again["guide_quote"]["text"]})
        mine["params"].update({k: v for k, v in rule["params"].items() if k in FIXED_VALUES})
        mine["params"].pop("needs_review", None)
        if inside(mine["guide_quote"]):
            mine["guide_quote"] = rule["guide_quote"]
    return blocks


# ── 조용히 버리지 않기 ───────────────────────────────────────────────────
# AI가 낸 조건을 확인하지 못해 버렸으면, 조건표에 "직접 봐 주세요" 안내를 조건 하나로 남겨요 (점검에서는 판단 보류).
# 안내에는 코드가 가이드에서 찾은 줄만 실어요. AI가 쓴 인용이나 라벨은 싣지 않아요.

NOTICE_CODES = (QUOTE_NOT_FOUND, VALUE_NOT_IN_GUIDE, SCHEMA_INVALID, LIMIT_EXCEEDED)
NOTICE_LABEL = "조건 하나를 확인하지 못했어요"
NOTICE_QUESTION = "가이드의 이 부분을 직접 봐 주세요"
NOTICE_QUESTION_NO_LINE = "가이드를 직접 다시 봐 주세요"
MAX_NOTICES = 10
SIMILAR = 0.5                    # 줄과 인용이 이만큼 닮았으면 그 줄로 봐요 (우리 기준, 두 글자씩 묶어 겹치는 비율)


def _pairs(text: str) -> set[str]:
    flat = _flat(text)[0]
    return {flat[i:i + 2] for i in range(len(flat) - 1)}


def locate_line(guide: str, lines: list, quote, line_pairs: list | None = None) -> tuple[tuple[int, int] | None, bool]:
    """AI가 쓴 인용이 가리키는 가이드 줄과, 인용이 원문에 실제로 있었는지.

    그대로 있으면 (그 줄, True), 없으면 (가장 닮은 줄, False), 닮은 줄도 없으면 (None, False).
    """
    if not isinstance(quote, str) or not quote.strip():
        return None, False
    found = find_quote(guide, quote)
    if found:
        return next(((s, e) for s, e, _ in lines if s <= found[0] < e), found), True
    if line_pairs is None:
        line_pairs = []
    if not line_pairs:                    # 줄마다 한 번만 계산해 둬요
        line_pairs.extend(_pairs(text) for _, _, text in lines)
    want = _pairs(quote)
    best, best_score = None, SIMILAR
    for (s, e, _), have in zip(lines, line_pairs):
        score = 2 * len(want & have) / (len(want) + len(have)) if want and have else 0
        if score > best_score:
            best, best_score = (s, e), score
    return best, False


def add_notices(guide: str, kept: list[dict], dropped: list[dict], blocks: list[tuple[int, int]]) -> None:
    lines = _guide_lines(guide)
    line_pairs: list = []
    seen = set()
    for d in dropped:
        if d.get("code") not in NOTICE_CODES:
            continue                      # 같은 조건이라 합친 것(키워드 줄, 겹친 표기 등)은 안내하지 않아요
        span, exact = locate_line(guide, lines, d.get("quote"), line_pairs)
        if exact and any(bs < span[1] and span[0] < be for bs, be in blocks):
            continue                      # 인용이 고정 칸의 줄에 실제로 있으면, 그 줄은 코드가 직접 읽었어요
        key = span or (d.get("type") if d.get("type") in TYPES else None)
        if key in seen or len(seen) >= MAX_NOTICES:
            continue
        seen.add(key)
        start, end = span or (0, 0)
        kept.append({
            "id": "", "type": "judgment", "label": NOTICE_LABEL, "countable": False,
            "params": {"question": NOTICE_QUESTION if span else NOTICE_QUESTION_NO_LINE, "unverified": True},
            "guide_quote": {"text": guide[start:end], "start": start, "end": end},
        })


def build(guide: str, raw: dict, guide_id: str | None = None) -> tuple[dict, list[dict]]:
    """LLM이 뽑은 것(raw)을 확인해서 (조건 목록, 버린 목록)으로 만들어요."""
    kept, dropped = [], []
    items = raw.get("conditions") if isinstance(raw, dict) else None
    for rc in items if isinstance(items, list) else []:
        try:
            if not isinstance(rc, dict):
                raise Drop(SCHEMA_INVALID, "조건 모양이 아니에요")
            if len(kept) >= MAX_CONDITIONS:
                raise Drop(LIMIT_EXCEEDED, "조건이 너무 많아요")
            cond = make_condition(guide, rc)
            if any(cond == k for k in kept):
                raise Drop(DUPLICATE, "같은 조건이 두 번 나왔어요")
            kept.append(cond)
        except Drop as why:
            safe = rc if isinstance(rc, dict) else {}
            clip = lambda v: " ".join(v.split())[:200] if isinstance(v, str) else None     # 버린 목록도 글자로만, 짧게
            if len(dropped) < MAX_DROPPED:
                dropped.append({"code": why.code, "reason": str(why), "type": clip(safe.get("type")),
                                "label": clip(safe.get("label")), "quote": clip(safe.get("quote"))})
    blocks = apply_fixed(guide, kept, dropped)
    tidy_overlaps(kept, dropped)
    add_notices(guide, kept, dropped, blocks)
    kept.sort(key=lambda c: c["guide_quote"]["start"])     # 가이드에 나온 순서. 같은 자리는 LLM이 낸 순서
    for i, cond in enumerate(kept, 1):
        cond["id"] = f"c{i}"
    doc = {"version": VERSION}
    if guide_id:
        doc["guide_id"] = guide_id
    doc["platform"] = detect_platform(guide)
    doc["campaign_type"] = check_campaign_type(guide, raw.get("campaign_type") if isinstance(raw, dict) else None)
    doc["conditions"] = kept
    return doc, dropped


def drop_counts(dropped: list[dict]) -> dict[str, int]:
    """버린 이유를 "이유 코드:조건 종류" → 개수로. 기록에 남겨도 되는 것만 담아요 (가이드 글과 AI가 쓴 글은 없어요)."""
    out: dict[str, int] = {}
    for d in dropped:
        kind = d.get("type") if d.get("type") in TYPES else "?"       # AI가 낸 종류는 아무 글자나 올 수 있어요
        key = f'{d.get("code") if d.get("code") in DROP_CODES else "?"}:{kind}'
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


# ── 캐시 (개발용) ────────────────────────────────────────────────────────

def cache_dir_for(guide_file: Path) -> Path:
    """가이드 파일이 private 폴더 아래에 있으면 private 캐시를, 아니면 보통 캐시를 써요."""
    return PRIVATE_CACHE_DIR if "private" in Path(guide_file).resolve().parts else CACHE_DIR


def cache_path(cache_dir: Path, guide: str) -> Path:
    key = hashlib.sha256("\n".join((model_name(), PROMPT_VERSION, guide)).encode("utf-8")).hexdigest()[:32]
    return Path(cache_dir) / f"{key}.json"


def cached(cache_dir: Path | None, guide: str) -> dict | None:
    if cache_dir is None:
        return None
    path = cache_path(cache_dir, guide)
    return json.loads(path.read_text(encoding="utf-8"))["raw"] if path.exists() else None


def extract(guide: str, *, llm=None, cache_dir: Path | None = None, guide_id: str | None = None):
    """가이드 원문 → (조건 목록, 버린 목록).

    같은 가이드·모델·프롬프트면 cache_dir의 결과를 쓰고 API를 다시 부르지 않아요.
    cache_dir가 없으면 아무것도 파일에 남기지 않아요.
    """
    raw = cached(cache_dir, guide)
    if raw is None:
        raw = (llm or call_llm)(guide)
        if cache_dir is not None:
            path = cache_path(cache_dir, guide)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"model": model_name(), "prompt": PROMPT_VERSION, "raw": raw},
                                       ensure_ascii=False, indent=2), encoding="utf-8")
    return build(guide, raw, guide_id)
