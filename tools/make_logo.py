"""PromPatch 로고 만들기: Pretendard 글자를 윤곽선(path)으로 바꿔 SVG로 써요. 글꼴 없이도 똑같이 보여요.

실행 (저장소 맨 위 폴더에서, 개발용 도구가 필요해요: pip install fonttools brotli):
  python tools/make_logo.py            docs/brand/의 로고 SVG와 fe/favicon.svg를 만들고, 화면 머리(index·privacy·404)의 로고를 바꿔요
  python tools/make_logo.py --png      위에 더해 크롬으로 PNG 파비콘(16·32px)과 공유 미리보기(fe/og-image.png)도 만들어요 (pillow 필요)

- 색은 두 가지뿐이에요: 남색 #23395B(물결), 먹색 #1E2226 (어두운 바탕용은 먹색 자리에 흰색, 물결은 옅은 남색).
  화면에서 빨강은 원고 위 "고칠 곳" 표시에만 써서, 로고 물결은 대표 색인 남색으로 바꿨어요 (디자인 방향 A).
  시안 1·3(option-*)은 처음 그대로 빨강이에요.
- 글꼴은 저장소의 fe/fonts/Pretendard-Bold.subset.woff2만 써요.
- 시안 세 개(option-*.svg)는 --options를 줄 때만 만들어요. 고른 것은 시안 2 "물결 밑줄"이에요 (팀 저장소에는 고른 로고 4개만 둬요).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
FONT = ROOT / "fe" / "fonts" / "Pretendard-Bold.subset.woff2"
OUT = ROOT / "docs" / "brand"
RED, INK, PAPER = "#B3141E", "#1E2226", "#FFFFFF"
NAVY, NAVY_LIGHT = "#23395B", "#A9B8D3"        # 로고 물결 (밝은 바탕 / 어두운 바탕)
TRACK = -0.02                       # 글자 사이 (글자 크기 대비)

_font = None


def font() -> TTFont:
    global _font
    if _font is None:
        _font = TTFont(str(FONT))
    return _font


def text_path(text: str, size: float, x: float = 0, y: float = 0, track: float = TRACK) -> tuple[str, float]:
    """글자 → (path d, 너비). y는 글자 바닥선이에요."""
    f = font()
    glyphs, cmap, upm = f.getGlyphSet(), f.getBestCmap(), f["head"].unitsPerEm
    s = size / upm
    parts, cx = [], x
    for ch in text:
        name = cmap[ord(ch)]
        pen = SVGPathPen(glyphs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
        glyphs[name].draw(TransformPen(pen, (s, 0, 0, -s, cx, y)))
        parts.append(pen.getCommands())
        cx += glyphs[name].width * s + track * size
    return " ".join(p for p in parts if p), cx - x - track * size


def wave(x0: float, x1: float, y: float, amp: float, length: float) -> str:
    """물결 밑줄 (화면의 "고칠 곳" 표시와 같은 모양). 반 물결마다 위아래로 번갈아요."""
    half = length / 2
    n = max(2, round((x1 - x0) / half))
    half = (x1 - x0) / n
    d = f"M{x0:.1f} {y:.1f} Q{x0 + half / 2:.1f} {y - amp:.1f} {x0 + half:.1f} {y:.1f}"
    for _ in range(n - 1):
        d += " T"
        x0 += half
        d += f"{x0 + half:.1f} {y:.1f}"
    return d


def svg(w: float, h: float, body: str, title: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}" '
            f'role="img" aria-label="{title}"><title>{title}</title>{body}</svg>\n')


# ── 고른 시안: 물결 밑줄 (워드마크 + "P" 글자 심볼) ─────────────────────────

def wordmark(ink: str = INK, mark: str = NAVY) -> str:
    """PromPatch 글자 + 남색 물결 밑줄 (교정 펜 자국 모양)."""
    size, base = 64, 62
    d, width = text_path("PromPatch", size, 4, base)
    w = width + 8
    body = (f'<path fill="{ink}" d="{d}"/>'
            f'<path fill="none" stroke="{mark}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" '
            f'd="{wave(6, width + 2, base + 17, 4.5, 20)}"/>')
    return svg(w, base + 28, body, "PromPatch")


def symbol(ink: str = INK, paper: str | None = None, size: int = 64, mark: str = NAVY) -> str:
    """심볼: 굵은 "P" 아래 남색 물결. 16px에서도 보이게 획을 두껍게, 요소는 둘만."""
    d, width = text_path("P", 46, 0, 0, 0)
    x = (size - width) / 2
    d, _ = text_path("P", 46, x, 42, 0)
    back = f'<rect x="1" y="1" width="{size - 2}" height="{size - 2}" rx="8" fill="{paper}"/>' if paper else ""
    body = (back + f'<path fill="{ink}" d="{d}"/>'
            f'<path fill="none" stroke="{mark}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" '
            f'd="{wave(14, size - 14, 53, 4.5, 18)}"/>')
    return svg(size, size, body, "PromPatch")


def favicon() -> str:
    """파비콘: 32칸 기준으로 다시 그린 심볼. 흰 종이 위에 먹색 P와 남색 물결 (어두운 탭 바에서도 보이게)."""
    d, width = text_path("P", 24, 0, 0, 0)
    d, _ = text_path("P", 24, (32 - width) / 2, 22, 0)
    body = (f'<rect x="1" y="1" width="30" height="30" rx="5" fill="{PAPER}" stroke="{INK}" stroke-width="1.5"/>'
            f'<path fill="{INK}" d="{d}"/>'
            # 16px에서는 2px보다 가는 선이 사라져요. 물결을 굵고 짧게(반 물결 셋) 그려요
            f'<path fill="none" stroke="{NAVY}" stroke-width="4.4" stroke-linecap="round" stroke-linejoin="round" '
            f'd="{wave(7.5, 24.5, 26.2, 2.2, 11)}"/>')
    return svg(32, 32, body, "PromPatch")


# ── 시안 1, 3 (고르지 않은 것, docs/ui/logo-options.png에만) ────────────────

def option_caret() -> str:
    """시안 1 삽입표: "Prom"과 "Patch" 사이 아래에 빨간 ∧ (빠진 글자를 넣으라는 교정 부호). 심볼은 ∧ 하나."""
    size, base = 64, 58
    d1, w1 = text_path("Prom", size, 4, base)
    gap = 26
    d2, w2 = text_path("Patch", size, 4 + w1 + gap, base)
    cx = 4 + w1 + gap / 2
    body = (f'<path fill="{INK}" d="{d1} {d2}"/>'
            f'<path fill="none" stroke="{RED}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" '
            f'd="M{cx - 11:.1f} {base + 18} L{cx:.1f} {base - 2} L{cx + 11:.1f} {base + 18}"/>')
    return svg(4 + w1 + gap + w2 + 8, base + 26, body, "시안 1")


def option_margin() -> str:
    """시안 3 여백 체크: 종이 한 장(먹색 줄 셋) 옆 여백에 빨간 체크 + 글자. 교정지 여백에 다는 확인 표시."""
    size, base = 56, 56
    d, w = text_path("PromPatch", size, 84, base)
    page = (f'<rect x="6" y="8" width="54" height="64" rx="3" fill="none" stroke="{INK}" stroke-width="5"/>'
            f'<path stroke="{INK}" stroke-width="5" stroke-linecap="round" d="M18 26h30M18 40h30M18 54h18"/>'
            f'<path fill="none" stroke="{RED}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M40 56l8 9 16-22"/>')
    return svg(84 + w + 8, 80, page + f'<path fill="{INK}" d="{d}"/>', "시안 3")


def option_caret_symbol() -> str:
    """시안 1 심볼: 먹색 바닥선 위로 빨간 ∧ (빠진 곳 표시)."""
    body = (f'<path stroke="{INK}" stroke-width="7" stroke-linecap="round" d="M8 46h48"/>'
            f'<path fill="none" stroke="{RED}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" d="M18 56L32 22L46 56"/>')
    return svg(64, 64, body, "시안 1 심볼")


def option_margin_symbol() -> str:
    """시안 3 심볼: 종이 한 장과 여백의 빨간 체크."""
    body = (f'<rect x="8" y="6" width="40" height="52" rx="3" fill="none" stroke="{INK}" stroke-width="6"/>'
            f'<path stroke="{INK}" stroke-width="6" stroke-linecap="round" d="M18 22h20M18 34h20"/>'
            f'<path fill="none" stroke="{RED}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" d="M30 46l8 8 18-24"/>')
    return svg(64, 64, body, "시안 3 심볼")


# ── 화면 머리: 세 화면의 로고를 같은 워드마크로 (글자 없이 path만) ─────────

START, END = "<!-- 로고: tools/make_logo.py가 넣어요 -->", "<!-- /로고 -->"
PAGES = ("index.html", "privacy.html", "404.html")


def header_logo() -> str:
    text = re.sub(r"<title>.*?</title>", "", wordmark()).replace(' xmlns="http://www.w3.org/2000/svg"', "")   # HTML 안에서는 필요 없어요
    text = re.sub(r' width="\d+" height="\d+" role="img" aria-label="PromPatch"',
                  ' class="wordmark" aria-hidden="true" focusable="false"', text)
    return f"{START}{text.strip()}{END}"


def update_pages() -> None:
    old = re.compile(r'<svg class="mark".*?</svg>\s*<span class="word">PromPatch</span>', re.S)
    for name in PAGES:
        path = ROOT / "fe" / name
        page = path.read_text(encoding="utf-8")
        if START in page:
            page = re.sub(re.escape(START) + ".*?" + re.escape(END), lambda m: header_logo(), page, flags=re.S)
        else:
            page, n = old.subn(lambda m: header_logo(), page)
            assert n == 1, name
        path.write_text(page, encoding="utf-8", newline="\n")


# ── PNG (크롬으로 그려요): 파비콘 16·32px, 공유 미리보기 1200×630 ──────────────

OG_TEXT = "체험단 원고, 내기 전에 가이드와 맞춰 봐요"


def shoot(html: str, out: Path, w: int, h: int, transparent: bool = False) -> None:
    import subprocess
    import tempfile
    from fe.test_fe import find_chrome
    chrome = find_chrome()
    if not chrome:
        raise SystemExit("크롬을 찾지 못했어요 (CHROME 환경 변수에 경로를 넣어 주세요)")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        page = Path(tmp) / "page.html"
        page.write_text(html, encoding="utf-8")
        args = [chrome, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={tmp}/c", "--hide-scrollbars",
                "--virtual-time-budget=3000", f"--window-size={max(w, 520)},{max(h, 200)}", f"--screenshot={out}", page.as_uri()]
        if transparent:
            args.insert(1, "--default-background-color=00000000")
        subprocess.run(args, capture_output=True, timeout=120)


def pngs() -> None:
    from PIL import Image
    fav = (ROOT / "fe" / "favicon.svg").read_text(encoding="utf-8")
    tmp = OUT / "_shot.png"
    for size in (16, 32):
        icon = fav.replace('width="32" height="32"', f'width="{size}" height="{size}"')
        shoot(f'<!doctype html><body style="margin:0;background:transparent">{icon}</body>', tmp, size, size, transparent=True)
        Image.open(tmp).crop((0, 0, size, size)).save(ROOT / "fe" / f"favicon-{size}.png")
    font_url = (ROOT / "fe" / "fonts" / "Pretendard-Bold.subset.woff2").as_uri()
    logo = re.sub(r' width="\d+" height="\d+"', ' style="height:118px;width:auto;display:block"', wordmark(), count=1)
    og = (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>'
          f'@font-face {{ font-family: P; font-weight: 700; src: url("{font_url}"); }}'
          f'body {{ margin: 0; width: 1200px; height: 630px; background: #F3F0E8; display: flex; align-items: center; }}'
          f'.sheet {{ margin-left: 96px; }}'
          f'p {{ margin: 46px 0 0 6px; font: 700 50px/1.35 P, sans-serif; color: {INK}; letter-spacing: -0.02em; }}'
          f'</style></head><body><div class="sheet">{logo}<p>{OG_TEXT}</p></div></body></html>')
    shoot(og, tmp, 1200, 630)
    Image.open(tmp).crop((0, 0, 1200, 630)).save(ROOT / "fe" / "og-image.png")
    tmp.unlink()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        OUT / "prompatch-wordmark.svg": wordmark(),
        OUT / "prompatch-wordmark-dark.svg": wordmark(ink=PAPER, mark=NAVY_LIGHT),   # 어두운 바탕용: 먹색 자리에 흰색
        OUT / "prompatch-symbol.svg": symbol(),
        OUT / "prompatch-symbol-dark.svg": symbol(ink=PAPER, mark=NAVY_LIGHT),
        ROOT / "fe" / "favicon.svg": favicon(),
    }
    if "--options" in sys.argv:                                  # 고르지 않은 시안은 달라고 할 때만
        files.update({
            OUT / "option-1-caret.svg": option_caret(),
            OUT / "option-2-wave.svg": wordmark(mark=RED),        # 시안은 처음 그대로
            OUT / "option-3-margin.svg": option_margin(),
            OUT / "option-1-symbol.svg": option_caret_symbol(),
            OUT / "option-2-symbol.svg": symbol(mark=RED),
            OUT / "option-3-symbol.svg": option_margin_symbol(),
        })
    for path, text in files.items():
        path.write_text(text, encoding="utf-8", newline="\n")
        print(path.relative_to(ROOT), len(text))
    update_pages()
    if "--png" in sys.argv:
        pngs()


if __name__ == "__main__":
    main()
