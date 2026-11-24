# ai: 가이드에서 조건 뽑기 (훈)

광고주 가이드 원문을 받아 `contracts/conditions.schema.json` 형식의 조건 목록을 내보내요.

- **입력**: 가이드 원문 문자열 (예시: `samples/guide-sample.md`)
- **출력**: 조건 목록 JSON (예시: `contracts/conditions.example.json`)
- **연결 ①** owner예요. BE가 이 결과를 어떻게 받을지(함수 호출, 명령어, HTTP)는 감자와 정해요.

## 혼자 개발하는 법

1. `samples/guide-sample.md`를 넣어 조건 목록을 뽑아요.
2. 뽑은 결과를 `python contracts/validate.py conditions 결과.json`으로 확인해요.
3. `criteria/sample-answer-key.md`의 조건 정답과 비교해요. 빠뜨린 조건, 지어낸 조건이 없어야 해요.

## 지킬 것

- 가이드에 없는 조건은 만들지 않아요. 조건마다 `guide_quote`에 원문과 위치를 남겨요.
- 셀 수 있는 조건도 개수는 세지 않아요. 기준값만 뽑고 세는 건 BE가 해요.
- API 키는 `.env`의 `ANTHROPIC_API_KEY`에서 읽어요.

## 여기에 적어 주세요

- 쓰는 언어와 라이브러리:
- 실행 방법:
- 쓰는 모델과 프롬프트 위치:
