"""규칙 엔진: 조건 목록 + 점검 요청 → 점검 결과 (contracts 0.3).

- 셀 수 있는 조건은 전부 여기서 코드로 판정해요. LLM을 부르지 않아요.
- 받은 가이드·원고 글을 화면이나 로그, 파일에 남기지 않아요. 이 파일에서는 출력 함수와 로그 모듈을 쓰지 않아요.
- 위치는 코드 포인트(파이썬 문자열 위치)예요. end는 포함하지 않아요.
- 같은 입력이면 항상 같은 결과가 나와요.
- "도움이 될 팁"(tips)은 판정과 따로예요. 상태가 없고 요약 개수에 들어가지 않아요.
"""
from __future__ import annotations

import bisect
import os
import re
import unicodedata

from . import phrases

VERSION = "0.3"
MARKS = {"[사진]": "photo", "[동영상]": "video", "[지도]": "map"}
# 네이버 글쓰기 화면에서 본문을 복사하면 같이 딸려 오는 편집 화면 줄. 줄 전체가 이것과 같을 때만 빼요.
EDITOR_LINES = {"대표사진 삭제", "대표사진 설정", "AI 활용 설정", "사진 설명을 입력하세요.", "동영상 설명을 입력하세요.",
                # 2026-11-27 글쓰기 화면 복사 시험(samples/editor/)에서 찾은 단추 글자: 대표 지정, 슬라이드 넘기기, 정렬, 지우기
                "대표", "이전 이미지", "다음 이미지", "이전 이미지다음 이미지", "이전 이미지 다음 이미지",
                "오른쪽 정렬", "왼쪽 정렬", "가운데 정렬", "삭제", "사진 삭제", "이미지 삭제", "이미지 썸네일 삭제"}
PHOTO_LINES = ("대표사진 삭제", "대표사진 설정")       # 사진 하나에 이 줄이 하나씩 붙는다고 봐요 (실제 에디터로 확인할 것)
HIDDEN = re.compile("[​⁠﻿\r]")        # 숨은 문자(fe/analyze.js의 zw와 같은 것)와 \r. 글자 수에 넣지 않아요

# 발행된 글을 보기 화면에서 복사하면 딸려 오는 줄 (실제 보기 화면에서 본 모양). 글자 수와 키워드 찾기에서 빼요.
# 줄 전체(공백은 하나로 묶어서)가 이것과 같거나, 아래 모양일 때만 빼요.
VIEWER_LINES = {"프로파일", "URL 복사 이웃추가", "본문 기타 기능", "접기/펴기", "Previous imageNext image", "인쇄", "태그",
                "AI 활용", "이웃추가본문 기타 기능", "이웃추가"}            # 뒤의 둘: 모바일 보기 화면 머리 (2026-11-27)
VIEWER_PREFIX = ("저작자 명시 필수", "블로그 보내기")
# [출처] 제목|작성자 이름 — 본문에 쓴 "[출처] 네이버 지식백과" 같은 인용 줄과 헷갈리지 않게 "|작성자"가 있을 때만
SOURCE_LINE = re.compile(r"\[출처\].*\|작성자.*")
# 작성자 ・ 2026. 11. 15. 12:08, 또는 방금 올린 글의 "2시간 전", "어제"
AUTHOR_DATE = re.compile(r".{1,40}\s・\s(\d{4}\.\s?\d{1,2}\.\s?\d{1,2}\..*|\d+\s*(초|분|시간|일)\s*전|방금\s*전|어제.*)")
LIKES = re.compile(r"공감\s*\d*\s+이 글에 공감한 블로거.*")                          # 공감 12 이 글에 공감한 블로거 … 댓글 쓰기
BARE_DOMAIN = re.compile(r"[a-z0-9-]+(\.[a-z0-9-]+)+", re.I)                          # 링크 카드 맨 아래 도메인 줄
VIDEO_TITLE = re.compile(r".*\(\d+\)")                                                # 접기/펴기 다음 동영상 제목 "글 제목 (1)"
AI_MARK = "AI 활용"           # 보기 화면의 "AI 활용" 표시 줄 (네이버가 붙이는 표시인지는 확인 필요)
HEADER_LINES = 5              # 맨 위 몇 줄 안에 "프로파일"이 있으면 그 위(제목·카테고리)는 머리로 봐요 (우리 기준)
SENTENCE = re.compile(r"[^.!?\n]+")
URL = re.compile(r"https?://[^\s<>\"'()\[\]]+")
WORD_CHAR = re.compile(r"[0-9A-Za-z가-힣]")



def _setting(name: str, default: int) -> int:
    """환경 변수의 양의 정수 설정. 없거나 잘못된 값이면 기본값이에요."""
    value = os.environ.get(name, "")
    return int(value) if value.isdigit() and int(value) > 0 else default


EXTRA_LINK_LIMIT = 3          # p4: 가이드 필수 링크 밖의 링크가 이 수를 넘으면 알림 (우리 기준)
# p3: 가이드 요구 횟수의 이 배수를 넘으면 "확인해 보세요" (우리 기준. 네이버 공식 숫자는 없어요)
KEYWORD_REPEAT_FACTOR = _setting("PROMPATCH_KEYWORD_REPEAT_FACTOR", 2)
# 글자 수 기준 (2026-11-27 카티 결정): "네이버 블로그 본문 글 블록에 쓴 글자"
#   - 서식(HTML)이 있으면 화면(analyze.js)이 스마트에디터 구조로 글 블록 글자만 draft_text에 넣어요.
#     글 중간에 직접 쓴 #해시태그와 주소도 글 블록이라 세요.
#   - 글만 있으면 보기 화면에서 딸려 온 줄(viewer_skip)을 빼서 최대한 같게 맞추고 "글자만으로 센 값"이라고 적어요.
#   - 사진 설명(캡션): 요청의 captions 자리. 기본은 세요. PROMPATCH_COUNT_CAPTIONS=0이면 빼요.
#     요청에 count_captions(참/거짓)가 있으면 그 값을 써요 (화면의 "설정").
COUNT_CAPTIONS = os.environ.get("PROMPATCH_COUNT_CAPTIONS", "1").strip() != "0"
TITLE_FRONT_SHARE = 0.5       # 제목 키워드 위치 안내: 제목 앞 절반 안에서 시작하면 "앞쪽" (우리 기준)
BODY_FRONT_CHARS = 300        # 본문 키워드 위치 안내: 본문 앞 300자 안에 한 번 나오면 "앞부분" (우리 기준)
MAX_SPANS = 200               # 항목 하나가 돌려주는 위치 개수의 상한 (응답이 한없이 커지는 것을 막아요)
CHARS_PER_PHOTO = 30          # p5: 사진 1장당 공백 제외 글자 수가 이보다 적으면 알림 (우리 기준)

BASIS = {
    "p1": "공정위 추천·보증 심사지침(2024-12-01 시행), 네이버 D.I.A.+(2020-11-18)",
    "p2": "공정위 추천·보증 심사지침(2024-12-01 시행)",
    "p3": "네이버 콘텐츠 작성 가이드(2026-05-26) \"맥락과 관계 없는 키워드를 억지로 끼워 넣지 마세요\"",
    "p4": "네이버 콘텐츠 작성 가이드(2026-05-26) \"외부로 이동하는 URL을 과도하게\"",
    "p5": "네이버 콘텐츠 작성 가이드(2026-05-26) \"핵심 내용은 텍스트로도\"",
    "p6": "리뷰플레이스 기자단 가이드 \"직접 체험한 것처럼 여겨지는 표현 및 내용은 사용 불가\", "
          "공정위 심사지침 개정(2026-06-01 시행)",
    "p7": "우리 기준, 공식 근거 아님: 체험단 가이드에 생성형 AI 이용을 막는 안내가 흔해요(레뷰 등). \"AI 활용\" 표시가 네이버가 붙이는 것인지는 확인 필요",
}
PATTERN_NOTE = "네이버·공정위가 불리하다고 밝힌 패턴이에요"     # p1 (근거가 둘 다)
FTC_NOTE = "공정위가 부적절하다고 밝힌 표현이에요"               # p2
NAVER_NOTE = "네이버가 불리하다고 밝힌 패턴이에요"               # p4, p5
# p3: 공식 숫자 기준이 없어서 공식 안내 문장만 옮기고 "확인해 보세요"까지만 말해요
KEYWORD_NOTE = "네이버는 관련 없는 키워드를 억지로 넣지 말라고 안내해요. 확인해 보세요"
TITLE_UNKNOWN = "제목을 몰라서 판단 보류예요. 제목을 적어 주시면 함께 볼게요"


# ── 원고 읽기 ────────────────────────────────────────────────────────────

