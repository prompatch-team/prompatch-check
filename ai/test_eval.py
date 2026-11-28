"""정확도 재기 도구(ai/eval.py) 시험. 실행: python -m unittest ai.test_eval

실제 자료는 쓰지 않아요. 지어낸 가이드(samples/guide-sample-2.md)와 조건 목록 예시로 임시 비공개 폴더를 만들어요.
AI를 부르지 않아요 (client.call을 가짜로 바꿔요).
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ai import client
from ai import eval as ev
from ai.test_extract import as_llm_output

ROOT = Path(__file__).resolve().parent.parent
GUIDE = (ROOT / "samples" / "guide-sample-2.md").read_text(encoding="utf-8")
EXAMPLE = json.loads((ROOT / "contracts" / "conditions.example-2.json").read_text(encoding="utf-8"))
ANSWER = as_llm_output(EXAMPLE)


class Eval(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        (self.base / "guides").mkdir()
        (self.base / "answer-keys").mkdir()
        (self.base / "guides" / "G1.txt").write_text(GUIDE, encoding="utf-8")
        types = {c["type"] for c in EXAMPLE["conditions"]}
        missing = next(t for t in ("map", "video_count", "banned_terms", "link") if t not in types)
        spec = {"outside_heads": {}, "guides": {"G1": {"file": "G1.txt", "form": "reviewplace", "items": [
            {"id": "i1", "kind": "제목 키워드", "class": "must", "type": "title_keyword"},
            {"id": "i2", "kind": "없어야 할 조건", "class": "absent", "type": missing}]}}}
        (self.base / "answer-keys" / "scoring.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        self.env = mock.patch.dict(os.environ, {ev.ENV: str(self.base)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def run_main(self, *args) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ev.main(list(args))
        return code, out.getvalue()

    def assert_no_guide_text(self, said: str):
        """화면에는 숫자만: 가이드 인용·키워드가 나오면 안 돼요."""
        for c in EXAMPLE["conditions"]:
            self.assertNotIn(c["guide_quote"]["text"], said)
            for k in c["params"].get("keywords") or []:
                self.assertNotIn(k, said)

    def test_without_private_data_it_says_so_and_stops(self):
        with mock.patch.dict(os.environ, {ev.ENV: str(self.base / "없는 폴더")}):
            code, said = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("비공개 자료가 없어요", said)

    def test_rescore_saved_answers_without_calling_ai(self):
        (self.base / "responses" / "묶음1").mkdir(parents=True)
        for i in (1, 2):
            (self.base / "responses" / "묶음1" / f"G1-{i}.json").write_text(json.dumps({"response": ANSWER}, ensure_ascii=False),
                                                                           encoding="utf-8")
        with mock.patch.object(client, "call", side_effect=AssertionError("AI를 부르면 안 돼요")):
            code, said = self.run_main()
        self.assertEqual(code, 0)
        n = len(EXAMPLE["conditions"])
        used = sum(c["type"] == "title_keyword" for c in EXAMPLE["conditions"])
        outside = sum(c["type"] == "outside_draft" for c in EXAMPLE["conditions"])
        self.assertIn(f"| G1 | 2 | 4/4 | 100% | {2 * (n - used - outside)} |", said)
        self.assert_no_guide_text(said)

    def test_live_calls_stop_at_the_cap_and_save_only_in_the_private_folder(self):
        with mock.patch.object(client, "call", return_value=(ANSWER, {"input_tokens": 1, "output_tokens": 1})) as call:
            code, said = self.run_main("--max-calls", "2", "--repeat", "5")
        self.assertEqual((code, call.call_count), (0, 2))
        (folder,) = list((self.base / "results").glob("eval-*"))
        self.assertEqual(len(list(folder.glob("G1-*.json"))), 2)
        self.assertIn("호출 2번 (상한 2번)", said)
        self.assert_no_guide_text(said)

    def test_failed_calls_count_toward_the_cap(self):
        with mock.patch.object(client, "call", side_effect=client.AIError(client.AI_TIMEOUT, "시간 초과")) as call:
            code, said = self.run_main("--max-calls", "3", "--repeat", "9")
        self.assertEqual(call.call_count, 3)
        self.assertIn("호출 3번 (상한 3번)", said)

    def test_cap_never_goes_over_the_hard_limit(self):
        with mock.patch.object(client, "call", return_value=(ANSWER, {})) as call, mock.patch.object(ev, "LIMIT", 2):
            self.run_main("--max-calls", "50", "--repeat", "50")
        self.assertEqual(call.call_count, 2)


if __name__ == "__main__":
    unittest.main()
