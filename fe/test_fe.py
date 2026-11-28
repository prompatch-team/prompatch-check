"""화면(fe) 확인. 실행: python -m unittest fe.test_fe

- 분석 코드가 paste-test와 같은지, 예시 데이터가 엔진 결과와 같은지
- 화면 코드에 밖으로 나가는 요청, 사진 불러오기, 보장 문구가 없는지
- 크롬이 있으면 화면 자체 시험(index.html#selftest)까지 돌려요. 없으면 그 시험만 건너뛰어요.
API를 부르지 않아요.
"""
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from be import engine
from fe import make_analyze, make_mock

FE = Path(__file__).resolve().parent
ROOT = FE.parent
OURS = ("index.html", "privacy.html", "404.html", "style.css", "api.js", "reader.js", "results.js", "app.js", "selftest.js")      # 손으로 쓴 파일
ALL = OURS + ("analyze.js", "mock-data.js")
NOTICE = "점검 결과는 참고용이며 노출·법규 준수를 보장하지 않아요."
# 처리방침 페이지가 근거로 거는 공식 문서 주소. 이것 말고는 화면 파일에 바깥 주소가 없어야 해요.
OFFICIAL_LINKS = (
    "https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training",
    "https://www.anthropic.com/legal/commercial-terms",
    "https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data",
    "https://platform.claude.com/docs/en/manage-claude/data-residency",
)
# 7-2: 키워드를 누르면 네이버 화면을 새 탭으로 여는 링크. results.js에만 있고, 요청은 보내지 않아요.
NAVER_LINKS = ("https://search.naver.com/search.naver?query=", "https://datalab.naver.com/keyword/trendSearch.naver")


def read(name: str) -> str:
    return (FE / name).read_text(encoding="utf-8")


