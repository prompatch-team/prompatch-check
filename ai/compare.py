"""뽑은 조건 목록을 기준 조건 목록(형식 예시나 정답)과 비교해요.

조건 번호(id)가 아니라 종류(type)와 인용 문구로 짝을 지어요.
원고 밖 조건(outside_draft)은 정확도에서 빼고 따로 보여 줘요 (criteria/README.md).
"""
from __future__ import annotations

SAME, DIFF, RANGE, MISSED, EXTRA, OUTSIDE = "같음", "값이 다름", "인용 범위가 다름", "놓침", "더 뽑음", "원고 밖 (세지 않음)"


def _overlaps(a: dict, b: dict) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


# 글로 풀어 쓴 값은 표현이 달라도 같은 조건이라 비교하지 않아요
FREE_TEXT = {"question", "what", "after", "subject", "category"}


def _diff(got: dict, want: dict) -> str:
    keys = sorted((set(got["params"]) | set(want["params"])) - FREE_TEXT)
    parts = [f'{k}: {got["params"].get(k)!r} (기준 {want["params"].get(k)!r})'
             for k in keys if got["params"].get(k) != want["params"].get(k)]
    if got["countable"] != want["countable"]:
        parts.append(f'countable: {got["countable"]} (기준 {want["countable"]})')
    return ", ".join(parts)


def compare(doc: dict, reference: dict) -> list[dict]:
    """한 줄에 조건 하나: {status, type, label, detail}. 기준 쪽 순서 먼저, 그다음 더 뽑은 것."""
    left = list(doc["conditions"])
    rows = []

    def take(want, test):
        for got in left:
            if got["type"] == want["type"] and test(got["guide_quote"], want["guide_quote"]):
                left.remove(got)
                return got
        return None

    for want in reference["conditions"]:
        outside = want["type"] == "outside_draft"
        got = take(want, lambda g, w: g["text"] == w["text"])
        if got is not None:
            detail = _diff(got, want)
            status = OUTSIDE if outside else (DIFF if detail else SAME)
        else:
            got = take(want, _overlaps)
            if got is not None:
                status = OUTSIDE if outside else RANGE
                detail = f'뽑은 인용: "{got["guide_quote"]["text"]}"' + (f' / {_diff(got, want)}' if _diff(got, want) else "")
            else:
                status, detail = (OUTSIDE if outside else MISSED), "기준에는 있는데 뽑지 않았어요"
        rows.append({"status": status, "type": want["type"], "label": want["label"], "detail": detail})
    for got in left:
        outside = got["type"] == "outside_draft"
        rows.append({"status": OUTSIDE if outside else EXTRA, "type": got["type"], "label": got["label"],
                     "detail": f'기준에 없어요. 인용: "{got["guide_quote"]["text"]}"'})
    return rows


def summary(rows: list[dict]) -> dict:
    counted = [r for r in rows if r["status"] != OUTSIDE]
    return {s: sum(r["status"] == s for r in counted) for s in (SAME, DIFF, RANGE, MISSED, EXTRA)} | {
        OUTSIDE: len(rows) - len(counted)}


def table(rows: list[dict]) -> str:
    lines = ["| 결과 | 종류 | 조건 | 다른 점 |", "| --- | --- | --- | --- |"]
    lines += [f'| {r["status"]} | {r["type"]} | {r["label"]} | {r["detail"]} |' for r in rows]
    return "\n".join(lines)
