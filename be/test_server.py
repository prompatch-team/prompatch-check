"""서버 테스트. 실행: python -m unittest be.test_server

AI API를 부르지 않아요. AI 자리에 가짜 응답을 넣어요.
- 주소 세 개가 contracts 형식대로 주고받는지
- 받은 가이드·원고 글이 로그·파일에 남지 않는지, 밖으로 나가는 연결이 없는지
- 크롬이 있으면 화면까지 붙여서 끝까지 눌러 봐요 (없으면 그 시험만 건너뛰어요)
"""
import contextlib
import html
import io
import json
import os
import logging
import re
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

try:
    import uvicorn
    from fastapi.testclient import TestClient
except ImportError:            # 서버 패키지(be/requirements.txt)가 없는 컴퓨터: 서버 시험은 건너뛰어요
    uvicorn = TestClient = None

from ai import client as ai_client
from ai import extract as ai_extract
from ai import judge as ai_judge
from ai.test_extract import as_llm_output, said
from be import engine, events

server = None
if TestClient is not None:
    from be import server

ROOT = Path(__file__).resolve().parent.parent
# 화면(fe/)이 있는 저장소에서만 도는 시험 (팀 저장소에서는 FE PR 전에 건너뛰어요)
needs_screen = unittest.skipUnless((ROOT / "fe" / "index.html").exists(), "화면 파일(fe/)이 아직 없어요")
needs_server = unittest.skipIf(server is None, "서버 패키지가 없어요 (pip install -r be/requirements.txt)")

@contextlib.contextmanager
def captured():
    """서버 기록(be/events.py, 표준 출력 JSON 한 줄씩)을 모아요. output은 줄 목록이에요."""
    out, box = io.StringIO(), type("Box", (), {})()
    box.output = []
    with contextlib.redirect_stdout(out):
        yield box
    box.output = out.getvalue().splitlines()
    box.events = [json.loads(line) for line in box.output]


SECRET_GUIDE = "솔바람찻집비밀가이드"       # 로그에 새면 안 되는 표시 글자
SECRET_DRAFT = "아무도몰라야하는원고문장"
ANY_GUIDE = "본문에 키워드를 3회 이상 넣고, 사진은 15장 이상 올려 주세요."   # AI를 부르기 전 막기(의미 없는 글)를 지나는 짧은 가이드


def load(*parts) -> dict:
    return json.loads(ROOT.joinpath(*parts).read_text(encoding="utf-8"))


def text(*parts) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def fake_llm(guide: str) -> dict:
    """가이드 글을 보고 그 예시의 조건을 "AI가 뽑은 것처럼" 돌려줘요."""
    fake_llm.calls += 1
    for guide_file, example in (("guide-sample.md", "conditions.example.json"), ("guide-sample-2.md", "conditions.example-2.json")):
        if guide.strip() == text("samples", guide_file).strip():
            return as_llm_output(load("contracts", example))
    return {"campaign_type": "모름", "conditions": []}


fake_llm.calls = 0


def fake_judge(request: dict):
    """정성 판단 자리의 가짜 AI. 받은 조건마다 "지킴"을 돌려줘요 (근거 문장 없음)."""
    fake_judge.calls += 1
    ids = re.findall(r'"id": "([^"]+)"', request["messages"][0]["content"])
    return {"results": [{"id": i, "status": "kept", "quote": "", "reason": "가짜 판단이에요"} for i in ids]},         {"input_tokens": 100, "output_tokens": 20, "cache_read_input_tokens": 80}


fake_judge.calls = 0


