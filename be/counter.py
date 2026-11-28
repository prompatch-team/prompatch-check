"""원고에서 셀 수 있는 조건을 코드로 세요. LLM을 부르지 않아요.

입력: 점검 요청(check-request) + 조건 목록(conditions)
출력: 점검 결과(check-result) 형식의 dict
"""

VERSION = "0.1-draft"

# 글자 수를 셀 때 빼는 줄
SKIP_LINES = ("[사진]", "[지도]")

# 대가성 문구를 찾는 범위: 원고 첫 몇 줄
DISCLOSURE_TOP_LINES = 3

HOLD_JUDGMENT = "셀 수 없는 조건이라 1주차에는 판단하지 않아요"


def find_keyword(text, keyword):
    """키워드 위치를 겹치지 않게 앞에서부터 찾아요. [(start, end), ...]"""
    spans = []
    if not keyword:
        return spans
    i = 0
    while True:
        j = text.find(keyword, i)
        if j == -1:
            return spans
        spans.append((j, j + len(keyword)))
        i = j + len(keyword)


def body_text(text):
    """[사진], [지도] 줄을 뺀 본문이에요."""
    lines = [line for line in text.split("\n") if line.strip() not in SKIP_LINES]
    return "\n".join(lines).strip()


def count_length(text):
    """본문 글자 수를 두 가지로 세요.

    without_spaces: 공백과 줄바꿈을 모두 뺀 글자 수
    with_spaces: 공백과 줄바꿈을 포함한 글자 수 (본문 앞뒤 빈 줄은 빼요)
    """
    body = body_text(text)
    without_spaces = sum(1 for ch in body if not ch.isspace())
    return {"with_spaces": len(body), "without_spaces": without_spaces}


def find_in_top_lines(text, phrase, n_lines=DISCLOSURE_TOP_LINES):
    """원고 첫 n줄 안에서 문구를 찾아요. (줄 번호, start, end) 또는 None"""
    offset = 0
    for line_no, line in enumerate(text.split("\n")[:n_lines], start=1):
        j = line.find(phrase)
        if j != -1:
            return line_no, offset + j, offset + j + len(phrase)
        offset += len(line) + 1  # 줄바꿈 한 글자
    return None


def _result(cond, status, note, expected=None, actual=None, unit=None, spans=()):
    return {
        "condition_id": cond["id"],
        "label": cond["label"],
        "status": status,
        "expected": expected,
        "actual": actual,
        "unit": unit,
        "note": note,
        "draft_spans": [{"start": s, "end": e} for s, e in spans],
    }


def check_keyword(cond, req):
    p = cond["params"]
    # 형식 0.3: 키워드가 목록(keywords)이에요. 여러 개면 가장 많이 쓴 키워드로 세요
    keywords = p.get("keywords") or [p.get("keyword", "")]
    spans = max((find_keyword(req["draft_text"], k) for k in keywords), key=len)
    need, got = p.get("min"), len(spans)
    if need is None:
        return _result(cond, "hold", "기준 횟수가 없어서 판단하지 않아요", None, got, "회", spans)
    if got >= need:
        return _result(cond, "kept", "기준을 채웠어요", need, got, "회", spans)
    return _result(cond, "missing", f"{need - got}회 더 필요해요", need, got, "회", spans)


def check_length(cond, req):
    p = cond["params"]
    counts = count_length(req["draft_text"])
    with_spaces = p.get("count_spaces", False)
    got = counts["with_spaces"] if with_spaces else counts["without_spaces"]
    how = "공백 포함" if with_spaces else "공백 제외"
    need = p.get("min")
    if need is None:
        return _result(cond, "hold", "기준 글자 수가 없어서 판단하지 않아요", None, got, "자")
    if got >= need:
        return _result(cond, "kept", f"기준을 채웠어요 ({how}, [사진] 줄 제외)", need, got, "자")
    return _result(cond, "missing", f"{need - got}자 더 필요해요 ({how}, [사진] 줄 제외)", need, got, "자")


def check_photo(cond, req):
    if "subject" in cond["params"]:
        return _result(cond, "hold", "사진 내용은 확인할 수 없어요")
    need, got = cond["params"].get("min"), req.get("photo_count")
    if got is None:
        return _result(cond, "hold", "사진 수를 입력하지 않았어요", need, None, "장")
    if need is None:
        return _result(cond, "hold", "기준 장수가 없어서 판단하지 않아요", None, got, "장")
    if got >= need:
        return _result(cond, "kept", "기준을 채웠어요 (입력한 사진 수 기준)", need, got, "장")
    return _result(cond, "missing", f"{need - got}장 더 필요해요 (입력한 사진 수 기준)", need, got, "장")


def check_disclosure(cond, req):
    phrase = cond["params"].get("phrase", "")
    if not phrase:
        return _result(cond, "hold", "확인할 문구가 없어서 판단하지 않아요")
    found = find_in_top_lines(req["draft_text"], phrase)
    if found is None:
        return _result(cond, "missing", f"첫 {DISCLOSURE_TOP_LINES}줄 안에 문구가 없어요")
    line_no, s, e = found
    where = "첫 줄" if line_no == 1 else f"{line_no}번째 줄"
    return _result(cond, "kept", f"{where}에 있어요", spans=[(s, e)])


def check_map(cond, req):
    has_map = req.get("has_map")
    if has_map is None:
        return _result(cond, "hold", "지도 첨부 여부를 입력하지 않았어요")
    if has_map:
        return _result(cond, "kept", "지도를 첨부했다고 입력했어요")
    return _result(cond, "missing", "지도를 첨부하지 않았다고 입력했어요")


CHECKERS = {
    "keyword_count": check_keyword,
    "length": check_length,
    "photo_count": check_photo,
    "disclosure": check_disclosure,
    "map": check_map,
}


def check(request, conditions):
    """점검 요청과 조건 목록으로 점검 결과를 만들어요."""
    results = []
    for cond in conditions["conditions"]:
        checker = CHECKERS.get(cond["type"])
        if not cond.get("countable", False):
            # 셀 수 없는 조건은 1주차에 모두 판단 보류
            note = "사진 내용은 확인할 수 없어요" if "subject" in cond["params"] else HOLD_JUDGMENT
            results.append(_result(cond, "hold", note))
        elif checker is None:
            results.append(_result(cond, "hold", "아직 셀 수 없는 종류의 조건이에요"))
        else:
            results.append(checker(cond, request))

    summary = {s: sum(1 for r in results if r["status"] == s) for s in ("kept", "missing", "hold")}
    return {"version": VERSION, "summary": summary, "results": results}
