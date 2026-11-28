"""저장된 응답 모드(PROMPATCH_AI_MODE=recorded) 서버 시험. 실행: python -m unittest be.test_recorded

ai/ 코드와 API 키 없이 돌아요. 지어낸 예시 가이드 4개(samples/)와 조건 목록 예시(contracts/)만 써요.
fastapi가 없으면 서버 시험은 건너뛰어요 (pip install -r be/requirements.txt).
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from be import recorded

ROOT = Path(__file__).resolve().parent.parent
try:
    from fastapi.testclient import TestClient
    from be import server
except ImportError:                     # 서버 패키지를 설치하지 않은 컴퓨터: 서버 시험만 건너뛰어요
    server = None


def load(*parts) -> dict:
    return json.loads(ROOT.joinpath(*parts).read_text(encoding="utf-8"))


class Examples(unittest.TestCase):
    def test_each_example_guide_gives_its_conditions_and_quotes_point_into_the_guide(self):
        for guide_file, doc_file in recorded.EXAMPLES:
            guide = (ROOT / "samples" / guide_file).read_text(encoding="utf-8")
            doc = recorded.conditions(guide)
            self.assertEqual(doc, load("contracts", doc_file), guide_file)
            for c in doc["conditions"]:
                for q in [c["guide_quote"], *c.get("extra_quotes", [])]:
                    self.assertEqual(guide[q["start"]:q["end"]], q["text"], f'{guide_file} {c["id"]}')

    def test_line_endings_and_trailing_spaces_do_not_matter_but_other_text_does(self):
        guide = (ROOT / "samples" / "guide-sample.md").read_text(encoding="utf-8")
        self.assertIsNotNone(recorded.conditions("\n" + guide.replace("\n", "  \r\n")))
        self.assertIsNone(recorded.conditions(guide + "\n한 줄 더"))

    def test_mode(self):
        with mock.patch.dict(os.environ, {recorded.ENV: ""}):
            self.assertTrue(recorded.active(ai_ready=False))          # ai/ 코드가 없으면 늘 저장된 응답
            self.assertFalse(recorded.active(ai_ready=True))
        with mock.patch.dict(os.environ, {recorded.ENV: "recorded"}):
            self.assertTrue(recorded.active(ai_ready=True))

    def test_mode_can_be_set_in_the_env_file_only(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ):
            os.environ.pop(recorded.ENV, None)
            env = Path(tmp) / ".env"
            env.write_text("# 주석\nPROMPATCH_AI_MODE=recorded\n", encoding="utf-8")
            recorded.load_env(env)
            self.assertTrue(recorded.active(ai_ready=True))


@unittest.skipIf(server is None, "fastapi가 없어요 (pip install -r be/requirements.txt)")
class RecordedServer(unittest.TestCase):
    def setUp(self):
        server.limiters = server.new_limiters()
        self.env = mock.patch.dict(os.environ, {recorded.ENV: "recorded"})
        self.env.start()
        self.client = TestClient(server.app)

    def tearDown(self):
        self.env.stop()

    def post(self, path, body):
        return self.client.post(path, json=body)

    def test_guide_to_result_without_ai(self):
        guide = (ROOT / "samples" / "guide-sample.md").read_text(encoding="utf-8")
        with mock.patch.object(server, "_in_thread", side_effect=AssertionError("AI를 부르면 안 돼요")):
            got = self.post("/api/extract", {"guide": guide})
            self.assertEqual(got.status_code, 200)
            doc = got.json()["conditions"]
            self.assertEqual(doc, load("contracts", "conditions.example.json"))
            result = self.post("/api/check", {"conditions": doc, "request": load("contracts", "check-request.example.json")})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["summary"], {"kept": 1, "missing": 4, "hold": 3})      # 정답지 예시의 요약
            judged = self.post("/api/judge", {"conditions": doc, "request": load("contracts", "check-request.example.json")})
            self.assertEqual(judged.json(), result.json())                                       # AI 없이 코드로 센 결과

    def test_platform_form_comes_from_the_example(self):
        guide = (ROOT / "samples" / "guide-sample-2.md").read_text(encoding="utf-8")
        self.assertEqual(self.post("/api/extract", {"guide": guide}).json()["form"], "reviewplace")

    def test_unknown_guide_is_refused_without_echoing_it(self):
        secret = "아무도 모르는 가이드 문장이에요 비밀7731"
        got = self.post("/api/extract", {"guide": secret})
        self.assertEqual(got.status_code, 422)
        self.assertNotIn("비밀7731", got.text)
        self.assertIn("예시 가이드", got.json()["error"])

    def test_pages_that_do_not_exist_yet_are_404_not_a_crash(self):
        self.assertEqual(self.client.get("/api/nothing").status_code, 404)
        self.assertEqual(self.client.get("/no-such-page").status_code, 404)
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200 if (ROOT / "fe" / "index.html").exists() else 404)


if __name__ == "__main__":
    unittest.main()
