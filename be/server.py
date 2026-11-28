"""서버: 화면(fe/)을 내보내고, 조건 뽑기와 점검을 이어 줘요.

실행 (저장소 맨 위 폴더에서): python -m uvicorn be.server:app --port 8000
API 키 없이: PROMPATCH_AI_MODE=recorded (저장된 예시 응답만 써요. ai/ 코드가 없으면 늘 이 모드예요. be/recorded.py)

주소
- POST /api/extract   {"guide": "..."}                        → {"conditions": 조건 목록, "dropped": 버린 목록}
- POST /api/check     {"conditions": 조건 목록, "request": 점검 요청} → 점검 결과 (정적 분석만, AI 안 부름)
- POST /api/judge     {"conditions": 조건 목록, "request": 점검 요청} → 점검 결과 (정성 조건만 AI로 채움)
- POST /api/feedback  {"consent": true, "kind", "id", "label", "status"} → {"saved": true}
- GET  /api/health

지키는 것 (.claude/claude-security-guidance.md)
- 서버가 밖으로 보내는 요청은 AI API 하나뿐이에요 (ai.client.call). 네이버나 체험단 플랫폼에 접속하지 않아요.
- 받은 가이드·원고 글은 점검에만 쓰고, 파일·DB·로그에 남기지 않아요. 오류가 나도 오류 종류만 남겨요.
- "판정이 틀렸어요"는 동의한 경우에만, 조건 이름과 판정만 저장해요.
- 주고받는 값은 contracts/ 형식으로 확인해요. 길이 한도는 AI를 부르기 전에 확인해요.
- IP별 한도는 X-Forwarded-For를 그대로 믿지 않아요.
"""
from __future__ import annotations

import functools
import json
import os
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from jsonschema import Draft202012Validator

from . import engine, recorded
from .events import log_event, ms

ROOT = Path(__file__).resolve().parent.parent
# AI 코드(ai/)가 있을 때만 불러와요. 없으면 저장된 응답 모드로만 돌아요 (be/recorded.py).
# 있는데 불러오다 실패하면 그대로 오류를 내요 (설치가 깨진 것을 숨기지 않아요).
AI_READY = (ROOT / "ai" / "extract.py").exists()
if AI_READY:
    from ai import client as ai_client
    from ai import extract as ai_extract
    from ai import judge as ai_judge
FE = ROOT / "fe"
FEEDBACK_FILE = Path(__file__).resolve().parent / "data" / "feedback.jsonl"   # 저장소에 올라가지 않아요
# 화면에 필요한 파일만 내보내요 (테스트 파일, 만드는 스크립트, 자체 시험 파일은 내보내지 않아요)
STATIC = {
    "": ("index.html", "text/html; charset=utf-8"),
    "index.html": ("index.html", "text/html; charset=utf-8"),
    "style.css": ("style.css", "text/css; charset=utf-8"),
    "analyze.js": ("analyze.js", "text/javascript; charset=utf-8"),
    "mock-data.js": ("mock-data.js", "text/javascript; charset=utf-8"),
    "api.js": ("api.js", "text/javascript; charset=utf-8"),
    "reader.js": ("reader.js", "text/javascript; charset=utf-8"),
    "results.js": ("results.js", "text/javascript; charset=utf-8"),
    "app.js": ("app.js", "text/javascript; charset=utf-8"),
    "privacy.html": ("privacy.html", "text/html; charset=utf-8"),
    "404.html": ("404.html", "text/html; charset=utf-8"),
    "favicon.svg": ("favicon.svg", "image/svg+xml"),
    "favicon-16.png": ("favicon-16.png", "image/png"),
    "favicon-32.png": ("favicon-32.png", "image/png"),
    "og-image.png": ("og-image.png", "image/png"),
    "fonts/Pretendard-Regular.subset.woff2": ("fonts/Pretendard-Regular.subset.woff2", "font/woff2"),
    "fonts/Pretendard-Bold.subset.woff2": ("fonts/Pretendard-Bold.subset.woff2", "font/woff2"),
    "fonts/OFL-Pretendard.txt": ("fonts/OFL-Pretendard.txt", "text/plain; charset=utf-8"),
}

