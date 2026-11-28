"""커밋 전 대조 확인. 실행: python -m unittest tools.test_leak_check

실제 원문 폴더는 쓰지 않아요. 지어낸 폴더를 임시로 만들어 봐요.
"""
import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import leak_check as L

# 이 파일 자체가 대조에 걸리지 않게 조각을 이어 붙여요
FAKE_BLOG = "https://blog." + "naver.com/" + "someone123"
FAKE_KEY = "API_" + "KEY = '" + "a" * 21 + "'"
NL = "\n"


class LeakCheck(unittest.TestCase):
    """대조 목록은 원문 폴더 아래의 .txt 파일에서만 만들고, 공백 빼고 8글자 이상 이어진 구절로 맞춰요.
    메모(.md)는 쓰지 않아요. 이름·주소·아이디는 짧아도 막아요. (모두 지어낸 글)"""
    SENTENCE = "솔바람 가게 창가 자리에서 녹차를 천천히 마셨어요"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        posts, guides, other = base / "posts", base / "guides", base / "deep" / "folder"
        for d in (posts, guides, other):
            d.mkdir(parents=True)
        post = NL.join([self.SENTENCE, "프로필", "가나다", "이웃추가 화면 아래쪽 공감 버튼 글자", "솔바람상회.co.kr 에서 샀어요",
                        "@solbaram_tea", ""])
        (posts / "P1-text.txt").write_text(post, encoding="utf-8")
        (posts / "P1-paste-check.txt").write_text(post, encoding="utf-8")          # 같은 글이라 한 글로 세요
        (posts / "P2-text.txt").write_text(NL.join(["다른 글이에요", "이웃추가 화면 아래쪽 공감 버튼 글자", ""]), encoding="utf-8")
        (guides / "K1.txt").write_text("방문 후 사진을 열다섯 장 이상 올려 주세요" + NL, encoding="utf-8")
        (guides / "K1-memo.md").write_text('| c1 | 정답 메모에만 있는 긴 설명 문장이에요 "솔바람녹차" |' + NL, encoding="utf-8")
        (other / "L9.txt").write_text("하위 폴더 깊은 곳에 둔 글의 첫 문장이에요 정말로" + NL, encoding="utf-8")
        (base / "results").mkdir()
        (base / "results" / "summary.txt").write_text("도구가 만든 숫자 요약의 설명 문장이에요 정말로" + NL, encoding="utf-8")
        with mock.patch.object(L, "made_up_shingles", return_value=set()):
            self.pieces, self.words = L.collect(base)
        self.env = mock.patch.dict(os.environ, {L.ENV: str(base)})

    def tearDown(self):
        self.tmp.cleanup()

    def kinds(self, added: str, allow=frozenset()) -> set:
        return {h.split(":")[0] for h in L.scan(added, self.pieces, self.words, set(allow))}

    def test_a_phrase_from_any_txt_is_blocked_even_with_other_spacing(self):
        self.assertEqual(self.kinds("설명: 창가자리에서 녹차를  천천히"), {"구절"})
        self.assertEqual(self.kinds("하위 폴더 깊은 곳에 둔 글의"), {"구절"})             # 폴더 아래 어디에 있든 .txt면 원문
        self.assertEqual(self.kinds("방문 후 사진을 열다섯 장"), {"구절"})               # 원문 가이드
        self.assertEqual(self.kinds("창가 자리에서 차를 마셨어요"), set())               # 8글자가 이어지지 않으면 괜찮아요

    def test_memos_in_other_file_types_are_not_used(self):
        self.assertEqual(self.kinds("정답 메모에만 있는 긴 설명 문장이에요 솔바람녹차"), set())
        self.assertEqual(self.kinds("도구가 만든 숫자 요약의 설명 문장이에요"), set())          # results/ 폴더는 읽지 않아요

    def test_phrases_shared_by_two_posts_are_screen_words(self):
        self.assertEqual(self.kinds("이웃추가 화면 아래쪽 공감 버튼 글자"), set())

    def test_a_copy_of_the_same_file_elsewhere_does_not_make_its_phrases_common(self):
        """원문을 다른 폴더에 그대로 복사해 둬도(나눠 줄 묶음 등) 그 글의 구절은 계속 막아요."""
        base = Path(self.tmp.name)
        (base / "copy").mkdir()
        (base / "copy" / "K1.txt").write_text((base / "guides" / "K1.txt").read_text(encoding="utf-8"), encoding="utf-8")
        with mock.patch.object(L, "made_up_shingles", return_value=set()):
            pieces, words = L.collect(base)
        self.assertEqual({h.split(":")[0] for h in L.scan("방문 후 사진을 열다섯 장", pieces, words, set())}, {"구절"})

    def test_names_addresses_and_ids_are_blocked_even_when_short(self):
        self.assertIn("가나다", self.words)                                        # 프로필 다음 줄의 작성자 이름
        self.assertEqual(self.kinds("작성자 가나다"), {"낱말"})
        self.assertEqual(self.kinds("주소 솔바람상회.co.kr"), {"낱말"})
        self.assertEqual(self.kinds("채널 @solbaram_tea"), {"낱말"})
        self.assertEqual(self.kinds(FAKE_BLOG + NL + FAKE_KEY), {"블로그 주소", "키 모양"})
        self.assertEqual(L.scan("https://blog.naver.com/naver_search/1", set(), set(), set()), [])   # 공식 블로그는 괜찮아요

    def test_allowlist(self):
        self.assertEqual(self.kinds("창가 자리에서 녹차를 천천히", {"창가 자리에서 녹차를 천천히"}), set())
        self.assertEqual(self.kinds("작성자 가나다", {"가나다"}), set())
        # 짧은 허용 낱말로는 원문 문장을 끊지 않아요
        self.assertEqual(self.kinds("창가 자리에서 녹차를 천천히", {"녹차"}), {"구절"})

    def test_made_up_samples_are_common_words(self):
        with mock.patch.object(L, "made_up_shingles", return_value=L.shingles(self.SENTENCE)):
            pieces, _ = L.collect(Path(self.tmp.name))
        self.assertEqual(L.scan(self.SENTENCE, pieces, set(), set()), [])

    def run_main(self, args, added=None) -> tuple[int, str]:
        err = io.StringIO()
        with contextlib.redirect_stderr(err), mock.patch.object(L, "allowed", return_value=set()), \
                mock.patch.object(L, "made_up_shingles", return_value=set()):
            if added is None:
                return L.main(args), err.getvalue()
            with mock.patch.object(L, "added_text", return_value=added):
                return L.main(args), err.getvalue()

    def test_main_fails_the_commit_on_a_hit_and_passes_otherwise(self):
        with self.env:
            code, said = self.run_main([], "설명: 솔바람 가게 창가 자리에서 녹차를")
            self.assertEqual(code, 1)
            self.assertIn("멈춰요", said)
            self.assertEqual(self.run_main([], "지어낸 문장이에요")[0], 0)

    def test_text_files_can_be_checked_before_posting(self):
        """이슈·PR에 올릴 글 파일도 같은 대조로 봐요 (--text 파일…)."""
        good, bad = Path(self.tmp.name) / "ok.md", Path(self.tmp.name) / "bad.md"
        good.write_text("형식을 맞췄어요. 테스트 9개 통과" + NL, encoding="utf-8")
        bad.write_text("예: " + self.SENTENCE + NL, encoding="utf-8")
        with self.env:
            self.assertEqual(self.run_main(["--text", str(good)])[0], 0)
            self.assertEqual(self.run_main(["--text", str(good), str(bad)])[0], 1)

    def test_runs_without_the_private_folder(self):
        """원문 폴더가 없는 컴퓨터: 오류 없이 지나가고, 블로그 주소와 키 모양은 그래도 막아요."""
        with mock.patch.dict(os.environ, {L.ENV: str(Path(self.tmp.name) / "없음")}):
            code, said = self.run_main([], self.SENTENCE)
            self.assertEqual(code, 0)
            self.assertIn("블로그 주소와 키 모양만", said)
            self.assertEqual(self.run_main([], FAKE_BLOG)[0], 1)

    def test_hook_runs_this_check_and_then_the_tests_that_exist(self):
        hook = L.HOOK.format(python="python")
        self.assertTrue(hook.startswith("#!/bin/sh"))
        check, tests = [line for line in hook.splitlines() if "tools/leak_check.py" in line and not line.startswith("#")]
        self.assertTrue(check.endswith("tools/leak_check.py || exit 1"))            # 대조가 먼저, 걸리면 멈춤
        self.assertTrue(tests.endswith("--tests || exit 1"))                        # 그다음 테스트, 실패하면 멈춤
        # 테스트 목록은 고정이 아니라 지금 있는 파일로 정해요. 없는 테스트 이름을 부르지 않아요
        cmds = L.test_commands()
        named = [m for cmd in cmds for m in cmd[3:] if "." in m and not m.startswith("-")]
        self.assertIn("tools.test_leak_check", named)
        for name in named:
            self.assertTrue((L.ROOT / (name.replace(".", "/") + ".py")).exists(), name)
        self.assertEqual(any("discover" in cmd for cmd in cmds), (L.ROOT / "be" / "tests").is_dir())

    def test_failing_tests_stop_the_commit(self):
        fail = [[L.sys.executable, "-c", "import sys; print('실패한 테스트 이름'); sys.exit(1)"]]
        out = io.StringIO()
        with mock.patch.object(L, "test_commands", return_value=fail), contextlib.redirect_stdout(out):
            self.assertEqual(L.main(["--tests"]), 1)
        self.assertIn("커밋을 멈춰요", out.getvalue())
        with mock.patch.object(L, "test_commands", return_value=[]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(L.main(["--tests"]), 0)


if __name__ == "__main__":
    unittest.main()
