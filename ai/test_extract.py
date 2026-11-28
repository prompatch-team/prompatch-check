"""조건 추출 테스트. 실행: python -m unittest ai.test_extract

AI API를 부르지 않아요. LLM 응답 자리에 가짜 응답을 넣어서, 코드가 하는 일(인용 확인, 위치 계산, 형식 맞추기)만 확인해요.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ai import compare as cmp
from ai import extract as ex
from ai.prompt import OUTPUT_SCHEMA, TYPES

ROOT = Path(__file__).resolve().parent.parent
BLANK = {
    "keywords": [], "tags": [], "terms": [], "forbidden": [], "min": 0, "pick": "", "scope": "",
    "count_spaces": "unspecified", "position": "", "url": "", "phrase": "", "allowed": "", "after": "",
    "category": "", "subject": "", "what": "", "question": "",
}


def never_call(guide):
    raise AssertionError("테스트가 진짜 AI API를 부르려고 했어요")


def setUpModule():
    """실수로라도 진짜 API가 불리지 않게 막아요."""
    patcher = mock.patch.object(ex, "call_llm", never_call)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


def said(kind: str, quote: str, label: str = "조건", **fields) -> dict:
    """LLM이 낸 조건 하나 (가짜)."""
    return {"type": kind, "label": label, "quote": quote, **BLANK, **fields}


def fake(conditions: list, campaign_type: str = "모름"):
    """가짜 LLM. 몇 번 불렸는지 세요."""
    def llm(guide):
        llm.calls += 1
        return {"campaign_type": campaign_type, "conditions": conditions}
    llm.calls = 0
    return llm


def notices(doc: dict) -> list[dict]:
    """확인하지 못해 "직접 봐 주세요" 안내로 남긴 조건."""
    return [c for c in doc["conditions"] if c["params"].get("unverified")]


def checked(doc: dict) -> list[dict]:
    """코드가 확인한 조건 (안내로 남긴 것은 빼고)."""
    return [c for c in doc["conditions"] if not c["params"].get("unverified")]


def as_llm_output(example: dict) -> dict:
    """contracts 예시를 LLM 응답 모양으로 바꿔요. 위치와 countable은 빼요(코드가 다시 계산해야 하니까)."""
    out = []
    for c in example["conditions"]:
        p = c["params"]
        rc = said(c["type"], c["guide_quote"]["text"], c["label"])
        for key in ("keywords", "tags", "terms", "forbidden", "min", "pick", "scope", "url", "phrase", "allowed",
                    "after", "category", "subject", "what", "question", "position"):
            if p.get(key) is not None:
                rc[key] = p[key]
        if "count_spaces" in p:
            rc["count_spaces"] = {True: "yes", False: "no", None: "unspecified"}[p["count_spaces"]]
        out.append(rc)
    return {"campaign_type": example.get("campaign_type") or "모름", "conditions": out}


def example_4_raw() -> dict:
    """예시 4(샘플 05 가이드)를 만들 때 쓰는 가짜 AI 응답.

    고정 칸의 조건은 하나도 내지 않았고(코드가 읽어요), 조건이 아닌 경고 줄을 숫자 없는 글자 수 조건으로 잘못 냈어요.
    fe/make_mock.py도 이걸로 예시 화면의 예시 4를 만들어요.
    """
    return {"campaign_type": "체험", "conditions": [
        said("banned_terms", "1. 질병 이름은 직접 언급하지 말아주세요.", "질병 이름 직접 언급 금지", category="질병 이름", scope="title_and_body"),
        said("banned_terms", "2. '다이어트', '감량' 단어는 사용하지 말아주세요.", "다이어트·감량 단어 금지", terms=["다이어트", "감량"],
             scope="title_and_body"),
        said("required_phrase", '3. 원료를 소개하는 문장 아래에는 "*제품이 아닌 원료에 관한 설명입니다" 문구를 넣어주세요.',
             "원료 설명 아래 안내 문구", phrase="*제품이 아닌 원료에 관한 설명입니다", after="원료를 소개하는 문장", scope="body"),
        said("hashtag", "4. 필수 해시태그 #새벽곡물 #아침선식 을 모두 넣어주세요.", "필수 해시태그 #새벽곡물 #아침선식",
             tags=["#새벽곡물", "#아침선식"], pick="each"),
        said("photo_count", "5. 물이나 우유에 타는 모습을 사진으로 1장 이상 넣어주세요.", "물이나 우유에 타는 모습 사진 1장 이상",
             min=1, subject="물이나 우유에 타는 모습"),
        said("length", "미션이 지켜지지 않을 경우 제공된 제품 및 포인트의 환수 혹은 미지급 처리가 될 수 있습니다", "글자 수"),
    ]}


def sample(guide_file: str, example_file: str):
    guide = (ROOT / "samples" / guide_file).read_text(encoding="utf-8")
    example = json.loads((ROOT / "contracts" / example_file).read_text(encoding="utf-8"))
    return guide, example


def without_id(conditions: list) -> list:
    return [{k: v for k, v in c.items() if k != "id"} for c in conditions]


GUIDE = (
    "🍵 솔바람 찻집 체험단 안내\n"
    "1. 본문에 \"솔바람 찻집\"을 3회 이상 넣어 주세요.\n"
    "2. 사진은 12장 이상 올려 주세요.\n"
    "3. '특효' 단어는 쓰지 말아 주세요.\n"
    "4. 창가 자리  사진을   꼭 넣어 주세요.\n"
)


class Samples(unittest.TestCase):
    """LLM이 예시와 같은 내용을 냈을 때, 코드가 위치를 계산해 contracts 예시와 같은 조건 목록을 만드는지."""

    def check(self, guide_file, example_file, same_ids):
        guide, example = sample(guide_file, example_file)
        doc, dropped = ex.extract(guide, llm=lambda g: as_llm_output(example), guide_id=example["guide_id"])
        self.assertEqual(dropped, [])
        self.assertEqual({k: v for k, v in doc.items() if k != "conditions"},
                         {k: v for k, v in example.items() if k != "conditions"})
        if same_ids:
            self.assertEqual(doc["conditions"], example["conditions"])
        else:   # 예시 1은 손으로 번호를 붙여서 순서만 달라요
            key = lambda c: json.dumps(c, ensure_ascii=False, sort_keys=True)
            self.assertEqual(sorted(without_id(doc["conditions"]), key=key),
                             sorted(without_id(example["conditions"]), key=key))
        for c in doc["conditions"]:
            q = c["guide_quote"]
            self.assertEqual(guide[q["start"]:q["end"]], q["text"])
        return doc

    def test_sample_1(self):
        doc = self.check("guide-sample.md", "conditions.example.json", same_ids=False)
        self.assertEqual([c["id"] for c in doc["conditions"]], [f"c{i}" for i in range(1, 9)])

    def test_sample_2_reviewplace(self):
        doc = self.check("guide-sample-2.md", "conditions.example-2.json", same_ids=True)
        self.assertEqual(doc["platform"], "reviewplace")
        # "제목 및 #태그" 한 문장에서 조건 두 개: 같은 인용, 같은 위치
        c1, c2 = doc["conditions"][:2]
        self.assertEqual((c1["type"], c2["type"], c2["params"]["pick"]), ("title_keyword", "hashtag", "any"))
        self.assertEqual(c1["guide_quote"], c2["guide_quote"])

    def test_output_matches_schema(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema가 없어요 (pip install jsonschema)")
        schema = json.loads((ROOT / "contracts" / "conditions.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        for guide_file, example_file in (("guide-sample.md", "conditions.example.json"),
                                         ("guide-sample-2.md", "conditions.example-2.json")):
            guide, example = sample(guide_file, example_file)
            doc, _ = ex.extract(guide, llm=lambda g: as_llm_output(example))
            self.assertEqual([e.message for e in validator.iter_errors(doc)], [])
        empty, _ = ex.extract(GUIDE, llm=fake([]))
        self.assertEqual([e.message for e in validator.iter_errors(empty)], [])


class QuoteCheck(unittest.TestCase):
    def test_made_up_quote_is_dropped_and_listed(self):
        real = said("photo_count", "사진은 12장 이상 올려 주세요.", "사진 12장", min=12)
        made_up = said("video_count", "동영상을 1개 이상 넣어 주세요.", "동영상", min=1)
        doc, dropped = ex.extract(GUIDE, llm=fake([made_up, real]))
        self.assertEqual([c["type"] for c in checked(doc)], ["photo_count"])
        self.assertEqual(len(dropped), 1)
        self.assertEqual(dropped[0]["code"], ex.QUOTE_NOT_FOUND)
        self.assertEqual((dropped[0]["type"], dropped[0]["label"]), ("video_count", "동영상"))
        self.assertIn("가이드 원문에 없어요", dropped[0]["reason"])

    def test_positions_are_code_points_counted_by_code(self):
        quote = "사진은 12장 이상 올려 주세요."
        doc, _ = ex.extract(GUIDE, llm=fake([said("photo_count", quote, min=12)]))
        q = doc["conditions"][0]["guide_quote"]
        self.assertEqual((q["start"], q["end"]), (GUIDE.index(quote), GUIDE.index(quote) + len(quote)))
        self.assertEqual(list(GUIDE)[q["start"]:q["end"]], list(quote))   # 앞에 이모지가 있어도 1글자로 셈

    def test_spacing_difference_is_fixed_to_the_original_text(self):
        doc, dropped = ex.extract(GUIDE, llm=fake([said("judgment", "창가 자리 사진을 꼭 넣어 주세요.", question="창가 자리 사진이 있는가")]))
        self.assertEqual(dropped, [])
        q = doc["conditions"][0]["guide_quote"]
        self.assertEqual(q["text"], "창가 자리  사진을   꼭 넣어 주세요.")
        self.assertEqual(GUIDE[q["start"]:q["end"]], q["text"])

    def test_leading_hash_marker_is_included_in_the_quote(self):
        guide = "본문키워드\n솔바람\n# 키워드를 본문에 3번 이상 넣어주세요.\n#솔바람 태그도 넣어주세요."
        doc, _ = ex.extract(guide, llm=fake([
            said("keyword_count", "키워드를 본문에 3번 이상 넣어주세요.", keywords=["솔바람"], min=3),
            said("hashtag", "솔바람 태그도 넣어주세요.", tags=["#솔바람"])]))
        quotes = [c["guide_quote"]["text"] for c in doc["conditions"]]
        self.assertEqual(quotes, ["# 키워드를 본문에 3번 이상 넣어주세요.", "솔바람 태그도 넣어주세요."])   # "#솔"은 안내 줄 표시가 아님

    def test_leading_list_number_is_left_out_of_the_quote(self):
        guide = "캠페인 안내\n4. 본문에 구매 링크를 넣어주세요.\n2) 사진은 3장 이상 넣어주세요.\n10장 이상"
        doc, _ = ex.extract(guide, llm=fake([
            said("link", "4. 본문에 구매 링크를 넣어주세요."),
            said("photo_count", "2) 사진은 3장 이상 넣어주세요.", min=3),
            said("photo_count", "10장 이상", min=10)]))
        got = [(c["guide_quote"]["text"], guide[c["guide_quote"]["start"]:c["guide_quote"]["end"]]) for c in doc["conditions"]]
        self.assertEqual(got, [("본문에 구매 링크를 넣어주세요.",) * 2, ("사진은 3장 이상 넣어주세요.",) * 2, ("10장 이상",) * 2])

    def test_mission_line_that_only_says_keyword_is_dropped(self):
        """리뷰어 미션의 "키워드" 한 줄을 조건으로 또 뽑으면 버려요 (위의 키워드 조건과 같은 조건)."""
        guide = "본문키워드\n솔바람\n# 키워드 중 1개를 선택하여 본문에 3번 이상 넣어주세요.\n\n리뷰어 미션\n키워드\n링크 삽입"
        doc, dropped = ex.extract(guide, llm=fake([
            said("keyword_count", "# 키워드 중 1개를 선택하여 본문에 3번 이상 넣어주세요.", keywords=["솔바람"], min=3),
            said("keyword_count", "키워드", keywords=["솔바람"], min=1)]))
        self.assertEqual([(c["type"], c["params"]["min"]) for c in doc["conditions"]], [("keyword_count", 3), ("link", 1)])
        self.assertEqual(doc["conditions"][1]["source"], "rule")      # "링크 삽입"은 AI가 안 냈지만 코드가 고정 칸에서 읽었어요
        self.assertIn("리뷰어 미션", dropped[0]["reason"])
        self.assertEqual((dropped[0]["code"], notices(doc)), (ex.MISSION_KEYWORD_LINE, []))     # 일부러 합친 것은 안내하지 않아요

    def test_made_up_keyword_is_dropped(self):
        quote = "본문에 \"솔바람 찻집\"을 3회 이상 넣어 주세요."
        ok = said("keyword_count", quote, keywords=["솔바람 찻집"], min=3)
        bad = said("keyword_count", quote, keywords=["솔바람 카페"], min=3)
        doc, dropped = ex.extract(GUIDE, llm=fake([ok, bad]))
        self.assertEqual(len(checked(doc)), 1)
        self.assertIn('"솔바람 카페"가 가이드 원문에 없어요', dropped[0]["reason"])
        self.assertEqual(dropped[0]["code"], ex.VALUE_NOT_IN_GUIDE)

    def test_number_not_in_quote_is_kept_for_review(self):
        """기준 숫자가 인용 문구에 안 보이면 버리지 않고 needs_review를 달아요."""
        quote = "사진은 12장 이상 올려 주세요."

        def params(guide, kind, q, **fields):
            doc, dropped = ex.extract(guide, llm=fake([said(kind, q, **fields)]))
            self.assertEqual(dropped, [])
            return doc["conditions"][0]["params"]

        self.assertNotIn("needs_review", params(GUIDE, "photo_count", quote, min=12))
        self.assertEqual(params(GUIDE, "photo_count", quote, min=20), {"min": 20, "needs_review": True})
        self.assertIs(params(GUIDE, "photo_count", quote, min=2)["needs_review"], True)   # "12장"의 2는 2장이 아니에요
        korean = "키워드를 다섯 번 넣어 주세요. 키워드는 솔바람이에요."
        got = params(korean, "keyword_count", "키워드를 다섯 번 넣어 주세요.", keywords=["솔바람"], min=5)
        self.assertEqual((got["min"], got["needs_review"]), (5, True))                    # 한글 숫자
        comma = "글은 1,500자 이상 써 주세요."
        self.assertNotIn("needs_review", params(comma, "length", comma, min=1500))        # 쉼표가 든 숫자는 알아봄
        self.assertNotIn("needs_review", params("링크 삽입", "link", "링크 삽입"))            # 숫자 없는 1개 조건

    def test_broken_items_are_dropped_not_crashed(self):
        raw = [said("새로운종류", "사진은 12장 이상 올려 주세요."), said("length", "사진은 12장 이상 올려 주세요."),
               said("keyword_count", "사진은 12장 이상 올려 주세요."), "조건이 아님", said("photo_count", "")]
        doc, dropped = ex.extract(GUIDE, llm=fake(raw))
        self.assertEqual((checked(doc), len(dropped)), ([], 5))
        self.assertEqual([d["code"] for d in dropped], [ex.SCHEMA_INVALID] * 4 + [ex.QUOTE_NOT_FOUND])
        doc, dropped = ex.extract(GUIDE, llm=lambda g: "JSON 객체가 아님")
        self.assertEqual((doc["conditions"], dropped), ([], []))

    def test_same_condition_twice_is_kept_once(self):
        c = said("photo_count", "사진은 12장 이상 올려 주세요.", min=12)
        doc, dropped = ex.extract(GUIDE, llm=fake([c, dict(c)]))
        self.assertEqual((len(doc["conditions"]), len(dropped)), (1, 1))


class DecidedByCode(unittest.TestCase):
    def test_countable(self):
        raw = [
            said("banned_terms", "'특효' 단어는 쓰지 말아 주세요.", terms=["특효"]),
            said("banned_terms", "'특효' 단어는 쓰지 말아 주세요.", category="과장 표현"),
            said("photo_count", "창가 자리  사진을   꼭 넣어 주세요.", subject="창가 자리"),
            said("judgment", "창가 자리  사진을   꼭 넣어 주세요.", question="창가 자리 사진이 있는가"),
            said("outside_draft", "🍵 솔바람 찻집 체험단 안내", what="안내"),
        ]
        doc, dropped = ex.extract(GUIDE, llm=fake(raw))
        self.assertEqual(dropped, [])
        got = {(c["type"], c["countable"]) for c in doc["conditions"]}
        self.assertEqual(got, {("banned_terms", True), ("banned_terms", False), ("photo_count", False),
                               ("judgment", False), ("outside_draft", False)})

    def test_single_item_pick_and_hashtag_only_phrase_are_normalized(self):
        guide = "키워드 솔바람을 3회 넣어 주세요.\n필수 해시태그 #솔바람찻집 을 넣어주세요.\n\"#오늘의차 한 잔\" 문구를 넣어주세요."
        doc, dropped = ex.extract(guide, llm=fake([
            said("keyword_count", "키워드 솔바람을 3회 넣어 주세요.", keywords=["솔바람"], min=3, pick="each"),
            said("required_phrase", "필수 해시태그 #솔바람찻집 을 넣어주세요.", phrase="#솔바람찻집"),
            said("required_phrase", "\"#오늘의차 한 잔\" 문구를 넣어주세요.", phrase="#오늘의차 한 잔")]))
        self.assertEqual(dropped, [])
        kw, tag, phrase = doc["conditions"]
        self.assertEqual(kw["params"]["pick"], "any")
        self.assertEqual((tag["type"], tag["params"]), ("hashtag", {"tags": ["#솔바람찻집"], "pick": "each"}))
        self.assertEqual(phrase["type"], "required_phrase")       # 태그 말고 다른 글자가 있으면 문구 그대로

    def test_hashtags_from_keywords_with_spaces(self):
        """키워드에 띄어쓰기가 있어도 해시태그는 붙여 써요. LLM이 어느 쪽으로 주든 같은 결과예요."""
        guide = "제목키워드\n솔내동 찻집 , 솔바람 찻집\n# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요."
        quote = "# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요."
        for tags in (["#솔내동 찻집", "#솔바람 찻집"], ["#솔내동찻집", "#솔바람찻집"], ["솔내동 찻집", "솔바람 찻집"]):
            doc, dropped = ex.extract(guide, llm=fake([said("hashtag", quote, tags=tags, pick="any")]))
            self.assertEqual(dropped, [], tags)
            self.assertEqual(doc["conditions"][0]["params"], {"tags": ["#솔내동찻집", "#솔바람찻집"], "pick": "any"})
        doc, dropped = ex.extract(guide, llm=fake([said("hashtag", quote, tags=["#지어낸태그"])]))
        self.assertEqual((checked(doc), len(dropped)), ([], 1))

    def test_phrase_with_several_hashtags_becomes_a_hashtag_condition(self):
        guide = "필수 해시태그 #솔바람 #아침차 를 모두 넣어주세요."
        doc, dropped = ex.extract(guide, llm=fake([said("required_phrase", guide, phrase="#솔바람 #아침차")]))
        self.assertEqual(dropped, [])
        self.assertEqual((doc["conditions"][0]["type"], doc["conditions"][0]["params"]),
                         ("hashtag", {"tags": ["#솔바람", "#아침차"], "pick": "each"}))

    def test_ids_follow_guide_order(self):
        raw = [said("banned_terms", "'특효' 단어는 쓰지 말아 주세요.", terms=["특효"]),
               said("photo_count", "사진은 12장 이상 올려 주세요.", min=12)]
        doc, _ = ex.extract(GUIDE, llm=fake(raw))
        self.assertEqual([(c["id"], c["type"]) for c in doc["conditions"]], [("c1", "photo_count"), ("c2", "banned_terms")])

    def test_platform(self):
        self.assertIsNone(ex.detect_platform(GUIDE))
        self.assertEqual(ex.detect_platform("제목키워드\n가, 나\n\n리뷰어 미션\n링크 삽입"), "reviewplace")
        self.assertIsNone(ex.detect_platform("본문키워드를 넣어 주세요"))

    def test_campaign_type_needs_the_word_in_the_guide(self):
        self.assertEqual(ex.extract(GUIDE, llm=fake([], "체험"))[0]["campaign_type"], "체험")
        self.assertEqual(ex.extract("방문형 캠페인 안내", llm=fake([], "체험"))[0]["campaign_type"], "체험")   # "체험"이라는 말이 없어도
        self.assertEqual(ex.extract(GUIDE, llm=fake([], "기자단"))[0]["campaign_type"], "체험")   # 근거 없는 기자단은 체험으로
        self.assertIsNone(ex.extract(GUIDE, llm=fake([], "모름"))[0]["campaign_type"])
        self.assertEqual(ex.extract("기자단 가이드", llm=fake([], "기자단"))[0]["campaign_type"], "기자단")
        no_word = "직접 써 본 것처럼 쓰지 말고, 체험한 것처럼 보이는 말은 빼 주세요."   # "기자단"이라는 말이 없는 기자단 가이드
        self.assertEqual(ex.extract(no_word, llm=fake([], "기자단"))[0]["campaign_type"], "기자단")
        self.assertIsNone(ex.extract(GUIDE, llm=fake([], "아무 값"))[0]["campaign_type"])


class Compare(unittest.TestCase):
    def test_compare_matches_by_type_and_quote_not_id(self):
        guide, example = sample("guide-sample-2.md", "conditions.example-2.json")
        raw = as_llm_output(example)
        raw["conditions"].reverse()                                   # 순서가 달라도
        doc, _ = ex.extract(guide, llm=lambda g: raw)
        rows = cmp.compare(doc, example)
        self.assertEqual(cmp.summary(rows), {"같음": 13, "값이 다름": 0, "인용 범위가 다름": 0, "놓침": 0,
                                             "더 뽑음": 0, "원고 밖 (세지 않음)": 1})

    def test_compare_reports_each_kind_of_difference(self):
        guide, example = sample("guide-sample.md", "conditions.example.json")
        raw = as_llm_output(example)
        by_type = {c["type"]: c for c in raw["conditions"]}
        by_type["keyword_count"]["min"] = 3                            # 값이 다름 (숫자 3은 인용에 없어서 확인 표시도 붙음)
        by_type["photo_count"]["subject"] = "가게 바깥 모습"              # 풀어 쓴 말이 달라도 같은 조건
        by_type["length"]["quote"] = "공백 제외 450자 이상"               # 인용 범위가 다름
        raw["conditions"].remove(by_type["map"])                       # 놓침
        raw["conditions"].append(said("judgment", "아래 내용을 지켜 원고를 작성해 주세요.", question="내용을 지켰는가"))   # 더 뽑음
        raw["conditions"].append(said("outside_draft", "원고는 방문 후 7일 안에 제출해 주세요.", what="기한"))          # 세지 않음
        doc, dropped = ex.extract(guide, llm=lambda g: raw)
        self.assertEqual(dropped, [])
        rows = cmp.compare(doc, example)
        got = {(r["type"], r["status"]) for r in rows}
        for pair in (("keyword_count", "값이 다름"), ("length", "인용 범위가 다름"), ("map", "놓침"),
                     ("outside_draft", "원고 밖 (세지 않음)"), ("disclosure", "같음")):
            self.assertIn(pair, got)
        self.assertEqual(cmp.summary(rows), {"같음": 5, "값이 다름": 1, "인용 범위가 다름": 1, "놓침": 1,
                                             "더 뽑음": 1, "원고 밖 (세지 않음)": 1})
        self.assertIn("| 놓침 | map |", cmp.table(rows))


class Decisions(unittest.TestCase):
    """2026-11-26 카티 결정 (후처리)."""

    def test_7_both_are_kept_when_the_sentence_has_no_condition(self):
        """조건 없이 "반드시 넣고, 다른 이름은 쓰지 마세요"라고 하면 필수 문구와 표기 조건을 둘 다 남겨요."""
        guide = "반드시 '솔바람 찻집'을 넣고, '솔바람 카페'라고는 쓰지 마세요."
        doc, dropped = ex.extract(guide, llm=fake([
            said("exact_phrase", guide, allowed="솔바람 찻집", forbidden=["솔바람 카페"]),
            said("required_phrase", guide, "필수 표기", phrase="솔바람 찻집")]))
        self.assertEqual(dropped, [])
        self.assertEqual(sorted(c["type"] for c in doc["conditions"]), ["exact_phrase", "required_phrase"])

    def test_7_conditional_wording(self):
        yes = ["제품명을 언급할 경우, 반드시", "상호 언급 시 반드시", "이름을 쓸 때는 반드시", "제품명을 작성하실 때 반드시", "표기 시에는"]
        no = ["반드시 '솔바람 찻집'을 넣고", "꼭 넣어 주세요", "시간이 지나도", "솔바람 시장에서", "어떤 경우에도 넣어 주세요"]
        self.assertTrue(all(ex.CONDITIONAL.search(t) for t in yes), [t for t in yes if not ex.CONDITIONAL.search(t)])
        self.assertFalse(any(ex.CONDITIONAL.search(t) for t in no), [t for t in no if ex.CONDITIONAL.search(t)])

    def test_7_required_phrase_on_the_same_quote_as_exact_phrase_is_dropped(self):
        guide = "1. 상호명을 언급할 경우, 반드시 '솔바람 찻집'으로 작성해주세요. ('솔바람 카페' x)\n2. \"*개인 차이가 있어요\" 문구를 넣어주세요."
        first = "상호명을 언급할 경우, 반드시 '솔바람 찻집'으로 작성해주세요. ('솔바람 카페' x)"
        doc, dropped = ex.extract(guide, llm=fake([
            said("exact_phrase", first, allowed="솔바람 찻집", forbidden=["솔바람 카페"]),
            said("required_phrase", first, "필수 표기", phrase="솔바람 찻집"),
            said("required_phrase", "\"*개인 차이가 있어요\" 문구를 넣어주세요.", phrase="*개인 차이가 있어요")]))
        self.assertEqual([c["type"] for c in doc["conditions"]], ["exact_phrase", "required_phrase"])
        self.assertEqual(doc["conditions"][1]["params"]["phrase"], "*개인 차이가 있어요")   # 다른 문장의 필수 문구는 그대로
        self.assertEqual((len(dropped), dropped[0]["label"]), (1, "필수 표기"))

    def test_8_link_with_and_without_address_become_one(self):
        guide = "4. 본문에 구매 링크를 넣어주세요. https://example.invalid/shop\n\n리뷰어 미션\n링크 삽입"
        both = [said("link", "링크 삽입", min=1),
                said("link", "본문에 구매 링크를 넣어주세요. https://example.invalid/shop", min=1, url="https://example.invalid/shop")]
        doc, dropped = ex.extract(guide, llm=fake(both))
        self.assertEqual((len(doc["conditions"]), dropped), (1, []))
        link = doc["conditions"][0]
        self.assertEqual(link["params"], {"min": 1, "url": "https://example.invalid/shop"})
        self.assertEqual([q["text"] for q in link["extra_quotes"]], ["링크 삽입"])
        self.assertEqual(guide[link["extra_quotes"][0]["start"]:link["extra_quotes"][0]["end"]], "링크 삽입")
        only, _ = ex.extract(guide, llm=fake(both[:1]))
        self.assertNotIn("extra_quotes", only["conditions"][0])                        # 주소 없는 링크만 있으면 그대로

    def test_8_contract_example_3_has_both_quotes_at_the_right_places(self):
        guide, example = sample("guide-04.md", "conditions.example-3.json")
        link = next(c for c in example["conditions"] if c["type"] == "link")
        self.assertEqual([q["text"] for q in link["extra_quotes"]], ["링크 삽입"])
        for c in example["conditions"]:
            for q in [c["guide_quote"], *c.get("extra_quotes", [])]:
                self.assertEqual(guide[q["start"]:q["end"]], q["text"], c["id"])

    def test_9_example_2_photo_line_is_a_photo_condition_with_a_subject(self):
        _, example = sample("guide-sample-2.md", "conditions.example-2.json")
        c = next(c for c in example["conditions"] if c["label"].startswith("사무실 책상"))
        self.assertEqual((c["type"], c["countable"], c["params"]["min"], "subject" in c["params"]), ("photo_count", False, 1, True))

    def test_10_press_needs_evidence_and_falls_back_to_experience(self):
        kind = lambda guide, said_: ex.extract(guide, llm=fake([], said_))[0]["campaign_type"]
        self.assertEqual(kind("본 캠페인은 기자단 캠페인입니다.", "기자단"), "기자단")
        self.assertEqual(kind("방문형 캠페인 안내", "기자단"), "체험")       # 근거가 없으면 null이 아니라 체험
        self.assertEqual(kind("방문형 캠페인 안내", "체험"), "체험")
        self.assertIsNone(kind("방문형 캠페인 안내", "모름"))              # AI가 모른다고 한 경우만 null


class CacheAndApi(unittest.TestCase):
    def test_same_guide_calls_once(self):
        llm = fake([said("photo_count", "사진은 12장 이상 올려 주세요.", min=12)])
        with tempfile.TemporaryDirectory() as tmp:
            first = ex.extract(GUIDE, llm=llm, cache_dir=Path(tmp))
            second = ex.extract(GUIDE, llm=llm, cache_dir=Path(tmp))
            self.assertEqual((llm.calls, first), (1, second))
            self.assertEqual(len(list(Path(tmp).iterdir())), 1)
            ex.extract(GUIDE + "5. 지도를 넣어 주세요.\n", llm=llm, cache_dir=Path(tmp))
            self.assertEqual(llm.calls, 2)          # 가이드가 바뀌면 다시 불러요
            with mock.patch.dict(os.environ, {ex.MODEL_ENV: "claude-sonnet-5-5"}):
                ex.extract(GUIDE, llm=llm, cache_dir=Path(tmp))
            self.assertEqual(llm.calls, 3)          # 모델이 바뀌어도 다시 불러요

    def test_without_cache_dir_nothing_is_written_or_printed(self):
        out, err = io.StringIO(), io.StringIO()
        before = set(ROOT.rglob("*.json"))
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), self.assertNoLogs(level="DEBUG"):
            ex.extract(GUIDE, llm=fake([said("photo_count", "사진은 12장 이상 올려 주세요.", min=12),
                                        said("video_count", "지어낸 문장", min=1)]))
        self.assertEqual((out.getvalue(), err.getvalue()), ("", ""))
        self.assertEqual(set(ROOT.rglob("*.json")), before)
        source = Path(ex.__file__).read_text(encoding="utf-8")
        for call in ("print(", "logging", "sys.stdout", "sys.stderr"):
            self.assertNotIn(call, source)

    def test_request_shape(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ex.MODEL_ENV, None)
            req = ex.build_request(GUIDE)
            self.assertEqual(req["model"], "claude-haiku-5-5")       # 개발 중 기본은 작은 모델
            os.environ[ex.MODEL_ENV] = "claude-sonnet-5-5"
            self.assertEqual(ex.build_request(GUIDE)["model"], "claude-sonnet-5-5")
        self.assertEqual(req["messages"], [{"role": "user", "content": f"<guide>\n{GUIDE}\n</guide>"}])
        self.assertEqual(req["output_config"]["format"], {"type": "json_schema", "schema": OUTPUT_SCHEMA})
        self.assertFalse({"temperature", "top_p", "top_k", "tool_choice"} & set(req))
        self.assertNotIn(GUIDE, req["system"][0]["text"])

    def test_output_schema_is_strict(self):
        item = OUTPUT_SCHEMA["properties"]["conditions"]["items"]
        for obj in (OUTPUT_SCHEMA, item):
            self.assertIs(obj["additionalProperties"], False)
            self.assertEqual(sorted(obj["required"]), sorted(obj["properties"]))
        self.assertEqual(item["properties"]["type"]["enum"], TYPES)
        self.assertEqual(sorted(said("judgment", "x")), sorted(item["properties"]))   # 가짜 응답도 같은 칸

    def test_types_match_the_contract(self):
        schema = json.loads((ROOT / "contracts" / "conditions.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(TYPES, schema["properties"]["conditions"]["items"]["properties"]["type"]["enum"])

    def test_private_guides_use_a_separate_cache_folder(self):
        self.assertEqual(ex.cache_dir_for(ROOT / "samples" / "guide-03.md"), ex.CACHE_DIR)
        self.assertEqual(ex.cache_dir_for(ROOT / "samples" / "private" / "dev" / "guide-01.md"), ex.PRIVATE_CACHE_DIR)
        self.assertEqual(ex.cache_dir_for(ROOT / "samples" / "private" / "holdout" / "guide-01.md"), ex.PRIVATE_CACHE_DIR)
        self.assertEqual(ex.PRIVATE_CACHE_DIR, ex.CACHE_DIR / "private")

    def test_holdout_guides_print_counts_only(self):
        """holdout 폴더의 가이드는 명령이 개수만 보여 줘요. 조건이나 가이드 글이 화면에 나오면 안 돼요."""
        import subprocess
        import sys
        guide, example = sample("guide-sample.md", "conditions.example.json")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "private" / "holdout"
            folder.mkdir(parents=True)
            (folder / "guide-01.md").write_text(guide, encoding="utf-8", newline="")
            cache = ex.cache_path(ex.PRIVATE_CACHE_DIR, guide)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps({"raw": as_llm_output(example)}, ensure_ascii=False), encoding="utf-8")
            self.addCleanup(lambda: cache.unlink(missing_ok=True))
            env = {**os.environ, "PYTHONIOENCODING": "utf-8", ex.MODEL_ENV: ex.model_name()}
            run = lambda *more: subprocess.run([sys.executable, "-m", "ai", str(folder / "guide-01.md"), *more],
                                               cwd=ROOT, capture_output=True, env=env, timeout=60)
            done = run()
            shown = done.stdout.decode("utf-8") + done.stderr.decode("utf-8")
            self.assertEqual(done.returncode, 0, shown)
            self.assertIn("조건 8개, 버린 조건 0개, 숫자 확인 필요 0개", shown)
            for secret in ("전포동", "모래알", "키워드", "guide_quote"):
                self.assertNotIn(secret, shown)
            refused = run("--out", str(Path(tmp) / "out.json"))
            self.assertNotEqual(refused.returncode, 0)
            self.assertFalse((Path(tmp) / "out.json").exists())

    def test_load_env_reads_names_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"PP_TEST_KEEP": "원래 값"}):
            path = Path(tmp) / ".env"
            path.write_text("# 설명\nPP_TEST_NEW=새 값\nPP_TEST_KEEP=바뀌면 안 됨\n\n빈줄아님\n", encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                ex.load_env(path)
                ex.load_env(Path(tmp) / "없는 파일")
            self.assertEqual((os.environ["PP_TEST_NEW"], os.environ["PP_TEST_KEEP"], out.getvalue()),
                             ("새 값", "원래 값", ""))
            os.environ.pop("PP_TEST_NEW")


class Notices(unittest.TestCase):
    """조건을 버리면 조용히 넘어가지 않고, 조건표에 "직접 봐 주세요" 안내를 남겨요."""

    def test_dropped_condition_leaves_a_notice_with_the_guide_line(self):
        # 인용이 가이드 문장과 닮았지만 글자가 달라요 (띄어쓰기·따옴표 차이가 아님)
        changed = said("photo_count", "사진은 12장 이상 꼭 올려 주시기 바랍니다.", "사진 12장", min=12)
        doc, dropped = ex.extract(GUIDE, llm=fake([changed]))
        self.assertEqual((checked(doc), dropped[0]["code"]), ([], ex.QUOTE_NOT_FOUND))
        (n,) = notices(doc)
        self.assertEqual((n["type"], n["label"], n["countable"]), ("judgment", "조건 하나를 확인하지 못했어요", False))
        self.assertEqual(n["params"], {"question": "가이드의 이 부분을 직접 봐 주세요", "unverified": True})
        self.assertEqual(n["guide_quote"]["text"], "2. 사진은 12장 이상 올려 주세요.")       # 코드가 찾은 가이드의 줄
        self.assertEqual(GUIDE[n["guide_quote"]["start"]:n["guide_quote"]["end"]], n["guide_quote"]["text"])

    def test_notice_without_a_line_when_nothing_in_the_guide_looks_like_it(self):
        doc, dropped = ex.extract(GUIDE, llm=fake([said("video_count", "동영상을 1개 이상 넣어 주세요.", "동영상", min=1)]))
        (n,) = notices(doc)
        self.assertEqual(n["guide_quote"], {"text": "", "start": 0, "end": 0})
        self.assertEqual(n["params"], {"question": "가이드를 직접 다시 봐 주세요", "unverified": True})

    def test_notice_never_carries_what_the_ai_wrote(self):
        bad = said("required_phrase", "3. '특효' 단어는 쓰지 말아 주세요.", "<b>AI가 쓴 라벨</b>", phrase="AI가 지어낸 문구")
        doc, dropped = ex.extract(GUIDE, llm=fake([bad]))
        self.assertEqual(dropped[0]["code"], ex.VALUE_NOT_IN_GUIDE)
        text = json.dumps(notices(doc), ensure_ascii=False)
        self.assertNotIn("AI가", text)
        self.assertIn("3. '특효' 단어는 쓰지 말아 주세요.", text)

    def test_one_notice_per_line_and_a_cap(self):
        same_line = [said("length", "2. 사진은 12장 이상 올려 주세요.", f"엉뚱한 조건 {i}") for i in range(5)]
        doc, dropped = ex.extract(GUIDE, llm=fake(same_line))
        self.assertEqual((len(dropped), len(notices(doc))), (5, 1))
        guide = "\n".join(f"{i}번 줄에는 조건 문장이 하나 들어 있어요 {i * 7919}" for i in range(40))
        many = [said("length", line, "숫자 없는 글자 수") for line in guide.splitlines()]
        doc, dropped = ex.extract(guide, llm=fake(many))
        self.assertEqual((len(dropped), len(notices(doc))), (40, ex.MAX_NOTICES))

    def test_notice_is_a_hold_in_the_check_result(self):
        try:
            from be import engine
        except ImportError:
            self.skipTest("be/engine.py가 없는 저장소예요 (서버와 이어진 뒤에 돌려요)")
        doc, _ = ex.extract(GUIDE, llm=fake([said("video_count", "동영상을 1개 이상 넣어 주세요.", min=1),
                                             said("photo_count", "사진은 12장 이상 올려 주세요.", min=12)]))
        request = json.loads((ROOT / "contracts" / "check-request.example.json").read_text(encoding="utf-8"))
        request["photo_count"] = 12
        result = engine.check(doc, request)
        self.assertEqual(result["summary"], {"kept": 1, "missing": 0, "hold": 1})
        hold = next(r for r in result["results"] if r["status"] == "hold")
        self.assertEqual(hold["label"], "조건 하나를 확인하지 못했어요")
        self.assertIn("직접", hold["note"])
        self.assertNotIn("셀 수 없는", hold["note"])

    def test_small_differences_in_the_quote_are_the_same_quote(self):
        """띄어쓰기·줄바꿈, 따옴표 종류, 앞의 번호만 다르면 같은 인용으로 보고 살려요."""
        guide = "안내\n1) 본문에 “솔바람 찻집”을 3회 이상\n넣어 주세요.\n2. '특효' 단어는 쓰지 말아 주세요.\n"
        for quote, want in (
            ('본문에 "솔바람 찻집"을 3회 이상 넣어 주세요.', "본문에 “솔바람 찻집”을 3회 이상\n넣어 주세요."),      # 따옴표 종류, 줄바꿈
            ("1. 본문에 “솔바람찻집”을 3회이상 넣어주세요.", "본문에 “솔바람 찻집”을 3회 이상\n넣어 주세요."),     # 번호 모양, 띄어쓰기
            ("3) ‘특효’ 단어는 쓰지 말아 주세요.", "'특효' 단어는 쓰지 말아 주세요."),                           # 번호가 다름, 따옴표 종류
        ):
            doc, dropped = ex.extract(guide, llm=fake([said("judgment", quote, question="물음")]))
            self.assertEqual((dropped, notices(doc)), ([], []), quote)
            q = doc["conditions"][0]["guide_quote"]
            self.assertEqual((q["text"], guide[q["start"]:q["end"]]), (want, want))
        # 글자가 다르면 지금처럼 버리고(안내는 남김), 키워드 같은 값은 여전히 글자 그대로 있어야 해요
        doc, dropped = ex.extract(guide, llm=fake([said("judgment", "'특효' 단어는 쓰지 마세요.", question="물음"),
                                                   said("keyword_count", "본문에 “솔바람 찻집”을 3회 이상", keywords=["솔바람찻집"], min=3)]))
        self.assertEqual([d["code"] for d in dropped], [ex.QUOTE_NOT_FOUND, ex.VALUE_NOT_IN_GUIDE])
        self.assertEqual((checked(doc), len(notices(doc))), ([], 2))

    def test_long_guide_with_many_dropped_conditions_is_fast(self):
        import time
        guide = "\n".join("가나다라마바사아자차" * 20 for _ in range(100))[:20_000]
        junk = [said("length", "가나다라마바사아자차카" * 18 + str(i)) for i in range(100)]
        started = time.time()
        doc, dropped = ex.build(guide, {"campaign_type": "모름", "conditions": junk})
        self.assertLess(time.time() - started, 2)
        self.assertLessEqual(len(notices(doc)), ex.MAX_NOTICES)

    def test_drop_counts_have_codes_and_types_only(self):
        _, dropped = ex.extract(GUIDE, llm=fake([said("video_count", "지어낸 문장", min=1), said("video_count", "또 지어낸 문장", min=1),
                                                 said("length", "2. 사진은 12장 이상 올려 주세요.")]))
        self.assertEqual(ex.drop_counts(dropped), {"QUOTE_NOT_FOUND:video_count": 2, "SCHEMA_INVALID:length": 1})


RP_GUIDES = ["guide-sample-2.md"] + [f"guide-0{n}.md" for n in range(3, 8)]
EMPTY = {"campaign_type": "모름", "conditions": []}


def rule_made(doc: dict) -> list[dict]:
    return [c for c in doc["conditions"] if c.get("source") == "rule"]


class FixedFields(unittest.TestCase):
    """리뷰플레이스 고정 칸은 코드가 직접 읽어요 (AI 결과의 안전망)."""

    def read(self, name: str) -> str:
        return (ROOT / "samples" / name).read_text(encoding="utf-8")

    def test_nothing_happens_outside_reviewplace_guides(self):
        self.assertEqual(ex.read_fixed(self.read("guide-sample.md")), [])
        self.assertEqual(ex.read_fixed(GUIDE), [])
        doc, _ = ex.build(self.read("guide-sample.md"), EMPTY)
        self.assertEqual(doc["conditions"], [])
        # 칸 이름이 하나뿐이면 리뷰플레이스 모양으로 보지 않아요
        self.assertEqual(ex.read_fixed("리뷰어 미션\n링크 삽입\n1,000자 이상"), [])

    def test_code_alone_reads_the_fixed_fields_of_every_sample(self):
        """AI가 아무것도 못 냈어도 고정 칸의 조건은 나와요."""
        for name in RP_GUIDES:
            guide = self.read(name)
            doc, dropped = ex.build(guide, EMPTY)
            kinds = [c["type"] for c in doc["conditions"]]
            for kind in ("title_keyword", "hashtag", "keyword_count", "disclosure", "length", "photo_count", "outside_draft"):
                self.assertIn(kind, kinds, name)
            self.assertEqual((rule_made(doc), dropped), (doc["conditions"], []), name)
            for c in doc["conditions"]:
                q = c["guide_quote"]
                self.assertEqual(guide[q["start"]:q["end"]], q["text"], name)
                self.assertNotIn("needs_review", c["params"], name)

    def test_code_reading_matches_the_contract_examples(self):
        """코드가 읽은 값이 예시(샘플 2, 샘플 04)의 같은 조건과 같아요."""
        for guide_file, example_file in (("guide-sample-2.md", "conditions.example-2.json"), ("guide-04.md", "conditions.example-3.json")):
            guide, example = sample(guide_file, example_file)
            doc, _ = ex.build(guide, EMPTY)
            for c in doc["conditions"]:
                quotes = lambda e: [e["guide_quote"]["text"]] + [q["text"] for q in e.get("extra_quotes", [])]
                (want,) = [e for e in example["conditions"] if e["type"] == c["type"] and c["guide_quote"]["text"] in quotes(e)]
                for key in ex.FIXED_VALUES:
                    if key in c["params"]:
                        self.assertEqual(c["params"][key], want["params"][key], (guide_file, c["type"], key))

    def test_code_reading_matches_the_answer_keys(self):
        """샘플 03~07: 코드가 읽은 조건이 정답지의 조건과 같아요 (정답지는 읽기만 해요)."""
        import sys
        sys.path.insert(0, str(ROOT / "criteria"))
        try:
            import measure
        except ImportError:
            self.skipTest("criteria/measure.py가 없는 저장소예요")
        for n in measure.SAMPLES:
            doc, _ = ex.build(self.read(f"guide-{n}.md"), EMPTY)
            key = measure.read_key(n)["conditions"]
            self.assertEqual(len(doc["conditions"]), 8, n)
            for c in doc["conditions"]:
                (want,) = [w for w in key if w["kind"] == c["type"] and measure.quote_matches(w, c)]
                diffs = [d for d in measure.value_diffs(want, c) if not d.startswith("url")]    # 주소는 캠페인 안내 줄에 있어요 (AI가 읽어요)
                self.assertEqual(diffs, [], (n, c["type"]))

    def test_missing_fixed_fields_are_simply_not_made(self):
        """고정 칸 일부가 없는 가이드: 있는 칸만 읽어요."""
        guide = (
            "[블로그] 달빛 수제청을 소개해주세요\n\n"
            "제목키워드\n달빛 수제청 , 유자청 추천\n# 키워드 중 1개를 선택하여 제목에 넣어주세요.\n\n"      # 태그 말이 없음
            "본문키워드\n달빛 수제청\n"                                                                    # 안내 줄이 없음
            "캠페인 안내\n1. 따뜻한 물에 타서 마시는 사진을 넣어주세요.\n\n"                              # 대가성 줄이 없음
            "리뷰어 미션\n키워드\n800자 이상\n미션이 지켜지지 않을 경우 환수될 수 있습니다\n"             # 링크, 사진, 동영상 줄이 없음
        )                                                                                                # 등록기간 줄이 없음
        doc, dropped = ex.build(guide, EMPTY)
        self.assertEqual([(c["type"], c["params"], c["guide_quote"]["text"]) for c in doc["conditions"]], [
            ("title_keyword", {"keywords": ["달빛 수제청", "유자청 추천"], "pick": "any"}, "# 키워드 중 1개를 선택하여 제목에 넣어주세요."),
            ("length", {"min": 800, "count_spaces": None}, "800자 이상"),
        ])
        self.assertEqual((dropped, [c["source"] for c in doc["conditions"]]), ([], ["rule", "rule"]))

    def test_ai_condition_is_used_but_code_values_win(self):
        guide = self.read("guide-sample-2.md")
        note = "# 키워드 중 1개를 선택하여 본문에 4번 이상 넣어주세요."
        doc, dropped = ex.build(guide, {"campaign_type": "체험", "conditions": [
            said("keyword_count", note, "AI가 붙인 이름", keywords=["녹차스틱", "바다숲녹차"], min=5, pick="each", scope="title_and_body"),
            said("photo_count", "15장 이상", "사진", min=10)]})
        kc = next(c for c in doc["conditions"] if c["type"] == "keyword_count")
        self.assertEqual(kc["params"], {"keywords": ["녹차스틱", "바다숲녹차", "간편녹차", "사무실차"], "min": 4, "pick": "any", "scope": "body"})
        self.assertEqual((kc["label"], kc.get("source")), ("AI가 붙인 이름", None))       # AI 조건을 쓰되 값은 코드 것
        photo = next(c for c in doc["conditions"] if c["type"] == "photo_count")
        self.assertEqual((photo["params"], photo.get("source")), ({"min": 15}, None))     # needs_review를 달지 않아요
        self.assertEqual(dropped, [])
        self.assertEqual(len(doc["conditions"]), 9)                                       # 나머지 7개는 코드가 만들었어요
        self.assertEqual(len(rule_made(doc)), 7)

    def test_no_double_condition_when_the_ai_quotes_another_line_of_the_same_field(self):
        """AI가 안내 줄이 아니라 키워드 줄을 인용해도 같은 조건으로 봐요 (실제로 나온 경우)."""
        guide = self.read("guide-06.md")
        doc, dropped = ex.build(guide, {"campaign_type": "기자단", "conditions": [
            said("title_keyword", "솔내동 스터디카페 , 모담 스터디카페", "제목에 키워드 1개", keywords=["솔내동 스터디카페", "모담 스터디카페"], pick="any"),
            said("title_keyword", "제목키워드", "제목 키워드", keywords=["모담 스터디카페"], pick="any")]})
        titles = [c for c in doc["conditions"] if c["type"] == "title_keyword"]
        self.assertEqual(len(titles), 1)
        self.assertEqual(titles[0]["guide_quote"]["text"], "# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.")
        self.assertEqual(titles[0]["params"], {"keywords": ["솔내동 스터디카페", "모담 스터디카페"], "pick": "any"})
        self.assertEqual([d["code"] for d in dropped], [ex.DUPLICATE])

    def test_disclosure_line_read_as_an_empty_required_phrase_is_still_a_disclosure(self):
        """실제로 나온 경우: AI가 대가성 줄을 문구가 빈 필수 문구로 냈어요. 코드가 대가성 조건을 만들고, 안내는 띄우지 않아요."""
        guide = self.read("guide-06.md")
        line = "공정위 대가성 문구는 반드시 리뷰 상단에 기재해주세요."
        doc, dropped = ex.build(guide, {"campaign_type": "기자단", "conditions": [said("required_phrase", line, "대가성 문구를 리뷰 상단에", position="top")]})
        self.assertEqual(ex.drop_counts(dropped), {"SCHEMA_INVALID:required_phrase": 1})
        disclosure = next(c for c in doc["conditions"] if c["type"] == "disclosure")
        self.assertEqual((disclosure["params"], disclosure["source"], disclosure["guide_quote"]["text"]),
                         ({"phrase": None, "position": "top"}, "rule", line))
        self.assertEqual(notices(doc), [])
        # 리뷰플레이스 모양이 아닌 가이드에서는 코드가 만들지 않으니 안내가 떠요
        plain = "체험단 안내\n" + line + "\n사진은 3장 이상 넣어주세요."
        doc, _ = ex.build(plain, {"campaign_type": "체험", "conditions": [said("required_phrase", line, position="top")]})
        self.assertEqual([n["guide_quote"]["text"] for n in notices(doc)], [line])

    def test_link_with_address_and_mission_link_are_still_one(self):
        """AI가 주소 있는 링크만 냈어도, 코드가 읽은 "링크 삽입"과 하나로 합쳐져요."""
        guide, example = sample("guide-04.md", "conditions.example-3.json")
        raw = as_llm_output(example)
        raw["conditions"] = [c for c in raw["conditions"] if c["quote"] != "링크 삽입"]
        doc, _ = ex.build(guide, raw, example["guide_id"])
        self.assertEqual(doc["conditions"], example["conditions"])

    def test_repeated_fixed_lines_make_one_condition_each(self):
        """같은 고정 줄을 수백 번 되풀이한 가이드여도 코드가 만드는 조건은 종류마다 하나예요."""
        guide = self.read("guide-06.md") + "\n리뷰 등록기간 12.04 ~ 12.11" * 300 + "\n공정위 대가성 문구는 상단에 기재해주세요." * 300 \
            + "\n리뷰어 미션\n" + "700자 이상\n" * 300
        doc, dropped = ex.build(guide, EMPTY)
        kinds = [c["type"] for c in doc["conditions"]]
        self.assertEqual((len(kinds), len(set(kinds)), dropped), (8, 8, []))
        self.assertEqual(next(c for c in doc["conditions"] if c["type"] == "outside_draft")["guide_quote"]["start"],
                         guide.index("리뷰 등록기간"))

    def test_notice_is_not_hidden_when_the_fixed_line_is_only_a_guess(self):
        """고정 칸의 줄과 닮기만 한 인용(원문에 없는 문장)은 안내를 숨기지 않아요."""
        guide = self.read("guide-06.md")
        near = said("required_phrase", "공정위 대가성 문구는 반드시 리뷰 맨 아래에 기재해주세요.", "지어낸 문장")
        doc, dropped = ex.build(guide, {"campaign_type": "기자단", "conditions": [near]})
        self.assertEqual([d["code"] for d in dropped], [ex.QUOTE_NOT_FOUND])
        self.assertEqual([n["guide_quote"]["text"] for n in notices(doc)], ["공정위 대가성 문구는 반드시 리뷰 상단에 기재해주세요."])

    def test_contract_example_4_is_what_the_code_builds(self):
        """예시 4: 고정 칸 8개는 코드가 만들고(source: rule), 확인하지 못한 조건 하나는 안내로 남아요."""
        guide, example = sample("guide-05.md", "conditions.example-4.json")
        doc, dropped = ex.build(guide, example_4_raw(), example["guide_id"])
        self.assertEqual(doc, example)
        self.assertEqual(ex.drop_counts(dropped), {"SCHEMA_INVALID:length": 1})
        self.assertEqual((len(rule_made(doc)), len(notices(doc)), len(doc["conditions"])), (8, 1, 14))
        self.assertEqual(notices(doc)[0]["guide_quote"]["text"],
                         "미션이 지켜지지 않을 경우 제공된 제품 및 포인트의 환수 혹은 미지급 처리가 될 수 있습니다")

    def test_output_with_rule_made_conditions_and_notices_matches_the_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema가 없어요 (pip install -r ai/requirements.txt)")
        schema = json.loads((ROOT / "contracts" / "conditions.schema.json").read_text(encoding="utf-8"))
        doc, _ = ex.build(self.read("guide-05.md"), {"campaign_type": "체험", "conditions": [
            said("banned_terms", "1. 질병 이름은 직접 언급하지 말아주세요.", terms=["지어낸 금지어"])]})
        self.assertEqual((len(rule_made(doc)), len(notices(doc))), (8, 1))
        jsonschema.validate(doc, schema)



# 10단계: 레뷰·강남맛집 고정 틀 (지어낸 가이드. 실제 가이드의 칸 모양만 따랐어요)
REVU = "\n".join([
    "제공 내역\t", "- 솔바람 녹차 30포", "캠페인 미션\t", "", "키워드", "", "링크 삽입", "", "1000자 이상", "", "15장 이상", "",
    "동영상 첨부", "", "1. 아침마다 솔바람 녹차를 마신다는 내용.", "2. 패키지와 우린 차를 함께 찍어 주세요.",
    "키워드 ", "제목 키워드 키워드 복사", "솔바람녹차, 녹차추천",
    "- 위 키워드를 글 제목에 넣어 주세요.",
    "본문 키워드 키워드 복사", "아침차,녹차선물,아침차,티타임",
    "- 위 키워드 중 1개 이상을 선택하여 총 5회 이상 써 주세요.",
    "링크\t", "https://example.invalid/tea", "복사", "- 위 링크를 글에 넣어 주세요.", "",
    "추가 안내사항\t- 등록기간 미준수 시 페널티", "- 선정 인원 변경 가능", "- 단독 촬영 필수", "- 유지기간 6개월",
    "- 생성형 AI 이용 불가", "- 앱 이벤트 안내",
])
GANGNAM = "\n".join([
    "[서울] 솔바람찻집 성수점", "", "Blog 방문형", "", "키워드", "솔바람찻집 성수카페 성수디저트",
    "- 키워드는 제목 1회, 본문 3회 이상 넣어 주세요.", "", "플레이스 URL", "", "가이드라인", "",
    "1. 사진을 정성껏 찍어 주세요.", "2. 동영상을 포함하여 사진은 최소 15장 넣어 주세요",
    "3. 하단에 지도 위치 링크를 넣어 주세요", "4. 텍스트 1,000자 이상 써 주세요", "5. 참고해 주세요.", "",
    "리뷰 시 주의사항", "1. 예약 시간을 지켜 주세요.", "2. 유지 기간 6개월.", "NOTICE", "1. 메일링 안내", "2. 배너 안내",
    "3. 블로그 글에는 스폰서 배너를 글 맨 위에 붙여 주세요.", "(블로그 밖 SNS 글에는 대가성 문구를 맨 위에 써 주세요.)",
])


def validate(kind: str, data: dict) -> list:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        raise unittest.SkipTest("jsonschema가 없어요 (pip install -r ai/requirements.txt)") from None
    schema = json.loads((ROOT_DIR / "contracts" / f"{kind}.schema.json").read_text(encoding="utf-8"))
    return [e.message for e in Draft202012Validator(schema).iter_errors(data)]


ROOT_DIR = Path(__file__).resolve().parent.parent


def rule_doc(guide: str) -> dict:
    """AI 없이 코드가 읽은 조건만 (AI 응답이 비었을 때)."""
    return ex.build(guide, {"campaign_type": "체험", "conditions": []})[0]


class FixedForms(unittest.TestCase):
    def test_revu_chips_keywords_link_and_notices_are_read_by_code(self):
        self.assertEqual(ex.detect_form(REVU), "revu")
        doc = rule_doc(REVU)
        by = {c["type"]: c for c in doc["conditions"]}
        self.assertTrue(all(c["source"] == "rule" for c in doc["conditions"]))
        self.assertEqual(by["title_keyword"]["params"], {"keywords": ["솔바람녹차", "녹차추천"], "pick": "each"})
        self.assertEqual(by["keyword_count"]["params"], {"keywords": ["아침차", "녹차선물", "티타임"], "min": 5, "pick": "sum",
                                                         "scope": "body"})       # 목록 안 중복은 하나로
        self.assertEqual(by["link"]["params"], {"min": 1, "url": "https://example.invalid/tea"})
        self.assertEqual((by["length"]["params"]["min"], by["photo_count"]["params"]["min"], by["video_count"]["params"]["min"]),
                         (1000, 15, 1))
        self.assertEqual([c["type"] for c in doc["conditions"]].count("outside_draft"), 1)    # 추가 안내사항 6줄은 하나로
        self.assertIsNone(doc["platform"])                       # 조건 목록의 platform 값은 그대로 (리뷰플레이스만)
        self.assertEqual(validate("conditions", doc), [])

    def test_revu_contradictions_are_shown_not_resolved(self):
        guide = REVU.replace("링크 삽입", "").replace("2. 패키지와", "2. 링크 필수로 넣고 패키지와") \
            .replace("1. 아침마다 솔바람 녹차를", "1. 아침마다 솔바람 녹차를 (솔바람 녹차)")
        doc = rule_doc(guide)
        conflicts = [c for c in doc["conditions"] if c["label"].startswith(ex.CONFLICT)]
        self.assertEqual(sorted(c["label"] for c in conflicts), ["가이드 안에서 말이 달라요: 링크", "가이드 안에서 말이 달라요: 키워드 띄어쓰기"])
        self.assertTrue(all(c["type"] == "judgment" and not c["countable"] and "확인해 주세요" in c["params"]["question"]
                            for c in conflicts))
        self.assertEqual(validate("conditions", doc), [])

    def test_gangnam_keywords_guidelines_and_notice(self):
        self.assertEqual(ex.detect_form(GANGNAM), "gangnam")
        doc = rule_doc(GANGNAM)
        by = {c["type"]: c for c in doc["conditions"]}
        self.assertEqual(by["title_keyword"]["params"], {"keywords": ["솔바람찻집", "성수카페", "성수디저트"], "pick": "any"})
        # 강남맛집 규칙(블로거 확인): 지정 키워드 중 1개 이상이 3회 이상 + 자율 키워드(블로거가 적음) 3회 이상
        fixed, free = [c for c in doc["conditions"] if c["type"] == "keyword_count"]
        self.assertEqual(fixed["params"], {"keywords": ["솔바람찻집", "성수카페", "성수디저트"], "min": 3, "pick": "any", "scope": "body"})
        self.assertEqual(free["params"], {"keywords": [], "min": 3, "pick": "each", "scope": "body", "free": True})
        self.assertNotIn("애매", fixed["label"])
        self.assertEqual(by["photo_count"]["params"], {"min": 15, "include_video": True})
        self.assertEqual(by["map"]["params"], {"position": "bottom"})
        self.assertEqual(by["length"]["params"]["min"], 1000)
        self.assertEqual([c["type"] for c in doc["conditions"]].count("outside_draft"), 1)
        self.assertFalse(any(c["label"].startswith(ex.CONFLICT) for c in doc["conditions"]))
        self.assertEqual(validate("conditions", doc), [])

    def test_gangnam_keywords_with_inner_spaces_are_left_to_ai(self):
        guide = GANGNAM.replace("솔바람찻집 성수카페 성수디저트", "성수 근처 카페 성수 근처 디저트 카페")
        doc = rule_doc(guide)
        self.assertFalse(any(c["type"] in ("title_keyword", "keyword_count") for c in doc["conditions"]))

    def test_delivery_guide_with_a_map_line_is_flagged(self):
        doc = rule_doc(GANGNAM.replace("Blog 방문형", "Blog 배송형"))
        self.assertTrue(any(c["label"] == "가이드 안에서 말이 달라요: 지도" for c in doc["conditions"]))

    def test_ai_values_for_fixed_fields_are_replaced_by_code(self):
        quote = "- 위 키워드 중 1개 이상을 선택하여 총 5회 이상 써 주세요."
        ai = {"campaign_type": "체험", "conditions": [
            {"type": "keyword_count", "label": "본문 키워드", "keywords": ["아침차"], "min": 3, "pick": "any", "quote": quote}]}
        doc = ex.build(REVU, ai)[0]
        (kw,) = [c for c in doc["conditions"] if c["type"] == "keyword_count"]
        self.assertEqual((kw["params"]["pick"], kw["params"]["min"], kw["params"]["keywords"]), ("sum", 5, ["아침차", "녹차선물", "티타임"]))



class PhotoRange(unittest.TestCase):
    def test_photo_range_sets_the_maximum_and_counts_videos(self):
        guide = REVU.replace("2. 패키지와 우린 차를 함께 찍어 주세요.", "2. 사진·영상 합쳐 15~20장 넣어 주세요.")
        doc = rule_doc(guide)
        (photo,) = [c for c in doc["conditions"] if c["type"] == "photo_count"]
        self.assertEqual(photo["params"], {"min": 15, "max": 20, "include_video": True})
        self.assertEqual(photo["label"], "사진 15~20장 (동영상 포함)")
        self.assertEqual([q["text"] for q in photo["extra_quotes"]], ["2. 사진·영상 합쳐 15~20장 넣어 주세요."])
        self.assertEqual(validate("conditions", doc), [])

    def test_no_range_leaves_the_photo_condition_alone(self):
        (photo,) = [c for c in rule_doc(REVU)["conditions"] if c["type"] == "photo_count"]
        self.assertEqual(photo["params"], {"min": 15})


class FixedFormsWithAi(unittest.TestCase):
    def test_ai_title_keyword_on_the_note_line_is_merged_into_the_code_one(self):
        note = "- 위 키워드를 글 제목에 넣어 주세요."
        ai = {"campaign_type": "체험", "conditions": [
            {"type": "title_keyword", "label": "제목 키워드", "keywords": ["솔바람녹차"], "pick": "any", "quote": note}]}
        doc = ex.build(REVU, ai)[0]
        (title,) = [c for c in doc["conditions"] if c["type"] == "title_keyword"]
        self.assertEqual(title["params"], {"keywords": ["솔바람녹차", "녹차추천"], "pick": "each"})



class FixedValuesWithAi(unittest.TestCase):
    def test_include_video_from_the_fixed_field_replaces_the_ai_value(self):
        """실제 AI 시험(2026-11-27)에서 찾은 것: AI도 같은 줄에서 사진 조건을 뽑으면 코드가 읽은 "동영상 포함"이 빠졌어요."""
        line = "2. 동영상을 포함하여 사진은 최소 15장 넣어 주세요"
        ai = {"campaign_type": "체험", "conditions": [{"type": "photo_count", "label": "사진 15장", "min": 15, "quote": line}]}
        (photo,) = [c for c in ex.build(GANGNAM, ai)[0]["conditions"] if c["type"] == "photo_count"]
        self.assertEqual(photo["params"], {"min": 15, "include_video": True})


class TitleRule(unittest.TestCase):
    """제목 키워드 기준을 가이드 문장으로 정해요 (2026-11-27). 경계: 3개/4개, 고르는 말, [필수]."""

    def test_count_and_wording(self):
        three, four = ["가나", "다라", "마바"], ["가나", "다라", "마바", "사아"]
        self.assertEqual(ex.title_rule("가나, 다라, 마바", three), (three, "each"))
        self.assertEqual(ex.title_rule("가나, 다라, 마바, 사아", four), (four, "both"))
        for words in ("위 키워드 중 1개를 제목에", "1개를 선택해 제목에", "택1", "하나 이상 넣어 주세요", "키워드 1개 이상"):
            self.assertEqual(ex.title_rule(words, four)[1], "any", words)
        for words in ("집중해서 써 주세요", "중요한 키워드예요", "중간에 넣어 주세요"):        # "중"이 낱말 안에 든 경우
            self.assertEqual(ex.title_rule(words, four)[1], "both", words)

    def test_required_mark_keeps_only_required_keywords(self):
        text = "[필수] 가나, 다라\n[추가] 마바, 사아"
        self.assertEqual(ex.title_rule(text, ["가나", "다라", "마바", "사아"]), (["가나", "다라"], "each"))
        # 같은 줄에 [선택]이 있어도 [필수]가 먼저예요
        self.assertEqual(ex.title_rule("[필수] 가나, 다라 [선택] 마바", ["가나", "다라", "마바"]), (["가나", "다라"], "each"))

    def test_wording_on_the_line_above_the_keyword_list_counts(self):
        guide = "아래 키워드 중 1개를 제목에 넣어 주세요.\n솔바람녹차, 녹차추천, 아침차\n"
        ai = {"campaign_type": "체험", "conditions": [{"type": "title_keyword", "label": "제목 키워드", "pick": "each",
              "keywords": ["솔바람녹차", "녹차추천", "아침차"], "quote": "솔바람녹차, 녹차추천, 아침차"}]}
        (title,) = ex.build(guide, ai)[0]["conditions"]
        self.assertEqual(title["params"]["pick"], "any")

    def test_revu_required_list_is_read_by_code(self):
        guide = REVU.replace("솔바람녹차, 녹차추천", "[필수] 솔바람녹차, 녹차추천\n[추가] 아침차, 티타임")
        (title,) = [c for c in rule_doc(guide)["conditions"] if c["type"] == "title_keyword"]
        self.assertEqual(title["params"], {"keywords": ["솔바람녹차", "녹차추천"], "pick": "each"})
        self.assertEqual(title["label"], "제목에 필수 키워드 모두")

    def test_revu_four_keywords_without_wording_shows_both(self):
        guide = REVU.replace("솔바람녹차, 녹차추천", "솔바람녹차, 녹차추천, 아침차, 티타임")
        (title,) = [c for c in rule_doc(guide)["conditions"] if c["type"] == "title_keyword"]
        self.assertEqual(title["params"]["pick"], "both")
        self.assertEqual(validate("conditions", rule_doc(guide)), [])

    def test_ai_title_condition_outside_fixed_fields_follows_the_wording(self):
        guide = "제목 키워드\n솔바람녹차, 녹차추천, 아침차, 티타임\n- 위 키워드 중 1개를 제목에 넣어 주세요.\n"
        ai = {"campaign_type": "체험", "conditions": [{"type": "title_keyword", "label": "제목 키워드", "pick": "each",
              "keywords": ["솔바람녹차", "녹차추천", "아침차", "티타임"], "quote": "솔바람녹차, 녹차추천, 아침차, 티타임"}]}
        (title,) = ex.build(guide, ai)[0]["conditions"]
        self.assertEqual(title["params"]["pick"], "any")

    def test_ai_cannot_make_a_free_keyword_condition(self):
        guide = "본문 키워드\n녹차\n- 3회 이상 써 주세요.\n"
        ai = {"campaign_type": "체험", "conditions": [{"type": "keyword_count", "label": "본문", "keywords": [], "min": 3,
              "free": True, "quote": "- 3회 이상 써 주세요."}]}
        doc, dropped = ex.build(guide, ai)
        self.assertFalse(any(c["params"].get("free") for c in doc["conditions"]))


class FasterRequest(unittest.TestCase):
    """2026-11-27: AI가 느린 이유(생각 토큰, 코드가 읽은 칸까지 다시 뽑기)를 줄인 요청."""

    def test_thinking_off_low_effort_and_smaller_cap(self):
        req = ex.build_request(GUIDE)
        self.assertEqual(req["thinking"], {"type": "disabled"})
        self.assertEqual(req["output_config"]["effort"], "medium")      # 생각은 끈 채로 한 단계 위 (docs/metrics.md)
        self.assertLessEqual(req["max_tokens"], 8000)
        self.assertNotIn("temperature", req)          # claude-haiku-5-5는 기본값이 아닌 temperature를 받지 않아요

    def test_fixed_fields_are_masked_for_the_ai_only(self):
        text = ex.build_request(REVU)["messages"][0]["content"]
        self.assertIn(ex.FIXED_MARK, text)
        self.assertNotIn("솔바람녹차, 녹차추천", text)           # 제목 키워드 칸은 코드가 읽어요
        self.assertNotIn("단독 촬영 필수", text)                  # 추가 안내사항(원고 밖)도 가려요
        self.assertIn("1. 아침마다 솔바람 녹차를 마신다는 내용.", text)   # 미션 본문은 AI가 읽어요
        self.assertIn(ex.FIXED_NOTE.strip(), text)
        gangnam = ex.masked(GANGNAM)
        self.assertNotIn("예약 시간을 지켜 주세요", gangnam)       # 리뷰 시 주의사항은 가리고
        self.assertNotIn("1. 메일링 안내", gangnam)               # NOTICE도 고정 문장이라 가려요 (2026-11-27)
        self.assertEqual(ex.masked(GUIDE), GUIDE)                  # 고정 칸이 없으면 그대로

    def test_ai_condition_quoting_the_mask_is_dropped_without_a_notice(self):
        ai = {"campaign_type": "체험", "conditions": [{"type": "judgment", "label": "가린 칸", "question": "x", "quote": ex.FIXED_MARK}]}
        doc, dropped = ex.build(REVU, ai)
        self.assertEqual([d["code"] for d in dropped], ["FIXED_FIELD"])
        self.assertFalse(any(c["label"] == ex.NOTICE_LABEL for c in doc["conditions"]))


class FormDetection(unittest.TestCase):
    """가이드 형식을 칸 이름으로 알아봐요. 못 알아보면 일반 가이드(None)로 점검해요 (2026-11-27)."""

    def test_each_form_and_general(self):
        sample2 = (ROOT_DIR / "samples" / "guide-sample-2.md").read_text(encoding="utf-8")
        general = (ROOT_DIR / "samples" / "guide-sample.md").read_text(encoding="utf-8")
        self.assertEqual([ex.detect_form(g) for g in (REVU, GANGNAM, sample2, general)], ["revu", "gangnam", "reviewplace", None])

    def test_reviewnote_by_banner_address_or_guide_words(self):
        """2026-11-27: 리뷰노트는 이름·공정위 배너 주소·"강조사항" 칸 중 두 가지로 알아봐요. 하나뿐이면 일반 가이드예요.
        고정 칸은 아직 몰라서 코드가 읽는 조건이 없어요 (지어낸 글)."""
        by_banner = "강조사항\n1. 교재 사진을 올려 주세요.\n공정위 배너: https://reviewnote.cloud/gongjeong/v1/example.png"
        by_words = "리뷰노트 캠페인 가이드\n강조사항\n1. 직접 써 본 느낌을 적어 주세요."
        self.assertEqual([ex.detect_form(g) for g in (by_banner, by_words)], ["reviewnote", "reviewnote"])
        self.assertIsNone(ex.detect_form("강조사항\n1. 사진을 올려 주세요."))
        doc = ex.build(by_words, {"campaign_type": None, "conditions": []})[0]
        self.assertEqual([c for c in doc["conditions"] if c["source"] == "rule"], [])

    def test_detection_survives_a_missing_field(self):
        self.assertEqual(ex.detect_form(REVU.replace("추가 안내사항", "그 밖의 안내")), "revu")
        self.assertEqual(ex.detect_form(GANGNAM.replace("NOTICE", "알림")), "gangnam")
        self.assertIsNone(ex.detect_form("가이드라인\n캠페인 미션\n아무 형식도 아닌 글"))      # 1:1 동점이면 일반 가이드

    def test_general_form_turns_off_fixed_fields(self):
        doc = ex.build(REVU, {"campaign_type": "체험", "conditions": []}, form=ex.GENERAL)[0]
        self.assertEqual(doc["conditions"], [])
        self.assertEqual(ex.masked(REVU, ex.GENERAL), REVU)


class BodyRule(unittest.TestCase):
    def test_wording_decides_each_any_sum_or_both(self):
        two = ["가나", "다라"]
        self.assertEqual(ex.body_rule("키워드를 본문에 총 5회 이상", two), "sum")
        self.assertEqual(ex.body_rule("각 키워드를 3회씩", two), "each")
        self.assertEqual(ex.body_rule("아래 키워드 중 1개를 3회", two), "any")
        self.assertEqual(ex.body_rule("키워드를 본문에 3회 이상", two), "both")
        self.assertEqual(ex.body_rule("키워드를 본문에 3회 이상", ["가나"]), "any")

    def test_ai_body_keywords_in_a_general_guide_show_both_readings(self):
        guide = "본문 키워드\n솔바람녹차, 아침차\n- 키워드를 본문에 3회 이상 넣어 주세요.\n"
        ai = {"campaign_type": "체험", "conditions": [{"type": "keyword_count", "label": "본문 키워드 3회", "keywords": ["솔바람녹차", "아침차"],
              "min": 3, "pick": "each", "quote": "- 키워드를 본문에 3회 이상 넣어 주세요."}]}
        (kw,) = ex.build(guide, ai)[0]["conditions"]
        self.assertEqual(kw["params"]["pick"], "both")
        self.assertIn("가이드 기준 확인 필요", kw["label"])


class FixedSentences(unittest.TestCase):
    """업체 양식의 고정 문장(강남맛집 스폰서 배너 최상단)은 코드가 읽고 AI에는 가려요 (2026-11-27)."""

    def test_banner_top_is_read_by_code(self):
        (banner,) = [c for c in rule_doc(GANGNAM)["conditions"] if c["label"] == ex.BANNER_LABEL]
        self.assertEqual((banner["type"], banner["countable"], banner["source"]), ("judgment", False, "rule"))
        self.assertEqual(banner["guide_quote"]["text"], "3. 블로그 글에는 스폰서 배너를 글 맨 위에 붙여 주세요.")

    def test_banner_and_the_sns_note_below_are_masked_for_the_ai(self):
        text = ex.masked(GANGNAM)
        self.assertNotIn("스폰서 배너", text)
        self.assertNotIn("블로그 밖 SNS", text)
        self.assertNotIn("1. 메일링 안내", text)                 # NOTICE의 다른 줄도 고정 문장이라 가려요 (2026-11-27)

    def test_gangnam_notice_is_outside_the_draft_and_the_banner_stays_a_condition(self):
        """강남맛집 "리뷰 시 주의사항"과 NOTICE 1~3·5는 코드가 원고 밖 조건 하나로, NOTICE의 스폰서 배너만 조건으로 남아요.
        AI에 보내는 사본에는 "리뷰 시 주의사항"부터 끝까지가 가림 표시 하나예요. AI는 부르지 않아요."""
        doc = rule_doc(GANGNAM)
        outside = [c for c in doc["conditions"] if c["type"] == "outside_draft"]
        self.assertEqual(len(outside), 1)
        self.assertIn("NOTICE", outside[0]["label"])
        self.assertEqual(outside[0]["guide_quote"]["text"], "리뷰 시 주의사항")          # 인용은 칸 이름, 가리는 범위는 칸 전체
        self.assertEqual([c["label"] for c in doc["conditions"] if c["label"] == ex.BANNER_LABEL], [ex.BANNER_LABEL])
        text = ex.masked(GANGNAM)
        self.assertTrue(text.endswith("5. 참고해 주세요.\n\n" + ex.FIXED_MARK))          # 가이드라인 다음은 가림 표시 하나

    def test_banner_condition_stays_hold_in_the_engine(self):
        from be import engine
        doc = rule_doc(GANGNAM)
        out = engine.check(doc, {"version": "0.3", "input_mode": "text", "counts_source": "user", "title": None,
                                 "draft_text": "본문이에요", "links": [], "hashtags": [], "media": []})
        (r,) = [r for c, r in zip(doc["conditions"], out["results"]) if c["label"] == ex.BANNER_LABEL]
        self.assertEqual(r["status"], "hold")

    def test_no_banner_line_no_condition(self):
        self.assertFalse(any(c["label"] == ex.BANNER_LABEL for c in rule_doc(REVU)["conditions"]))


class SameLineJudgment(unittest.TestCase):
    """2026-11-28: 셀 수 있는 조건이 이미 나온 가이드 줄에서 AI가 덧붙인 셀 수 없는 조건은 버려요 (지어낸 가이드)."""
    GUIDE = "사진은 15장 이상 올려 주세요.\n매장 분위기를 솔직하게 적어 주세요.\n"

    def build(self, *conds):
        return ex.build(self.GUIDE, {"campaign_type": "체험", "conditions": list(conds)})

    def test_judgment_on_a_countable_line_is_dropped_and_listed(self):
        doc, dropped = self.build(
            said("photo_count", "사진은 15장 이상 올려 주세요", "사진 15장", min=15),
            said("judgment", "사진은 15장 이상 올려 주세요", "사진을 성의 있게", question="사진을 성의 있게 올렸는가"),
            said("judgment", "매장 분위기를 솔직하게 적어 주세요", "솔직한 분위기", question="분위기를 솔직하게 적었는가"))
        self.assertEqual([(c["type"], c["label"]) for c in doc["conditions"]],
                         [("photo_count", "사진 15장"), ("judgment", "솔직한 분위기")])
        self.assertEqual([d["code"] for d in dropped], [ex.SAME_LINE_COUNTABLE])

    def test_without_a_countable_condition_on_the_line_nothing_is_dropped(self):
        doc, dropped = self.build(said("judgment", "사진은 15장 이상 올려 주세요", "사진을 성의 있게", question="성의 있게 올렸는가"))
        self.assertEqual(len(doc["conditions"]), 1)
        self.assertEqual(dropped, [])

    def test_switch_off_keeps_everything(self):
        with mock.patch.object(ex, "DROP_SAME_LINE_JUDGMENT", False):
            doc, _ = self.build(said("photo_count", "사진은 15장 이상 올려 주세요", "사진 15장", min=15),
                                said("judgment", "사진은 15장 이상 올려 주세요", "사진을 성의 있게", question="성의 있게 올렸는가"))
        self.assertEqual(len(doc["conditions"]), 2)


if __name__ == "__main__":
    unittest.main()
