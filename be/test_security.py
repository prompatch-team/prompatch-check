"""서버 보안 테스트. 실행: python -m unittest be.test_security

.claude/claude-security-guidance.md의 규칙을 하나씩 확인해요. AI API를 부르지 않아요.
"""
import json
import logging
import time
import unittest
from unittest import mock

from ai import extract as ai_extract
from be.test_server import ANY_GUIDE, SECRET_DRAFT, SECRET_GUIDE, ServerCase, fake_llm, load, needs_screen, server

# 진짜 키가 아니에요. 새는지 보려는 표시예요. 저장소에 키 모양 글자가 한 줄로 남지 않게 실행할 때 이어 붙여요.
FAKE_KEY = "sk-" + "ant-" + "test-0000-FAKE-KEY-FOR-TESTS-0000"
JSON = {"content-type": "application/json"}


def cond(kind: str, params: dict, cid: str = "c1") -> dict:
    return {"id": cid, "type": kind, "label": "조건", "countable": True, "params": params,
            "guide_quote": {"text": "가이드", "start": 0, "end": 3}}


class ForwardedHeader(ServerCase):
    """규칙 6: IP별 한도는 X-Forwarded-For를 그대로 믿지 않아요."""

    def codes(self, headers_list):
        return [self.post("/api/extract", {"guide": ANY_GUIDE}, headers=h).status_code for h in headers_list]

    def test_header_is_ignored_by_default(self):
        """기본값에서는 헤더를 보지 않아요. 요청마다 다른 주소를 적어 보내도 한도를 피하지 못해요."""
        with mock.patch.object(server, "EXTRACT_PER_IP", 2):
            got = self.codes([{"x-forwarded-for": f"198.51.100.{i}"} for i in range(4)])
        self.assertEqual((got, fake_llm.calls), ([200, 200, 429, 429], 2))

    def test_trusted_proxy_value_is_read_from_the_right(self):
        """믿는 프록시가 1개면 맨 뒤 값(프록시가 붙인 것)만 읽어요. 앞쪽에 지어낸 값을 넣어도 소용없어요."""
        with mock.patch.object(server, "EXTRACT_PER_IP", 2), mock.patch.object(server, "PROXY_HOPS", 1):
            spoofed = self.codes([{"x-forwarded-for": f"198.51.100.{i}, 203.0.113.5"} for i in range(3)])
            other = self.codes([{"x-forwarded-for": "198.51.100.1, 203.0.113.6"}])
            no_header = self.codes([{}])           # 헤더가 없으면 실제로 연결한 주소를 써요
        self.assertEqual((spoofed, other, no_header), ([200, 200, 429], [200], [200]))

    def test_two_proxies(self):
        with mock.patch.object(server, "EXTRACT_PER_IP", 1), mock.patch.object(server, "PROXY_HOPS", 2):
            got = self.codes([{"x-forwarded-for": "spoofed-a, 203.0.113.5, 10.0.0.1"},
                              {"x-forwarded-for": "spoofed-b, 203.0.113.5, 10.0.0.2"},
                              {"x-forwarded-for": "203.0.113.9, 10.0.0.1"}])
        self.assertEqual(got, [200, 429, 200])