@needs_server
class ServerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.feedback = Path(self.tmp.name) / "data" / "feedback.jsonl"
        fake_llm.calls = fake_judge.calls = 0
        for target, value in ((ai_extract, ("call_llm", fake_llm)), (ai_judge, ("call_llm", fake_judge)),
                              (server, ("FEEDBACK_FILE", self.feedback)),
                              (server, ("limiters", server.new_limiters()))):
            patcher = mock.patch.object(target, *value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.client = TestClient(server.app, raise_server_exceptions=False)

    def post(self, path, payload, **kw):
        return self.client.post(path, json=payload, **kw)


class Api(ServerCase):
    def test_extract_returns_the_conditions_contract(self):
        r = self.post("/api/extract", {"guide": text("samples", "guide-sample-2.md")})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["conditions"]["conditions"], load("contracts", "conditions.example-2.json")["conditions"])
        self.assertEqual((r.json()["dropped"], fake_llm.calls), ([], 1))

    def test_dropped_conditions_are_logged_as_codes_only_and_shown_as_a_notice(self):
        """AI가 낸 조건을 버리면: 서버 기록에는 이유 코드·종류·개수만, 조건표에는 "직접 봐 주세요" 안내가 남아요."""
        guide = "솔바람 찻집 체험단 안내\n사진은 12장 이상 올려 주세요.\n"
        bad = said("length", "사진은 12장 이상 올려 주세요.", "AI가 쓴 비밀 라벨")           # 숫자 없는 글자 수 조건
        with mock.patch.object(ai_extract, "call_llm", lambda g: {"campaign_type": "모름", "conditions": [bad]}), \
                captured() as logs:
            r = self.post("/api/extract", {"guide": guide})
        self.assertEqual(r.status_code, 200)
        self.assertEqual([d["code"] for d in r.json()["dropped"]], ["SCHEMA_INVALID"])
        (notice,) = r.json()["conditions"]["conditions"]
        self.assertEqual((notice["params"]["unverified"], notice["guide_quote"]["text"]), (True, "사진은 12장 이상 올려 주세요."))
        line = " ".join(logs.output)
        self.assertIn("SCHEMA_INVALID:length", line)
        for secret in ("사진은", "비밀 라벨", "솔바람"):
            self.assertNotIn(secret, line)

    def test_check_returns_what_the_engine_returns(self):
        conditions, request = load("contracts", "conditions.example.json"), load("contracts", "check-request.example.json")
        r = self.post("/api/check", {"conditions": conditions, "request": request})
        self.assertEqual((r.status_code, r.json()), (200, engine.check(conditions, request)))
        self.assertEqual(r.json()["summary"], {"kept": 1, "missing": 4, "hold": 3})        # 정답지 1의 요약
        # 도움이 될 팁은 따로 오고(판정 없음), 있어도 요약 개수는 위와 같아요
        self.assertEqual([(t["kind"], "status" in t) for t in r.json()["tips"]], [("keyword_place", False)])
        again = [self.post("/api/check", {"conditions": conditions, "request": request}).json() for _ in range(3)]
        self.assertTrue(all(a == r.json() for a in again))                                   # 같은 원고를 3번 넣어도 같음
        self.assertEqual(fake_llm.calls, 0)                                                  # 점검은 AI를 부르지 않음

    def test_guide_to_result_end_to_end(self):
        doc = self.post("/api/extract", {"guide": text("samples", "guide-sample.md")}).json()["conditions"]
        result = self.post("/api/check", {"conditions": doc, "request": load("contracts", "check-request.example.json")}).json()
        self.assertEqual(result["summary"], {"kept": 1, "missing": 4, "hold": 3})

    def test_wrong_shapes_are_refused_without_echoing_the_text(self):
        request = load("contracts", "check-request.example.json")
        conditions = load("contracts", "conditions.example.json")
        bad = [
            self.post("/api/extract", {"guide": ""}),
            self.post("/api/extract", {"guide": 123}),
            self.post("/api/check", {"conditions": conditions, "request": dict(request, counts_source="auto", draft_text=SECRET_DRAFT)}),
            self.post("/api/check", {"conditions": {"version": "0.1", "conditions": []}, "request": request}),
            self.post("/api/check", {"request": request}),
            self.client.post("/api/check", content=("{" + SECRET_DRAFT).encode(), headers={"content-type": "application/json"}),
            self.client.post("/api/check", content=b"[1, 2]", headers={"content-type": "application/json"}),
        ]
        self.assertEqual([r.status_code for r in bad], [422, 422, 422, 422, 422, 400, 400])
        for r in bad:
            self.assertIn("error", r.json())
            self.assertNotIn(SECRET_DRAFT, r.text)
        self.assertIn("counts_source", bad[2].json()["error"])        # 어디가 틀렸는지는 알려 줘요

    def test_size_limits(self):
        request = load("contracts", "check-request.example.json")
        conditions = load("contracts", "conditions.example.json")
        self.assertEqual(self.post("/api/extract", {"guide": "가" * (server.MAX_GUIDE + 1)}).status_code, 413)
        long = dict(request, draft_text="가" * (server.MAX_DRAFT + 1))
        self.assertEqual(self.post("/api/check", {"conditions": conditions, "request": long}).status_code, 413)
        self.assertEqual(self.client.post("/api/check", content=b"x" * (server.MAX_BODY + 1),
                                          headers={"content-type": "application/json"}).status_code, 413)
        self.assertEqual(fake_llm.calls, 0)

    def test_ai_calls_are_limited_per_address(self):
        with mock.patch.object(server, "EXTRACT_PER_IP", 2), mock.patch.object(server, "PROXY_HOPS", 1):
            codes = [self.post("/api/extract", {"guide": ANY_GUIDE}, headers={"x-forwarded-for": "203.0.113.5"}).status_code
                     for _ in range(3)]
            other = self.post("/api/extract", {"guide": ANY_GUIDE}, headers={"x-forwarded-for": "203.0.113.6"}).status_code
        self.assertEqual((codes, other, fake_llm.calls), ([200, 200, 429], 200, 3))

    def test_ai_failure_gives_a_plain_message(self):
        def broken(guide):
            raise ai_extract.ExtractError("API 키가 맞지 않아요") from ValueError(SECRET_GUIDE)
        with mock.patch.object(ai_extract, "call_llm", broken), captured() as logs:
            r = self.post("/api/extract", {"guide": SECRET_GUIDE + " " + ANY_GUIDE})
        self.assertEqual((r.status_code, r.json()), (502, {"error": "조건을 뽑지 못했어요. 잠시 뒤에 다시 해 주세요."}))
        self.assertNotIn(SECRET_GUIDE, "\n".join(logs.output))

    def test_feedback_needs_consent_and_stores_only_condition_and_status(self):
        base = {"kind": "condition", "id": "c3", "label": "본문 키워드 4번 이상", "status": "kept"}
        self.assertEqual(self.post("/api/feedback", base).status_code, 422)                          # 동의 없음
        self.assertEqual(self.post("/api/feedback", dict(base, consent="yes")).status_code, 422)      # true가 아님
        self.assertFalse(self.feedback.exists())
        extra = dict(base, consent=True, note=SECRET_DRAFT, draft_text=SECRET_DRAFT, label="가" * 500)
        self.assertEqual(self.post("/api/feedback", extra).json(), {"saved": True})
        saved = [json.loads(line) for line in self.feedback.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(saved), 1)
        self.assertEqual(sorted(saved[0]), ["at", "id", "kind", "label", "status", "type"])
        self.assertEqual((saved[0]["status"], len(saved[0]["label"])), ("kept", 120))
        self.assertNotIn(SECRET_DRAFT, self.feedback.read_text(encoding="utf-8"))
        self.assertEqual(self.post("/api/feedback", dict(base, consent=True, status="wrong")).status_code, 422)