class Draft:
    """점검 요청에서 판정에 쓰는 값을 한 번만 계산해 둬요."""

    def __init__(self, request: dict):
        self.req = request
        # 자모가 나뉜 한글(NFD)은 합친 글자(NFC)로 바꿔 찾고 세요. 길이가 달라지니 원래 위치로 돌아갈 표를 둬요.
        self.title, self.title_map = nfc(request.get("title"))      # 제목 None = 모름
        draft, self.body_map = nfc(request["draft_text"])
        self.by_user = request.get("counts_source") == "user"
        self.text_mode = request.get("input_mode") == "text"
        given = request.get("count_captions")
        self.count_captions = given if isinstance(given, bool) else COUNT_CAPTIONS
        # 체험단 배너가 글 맨 위에 있는지 (화면이 서식에서 찾아요). 글만 붙여 넣으면 그림을 못 봐서 None(모름)
        banner = request.get("banner_top")
        self.banner_top = banner if isinstance(banner, bool) and not self.text_mode else (None if self.text_mode else False)

        # 원고를 줄마다 한 번 훑어서 두 가지를 만들어요.
        # - self.text: 찾을 때 쓰는 사본. 편집 화면 줄과 숨은 문자만 있는 줄을 같은 길이의 빈칸으로 바꿔요.
        #   길이가 원고와 같아서, 여기서 찾은 위치가 그대로 원고(draft_text)의 위치예요.
        # - body: 글자 수를 세는 본문. [사진] [동영상] [지도] 줄과 편집 화면 줄을 빼고, 숨은 문자와 \r을 지워요.
        search, counted = [], []
        self.editor_lines = self.editor_photos = self.caption_lines = 0
        lines = draft.split("\n")
        skip = viewer_skip(lines)
        self.viewer_lines = sum(_key(lines[i]) not in EDITOR_LINES for i in skip)    # 편집 화면 줄과 겹치면 편집 화면 줄로만 세요        # 글만 붙여 넣었을 때만: 글쓰기 화면 블록의 동영상 제목·링크 카드 설명·지도 장소 이름과 주소 (서식이 있으면 구조로 이미 빠져요)
        editor = editor_skip(lines) - skip if self.text_mode else set()
        skip |= editor
        captions = [(s, e) for c in request.get("captions") or []
                    if (s := self.to_norm(c.get("start"))) is not None and (e := self.to_norm(c.get("end"))) is not None]
        self.ai_marks, pos = [], 0
        for i, line in enumerate(lines):
            clean = HIDDEN.sub("", line)
            key = clean.strip()
            if " ".join(key.split()) == AI_MARK:
                at = pos + line.index("AI")
                self.ai_marks.append((at, at + len(AI_MARK)))
            caption = bool(key) and any(s <= pos and pos + len(line) <= e for s, e in captions)
            pos += len(line) + 1
            if key in EDITOR_LINES or i in editor:
                self.editor_lines += 1
                self.editor_photos += key in PHOTO_LINES
            drop = key in EDITOR_LINES or i in skip
            if drop and counted and not counted[-1].strip():
                counted.pop()           # 뺀 줄 바로 앞의 빈 줄도 빼요 (서식으로 센 값과 공백 포함 수를 맞춰요)
            search.append(" " * len(line) if not key or drop else line)
            # 사진 설명 줄: 찾는 사본에는 남기고, 설정이 끄면 글자 수에서만 빼요
            self.caption_lines += caption and not drop
            if key not in MARKS and not drop and not (caption and not self.count_captions):
                counted.append(clean)
        self.text = "\n".join(search)
        body = "\n".join(counted)
        self.chars = len(re.sub(r"\s", "", body))        # 공백 제외
        # 공백 포함 = 문단 안의 글자와 띄어쓰기만 (2026-11-28 카티 결정). 줄바꿈·빈 줄·줄 앞뒤 공백은 세지 않아요.
        # 그래서 보기 화면·글쓰기 화면·글만 붙여넣기 어디서 복사해도 같은 값이에요
        self.chars_with_spaces = sum(len(line.strip()) for line in counted)

        self.first_para = self._first_paragraph()
        self.sentences = [
            (m.start() + len(m.group()) - len(m.group().lstrip()), m.start() + len(m.group().rstrip()))
            for m in SENTENCE.finditer(self.text)
            if m.group().strip() and m.group().strip() not in MARKS
        ]
        self.sentence_starts = [start for start, _ in self.sentences]
        self.links = self._links()
        self.map_starts = [p for m in request.get("media") or []
                           if m.get("kind") == "map" and (p := self.to_norm(m.get("start"))) is not None]

    def to_norm(self, pos):
        """요청에 적힌 원고 위치 → 찾는 사본(NFC)의 위치. 글자 경계가 아니면 None."""
        if not isinstance(pos, int) or isinstance(pos, bool):
            return None
        if self.body_map is None:
            return pos
        starts = self.body_map[0]
        i = bisect.bisect_left(starts, pos)
        return i if i < len(starts) and starts[i] == pos else None

    def to_orig(self, s: dict) -> None:
        """찾은 위치(NFC 사본 기준)를 받은 원고 그대로의 위치로 바꿔요."""
        table = self.title_map if s.get("field") == "title" else self.body_map
        if table and s["end"] > s["start"]:
            s["start"], s["end"] = table[0][s["start"]], table[1][s["end"] - 1]

    def _first_paragraph(self) -> tuple[int, int]:
        """본문 첫 문단: 첫 글 줄부터 첫 빈 줄(또는 첫 미디어 줄) 전까지."""
        start = end = None
        pos = 0
        for line in self.text.split("\n"):
            blank_or_mark = not line.strip() or line.strip() in MARKS
            if start is None:
                if not blank_or_mark:
                    start = pos
                    end = pos + len(line)
            elif blank_or_mark:
                break
            else:
                end = pos + len(line)
            pos += len(line) + 1
        return (start, end) if start is not None else (0, 0)

    def _links(self) -> list[dict]:
        """요청의 links와 본문에 적힌 주소를 모아, 같은 주소는 하나로 세요."""
        found: dict[str, dict] = {}

        def add(url: str, start):
            key = norm_url(url)
            if not key:
                return
            span = None
            if isinstance(start, int) and self.text[start:start + len(url)] == url:
                span = body_span(start, start + len(url))
            item = found.setdefault(key, {"url": url, "span": None})
            item["span"] = item["span"] or span

        for link in self.req.get("links") or []:
            add(link.get("url") or "", self.to_norm(link.get("start")))
        for m in URL.finditer(self.text):
            url = m.group().rstrip(".,;:!?")
            add(url, m.start())
        return list(found.values())

    def sentence_at(self, pos: int) -> tuple[int, int]:
        """pos가 든 문장의 위치. 끝에는 마침표(. ! ?)까지 넣어요."""
        for start, end in self.sentences:
            if start <= pos < end:
                while end < len(self.text) and self.text[end] in ".!?":
                    end += 1
                return start, end
        return pos, pos + 1

    def text_after(self, pos: int) -> bool:
        """pos가 있는 줄 뒤에 글 문단이 있는지. 빈 줄, 해시태그 줄, 주소 줄, [사진] 같은 자리 표시 줄은 글이 아니에요."""
        for line in self.text[pos:].split("\n")[1:]:
            words = line.split()
            if words and line.strip() not in MARKS and not all(w.startswith("#") or URL.fullmatch(w) for w in words):
                return True
        return False

    def in_first_para(self, pos: int) -> bool:
        return self.first_para[0] <= pos < self.first_para[1]


def _key(line: str) -> str:
    return " ".join(HIDDEN.sub("", line).split())


def viewer_skip(lines: list[str]) -> set[int]:
    """보기 화면에서 딸려 온 줄 번호: 머리(제목·카테고리·프로파일·작성자 줄), 꼬리(CCL, 태그 목록, 공감, [출처]),
    링크 카드 글(주소 줄 아래 상품명·설명·도메인), 접기/펴기, 슬라이드 단추 글, 동영상 제목 줄."""
    keys = [_key(l) for l in lines]
    skip = set()
    filled = [i for i, k in enumerate(keys) if k]
    first = filled[:HEADER_LINES]
    for n, i in enumerate(first):
        if keys[i] in PROFILE_LINES:
            skip.update(j for j in range(i))         # 프로파일(모바일은 "프로필") 위는 제목과 카테고리
            skip.add(i)
            # 모바일: 프로필 → 작성자 이름 줄 → 날짜 줄이 따로 와요
            nxt = filled[n + 1:n + 3]
            if len(nxt) == 2 and len(keys[nxt[0]]) <= 20 and DATE_ONLY.fullmatch(keys[nxt[1]]):
                skip.update(nxt)
            break
    skip |= mobile_skip(keys, filled)
    in_tags = False
    for i, k in enumerate(keys):
        if not k:
            continue
        if (k in VIEWER_LINES or k.startswith(VIEWER_PREFIX) or SOURCE_LINE.fullmatch(k) or AUTHOR_DATE.fullmatch(k)
                or LIKES.fullmatch(k)):
            skip.add(i)
            in_tags = k == "태그"
            if k == "접기/펴기":
                nxt = next((j for j in range(i + 1, len(keys)) if keys[j]), None)
                if nxt is not None and VIDEO_TITLE.fullmatch(keys[nxt]):
                    skip.add(nxt)
            continue
        if in_tags and all(w.startswith("#") for w in k.split()):
            skip.add(i)                               # "태그" 아래 태그 목록
            continue
        in_tags = False
        if BARE_DOMAIN.fullmatch(k) and not URL.match(k):
            # 링크 카드: 주소 줄 → (빈 줄) → 상품명·설명 → (빈 줄) → 도메인 줄. 주소 줄을 찾을 때만 그 사이 글을 빼요
            # (주소 줄 자체는 글자 수 규칙 A대로 세고, 링크로도 세요)
            card, j = [i], i - 1
            while j >= 0 and i - j <= 6:
                if URL.fullmatch(keys[j]):
                    skip.update(card)
                    break
                if keys[j]:
                    card.append(j)
                j -= 1
    return skip


# ── 모바일 보기 화면 (2026-11-27 실제 모바일 화면에서 본 모양, 우리 기준) ─────────────────────────────
# 블록마다 앞뒤 기준 줄이 있을 때만 빼요. 블로거가 본문에 직접 쓴 줄은 기준 줄 사이가 아니면 남아요.
PROFILE_LINES = {"프로파일", "프로필"}
DATE_ONLY = re.compile(r"\d{4}\.\s?\d{1,2}\.\s?\d{1,2}\.(\s*\d{1,2}:\d{2})?|\d+\s*(초|분|시간|일)\s*전|방금\s*전|어제.*")
MAP_ANCHOR = "© NAVER Corp."
MAP_TAIL = {"예약", "이 장소의 다른 글", "길찾기", "공유"}       # 끝 줄까지의 사이 줄(체크인 안내 등)도 함께 빠져요
DISTANCE = re.compile(r"\d+(\.\d+)?\s?(m|km)")
CARD_TITLE = re.compile(r".+\s-\s[^-]{1,30}")                                           # 링크 카드 제목 "글 제목 - 사이트"
TAG_LINE = re.compile(r"#[^\s#]+")
MORE_TAGS = re.compile(r"\+\d+")                                                        # 태그 칸의 "+11"
MAP_BACK = 12                 # 지도 블록 앞쪽 장소 정보(영업시간·주차 등)를 찾는 줄 수


