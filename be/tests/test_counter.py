"""criteria/sample-answer-key.md의 숫자 정답과 같은지 고정하는 테스트예요.

실행 (저장소 맨 위 폴더에서):
    py -m unittest discover -s be/tests -v
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "be"))
from counter import check, count_length, find_keyword  # noqa: E402

REQUEST = json.loads((ROOT / "contracts/check-request.example.json").read_text(encoding="utf-8"))
CONDITIONS = json.loads((ROOT / "contracts/conditions.example.json").read_text(encoding="utf-8"))
DRAFT = (ROOT / "samples/draft-sample.md").read_text(encoding="utf-8")

# 정답지 "숫자 정답 (BE 비교용)" 표를 옮긴 것
ANSWER = {
    "c1": {"status": "missing", "actual": 3, "expected": 5, "starts": [33, 478, 578]},
    "c2": {"status": "missing", "actual": 414, "expected": 450, "starts": []},
    "c3": {"status": "missing", "actual": 8, "expected": 10, "starts": []},
    "c4": {"status": "kept", "starts": [0]},
    "c5": {"status": "missing", "starts": []},
    "c6": {"status": "hold", "starts": []},
    "c7": {"status": "hold", "starts": []},
    "c8": {"status": "hold", "starts": []},
}


class TestAnswerKey(unittest.TestCase):
    def setUp(self):
        self.result = check(REQUEST, CONDITIONS)
        self.by_id = {r["condition_id"]: r for r in self.result["results"]}

    def test_request_draft_is_sample_file(self):
        self.assertEqual(REQUEST["draft_text"], DRAFT)

    def test_summary(self):
        self.assertEqual(self.result["summary"], {"kept": 1, "missing": 4, "hold": 3})

    def test_each_condition(self):
        for cid, ans in ANSWER.items():
            with self.subTest(condition=cid):
                r = self.by_id[cid]
                self.assertEqual(r["status"], ans["status"])
                for key in ("actual", "expected"):
                    if key in ans:
                        self.assertEqual(r[key], ans[key])
                self.assertEqual([s["start"] for s in r["draft_spans"]], ans["starts"])

    def test_spans_point_to_text(self):
        for r in self.result["results"]:
            for s in r["draft_spans"]:
                self.assertLess(s["start"], s["end"])
                self.assertLessEqual(s["end"], len(DRAFT))
        c1 = self.by_id["c1"]["draft_spans"]
        self.assertTrue(all(DRAFT[s["start"]:s["end"]] == "전포동 카페" for s in c1))

    def test_length_both_ways(self):
        # 정답지 메모: 공백 제외 414자, 공백 포함 564자
        self.assertEqual(count_length(DRAFT), {"without_spaces": 414, "with_spaces": 564})


class TestEdgeCases(unittest.TestCase):
    def test_keyword_no_overlap(self):
        self.assertEqual(find_keyword("aaaa", "aa"), [(0, 2), (2, 4)])

    def test_keyword_spacing_differs(self):
        # 띄어쓰기가 다르면 세지 않아요 (정확히 같은 문자열만)
        self.assertEqual(find_keyword("전포동카페 전포동  카페", "전포동 카페"), [])

    def test_missing_inputs_are_hold(self):
        req = dict(REQUEST, photo_count=None, has_map=None)
        by_id = {r["condition_id"]: r for r in check(req, CONDITIONS)["results"]}
        self.assertEqual(by_id["c3"]["status"], "hold")
        self.assertEqual(by_id["c5"]["status"], "hold")

    def test_disclosure_after_third_line_is_missing(self):
        req = dict(REQUEST, draft_text="첫 줄\n둘째 줄\n셋째 줄\n업체로부터 음료를 제공받아 작성한 글입니다")
        by_id = {r["condition_id"]: r for r in check(req, CONDITIONS)["results"]}
        self.assertEqual(by_id["c4"]["status"], "missing")


if __name__ == "__main__":
    unittest.main()