MAX_BODY = 400_000        # 요청 본문 바이트
MAX_GUIDE = 20_000        # 가이드 글자 수 (AI에 보내는 한도는 PROMPATCH_AI_MAX_GUIDE)
MAX_DRAFT = 60_000        # 원고 글자 수
MAX_CONDITIONS = 80       # 조건 개수
MAX_ITEMS = 50            # 조건 하나의 키워드·태그·금지어 개수
MAX_ITEMS_TOTAL = 400     # 조건 전체의 키워드·태그·금지어 개수
MAX_ITEM_CHARS = 200      # 키워드·문구 하나의 글자 수
MAX_FEEDBACK_BYTES = 5_000_000
FEEDBACK_KEEP_DAYS = 183   # "판정이 틀렸어요" 기록은 6개월 동안만 둬요 (fe/privacy.html)
WINDOW = 600              # 한도를 세는 시간 (초)


def env_number(name: str, default: int, allow_zero: bool = False) -> int:
    """환경 변수의 숫자. 비어 있거나 숫자가 아니면 기본값을 써요."""
    value = os.environ.get(name, "").strip()
    if value.isdigit() and (int(value) > 0 or allow_zero):
        return int(value)
    return default


recorded.load_env()                                                  # .env를 먼저 읽고 나서 아래 값을 정해요
# AI를 부르는 주소는 돈이 들어서 횟수를 막아요.
# ponytail: 서버 한 대의 메모리에만 세요. 서버를 여러 대로 늘리면 공용 저장소(예: Redis)로 옮겨야 해요.
EXTRACT_PER_IP = env_number("PROMPATCH_EXTRACT_PER_IP", 10)          # IP 하나가 10분에
EXTRACT_PER_DAY = env_number("PROMPATCH_EXTRACT_PER_DAY", 500)       # 서버 전체가 하루에
# 서버 앞에 있는, 믿을 수 있는 프록시의 수. 0이면 X-Forwarded-For를 아예 보지 않아요.
# 이 헤더는 요청하는 쪽이 마음대로 적을 수 있어서, 믿는 프록시가 붙인 뒤쪽 값만 읽어요.
PROXY_HOPS = env_number("PROMPATCH_PROXY_HOPS", 0, allow_zero=True)
# AI에 보내는 글의 한도 (AI를 부르기 전에 확인). 정적 분석 한도(MAX_GUIDE, MAX_DRAFT)보다 클 수는 없어요.
AI_MAX_GUIDE = min(env_number("PROMPATCH_AI_MAX_GUIDE", MAX_GUIDE), MAX_GUIDE)
AI_MAX_DRAFT = min(env_number("PROMPATCH_AI_MAX_DRAFT", 20_000), MAX_DRAFT)
JUDGE_RETRY = "정성 판단은 잠시 뒤 다시 시도해 주세요"


def _schema(name: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((ROOT / "contracts" / f"{name}.schema.json").read_text(encoding="utf-8")))


SCHEMAS = {name: _schema(name) for name in ("conditions", "check-request", "check-result")}


class Problem(Exception):
    """화면에 보여 줄 오류. 메시지에 받은 글을 넣지 않아요."""

    def __init__(self, status: int, message: str):
        self.status, self.message = status, message


def shape_errors(kind: str, data) -> list[str]:
    """형식에 안 맞는 곳의 위치만 돌려줘요. 값(글)은 넣지 않아요."""
    return sorted({"/".join(str(p)[:40] for p in e.path) or "(맨 위)" for e in SCHEMAS[kind].iter_errors(data)})


def require_shape(kind: str, data, name: str) -> None:
    bad = shape_errors(kind, data)
    if bad:
        raise Problem(422, f"{name} 형식이 달라요: " + ", ".join(bad[:8]))