def mobile_skip(keys: list[str], filled: list[int]) -> set[int]:
    """모바일 보기 화면의 블록 글 줄 번호 (서식이 있든 없든 써요. 서식에서는 이런 줄이 원래 없어요).
    - 지도: "© NAVER Corp." 줄을 기준으로 뒤의 장소 이름·주소·예약·"이 장소의 다른 글"(그 사이 줄 포함), 앞의 거리 줄,
      그리고 같은 장소 이름이 앞쪽에 다시 나오면 거기부터(영업시간·주차 안내 등).
    - 동영상: 길이 줄(00:02) 뒤 2줄 안에 "재생"이 있을 때, 길이·제목·재생·재생 수·좋아요·좋아요 수·다시 나오는 제목.
    - 상품·링크 카드: 도메인만 있는 줄 위 3줄 안에 "제목 - 사이트" 줄이 있으면 그 줄부터 도메인 줄까지.
    - 태그 칸: 글 맨 끝에 "#태그" 하나씩인 줄이 이어지고, "+숫자" 줄이 있거나 그 태그가 모두 본문에 이미 있을 때."""
    skip = set()
    pos = {i: n for n, i in enumerate(filled)}
    for n, i in enumerate(filled):
        k = keys[i]
        if k == MAP_ANCHOR:
            block = [i]
            after = filled[n + 1:n + 6]
            tail = max((m for m, j in enumerate(after) if keys[j] in MAP_TAIL), default=None)
            name = keys[after[0]] if after else None
            if tail is not None:
                block += after[:tail + 1]
            elif len(after) >= 2 and ADDRESS.fullmatch(keys[after[1]]):
                block += after[:2]
            else:
                name = None
            before = filled[max(0, n - MAP_BACK):n]
            if before and DISTANCE.fullmatch(keys[before[-1]]):
                block.append(before[-1])
            start = next((j for j in before if name and keys[j] == name), None)
            if start is not None:
                block += [j for j in before if j >= start]
            skip.update(block)
        elif DURATION.fullmatch(k):
            after = filled[n + 1:n + 3]
            play = next((m for m, j in enumerate(after) if keys[j] == "재생"), None)
            if play is None:
                continue
            titles = [keys[j] for j in after[:play]]
            block, m = [i] + after[:play + 1], n + play + 2
            for want in ("count", "좋아요", "count"):                # 재생 수 → 좋아요 → 좋아요 수
                if m < len(filled) and (keys[filled[m]].isdigit() if want == "count" else keys[filled[m]] == want):
                    block.append(filled[m])
                    m += 1
            if m < len(filled) and keys[filled[m]] in titles:        # 영상 아래에 다시 나오는 제목
                block.append(filled[m])
            skip.update(block)
        elif BARE_DOMAIN.fullmatch(k) and not URL.match(k):
            above = filled[max(0, n - 3):n]
            top = next((j for j in above if CARD_TITLE.fullmatch(keys[j])), None)
            if top is not None:
                skip.update(j for j in above if j >= top)
                skip.add(i)
    # 태그 칸: 글 맨 끝의 "+숫자"와 그 위 "#태그" 하나씩인 줄들
    end = len(filled)
    more = end > 0 and bool(MORE_TAGS.fullmatch(keys[filled[-1]]))
    if more:
        end -= 1
    run = []
    while end - 1 - len(run) >= 0 and TAG_LINE.fullmatch(keys[filled[end - 1 - len(run)]]):
        run.append(filled[end - 1 - len(run)])
    if run:
        earlier = " ".join(keys[j] for j in filled[:pos[run[-1]]]).split()
        if more or all(keys[j] in earlier for j in run):
            skip.update(run)
            if more:
                skip.add(filled[-1])
    return skip


# 글쓰기 화면에서 글만 복사했을 때 블록 글을 알아보는 모양 (2026-11-27, 우리 기준)
DURATION = re.compile(r"\d{1,2}:\d{2}(:\d{2})?")                                       # 동영상 길이 00:03
VIDEO_BLOCK_END = {"대표", "AI 활용 설정", "동영상 설명을 입력하세요."}
ADDRESS = re.compile(r"(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충청|충북|충남|전라|전북|전남|경상|경북|경남|제주)\S*"
                     r"(\s+\S+)*\s+\S+(시|군|구|읍|면|동|로|길)(\s+\S+)*")
SENTENCE_END = re.compile(r".*[.!?~요다]")


def editor_skip(lines: list[str]) -> set[int]:
    """글쓰기 화면에서 글만 복사했을 때 딸려 오는 블록 글의 줄 번호 (서식이 없을 때만 써요).
    - 동영상: 길이 줄(00:03)과 그 뒤 제목 줄(같은 제목이 두 번 올 수 있어요). 길이 줄 뒤 3줄 안에 "대표" 같은 편집 화면 줄이 있을 때만.
    - 링크 카드: "이미지 썸네일 삭제" 줄 뒤 도메인 줄까지의 제목·설명.
    - 지도: 주소 모양 줄(문장으로 끝나지 않는 것)과 바로 위 장소 이름 줄. 본문에 직접 쓴 주소 줄도 빠질 수 있어서
      글만 붙여 넣었을 때만 써요."""
    keys = [_key(l) for l in lines]
    filled = [i for i, k in enumerate(keys) if k]
    skip = set()
    for n, i in enumerate(filled):
        k = keys[i]
        if DURATION.fullmatch(k):
            after = filled[n + 1:n + 4]
            end = next((m for m, j in enumerate(after) if keys[j] in VIDEO_BLOCK_END), None)
            if end is not None:
                skip.add(i)
                skip.update(after[:end])                 # 길이 줄과 편집 화면 줄 사이 = 동영상 제목
        elif k == "이미지 썸네일 삭제":
            after = filled[n + 1:n + 5]
            dom = next((m for m, j in enumerate(after) if BARE_DOMAIN.fullmatch(keys[j]) and not URL.match(keys[j])), None)
            if dom is not None:
                skip.update(after[:dom + 1])
        elif len(k) <= 60 and ADDRESS.fullmatch(k) and not SENTENCE_END.fullmatch(k):
            skip.add(i)
            above = keys[filled[n - 1]] if n > 0 else ""
            if (above and len(above) <= 40 and not SENTENCE_END.fullmatch(above) and above not in MARKS
                    and above not in EDITOR_LINES and not URL.match(above)):
                skip.add(filled[n - 1])
    return skip


def guess_title(text: str) -> str | None:
    """보기 화면에서 복사한 글의 제목: [출처] 줄이 있으면 거기서, 없으면 머리 줄("프로파일", 모바일은 "프로필") 바로 위 줄.
    머리 줄은 글 맨 위 몇 줄 안에 있을 때만 봐요 (본문에 쓴 "프로필" 같은 낱말과 헷갈리지 않게). 없으면 None."""
    keys = [_key(l) for l in (text or "").split("\n")]
    for k in reversed(keys):
        if SOURCE_LINE.fullmatch(k):
            return k[len("[출처]"):].rsplit("|작성자", 1)[0].strip() or None
    filled = [i for i, k in enumerate(keys) if k]
    for i in filled[:HEADER_LINES]:
        if keys[i] in PROFILE_LINES:
            above = [x for x in keys[:i] if x]
            return above[-1] if above else None
    return None


def count_posts(text: str) -> int:
    """글 개수: 머리 줄("프로파일"/"프로필") 바로 다음(빈 줄 건너뜀)에 작성자 ・ 날짜 줄이 오거나,
    모바일처럼 작성자 이름 줄과 날짜 줄이 따로 오는 곳의 수. 보기 화면이 아니면 0이에요."""
    keys = [k for k in (_key(l) for l in (text or "").split("\n")) if k]

    def head(i: int) -> bool:
        if keys[i] not in PROFILE_LINES or i + 1 >= len(keys):
            return False
        return bool(AUTHOR_DATE.fullmatch(keys[i + 1])) or (
            i + 2 < len(keys) and len(keys[i + 1]) <= 20 and bool(DATE_ONLY.fullmatch(keys[i + 2])))
    return sum(head(i) for i in range(len(keys)))


# 앞 글자와 합쳐지는 글자: 결합 부호, 한글 가운뎃소리·끝소리 자모 (U+1160~11FF, U+D7B0~D7FF)
def _joins(ch: str) -> bool:
    return bool(unicodedata.combining(ch)) or "\u1160" <= ch <= "\u11ff" or "\ud7b0" <= ch <= "\ud7ff"


def nfc(text):
    """(NFC로 바꾼 글, 위치 표). 이미 NFC면 표는 None이에요.

    표는 (starts, ends): 바꾼 글의 k번째 글자가 원래 글의 starts[k]부터 ends[k] 전까지에서 왔다는 뜻이에요.
    합쳐지는 글자 묶음마다 따로 바꿔요. ponytail: 묶음 사이에서 합쳐지는 드문 글자는 합치지 않아요.
    """
    if text is None or unicodedata.is_normalized("NFC", text):
        return text, None
    out, starts, ends, i = [], [], [], 0
    while i < len(text):
        j = i + 1
        while j < len(text) and _joins(text[j]):
            j += 1
        piece = unicodedata.normalize("NFC", text[i:j])
        out.append(piece)
        starts += [i] * len(piece)
        ends += [j] * len(piece)
        i = j
    return "".join(out), (starts, ends)


def norm_url(url: str) -> str:
    return url.strip().rstrip("/")


def in_hashtag(text: str, pos: int) -> bool:
    """pos가 해시태그(#부터 공백 전까지) 안에 있는지."""
    while pos > 0 and not text[pos - 1].isspace():
        pos -= 1
        if text[pos] == "#":
            return True
    return False


def find_all(text: str, needle: str) -> list[int]:
    """겹치지 않게 앞에서부터 찾은 위치."""
    out, i = [], 0
    if not needle:
        return out
    while (i := text.find(needle, i)) != -1:
        out.append(i)
        i += len(needle)
    return out


