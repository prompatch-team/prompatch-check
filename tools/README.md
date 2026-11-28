# tools: 커밋 전 대조

실제 가이드·글의 문장, 블로그 주소, 키가 커밋에 섞여 들어가지 않게 막아요. 자세한 규칙은 `leak_check.py` 맨 위에 있어요.

1. 한 번만 설치: `python tools/leak_check.py --install` (커밋할 때마다 대조와 테스트가 돌아요)
2. 원문이 있으면 `.env`에 `PROMPATCH_PRIVATE_DATA=원문 폴더`를 적어요. 없으면 비워 둬도 돌아가요 (블로그 주소와 키 모양만 봐요)
3. 이슈·PR 글은 올리기 전에: `python tools/leak_check.py --text 글파일`

걸려도 괜찮은 화면 글자는 `leak-allow.txt`에 한 줄씩 적어요. 실제 글 문장은 적지 않아요.