def find_chrome() -> str | None:
    candidates = [os.environ.get("CHROME"), shutil.which("chrome"), shutil.which("google-chrome"), shutil.which("chromium"),
                  r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    return next((c for c in candidates if c and Path(c).exists()), None)


class Generated(unittest.TestCase):
    def test_analysis_code_is_the_same_as_paste_test(self):
        self.assertEqual(read("analyze.js"), make_analyze.expected(),
                         "tools/paste-test.html의 분석 코드와 달라요. python fe/make_analyze.py 를 돌려 주세요")

    def test_mock_data_is_what_the_engine_returns(self):
        self.assertEqual(read("mock-data.js"), make_mock.expected(),
                         "예시 데이터가 엔진 결과와 달라요. python fe/make_mock.py 를 돌려 주세요")

    def test_mock_requests_and_results_match_the_contract(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema가 없어요 (pip install jsonschema)")
        schema = lambda kind: Draft202012Validator(
            json.loads((ROOT / "contracts" / f"{kind}.schema.json").read_text(encoding="utf-8")))
        for s in make_mock.scenarios():
            for kind, data in (("conditions", s["doc"]), ("check-request", s["request"]), ("check-result", s["result"])):
                self.assertEqual([e.message for e in schema(kind).iter_errors(data)], [], f'{s["id"]} {kind}')
        self.assertTrue(any(c["params"].get("needs_review") for s in make_mock.scenarios() for c in s["doc"]["conditions"]))


class Rules(unittest.TestCase):
    def test_no_code_that_sends_anything_out(self):
        """화면에서 원고 글이 밖으로 나가는 코드가 없어요."""
        for name in ALL:
            text = read(name)
            for bad in ("XMLHttpRequest", "sendBeacon", "WebSocket", "EventSource", "import(", ".submit("):
                self.assertFalse(bad in text, f"{name}에 {bad}")
            if name != "api.js":                       # 요청을 보내는 코드는 api.js 한 곳에만
                self.assertFalse("fetch(" in text, f"{name}에 fetch(")
        api = read("api.js")
        self.assertEqual(api.count("fetch("), 1)       # 그 한 곳도 우리 서버의 /api/ 아래로만
        self.assertIn("fetch('/api/' + path, {", api)
        self.assertIn("credentials: 'omit'", api)
        for name in OURS:
            text = read(name).replace("https://example.invalid/", "")      # 자체 시험의 지어낸 주소
            if name == "privacy.html":
                for link in OFFICIAL_LINKS:
                    text = text.replace(link, "")
            if name == "results.js":
                for link in NAVER_LINKS:
                    text = text.replace(f"'{link}'", "")
            self.assertIsNone(re.search(r"https?://", text), f"{name}에 밖의 주소가 있어요")

    def test_pasted_content_is_never_put_on_the_page_as_html(self):
        for name in ("app.js", "api.js", "analyze.js", "reader.js", "results.js", "selftest.js"):
            text = read(name)
            for bad in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "createElement('img')", "new Image"):
                self.assertFalse(bad in text, f"{name}에 {bad}")
        self.assertIsNone(re.search(r"<(img|iframe|video|audio|object|embed)\b", read("index.html")))
        # 스타일에서 불러오는 것은 이 서버에 둔 글꼴(fonts/)뿐이에요 (3단계 디자인, 2026-11-27)
        css = read("style.css")
        self.assertNotIn("@import", css)
        self.assertEqual(re.findall(r"url\(([^)]*)\)", css),
                         ['"fonts/Pretendard-Regular.subset.woff2"', '"fonts/Pretendard-Bold.subset.woff2"'])
        for name in ("Pretendard-Regular.subset.woff2", "Pretendard-Bold.subset.woff2", "OFL-Pretendard.txt"):
            self.assertTrue((FE / "fonts" / name).exists(), name)
        self.assertIn("SIL Open Font License", (FE / "fonts" / "OFL-Pretendard.txt").read_text(encoding="utf-8"))

    def test_no_download_or_copy_of_the_draft_on_the_public_screen(self):
        """원고가 든 JSON을 내려받거나 복사하는 버튼은 개발 도구(tools/paste-test.html)에만 있어요. 배포 화면에는 없어요."""
        for name in ALL + ("privacy.html",):
            text = read(name)
            for bad in ("내려받기", "createObjectURL", "new Blob", "download:", "download=", "JSON 복사"):
                self.assertFalse(bad in text, f"{name}에 {bad}")
        tool = (ROOT / "tools" / "paste-test.html").read_text(encoding="utf-8")
        self.assertIn("점검 요청 JSON 내려받기", tool)
        self.assertIn(".request.json", tool)

    def test_browser_blocks_outside_requests(self):
        page = read("index.html")
        csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', page).group(1)
        self.assertIn("default-src 'none'", csp)
        self.assertIn("connect-src 'self';", csp)           # 연결은 같은 주소(우리 서버)로만
        for opened in ("frame-src", "'unsafe-inline'", "'unsafe-eval'", "*", "http:", "https:", "data:", "blob:"):
            self.assertNotIn(opened, csp)
        # 그림은 이 서버의 파일(파비콘)만. 붙여 넣은 서식은 화면에 넣지 않아서 붙여 넣은 사진은 그래도 불러오지 않아요
        self.assertEqual(re.findall(r"img-src [^;]+;", csp), ["img-src 'self';"])
        self.assertNotIn('type="url"', page + read("app.js"))             # 주소(URL) 입력칸을 만들지 않아요
        self.assertIn("font-src 'self';", csp)                            # 글꼴은 이 서버에 둔 것만 (3단계에서 이것 하나만 더함)
        for other in ("privacy.html", "404.html"):
            self.assertIn("font-src 'self'", read(other))

    def test_page_title_description_share_tags_and_icons(self):
        page = read("index.html")
        for tag in ('<meta name="description"', '<meta property="og:title"', '<meta property="og:description"',
                    '<meta property="og:image" content="og-image.png">', '<link rel="icon" href="favicon.svg"'):
            self.assertIn(tag, page)
        self.assertTrue(re.search(r"<title>PromPatch: [^<]+</title>", page))
        for name in ("og-image.png", "favicon.svg", "404.html"):
            self.assertTrue((FE / name).exists(), name)
        self.assertIn("없는 주소예요", read("404.html"))

    def test_notice_and_no_guarantee_wording(self):
        self.assertIn(f'<p class="notice">{NOTICE}</p>', read("index.html"))
        for name in ("index.html", "app.js", "api.js", "results.js"):    # 사람이 보는 글이 든 파일
            text = read(name).replace(NOTICE, "")
            self.assertIsNone(re.search(r"상위\s?노출|노출 보장|준수 보장|보장해|보장돼|보장합니다", text), name)

    def test_privacy_page_says_what_the_code_does(self):
        """처리방침 초안의 문장이 코드가 하는 일과 맞는지."""
        page = read("privacy.html")
        self.assertIn(NOTICE, page)
        self.assertIn('href="privacy.html"', read("index.html"))
        self.assertIsNone(re.search(r"<script|<img|<form|<input", page))                 # 글만 있는 페이지
        self.assertIsNone(re.search(r"보장해|보장돼|보장합니다|안전합니다|완벽", page.replace(NOTICE, "")))
        server = (ROOT / "be" / "server.py").read_text(encoding="utf-8")
        # "원고 글은 AI 서비스로 보내지 않아요": 점검 주소는 엔진만 부르고, AI는 조건 뽑기 주소에서만 불러요
        check = server[server.index("async def api_check"):server.index("async def api_judge")]
        self.assertIn('checked("check", conditions, req)', check)
        self.assertIn("engine.check(conditions, req)", server[server.index("def checked("):server.index("@app.get")])
        self.assertFalse("ai_extract" in check)
        self.assertEqual(server.count("ai_extract.extract"), 1)
        # "조건의 이름과 판정, 보낸 시각만 저장해요"
        self.assertIn('"at":', server)
        for field in ('"kind"', '"id"', '"type"', '"label"', '"status"'):
            self.assertIn(field, server[server.index("record = {"):server.index("FEEDBACK_FILE.parent.mkdir")])
        # 쿠키를 쓰지 않아요
        for name in ("app.js", "api.js", "analyze.js", "reader.js", "results.js"):
            self.assertFalse("document.cookie" in read(name) or "localStorage" in read(name), name)
        self.assertFalse("set_cookie" in server)
        self.assertIn('id="draft-note"', page)                                           # 초안 표시가 아직 붙어 있어요
        self.assertIn("법률 검토 전 초안", page)
        self.assertEqual(page.count("[미정]"), 3)                                         # 문의처, 서버 위치 (+ 맨 위 안내)
        self.assertIn("30일", page)                                                      # 서버 기록
        self.assertIn("6개월", page)                                                     # 피드백 기록
        self.assertIn("FEEDBACK_KEEP_DAYS = 183", server)
        # AI 서비스 항목: 가이드는 보내고 원고는 보내지 않는다고 적혀 있고, Anthropic 쪽 숫자를 지어 적지 않아요
        ai = page[page.index('<h2 id="ai">'):page.index("<h2>저장하는 것")]
        self.assertIn("가이드 글은 조건을 뽑기 위해 미국 회사 Anthropic의 API", ai)
        # 원고 글은 블로거가 켰을 때만 AI로 가요: 화면은 S.ai가 켜졌을 때만 Api.judge를 불러요
        self.assertIn("켰을 때만 전송돼요", ai)
        app = read("app.js")
        self.assertEqual(app.count("Api.judge("), 1)
        self.assertLess(app.index("if (!S.ai || Api.mock"), app.index("Api.judge("))
        self.assertIn("ai: false", app)                                                  # 기본은 꺼져 있어요
        self.assertEqual(sorted(re.findall(r'href="([^"]+)"', ai)), sorted(OFFICIAL_LINKS))
        shown = re.sub(r"<[^>]+>", "", ai)                                               # 태그와 주소를 뺀, 보이는 글
        self.assertIsNone(re.search(r"\d", shown), "Anthropic 쪽 보관 기간 같은 숫자를 옮겨 적지 않아요")

    def test_logo_is_outlines_in_two_colors(self):
        """로고(2026-11-27): 글자는 윤곽선(path)이라 글꼴 없이도 같아요. 색은 남색 #23395B와 먹색 #1E2226뿐
        (어두운 바탕용은 흰색과 옅은 남색 #A9B8D3). 빨강은 원고 위 "고칠 곳" 표시에만 써서 로고에는 없어요 (디자인 방향 A)."""
        brand = ROOT / "docs" / "brand"
        files = [brand / n for n in ("prompatch-wordmark.svg", "prompatch-wordmark-dark.svg", "prompatch-symbol.svg",
                                    "prompatch-symbol-dark.svg")] + [FE / "favicon.svg"]
        for f in files:
            text = f.read_text(encoding="utf-8")
            self.assertNotIn("<text", text, f.name)
            self.assertNotRegex(text, r"[Gg]radient", f.name)
            self.assertLessEqual(set(re.findall(r"#[0-9A-Fa-f]{6}", text)), {"#23395B", "#A9B8D3", "#1E2226", "#FFFFFF"}, f.name)
            self.assertNotIn("#B3141E", text, f.name)
        for name in ("index.html", "privacy.html", "404.html"):
            page = read(name)
            self.assertIn('<svg viewBox=', page.split("<!-- 로고: tools/make_logo.py가 넣어요 -->", 1)[1][:20], name)
            self.assertIn('class="wordmark"', page)
            self.assertIn('favicon-16.png', page)
        for name in ("favicon-16.png", "favicon-32.png"):
            self.assertTrue((FE / name).exists(), name)

    def test_naver_links_are_plain_new_tab_links_only(self):
        """7-2: 네이버 주소는 새 탭 링크(href)로만 써요. 불러오거나(fetch, img, iframe) 가공하지 않아요."""
        res = read("results.js")
        self.assertEqual(res.count(NAVER_LINKS[0]), 1)
        self.assertEqual(res.count(NAVER_LINKS[1]), 1)
        self.assertIn("h('a', { href, target: '_blank', rel: 'noopener noreferrer'", res)
        self.assertEqual(re.findall(r"NAVER_(?:SEARCH|DATALAB)\b", res).count("NAVER_SEARCH"), 2)    # 정의 1 + 링크 1
        for name in ALL:
            if name != "results.js":
                self.assertFalse(any(link in read(name) for link in NAVER_LINKS), name)
        server = (ROOT / "be" / "server.py").read_text(encoding="utf-8")
        self.assertNotIn("naver.com", server)                     # 서버는 네이버에 요청하지 않아요

    def test_reading_and_showing_are_separate_files(self):
        """8단계: 원고를 읽는 부분(reader.js)과 결과를 보여 주는 부분(results.js)은 상태(S)와 서버(Api)를 몰라요."""
        for name in ("reader.js", "results.js"):
            text = read(name)
            self.assertIsNone(re.search(r"\bS\.|\bApi\.", text), name)
        self.assertNotIn("document", read("reader.js"))
        server = (ROOT / "be" / "server.py").read_text(encoding="utf-8")
        message = re.search(r'MANY_POSTS = "([^"]+)"', server).group(1)
        self.assertIn(f"MANY_POSTS: '{message}'", read("reader.js"))        # 글 여러 개 안내는 화면과 서버가 같은 문장
        page = read("index.html")
        order = [page.index(f'src="{n}"') for n in ("analyze.js", "api.js", "reader.js", "results.js", "app.js")]
        self.assertEqual(order, sorted(order))

    def test_fixed_disclosure_example_passes_our_own_checks(self):
        """복사 버튼의 대가성 문구 예시(고정 문구)를 글 첫 줄에 쓰면 p1은 지킴이고 p2(모호한 표현)에 걸리지 않아요."""
        phrase = re.search(r"const DISCLOSURE_EXAMPLE = '([^']+)';", read("app.js")).group(1)
        request = {"version": "0.3", "input_mode": "text", "counts_source": "user", "title": "후기",
                   "draft_text": phrase + "\n\n본문이에요.", "photo_count": None, "video_count": None, "has_map": None,
                   "links": [], "hashtags": [], "media": []}
        top = {"id": "c1", "type": "disclosure", "label": "대가성", "countable": True,
               "params": {"phrase": None, "position": "top"}, "guide_quote": {"text": "x", "start": 0, "end": 1}}
        out = engine.check({"version": "0.3", "conditions": [top]}, request)
        status = {p["rule_id"]: p["status"] for p in out["principles"]}
        self.assertEqual((out["results"][0]["status"], status["p1"], status["p2"]), ("kept", "kept", "kept"))

    def test_timing_sends_only_numbers(self):
        """걸린 시간은 숫자 세 개(첫 결과, 전체 결과, AI 상태)만 보내요 (2026-11-27)."""
        self.assertIn("await post('timing', { first_ms, full_ms, ai }, 5000)", read("api.js"))
        app = read("app.js")
        self.assertEqual(app.count("Api.timing("), 2)
        self.assertEqual(re.findall(r"Api\.timing\(\{ (\w+): ", app), ["first_ms", "first_ms"])

    def test_feedback_sends_only_condition_and_status(self):
        self.assertIn("const payload = { consent: true, kind, id, label, status };", read("api.js"))
        self.assertIn("await Api.feedback({ kind, id, label, status })", read("app.js"))
        self.assertFalse("console.log" in read("app.js"))


EDITOR_SAMPLE = ROOT / "samples" / "editor" / "editor-test.html"


def analyze_in_chrome(chrome: str, pasted: str) -> dict:
    """붙여 넣은 서식(HTML)을 fe/analyze.js로 읽은 결과. 임시 폴더의 시험 화면에서 돌리고 결과 JSON만 받아요."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        page = Path(tmp) / "analyze.html"
        page.write_text(
            f'<!doctype html><meta charset="utf-8"><script src="{(FE / "analyze.js").as_uri()}"></script><pre id="out"></pre>'
            f"<script>const r = analyze({json.dumps(pasted)}); document.getElementById('out').textContent = "
            "JSON.stringify({ request: toRequest(r), imgs: r.imgs, units: r.units, excluded: r.excluded });</script>",
            encoding="utf-8")
        done = subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={tmp}/profile",
                               "--virtual-time-budget=3000", "--dump-dom", page.as_uri()], capture_output=True, timeout=120)
    found = re.search(r'<pre id="out">(.*?)</pre>', done.stdout.decode("utf-8", "replace"), re.S)
    if not found:
        raise AssertionError("분석 결과가 화면에 나오지 않았어요 (스크립트 오류일 수 있어요)")
    return json.loads(html.unescape(found.group(1)))


class EditorCopy(unittest.TestCase):
    """2026-11-27 에디터 복사 시험: 네이버 글쓰기 화면에서 직접 복사한 지어낸 글 (samples/editor/editor-test.html).
    정답은 카티가 준 것: 사진 7(단독 1, 콜라주 2, 단독 1 + 설명, 슬라이드 3), 스티커 1(사진 수 제외), 동영상 1, 지도 1,
    링크 카드 1, 사진 설명 1, 본문 키워드 시험맛집 3·테스트카페 3·라떼추천 2(본문 해시태그 포함)."""

    @classmethod
    def setUpClass(cls):
        chrome = find_chrome()
        if not chrome:
            raise unittest.SkipTest("크롬을 찾지 못했어요. CHROME 환경 변수에 경로를 넣으면 돌려요")
        cls.got = analyze_in_chrome(chrome, EDITOR_SAMPLE.read_text(encoding="utf-8"))
        cls.req = cls.got["request"]
        cls.lines = cls.req["draft_text"].split("\n")

    def test_sample_has_no_account_addresses(self):
        """사진·동영상·지도·스티커 주소는 example 주소로 바꿔 넣었어요. 계정을 알 수 있는 주소가 남으면 안 돼요."""
        text = EDITOR_SAMPLE.read_text(encoding="utf-8")
        self.assertNotIn("pstatic", text)
        self.assertNotIn("스크린샷", text)
        hosts = set(re.findall(r"https?://([^/\"'&;)<\s]+)", text))
        self.assertLessEqual(hosts, {"example.com", "www.naver.com"})

    def test_photos_sticker_video_map_card(self):
        self.assertEqual((self.req["photo_count"], self.req["video_count"], self.req["has_map"]), (7, 1, True))
        kinds = [i["kind"] for i in self.got["imgs"]]
        self.assertEqual(kinds.count("photo"), 7)
        self.assertEqual(sorted(k for k in kinds if k != "photo"), ["map", "oglink", "sticker", "video"])   # 스티커는 사진 수에서 빼요
        self.assertEqual(sorted(u["kind"] for u in self.got["units"]), ["map", "oglink", "sticker", "video"])

    def test_one_caption_and_no_placeholders(self):
        caps = [self.req["draft_text"][c["start"]:c["end"]] for c in self.req["captions"]]
        self.assertEqual(caps, ["창가 자리 라떼"])
        for noise in ("대표", "이전 이미지", "다음 이미지", "00:03"):         # 단추·길이 글자는 줄 전체로 (본문에 "대표 메뉴는"이 있어요)
            self.assertNotIn(noise, self.lines)
        for noise in ("사진 설명을 입력하세요.", "동영상 설명을 입력하세요.", "AI 활용 설정", "영상제목입니다", "예시점", "예시로 1",
                      "네이버 메인에서"):
            self.assertFalse(any(noise in l for l in self.lines), noise)
        self.assertNotIn("www.naver.com", self.lines)        # 링크 카드 맨 아래 도메인 줄
        self.assertNotIn("", self.lines)                     # 사진 블록의 빈 설명 칸·편집 화면 문단이 빈 줄을 만들지 않아요

    def test_links_from_data_href_and_card(self):
        """글쓰기 화면의 링크는 span.se-link[data-href]. 링크 카드는 카드 안 주소 글자로 하나."""
        body = [l for l in self.req["links"] if l["start"] is not None]
        self.assertEqual([(l["url"], self.req["draft_text"][l["start"]:l["start"] + len(l["url"])]) for l in body],
                         [("https://example.com/menu",) * 2, ("https://www.naver.com",) * 2])
        self.assertEqual([l["url"] for l in self.req["links"] if l["start"] is None], ["https://www.naver.com"])
        # 링크 카드 위 "https://www.naver.com" 줄은 카드 안 글자가 아니라 본문 글 블록의 별도 줄이라 본문 글자로 세요
        self.assertIn("https://www.naver.com", self.lines)

    def test_body_lines_and_characters(self):
        """정답(카티): 본문 글 13줄, 공백 포함 376자, 공백 제외 308자. 사진 설명을 넣으면 +8 / +6.
        공백 포함은 문단 안의 글자와 띄어쓰기만 세요 (2026-11-28, 줄바꿈·빈 줄·줄 끝 공백은 안 셈. 예전 기준 388).
        처음 정답 402/325는 HTML에 없는 스콘 두 줄을 넣어 센 값이라 고쳤어요 (링크 카드 위 주소 줄은 본문 문단이라 세요)."""
        text_lines = [l for l in self.lines if l not in engine.MARKS and l != "창가 자리 라떼"]
        self.assertEqual(len(text_lines), 13)
        self.assertEqual(sum(len(l) for l in text_lines), 376)
        req = dict(self.req, count_captions=False)
        d = engine.Draft(req)
        self.assertEqual((d.chars_with_spaces, d.chars), (376, 308))
        d = engine.Draft(dict(self.req, count_captions=True))
        self.assertEqual((d.chars_with_spaces, d.chars), (376 + 8, 308 + 6))

    def test_body_keywords_count_body_hashtags(self):
        want = {"시험맛집": (3, "본문 글 2번 + 해시태그 1번"), "테스트카페": (3, None), "라떼추천": (2, "본문 글 1번 + 해시태그 1번")}
        for word, (n, split) in want.items():
            c = {"id": "k", "type": "keyword_count", "label": word, "countable": True,
                 "params": {"keywords": [word], "min": 1, "scope": "body"}, "guide_quote": {"text": word}}
            r = engine.check({"conditions": [c]}, self.req)["results"][0]
            self.assertEqual(r["actual"], n, word)
            if split:
                self.assertIn(split, r["note"], word)
            else:
                self.assertNotIn("해시태그", r["note"], word)


def se_block(kind: str, inner: str) -> str:
    return f'<div class="se-component se-{kind}"><div class="se-component-content">{inner}</div></div>'


def photo(src: str) -> str:
    return se_block("image", f'<div class="se-module se-module-image"><img class="se-image-resource" src="{src}"></div>')


def text(words: str) -> str:
    return se_block("text", f'<div class="se-module se-module-text"><p class="se-text-paragraph"><span>{words}</span></p></div>')


class BannerFilter(unittest.TestCase):
    """2026-11-27: 체험단 배너 거르기 (강남맛집 /_sp/, 리뷰노트 /gongjeong/). 배너는 사진 수에서 빼고 따로 세요.
    맨 위(첫 사진 블록이나 첫 3블록 안) 배너는 대가성 표시로 봐요. 주소 뒤쪽은 지어낸 예시예요."""
    GANGNAM = "https://xn--939au0g4vj8sq.net/_sp/wgs.php?ctf=example"
    REVIEWNOTE = "https://reviewnote.cloud/gongjeong/v1/image.example.png"

    @classmethod
    def setUpClass(cls):
        cls.chrome = find_chrome()
        if not cls.chrome:
            raise unittest.SkipTest("크롬을 찾지 못했어요. CHROME 환경 변수에 경로를 넣으면 돌려요")

    def read(self, html_text: str) -> dict:
        return analyze_in_chrome(self.chrome, html_text)["request"]

    def test_two_platform_banners_are_counted_apart_from_photos(self):
        for banner in (self.GANGNAM, self.REVIEWNOTE):
            req = self.read(photo(banner) + text("오늘 다녀온 곳이에요.") + photo("https://example.com/a.png") + photo("https://example.com/b.png"))
            self.assertEqual((req["photo_count"], req["banner_count"], req["banner_top"]), (2, 1, True), banner)

    def test_same_site_pictures_outside_the_banner_path_are_photos(self):
        req = self.read(photo("https://xn--939au0g4vj8sq.net/data/example.png") + photo("https://reviewnote.cloud/files/example.png"))
        self.assertEqual((req["photo_count"], req["banner_count"], req["banner_top"]), (2, 0, False))

    def test_banner_far_down_is_not_a_top_banner(self):
        body = photo("https://example.com/a.png") + "".join(text(f"{n}번째 문단이에요.") for n in range(4)) + photo(self.GANGNAM)
        req = self.read(body)
        self.assertEqual((req["banner_count"], req["banner_top"]), (1, False))

    def test_top_banner_counts_as_disclosure_and_nothing_means_missing(self):
        p1 = lambda req: next(p for p in engine.check({"version": "0.3", "conditions": []}, req)["principles"] if p["rule_id"] == "p1")
        with_banner = dict(self.read(photo(self.REVIEWNOTE) + text("교재를 한 달 써 봤어요.")), title="교재 후기")
        self.assertEqual(p1(with_banner)["status"], "kept")
        self.assertIn("대가성 표시 있음(맨 위 배너)", p1(with_banner)["note"])
        nothing = dict(self.read(photo("https://example.com/a.png") + text("교재를 한 달 써 봤어요.")), title="교재 후기")
        self.assertEqual(p1(nothing)["status"], "missing")


class SameCountEverywhere(unittest.TestCase):
    """2026-11-28: 공백 포함 = 문단 안의 글자와 띄어쓰기만 (줄바꿈·빈 줄·줄 끝 공백은 안 셈).
    글쓰기 화면(서식), 보기 화면(글자), 글만 붙여넣기 어디서 복사해도 같은 값이에요. 지어낸 글이에요."""
    BODY = ["솔바람 찻집에 다녀왔어요.", "창가 자리가 좋았어요. 녹차가 진했어요.", "#솔바람찻집 #녹차맛집"]

    def test_editor_viewer_and_plain_text_give_the_same_counts(self):
        chrome = find_chrome()
        if not chrome:
            self.skipTest("크롬을 찾지 못했어요")
        editor = analyze_in_chrome(chrome, "".join(text(line) for line in self.BODY) + photo("https://example.com/a.png"))["request"]
        viewer = "\n".join(["솔바람 찻집 후기", "", "프로필", "가나다", "2026. 11. 9. 21:40", "", " 이웃추가본문 기타 기능", "",
                            self.BODY[0] + " ", "", "", self.BODY[1] + "  ", "", self.BODY[2], "", "#솔바람찻집", "#녹차맛집", "+1"])
        plain = "\n".join(self.BODY)
        want = (sum(len(line) for line in self.BODY), len("".join("".join(self.BODY).split())))
        for name, req in (("글쓰기 화면", editor),
                          ("보기 화면", {**editor, "input_mode": "text", "counts_source": "user", "draft_text": viewer, "media": [], "captions": []}),
                          ("글만", {**editor, "input_mode": "text", "counts_source": "user", "draft_text": plain, "media": [], "captions": []})):
            d = engine.Draft(req)
            self.assertEqual((d.chars_with_spaces, d.chars), want, name)


class Browser(unittest.TestCase):
    def test_selftest_in_chrome(self):
        chrome = find_chrome()
        if not chrome:
            self.skipTest("크롬을 찾지 못했어요. CHROME 환경 변수에 경로를 넣으면 돌려요")
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
            done = subprocess.run(
                [chrome, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={profile}",
                 "--virtual-time-budget=6000", "--dump-dom", (FE / "index.html").as_uri() + "#selftest"],
                capture_output=True, timeout=120)
        dom = done.stdout.decode("utf-8", "replace")
        failed = [html.unescape(t) for good, t in re.findall(r'<li data-pass="(\w+)">(.*?)</li>', dom) if good != "true"]
        report = re.search(r'id="selftest"[^>]*>자체 시험 (\d+)/(\d+) 통과<', dom)
        self.assertIsNotNone(report, "자체 시험 결과가 화면에 나오지 않았어요 (스크립트 오류일 수 있어요)")
        self.assertEqual(failed, [])
        self.assertEqual(report.group(1), report.group(2))
        self.assertGreaterEqual(int(report.group(2)), 30)


if __name__ == "__main__":
    unittest.main()
