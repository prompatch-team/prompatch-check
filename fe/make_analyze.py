"""tools/paste-test.html의 분석 코드를 fe/analyze.js로 옮겨요. 실행: python fe/make_analyze.py

붙여 넣은 서식을 읽는 코드는 paste-test가 기준이에요. 화면(fe)은 그 코드를 그대로 써요.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BEGIN, END = "// <<분석 코드 시작>>", "// <<분석 코드 끝>>"
HEADER = (
    "// 이 파일은 손으로 고치지 않아요. tools/paste-test.html의 분석 코드를 그대로 옮긴 거예요.\n"
    "// 고칠 때는 paste-test.html을 고친 뒤 python fe/make_analyze.py 를 돌려요.\n"
    "'use strict';\n\n"
)


def block() -> str:
    text = (ROOT / "tools" / "paste-test.html").read_text(encoding="utf-8")
    start, end = text.index(BEGIN), text.index(END) + len(END)
    return text[start:end] + "\n"


def expected() -> str:
    return HEADER + block()


if __name__ == "__main__":
    (ROOT / "fe" / "analyze.js").write_text(expected(), encoding="utf-8", newline="\n")
    print("fe/analyze.js를 만들었어요.")