class InputLimits(ServerCase):
    """규칙 7: 길이 한도는 AI를 부르기 전에, 본문을 다 읽기 전에 확인해요."""

    def test_long_guide_is_refused_before_ai_and_does_not_use_up_the_limit(self):
        with mock.patch.object(server, "EXTRACT_PER_IP", 1):
            long = [self.post("/api/extract", {"guide": "가" * (server.MAX_GUIDE + 1)}).status_code for _ in range(3)]
            self.assertEqual((long, fake_llm.calls), ([413, 413, 413], 0))
            ok = self.post("/api/extract", {"guide": ("가나다라마바사아자차 " * server.MAX_GUIDE)[:server.MAX_GUIDE]})          # 딱 한도까지는 받아요
            self.assertEqual((ok.status_code, fake_llm.calls), (200, 1))

    def test_body_without_a_length_header_is_cut_off(self):
        def endless():
            for _ in range(server.MAX_BODY // 1000 + 50):
                yield b"x" * 1000
        r = self.client.post("/api/check", content=endless(), headers=JSON)
        self.assertEqual(r.status_code, 413)

    def test_only_json_requests_are_accepted(self):
        """다른 사이트의 화면이 방문자 몰래 부를 수 있는 형식(글, 폼)은 받지 않아요."""
        payload = json.dumps({"guide": ANY_GUIDE})
        plain = self.client.post("/api/extract", content=payload, headers={"content-type": "text/plain"})
        form = self.client.post("/api/extract", data={"guide": ANY_GUIDE})
        none = self.client.post("/api/extract", content=payload)
        self.assertEqual([r.status_code for r in (plain, form, none)], [415, 415, 415])
        self.assertEqual(fake_llm.calls, 0)
        ok = self.client.post("/api/extract", content=payload, headers={"content-type": "application/json; charset=utf-8"})
        self.assertEqual(ok.status_code, 200)

    def test_no_cross_site_permission_is_given(self):
        r = self.client.options("/api/extract", headers={"origin": "https://example.invalid",
                                                         "access-control-request-method": "POST"})
        self.assertNotIn("access-control-allow-origin", {k.lower() for k in r.headers})
        r = self.post("/api/extract", {"guide": ANY_GUIDE}, headers={"origin": "https://example.invalid"})
        self.assertNotIn("access-control-allow-origin", {k.lower() for k in r.headers})

    def test_oversized_condition_lists_are_refused(self):
        request = load("contracts", "check-request.example.json")

        def check(conds):
            return self.post("/api/check", {"conditions": {"version": "0.3", "conditions": conds}, "request": request}).status_code
        many = ["키워드%d" % i for i in range(server.MAX_ITEMS + 1)]
        self.assertEqual(check([cond("keyword_count", {"keywords": many, "min": 1})]), 413)
        self.assertEqual(check([cond("keyword_count", {"keywords": ["가" * (server.MAX_ITEM_CHARS + 1)], "min": 1})]), 413)
        spread = [cond("keyword_count", {"keywords": many[:50], "min": 1}, f"c{i}") for i in range(9)]     # 9 × 50 > 400
        self.assertEqual(check(spread), 413)
        self.assertEqual(check([cond("judgment", {"question": "가"}, f"c{i}") for i in range(server.MAX_CONDITIONS + 1)]), 413)
        self.assertEqual(check([cond("keyword_count", {"keywords": [{"안": "쪽"}], "min": 1})]), 422)
        self.assertEqual(check([cond("keyword_count", {"keywords": many[:50], "min": 1})]), 200)

    def test_largest_allowed_check_finishes_quickly(self):
        """한도까지 꽉 채운 원고와 조건으로도 금방 끝나요 (큰 입력으로 서버를 붙잡지 못해요)."""
        request = dict(load("contracts", "check-request.example.json"))
        request["draft_text"] = ("가나 다. " * 12000)[:server.MAX_DRAFT]
        words = ["가", "나", "다", "가나", "나 다", "다. 가", "가나 다", "."]
        conds = [cond("keyword_count", {"keywords": (words * 7)[:50], "min": 1, "pick": "each", "scope": "body"}, f"c{i}")
                 for i in range(8)]
        started = time.time()
        payload = json.dumps({"conditions": {"version": "0.3", "conditions": conds}, "request": request}, ensure_ascii=False)
        r = self.client.post("/api/check", content=payload.encode("utf-8"), headers=JSON)     # 브라우저처럼 UTF-8로 보내요
        took = time.time() - started
        self.assertEqual(r.status_code, 200)
        self.assertLess(took, 20, f"{took:.1f}초 걸렸어요")
        self.assertLess(len(r.content), 1_500_000)      # 응답도 한없이 커지지 않아요 (위치는 항목마다 200곳까지)

    def test_feedback_is_limited_and_the_file_cannot_grow_forever(self):
        base = {"consent": True, "kind": "condition", "id": "c1", "label": "조건", "status": "kept"}
        codes = [self.post("/api/feedback", base).status_code for _ in range(22)]
        self.assertEqual((codes[:20], codes[20:]), ([200] * 20, [429, 429]))
        with mock.patch.dict(server.limiters, server.new_limiters()), mock.patch.object(server, "MAX_FEEDBACK_BYTES", 10):
            self.assertEqual(self.post("/api/feedback", base).status_code, 503)
        self.assertEqual(len(self.feedback.read_text(encoding="utf-8").splitlines()), 20)


class Retention(ServerCase):
    def test_feedback_older_than_six_months_is_removed(self):
        """처리방침에 적은 대로, "판정이 틀렸어요" 기록은 6개월이 지나면 지워요."""
        base = {"consent": True, "kind": "condition", "id": "c1", "label": "조건", "status": "kept"}
        self.feedback.parent.mkdir(parents=True, exist_ok=True)
        old = {"at": "2020-01-01T00:00:00Z", "kind": "condition", "id": "old", "type": "", "label": "옛 기록", "status": "kept"}
        recent_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 30 * 86400))
        recent = dict(old, at=recent_at, id="recent")
        self.feedback.write_text(json.dumps(old, ensure_ascii=False) + "\n" + json.dumps(recent, ensure_ascii=False) + "\n",
                                 encoding="utf-8")
        self.assertEqual(self.post("/api/feedback", base).status_code, 200)
        ids = [json.loads(line)["id"] for line in self.feedback.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(ids, ["recent", "c1"])
        self.assertEqual(server.FEEDBACK_KEEP_DAYS, 183)


class Secrets(ServerCase):
    """규칙 5: API 키는 코드·로그·응답에 나오면 안 돼요."""

    def test_api_key_never_appears_in_responses_or_logs(self):
        records = []
        handler = logging.Handler()
        handler.emit = lambda r: records.append(r.getMessage() + " " + str(r.exc_info))
        root = logging.getLogger()
        root.addHandler(handler)
        old = root.level
        root.setLevel(logging.DEBUG)
        self.addCleanup(lambda: (root.removeHandler(handler), root.setLevel(old)))

        def broken(guide):       # AI API가 키를 섞은 오류 문장을 돌려준 것처럼
            raise ai_extract.ExtractError(f"AI API가 오류를 돌려줬어요: {FAKE_KEY}") from RuntimeError(FAKE_KEY)

        replies = []
        with mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": FAKE_KEY}):
            with mock.patch.object(ai_extract, "call_llm", broken):
                replies.append(self.post("/api/extract", {"guide": ANY_GUIDE}))
            replies.append(self.post("/api/extract", {"guide": ANY_GUIDE}))
            replies.append(self.post("/api/check", {"conditions": {}, "request": {}}))
            replies.append(self.client.get("/api/health"))
            for path in ("/.env", "/..%2f.env", "/%2e%2e/.env", "/.env.example", "/be/server.py", "/.git/config"):
                replies.append(self.client.get(path))
        self.assertEqual(replies[0].status_code, 502)
        self.assertTrue(all(r.status_code == 404 for r in replies[4:]))
        for r in replies:
            self.assertNotIn(FAKE_KEY, r.text)
            self.assertNotIn("sk-ant-", r.text)
        self.assertNotIn(FAKE_KEY, "\n".join(records))

    def test_no_key_shaped_text_in_tracked_files(self):
        import re
        import subprocess
        files = subprocess.run(["git", "ls-files"], cwd=server.ROOT, capture_output=True, text=True, encoding="utf-8").stdout.split("\n")
        self.assertNotIn(".env", files)
        hits = []
        for name in filter(None, files):
            path = server.ROOT / name
            if path.suffix in (".png", ".jpg"):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"sk-ant-[A-Za-z0-9_-]{8,}", text):
                hits.append(name)
        self.assertEqual(hits, [])

    def test_code_reads_env_only_in_known_places(self):
        """환경 변수를 읽는 곳은 정해져 있고, 읽은 값을 내보내는 코드가 없어요."""
        for name in ("be/server.py", "ai/extract.py", "ai/__main__.py", "be/engine.py", "be/__main__.py"):
            source = (server.ROOT / name).read_text(encoding="utf-8")
            self.assertFalse("ANTHROPIC_API_KEY" in source.replace(".env의 ANTHROPIC_API_KEY", ""), name)
            self.assertFalse("api_key=" in source, name)          # 키를 코드에서 직접 넘기지 않아요 (SDK가 환경에서 읽어요)
            self.assertFalse("os.environ)" in source or "dict(os.environ" in source, name)


