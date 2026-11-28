"""규칙 엔진 테스트. 실행: python -m unittest be.test_engine

- 예시 1은 카티의 정답지(criteria/sample-answer-key.md) 숫자로 고정해요.
- 나머지 조건 type은 정답지가 없어서, 지어낸 짧은 글과 기대값을 여기에 직접 적었어요.
- API를 부르지 않아요.
"""
import contextlib
import io
import json
import re
import unittest
from pathlib import Path

from be import engine, phrases

ROOT = Path(__file__).resolve().parent.parent


def load(name: str) -> dict:
    return json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))


def req(text: str, **kw) -> dict:
    base = {
        "version": "0.3", "input_mode": "html", "counts_source": "parsed", "title": None,
        "draft_text": text, "photo_count": None, "video_count": None, "has_map": None,
        "links": [], "hashtags": [], "media": [],
    }
    base.update(kw)
    return base


def cond(kind: str, params: dict, countable: bool = True, cid: str = "c1") -> dict:
    return {"id": cid, "type": kind, "label": "조건", "countable": countable, "params": params,
            "guide_quote": {"text": "가이드", "start": 0, "end": 3}}


def run(conds, request) -> dict:
    conds = conds if isinstance(conds, list) else [conds]
    return engine.check({"version": "0.3", "conditions": conds}, request)


def one(kind: str, params: dict, request: dict, **kw) -> dict:
    return run(cond(kind, params, **kw), request)["results"][0]


def rule(out: dict, rule_id: str) -> dict:
    return next(p for p in out["principles"] if p["rule_id"] == rule_id)


def starts(r: dict) -> list[int]:
    return [s["start"] for s in r["draft_spans"]]


def cut(text: str, s: dict) -> str:
    return text[s["start"]:s["end"]]


class Sample1(unittest.TestCase):
    """samples/draft-sample.md + criteria/sample-answer-key.md"""

    @classmethod
    def setUpClass(cls):
        cls.conditions = load("conditions.example.json")
        cls.request = load("check-request.example.json")
        cls.out = engine.check(cls.conditions, cls.request)
        cls.by_id = {r["condition_id"]: r for r in cls.out["results"]}

    def test_answer_key_numbers(self):
        r = self.by_id
        self.assertEqual((r["c1"]["status"], r["c1"]["actual"], r["c1"]["expected"]), ("missing", 3, 5))
        self.assertEqual(starts(r["c1"]), [33, 478, 578])
        self.assertEqual((r["c2"]["status"], r["c2"]["actual"], r["c2"]["expected"]), ("missing", 414, 450))
        self.assertEqual((r["c3"]["status"], r["c3"]["actual"], r["c3"]["expected"]), ("missing", 8, 10))
        self.assertEqual((r["c4"]["status"], starts(r["c4"])), ("kept", [0]))
        self.assertEqual(r["c5"]["status"], "missing")
        self.assertEqual([r[c]["status"] for c in ("c6", "c7", "c8")], ["hold"] * 3)
        self.assertEqual(self.out["summary"], {"kept": 1, "missing": 4, "hold": 3})

    def test_answer_key_shortfall_and_space_count(self):
        self.assertIn("2회 더", self.by_id["c1"]["note"])
        self.assertIn("36자 더", self.by_id["c2"]["note"])
        self.assertIn("2장 더", self.by_id["c3"]["note"])
        self.assertEqual(engine.Draft(self.request).chars_with_spaces, 550)   # 정답지 메모: 공백 포함이면 550자 (줄바꿈 안 셈, 11/28)

    def test_same_as_contract_example(self):
        """상태·숫자·위치·근거가 contracts/check-result.example.json과 같아요. note 문장은 비교하지 않아요."""
        want = load("check-result.example.json")
        self.assertEqual(self.out["version"], want["version"])
        self.assertEqual(self.out["summary"], want["summary"])
        keys = ("condition_id", "label", "status", "expected", "actual", "unit", "draft_spans")
        self.assertEqual([{k: r[k] for k in keys} for r in self.out["results"]],
                         [{k: r[k] for k in keys} for r in want["results"]])
        keys = ("rule_id", "label", "status", "basis", "draft_spans")
        self.assertEqual([{k: p[k] for k in keys} for p in self.out["principles"]],
                         [{k: p[k] for k in keys} for p in want["principles"]])

    def test_same_result_three_times(self):
        again = [engine.check(self.conditions, self.request) for _ in range(3)]
        self.assertTrue(all(a == self.out for a in again))

    def test_output_matches_schema(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema가 없어요 (pip install jsonschema)")
        validator = Draft202012Validator(load("check-result.schema.json"))
        for out in (self.out, engine.check(load("conditions.example-2.json"), GOOD2)):
            self.assertEqual([e.message for e in validator.iter_errors(out)], [])


# 예시 2 가이드(바다숲 녹차 스틱)에 맞춰 지어낸 원고. 기대값은 Claude가 적은 것이고 정답지가 아니에요.
BODY2 = (
    "업체로부터 제품을 제공받아 작성한 글입니다.\n"
    "\n"
    "사무실에서 마시기 좋은 바다숲녹차를 일주일 마셔 봤어요 🍵\n"
    "[사진]\n"
    "바다숲녹차는 찬물에도 잘 녹아요. 바다숲녹차 한 포면 한 잔이 돼요.\n"
    "찻잎을 곱게 갈아 만든 가루예요.\n"
    "*제품이 아닌 원료에 관한 내용입니다\n"
    "[동영상]\n"
    "오후에 바다숲녹차를 타 두면 퇴근할 때까지 마셔요.\n"
    "\n"
    "#바다숲녹차 #간편녹차"
)
GOOD2 = req(BODY2, title="바다숲녹차 일주일 후기, 바다숲 녹차 맛은", photo_count=15, video_count=1,
            has_map=False, hashtags=["#바다숲녹차", "#간편녹차"],
            links=[{"url": "https://example.invalid/shop", "start": None}],
            media=[{"kind": "photo", "start": BODY2.index("[사진]")}, {"kind": "video", "start": BODY2.index("[동영상]")}])


class Sample2(unittest.TestCase):
    """contracts/conditions.example-2.json의 모든 type이 지어낸 원고에서 기대대로 나오는지."""

    @classmethod
    def setUpClass(cls):
        cls.out = engine.check(load("conditions.example-2.json"), GOOD2)
        cls.by_id = {r["condition_id"]: r for r in cls.out["results"]}

    def test_statuses(self):
        want = {
            "c1": "kept",      # 제목 키워드
            "c2": "kept",      # 태그에 키워드 1개 (pick: any)
            "c3": "kept",      # 본문 키워드 4번
            "c4": "kept",      # 대가성 문구 상단
            "c5": "kept",      # 제목 표기
            "c6": "kept",      # 금지어 없음
            "c7": "hold",      # 필수 문구는 있지만 "원료 문장 아래"인지는 판단 보류
            "c8": "kept",      # 필수 해시태그
            "c9": "hold",      # judgment
            "c10": "kept",     # 링크
            "c11": "missing",  # 1,000자
            "c12": "kept",     # 사진 15장
            "c13": "kept",     # 동영상
            "c14": "hold",     # 원고 밖 조건
        }
        self.assertEqual({k: r["status"] for k, r in self.by_id.items()}, want)

    def test_keyword_positions_after_emoji(self):
        r = self.by_id["c3"]
        self.assertEqual(r["actual"], 5)   # 본문 글 4번 + 본문 해시태그 1번 (2026-11-27부터 해시태그도 세요)
        self.assertEqual([cut(BODY2, s) for s in r["draft_spans"]], ["바다숲녹차"] * 5)
        self.assertIn("본문 글 4번 + 해시태그 1번", r["note"])

    def test_length_shows_both_counts_when_guide_is_silent(self):
        note = self.by_id["c11"]["note"]
        d = engine.Draft(GOOD2)
        self.assertEqual(self.by_id["c11"]["actual"], d.chars_with_spaces)     # 가이드가 안 정하면 공백 포함으로 판정
        self.assertIn(f"공백 포함 {d.chars_with_spaces}자(줄바꿈은 세지 않아요), 공백 제외 {d.chars}자", note)
        self.assertIn("공백 포함 기준으로 판정했어요 (가이드가 공백 기준을 정하지 않음)", note)

    def test_counts_say_where_the_number_came_from(self):
        self.assertIn("자동으로 센 사진 수", self.by_id["c12"]["note"])
        typed = engine.check(load("conditions.example-2.json"), dict(GOOD2, counts_source="user"))
        self.assertIn("입력한 사진 수", typed["results"][11]["note"])


class Rules(unittest.TestCase):
    def test_title_keyword(self):
        p = {"keywords": ["녹차스틱", "간편녹차"], "pick": "any"}
        r = one("title_keyword", p, req("본문", title="간편녹차 후기"))
        self.assertEqual((r["status"], r["draft_spans"]), ("kept", [{"start": 0, "end": 4, "field": "title"}]))
        self.assertEqual(one("title_keyword", p, req("본문", title="녹차 후기"))["status"], "missing")
        self.assertEqual(one("title_keyword", p, req("본문 간편녹차"))["status"], "hold")   # 제목을 모름
        self.assertEqual(one("title_keyword", dict(p, pick="each"), req("본문", title="간편녹차 후기"))["status"], "missing")

    def test_keyword_count_pick(self):
        text = "가가 나 가 나 가"
        any_ = one("keyword_count", {"keywords": ["가", "나"], "min": 4, "pick": "any", "scope": "body"}, req(text))
        self.assertEqual((any_["status"], any_["actual"], starts(any_)), ("kept", 4, [0, 1, 5, 9]))
        each = one("keyword_count", {"keywords": ["가", "나"], "min": 4, "pick": "each", "scope": "body"}, req(text))
        self.assertEqual((each["status"], each["actual"]), ("missing", 2))

    def test_keyword_does_not_overlap(self):
        r = one("keyword_count", {"keywords": ["아아"], "min": 1}, req("아아아아아"))
        self.assertEqual((r["actual"], starts(r)), (2, [0, 2]))

    def test_length_counts_body_only(self):
        text = "가 나\n[사진]\n다\n[지도]\n[동영상]\n라 😀"
        self.assertEqual(one("length", {"min": 5, "count_spaces": False}, req(text))["actual"], 5)
        self.assertEqual(one("length", {"min": 5, "count_spaces": True}, req(text))["actual"], len("가 나다라 😀"))   # 줄바꿈은 안 세요

    def test_counts_hold_when_unknown(self):
        self.assertEqual(one("photo_count", {"min": 3}, req("글"))["status"], "hold")
        self.assertEqual(one("video_count", {"min": 1}, req("글", video_count=0))["status"], "missing")
        self.assertEqual(one("map", {"position": None}, req("글"))["status"], "hold")

    def test_map_bottom(self):
        late = "가나다라마바사아자차\n[지도]\n\n#태그 #둘\n[사진]\n"
        early = "가나다라마바사아자차\n[지도]\n카"
        bottom = {"position": "bottom"}
        r = one("map", bottom, req(late, has_map=True, media=[{"kind": "map", "start": late.index("[지도]")}]))
        self.assertEqual((r["status"], cut(late, r["draft_spans"][0])), ("kept", "[지도]"))
        r = one("map", bottom, req(early, has_map=True, media=[{"kind": "map", "start": early.index("[지도]")}]))
        self.assertEqual((r["status"], cut(early, r["draft_spans"][0])), ("missing", "[지도]"))   # 뒤에 글 한 글자만 있어도
        self.assertEqual(one("map", bottom, req("글", input_mode="text", counts_source="user", has_map=True))["status"], "hold")
        self.assertEqual(one("map", bottom, req("글", has_map=False))["status"], "missing")

    def test_same_link_counts_once(self):
        url = "https://example.invalid/shop"
        text = f"구경은 {url} 에서 했어요."
        twice = [{"url": url, "start": text.index(url)}, {"url": url + "/", "start": None}]   # 글자 링크 + 카드
        r = one("link", {"min": 2, "url": None}, req(text, links=twice))
        self.assertEqual((r["status"], r["actual"]), ("missing", 1))
        self.assertEqual(one("link", {"min": 1, "url": None}, req(text, links=twice))["draft_spans"],
                         [{"start": text.index(url), "end": text.index(url) + len(url)}])
        self.assertEqual(one("link", {"min": 1, "url": url}, req("글", links=twice))["status"], "kept")
        self.assertEqual(one("link", {"min": 1, "url": "https://example.invalid/other"}, req("글", links=twice))["status"], "missing")

    def test_link_in_text_mode(self):
        text_only = dict(input_mode="text", counts_source="user")
        self.assertEqual(one("link", {"min": 1, "url": None}, req("글만 있어요", **text_only))["status"], "hold")
        self.assertEqual(one("link", {"min": 1, "url": None}, req("주소 https://example.invalid/a.", **text_only))["status"], "kept")

    def test_hashtag_pick(self):
        r = req("글 #녹차스틱에 #간편녹차", hashtags=["#녹차스틱에", "#간편녹차"])
        any_ = one("hashtag", {"tags": ["#녹차스틱", "#간편녹차"], "pick": "any"}, r)
        self.assertEqual((any_["status"], [cut(r["draft_text"], s) for s in any_["draft_spans"]]), ("kept", ["#간편녹차"]))
        self.assertEqual(one("hashtag", {"tags": ["#녹차스틱", "#간편녹차"], "pick": "each"}, r)["status"], "missing")
        self.assertEqual(one("hashtag", {"tags": ["#녹차스틱", "#간편녹차"]}, r)["status"], "missing")   # pick이 없으면 each

    def test_exact_phrase(self):
        p = {"allowed": "바다숲 녹차", "forbidden": ["바다숲 녹차 스틱"], "scope": "title"}
        bad = one("exact_phrase", p, req("본문", title="바다숲 녹차 스틱 후기"))
        self.assertEqual((bad["status"], bad["draft_spans"]), ("missing", [{"start": 0, "end": 9, "field": "title"}]))
        self.assertEqual(one("exact_phrase", p, req("본문", title="바다숲 녹차 후기"))["status"], "kept")
        self.assertEqual(one("exact_phrase", p, req("본문", title="녹차 후기"))["status"], "kept")   # 허용 표기가 없어도 지킴
        self.assertEqual(one("exact_phrase", p, req("본문"))["status"], "hold")

    def test_banned_terms_marks_words_that_only_contain_the_term(self):
        text = "효과가 좋아요. 효과적이에요. 역효과는 없어요."
        r = one("banned_terms", {"terms": ["효능", "효과"], "category": None, "scope": "body"}, req(text))
        self.assertEqual((r["status"], r["actual"], starts(r)), ("missing", 3, [0, 9, 18]))
        self.assertIn('그중 2곳은 다른 단어 안에 들어 있어요: "효과적이에요", "역효과는"', r["note"])
        plain = one("banned_terms", {"terms": ["효과"], "scope": "body"}, req("효과가 좋아요"))
        self.assertNotIn("다른 단어", plain["note"])
        self.assertEqual(one("banned_terms", {"terms": ["효과"], "scope": "body"}, req("좋아요"))["status"], "kept")
        self.assertEqual(one("banned_terms", {"terms": ["효과"]}, req("좋아요"))["status"], "hold")   # 제목을 모름
        self.assertEqual(one("banned_terms", {"terms": [], "category": "병명"}, req("글"), countable=False)["status"], "hold")

    def test_required_phrase(self):
        p = {"phrase": "*제품이 아닌 원료에 관한 내용입니다", "scope": "body"}
        self.assertEqual(one("required_phrase", p, req("찻잎이에요.\n*제품이 아닌 원료에 관한 내용입니다"))["status"], "kept")
        self.assertEqual(one("required_phrase", p, req("찻잎이에요."))["status"], "missing")
        after = one("required_phrase", dict(p, after="원료 특징 문장"), req("찻잎이에요.\n*제품이 아닌 원료에 관한 내용입니다"))
        self.assertEqual((after["status"], starts(after)), ("hold", [7]))

    def test_disclosure_first_paragraph_ends_at_blank_line(self):
        top = {"phrase": None, "position": "top"}
        first = "안녕하세요.\n제품을 제공받아 썼어요.\n\n본문이에요."
        r = one("disclosure", top, req(first))
        self.assertEqual((r["status"], cut(first, r["draft_spans"][0])), ("kept", "제품을 제공받아 썼어요."))
        self.assertIn("우리 기준", r["note"])
        late = "안녕하세요.\n\n본문이에요.\n제품을 제공받아 썼어요."
        self.assertEqual(one("disclosure", top, req(late, title="후기"))["status"], "missing")
        after_photo = "안녕하세요.\n[사진]\n제품을 제공받아 썼어요."
        self.assertEqual(one("disclosure", top, req(after_photo, title="후기"))["status"], "missing")
        photo_first = "[사진]\n\n제품을 제공받아 썼어요.\n\n본문이에요."
        self.assertEqual(one("disclosure", top, req(photo_first))["status"], "kept")

    def test_disclosure_in_title_counts(self):
        top = {"phrase": None, "position": "top"}
        r = one("disclosure", top, req("본문이에요.", title="[협찬] 녹차 후기"))
        self.assertEqual((r["status"], r["draft_spans"][0]["field"]), ("kept", "title"))
        self.assertEqual(one("disclosure", top, req("본문이에요.", title="녹차 후기"))["status"], "missing")
        self.assertEqual(one("disclosure", top, req("본문이에요."))["status"], "hold")   # 제목을 모름

    def test_disclosure_with_guide_phrase(self):
        p = {"phrase": "업체로부터 음료를 제공받아 작성한 글입니다", "position": "top"}
        other = one("disclosure", p, req("음료를 제공받아 썼어요.\n\n본문.", title="후기"))
        self.assertEqual(other["status"], "missing")
        self.assertIn("가이드 문구와 같지 않아요", other["note"])

    def test_needs_review_is_judged_and_flagged(self):
        r = one("photo_count", {"min": 5, "needs_review": True}, req("글", photo_count=3))
        self.assertEqual((r["status"], r["expected"], r["actual"]), ("missing", 5, 3))
        self.assertIn("조건표에서 확인", r["note"])
        self.assertNotIn("조건표에서 확인", one("photo_count", {"min": 5}, req("글", photo_count=3))["note"])

    def test_positions_are_capped_but_the_count_is_not(self):
        text = "가 " * 1000
        r = one("keyword_count", {"keywords": ["가"], "min": 1, "pick": "any", "scope": "body"}, req(text))
        self.assertEqual((r["actual"], len(r["draft_spans"]), starts(r)[:3]), (1000, engine.MAX_SPANS, [0, 2, 4]))
        self.assertIn(f"{engine.MAX_SPANS}곳만 표시", r["note"])
        few = one("keyword_count", {"keywords": ["가"], "min": 1, "pick": "any", "scope": "body"}, req("가 가"))
        self.assertNotIn("곳만 표시", few["note"])

    def test_conditions_that_cannot_be_counted_ask_the_blogger_to_check(self):
        """셀 수 없는 조건은 판단 보류로 두고, 결과마다 "이 조건은 직접 확인해 주세요"라고 알려요."""
        ask = engine.CHECK_YOURSELF
        text = "찻잎이에요.\n*안내 문구"
        holds = [
            one("judgment", {"question": "느낌이 있는가"}, req(text), countable=False),
            one("photo_count", {"min": 1, "subject": "매장 외관"}, req(text, photo_count=5), countable=False),
            one("banned_terms", {"terms": [], "category": "질병 이름"}, req(text), countable=False),
            one("outside_draft", {"what": "기간"}, req(text), countable=False),
            one("required_phrase", {"phrase": "*안내 문구", "scope": "body", "after": "찻잎 문장"}, req(text)),
        ]
        for r in holds:
            self.assertEqual(r["status"], "hold")
            self.assertIn(ask, r["note"])
        doc = {"version": "0.3", "campaign_type": "기자단", "conditions": []}
        self.assertIn(ask, rule(engine.check(doc, req(text)), "p6")["note"])
        for sample, request in (("conditions.example.json", load("check-request.example.json")), ("conditions.example-2.json", GOOD2)):
            conditions = load(sample)
            out = engine.check(conditions, request)
            for c, r in zip(conditions["conditions"], out["results"]):
                if not c["countable"]:
                    self.assertEqual((r["status"], ask in r["note"]), ("hold", True), c["id"])
        # 숫자를 몰라서 보류인 것은 "넣으면 판정해요"라고 해요 (직접 확인하라는 말이 아니에요)
        self.assertNotIn(ask, one("photo_count", {"min": 3}, req(text))["note"])

    def test_broken_params_become_hold(self):
        self.assertEqual(one("keyword_count", {"keywords": [], "min": 3}, req("글"))["status"], "hold")
        self.assertEqual(one("length", {"min": "1000"}, req("글"))["status"], "hold")
        self.assertEqual(one("keyword_count", {"keywords": ["가"], "min": 1, "scope": "어딘가"}, req("가"))["status"], "hold")
        self.assertEqual(one("새로운종류", {}, req("글"))["status"], "hold")


class FromCounter(unittest.TestCase):
    """감자님 be/counter.py·be/tests/test_counter.py(팀 저장소 PR #14)에서 가져온 규칙과 테스트."""

    def test_spacing_must_match_exactly(self):
        r = one("keyword_count", {"keywords": ["전포동 카페"], "min": 1}, req("전포동카페 전포동  카페"))
        self.assertEqual((r["status"], r["actual"]), ("missing", 0))

    def test_missing_min_is_hold_not_one(self):
        for kind, params in (("keyword_count", {"keywords": ["가"]}), ("length", {"count_spaces": False}),
                             ("photo_count", {}), ("video_count", {"min": None})):
            r = one(kind, params, req("가", photo_count=3, video_count=1))
            self.assertEqual((r["status"], r["note"]), ("hold", engine.NO_MIN), kind)


class RuleTable(unittest.TestCase):
    """2단계: 조건 종류마다 규칙 하나, 정적 분석은 원고 한 편에 0.1초 안."""

    def test_every_contract_type_has_a_rule(self):
        schema = load("conditions.schema.json")
        kinds = schema["properties"]["conditions"]["items"]["properties"]["type"]["enum"]
        self.assertEqual(set(kinds), set(engine.RULES))

    def test_new_type_needs_only_one_entry(self):
        engine.RULES["시험용"] = lambda c, p, d: engine.result(c, "kept", "규칙 하나로 동작해요")
        try:
            self.assertEqual(one("시험용", {}, req("글"))["status"], "kept")
        finally:
            del engine.RULES["시험용"]

    def test_static_check_is_under_100ms(self):
        import time
        para = "전포동 카페에 다녀왔어요. 녹차라떼가 맛있었고 https://example.invalid/a 주소도 있어요. #전포동카페\n[사진]\n대표사진 삭제\n"
        text = "체험단으로 제품을 제공받아 작성했어요.\n\n" + para * 60          # 약 6천 자, 사진 60장
        conds = [cond(k, p, cid=f"c{i}") for i, (k, p) in enumerate([
            ("title_keyword", {"keywords": ["전포동 카페"], "pick": "any"}),
            ("keyword_count", {"keywords": ["전포동 카페", "녹차라떼"], "min": 5, "pick": "any", "scope": "title_and_body"}),
            ("length", {"min": 1000, "count_spaces": None}),
            ("photo_count", {"min": 15}), ("video_count", {"min": 1}), ("link", {"min": 1, "url": None}),
            ("map", {"position": "bottom"}), ("hashtag", {"tags": ["#전포동카페"]}),
            ("exact_phrase", {"allowed": "전포동 카페", "forbidden": ["전포동카페"], "scope": "body"}),
            ("banned_terms", {"terms": ["효능", "최고"], "scope": "title_and_body"}),
            ("required_phrase", {"phrase": "제공받아", "scope": "body"}),
            ("disclosure", {"phrase": None, "position": "top"}),
            ("outside_draft", {"what": "기간"}), ("judgment", {"question": "비교 내용이 없는가"}),
        ])]
        request = req(text, title="전포동 카페 후기", photo_count=60, video_count=0, has_map=False,
                      hashtags=["#전포동카페"])
        run(conds, request)                      # 첫 실행(정규식 컴파일 등)은 빼고 재요
        start = time.perf_counter()
        out = run(conds, request)
        took = time.perf_counter() - start
        self.assertEqual(len(out["results"]), 14)
        self.assertLess(took, 0.1, f"정적 분석 {took:.3f}초")


class AnswerKeyRules(unittest.TestCase):
    """정답지 03~07의 "세는 규칙 메모"에서 정한 세 가지 (2026-11-26, 카티 결정)."""

    def test_body_hashtag_and_url_lines_are_counted(self):
        """글자 수 기준(2026-11-27): 본문 글 블록에 직접 쓴 해시태그 줄과 주소 줄도 세요. 자리 표시 줄은 빼요."""
        url = "https://example.invalid/shop"
        text = f"가나 다 {url}\n[사진]\n[동영상]\n[지도]\n{url}\n#태그 #둘"
        r = one("length", {"min": 1, "count_spaces": False}, req(text))
        self.assertEqual(r["actual"], len("가나다") + 2 * len(url) + len("#태그#둘"))
        self.assertEqual(one("link", {"min": 1, "url": None}, req(text))["actual"], 1)   # 같은 주소는 링크 1개

    def test_p3_ignores_photo_lines_between_sentences(self):
        """p3: 사이에 [사진] 줄이 있어도 이어진 두 문장으로 봐요."""
        kw = cond("keyword_count", {"keywords": ["녹차"], "min": 5, "pick": "any", "scope": "body"})
        split = rule(run(kw, req("오늘은 녹차 이야기예요.\n\n[사진]\n[사진]\n\n녹차는 물에 잘 녹아요.")), "p3")
        self.assertEqual(split["status"], "missing")
        self.assertIn("이어진 두 문장", split["note"])
        apart = rule(run(kw, req("오늘은 녹차 이야기예요.\n\n[사진]\n\n맛있어요.\n\n녹차는 물에 잘 녹아요.")), "p3")
        self.assertEqual(apart["status"], "kept")

    def test_keyword_inside_a_forbidden_form_is_still_counted(self):
        """키워드가 금지 표기 안에 들어 있어도("달무리 국수집" 안의 "달무리 국수") 그대로 세요."""
        text = "달무리 국수에 갔어요. 달무리 국수집은 조용해요."
        r = one("keyword_count", {"keywords": ["달무리 국수"], "min": 2, "pick": "any", "scope": "body"}, req(text))
        self.assertEqual((r["status"], r["actual"], starts(r)), ("kept", 2, [0, 13]))
        bad = one("exact_phrase", {"allowed": "달무리 국수", "forbidden": ["달무리 국수집"], "scope": "body"}, req(text))
        self.assertEqual((bad["status"], starts(bad)), ("missing", [13]))


class BannerDisclosure(unittest.TestCase):
    """2026-11-27: 대가성 표시를 맨 위 체험단 배너 그림으로도 판정해요 (요청의 banner_top, 화면이 서식에서 찾아요).
    배너도 문구도 없을 때만 "없음", 글만 붙여 넣어 그림을 못 보면 판단 보류로 안내해요."""
    TEXT = "교재를 한 달 써 봤어요.\n매일 조금씩 공부했어요."

    def p1(self, **kw):
        out = run([], req(self.TEXT, title="교재 후기", **kw))
        return next(p for p in out["principles"] if p["rule_id"] == "p1")

    def test_banner_only_without_words_is_kept(self):
        p = self.p1(banner_top=True, banner_count=1)
        self.assertEqual(p["status"], "kept")
        self.assertIn("대가성 표시 있음(맨 위 배너)", p["note"])

    def test_no_banner_and_no_words_is_missing(self):
        self.assertEqual(self.p1(banner_top=False, banner_count=0)["status"], "missing")
        self.assertEqual(self.p1()["status"], "missing")              # 서식인데 값이 없으면 배너 없음으로 봐요

    def test_text_only_paste_cannot_see_the_banner(self):
        p = self.p1(input_mode="text", counts_source="user", banner_top=None)
        self.assertEqual(p["status"], "hold")
        self.assertIn("대가성 문구를 찾지 못했어요. 배너 그림을 넣었다면 괜찮아요", p["note"])
        later = run([], req("교재를 써 봤어요.\n\n" * 5 + "제품을 제공받아 작성했어요.", title="교재 후기",
                            input_mode="text", counts_source="user"))
        p = next(p for p in later["principles"] if p["rule_id"] == "p1")
        self.assertEqual(p["status"], "missing")                       # 문구가 뒤쪽에 있는 것은 그대로 알려요
        self.assertIn("배너 그림을 넣었다면 괜찮아요", p["note"])

    def test_disclosure_condition_accepts_a_top_banner_unless_the_guide_names_the_words(self):
        plain = cond("disclosure", {"phrase": None, "position": "top"})
        self.assertEqual(one("disclosure", plain["params"], req(self.TEXT, title="교재 후기", banner_top=True))["status"], "kept")
        self.assertEqual(one("disclosure", plain["params"], req(self.TEXT, title="교재 후기", banner_top=False))["status"], "missing")
        unseen = one("disclosure", plain["params"], req(self.TEXT, title="교재 후기", input_mode="text", counts_source="user"))
        self.assertEqual(unseen["status"], "hold")
        named = {"phrase": "체험단으로 제공받았어요", "position": "top"}
        self.assertEqual(one("disclosure", named, req(self.TEXT, title="교재 후기", banner_top=True))["status"], "missing")


class Decisions(unittest.TestCase):
    """2026-11-26 카티 결정 (정답지 03~07을 재고 나서 정한 세는 규칙). 1번은 2026-11-27에 바뀌었어요."""

    def test_1_keyword_inside_a_body_hashtag_is_counted(self):
        """2026-11-27 카티 결정으로 바뀜: 본문에 직접 쓴 #해시태그 안의 키워드도 세요 (예전: 뺐어요).
        "본문 글 N번 + 해시태그 M번"으로 나눠 보여 주고, 해시태그로 기준을 채우면 안내만 붙여요 (판정은 지킴)."""
        text = "솔바람 차를 마셨어요. 솔바람 좋아요.\n\n#솔바람 #아침솔바람차"
        r = one("keyword_count", {"keywords": ["솔바람"], "min": 3, "pick": "any", "scope": "body"}, req(text))
        self.assertEqual((r["status"], r["actual"], starts(r)), ("kept", 4, [0, 13, 24, 31]))
        self.assertIn("본문 글 2번 + 해시태그 2번", r["note"])
        self.assertIn("해시태그로 기준을 채웠어요. 본문 글에도 넣으면 더 자연스러워요", r["note"])
        only = one("keyword_count", {"keywords": ["솔바람"], "min": 1, "scope": "body"}, req("차를 마셨어요.\n#솔바람"))
        self.assertEqual(only["status"], "kept")
        self.assertIn("해시태그로만 채웠어요", only["note"])
        plain = one("keyword_count", {"keywords": ["솔바람"], "min": 2, "scope": "body"}, req(text))
        self.assertNotIn("해시태그로", plain["note"])         # 본문 글만으로 기준을 넘으면 안내하지 않아요
        many = one("keyword_count", {"keywords": ["솔바람", "녹차"], "min": 3, "scope": "body"}, req(text))
        self.assertIn('"솔바람" 4회(본문 글 2번 + 해시태그 2번)', many["note"])

    def test_2_tied_keywords_all_show_their_positions(self):
        text = "가가 나나 가가 나나 다다"
        r = one("keyword_count", {"keywords": ["가가", "나나", "다다"], "min": 3, "pick": "any", "scope": "body"}, req(text))
        self.assertEqual((r["status"], r["actual"], starts(r)), ("missing", 2, [0, 3, 6, 9]))
        self.assertIn('"가가", "나나" 각 2회', r["note"])
        none = one("keyword_count", {"keywords": ["라라", "마마"], "min": 1, "pick": "any", "scope": "body"}, req(text))
        self.assertEqual((none["actual"], none["draft_spans"]), (0, []))

    def test_3_sentence_position_includes_the_final_period(self):
        text = "안녕하세요.\n\n본문이에요.\n\n본 글은 제품을 제공받아 썼습니다. 끝!"
        r = one("disclosure", {"phrase": None, "position": "top"}, req(text, title="후기"))
        s = r["draft_spans"][0]
        self.assertEqual((r["status"], cut(text, s), text[s["end"]]), ("missing", "본 글은 제품을 제공받아 썼습니다.", " "))
        guide = one("disclosure", {"phrase": "제품을 제공받아", "position": None}, req(text))
        self.assertEqual(cut(text, guide["draft_spans"][0]), "제품을 제공받아")      # 가이드 문구는 문구 자리 그대로

    def test_4_map_is_at_the_bottom_when_no_text_paragraph_follows(self):
        def judge(text):
            media = [{"kind": "map", "start": text.index("[지도]")}]
            return one("map", {"position": "bottom"}, req(text, has_map=True, media=media))["status"]
        self.assertEqual(judge("짧은 글.\n[지도]\n\n#태그 #둘"), "kept")                # 글 앞쪽이어도 뒤에 글이 없으면 하단
        self.assertEqual(judge("아주 긴 글 " * 50 + "\n[지도]\n\n감사합니다."), "missing")   # 글 뒤쪽이어도 뒤에 글이 있으면 아님
        self.assertEqual(judge("글.\n[지도]\nhttps://example.invalid/a\n[사진]\n#태그"), "kept")   # 주소 줄, 사진 줄, 해시태그 줄은 글이 아님
        self.assertEqual(judge("글.\n[지도]\n주소는 https://example.invalid/a 예요"), "missing")       # 주소가 든 문장은 글

    def test_5_press_campaign_p6_stays_on_hold(self):
        doc = {"version": "0.3", "campaign_type": "기자단", "conditions": []}
        self.assertEqual(rule(engine.check(doc, req("자료를 바탕으로 썼어요.")), "p6")["status"], "hold")

    def test_6_summary_leaves_out_conditions_outside_the_draft(self):
        conds = [cond("photo_count", {"min": 1}, cid="c1"),
                 cond("outside_draft", {"what": "기간"}, countable=False, cid="c2"),
                 cond("judgment", {"question": "느낌이 있는가"}, countable=False, cid="c3")]
        out = run(conds, req("글", photo_count=2))
        self.assertEqual(out["summary"], {"kept": 1, "missing": 0, "hold": 1})
        self.assertEqual([r["status"] for r in out["results"]], ["kept", "hold", "hold"])   # 결과 목록에는 그대로 있어요


class Principles(unittest.TestCase):
    def test_p1(self):
        late = req("안녕하세요.\n\n본문이에요.\n\n제품을 제공받아 썼어요.", title="후기")
        p = rule(run([], late), "p1")
        self.assertEqual((p["status"], cut(late["draft_text"], p["draft_spans"][0])), ("missing", "제품을 제공받아 썼어요."))
        self.assertIn("불리하다고 밝힌 패턴", p["note"])
        self.assertIn("우리 기준", p["note"])
        self.assertEqual(rule(run([], req("본문이에요.", title="후기")), "p1")["status"], "missing")
        self.assertEqual(rule(run([], req("본문이에요.")), "p1")["status"], "hold")
        self.assertEqual(rule(run([], req("본문이에요.", title="협찬 후기")), "p1")["status"], "kept")

    def test_p2(self):
        text = "소정의 수수료를 지급받을수 있음.\n\n본문이에요."
        p = rule(run([], req(text)), "p2")
        self.assertEqual(p["status"], "missing")
        self.assertIn("지급받을수 있", [cut(text, s) for s in p["draft_spans"]])
        self.assertEqual(rule(run([], req("제품을 제공받아 썼어요.")), "p2")["status"], "kept")

    def test_p3(self):
        kw = cond("keyword_count", {"keywords": ["녹차"], "min": 1, "pick": "any", "scope": "body"})
        many = rule(run(kw, req("녹차 좋아요.\n\n맛있어요.\n\n녹차 또.\n\n그래요.\n\n녹차 끝.")), "p3")
        self.assertEqual((many["status"], len(many["draft_spans"])), ("missing", 3))
        self.assertIn("2배", many["note"])
        kw5 = cond("keyword_count", {"keywords": ["녹차"], "min": 5, "pick": "any", "scope": "body"})
        twice = rule(run(kw5, req("녹차 좋아요. 녹차 맛있어요.")), "p3")
        self.assertEqual(twice["status"], "missing")
        self.assertIn("이어진 두 문장", twice["note"])
        self.assertEqual(rule(run(kw5, req("녹차 좋아요. 맛있어요. 녹차 또.")), "p3")["status"], "kept")
        self.assertEqual(rule(run([], req("녹차 좋아요.")), "p3")["status"], "hold")
        # 해시태그 안의 키워드는 반복으로 치지 않아요
        tagged = rule(run(kw5, req("녹차가 맛있어요.\n\n#녹차 #차", hashtags=["#녹차", "#차"])), "p3")
        self.assertEqual((tagged["status"], tagged["draft_spans"]), ("kept", []))
        self.assertIn('"녹차" 1회', tagged["note"])

    def test_p4_counts_addresses_once_and_skips_required_links(self):
        def links(n):
            return [{"url": f"https://example.invalid/{i}", "start": None} for i in range(n)]
        need1 = cond("link", {"min": 1, "url": None})
        self.assertEqual(rule(run(need1, req("글", links=links(4))), "p4")["status"], "kept")       # 필수 1 + 밖 3
        self.assertEqual(rule(run(need1, req("글", links=links(5))), "p4")["status"], "missing")    # 필수 1 + 밖 4
        self.assertEqual(rule(run(need1, req("글", links=links(4) + links(4))), "p4")["status"], "kept")   # 같은 주소
        self.assertEqual(rule(run([], req("글", links=links(4))), "p4")["status"], "missing")

    def test_p5(self):
        self.assertEqual(rule(run([], req("가" * 59, photo_count=2)), "p5")["status"], "missing")
        self.assertEqual(rule(run([], req("가" * 60, photo_count=2)), "p5")["status"], "kept")
        self.assertEqual(rule(run([], req("가")), "p5")["status"], "hold")
        self.assertEqual(rule(run([], req("가", photo_count=0)), "p5")["status"], "kept")

    def test_p6_only_for_press_campaigns(self):
        def ids(campaign_type):
            doc = {"version": "0.3", "campaign_type": campaign_type, "conditions": []}
            return [p["rule_id"] for p in engine.check(doc, req("글"))["principles"]]
        self.assertEqual(ids("기자단"), ["p1", "p2", "p3", "p4", "p5", "p6"])
        self.assertEqual(ids("체험"), ["p1", "p2", "p3", "p4", "p5"])
        self.assertEqual(ids(None), ["p1", "p2", "p3", "p4", "p5"])
        doc = {"version": "0.3", "campaign_type": "기자단", "conditions": []}
        self.assertEqual(rule(engine.check(doc, req("글")), "p6")["status"], "hold")

    def test_no_guarantee_wording(self):
        """결과 문구에 보장 표현이 없어요."""
        outs = [engine.check(load("conditions.example.json"), load("check-request.example.json")),
                engine.check(load("conditions.example-2.json"), GOOD2)]
        text = json.dumps(outs, ensure_ascii=False)
        for banned in ("상위노출", "노출 보장", "준수 보장", "보장돼", "보장해"):
            self.assertNotIn(banned, text)


class EditorPaste(unittest.TestCase):
    """네이버 글쓰기 화면에서 본문을 복사해 붙여 넣은 원고: 편집 화면 줄과 숨은 문자가 섞여 와요."""

    # 맨 앞과 맨 뒤에 U+FEFF, 줄 끝은 \r\n. 사진 한 장에 편집 화면 줄 세 개가 붙어 있어요.
    PASTE = "﻿\r\nㅇㅇㅇㅇ\r\n대표사진 삭제\r\nAI 활용 설정\r\n사진 설명을 입력하세요.\r\ndddd\r\n﻿"

    def both(self):
        """\\r\\n인 것, \\n인 것, 숨은 문자가 따로 한 줄이 아니라 글에 붙어 온 것."""
        glued = "﻿ㅇㅇㅇㅇ\r\n대표사진 삭제\r\nAI 활용 설정\r\n사진 설명을 입력하세요.\r\ndddd﻿"
        return [self.PASTE, self.PASTE.replace("\r\n", "\n"), glued]

    def test_nfd_hangul_is_counted_as_nfc_and_spans_point_to_the_original(self):
        """자모가 나뉜 한글(NFD, 맥에서 복사할 때 등)도 같은 글자 수·키워드 수. 위치는 받은 원고 그대로예요."""
        import unicodedata
        nfc_text = "녹차 후기예요.\r\n녹차라떼와 녹차.\n[지도]\n#녹차"
        # 화면이 넣는 [지도] 같은 자리 표시 줄은 NFC 그대로이고, 블로거가 쓴 글만 NFD예요
        lines = nfc_text.split("\n")
        nfd = "\n".join(l if l in engine.MARKS else unicodedata.normalize("NFD", l) for l in lines)
        self.assertNotEqual(len(nfd), len(nfc_text))
        title = unicodedata.normalize("NFD", "녹차 후기")
        map_at = nfd.index("[지도]")
        conds = [cond("keyword_count", {"keywords": ["녹차"], "min": 3, "scope": "title_and_body"}, cid="k"),
                 cond("length", {"min": 1, "count_spaces": False}, cid="l"),
                 cond("map", {"position": "bottom"}, cid="m")]
        a = run(conds, req(nfc_text, title="녹차 후기", has_map=True, media=[{"kind": "map", "start": nfc_text.index("[지도]")}]))
        b = run(conds, req(nfd, title=title, has_map=True, media=[{"kind": "map", "start": map_at}]))
        for x, y in zip(a["results"], b["results"]):
            self.assertEqual((x["status"], x["actual"]), (y["status"], y["actual"]), x["condition_id"])
        k = b["results"][0]
        self.assertEqual(k["actual"], 5)     # 제목 1 + 본문 글 3 + 본문 해시태그 1
        for s in k["draft_spans"]:
            src = title if s.get("field") == "title" else nfd
            self.assertEqual(unicodedata.normalize("NFC", src[s["start"]:s["end"]]), "녹차")
        self.assertEqual(b["results"][2]["draft_spans"], [{"start": map_at, "end": map_at + 4}])

    def test_nfd_link_span_shared_by_two_results_is_mapped_once(self):
        """같은 링크 위치가 조건 두 개와 p4에 같이 들어가도 원래 위치로 한 번만 바꿔요."""
        import unicodedata
        url = "https://example.invalid/a"
        nfd = unicodedata.normalize("NFD", "녹차 후기 녹차 후기 ") + url
        links = [{"url": url, "start": nfd.index(url)}] + [{"url": f"https://example.invalid/{i}", "start": None} for i in range(5)]
        conds = [cond("link", {"min": 1, "url": None}, cid="l1"), cond("link", {"min": 1, "url": None}, cid="l2")]
        out = run(conds, req(nfd, links=links))
        spans = [s for r in out["results"] + out["principles"] for s in r["draft_spans"]]
        self.assertGreaterEqual(len(spans), 3)
        for s in spans:
            self.assertEqual(nfd[s["start"]:s["end"]], url)

    def test_editor_lines_hidden_characters_and_cr_are_not_counted(self):
        for text in self.both():
            without = one("length", {"min": 1, "count_spaces": False}, req(text))
            self.assertEqual(without["actual"], len("ㅇㅇㅇㅇdddd"))
            self.assertIn("편집 화면 줄 3개", without["note"])
            self.assertEqual(one("length", {"min": 1, "count_spaces": True}, req(text))["actual"], len("ㅇㅇㅇㅇdddd"))

    def test_words_inside_editor_lines_are_not_found(self):
        for text in self.both():
            r = one("keyword_count", {"keywords": ["사진"], "min": 1}, req(text))
            self.assertEqual((r["status"], r["actual"], r["draft_spans"]), ("missing", 0, []))
            self.assertEqual(one("banned_terms", {"terms": ["설정"], "category": None, "scope": "body"}, req(text))["status"], "kept")

    def test_positions_point_into_the_pasted_text_as_it_came(self):
        for text in self.both():
            r = one("keyword_count", {"keywords": ["dddd"], "min": 1}, req(text))
            self.assertEqual([cut(text, s) for s in r["draft_spans"]], ["dddd"])

    def test_only_lines_on_the_list_are_left_out(self):
        text = "대표사진 삭제함\nAI 활용 설정 방법\n본문"
        r = one("length", {"min": 1, "count_spaces": False}, req(text))
        self.assertEqual(r["actual"], len("대표사진삭제함AI활용설정방법본문"))
        self.assertNotIn("편집 화면 줄", r["note"])
        self.assertEqual(one("keyword_count", {"keywords": ["사진"], "min": 1}, req(text))["actual"], 1)
        self.assertEqual(one("photo_count", {"min": 1}, req(text))["status"], "hold")

    def test_hidden_characters_next_to_text(self):
        text = "​대표사진 설정​\n﻿본문​이에요 ⁠끝"
        self.assertEqual(one("length", {"min": 1, "count_spaces": False}, req(text))["actual"], len("본문이에요끝"))
        self.assertEqual(one("length", {"min": 1, "count_spaces": True}, req(text))["actual"], len("본문이에요 끝"))
        r = one("keyword_count", {"keywords": ["본문"], "min": 1}, req(text))
        self.assertEqual([cut(text, s) for s in r["draft_spans"]], ["본문"])
        # 낱말 가운데에 숨은 문자가 끼어 있으면 지금처럼 다른 낱말로 봐요 (새로 찾아 주지 않아요)
        self.assertEqual(one("keyword_count", {"keywords": ["본문이에요"], "min": 1}, req(text))["actual"], 0)

    def test_photo_count_uses_editor_lines_only_when_no_number_was_given(self):
        text = self.PASTE
        seen = one("photo_count", {"min": 1}, req(text, input_mode="text", counts_source="user"))
        self.assertEqual((seen["status"], seen["actual"]), ("kept", 1))
        self.assertIn("\"대표사진\" 줄로 센", seen["note"])
        self.assertEqual(one("photo_count", {"min": 2}, req(text))["status"], "missing")
        self.assertEqual(one("video_count", {"min": 1}, req(text))["status"], "hold")      # 동영상은 줄로 세지 않아요

        typed = one("photo_count", {"min": 3}, req(text, input_mode="text", counts_source="user", photo_count=3))
        self.assertEqual((typed["status"], typed["actual"]), ("kept", 3))                  # 입력한 수가 먼저예요
        self.assertIn("입력한 사진 수 기준", typed["note"])
        self.assertIn("서로 달라요", typed["note"])
        same = one("photo_count", {"min": 1}, req(text, input_mode="text", counts_source="user", photo_count=1))
        self.assertNotIn("달라요", same["note"])

    def test_two_photos_make_two(self):
        text = "글\n대표사진 삭제\nAI 활용 설정\n내가 쓴 사진 설명\n글\n대표사진 설정\nAI 활용 설정\n사진 설명을 입력하세요."
        self.assertEqual(one("photo_count", {"min": 2}, req(text))["actual"], 2)
        self.assertEqual(one("length", {"min": 1, "count_spaces": False}, req(text))["actual"], len("글내가쓴사진설명글"))

    def test_first_paragraph_skips_a_hidden_first_line_and_ends_at_a_photo(self):
        top = {"phrase": None, "position": "top"}
        hidden_first = "﻿\r\n제품을 제공받아 썼어요.\r\n\r\n본문이에요."
        r = one("disclosure", top, req(hidden_first))
        self.assertEqual((r["status"], cut(hidden_first, r["draft_spans"][0])), ("kept", "제품을 제공받아 썼어요."))
        after_photo = "안녕하세요.\n대표사진 삭제\nAI 활용 설정\n사진 설명을 입력하세요.\n제품을 제공받아 썼어요."
        self.assertEqual(one("disclosure", top, req(after_photo, title="후기"))["status"], "missing")   # [사진] 줄 뒤와 같아요

    def test_text_without_editor_lines_says_nothing_about_them(self):
        out = engine.check(load("conditions.example.json"), load("check-request.example.json"))
        for r in out["results"]:
            self.assertNotIn("편집 화면", r["note"])
            self.assertNotIn("대표사진", r["note"])


class Privacy(unittest.TestCase):
    def test_engine_prints_and_logs_nothing(self):
        """엔진은 받은 가이드·원고 글을 화면이나 로그에 찍지 않아요."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), self.assertNoLogs(level="DEBUG"):
            engine.check(load("conditions.example.json"), load("check-request.example.json"))
            engine.check(load("conditions.example-2.json"), GOOD2)
            run(cond("length", {"min": "깨진 값"}), req("글"))
        self.assertEqual((out.getvalue(), err.getvalue()), ("", ""))

    def test_engine_source_has_no_output_or_file_calls(self):
        for module in (engine, phrases):
            source = Path(module.__file__).read_text(encoding="utf-8")
            for call in ("print(", "logging", "open(", "write_text(", "sys.stdout", "sys.stderr"):
                self.assertNotIn(call, source, f"{Path(module.__file__).name}에 {call}")



class ViewerLookAlikes(unittest.TestCase):
    """보기 화면 줄과 닮은 본문 문장은 빼지 않아요."""

    def test_citation_and_likes_sentences_in_the_body_stay(self):
        text = "녹차 이야기예요.\n[출처] 네이버 지식백과\n공감 가는 댓글이 많았어요."
        self.assertIsNone(engine.guess_title(text))
        self.assertEqual(engine.Draft(req(text)).viewer_lines, 0)
        self.assertEqual(engine.guess_title(text + "\n[출처] 녹차 후기|작성자 가나다"), "녹차 후기")


if __name__ == "__main__":
    unittest.main()


class KeywordGuide(unittest.TestCase):
    """7-2: 내 원고만 보는 키워드 안내 (외부 데이터 없음). 판정 상태는 바꾸지 않고 note에만 안내해요."""

    def test_title_keyword_front_or_back_is_a_note_only(self):
        front = one("title_keyword", {"keywords": ["녹차"]}, req("본문", title="녹차 스틱 한 달 후기"))
        back = one("title_keyword", {"keywords": ["녹차"]}, req("본문", title="한 달 동안 마셔 본 후기 녹차"))
        self.assertEqual((front["status"], back["status"]), ("kept", "kept"))
        self.assertIn("제목 앞쪽에 있어요", front["note"])
        self.assertIn("앞쪽에 둘지 확인해 보세요", back["note"])

    def test_body_keyword_in_first_part_or_not(self):
        early = one("keyword_count", {"keywords": ["녹차"], "min": 1}, req("녹차를 마셨어요.\n" + "가" * 400))
        late = one("keyword_count", {"keywords": ["녹차"], "min": 1}, req("가" * 400 + "\n녹차를 마셨어요."))
        self.assertEqual((early["status"], late["status"]), ("kept", "kept"))
        self.assertIn("글 앞부분(본문 앞 300자)에 키워드가 나와요", early["note"])
        self.assertIn("앞부분(본문 앞 300자)에는 키워드가 없어요. 확인해 보세요", late["note"])
        none = one("keyword_count", {"keywords": ["녹차"], "min": 1}, req("가" * 50))
        self.assertNotIn("앞부분", none["note"])          # 한 번도 없으면 위치 안내는 하지 않아요

    def test_repeat_warning_uses_the_official_sentence_and_no_number_claim(self):
        text = "녹차를 마셨어요. 오늘은 날이 맑아요. " * 4
        p = rule(run(cond("keyword_count", {"keywords": ["녹차"], "min": 1}), req(text)), "p3")
        self.assertEqual(p["status"], "missing")
        self.assertIn("네이버는 관련 없는 키워드를 억지로 넣지 말라고 안내해요. 확인해 보세요", p["note"])
        self.assertIn("억지로 끼워 넣지 마세요", p["basis"])
        self.assertNotIn("반복적인 키워드 나열", p["note"] + p["basis"])

    def test_repeat_factor_comes_from_a_setting(self):
        import os
        from unittest import mock
        for value, want in (("5", 5), ("0", 2), ("abc", 2), ("", 2)):
            with mock.patch.dict(os.environ, {"PROMPATCH_KEYWORD_REPEAT_FACTOR": value}):
                self.assertEqual(engine._setting("PROMPATCH_KEYWORD_REPEAT_FACTOR", 2), want)
        text = "녹차 하나. 다른 문장. 녹차 둘. 다른 문장. 녹차 셋. 다른 문장."
        conds = cond("keyword_count", {"keywords": ["녹차"], "min": 1})
        self.assertEqual(rule(run(conds, req(text)), "p3")["status"], "missing")      # 3회 > 1회 × 2
        with mock.patch.object(engine, "KEYWORD_REPEAT_FACTOR", 3):
            self.assertEqual(rule(run(conds, req(text)), "p3")["status"], "kept")     # 3회 ≤ 1회 × 3


# 10단계: 보기 화면에서 복사한 글 (지어낸 예시. 실제 글의 모양만 따랐어요)
VIEWER = "\n".join([
    "일상 기록",                                  # 카테고리
    "솔바람 녹차 한 달 마셔 본 후기 | 녹차추천",          # 제목
    "",
    "프로파일",
    " 가나다 ・ 2026. 1. 2. 10:00",
    "URL 복사  이웃추가 ",
    "본문 기타 기능",
    "",
    "이 글은 업체로부터 제품을 제공받아 작성했어요.",
    "\u200b",
    "녹차를 매일 마셨어요.\r",
    "",
    "https://example.invalid/item",
    "",
    "",
    "솔바람 녹차 30포 : 솔바람상회",
    "[솔바람상회] 녹차 전문 브랜드",
    "",
    "example.invalid",
    "",
    "접기/펴기",
    "녹차 우리는 영상 (1)",
    "Previous imageNext image",
    "녹차 향이 좋았어요.",
    "#녹차 #녹차추천",
    "저작자 명시 필수 영리적 사용 불가 내용 변경 불가",
    "태그",
    "#녹차",
    "#녹차추천",
    "  공감 3  이 글에 공감한 블로거 열고 닫기 댓글 쓰기  이 글에 댓글 단 블로거 열고 닫기",
    "[출처] 솔바람 녹차 한 달 마셔 본 후기 | 녹차추천|작성자 가나다",
])


EDITOR_TEXT = "\n".join([          # 글쓰기 화면에서 글만 복사한 모양 (지어낸 글, samples/editor/와 같은 블록 순서)
    "오늘은 시험맛집에 다녀왔어요.",
    "대표",
    "사진 삭제",
    "AI 활용 설정",
    "사진 설명을 입력하세요.",
    "이전 이미지다음 이미지",
    "가운데 정렬",
    "00:03",
    "영상제목입니다",
    "영상제목입니다",
    "대표",
    "AI 활용 설정",
    "동영상 설명을 입력하세요.",
    "주차는 근처에 하면 돼요.",
    "시험맛집 예시점",
    "서울특별시 예시구 예시로 1",
    "https://www.naver.com",
    "이미지 썸네일 삭제",
    "네이버",
    "네이버 메인에서 다양한 정보와 유용한 컨텐츠를 만나 보세요",
    "www.naver.com",
    "주소는 서울특별시 예시구 예시로 1이에요.",
    "10:00",
    "가게는 10시에 열어요.",
])


class EditorTextPaste(unittest.TestCase):
    """2026-11-27: 글쓰기 화면 복사에서만 나오는 잡음 줄. 단추 글자는 줄 전체가 같을 때 어디서나 빼고,
    동영상 제목·링크 카드 설명·지도 장소 이름과 주소는 글만 붙여 넣었을 때만 빼요(서식이 있으면 구조로 이미 빠져요)."""

    def test_editor_block_lines_are_not_counted_in_text_mode(self):
        d = engine.Draft(req(EDITOR_TEXT, input_mode="text", counts_source="user"))
        kept = ["오늘은 시험맛집에 다녀왔어요.", "주차는 근처에 하면 돼요.", "https://www.naver.com",
                "주소는 서울특별시 예시구 예시로 1이에요.", "10:00", "가게는 10시에 열어요."]
        self.assertEqual(d.chars, len(re.sub(r"\s", "", "".join(kept))))
        self.assertEqual(d.chars_with_spaces, len("".join(kept)))         # 줄바꿈은 안 세요 (2026-11-28)
        # 링크 카드 설명은 보기 화면 규칙(주소 줄 → 카드 글 → 도메인 줄)이 먼저 잡아서 보기 화면 줄로 세어요
        self.assertEqual(d.editor_lines + d.viewer_lines, len(EDITOR_TEXT.split("\n")) - len(kept))

    def test_only_button_lines_are_dropped_when_html_was_read(self):
        """서식으로 읽은 원고에는 블로거가 본문에 직접 쓴 장소 이름·주소 줄이 있을 수 있어서 그대로 세요."""
        text = "가게 소개예요.\n시험맛집 예시점\n서울특별시 예시구 예시로 1\n대표\n이전 이미지"
        d = engine.Draft(req(text))
        self.assertEqual(d.chars_with_spaces, len("가게 소개예요.시험맛집 예시점서울특별시 예시구 예시로 1"))

    def test_lone_time_line_without_video_buttons_stays(self):
        self.assertEqual(engine.editor_skip(["12:30", "만나기로 했어요."]), set())


MOBILE_BODY = [                    # 블로거가 쓴 본문 줄 (지어낸 글)
    "솔바람 찻집에 다녀왔어요. 창가 자리가 좋았어요.",
    "주차는 근처 공영주차장을 이용하면 돼요.",
    "메뉴판은 아래에서 볼 수 있어요.",
    "https://example.com/menu",
    "예약은 전화로 했어요.",
    "#솔바람찻집 #녹차맛집",
]
MOBILE = "\n".join([               # 모바일 보기 화면에서 글만 복사한 모양 (지어낸 글, 실제 모바일 화면의 블록 순서를 따름)
    "[서울 종로] 솔바람 찻집 녹차 후기", "", "프로필", "가나다", "2026. 11. 9. 21:40", "", " 이웃추가본문 기타 기능", "",
    "솔바람 찻집 종로점", "", "매일 11:00 - 21:30", "", "L.O 라스트오더", "", "근처 공영주차장 이용 시 1시간 무료", "", "50m", "",
    "© NAVER Corp.", "솔바람 찻집 종로점", "서울특별시 종로구 예시로 1", "", "예약", "방문자 사진 보기", "", "이 장소의 다른 글", "",
    MOBILE_BODY[0], "", "", "00:02", "솔바람 찻집", "재생", "4", "좋아요", "0", "", "솔바람 찻집", "",
    MOBILE_BODY[1], "", MOBILE_BODY[2], "",
    "솔바람 녹차 세트 - 솔바람상회", "솔바람 녹차 세트 12,000원 바로 사기 상품 설명 보기", "", "example.com", "",
    MOBILE_BODY[3], "", MOBILE_BODY[4], "", MOBILE_BODY[5], "", "",
    "#솔바람찻집", "#녹차맛집", "#종로카페", "+3",
])


class MobileViewerPaste(unittest.TestCase):
    """2026-11-27: 모바일 보기 화면에서 글만 복사한 모양. 머리("프로필"과 따로 오는 작성자·날짜 줄), 지도 블록,
    동영상 블록, 상품·링크 카드, "태그" 머리 줄 없는 태그 칸과 "+숫자"를 빼요. 블록 기준 줄 사이가 아니면 본문 줄은 남겨요."""

    def test_only_the_body_lines_are_counted(self):
        d = engine.Draft(req(MOBILE, input_mode="text", counts_source="user"))
        self.assertEqual(d.chars, len(re.sub(r"\s", "", "".join(MOBILE_BODY))))

    def test_title_and_post_count(self):
        self.assertEqual(engine.guess_title(MOBILE), "[서울 종로] 솔바람 찻집 녹차 후기")
        self.assertEqual(engine.count_posts(MOBILE), 1)
        self.assertEqual(engine.count_posts(MOBILE + "\n" + MOBILE), 2)

    def test_body_lines_like_block_words_stay_outside_the_blocks(self):
        """기준 줄이 없으면 빼지 않아요: 본문의 "예약", 시간 줄, "제목 - 사이트" 모양 줄, 맨 끝 태그 한 줄씩."""
        text = "\n".join(["가게 소개예요.", "예약", "10:00", "재방문 의사 - 있음", "#새태그", "#다른태그"])
        self.assertEqual(engine.viewer_skip(text.split("\n")), set())

    def test_trailing_tags_without_more_are_dropped_only_when_already_in_the_body(self):
        lines = ["본문이에요.", "#솔바람찻집 #녹차맛집", "", "#솔바람찻집", "#녹차맛집"]
        self.assertEqual(engine.viewer_skip(lines), {3, 4})

    def test_profile_word_in_the_body_is_not_a_header(self):
        text = "\n".join(["첫 문장이에요.", "둘째 문장이에요.", "셋째 문장이에요.", "넷째 문장이에요.", "다섯째 문장이에요.", "프로필",
                          "가나다", "2026. 1. 2."])
        self.assertIsNone(engine.guess_title(text))


class ViewerPaste(unittest.TestCase):
    """10단계: 보기 화면에서 딸려 온 줄은 세지 않고, 제목과 글 개수를 알아봐요."""

    def test_header_footer_card_and_buttons_are_not_counted(self):
        d = engine.Draft(req(VIEWER))
        # 본문에 직접 쓴 주소 줄과 해시태그 줄은 세요. 링크 카드 글, 영상 제목, 태그 목록, 머리·꼬리는 빼요
        body = "이 글은 업체로부터 제품을 제공받아 작성했어요.녹차를 매일 마셨어요.https://example.invalid/item녹차 향이 좋았어요.#녹차 #녹차추천"
        self.assertEqual(d.chars, len(re.sub(r"\s", "", body)))
        r = one("keyword_count", {"keywords": ["녹차"], "min": 1}, req(VIEWER))
        # 제목·[출처]·링크 카드·영상 제목·맨 아래 태그 목록은 빼요. 본문 글 2회 + 본문에 쓴 해시태그 2회 (2026-11-27부터)
        self.assertEqual(r["actual"], 4)
        self.assertIn("본문 글 2번 + 해시태그 2번", r["note"])
        self.assertIn("보기 화면에서 딸려 온 줄", one("length", {"min": 1, "count_spaces": False}, req(VIEWER))["note"])

    def test_spans_still_point_into_the_pasted_text(self):
        r = one("keyword_count", {"keywords": ["녹차"], "min": 1}, req(VIEWER))
        self.assertEqual([cut(VIEWER, s) for s in r["draft_spans"]], ["녹차"] * 4)

    def test_title_from_source_line_or_line_above_profile(self):
        self.assertEqual(engine.guess_title(VIEWER), "솔바람 녹차 한 달 마셔 본 후기 | 녹차추천")
        no_source = VIEWER[:VIEWER.index("[출처]")]
        self.assertEqual(engine.guess_title(no_source), "솔바람 녹차 한 달 마셔 본 후기 | 녹차추천")   # 카테고리 줄이 아니라 프로파일 바로 위
        self.assertIsNone(engine.guess_title("그냥 쓴 원고예요.\n둘째 줄"))

    def test_many_posts_are_detected(self):
        self.assertEqual(engine.count_posts(VIEWER), 1)
        self.assertEqual(engine.count_posts(VIEWER + "\n\n다음 글 제목\n프로파일\n가나다 ・ 2026. 1. 3. 09:00\n본문"), 2)
        self.assertEqual(engine.count_posts("에디터에서 복사한 원고"), 0)

    def test_ai_mark_line_is_warned_only_when_present(self):
        text = "AI 활용\n녹차를 마셨어요."
        out = run(cond("keyword_count", {"keywords": ["녹차"], "min": 1}), req(text))
        p = rule(out, "p7")                     # 가이드에 생성형 AI 금지 조건이 없으면 "참고"로만
        self.assertEqual((p["status"], p["label"]), ("hold", '참고: "AI 활용" 표시'))
        self.assertTrue(p["note"].startswith("참고:"))
        self.assertIn("확인이 필요해요", p["note"])
        self.assertEqual([cut(text, s) for s in p["draft_spans"]], ["AI 활용"])
        self.assertNotIn("p7", [x["rule_id"] for x in run([], req("녹차를 마셨어요."))["principles"]])
        self.assertEqual(engine.Draft(req(text)).chars, len("녹차를마셨어요."))      # 표시 줄은 글자 수에서 빼요

    def test_ai_mark_goes_under_the_guide_ai_ban_condition(self):
        text = "AI 활용\n녹차를 마셨어요."
        for kind, params in (("judgment", {"question": "생성형 AI를 쓰지 않았는가"}),
                             ("outside_draft", {"what": "추가 안내사항 (생성형 AI 금지)"})):
            ban = cond(kind, params, countable=False, cid="c2")
            out = run([cond("keyword_count", {"keywords": ["녹차"], "min": 1}), ban], req(text))
            self.assertNotIn("p7", [x["rule_id"] for x in out["principles"]])
            r = out["results"][1]
            self.assertIn('"AI 활용" 표시 줄이 있어요', r["note"])
            self.assertIn("생성형 AI 사용을 금지해서 문제가 될 수 있어요", r["note"])
            self.assertEqual([cut(text, s) for s in r["draft_spans"]], ["AI 활용"])
            self.assertEqual(r["status"], "hold")

    def test_partners_disclosure_only_at_the_end_is_not_top(self):
        text = "첫 문단이에요.\n\n둘째 문단이에요.\n\n이 글은 쿠팡 파트너스 활동의 하나로 수수료를 제공받아요."
        p = rule(run([], req(text, title="후기")), "p1")
        self.assertEqual(p["status"], "missing")
        self.assertIn("뒤쪽", p["note"])
        top = rule(run([], req("이 포스팅은 쿠팡 파트너스 활동의 일환이에요.\n\n본문", title="후기")), "p1")
        self.assertEqual(top["status"], "kept")


class RealCaseRules(unittest.TestCase):
    """10단계: 합계로 세는 키워드, 동영상을 포함한 사진 수, 사진 상한."""

    def test_sum_of_chosen_keywords(self):
        text = "가나 가나 다라 다라 다라"
        r = one("keyword_count", {"keywords": ["가나", "다라", "마바"], "min": 5, "pick": "sum"}, req(text))
        self.assertEqual((r["status"], r["actual"]), ("kept", 5))
        self.assertIn("합계 5회", r["note"])
        short = one("keyword_count", {"keywords": ["가나", "다라"], "min": 6, "pick": "sum"}, req(text))
        self.assertEqual((short["status"], short["actual"]), ("missing", 5))
        self.assertIn("1회 더", short["note"])
        anyone = one("keyword_count", {"keywords": ["가나", "다라"], "min": 5, "pick": "any"}, req(text))
        self.assertEqual(anyone["status"], "missing")          # 하나만 세면 3회라서 빠짐 (합계와 다름)

    def test_photo_count_can_include_videos(self):
        r = one("photo_count", {"min": 15, "include_video": True}, req("본문", photo_count=13, video_count=2))
        self.assertEqual((r["status"], r["actual"]), ("kept", 15))
        self.assertIn("동영상 2개 포함", r["note"])
        r = one("photo_count", {"min": 15, "include_video": True}, req("본문", photo_count=13, video_count=None))
        self.assertEqual(r["status"], "hold")

    def test_photo_count_maximum(self):
        over = one("photo_count", {"min": 15, "max": 20}, req("본문", photo_count=22))
        self.assertEqual((over["status"], over["actual"]), ("missing", 22))
        self.assertIn("최대 20장", over["note"])
        ok = one("photo_count", {"min": 15, "max": 20}, req("본문", photo_count=18))
        self.assertEqual(ok["status"], "kept")
        self.assertIn("최대 20장", ok["note"])


class NewCountingRules(unittest.TestCase):
    """2026-11-27 기준 바꾸기: 강남맛집 키워드, 자율 키워드, 제목 두 해석, 사진 설명, 공백 기준 (경계 사례)."""

    GANGNAM = {"keywords": ["솔바람찻집", "성수카페"], "min": 3, "pick": "any", "scope": "body"}

    def test_gangnam_keyword_two_times_is_missing_and_three_times_is_kept(self):
        two = one("keyword_count", self.GANGNAM, req("솔바람찻집 솔바람찻집 성수카페"))
        self.assertEqual((two["status"], two["actual"]), ("missing", 2))
        self.assertIn('키워드별: "솔바람찻집" 2회, "성수카페" 1회', two["note"])
        three = one("keyword_count", self.GANGNAM, req("솔바람찻집 솔바람찻집 솔바람찻집 성수카페"))
        self.assertEqual((three["status"], three["actual"]), ("kept", 3))
        self.assertIn('"솔바람찻집" 3회(3회 이상), "성수카페" 1회', three["note"])     # 3회 이상인 것을 표시해요

    def test_free_keyword_empty_is_hold_and_filled_is_counted(self):
        free = {"keywords": [], "min": 3, "pick": "each", "scope": "body", "free": True}
        empty = one("keyword_count", free, req("성수 디저트 이야기"))
        self.assertEqual((empty["status"], empty["note"]), ("hold", "자율 키워드를 적어 주시면 함께 셀게요"))
        filled = dict(free, keywords=["말차라떼"])
        self.assertEqual(one("keyword_count", filled, req("말차라떼 말차라떼"))["status"], "missing")
        self.assertEqual(one("keyword_count", filled, req("말차라떼 말차라떼 말차라떼"))["status"], "kept")
        # 비어 있는 자율 키워드는 p3(과다 반복)에서도 건너뛰어요
        out = run(cond("keyword_count", free), req("성수 디저트"))
        self.assertEqual(rule(out, "p3")["status"], "hold")

    def test_title_with_three_keywords_needs_all_and_four_shows_both_readings(self):
        three = {"keywords": ["가나", "다라", "마바"], "pick": "each"}
        self.assertEqual(one("title_keyword", three, req("본문", title="가나 다라 이야기"))["status"], "missing")
        self.assertEqual(one("title_keyword", three, req("본문", title="가나 다라 마바 이야기"))["status"], "kept")
        four = {"keywords": ["가나", "다라", "마바", "사아"], "pick": "both"}
        some = one("title_keyword", four, req("본문", title="가나 이야기"))
        self.assertEqual(some["status"], "hold")
        self.assertIn("전부 넣는 기준이면 빠짐, 하나 이상 기준이면 지킴", some["note"])
        self.assertIn("가이드 기준 확인 필요", some["note"])
        self.assertEqual(one("title_keyword", four, req("본문", title="가나 다라 마바 사아"))["status"], "kept")
        self.assertEqual(one("title_keyword", four, req("본문", title="다른 제목"))["status"], "missing")

    def test_body_keywords_without_wording_show_both_readings(self):
        both = {"keywords": ["가나", "다라"], "min": 2, "pick": "both", "scope": "body"}
        r = one("keyword_count", both, req("가나 가나 다라"))
        self.assertEqual(r["status"], "hold")
        self.assertIn("키워드마다 2회 기준이면 빠짐, 하나만 2회 기준이면 지킴", r["note"])
        self.assertIn("가이드 기준 확인 필요", r["note"])
        self.assertEqual(one("keyword_count", both, req("가나 가나 다라 다라"))["status"], "kept")
        self.assertEqual(one("keyword_count", both, req("가나 다라"))["status"], "missing")

    def test_caption_lines_are_counted_by_default_and_can_be_left_out(self):
        from unittest import mock
        text = "본문 글이에요\n[사진]\n사진 설명\n끝 문단"
        at = text.index("사진 설명")
        request = req(text, captions=[{"start": at, "end": at + len("사진 설명")}])
        with_caption = one("length", {"min": 1, "count_spaces": False}, request)
        self.assertEqual(with_caption["actual"], len("본문글이에요사진설명끝문단"))
        self.assertIn("사진 설명 1줄은 셌어요", with_caption["note"])
        with mock.patch.object(engine, "COUNT_CAPTIONS", False):
            without = one("length", {"min": 1, "count_spaces": False}, request)
        self.assertEqual(without["actual"], len("본문글이에요끝문단"))
        self.assertIn("사진 설명 1줄은 세지 않았어요", without["note"])
        # 화면의 설정(요청의 count_captions)이 서버 기본값보다 먼저예요
        self.assertEqual(one("length", {"min": 1, "count_spaces": False}, dict(request, count_captions=False))["actual"],
                         len("본문글이에요끝문단"))
        with mock.patch.object(engine, "COUNT_CAPTIONS", False):
            self.assertEqual(one("length", {"min": 1, "count_spaces": False}, dict(request, count_captions=True))["actual"],
                             len("본문글이에요사진설명끝문단"))
        # 사진 설명 안의 키워드는 그대로 찾아요
        self.assertEqual(one("keyword_count", {"keywords": ["설명"], "min": 1}, request)["actual"], 1)

    def test_space_rule_follows_the_guide_and_defaults_to_with_spaces(self):
        text = "가나 다라\n마바"
        silent = one("length", {"min": 1, "count_spaces": None}, req(text))
        self.assertEqual(silent["actual"], len("가나 다라마바"))                    # 줄바꿈은 안 세요 (2026-11-28)
        self.assertIn("공백 포함 7자(줄바꿈은 세지 않아요), 공백 제외 6자", silent["note"])
        self.assertEqual(one("length", {"min": 1, "count_spaces": False}, req(text))["actual"], 6)
        self.assertEqual(one("length", {"min": 1, "count_spaces": True}, req(text))["actual"], 7)

    def test_text_only_count_says_so(self):
        text_req = req("글만 붙여 넣었어요", input_mode="text", counts_source="user")
        self.assertIn("글자만으로 센 값", one("length", {"min": 1, "count_spaces": None}, text_req)["note"])
        self.assertNotIn("글자만으로 센 값", one("length", {"min": 1, "count_spaces": None}, req("서식에서 읽었어요"))["note"])


# fe/selftest.js의 SE_HTML(스마트에디터 서식)과 같은 글을 보기 화면에서 글자로 복사한 모양 (지어낸 글)
SE_TEXT_PASTE = "\n".join([
    "일상 기록", "솔바람 녹차 후기", "", "프로파일", " 가나다 ・ 2026. 1. 2. 10:00",
    "솔바람 녹차를 한 달 마셨어요.", "아침에 우린 녹차", "https://example.invalid/item", "",
    "솔바람 녹차 30포", "녹차 전문", "", "example.invalid", "Previous imageNext image",
    "향이 좋았어요.", "#녹차 #아침차", "태그", "#녹차", "#태그칸만",
])


class HtmlTextParity(unittest.TestCase):
    def test_text_paste_counts_like_the_smart_editor_html(self):
        """글만 붙여 넣어도 서식으로 센 값(fe/selftest.js: 공백 포함 70, 공백 제외 62)과 같게 나와요 (줄바꿈은 안 세요)."""
        d = engine.Draft(req(SE_TEXT_PASTE, input_mode="text", counts_source="user"))
        self.assertEqual((d.chars_with_spaces, d.chars), (70, 62))


# 지역 키워드("부산맛집")에 맞춰 지어낸 원고. 정확히 쓴 곳 1번, 띄어 쓴 곳("부산 맛집") 1번, 해시태그 1번.
TIP_BODY = "\n".join([
    "업체로부터 식사를 제공받아 작성한 글입니다.", "",
    "주말에 부산 여행을 갔다가 돌솥집에 다녀왔어요. 친구가 알려 준 곳이에요.", "", "[사진]", "",
    "부산맛집 답게 줄이 길었어요. 그래도 금방 들어갔어요.", "",
    "메뉴는 돌솥밥 하나예요. 반찬이 깔끔하고 양이 넉넉했어요. 숭늉까지 먹으면 든든해요.", "",
    "부산 맛집을 찾는 분이라면 한 번 가 볼 만해요.", "",
    "주차는 가게 앞에 세 대까지 돼요. 다음에 부모님과 또 가려고요. 추천해요.", "", "#부산맛집 #돌솥밥"])
TIP_REQ = req(TIP_BODY, title="부산 맛집 돌솥집 후기", input_mode="text", counts_source="user")
TIP_CONDS = [cond("title_keyword", {"keywords": ["부산맛집"], "pick": "any"}, cid="c1"),
             cond("keyword_count", {"keywords": ["부산맛집"], "min": 5, "pick": "any", "scope": "body"}, cid="c2")]


class Tips(unittest.TestCase):
    """2026-11-28 "도움이 될 팁": 판정이 아니에요. 지킴·빠짐과 요약 개수를 바꾸지 않아요. 지어낸 예시만 써요."""

    @classmethod
    def setUpClass(cls):
        cls.out = run(TIP_CONDS, TIP_REQ)
        cls.tips = cls.out["tips"]

    def kind(self, kind: str, out=None) -> list[dict]:
        return [t for t in (self.tips if out is None else out["tips"]) if t["kind"] == kind]

    def test_tips_never_change_verdicts_or_counts(self):
        """팁을 만들든 안 만들든 results, principles, summary가 같아요 (지어낸 예시 전부)."""
        from unittest import mock
        samples = [(load("conditions.example.json"), load("check-request.example.json")),
                   (load("conditions.example-2.json"), GOOD2),
                   (load("conditions.example-3.json"),
                    json.loads((ROOT / "samples" / "draft-04.request.json").read_text(encoding="utf-8"))),
                   ({"version": "0.3", "conditions": TIP_CONDS}, TIP_REQ)]
        made = 0
        for conditions, request in samples:
            with_tips = engine.check(conditions, request)
            with mock.patch.object(engine, "tips", return_value=[]):
                without = engine.check(conditions, request)
            made += len(with_tips["tips"])
            for key in ("summary", "results", "principles"):
                self.assertEqual(with_tips[key], without[key], key)
        self.assertGreater(made, 0)
        self.assertEqual(self.out["summary"], {"kept": 0, "missing": 2, "hold": 0})      # 팁 3개가 있어도 빠짐은 조건 2개 그대로
        self.assertEqual(len(self.tips), 3)
        for tip in self.tips:
            self.assertNotIn("status", tip)

    def test_spacing_tip_marks_the_spaced_form_in_title_and_body(self):
        title, body = self.kind("keyword_spacing")
        self.assertEqual((title["condition_id"], title["draft_spans"]), ("c1", [{"start": 0, "end": 5, "field": "title"}]))
        self.assertEqual([cut(TIP_BODY, s) for s in body["draft_spans"]], ["부산 맛집"])
        self.assertIn("붙여 써야 키워드로 세져요", body["note"])
        self.assertEqual(body["templates"], [])

    def test_place_tip_only_when_short_and_points_at_fitting_paragraphs(self):
        (place,) = self.kind("keyword_place")
        self.assertEqual([cut(TIP_BODY, s) for s in place["draft_spans"]],
                         ["주말에 부산 여행을 갔다가 돌솥집에 다녀왔어요.", "다음에 부모님과 또 가려고요. 추천해요."])
        self.assertIn("3회가 더 필요할 때", place["note"])
        self.assertIn("우리 기준", place["note"])
        enough = [dict(TIP_CONDS[1], params=dict(TIP_CONDS[1]["params"], min=1))]
        self.assertEqual(run(enough, TIP_REQ)["tips"], [])                              # 기준을 채웠으면 팁이 없어요

    def test_frames_are_short_fragments_with_a_blank(self):
        """틀은 문장이 아니에요: 빈칸(○○)이 있고, 문장 끝(다/요/마침표)이 없고, 짧아요."""
        (place,) = self.kind("keyword_place")
        self.assertEqual(place["templates"], ["○○ 찾다가 알게 된 부산맛집", "부산맛집으로 유명한 ○○", "○○하기 좋은 부산맛집"])
        for frames in (phrases.TIP_FRAMES_REGION, phrases.TIP_FRAMES_GENERAL):
            self.assertIn(len(frames), (2, 3))
            for f in frames:
                self.assertIn("○○", f)
                self.assertIn("{k}", f)
                self.assertLessEqual(len(f), 25)
                self.assertNotRegex(f, r"[.!?]|[다요]$")
        self.assertEqual((engine.josa("제주도", "ro"), engine.josa("서울", "ro"), engine.josa("수분크림", "eul"),
                          engine.josa("녹차", "eul"), engine.josa("cafe", "eul")), ("로", "로", "을", "를", "을(를)"))
        self.assertEqual((engine.region_of("부산맛집"), engine.region_of("솔밭동 카페"), engine.region_of("수분크림")),
                         ("부산", "솔밭동", None))
        cream = run(cond("keyword_count", {"keywords": ["수분크림"], "min": 2}), req("겨울이라 하나 찾다가 골랐어요. 가볍게 잘 발려요."))
        self.assertEqual(self.kind("keyword_place", cream)[0]["templates"][1], "수분크림을 고른 이유는 ○○")

    def test_following_the_place_tip_does_not_trip_keyword_repeat(self):
        """추천한 자리마다 키워드를 넣어도 p3 "이어진 두 문장"에 걸리지 않아요. 키워드가 이미 있는 문단은 추천하지 않아요."""
        (place,) = self.kind("keyword_place")
        text = TIP_BODY
        for s in sorted(place["draft_spans"], key=lambda s: -s["start"]):
            self.assertNotIn("부산맛집", cut(TIP_BODY, s))
            self.assertNotIn("부산 맛집", cut(TIP_BODY, s))
            text = text[:s["start"]] + "부산맛집 " + text[s["start"]:]
        text = text.replace("부산 맛집", "부산맛집")                                   # 띄어쓰기 팁도 따랐을 때
        after = run(TIP_CONDS[1], dict(TIP_REQ, draft_text=text))
        self.assertEqual(rule(run(TIP_CONDS[1], TIP_REQ), "p3")["status"], "kept")
        self.assertEqual(rule(after, "p3")["status"], "kept")
        self.assertEqual(after["results"][0]["actual"], 5)                              # 1 + 띄어 쓴 1 + 넣은 2 + 해시태그 1

    def test_no_place_tip_when_fixing_the_spacing_is_enough(self):
        text = "솔밭동 카페에 다녀왔어요.\n\n다음에 또 가려고요. 솔밭동카페 추천해요."
        out = run(cond("keyword_count", {"keywords": ["솔밭동 카페"], "min": 2}), req(text))
        self.assertEqual([t["kind"] for t in out["tips"]], ["keyword_spacing"])
        self.assertIn("가이드와 똑같이 써야 키워드로 세져요", out["tips"][0]["note"])     # 띄어 쓰는 키워드를 붙여 쓴 반대 경우
        self.assertEqual(cut(text, out["tips"][0]["draft_spans"][0]), "솔밭동카페")

    def test_spaced_form_must_start_a_word(self):
        out = run(cond("keyword_count", {"keywords": ["강남맛집"], "min": 1}), req("한강 남 맛집 지도를 봤어요."))
        self.assertEqual(self.kind("keyword_spacing", out), [])

    def test_no_tips_when_the_verdict_is_hold_or_kept(self):
        untitled = dict(TIP_REQ, title=None)
        for conds, request in (
                (cond("keyword_count", {"keywords": [], "min": 3, "free": True}), TIP_REQ),              # 자율 키워드가 비어 있음
                (cond("keyword_count", {"keywords": ["부산맛집"], "min": None}), TIP_REQ),               # 기준 숫자가 없음
                (TIP_CONDS[0], untitled),                                                                # 제목을 모름
                (cond("keyword_count", {"keywords": ["부산맛집"], "min": 5, "scope": "title_and_body"}), untitled),
                (cond("keyword_count", {"keywords": ["부산맛집", "돌솥집"], "min": 1, "pick": "both"}),
                 req("부산맛집에 다녀왔어요. 부산 맛집이에요.")),                                         # 두 해석이 갈림
                (cond("judgment", {"question": "부산맛집 느낌"}, countable=False), TIP_REQ)):
            out = run(conds, request)
            self.assertNotEqual(out["results"][0]["status"], "missing")
            self.assertEqual(out["tips"], [])

    def test_which_keywords_get_a_place_tip(self):
        text = "솔밭동에 다녀왔어요.\n\n메뉴가 많아요. 분위기도 좋아요.\n\n다음에 또 가려고요. 추천해요."
        labels = lambda p: [t["label"] for t in self.kind("keyword_place", run(cond("keyword_count", p), req(text)))]
        four = ["가맛집", "나맛집", "다맛집", "라맛집"]
        self.assertEqual(len(labels({"keywords": four, "min": 1, "pick": "each"})), engine.TIP_KEYWORDS)   # 모자란 키워드마다, 3개까지
        self.assertEqual(labels({"keywords": four, "min": 1, "pick": "any"}), ['넣을 자리 추천: "가맛집"'])
        self.assertEqual(labels({"keywords": ["가맛집", "메뉴"], "min": 3, "pick": "any"}), ['넣을 자리 추천: "메뉴"'])   # 기준에 가까운 것
        self.assertEqual(labels({"keywords": ["가맛집", "메뉴"], "min": 3, "pick": "sum"}), ['넣을 자리 추천: "메뉴"'])
        self.assertEqual(labels({"keywords": four, "min": 1, "pick": "any", "scope": "title"}), [])       # 제목 조건은 자리 추천 없음

    def test_tips_stay_small_and_quick_at_the_server_limits(self):
        """서버 한도(원고 60,000자, 조건 80개, 키워드 400개)에서도 팁은 TIP_MAX개까지이고 금방 끝나요.
        (정규식으로 찾던 처음 판은 이 입력에서 15~48초가 걸렸어요. 글자 찾기로 바꾸고 상한을 뒀어요.)"""
        import time
        many = ("메뉴가 많아요. 다음에 또 가려고요.\n\n" * 3000)[:60000]
        spaced = (("부산 맛집 " * 10 + "다녀왔어요. 추천해요.\n\n") * 900)[:60000]
        near = ("가" * 199 + "나") * 300
        for text, conds in (
                (many, [cond("keyword_count", {"keywords": [f"가맛집{i}_{j}" for j in range(5)], "min": 5, "pick": "each"},
                             cid=f"c{i}") for i in range(80)]),
                (spaced, [cond("keyword_count", {"keywords": ["부산맛집"] + [f"부산맛집{j}" for j in range(49)], "min": 5000})]),
                (near, [cond("keyword_count", {"keywords": ["가" * 199 + chr(0xB098 + i * 50 + j) for j in range(50)], "min": 5,
                                               "pick": "each"}, cid=f"c{i}") for i in range(8)])):
            d = engine.Draft(req(text, title="제목"))
            results = [engine.judge(c, d) for c in conds]
            started = time.perf_counter()
            out = engine.tips(conds, results, d)
            self.assertLess(time.perf_counter() - started, 1.0)
            self.assertTrue(0 < len(out) <= engine.TIP_MAX)
            self.assertTrue(all(len(t["draft_spans"]) <= engine.MAX_SPANS for t in out))
        # 띄어 쓴 곳이 아주 많으면 개수는 전부 센 값으로 적고, 위치는 상한까지만 줘요
        note = run(cond("keyword_count", {"keywords": ["부산맛집"], "min": 5000}), req(spaced))["tips"][0]["note"]
        self.assertIn(f'{spaced.count("부산 맛집")}곳 있어요', note)
        self.assertIn(f"(위치는 앞에서부터 {engine.MAX_SPANS}곳만 표시해요)", note)

    def test_positions_point_at_the_draft_as_received(self):
        """자모가 나뉜 한글(NFD)로 와도 팁의 위치는 받은 원고 그대로의 위치예요."""
        import unicodedata
        nfd = unicodedata.normalize("NFD", TIP_BODY)
        out = run(TIP_CONDS[1], dict(TIP_REQ, draft_text=nfd))
        got = [unicodedata.normalize("NFC", cut(nfd, s)) for t in out["tips"] for s in t["draft_spans"]]
        want = [cut(TIP_BODY, s) for t in run(TIP_CONDS[1], TIP_REQ)["tips"] for s in t["draft_spans"]]
        self.assertEqual(got, want)
        self.assertEqual(len(want), 3)

    def test_contract_example_and_schema(self):
        self.assertEqual(engine.check(load("conditions.example.json"), load("check-request.example.json"))["tips"],
                         load("check-result.example.json")["tips"])
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema가 없어요 (pip install jsonschema)")
        validator = Draft202012Validator(load("check-result.schema.json"))
        self.assertEqual([e.message for e in validator.iter_errors(self.out)], [])
        self.assertEqual([e.message for e in validator.iter_errors({k: v for k, v in self.out.items() if k != "tips"})], [])
