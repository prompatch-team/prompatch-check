"""예시 모드 데이터(fe/mock-data.js)를 만들어요. 실행: python fe/make_mock.py

서버가 붙기 전까지 화면이 쓸 예시예요. 점검 결과는 손으로 쓰지 않고 be/engine.py를 돌려서 만들어요.
그래서 화면에 보이는 예시 결과가 엔진 결과와 항상 같아요. (지어낸 예시 1, 2와 샘플 04, 05만 써요.)
예시 4는 ai/extract.py를 가짜 AI 응답으로 돌려서 만들어요. 코드가 만든 조건과 "확인하지 못한 조건" 안내가 들어 있어요.
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(*parts) -> dict:
    return json.loads(ROOT.joinpath(*parts).read_text(encoding="utf-8"))


def scenarios() -> list[dict]:
    from be import engine
    from be.test_engine import GOOD2      # 예시 2 가이드에 맞춰 지어낸 원고 (정답지 아님)

    doc1 = load("contracts", "conditions.example.json")
    doc2 = copy.deepcopy(load("contracts", "conditions.example-2.json"))
    # 조건표의 "숫자를 확인해 주세요" 표시를 볼 수 있게, 예시 2의 사진 조건에 확인 표시를 달아 둬요.
    next(c for c in doc2["conditions"] if c["type"] == "photo_count" and c["countable"])["params"]["needs_review"] = True
    # 일부러 합친 조건의 예 (안내 없이 "버린 것" 목록에만 보여요). 확인하지 못해 버린 조건은 예시 4에 있어요.
    dropped2 = [{"code": "MISSION_KEYWORD_LINE", "reason": '리뷰어 미션의 "키워드" 줄은 위의 키워드 조건과 같은 조건이에요',
                 "type": "keyword_count", "label": "키워드 (예시로 넣은 버린 조건)", "quote": "키워드"}]
    req1 = load("contracts", "check-request.example.json")
    doc3 = load("contracts", "conditions.example-3.json")      # 링크 조건에 가이드 원문이 둘(extra_quotes)
    req3 = load("samples", "draft-04.request.json")
    from ai import extract
    from ai.test_extract import example_4_raw      # 가짜 AI 응답 (조건이 아닌 줄 하나를 잘못 읽은 경우)
    guide4 = (ROOT / "samples" / "guide-05.md").read_text(encoding="utf-8")
    doc4, dropped4 = extract.build(guide4, example_4_raw(), "guide-05")
    req4 = load("samples", "draft-05.request.json")
    out = []
    for sid, name, guide_file, doc, dropped, request in (
        ("sample-1", "예시 1: 카페 방문 가이드", "guide-sample.md", doc1, [], req1),
        ("sample-2", "예시 2: 리뷰플레이스 형식 가이드", "guide-sample-2.md", doc2, dropped2, GOOD2),
        ("sample-3", "예시 3: 화장품 배송 가이드", "guide-04.md", doc3, [], req3),
        ("sample-4", "예시 4: 확인하지 못한 조건이 있는 가이드", "guide-05.md", doc4, dropped4, req4),
    ):
        out.append({
            "id": sid, "name": name,
            "guide": (ROOT / "samples" / guide_file).read_text(encoding="utf-8"),
            "doc": doc, "dropped": dropped, "request": request,
            "form": extract.detect_form((ROOT / "samples" / guide_file).read_text(encoding="utf-8")),
            # 나눠 보여 주기 1단계: AI 없이 코드가 읽은 조건과 그 점검 결과
            "rules": rules_stage((ROOT / "samples" / guide_file).read_text(encoding="utf-8"), request),
            "result": engine.check(doc, request),
        })
    return out


def rules_stage(guide: str, request: dict) -> dict:
    from ai import extract
    from be import engine
    doc, dropped = extract.build(guide, {"campaign_type": None, "conditions": []})
    return {"doc": doc, "dropped": dropped, "result": engine.check(doc, request)}


def expected() -> str:
    return (
        "// 이 파일은 손으로 고치지 않아요. python fe/make_mock.py 가 be/engine.py를 돌려서 만들어요.\n"
        "// 지어낸 예시 1, 2의 가이드·조건표·점검 요청·점검 결과예요.\n"
        "'use strict';\n\n"
        "const MOCK = " + json.dumps({"scenarios": scenarios()}, ensure_ascii=False, indent=1) + ";\n"
    )


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    (ROOT / "fe" / "mock-data.js").write_text(expected(), encoding="utf-8", newline="\n")
    print("fe/mock-data.js를 만들었어요.")