class Headers(ServerCase):
    @needs_screen
    def test_pages_cannot_be_framed_and_types_are_not_guessed(self):
        for path in ("/", "/privacy.html", "/app.js", "/api/health"):
            h = self.client.get(path).headers
            self.assertEqual((h["x-frame-options"], h["x-content-type-options"]), ("DENY", "nosniff"), path)
            self.assertIn("frame-ancestors 'none'", h["content-security-policy"])
        page = self.client.get("/").text
        self.assertIn("default-src 'none'", page)
        self.assertIn("connect-src 'self'", page)

    @needs_screen
    def test_errors_do_not_echo_what_was_sent(self):
        marker = "<script>alert(1)</script>" + SECRET_DRAFT + SECRET_GUIDE
        request = dict(load("contracts", "check-request.example.json"), input_mode=marker)
        replies = [
            self.post("/api/check", {"conditions": load("contracts", "conditions.example.json"), "request": request}),
            self.post("/api/check", {"conditions": {marker: 1}, "request": {marker: 2}}),
            self.post("/api/feedback", {"consent": True, "kind": marker, "status": marker}),
            self.client.post("/api/extract", content=marker.encode(), headers=JSON),
            self.client.get("/" + marker),
        ]
        for i, r in enumerate(replies):
            self.assertGreaterEqual(r.status_code, 400)
            # 화면 주소가 없으면 고정된 404 화면(fe/404.html)이에요. 보낸 주소를 되돌려 쓰지 않아요
            kind = "text/html" if i == len(replies) - 1 else "application/json"
            self.assertEqual(r.headers["content-type"].split(";")[0], kind)
            for piece in ("<script>", SECRET_DRAFT, SECRET_GUIDE):
                self.assertNotIn(piece, r.text)


if __name__ == "__main__":
    unittest.main()