class Privacy(ServerCase):
    def run_everything(self):
        guide = text("samples", "guide-sample.md") + "\n" + SECRET_GUIDE
        request = dict(load("contracts", "check-request.example.json"))
        request["draft_text"] += "\n" + SECRET_DRAFT
        doc = self.post("/api/extract", {"guide": guide}).json()["conditions"]
        self.post("/api/check", {"conditions": doc, "request": request})
        self.post("/api/judge", {"conditions": doc, "request": request})
        self.post("/api/check", {"conditions": doc, "request": dict(request, input_mode="이상한 값")})      # 형식 오류
        self.post("/api/feedback", {"consent": True, "kind": "condition", "id": "c1", "label": "조건", "status": "missing"})
        with mock.patch.object(engine, "check", side_effect=RuntimeError(SECRET_DRAFT)):                   # 서버 안 오류
            crash = self.post("/api/check", {"conditions": doc, "request": request})
        self.assertEqual((crash.status_code, SECRET_DRAFT in crash.text), (500, False))
        self.client.get("/")

    def test_judge_fills_only_qualitative_conditions(self):
        """4단계: 정적 결과는 /api/check 그대로, 정성 조건만 AI 판단으로 바뀌어요."""
        doc, request = load("contracts", "conditions.example.json"), load("contracts", "check-request.example.json")
        static = self.post("/api/check", {"conditions": doc, "request": request}).json()
        r = self.post("/api/judge", {"conditions": doc, "request": request})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(server.shape_errors("check-result", r.json()), [])
        asked = {c["id"] for c in ai_judge.qualitative(doc)}
        self.assertTrue(asked)
        for before, after in zip(static["results"], r.json()["results"]):
            if before["condition_id"] in asked:
                self.assertEqual(after["status"], "kept")
                self.assertTrue(after["note"].startswith(ai_judge.AI_NOTE))
            else:
                self.assertEqual(after, before)
        self.assertEqual(r.json()["principles"], static["principles"])
        self.assertEqual(fake_judge.calls, 1)

    def test_judge_failure_keeps_static_and_says_try_later(self):
        doc, request = load("contracts", "conditions.example.json"), load("contracts", "check-request.example.json")
        for code in (ai_client.AI_TIMEOUT, ai_client.AI_5XX, ai_client.AI_4XX, ai_client.AI_TRUNCATED, ai_client.AI_NOT_JSON):
            def broken(req, code=code):
                raise ai_client.AIError(code, "실패") from ValueError(SECRET_DRAFT)
            with mock.patch.object(ai_judge, "call_llm", broken), captured() as logs:
                r = self.post("/api/judge", {"conditions": doc, "request": request})
            self.assertEqual(r.status_code, 502)
            self.assertIn(server.JUDGE_RETRY, r.json()["error"])
            self.assertIn(code, "\n".join(logs.output))
            self.assertNotIn(SECRET_DRAFT, "\n".join(logs.output) + r.text)

    def test_judge_is_not_called_for_bad_drafts(self):
        doc, request = load("contracts", "conditions.example.json"), load("contracts", "check-request.example.json")
        quotes = "\n".join(c["guide_quote"]["text"] for c in doc["conditions"])
        for draft in ("ㅋㅋㅋㅋㅋㅋ", "가" * 500, quotes, "녹차 " * (server.AI_MAX_DRAFT // 3 + 1)):
            r = self.post("/api/judge", {"conditions": doc, "request": dict(request, draft_text=draft)})
            self.assertIn(r.status_code, (413, 422), draft[:10])
            self.assertIn("정성 판단을 하지 않았어요", r.json()["error"])
        self.assertEqual(fake_judge.calls, 0)
        only_static = {"version": "0.4", "conditions": [c for c in doc["conditions"] if c["countable"]]}
        self.assertEqual(self.post("/api/judge", {"conditions": only_static, "request": request}).status_code, 200)
        self.assertEqual(fake_judge.calls, 0)                       # 정성 조건이 없으면 AI를 부르지 않아요

    def test_judge_shares_the_ai_limit(self):
        doc, request = load("contracts", "conditions.example.json"), load("contracts", "check-request.example.json")
        with mock.patch.object(server, "EXTRACT_PER_IP", 2):
            codes = [self.post("/api/judge", {"conditions": doc, "request": request}).status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])

    def test_guide_and_draft_never_reach_logs_or_files(self):
        records = []
        handler = logging.Handler()
        handler.emit = lambda record: records.append(record.getMessage() + " " + str(record.args) + " " + str(record.exc_info))
        root = logging.getLogger()
        root.addHandler(handler)
        old_level = root.level
        root.setLevel(logging.DEBUG)
        self.addCleanup(lambda: (root.removeHandler(handler), root.setLevel(old_level)))
        out, err = io.StringIO(), io.StringIO()
        before = {p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts}
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.run_everything()
        logged = "\n".join(records) + out.getvalue() + err.getvalue()
        self.assertIn('"kind": "RuntimeError"', out.getvalue())                    # 오류 종류는 남기고 (be/events.py, 표준 출력)
        for secret in (SECRET_GUIDE, SECRET_DRAFT, "전포동 카페", "모래알"):         # 글은 남기지 않아요
            self.assertNotIn(secret, logged)
        after = {p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts}
        self.assertEqual(after, before)                                             # 저장소 폴더에 새 파일 없음
        written = "".join(p.read_text(encoding="utf-8") for p in Path(self.tmp.name).rglob("*") if p.is_file())
        self.assertNotIn(SECRET_GUIDE, written)
        self.assertNotIn(SECRET_DRAFT, written)

    def test_no_outgoing_connections_when_ai_is_faked(self):
        """AI 자리를 빼면 서버가 밖으로 여는 연결이 하나도 없어요. (밖으로 나가는 곳은 ai.extract.call_llm 하나뿐)"""
        opened = []
        real_connect = socket.socket.connect

        def spy(sock, address):
            opened.append(address)
            return real_connect(sock, address)
        with mock.patch.object(socket.socket, "connect", spy), mock.patch.object(socket, "create_connection",
                                                                              side_effect=lambda *a, **k: opened.append(a)):
            self.run_everything()
        # 자기 컴퓨터 안(127.0.0.1)의 연결은 파이썬이 안에서 쓰는 것이라 빼고 봐요
        outside = [a for a in opened if not (isinstance(a, tuple) and a and a[0] in ("127.0.0.1", "::1", "localhost"))]
        self.assertEqual(outside, [])

    def test_crash_under_the_real_server_program_logs_no_text(self):
        """진짜 서버 프로그램(uvicorn)으로 띄워서 오류를 내도, 오류 문장(받은 글이 섞일 수 있음)이 로그에 안 찍혀요."""
        import urllib.error
        import urllib.request
        records = []
        handler = logging.Handler()
        handler.emit = lambda r: records.append(r.getMessage() + " " + str(r.exc_info) + " " + str(getattr(r, "exc_text", "")))
        loggers = [logging.getLogger(n) for n in ("", "uvicorn", "uvicorn.error", "uvicorn.access", "prompatch")]
        for lg in loggers:
            lg.addHandler(handler)
        self.addCleanup(lambda: [lg.removeHandler(handler) for lg in loggers])
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        live = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="debug"))
        thread = threading.Thread(target=live.run, daemon=True)
        err, out = io.StringIO(), io.StringIO()
        with mock.patch.object(engine, "check", side_effect=RuntimeError(SECRET_DRAFT)), contextlib.redirect_stderr(err), \
                contextlib.redirect_stdout(out):
            thread.start()
            try:
                for _ in range(100):
                    if live.started:
                        break
                    time.sleep(0.05)
                payload = json.dumps({"conditions": load("contracts", "conditions.example.json"),
                                      "request": load("contracts", "check-request.example.json")}).encode()
                req = urllib.request.Request(f"http://127.0.0.1:{port}/api/check", data=payload,
                                             headers={"Content-Type": "application/json"})
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(req, timeout=10)
                status, reply = caught.exception.code, caught.exception.read().decode("utf-8")
            finally:
                live.should_exit = True
                thread.join(timeout=10)
        logged = "\n".join(records) + err.getvalue() + out.getvalue()
        self.assertEqual(status, 500)
        self.assertIn("RuntimeError", logged)                      # 오류 종류는 남고
        for secret in (SECRET_DRAFT, "전포동 카페"):                 # 글은 응답에도 로그에도 없어요
            self.assertNotIn(secret, logged)
            self.assertNotIn(secret, reply)

    def test_limits_come_from_env_and_blank_means_default(self):
        with mock.patch.dict("os.environ", {"PP_N": "3", "PP_BLANK": "", "PP_BAD": "많이", "PP_ZERO": "0"}):
            self.assertEqual([server.env_number(n, 10) for n in ("PP_N", "PP_BLANK", "PP_BAD", "PP_ZERO", "PP_NONE")],
                             [3, 10, 10, 10, 10])
        source = text("be", "server.py")
        self.assertLess(source.index("recorded.load_env()"), source.index("EXTRACT_PER_IP = env_number"))

    def test_only_the_ai_module_talks_to_the_outside(self):
        for name in ("server.py", "engine.py", "phrases.py", "__main__.py"):
            source = text("be", name)
            for lib in ("import requests", "urllib.request", "import httpx", "http.client", "import socket", "aiohttp", "anthropic"):
                self.assertFalse(lib in source, f"be/{name}에 {lib}")
        self.assertEqual(text("ai", "client.py").count("anthropic.Anthropic("), 1)
        self.assertNotIn("anthropic.Anthropic(", text("ai", "extract.py"))

    def test_rules_only_extract_is_instant_and_does_not_call_ai(self):
        """나눠 보여 주기 1단계: ai가 false면 코드가 읽은 조건만 돌려주고 AI를 부르지 않아요."""
        guide = text("samples", "guide-sample-2.md")
        before = fake_llm.calls
        with mock.patch.object(ai_extract, "call_llm", fake_llm):
            r = self.post("/api/extract", {"guide": guide, "ai": False})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(fake_llm.calls, before)
        self.assertTrue(r.json()["conditions"]["conditions"])
        self.assertTrue(all(c.get("source") == "rule" for c in r.json()["conditions"]["conditions"]))
        self.assertEqual(r.json()["form"], "reviewplace")
        general = self.post("/api/extract", {"guide": guide, "ai": False, "form": "general"}).json()   # "바꾸기"에서 일반 가이드
        self.assertEqual((general["form"], general["conditions"]["conditions"]), (None, []))

    @needs_screen
    def test_pages_are_served_but_not_scripts_and_tests(self):
        for path, kind in (("/", "text/html"), ("/app.js", "text/javascript"), ("/style.css", "text/css"),
                           ("/api.js", "text/javascript"), ("/privacy.html", "text/html")):
            r = self.client.get(path)
            self.assertEqual((r.status_code, r.headers["content-type"].split(";")[0]), (200, kind), path)
            self.assertEqual(r.headers["x-content-type-options"], "nosniff")
        for path, kind in (("/fonts/Pretendard-Regular.subset.woff2", "font/woff2"), ("/favicon.svg", "image/svg+xml"),
                           ("/og-image.png", "image/png"), ("/fonts/OFL-Pretendard.txt", "text/plain")):
            r = self.client.get(path)
            self.assertEqual((r.status_code, r.headers["content-type"].split(";")[0]), (200, kind), path)
        for path in ("/test_fe.py", "/make_mock.py", "/selftest.js", "/../.env", "/.env", "/README.md", "/be/server.py", "/api/nothing"):
            self.assertEqual(self.client.get(path).status_code, 404, path)
        self.assertIn("max-age", self.client.get("/fonts/Pretendard-Bold.subset.woff2").headers["cache-control"])
        self.assertEqual(self.client.get("/").headers["cache-control"], "no-store")
        page = self.client.get("/없는-주소")                   # 화면 주소가 없으면 사람이 읽는 404 화면, /api/는 JSON
        self.assertEqual((page.status_code, page.headers["content-type"].split(";")[0]), (404, "text/html"))
        self.assertIn("없는 주소예요", page.text)
        self.assertEqual(self.client.get("/api/nothing").json(), {"error": "없는 주소예요."})
        self.assertEqual(self.client.get("/api/health").json(), {"ok": True})