def body_span(start: int, end: int) -> dict:
    return {"start": start, "end": end}


def span(field: str, start: int, end: int) -> dict:
    return {"start": start, "end": end, "field": "title"} if field == "title" else body_span(start, end)


def ordered(spans: list[dict]) -> list[dict]:
    """제목 먼저, 그다음 본문 앞에서부터. 같은 자리는 한 번만."""
    seen, out = set(), []
    for s in sorted(spans, key=lambda s: (s.get("field") != "title", s["start"], s["end"])):
        key = (s.get("field"), s["start"], s["end"])
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def fields(d: Draft, scope: str) -> tuple[list[tuple[str, str]], bool]:
    """scope에 맞는 (field, 글) 목록과, 제목을 몰라서 못 본 곳이 있는지."""
    if scope not in ("title", "body", "title_and_body"):
        raise ValueError("scope")
    out, unknown = [], False
    if scope != "body":
        if d.title is None:
            unknown = True
        else:
            out.append(("title", d.title))
    if scope != "title":
        out.append(("body", d.text))
    return out, unknown


def strs(value, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise ValueError("list of strings")
    if not value and not allow_empty:
        raise ValueError("empty list")
    return value


def number(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("number")
    return value


def quoted(items) -> str:
    return ", ".join(f'"{i}"' for i in items)


def capped(spans, note: str) -> tuple[list[dict], str]:
    """위치가 너무 많으면 앞에서부터 MAX_SPANS곳만 남기고, 그렇게 했다고 note에 적어요. 개수(actual)는 그대로예요."""
    spans = ordered(list(spans))
    if len(spans) > MAX_SPANS:
        return spans[:MAX_SPANS], f"{note} (위치는 앞에서부터 {MAX_SPANS}곳만 표시해요)"
    return spans, note


def result(cond: dict, status: str, note: str, spans=(), expected=None, actual=None, unit=None) -> dict:
    spans, note = capped(spans, note)
    return {
        "condition_id": cond["id"],
        "label": cond["label"],
        "status": status,
        "expected": expected,
        "actual": actual,
        "unit": unit,
        "note": note,
        "draft_spans": spans,
    }


# ── 조건별 규칙 ──────────────────────────────────────────────────────────

def rule_title_keyword(c, p, d):
    keywords = strs(p["keywords"])
    pick = p.get("pick", "any")
    need = len(keywords) if pick in ("each", "both") else 1
    if d.title is None:
        return result(c, "hold", TITLE_UNKNOWN, expected=need, unit="개")
    spans, found = [], []
    for k in keywords:
        hits = find_all(d.title, k)
        if hits:
            found.append(k)
            spans += [span("title", s, s + len(k)) for s in hits]
    if pick == "both":
        # 가이드가 "전부"인지 "하나 이상"인지 말하지 않은 4개 이상 목록: 두 해석을 같이 보여 줘요 (우리 기준)
        every, one = len(found) == len(keywords), bool(found)
        word = lambda ok: "지킴" if ok else "빠짐"
        note = (f"제목에 있는 키워드 {len(found)}개" + (f": {quoted(found)}" if found else "")
                + f". 전부 넣는 기준이면 {word(every)}, 하나 이상 기준이면 {word(one)}이에요. 가이드 기준 확인 필요")
        status = "kept" if every else "missing" if not one else "hold"
        return result(c, status, note, spans, need, len(found), "개")
    if len(found) >= need:
        return result(c, "kept", f"제목에 {quoted(found)} 있어요. {title_front_note(d, spans)}",
                      spans, need, len(found), "개")
    if need == 1:
        note = f"제목에 키워드가 없어요 ({quoted(keywords)} 중 1개 필요)"
    else:
        note = f"제목에 없는 키워드: {quoted(k for k in keywords if k not in found)}"
    return result(c, "missing", note, spans, need, len(found), "개")


def title_front_note(d: Draft, spans: list[dict]) -> str:
    """제목 키워드 위치 안내. 판정(상태)은 바꾸지 않아요."""
    if any(s["start"] < len(d.title) * TITLE_FRONT_SHARE for s in spans):
        return "제목 앞쪽에 있어요(안내, 우리 기준)"
    return "제목 뒤쪽에 있어요. 앞쪽에 둘지 확인해 보세요(안내, 우리 기준)"


def body_front_note(d: Draft, spans: list[dict]) -> str:
    """본문 키워드가 글 앞부분에 한 번은 나오는지 안내. 판정(상태)은 바꾸지 않아요."""
    body = [s["start"] for s in spans if s.get("field") != "title"]
    if not body:
        return ""
    # 앞의 빈칸(편집 화면 줄)과 빈 줄은 빼고, 첫 글자부터 BODY_FRONT_CHARS자까지를 앞부분으로 봐요
    first = len(d.text) - len(d.text.lstrip())
    where = f"본문 앞 {BODY_FRONT_CHARS}자"
    if min(body) < first + BODY_FRONT_CHARS:
        return f". 글 앞부분({where})에 키워드가 나와요(안내, 우리 기준)"
    return f". 글 앞부분({where})에는 키워드가 없어요. 확인해 보세요(안내, 우리 기준)"


FREE_EMPTY = "자율 키워드를 적어 주시면 함께 셀게요"


def rule_keyword_count(c, p, d):
    need = number(p["min"])
    if p.get("free") is True and not p.get("keywords"):
        # 강남맛집 자율 키워드: 블로거가 조건표에 적어야 셀 수 있어요
        return result(c, "hold", FREE_EMPTY, (), need, None, "회")
    keywords = strs(p["keywords"])
    texts, unknown = fields(d, p.get("scope", "body"))
    # 본문에 직접 쓴 #해시태그 안의 키워드도 본문 횟수에 세요 (2026-11-27 카티 결정). 맨 아래 태그 칸은 원고(draft_text)에
    # 없어서(서식) 또는 보기 화면 줄 빼기로(글자만) 세지 않아요. 결과에는 "본문 글 N번 + 해시태그 M번"으로 나눠 보여 줘요.
    found = {k: [(span(f, s, s + len(k)), in_hashtag(t, s)) for f, t in texts for s in find_all(t, k)] for k in keywords}
    per = {k: [s for s, _ in v] for k, v in found.items()}
    tags = {k: sum(tag for _, tag in v) for k, v in found.items()}

    def told(k: str) -> str:
        """"키워드" N회, 해시태그가 섞이면 (본문 글 N번 + 해시태그 M번)."""
        n, m = len(per[k]), tags[k]
        return f'"{k}" {n}회' + (f"(본문 글 {n - m}번 + 해시태그 {m}번)" if m else "")

    def tag_filled(ks: list[str]) -> str:
        """해시태그를 빼면 기준에 못 미치는 키워드 안내 (판정은 지킴 그대로)."""
        short = [k for k in ks if len(per[k]) - tags[k] < need <= len(per[k])]
        if not short:
            return ""
        how = "해시태그로만 채웠어요" if all(len(per[k]) == tags[k] for k in short) else "해시태그로 기준을 채웠어요"
        return f". {quoted(short)}는 {how}. 본문 글에도 넣으면 더 자연스러워요"

    if p.get("pick") == "both":
        # 가이드가 키워드마다인지 하나만인지 말하지 않았을 때: 두 해석을 같이 보여 줘요 (우리 기준)
        counts = {k: len(per[k]) for k in keywords}
        every, one = all(n >= need for n in counts.values()), any(n >= need for n in counts.values())
        actual = max(counts.values())
        spans = [s for v in per.values() for s in v]
        word = lambda good: "지킴" if good else "빠짐"
        note = ("키워드별: " + ", ".join(told(k) for k in keywords)
                + f". 키워드마다 {need}회 기준이면 {word(every)}, 하나만 {need}회 기준이면 {word(one)}이에요. 가이드 기준 확인 필요")
        status = "kept" if every else "missing" if not one else "hold"
        note += tag_filled([k for k in keywords if counts[k] >= need])
        if status != "kept" and unknown:
            status = "hold"
        return result(c, status, note + body_front_note(d, spans), spans, need, actual, "회")
    if p.get("pick") == "sum":
        # 레뷰 "본문 키워드 중 1개 이상을 선택하여 총 5회 이상": 고른 키워드의 합계로 세요
        actual = sum(len(v) for v in per.values())
        spans = [s for v in per.values() for s in v]
        ok = actual >= need
        used = ", ".join(told(k) for k in keywords if per[k])
        if not used:
            note = f"키워드가 하나도 없어요 ({quoted(keywords)} 중 골라 합계 {need}회 이상)"
        else:
            note = f"키워드 합계 {actual}회 ({used})" + ("" if ok else f". {need - actual}회 더 필요해요")
            if ok and actual - sum(tags.values()) < need:
                note += ". 해시태그를 빼면 기준에 못 미쳐요. 본문 글에도 넣으면 더 자연스러워요"
    elif p.get("pick", "any") == "each":
        short = [k for k in keywords if len(per[k]) < need]
        actual = min(len(v) for v in per.values())
        spans = [s for v in per.values() for s in v]
        ok = not short
        note = "모든 키워드가 기준을 넘어요" + tag_filled(keywords) if ok else "기준보다 적은 키워드: " + ", ".join(
            told(k) for k in short)
    else:
        actual = max(len(v) for v in per.values())
        top = [k for k in keywords if len(per[k]) == actual]      # 동률이면 전부
        spans = [s for k in top for s in per[k]]
        each_word = " 각" if len(top) > 1 else ""
        ok = actual >= need
        if ok:
            note = f"{quoted(top)}{each_word} {actual}회 있어요"
            if len(keywords) == 1 and tags[top[0]]:
                note += f" (본문 글 {actual - tags[top[0]]}번 + 해시태그 {tags[top[0]]}번)"
        elif len(keywords) == 1:
            note = f"{need - actual}회 더 필요해요"
        elif actual == 0:
            note = f"키워드가 하나도 없어요 ({quoted(keywords)} 중 1개를 {need}회 이상)"
        else:
            note = f"가장 많이 쓴 키워드는 {quoted(top)}{each_word} {actual}회예요. {need - actual}회 더 필요해요"
        if len(keywords) > 1:       # 키워드별 횟수를 모두 보여 주고 기준을 넘은 것을 표시해요
            note += ". 키워드별: " + ", ".join(
                told(k) + (f"({need}회 이상)" if len(per[k]) >= need else "") for k in keywords)
        if ok:
            note += tag_filled(top)
    if not ok and unknown:
        return result(c, "hold", f"본문만으로는 모자라요. {TITLE_UNKNOWN}", spans, need, actual, "회")
    return result(c, "kept" if ok else "missing", note + body_front_note(d, spans), spans, need, actual, "회")


TEXT_ONLY = "글자만으로 센 값이에요. 서식(HTML)이 없어서 보기 화면 줄은 규칙으로 뺐어요"


def rule_length(c, p, d):
    """본문 글 블록의 글자. 공백 포함·제외를 둘 다 적고, 가이드가 정한 기준(없으면 공백 포함)으로 판정해요."""
    need = number(p["min"])
    count_spaces = p.get("count_spaces")
    with_spaces = count_spaces is not False
    actual = d.chars_with_spaces if with_spaces else d.chars
    kind = "공백 포함" if with_spaces else "공백 제외"
    note = f"공백 포함 {d.chars_with_spaces}자(줄바꿈은 세지 않아요), 공백 제외 {d.chars}자"
    note += f". {kind} 기준으로 판정했어요" + (" (가이드가 공백 기준을 정하지 않음)" if count_spaces is None else "")
    if actual < need:
        note += f". {need - actual}자 더 필요해요"
    note += ". 본문 글 블록의 글자만 셌어요 ([사진] 줄, 링크 카드·동영상 제목 제외)"
    if d.text_mode:
        note += f". {TEXT_ONLY}"
    if d.editor_lines:
        note += f". \"대표사진 삭제\" 같은 편집 화면 줄 {d.editor_lines}개는 세지 않았어요"
    if d.viewer_lines:
        note += f". 보기 화면에서 딸려 온 줄(제목·작성자·태그 목록·링크 카드 글 등) {d.viewer_lines}개는 세지 않았어요"
    if d.caption_lines:
        note += f". 사진 설명 {d.caption_lines}줄은 " + ("셌어요" if d.count_captions else "세지 않았어요")
    return result(c, "kept" if actual >= need else "missing", note, (), need, actual, "자")


def count_rule(key: str, name: str, unit: str):
    def rule(c, p, d):
        need = number(p["min"])
        actual = d.req.get(key)
        seen = d.editor_photos if key == "photo_count" else 0       # 편집 화면 줄로 센 사진 수 (확실하지 않은 값)
        if actual is None and not seen:
            return result(c, "hold", f"{name} 수를 몰라서 판단 보류예요. {name} 수를 넣으면 판정해요", (), need, None, unit)
        source = f"입력한 {name} 수 기준" if d.by_user else f"자동으로 센 {name} 수 기준"
        if actual is None:          # 받은 숫자가 없을 때만 편집 화면 줄 수를 써요
            actual, source = seen, f"\"대표사진\" 줄로 센 {name} 수 기준. 다르면 {name} 수를 직접 넣어 주세요"
        elif seen and seen != actual:
            source += f". 원고의 \"대표사진\" 줄은 {seen}개라서 서로 달라요"
        if key == "photo_count" and p.get("include_video") is True:
            # 강남맛집 "동영상을 포함하여 사진은 최소 15장": 동영상도 장수에 넣어요
            video = d.req.get("video_count")
            if video is None:
                return result(c, "hold", "동영상을 포함해 세는 조건인데 동영상 수를 몰라서 판단 보류예요. 동영상 수를 넣으면 판정해요",
                              (), need, None, unit)
            actual += video
            source += f", 동영상 {video}개 포함"
        top = p.get("max")
        top = top if isinstance(top, int) and not isinstance(top, bool) and top >= need else None
        if top is not None and actual > top:
            return result(c, "missing", f"{actual - top}{unit} 많아요. 최대 {top}{unit}까지예요 ({source})", (), need, actual, unit)
        limit = f", 최대 {top}{unit}" if top is not None else ""
        if actual >= need:
            return result(c, "kept", f"{name} {actual}{unit}{limit} ({source})", (), need, actual, unit)
        return result(c, "missing", f"{need - actual}{unit} 더 필요해요{limit} ({source})", (), need, actual, unit)
    return rule


def rule_map(c, p, d):
    has_map = d.req.get("has_map")
    position = p.get("position")
    if has_map is None:
        return result(c, "hold", "지도가 있는지 몰라서 판단 보류예요. 지도 여부를 넣으면 판정해요")
    if not has_map:
        note = "지도를 첨부하지 않았다고 입력했어요" if d.by_user else "서식에서 지도를 찾지 못했어요 (자동으로 찾은 결과)"
        return result(c, "missing", note)
    if position is None:
        return result(c, "kept", "지도가 있어요")
    if position != "bottom":
        return result(c, "hold", "이 위치 조건은 아직 판정 규칙이 없어서 판단 보류예요")
    starts = d.map_starts
    if not starts:
        return result(c, "hold", "지도는 있지만 글 안 위치를 몰라서 \"하단\"인지는 판단 보류예요")
    last = max(starts)
    spans = [body_span(last, last + len("[지도]"))]
    rule = "지도 뒤에 글 문단이 없으면 하단으로 봐요 (해시태그 줄, 주소 줄, 사진 줄은 글로 안 봐요)"
    if d.text_after(last):
        return result(c, "missing", f"지도 뒤에 글이 더 있어요. {rule}", spans)
    return result(c, "kept", f"지도가 글 맨 아래에 있어요. {rule}", spans)


def rule_link(c, p, d):
    need = number(p.get("min", 1))
    url = p.get("url")
    if url:
        hits = [l for l in d.links if l["url"] and norm_url(l["url"]) == norm_url(url)]
        spans = [l["span"] for l in hits if l["span"]]
        if hits:
            return result(c, "kept", "가이드가 정한 주소의 링크가 있어요", spans, 1, 1, "개")
        actual, note = 0, "가이드가 정한 주소의 링크를 찾지 못했어요"
    else:
        actual = len(d.links)
        spans = [l["span"] for l in d.links if l["span"]]
        if actual >= need:
            return result(c, "kept", f"링크 {actual}개 (같은 주소는 1개로 셈)", spans, need, actual, "개")
        note = f"링크 {need - actual}개 더 필요해요 (같은 주소는 1개로 셈)"
    if d.text_mode:
        return result(c, "hold", "글만 붙여 넣어서 링크 카드는 확인할 수 없어요. 본문에 적힌 주소만 셌어요",
                      (), need if not url else 1, actual, "개")
    return result(c, "missing", note, (), need if not url else 1, actual, "개")


def rule_hashtag(c, p, d):
    tags = [t if t.startswith("#") else "#" + t for t in strs(p["tags"])]
    need = len(tags) if p.get("pick", "each") == "each" else 1
    have = {(h if h.startswith("#") else "#" + h).lower() for h in d.req.get("hashtags") or []}
    found = [t for t in tags if t.lower() in have]
    spans = []
    for t in found:
        for s in find_all(d.text, t):
            after = d.text[s + len(t):s + len(t) + 1]
            if not WORD_CHAR.match(after) and after != "_":
                spans.append(body_span(s, s + len(t)))
    if len(found) >= need:
        return result(c, "kept", f"{', '.join(found)} 태그가 있어요", spans, need, len(found), "개")
    if need == 1:
        note = f"태그가 없어요 ({', '.join(tags)} 중 1개 필요). 본문과 입력한 태그에서 찾았어요"
    else:
        note = f"없는 태그: {', '.join(t for t in tags if t not in found)}. 본문과 입력한 태그에서 찾았어요"
    return result(c, "missing", note, spans, need, len(found), "개")


def rule_exact_phrase(c, p, d):
    allowed = p.get("allowed")
    forbidden = strs(p.get("forbidden") or [], allow_empty=True)
    texts, unknown = fields(d, p.get("scope", "title_and_body"))
    bad_found = [x for x in forbidden if any(find_all(t, x) for _, t in texts)]
    bad = [span(f, s, s + len(x)) for x in forbidden for f, t in texts for s in find_all(t, x)]
    if bad:
        return result(c, "missing", f"쓰면 안 되는 표기가 {len(bad)}곳 있어요: {quoted(bad_found)}", bad)
    if unknown:
        return result(c, "hold", TITLE_UNKNOWN)
    good = [span(f, s, s + len(allowed)) for f, t in texts for s in find_all(t, allowed)] if allowed else []
    if good:
        return result(c, "kept", f'"{allowed}"(으)로 썼어요', good)
    return result(c, "kept", "쓰면 안 되는 표기가 없어요")


def embedded_word(text: str, start: int, length: int) -> str | None:
    """금지어가 다른 단어 안에 들어 있으면 그 단어를, 아니면 None."""
    left = start
    while left > 0 and WORD_CHAR.match(text[left - 1]):
        left -= 1
    right = start + length
    while right < len(text) and WORD_CHAR.match(text[right]):
        right += 1
    tail = text[start + length:right]
    if left == start and (not tail or tail.startswith(phrases.PARTICLES)):
        return None
    return text[left:right]


def rule_banned_terms(c, p, d):
    terms = strs(p["terms"])
    texts, unknown = fields(d, p.get("scope", "title_and_body"))
    spans, counts, inside = [], {}, []
    for term in terms:
        for f, t in texts:
            for s in find_all(t, term):
                spans.append(span(f, s, s + len(term)))
                counts[term] = counts.get(term, 0) + 1
                word = embedded_word(t, s, len(term))
                if word:
                    inside.append(word)
    if spans:
        note = "금지어가 있어요: " + ", ".join(f'"{t}" {n}곳' for t, n in counts.items())
        if inside:
            words = quoted(dict.fromkeys(inside))
            note += f". 그중 {len(inside)}곳은 다른 단어 안에 들어 있어요: {words}"
        return result(c, "missing", note, spans, 0, len(spans), "곳")
    if unknown:
        return result(c, "hold", f"본문에는 금지어가 없어요. {TITLE_UNKNOWN}", (), 0, 0, "곳")
    return result(c, "kept", "금지어가 없어요", (), 0, 0, "곳")


def rule_required_phrase(c, p, d):
    phrase = p["phrase"]
    if not isinstance(phrase, str) or not phrase.strip():
        raise ValueError("phrase")
    texts, unknown = fields(d, p.get("scope", "body"))
    spans = [span(f, s, s + len(phrase)) for f, t in texts for s in find_all(t, phrase)]
    if not spans:
        if unknown:
            return result(c, "hold", f"본문에는 필수 문구가 없어요. {TITLE_UNKNOWN}")
        return result(c, "missing", f'필수 문구가 없어요: "{phrase}"')
    if p.get("after"):
        return result(c, "hold", f'문구는 있어요. "{p["after"]}" 아래에 있는지는 판단 보류예요. {CHECK_YOURSELF}', spans)
    return result(c, "kept", "필수 문구가 있어요", spans)


def disclosure_hits(d: Draft, guide_phrases: list[str], use_terms: bool) -> list[dict]:
    """대가성 표시로 보이는 곳. 가이드 문구는 그 문구 자리, 표현 목록은 그 표현이 든 문장(제목은 전체)."""
    hits = []
    for phrase in guide_phrases:
        if d.title is not None:
            hits += [span("title", s, s + len(phrase)) for s in find_all(d.title, phrase)]
        hits += [body_span(s, s + len(phrase)) for s in find_all(d.text, phrase)]
    if use_terms:
        for term in phrases.DISCLOSURE_TERMS:
            if d.title is not None and term in d.title:
                hits.append(span("title", 0, len(d.title)))
            hits += [body_span(*d.sentence_at(s)) for s in find_all(d.text, term)]
    return ordered(hits)


def is_top(d: Draft, s: dict) -> bool:
    return s.get("field") == "title" or d.in_first_para(s["start"])


def where_top(s: dict) -> str:
    return "제목에 있어요" if s.get("field") == "title" else "본문 첫 문단에 있어요"


BANNER_TOP_NOTE = "대가성 표시 있음(맨 위 배너). 글 맨 위에 체험단 배너가 있어요"
BANNER_RULE = "\"맨 위\" = 첫 사진 블록이나 첫 3블록 안(우리 기준)"
BANNER_UNSEEN = "대가성 문구를 찾지 못했어요. 배너 그림을 넣었다면 괜찮아요"


def banner_unseen(d: Draft, phrase) -> str:
    """글만 붙여 넣어서 배너 그림을 못 볼 때 붙이는 안내 (가이드가 문구를 정했으면 배너로 대신할 수 없어요)."""
    return ". 맨 위에 체험단 배너 그림을 넣었다면 괜찮아요" if d.banner_top is None and not phrase else ""


def rule_disclosure(c, p, d):
    phrase = p.get("phrase")
    position = p.get("position")
    if position not in (None, "top"):
        return result(c, "hold", "이 위치 조건은 아직 판정 규칙이 없어서 판단 보류예요")
    hits = disclosure_hits(d, [phrase] if phrase else [], use_terms=not phrase)
    by_list = "" if phrase else " (대가성 표현 목록은 우리 기준)"
    top = [s for s in hits if is_top(d, s)]
    if position is None and hits:
        return result(c, "kept", f"대가성 문구가 있어요{by_list}", hits[:1])
    if top:
        return result(c, "kept", f"{where_top(top[0])}{by_list}", top[:1])
    if d.banner_top and not phrase:        # 가이드가 문구를 정하지 않았으면 맨 위 체험단 배너도 대가성 표시예요
        return result(c, "kept", BANNER_TOP_NOTE)
    if hits:
        return result(c, "missing", f"대가성 문구가 첫 부분이 아니라 뒤쪽에 있어요{by_list}" + banner_unseen(d, phrase), hits)
    if not phrase and d.banner_top is None:
        return result(c, "hold", BANNER_UNSEEN + (f". {TITLE_UNKNOWN}" if d.title is None else ""))
    if d.title is None:
        return result(c, "hold", f"본문에서 대가성 문구를 찾지 못했어요{by_list}. {TITLE_UNKNOWN}")
    note = "가이드가 정한 대가성 문구를 찾지 못했어요" if phrase else f"대가성 문구를 찾지 못했어요{by_list}"
    if phrase and any(is_top(d, s) for s in disclosure_hits(d, [], use_terms=True)):
        note += ". 첫 부분에 대가성 표현은 있지만 가이드 문구와 같지 않아요"
    return result(c, "missing", note)


RULES = {
    "title_keyword": rule_title_keyword,
    "keyword_count": rule_keyword_count,
    "length": rule_length,
    "photo_count": count_rule("photo_count", "사진", "장"),
    "video_count": count_rule("video_count", "동영상", "개"),
    "map": rule_map,
    "link": rule_link,
    "hashtag": rule_hashtag,
    "exact_phrase": rule_exact_phrase,
    "banned_terms": rule_banned_terms,
    "required_phrase": rule_required_phrase,
    "disclosure": rule_disclosure,
}

# 셀 수 없는 조건은 12/1 범위에서 AI로 판단하지 않아요. 판단 보류로 두고 직접 확인하라고 알려요.
CHECK_YOURSELF = "이 조건은 직접 확인해 주세요"
HOLD_NOTES = {
    "photo_count": f"사진에 무엇이 찍혔는지는 확인할 수 없어요. {CHECK_YOURSELF}",
    "outside_draft": f"원고 밖 조건이라 여기서는 확인할 수 없어요. {CHECK_YOURSELF}",
}
HOLD_DEFAULT = f"셀 수 없는 조건이라 판단 보류예요. {CHECK_YOURSELF}"
# AI가 낸 조건을 코드가 확인하지 못해 "직접 봐 주세요" 안내로 남긴 조건 (params.unverified)
HOLD_UNVERIFIED = "가이드에서 조건을 제대로 읽지 못했어요. 가이드의 이 부분을 직접 보고 원고를 확인해 주세요"


def rule_hold(c, p, d):
    """셀 수 없는 조건(outside_draft, judgment): 판단 보류."""
    return result(c, "hold", HOLD_NOTES.get(c.get("type"), HOLD_DEFAULT))


RULES["outside_draft"] = RULES["judgment"] = rule_hold

# 기준 숫자(min)가 꼭 있어야 판정할 수 있는 조건. 없으면 1 같은 값을 지어내지 않고 판단 보류예요
# (감자님 be/counter.py의 "기준 횟수가 없어서 판단하지 않아요" 규칙)
NEEDS_MIN = {"keyword_count": "회", "length": "자", "photo_count": "장", "video_count": "개"}
NO_MIN = "기준 숫자가 없어서 판단 보류예요. 조건표에서 숫자를 넣어 주세요"


def judge(cond: dict, d: Draft) -> dict:
    kind = cond.get("type")
    params = cond.get("params") or {}
    if params.get("unverified"):
        return result(cond, "hold", HOLD_UNVERIFIED)
    if not cond.get("countable"):
        return rule_hold(cond, params, d)
    rule = RULES.get(kind)
    if rule is None:
        return result(cond, "hold", "아직 판정 규칙이 없는 조건이라 판단 보류예요")
    if kind in NEEDS_MIN and params.get("min") is None:
        return result(cond, "hold", NO_MIN, unit=NEEDS_MIN[kind])
    try:
        out = rule(cond, params, d)
        if params.get("needs_review") is True:
            out["note"] += ". 기준 숫자는 가이드에서 확인하지 못한 값이에요. 조건표에서 확인해 주세요"
        return out
    except (KeyError, TypeError, ValueError):
        return result(cond, "hold", "조건 값이 형식과 달라서 판단 보류예요. 조건표에서 값을 확인해 주세요")


# ── 원칙 점검 (네이버·공정위) ────────────────────────────────────────────

def principle(rule_id: str, label: str, status: str, note: str, spans=()) -> dict:
    spans, note = capped(spans, note)
    return {
        "rule_id": rule_id,
        "label": label,
        "status": status,
        "basis": BASIS[rule_id],
        "note": note,
        "draft_spans": spans,
    }


def countable(conds: list[dict], kind: str) -> list[dict]:
    return [c for c in conds if c.get("type") == kind and c.get("countable") and isinstance(c.get("params"), dict)]


def p1(conds, d):
    label = "대가성 표시가 제목 또는 첫 부분에 있음"
    rule = "\"첫 부분\" = 본문 첫 문단(우리 기준)"
    guide_phrases = [c["params"]["phrase"] for c in countable(conds, "disclosure")
                     if isinstance(c["params"].get("phrase"), str) and c["params"]["phrase"].strip()]
    hits = disclosure_hits(d, guide_phrases, use_terms=True)
    top = [s for s in hits if is_top(d, s)]
    if top:
        return principle("p1", label, "kept", f"{where_top(top[0])}. {rule}", top[:1])
    if d.banner_top:
        return principle("p1", label, "kept", f"{BANNER_TOP_NOTE}. {BANNER_RULE}")
    if hits:
        return principle("p1", label, "missing",
                         f"대가성 표시가 첫 부분에 없고 뒤쪽에 있어요. {PATTERN_NOTE}. {rule}" + banner_unseen(d, None), hits)
    if d.banner_top is None:            # 글만 붙여 넣어서 배너 그림을 볼 수 없어요. 없다고 하지 않아요
        return principle("p1", label, "hold", BANNER_UNSEEN + (f". {TITLE_UNKNOWN}" if d.title is None else ""))
    if d.title is None:
        return principle("p1", label, "hold", f"본문에서 대가성 표시를 찾지 못했어요. {TITLE_UNKNOWN}")
    return principle("p1", label, "missing",
                     f"대가성 표시를 찾지 못했어요. {PATTERN_NOTE}. 대가성 표현 목록은 우리 기준이에요")


def p2(d):
    label = "모호한 대가성 표현 없음"
    spans = []
    for term in phrases.VAGUE_TERMS:
        pattern = re.compile(r"\s*".join(re.escape(ch) for ch in term if not ch.isspace()))
        if d.title is not None:
            spans += [span("title", m.start(), m.end()) for m in pattern.finditer(d.title)]
        spans += [body_span(m.start(), m.end()) for m in pattern.finditer(d.text)]
    if spans:
        return principle("p2", label, "missing",
                         f"\"받을 수 있음\" 같은 조건부 표현이 있어요. {FTC_NOTE}. 표현 목록은 우리 기준이에요", spans)
    return principle("p2", label, "kept", "\"수수료를 지급받을 수 있음\" 같은 조건부 표현이 없어요")


def p3(conds, d):
    label = "키워드 과다 반복 없음"
    limits: dict[str, int] = {}
    for c in countable(conds, "keyword_count"):
        try:
            need = number(c["params"]["min"])
            for k in strs(c["params"]["keywords"]):
                limits[k] = max(limits.get(k, 0), need)
        except (KeyError, TypeError, ValueError):
            continue
    if not limits:
        return principle("p3", label, "hold", "가이드에 키워드 횟수 조건이 없어서 판단 보류예요")

    spans, notes, most = [], [], None
    for k, need in limits.items():
        # 해시태그 안의 키워드는 반복으로 치지 않아요 (가이드가 태그에 넣으라고 한 것일 수 있어요)
        hits = [s for s in find_all(d.text, k) if not in_hashtag(d.text, s)]
        if most is None or len(hits) > most[1]:
            most = (k, len(hits), need)
        if len(hits) > need * KEYWORD_REPEAT_FACTOR:
            spans += [body_span(s, s + len(k)) for s in hits]
            notes.append(f'"{k}" {len(hits)}회로 가이드 요구({need}회)의 {KEYWORD_REPEAT_FACTOR}배를 넘어요')
        # 키워드가 든 문장 번호를 찾고, 번호가 이어진 문장들의 키워드 위치를 모아요.
        # (문장마다 전부 훑지 않아요. 큰 원고와 많은 키워드로 서버를 붙잡는 것을 막아요.)
        where: dict[int, list[int]] = {}
        for s in hits:
            i = bisect.bisect_right(d.sentence_starts, s) - 1
            if i >= 0 and s < d.sentences[i][1]:
                where.setdefault(i, []).append(s)
        twice = [body_span(s, s + len(k)) for i in sorted(where) if i + 1 in where or i - 1 in where for s in where[i]]
        if twice:
            spans += twice
            notes.append(f'이어진 두 문장에 "{k}"가 반복돼요')
    if notes:
        return principle("p3", label, "missing", f"{'. '.join(notes)}(우리 기준). {KEYWORD_NOTE}", spans)
    k, n, need = most
    return principle("p3", label, "kept",
                     f'"{k}" {n}회. 가이드 요구({need}회)의 {KEYWORD_REPEAT_FACTOR}배를 넘으면 알려요(우리 기준)')


def p4(conds, d):
    label = "외부 링크 과다 없음"
    required = 0
    for c in countable(conds, "link"):
        try:
            required += 1 if c["params"].get("url") else number(c["params"].get("min", 1))
        except ValueError:
            continue
    extra = max(0, len(d.links) - required)
    rule = f"가이드 필수 링크 밖의 링크가 {EXTRA_LINK_LIMIT}개를 넘으면 알려요(우리 기준)"
    if extra > EXTRA_LINK_LIMIT:
        return principle("p4", label, "missing", f"외부 링크 {extra}개. {rule}. {NAVER_NOTE}",
                         [l["span"] for l in d.links if l["span"]])
    return principle("p4", label, "kept", f"외부 링크 {extra}개. {rule}")


def p5(d):
    label = "사진에 비해 글이 충분함"
    photos = d.req.get("photo_count")
    rule = f"{CHARS_PER_PHOTO}자보다 적으면 알려요(우리 기준)"
    if photos is None:
        return principle("p5", label, "hold", "사진 수를 몰라서 판단 보류예요. 사진 수를 넣으면 판정해요")
    if photos == 0:
        return principle("p5", label, "kept", f"사진이 없어요. 사진 1장당 글자 수가 {rule}")
    per = d.chars / photos
    if per < CHARS_PER_PHOTO:
        return principle("p5", label, "missing", f"사진 1장당 약 {round(per)}자. {rule}. {NAVER_NOTE}")
    return principle("p5", label, "kept", f"사진 1장당 약 {round(per)}자. {rule}")


def p6():
    """기자단 가이드일 때만 나와요. 셀 수 없는 판단이라 AI 후보 문장이 붙기 전까지 판단 보류예요."""
    return principle("p6", "기자단의 체험 표현", "hold",
                     f"기자단 가이드예요. 직접 체험한 것처럼 읽히는 표현이 있는지는 판단 보류예요. {CHECK_YOURSELF}")


# "AI 활용" 표시 줄 (p7). 가이드에 생성형 AI 금지 조건이 있으면 그 조건 결과에 붙이고, 없으면 "참고"로만 보여요.
AI_BAN = re.compile(r"(생성형\s*)?AI.{0,25}(금지|불가|사용하지|쓰지|이용하지)", re.I)
AI_MARK_NOTE = "본문에 \"AI 활용\" 표시 줄이 있어요. 이 표시가 네이버가 붙이는 것인지는 확인이 필요해요"


def ai_ban_condition(conds: list[dict]) -> dict | None:
    """가이드의 생성형 AI 금지 조건 (라벨, 물음, 원고 밖 내용, 가이드 원문 중 하나에 금지 문장이 있으면)."""
    for c in conds:
        p = c.get("params") if isinstance(c.get("params"), dict) else {}
        quotes = [c.get("guide_quote") or {}, *(c.get("extra_quotes") or [])]
        texts = [c.get("label"), p.get("question"), p.get("what"), *(q.get("text") for q in quotes if isinstance(q, dict))]
        if any(isinstance(t, str) and AI_BAN.search(t) for t in texts):
            return c
    return None


def p7(d):
    """가이드에 생성형 AI 금지 조건이 없을 때의 "참고" 항목. 상태는 판단 보류예요."""
    spans = [body_span(s, e) for s, e in d.ai_marks]
    return principle("p7", "참고: \"AI 활용\" 표시", "hold",
                     f"참고: {AI_MARK_NOTE}. 가이드에는 생성형 AI 금지 조건이 없어요. 체험단 가이드는 생성형 AI 사용을 막는 경우가 많아요",
                     spans)


# ── 도움이 될 팁 ─────────────────────────────────────────────────────────
# 판정이 아니에요. results·principles·summary에 넣지 않고 tips에만 담아서, 팁이 있어도 "고칠 곳" 수는 그대로예요.
# 가이드가 생성형 AI 이용을 막는 경우가 많아서 문장을 써 주지 않아요. 위치와, 빈칸(○○)이 있는 짧은 고정 틀만 알려요.
# 키워드 조건이 "빠짐"으로 판정됐을 때만 만들어요 (판단 보류면 모자란지 알 수 없어서 만들지 않아요).
TIP_KEYWORDS = 3          # pick이 each인 조건 하나에서 자리 추천 팁을 만드는 키워드 수 (우리 기준)
TIP_PLACES = 2            # 자리 추천 팁 하나가 짚는 문단 수
TIP_MIN_CHARS = 10        # 이보다 짧은 문단(공백 제외)은 짚지 않아요 (우리 기준)
TIP_MAX = 10              # 한 번에 돌려주는 팁 수의 상한 (우리 기준). 큰 입력으로 서버를 붙잡는 것도 막아요
TIP_SELF = "문장은 직접 써 주세요. 아래 짧은 틀은 참고용이고 ○○은 직접 채워요"


def squash(text: str) -> tuple[str, list[int]]:
    """띄어쓰기(공백·탭)를 뺀 글과, 그 글자마다의 원래 위치. 줄바꿈은 남겨서 줄을 넘어 찾지 않아요."""
    at = [i for i, ch in enumerate(text) if ch not in " \t\u00a0"]
    return "".join(text[i] for i in at), at


def loose_hits(squashed: tuple[str, list[int]], keyword: str) -> list[tuple[int, int]]:
    """띄어쓰기만 다른 형태까지 찾은 키워드 자리 (start, end). "부산맛집" → "부산 맛집"도 찾아요.
    정규식을 쓰지 않고 글자 찾기(find)로만 해요. 긴 키워드와 큰 원고로 서버를 붙잡는 것을 막아요."""
    text, at = squashed
    needle = "".join(keyword.split())
    return [(at[i], at[i + len(needle) - 1] + 1) for i in find_all(text, needle)]


def josa(word: str, kind: str) -> str:
    """받침을 보고 고른 조사. kind: "ro"(로/으로), "eul"(을/를). 한글로 끝나지 않으면 둘 다 적어요."""
    last = word[-1]
    if not "가" <= last <= "힣":
        return {"ro": "(으)로", "eul": "을(를)"}[kind]
    final = (ord(last) - 0xAC00) % 28
    if kind == "ro":
        return "로" if final in (0, 8) else "으로"        # 받침이 없거나 ㄹ
    return "을" if final else "를"


def region_of(keyword: str) -> str | None:
    """키워드 앞머리의 지역 이름 ("부산맛집" → "부산", "솔밭동 카페" → "솔밭동"). 아니면 None (우리 기준)."""
    k = "".join(keyword.split())
    for name in sorted(phrases.REGIONS, key=len, reverse=True):
        if k.startswith(name) and len(k) > len(name):
            return name
    for kind in phrases.PLACE_KINDS:
        head = k[:-len(kind)] if k.endswith(kind) else ""
        if len(head) >= 2 and head.endswith(phrases.REGION_ENDS):
            return head
    return None


def short_keywords(c: dict, r: dict, d: Draft) -> tuple[list[tuple[str, int]], list[tuple[str, str]]]:
    """빠짐으로 판정된 키워드 조건에서 기준에 못 미친 (키워드, 모자란 횟수)와 찾아본 글. 아니면 빈 목록.
    세는 법은 판정 규칙(rule_keyword_count, rule_title_keyword)과 같아요."""
    if r["status"] != "missing" or not c.get("countable") or c.get("type") not in ("keyword_count", "title_keyword"):
        return [], []
    p = c["params"]
    keywords = list(dict.fromkeys(p["keywords"]))
    if c["type"] == "title_keyword":
        return [(k, 1) for k in keywords if k not in d.title], [("title", d.title)]
    texts, _ = fields(d, p.get("scope", "body"))
    counts = {k: sum(len(find_all(t, k)) for _, t in texts) for k in keywords}
    if p.get("pick") == "sum":          # 합계 기준: 어느 키워드를 넣어도 돼요. 많이 쓴 것부터
        lack = p["min"] - sum(counts.values())
        return [(k, lack) for k in sorted(keywords, key=lambda k: -counts[k])], texts
    return [(k, p["min"] - n) for k, n in counts.items() if n < p["min"]], texts


def tip_places(d: Draft, keyword: str, starts: list[int]) -> list[dict]:
    """키워드가 어울리는 문단 1~2곳 (우리 기준: 지역 이름, "다녀왔"·"추천" 같은 낱말, 첫·끝 문단).
    starts는 본문에서 이 키워드(띄어쓰기만 다른 형태 포함)가 있는 자리예요.
    ponytail: 낱말 목록으로 고르는 단순한 방법이에요. 가게 이름은 조건 목록에 없어서 보지 않아요.
    - 키워드가 이미 있는 문단, 대가성 문구 줄, 해시태그·주소만 있는 줄, [사진] 줄은 빼요.
    - 키워드가 든 문장 바로 옆 문장도 빼요. 거기에 넣으면 p3 "이어진 두 문장에 같은 키워드"에 걸려요."""
    region = region_of(keyword)
    has = set()                         # 키워드가 든 문장 번호. 해시태그 안의 키워드는 p3처럼 반복으로 치지 않아요
    for s in starts:
        i = bisect.bisect_right(d.sentence_starts, s) - 1
        if i >= 0 and s < d.sentences[i][1] and not in_hashtag(d.text, s):
            has.add(i)
    paras, pos = [], 0
    for line in d.text.split("\n"):
        start, pos = pos, pos + len(line) + 1
        words = line.split()
        if (words and line.strip() not in MARKS and not all(w.startswith("#") or URL.fullmatch(w) for w in words)
                and not any(term in line for term in phrases.DISCLOSURE_TERMS)):
            paras.append((start, start + len(line)))
    found = []
    for n, (start, end) in enumerate(paras):
        lo, hi = bisect.bisect_left(d.sentence_starts, start), bisect.bisect_left(d.sentence_starts, end)
        safe = [i for i in range(lo, hi) if not has & {i - 1, i, i + 1}]
        at = bisect.bisect_left(starts, start)
        if (at < len(starts) and starts[at] < end) or not safe:      # 이 문단에 키워드가 이미 있어요
            continue
        s, e = d.sentences[safe[0]][0], d.sentences[safe[-1]][1]
        while e < end and d.text[e] in ".!?":
            e += 1
        text = d.text[s:e]
        if len("".join(text.split())) < TIP_MIN_CHARS:
            continue
        score = ((n in (0, len(paras) - 1)) + (3 if region and region in text else 0)
                 + sum(weight for weight, cues in phrases.PLACE_CUES if any(cue in text for cue in cues)))
        if score:
            found.append((-score, s, e, safe[0], safe[-1]))
    picked = []
    for _, s, e, a, b in sorted(found):
        if all(a > last + 1 or b < first - 1 for _, _, first, last in picked):      # 고른 두 곳도 서로 이어지지 않게
            picked.append((s, e, a, b))
        if len(picked) == TIP_PLACES:
            break
    return [body_span(s, e) for s, e, _, _ in sorted(picked)]


def tips(conds: list[dict], results: list[dict], d: Draft) -> list[dict]:
    """도움이 될 팁: 띄어쓰기 안내(keyword_spacing)와 넣을 자리 추천(keyword_place). 판정(results)을 읽기만 해요.
    팁은 TIP_MAX개까지만 만들어요. 넘으면 거기서 멈춰요 (조건과 키워드가 아주 많아도 일이 한없이 늘지 않아요)."""
    out, seen = [], set()
    squashed: dict[str, tuple[str, list[int]]] = {}      # 띄어쓰기를 뺀 제목·본문. 처음 쓸 때 한 번만 만들어요

    def add(kind, c, keyword, label, note, spans, frames=()):
        key = (kind, keyword, tuple((s.get("field"), s["start"]) for s in spans))
        if key in seen:               # 같은 키워드를 두 조건이 말할 때 같은 팁을 두 번 내지 않아요
            return
        seen.add(key)
        spans, note = capped(spans, note)
        out.append({"tip_id": f"t{len(out) + 1}", "kind": kind, "condition_id": c["id"], "label": f'{label}: "{keyword}"',
                    "note": note, "templates": list(frames), "draft_spans": spans})

    for c, r in zip(conds, results):
        short, texts = short_keywords(c, r, d)
        if not short:
            continue
        in_body = c["type"] == "keyword_count" and c["params"].get("scope", "body") != "title"
        # 자리 추천: each는 모자란 키워드마다(앞에서부터 몇 개), 나머지는 기준에 가장 가까운 키워드 하나만
        place = short[:TIP_KEYWORDS] if c["params"].get("pick") == "each" else sorted(short, key=lambda x: x[1])[:1]
        for k, lack in short:
            if len(out) >= TIP_MAX:
                return out
            hits = {}
            for f, t in texts:
                if f not in squashed:
                    squashed[f] = squash(t)
                hits[f] = loose_hits(squashed[f], k)
            spaced = [(f, s, e) for f, t in texts for s, e in hits[f]
                      if t[s:e] != k and (s == 0 or not WORD_CHAR.match(t[s - 1]))]
            if spaced:
                how = ("가이드와 똑같이 써야" if any(ch.isspace() for ch in k) else "붙여 써야")
                what = ("표기와 띄어쓰기가 다른 곳" if any(ch.isspace() for ch in k) else "사이를 띄어 쓴 곳")
                add("keyword_spacing", c, k, "띄어쓰기 안내",
                    f'키워드 "{k}" {what}이 {len(spaced)}곳 있어요. {how} 키워드로 세져요',
                    [span(f, s, e) for f, s, e in spaced[:MAX_SPANS + 1]])       # 위치는 상한까지만 만들어요 (개수는 전부 센 값)
            if not in_body or (k, lack) not in place or len(spaced) >= lack:      # 띄어 쓴 곳만 고쳐도 채워지면 자리 추천은 안 해요
                continue
            frames = phrases.TIP_FRAMES_REGION if region_of(k) else phrases.TIP_FRAMES_GENERAL
            frames = [f.format(k=k, ro=josa(k, "ro"), eul=josa(k, "eul")) for f in frames]
            spans = tip_places(d, k, [s for s, _ in hits["body"]])
            if spans:
                note = (f'"{k}" {lack}회가 더 필요할 때 표시한 문단에 넣으면 더 자연스러워요. 지역 이름이나 "다녀왔", "추천", "메뉴" 같은 말이 '
                        f"있는 문단과 첫·끝 문단에서 골랐어요(우리 기준). 같은 키워드가 든 문장 바로 옆은 뺐어요. {TIP_SELF}")
            else:
                note = (f'"{k}" {lack}회가 더 필요할 때 지역·가게 소개, 방문 이유, 마무리 문단에 넣으면 더 자연스러워요'
                        f"(우리 기준). 이 원고에서는 어울리는 문단을 따로 짚지 못했어요. {TIP_SELF}")
            add("keyword_place", c, k, "넣을 자리 추천", note, spans, frames)
    return out[:TIP_MAX]


# ── 전체 ─────────────────────────────────────────────────────────────────

def check(conditions: dict, request: dict) -> dict:
    """조건 목록(conditions 0.3)과 점검 요청(check-request 0.3)을 받아 점검 결과(check-result 0.3)를 돌려줘요."""
    d = Draft(request)
    conds = conditions.get("conditions") or []
    results = [judge(c, d) for c in conds]
    principles = [p1(conds, d), p2(d), p3(conds, d), p4(conds, d), p5(d)]
    if conditions.get("campaign_type") == "기자단":
        principles.append(p6())
    if d.ai_marks:
        ban = ai_ban_condition(conds)
        if ban is None:
            principles.append(p7(d))
        else:                       # 금지 조건의 결과 아래에 붙여요
            r = next(r for r in results if r["condition_id"] == ban["id"])
            r["note"] += f". {AI_MARK_NOTE}. 가이드가 생성형 AI 사용을 금지해서 문제가 될 수 있어요"
            r["draft_spans"] = ordered(r["draft_spans"] + [body_span(s, e) for s, e in d.ai_marks])
    # 링크 위치처럼 여러 항목이 같은 위치 객체를 나눠 쓰기도 해요. 객체마다 한 번만 바꿔요.
    extra = tips(conds, results, d)          # 판정이 끝난 뒤에 읽기만 해요. 요약(summary)에는 들어가지 않아요
    done: set[int] = set()
    for item in results + principles + extra:
        for s in item["draft_spans"]:
            if id(s) not in done:
                done.add(id(s))
                d.to_orig(s)
    return {"version": VERSION, "summary": summarize(conds, results), "results": results, "principles": principles,
            "tips": extra}


def summarize(conds: list[dict], results: list[dict]) -> dict:
    """원고 밖 조건(outside_draft)은 결과 목록에는 있지만 요약 개수에서는 빼요."""
    return {s: sum(r["status"] == s for c, r in zip(conds, results) if c.get("type") != "outside_draft")
            for s in ("kept", "missing", "hold")}
