"""커밋 전 대조: 내 컴퓨터에만 있는 실제 가이드·글의 문장, 블로그 주소, 키가 저장소에 들어가지 않게 막아요.

실행 (저장소 맨 위 폴더에서):
  python tools/leak_check.py --install      한 번만. .git/hooks/pre-commit에 이 대조와 테스트 실행을 걸어요
  python tools/leak_check.py                커밋하려고 올린 변경(git diff --cached)을 봐요. 훅이 이걸 불러요
  python tools/leak_check.py --log A..B     커밋 기록(git log -p, 커밋 메시지 포함)을 봐요
  python tools/leak_check.py --text 파일…   글 파일을 봐요 (이슈·PR에 올릴 글을 올리기 전에)
  python tools/leak_check.py --tests        지금 저장소에 있는 테스트를 돌려요. 훅이 대조 다음에 불러요

- 원문 폴더는 각자 .env의 PROMPATCH_PRIVATE_DATA에 적어요 (환경 변수로 줘도 돼요). 그 폴더 아래의 .txt 파일을 전부 원문으로 봐요.
  메모나 정답지처럼 원문이 아닌 글은 .md 같은 다른 확장자로 두거나 results/ 폴더에 두면 읽지 않아요. 이 도구는 원문을 어디에도 보내거나 쓰지 않아요.
- 원문 폴더가 없는 컴퓨터에서도 오류 없이 돌아요. 그때는 블로그 주소와 키 모양만 봐요.
- 공백을 빼고 8글자 이상 이어진 원문 구절(한 문장 안, 한글 6자 이상)을 막아요. 서로 다른 글 2곳 이상에 똑같이 나오는 구절과
  우리가 지어낸 예시(samples/, 커밋된 판)에도 있는 구절은 화면 글자·흔한 말로 보고 빼요.
- 원문에 나온 작성자 이름, 도메인, @아이디, 블로그 주소, 키 모양은 짧아도 막아요.
- 걸리면 종료 코드 1로 커밋을 멈춰요. 걸린 것은 앞 20글자만 보여 줘요.
- 훅은 작업 폴더의 파일로 테스트해요. 일부만 올려(stage) 커밋하면 올리지 않은 변경도 같이 시험돼요.
- 네이버·플랫폼 화면 글자처럼 걸려도 괜찮은 것은 tools/leak-allow.txt에 한 줄씩 적어요. 실제 글 문장은 적지 마세요.
- 이 파일은 표준 라이브러리만 써요 (훅이 python -I로 불러요).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOW_FILE = Path(__file__).resolve().parent / "leak-allow.txt"
ENV = "PROMPATCH_PRIVATE_DATA"
PHRASE = 8                    # 공백을 빼고 이 글자 수 이상 이어진 원문 구절을 막아요 (2026-11-27)
HANGUL = 6                    # 조각 안에 한글이 이만큼은 있어야 해요 (날짜·숫자·주소 조각은 고유 낱말 쪽에서 막아요)
HANGUL_RE = re.compile("[가-힣]")
COMMON_CASES = 2              # 서로 다른 사례 이만큼에 똑같이 나오는 구절은 화면 글자·가이드 틀로 보고 빼요 (같은 글의 파일은 한 사례)
MIN_WORD = 2
ALLOW_CUT = 6                 # 허용 목록 글자 가운데 이 길이 이상만 구절 조각을 끊어요
DOMAIN = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:com|net|kr|cloud|io|me|co)\b", re.I)
# 네이버·플랫폼·예시처럼 코드에 쓰는 주소는 고유 낱말로 치지 않아요
GENERIC_HOST = re.compile(r"(^|\.)(naver\.com|naver\.me|pstatic\.net|youtube\.com|example\.com|revu\.net|reviewnote\.cloud|"
                          r"xn--939au0g4vj8sq\.net)$")
HANDLE = re.compile(r"(?<![\w.])@[A-Za-z0-9_.-]{3,}")
BLOG = re.compile(r"(?:m\.)?blog\.naver\.com/(?!naver_search\b)[A-Za-z0-9_-]{3,}")     # 네이버 검색 공식 블로그는 괜찮아요
KEY = re.compile(r"sk-ant-[\w-]{10,}|(?i:api[_-]?key|secret|token)\s*[=:]\s*['\"]?[\w-]{16,}")
HOOK = (
    "#!/bin/sh\n"
    "# 커밋 전 확인 (tools/leak_check.py --install이 만듦): 1) 비공개 자료 대조 2) 테스트. 하나라도 실패하면 커밋을 멈춰요.\n"
    "\"{python}\" -I tools/leak_check.py || exit 1\n"
    "\"{python}\" -I tools/leak_check.py --tests || exit 1\n"
)


def test_commands() -> list[list[str]]:
    """지금 저장소에 있는 테스트를 돌리는 명령. 테스트 파일이 늘거나 줄어도 훅을 다시 설치하지 않아도 돼요.
    - 영역 폴더 바로 아래의 test_*.py (be/test_engine.py → be.test_engine)
    - be/tests/ 폴더가 있으면 그 안의 테스트 (unittest discover)"""
    modules = sorted(f"{f.parent.name}.{f.stem}" for f in ROOT.glob("*/test_*.py") if not f.parent.name.startswith("."))
    cmds = [[sys.executable, "-m", "unittest", *modules]] if modules else []
    if (ROOT / "be" / "tests").is_dir():
        cmds.append([sys.executable, "-m", "unittest", "discover", "-s", "be/tests"])
    return cmds


def run_tests() -> int:
    for cmd in test_commands():
        done = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if done.returncode:
            print("\n".join((done.stdout + done.stderr).splitlines()[-25:]))
            print("테스트가 실패해서 커밋을 멈춰요. 고친 뒤 다시 커밋해 주세요.")
            return 1
    print("테스트: 통과")
    return 0


def norm(s: str) -> str:
    return " ".join(s.replace("​", "").split())


def private_dir() -> Path | None:
    value = os.environ.get(ENV, "")
    env = ROOT / ".env"
    if not value and env.exists():                      # .env에서 이 이름 하나만 읽어요 (내용을 출력하지 않아요)
        for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith(ENV + "="):
                value = line.split("=", 1)[1].strip().strip('"')
    path = Path(value) if value else None
    return path if path and path.is_dir() else None


def flat(s: str) -> str:
    """공백과 숨은 문자를 모두 뺀 글 (구절 비교용)."""
    return re.sub(r"[\s\u200b\u2060\ufeff]+", "", s)


def source_files(private: Path) -> list[Path]:
    """대조 목록을 만드는 원문 파일: 원문 폴더 아래의 .txt 전부. 메모·정답지는 .md 같은 다른 확장자로 두면 읽지 않아요.
    results/ 폴더는 우리 도구가 만든 결과(숫자 요약)를 두는 곳이라 읽지 않아요."""
    return sorted(f for f in private.rglob("*.txt") if f.is_file() and "results" not in f.relative_to(private).parts[:-1])


def case_of(private: Path, f: Path) -> str:
    """같은 글을 여러 번 복사해 둔 파일은 한 글로 세요 (이름 끝의 -text, -paste-check, -draft만 다른 파일)."""
    return f.parent.relative_to(private).as_posix() + "/" + re.sub(r"-(text|paste-check|draft)$", "", f.stem)


def strip_allowed(s: str, allow: set[str]) -> str:
    """공백을 뺀 글에서 허용 목록 글자를 끊는 표시로 바꿔요. 허용된 글자에 걸친 조각이 생기지 않게요."""
    s = flat(s)
    for a in sorted((flat(x) for x in allow), key=len, reverse=True):
        if len(a) >= ALLOW_CUT:            # 짧은 허용 낱말("필수" 같은 것)로는 원문 문장을 끊지 않아요
            s = s.replace(a, "\x00")
    return re.sub(r"[.!?]", "\x00", s)        # 구절은 한 문장 안에서만 (문장 경계에 걸친 흔한 조각은 빼요)


def shingles(s: str, allow: set[str] = frozenset()) -> set[str]:
    """공백을 뺀 글에서 PHRASE 글자씩 이어진 조각 가운데 한글이 HANGUL자 이상인 것 (허용 목록 글자는 끊어요)."""
    s = strip_allowed(s, allow)
    return {s[i:i + PHRASE] for i in range(len(s) - PHRASE + 1)
            if "\x00" not in s[i:i + PHRASE] and len(HANGUL_RE.findall(s[i:i + PHRASE])) >= HANGUL}


def made_up_shingles() -> set[str]:
    """우리가 지어낸 예시(samples/의 가이드·원고, 커밋된 판)에도 있는 조각. 실제 글이 아닌 흔한 말이라 빼요.
    작업 폴더가 아니라 커밋된 판을 읽어서, 새로 넣는 글이 스스로를 허용하지 못해요."""
    names = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only", "HEAD", "samples"],
                           capture_output=True, text=True, encoding="utf-8").stdout.split()
    out: set[str] = set()
    for name in names:
        if name.endswith(".md") and "/private/" not in name:
            text = subprocess.run(["git", "-C", str(ROOT), "show", f"HEAD:{name}"], capture_output=True, text=True,
                                  encoding="utf-8").stdout
            out |= shingles(text)
    return out


def collect(private: Path, allow: set[str] = frozenset()) -> tuple[set[str], set[str]]:
    """원문 파일의 (구절 조각, 고유 낱말).
    - 구절 조각: 공백을 빼고 8글자씩 이어진 조각. 서로 다른 글 2곳 이상에 똑같이 나오는 조각은 네이버 화면 글자나
      플랫폼 가이드 틀이라 빼요 (실제 블로거 글은 한 사례에만 있어요).
    - 고유 낱말(짧아도 막아요): 작성자 이름(프로필 다음 줄, "・" 앞, [출처]의 작성자), 원문 속 도메인과 @아이디."""
    seen: dict[str, set[str]] = {}
    words: set[str] = set()
    same: set[str] = set()
    for f in source_files(private):
        text = f.read_text(encoding="utf-8", errors="replace")
        if flat(text) in same:          # 같은 글을 다른 폴더에 복사해 둔 파일은 한 번만 세요 (2026-11-28).
            continue                    # 두 번 세면 "여러 글에 나오는 흔한 구절"로 보고 막지 않게 돼요
        same.add(flat(text))
        case = case_of(private, f)
        for piece in shingles(text, allow):
            seen.setdefault(piece, set()).add(case)
        rows = [norm(r.strip()) for r in text.replace("\r\n", "\n").split("\n")]
        rows = [r[:-2].strip() if r.endswith("CR") else r for r in rows]          # 붙여넣기 확인의 줄 끝 표시
        filled = [r for r in rows if r]
        for i, row in enumerate(filled):
            if row in ("프로필", "프로파일") and i + 1 < len(filled) and len(filled[i + 1]) <= 20:
                words.add(filled[i + 1])
            if " ・ " in row:
                words.add(norm(row.split(" ・ ")[0]))
            if row.startswith("[출처]") and "|작성자" in row:
                words.add(norm(row.split("|작성자", 1)[1]))
        words.update(m.lower() for m in DOMAIN.findall(text) if not GENERIC_HOST.search(m.lower()))
        words.update(HANDLE.findall(text))
    pieces = {s for s, cases in seen.items() if len(cases) < COMMON_CASES} - made_up_shingles()
    words = {w for w in words if len(w) >= MIN_WORD and not re.fullmatch(r"[\d\s.,%:~/()-]+", w)}
    return pieces, words


def allowed() -> set[str]:
    if not ALLOW_FILE.exists():
        return set()
    return {norm(l) for l in ALLOW_FILE.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}


def scan(added: str, pieces: set[str], words: set[str], allow: set[str]) -> list[str]:
    """새로 들어가는 글(added)에서 걸린 것: 원문 구절(공백 빼고 8글자 이상 이어짐), 고유 낱말, 블로그 주소, 키 모양."""
    s = strip_allowed(added, allow)
    hit = [i for i in range(len(s) - PHRASE + 1) if s[i:i + PHRASE] in pieces]
    phrases, start, end = [], None, None
    for i in hit:                                     # 이어진 조각은 한 구절로 묶어요
        if start is not None and i <= end:
            end = i + PHRASE
        else:
            if start is not None:
                phrases.append(s[start:end])
            start, end = i, i + PHRASE
    if start is not None:
        phrases.append(s[start:end])
    spaced = norm(added)
    hits = [f"구절: {x}" for x in phrases]
    hits += [f"낱말: {w}" for w in sorted(words - allow) if w in spaced or w in s]
    hits += [f"블로그 주소: {m}" for m in sorted(set(BLOG.findall(added)))]
    hits += [f"키 모양: {m[:12]}" for m in KEY.findall(added)]
    return hits


def added_text(args: list[str]) -> str:
    if args[:1] == ["--text"]:
        return "\n".join(Path(name).read_text(encoding="utf-8", errors="replace") for name in args[1:])
    if args[:1] == ["--log"]:
        out = subprocess.run(["git", "-C", str(ROOT), "log", "-p", "--format=+%s%n+%b", args[1]],
                             capture_output=True, text=True, encoding="utf-8").stdout
    else:
        out = subprocess.run(["git", "-C", str(ROOT), "diff", "--cached", "-U0"], capture_output=True, text=True,
                             encoding="utf-8").stdout
    return "\n".join(l[1:] for l in out.splitlines() if l.startswith("+") and not l.startswith("+++"))


def main(args: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if args[:1] == ["--install"]:
        hook = ROOT / ".git" / "hooks" / "pre-commit"
        python = Path(sys.executable).as_posix()
        hook.write_text(HOOK.format(python=python), encoding="utf-8", newline="\n")
        print(f"설치했어요: {hook}")
        return 0
    if args[:1] == ["--tests"]:
        return run_tests()
    private = private_dir()
    allow = allowed()
    lines, words = collect(private, allow) if private else (set(), set())
    hits = scan(added_text(args), lines, words, allow)
    if hits:
        print(f"비공개 대조: {len(hits)}개 걸려서 멈춰요. 괜찮은 화면 글자라면 tools/leak-allow.txt에 적어 주세요.", file=sys.stderr)
        for h in hits[:40]:
            print("  " + h[:24] + ("…" if len(h) > 24 else ""), file=sys.stderr)
        return 1
    if private is None:
        print(f"비공개 대조: 통과. 원문 폴더({ENV})가 없어서 블로그 주소와 키 모양만 봤어요.", file=sys.stderr)
        return 0
    print(f"비공개 대조: 통과 (원문 구절 조각 {len(lines)}개, 고유 낱말 {len(words)}개와 대조)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