@needs_server
class Browser(unittest.TestCase):
    """서버를 진짜로 띄우고(가짜 AI), 크롬에서 화면을 끝까지 눌러 봐요."""

    @needs_screen
    def test_screen_with_live_server(self):
        from fe.test_fe import find_chrome
        chrome = find_chrome()
        if not chrome:
            self.skipTest("크롬을 찾지 못했어요. CHROME 환경 변수에 경로를 넣으면 돌려요")
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp, \
                mock.patch.object(ai_extract, "call_llm", fake_llm), \
                mock.patch.object(ai_judge, "call_llm", fake_judge), \
                mock.patch.object(server, "FEEDBACK_FILE", Path(tmp) / "feedback.jsonl"), \
                mock.patch.object(server, "limiters", server.new_limiters()), \
                mock.patch.dict(server.STATIC, {"selftest.js": ("selftest.js", "text/javascript; charset=utf-8")}):
            with socket.socket() as s:
                s.bind(("127.0.0.1", 0))
                port = s.getsockname()[1]
            live = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="warning"))
            thread = threading.Thread(target=live.run, daemon=True)
            thread.start()
            try:
                for _ in range(100):
                    if live.started:
                        break
                    time.sleep(0.05)
                self.assertTrue(live.started, "서버가 뜨지 않았어요")
                done = subprocess.run(
                    [chrome, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={tmp}/chrome",
                     "--virtual-time-budget=20000", "--dump-dom", f"http://127.0.0.1:{port}/#selftest-server"],
                    capture_output=True, timeout=180)
                saved = (Path(tmp) / "feedback.jsonl").read_text(encoding="utf-8") if (Path(tmp) / "feedback.jsonl").exists() else ""
            finally:
                live.should_exit = True
                thread.join(timeout=10)
        dom = done.stdout.decode("utf-8", "replace")
        failed = [html.unescape(t) for good, t in re.findall(r'<li data-pass="(\w+)">(.*?)</li>', dom) if good != "true"]
        report = re.search(r'id="selftest"[^>]*>서버 자체 시험 (\d+)/(\d+) 통과<', dom)
        self.assertIsNotNone(report, "서버 자체 시험 결과가 화면에 나오지 않았어요")
        self.assertEqual(failed, [])
        self.assertGreaterEqual(int(report.group(2)), 16)                                      # 4단계 시험 7개 포함
        self.assertEqual([json.loads(line)["id"] for line in saved.splitlines()], ["c3"])    # 동의한 피드백 1건이 저장됨



class Events(ServerCase):
    """9단계: 서버 기록은 log_event 하나로, JSON 한 줄씩. 숫자·코드만 남고 글은 남지 않아요."""

    def test_log_event_writes_one_json_line_and_drops_text(self):
        with captured() as logs:
            events.log_event("check", check_ms=3, code="AI_TIMEOUT", note=SECRET_DRAFT, dropped={"SCHEMA_INVALID:length": 1},
                             nested={"a": {"b": 1}}, items=[1, 2], **{"한글키": 1})
        (line,) = logs.output
        record = json.loads(line)
        self.assertEqual((record["event"], record["check_ms"], record["code"]), ("check", 3, "AI_TIMEOUT"))
        self.assertEqual((record["note"], record["nested"], record["items"]), ("?", {"a": "?"}, "?"))
        self.assertEqual(record["dropped"], {"SCHEMA_INVALID:length": 1})
        self.assertNotIn("한글키", record)
        self.assertNotIn(SECRET_DRAFT, line)

    def test_check_records_time_counts_and_no_text(self):
        doc, request = load("contracts", "conditions.example.json"), load("contracts", "check-request.example.json")
        with captured() as logs:
            self.post("/api/check", {"conditions": doc, "request": dict(request, draft_text=SECRET_DRAFT + request["draft_text"])})
        (record,) = [e for e in logs.events if e["event"] == "check"]
        self.assertEqual(record["route"], "check")
        self.assertIsInstance(record["check_ms"], int)
        self.assertEqual(record["conditions"], len(doc["conditions"]))
        self.assertEqual(record["conditions_static"] + record["conditions_qualitative"] + record["conditions_outside"],
                         len(doc["conditions"]))
        self.assertNotIn("anomaly", record)
        self.assertNotIn(SECRET_DRAFT, "\n".join(logs.output))

    def test_timing_records_only_numbers(self):
        """화면이 잰 첫 결과·전체 결과까지 시간(2026-11-27). 숫자만 받고 숫자만 남겨요."""
        with captured() as logs:
            ok = self.post("/api/timing", {"first_ms": 820, "full_ms": 5400, "ai": "done"})
            failed = self.post("/api/timing", {"first_ms": 700, "full_ms": None, "ai": "failed"})
            for bad in ({"first_ms": SECRET_DRAFT, "full_ms": 1, "ai": "done"}, {"first_ms": 1, "full_ms": 1, "ai": SECRET_DRAFT},
                        {"first_ms": -1, "full_ms": 1, "ai": "done"}, {"first_ms": True, "full_ms": 1, "ai": "done"}):
                self.assertEqual(self.post("/api/timing", bad).status_code, 422)
        self.assertEqual((ok.status_code, failed.status_code), (200, 200))
        timing = [e for e in logs.events if e["event"] == "timing"]
        self.assertEqual([(e["first_ms"], e["full_ms"], e["ai"]) for e in timing], [(820, 5400, "done"), (700, None, "failed")])
        self.assertNotIn(SECRET_DRAFT, "\n".join(logs.output))

    def test_ai_calls_log_cost_in_won(self):
        from ai import client as ai_client
        usage = {"input_tokens": 1500, "output_tokens": 1000, "cache_read_input_tokens": 4000, "cache_creation_input_tokens": 0}
        with mock.patch.dict(os.environ, {ai_client.KRW_ENV: "1400"}):
            won = ai_client.cost_krw(usage, "claude-haiku-5-5")
            self.assertEqual(won, round((1500 * 0.10 + 1000 * 0.50 + 4000 * 0.01) / 1e6 * 1400, 3))
            self.assertIsNone(ai_client.cost_krw(usage, "모르는-모델"))
            self.assertEqual(server.tokens(usage)["cost_krw"], won)

    def test_zero_conditions_is_flagged(self):
        request = load("contracts", "check-request.example.json")
        with captured() as logs:
            self.post("/api/check", {"conditions": {"version": "0.4", "platform": None, "campaign_type": None, "conditions": []},
                                     "request": request})
        (record,) = [e for e in logs.events if e["event"] == "check"]
        self.assertEqual((record["conditions"], record["anomaly"]), (0, "NO_CONDITIONS"))

    def test_ai_calls_record_time_tokens_and_cache_reads(self):
        with captured() as logs:
            self.post("/api/extract", {"guide": text("samples", "guide-sample-2.md")})
        (record,) = [e for e in logs.events if e["event"] == "extract"]
        self.assertIsInstance(record["ai_ms"], int)
        for key in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "conditions_static",
                    "conditions_qualitative", "dropped"):
            self.assertIn(key, record)

    def test_output_place_is_decided_in_one_function(self):
        source = (Path(server.__file__).parent / "events.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("sys.stdout.write("), 1)
        self.assertIn("def _write(", source)
        for name in ("server.py", "engine.py"):
            code = (Path(server.__file__).parent / name).read_text(encoding="utf-8")
            self.assertNotIn("print(", code)
            self.assertNotIn("logging.getLogger", code)


class ManyPosts(ServerCase):
    def test_two_posts_in_one_paste_are_refused_before_checking(self):
        doc, request = load("contracts", "conditions.example.json"), load("contracts", "check-request.example.json")
        two = "첫 글\n프로파일\n가나다 ・ 2026. 1. 2. 10:00\n본문\n\n둘째 글\n프로파일\n가나다 ・ 2026. 1. 3. 10:00\n본문"
        for path in ("/api/check", "/api/judge"):
            r = self.post(path, {"conditions": doc, "request": dict(request, draft_text=two)})
            self.assertEqual((r.status_code, r.json()["error"]), (422, server.MANY_POSTS))
        one = self.post("/api/check", {"conditions": doc, "request": dict(request, draft_text=two.split("\n\n")[0])})
        self.assertEqual(one.status_code, 200)


if __name__ == "__main__":
    unittest.main()
