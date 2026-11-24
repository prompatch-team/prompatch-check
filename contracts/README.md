# 연결 형식 (contracts)

영역 사이에 주고받는 JSON의 약속이에요. 지금 파일은 **초안(0.1-draft)**이고, 11/25 회의에서 owner가 고쳐 확정해요.

| 연결 | 누가 → 누구 | 파일 | owner |
| --- | --- | --- | --- |
| ① 조건 목록 | AI → BE | `conditions.schema.json`, `conditions.example.json` | 훈 |
| ② 점검 요청 | FE → BE | `check-request.schema.json`, `check-request.example.json` | 리릭 |
| ② 점검 결과 | BE → FE | `check-result.schema.json`, `check-result.example.json` | 리릭 |

예시 파일은 `samples/`의 지어낸 가이드·원고로 만들었어요. 숫자는 `criteria/sample-answer-key.md`와 같아요.

## 조건 목록 (연결 ①)

조건마다 `id`, `type`, `label`, `countable`, `params`, `guide_quote`(가이드 원문과 위치)가 있어요.

| type | 뜻 | params 예 |
| --- | --- | --- |
| `keyword_count` | 키워드 횟수 | `{"keyword": "전포동 카페", "min": 5}` |
| `length` | 글자 수 | `{"min": 450, "count_spaces": false}` |
| `photo_count` | 사진 수 | `{"min": 10}` |
| `disclosure` | 대가성 문구 | `{"phrase": "...", "position": "top"}` |
| `map` | 지도 첨부 | `{"position": "bottom"}` |
| `judgment` | 셀 수 없는 조건 | `{"question": "매장 분위기 언급이 있는가"}` |

`countable: false`인 조건은 1주차에 판단하지 않고 `hold`로 돌려줘요.

## 점검 요청과 결과 (연결 ②)

- 요청: `guide_text`, `draft_text`, `photo_count`(블로거가 입력한 사진 수), `has_map`
- 결과: `summary`(지킴·빠짐·판단 보류 개수)와 조건마다 `status`, `expected`, `actual`, `unit`, `note`, `draft_spans`(원고 안 위치)

상태는 `kept`(지킴), `missing`(빠짐), `hold`(판단 보류) 셋뿐이에요.

## 형식을 바꿀 때

1. owner가 스키마와 예시를 같이 고치고 `version`을 올려요.
2. `python contracts/validate.py`로 예시가 통과하는지 확인해요.
3. PR 제목에 `[연결 ①]` 또는 `[연결 ②]`를 붙이고, 영향받는 사람을 리뷰어로 넣어요.

## 확인하기

```bash
pip install jsonschema
python contracts/validate.py                       # 예시 세 개 모두
python contracts/validate.py conditions out.json   # 내가 만든 파일
```
