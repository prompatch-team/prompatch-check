# ai 폴더 (AI 영역, 담당 훈)

- 이 폴더 안에서만 파일을 만들고 고쳐요.
- 할 일: 가이드 원문 → `contracts/conditions.schema.json`에 맞는 조건 목록.
- LLM 결과는 그대로 믿지 말고, 스키마 확인과 `guide_quote` 위치가 가이드 원문과 실제로 맞는지 코드로 확인해요.
- 가이드에 없는 조건은 버려요. 애매한 조건은 `countable: false`, `type: "judgment"`로 둬요.
- 테스트는 `samples/guide-sample.md`와 `criteria/sample-answer-key.md`로 해요.