def require_small(conditions: dict) -> None:
    """조건 목록이 지나치게 크면 거절해요. 큰 입력으로 서버를 오래 붙잡는 것을 막아요."""
    total = 0
    if len(conditions["conditions"]) > MAX_CONDITIONS:
        raise Problem(413, "조건이 너무 많아요.")
    for cond in conditions["conditions"]:
        for value in cond["params"].values():
            items = value if isinstance(value, list) else [value]
            if len(items) > MAX_ITEMS:
                raise Problem(413, "조건 하나에 키워드가 너무 많아요.")
            total += len(items) if isinstance(value, list) else 0
            if any(isinstance(v, str) and len(v) > MAX_ITEM_CHARS for v in items):
                raise Problem(413, "키워드나 문구가 너무 길어요.")
            if any(isinstance(v, (dict, list)) for v in items):
                raise Problem(422, "조건 목록 형식이 달라요: params")
    if total > MAX_ITEMS_TOTAL:
        raise Problem(413, "조건에 든 키워드가 너무 많아요.")


class Limiter:
    """한 주소(IP)가 10분에 부를 수 있는 횟수와, 서버 전체가 하루에 받을 횟수를 막아요."""

    def __init__(self, per_ip, per_day):
        self.per_ip, self.per_day = per_ip, per_day      # 숫자, 또는 숫자를 돌려주는 함수
        self.lock = threading.Lock()
        self.by_ip: dict[str, list[float]] = {}
        self.day, self.count = "", 0

    def allow(self, ip: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        per_ip = self.per_ip() if callable(self.per_ip) else self.per_ip
        per_day = self.per_day() if callable(self.per_day) else self.per_day
        with self.lock:
            today = time.strftime("%Y-%m-%d", time.gmtime(now))
            if today != self.day:
                self.day, self.count = today, 0
            recent = [t for t in self.by_ip.get(ip, []) if now - t < WINDOW]
            if len(recent) >= per_ip or self.count >= per_day:
                self.by_ip[ip] = recent
                return False
            self.by_ip[ip] = recent + [now]
            self.count += 1
            if len(self.by_ip) > 5000:      # 오래된 IP 기록은 지워요
                self.by_ip = {k: v for k, v in self.by_ip.items() if v and now - v[-1] < WINDOW}
            return True


def new_limiters() -> dict[str, Limiter]:
    return {
        "extract": Limiter(lambda: EXTRACT_PER_IP, lambda: EXTRACT_PER_DAY),   # AI를 불러요 (돈이 들어요)
        "judge": Limiter(lambda: EXTRACT_PER_IP, lambda: EXTRACT_PER_DAY),     # AI를 불러요 (같은 한도)
        "check": Limiter(120, 50_000),                                         # AI는 안 부르지만 서버 일을 시켜요
        "feedback": Limiter(20, 2_000),                                        # 파일에 써요
        "timing": Limiter(120, 50_000),                                        # 걸린 시간 숫자만 기록해요
    }


limiters = new_limiters()
app = FastAPI(title="PromPatch", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def guard(request: Request, call_next):
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_BODY:
        return JSONResponse({"error": "보낸 내용이 너무 커요."}, status_code=413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    # 글꼴은 바뀌지 않는 파일이라 브라우저가 오래 들고 있게 해요 (약 540KB를 매번 받지 않게). 나머지는 저장하지 않아요
    fixed = request.url.path.startswith("/fonts/") and response.status_code == 200
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable" if fixed else "no-store"
    response.headers["X-Frame-Options"] = "DENY"                               # 다른 사이트가 이 화면을 틀 안에 넣지 못하게
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    return response


@app.exception_handler(Problem)
async def on_problem(request: Request, why: Problem):
    return JSONResponse({"error": why.message}, status_code=why.status)


@app.exception_handler(RequestValidationError)
async def on_bad_body(request: Request, why: RequestValidationError):
    return JSONResponse({"error": "보낸 내용을 읽지 못했어요."}, status_code=400)   # 받은 값을 되돌려 보내지 않아요


@app.exception_handler(Exception)
async def on_crash(request: Request, why: Exception):
    log_event("error", kind=type(why).__name__, path=request.url.path)        # 오류 종류와 주소만. 내용은 남기지 않아요
    return JSONResponse({"error": "서버에서 문제가 생겼어요. 잠시 뒤에 다시 해 주세요."}, status_code=500)


def quiet(handler):
    """주소 안에서 난 오류를 여기서 끝내요. 밖으로 새면 서버 프로그램(uvicorn)이 오류 내용까지 로그에 찍어요."""
    @functools.wraps(handler)
    async def wrapper(request: Request):
        try:
            return await handler(request)
        except Problem:
            raise
        except Exception as why:        # 오류 종류와 주소만 남겨요. 오류 문장에는 받은 글이 섞여 있을 수 있어요
            log_event("error", kind=type(why).__name__, path=request.url.path)
            return JSONResponse({"error": "서버에서 문제가 생겼어요. 잠시 뒤에 다시 해 주세요."}, status_code=500)
    return wrapper


async def body(request: Request) -> dict:
    """JSON 본문을 읽어요. 한도를 넘으면 다 읽기 전에 그만 읽어요."""
    # JSON이라고 밝힌 요청만 받아요. 다른 사이트의 화면이 방문자 몰래 이 주소를 부르는 것을 브라우저가 막게 돼요.
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise Problem(415, "JSON으로 보내 주세요.")
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BODY:
            raise Problem(413, "보낸 내용이 너무 커요.")
        chunks.append(chunk)
    try:
        data = json.loads(b"".join(chunks))
    except ValueError:
        raise Problem(400, "보낸 내용을 읽지 못했어요.") from None
    if not isinstance(data, dict):
        raise Problem(400, "보낸 내용을 읽지 못했어요.")
    return data


def client_ip(request: Request) -> str:
    """한도를 셀 때 쓰는 주소. X-Forwarded-For는 요청하는 쪽이 지어낼 수 있어서 기본으로는 보지 않아요.

    PROMPATCH_PROXY_HOPS가 n이면 "믿는 프록시가 n개 있다"는 뜻이라, 헤더의 뒤에서 n번째 값을 써요.
    (프록시는 자기가 본 주소를 맨 뒤에 붙여요. 앞쪽 값은 요청하는 쪽이 적은 것일 수 있어요.)
    """
    peer = request.client.host if request.client else "unknown"
    if PROXY_HOPS <= 0:
        return peer
    hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    return hops[-PROXY_HOPS][:64] if len(hops) >= PROXY_HOPS else peer


def tokens(usage) -> dict:
    """AI 사용량에서 기록할 숫자만. 비용은 토큰 수로 계산한 원 단위 어림값이에요 (ai/client.py의 PRICES, 환율 설정)."""
    usage = usage or {}
    return {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
            "cache_read_tokens": usage.get("cache_read_input_tokens"),
            "cache_write_tokens": usage.get("cache_creation_input_tokens"),
            "cost_krw": ai_client.cost_krw(usage, ai_extract.model_name())}


def condition_counts(conds: list) -> dict:
    """조건 수: 정적(코드가 세는 것), 정성(셀 수 없는 것), 원고 밖. 0개면 이상 징후로 표시해요."""
    out = {"conditions": len(conds),
           "conditions_static": sum(bool(c.get("countable")) for c in conds),
           "conditions_qualitative": sum(not c.get("countable") and c.get("type") != "outside_draft" for c in conds),
           "conditions_outside": sum(c.get("type") == "outside_draft" for c in conds)}
    if not conds:
        out["anomaly"] = "NO_CONDITIONS"
    return out


MANY_POSTS = "글이 여러 개 들어왔어요. 블로그 화면에서 점검할 글 하나만 열고 복사해 붙여 넣어 주세요."


def require_one_post(req: dict) -> None:
    """보기 화면에서 글 여러 개가 한꺼번에 복사됐으면 점검하지 않아요 (사진·글자 수가 섞여서 틀린 결과가 나와요)."""
    posts = engine.count_posts(req["draft_text"])
    if posts > 1:
        log_event("refused", code="MANY_POSTS", posts=posts)
        raise Problem(422, MANY_POSTS)


def checked(route: str, conditions: dict, req: dict) -> dict:
    """정적 분석(엔진)을 돌리고 시간과 개수를 기록해요."""
    started = time.perf_counter()
    result = engine.check(conditions, req)
    log_event("check", route=route, check_ms=ms(started), **condition_counts(conditions["conditions"]),
              **result["summary"], tips=len(result["tips"]))          # 팁은 개수만 남겨요
    return result


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/extract")
@quiet
async def api_extract(request: Request):
    data = await body(request)
    guide = data.get("guide")
    if not isinstance(guide, str) or not guide.strip():
        raise Problem(422, "가이드 글이 비어 있어요.")
    if len(guide) > MAX_GUIDE:                       # 길이 한도는 AI를 부르기 전에 확인해요
        raise Problem(413, f"가이드가 너무 길어요. {MAX_GUIDE:,}자까지 돼요.")
    if recorded.active(AI_READY):
        return recorded_extract(request, guide)
    no = ai_client.refuse(guide, AI_MAX_GUIDE)
    if no:
        log_event("ai_skipped", what="guide", code=no[0])
        raise Problem(413 if no[0] == ai_client.TOO_LONG else 422, f"가이드를 살펴볼 수 없어요. {no[1]}.")
    # form: 화면의 "바꾸기"로 고른 가이드 형식. 없으면 코드가 가이드 문장으로 알아봐요
    form = data.get("form") if data.get("form") in (*ai_extract.FORM_READERS, ai_extract.GENERAL) else None
    if data.get("ai") is False:
        # 나눠 보여 주기 1단계: AI 없이 코드가 고정 칸에서 읽은 조건만 바로 돌려줘요 (AI를 부르지 않아서 점검 한도로 세요)
        if not limiters["check"].allow(client_ip(request)):
            log_event("limited", route="rules")
            raise Problem(429, "너무 자주 점검했어요. 잠시 뒤에 다시 해 주세요.")
        started = time.perf_counter()
        doc, dropped = ai_extract.build(guide, {"campaign_type": None, "conditions": []}, form=form)
        log_event("rules", rules_ms=ms(started), **condition_counts(doc["conditions"]))
        require_shape("conditions", doc, "조건 목록")
        return {"conditions": doc, "dropped": dropped, "form": shown_form(form, guide)}
    if not limiters["extract"].allow(client_ip(request)):
        log_event("limited", route="extract")
        raise Problem(429, "조건표를 너무 자주 만들었어요. 10분쯤 뒤에 다시 해 주세요.")
    started = time.perf_counter()
    try:
        # 캐시 폴더 없이 불러요. 그래서 가이드 글이 파일에 남지 않아요.
        doc, dropped = await _in_thread(lambda: ai_extract.extract(guide, form=form))
    except ai_extract.ExtractError as why:
        log_event("ai_error", route="extract", code=why.code or "ExtractError", ai_ms=ms(started))
        raise Problem(502, "조건을 뽑지 못했어요. 잠시 뒤에 다시 해 주세요.") from None
    # 숫자와 정해진 코드만 남겨요 (비용과, 조건을 왜 버렸는지 보려고). 가이드 글과 AI가 쓴 글은 남기지 않아요.
    log_event("extract", ai_ms=ms(started), **tokens(ai_extract.last_usage), **condition_counts(doc["conditions"]),
              dropped=ai_extract.drop_counts(dropped))
    require_shape("conditions", doc, "조건 목록")
    # form: 가이드 형식(reviewplace, revu, gangnam, reviewnote, 모르면 null). 화면이 "레뷰 가이드로 읽었어요"처럼 보여 줘요
    return {"conditions": doc, "dropped": dropped, "form": shown_form(form, guide)}


def recorded_extract(request: Request, guide: str) -> dict:
    """저장된 응답 모드: 예시 가이드의 조건 목록을 그대로 돌려줘요. AI를 부르지 않아서 점검 한도로 세요."""
    if not limiters["check"].allow(client_ip(request)):
        log_event("limited", route="recorded")
        raise Problem(429, "너무 자주 점검했어요. 잠시 뒤에 다시 해 주세요.")
    doc = recorded.conditions(guide)
    if doc is None:
        log_event("refused", code="RECORDED_UNKNOWN_GUIDE")
        raise Problem(422, recorded.UNKNOWN)
    log_event("rules", mode="recorded", **condition_counts(doc["conditions"]))
    require_shape("conditions", doc, "조건 목록")
    return {"conditions": doc, "dropped": [], "form": doc.get("platform")}


def shown_form(form: str | None, guide: str) -> str | None:
    """화면에 적을 가이드 형식: 고른 형식, 없으면 알아본 형식. 일반 가이드는 None이에요."""
    if form == ai_extract.GENERAL:
        return None
    return form or ai_extract.detect_form(guide)


@app.post("/api/check")
@quiet
async def api_check(request: Request):
    data = await body(request)
    if not limiters["check"].allow(client_ip(request)):
        log_event("limited", route="check")
        raise Problem(429, "너무 자주 점검했어요. 조금 뒤에 다시 해 주세요.")
    conditions, req = data.get("conditions"), data.get("request")
    require_shape("conditions", conditions, "조건 목록")
    require_shape("check-request", req, "점검 요청")
    if len(req["draft_text"]) > MAX_DRAFT:
        raise Problem(413, f"원고가 너무 길어요. {MAX_DRAFT:,}자까지 돼요.")
    require_small(conditions)
    require_one_post(req)
    result = checked("check", conditions, req)
    require_shape("check-result", result, "점검 결과")
    return result


@app.post("/api/judge")
@quiet
async def api_judge(request: Request):
    """정성 조건(셀 수 없는 조건)만 AI로 판단해 점검 결과를 채워요. 정적 결과는 /api/check로 먼저 보여 줘요.

    AI가 실패하면 502와 "정성 판단은 잠시 뒤 다시 시도해 주세요"를 돌려줘요. 화면은 정적 결과를 그대로 둬요.
    """
    data = await body(request)
    if not limiters["check"].allow(client_ip(request)):      # 정적 분석도 서버 일이라 /api/check와 같은 한도를 먼저 세요
        log_event("limited", route="judge")
        raise Problem(429, "너무 자주 점검했어요. 조금 뒤에 다시 해 주세요.")
    conditions, req = data.get("conditions"), data.get("request")
    require_shape("conditions", conditions, "조건 목록")
    require_shape("check-request", req, "점검 요청")
    if len(req["draft_text"]) > MAX_DRAFT:
        raise Problem(413, f"원고가 너무 길어요. {MAX_DRAFT:,}자까지 돼요.")
    require_small(conditions)
    require_one_post(req)
    result = checked("judge", conditions, req)
    if recorded.active(AI_READY):
        return result                                   # 저장된 응답 모드: AI 없이 코드로 센 결과만
    if not ai_judge.qualitative(conditions):
        return result                                   # AI에게 물을 조건이 없으면 부르지 않아요
    no = ai_client.refuse(req["draft_text"], AI_MAX_DRAFT)
    if not no and ai_client.looks_like_guide(req["draft_text"], [c["guide_quote"]["text"] for c in conditions["conditions"]]):
        no = (ai_client.SAME_AS_GUIDE, "원고 칸에 가이드를 넣은 것 같아요")
    if no:
        log_event("ai_skipped", what="draft", code=no[0])
        raise Problem(422, f"정성 판단을 하지 않았어요. {no[1]}.")
    if not limiters["judge"].allow(client_ip(request)):
        log_event("limited", route="judge_ai")
        raise Problem(429, f"너무 자주 불렀어요. {JUDGE_RETRY}.")
    started = time.perf_counter()
    try:
        judged, info = await _in_thread(ai_judge.judge, conditions, req["draft_text"])
    except ai_client.AIError as why:
        log_event("ai_error", route="judge", code=why.code, ai_ms=ms(started))
        raise Problem(502, f"{JUDGE_RETRY}.") from None
    log_event("judge", ai_ms=ms(started), **tokens(info.get("usage")), asked=info["asked"], judged=len(judged),
              unsupported=info["unsupported"], scope=info["scope"])
    by_id = {r["condition_id"]: r for r in judged}
    result["results"] = [by_id.get(r["condition_id"], r) for r in result["results"]]
    result["summary"] = engine.summarize(conditions["conditions"], result["results"])
    require_shape("check-result", result, "점검 결과")
    return result


@app.post("/api/timing")
@quiet
async def api_timing(request: Request):
    """화면이 잰 시간(숫자만): 점검하기를 누르고 첫 결과(코드가 읽은 결과)까지, 전체 결과(가이드의 나머지까지)까지.
    가이드·원고 글은 받지 않아요. 숫자가 아니면 받지 않아요."""
    data = await body(request)
    def millis(key):
        v = data.get(key)
        if v is None and key == "full_ms":
            return None
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 600_000:
            raise Problem(422, "보낸 내용을 읽지 못했어요.")
        return v
    first, full = millis("first_ms"), millis("full_ms")
    if data.get("ai") not in ("done", "failed"):
        raise Problem(422, "보낸 내용을 읽지 못했어요.")
    if not limiters["timing"].allow(client_ip(request)):
        raise Problem(429, "너무 자주 보냈어요.")
    log_event("timing", first_ms=first, full_ms=full, ai=data["ai"])
    return {"ok": True}


@app.post("/api/feedback")
@quiet
async def api_feedback(request: Request):
    """동의한 경우에만, 조건 이름과 판정만 저장해요. 원고 글과 note는 받지도 저장하지도 않아요."""
    data = await body(request)
    if data.get("consent") is not True:
        raise Problem(422, "동의가 있어야 보낼 수 있어요.")
    if data.get("kind") not in ("condition", "principle") or data.get("status") not in ("kept", "missing", "hold"):
        raise Problem(422, "보낸 내용을 읽지 못했어요.")
    if not limiters["feedback"].allow(client_ip(request)):
        raise Problem(429, "너무 자주 보냈어요. 조금 뒤에 다시 해 주세요.")
    if FEEDBACK_FILE.exists() and FEEDBACK_FILE.stat().st_size > MAX_FEEDBACK_BYTES:
        log_event("error", kind="FEEDBACK_FULL", path="/api/feedback")
        raise Problem(503, "지금은 받을 수 없어요. 나중에 다시 해 주세요.")
    record = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kind": data["kind"],
        "id": str(data.get("id", ""))[:20],
        "type": str(data.get("type", ""))[:30],
        "label": str(data.get("label", ""))[:120],
        "status": data["status"],
    }
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    drop_old_feedback()
    with FEEDBACK_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"saved": True}


def drop_old_feedback(now: float | None = None) -> None:
    """6개월이 지난 기록을 지워요. 새 기록을 쓸 때마다 한 번 봐요."""
    if not FEEDBACK_FILE.exists():
        return
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime((time.time() if now is None else now) - FEEDBACK_KEEP_DAYS * 86400))
    lines = FEEDBACK_FILE.read_text(encoding="utf-8").splitlines()
    def recent(line: str) -> bool:
        try:
            return str(json.loads(line).get("at", "")) >= cutoff
        except ValueError:
            return False                      # 읽을 수 없는 줄은 지워요
    kept = [line for line in lines if recent(line)]
    if len(kept) != len(lines):
        FEEDBACK_FILE.write_text("".join(line + "\n" for line in kept), encoding="utf-8")


@app.get("/{name:path}")
def static(name: str):
    file, kind = STATIC.get(name, (None, None))
    if file is None or not (FE / file).exists():          # 화면 파일이 아직 없는 저장소(FE PR 전)에서도 404로 답해요
        if name.startswith("api/") or not (FE / "404.html").exists():
            return JSONResponse({"error": "없는 주소예요."}, status_code=404)
        return FileResponse(FE / "404.html", media_type="text/html; charset=utf-8", status_code=404)
    return FileResponse(FE / file, media_type=kind)


async def _in_thread(fn, *args):
    import anyio
    return await anyio.to_thread.run_sync(fn, *args)
