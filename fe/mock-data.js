// 이 파일은 손으로 고치지 않아요. python fe/make_mock.py 가 be/engine.py를 돌려서 만들어요.
// 지어낸 예시 1, 2의 가이드·조건표·점검 요청·점검 결과예요.
'use strict';

const MOCK = {
 "scenarios": [
  {
   "id": "sample-1",
   "name": "예시 1: 카페 방문 가이드",
   "guide": "# 예시 가이드: 모래알 카페 체험단\n\n> 지어낸 예시예요. 실제 광고주·블로거와 관계없어요. 실제 가이드와 원고는 이 저장소에 올리지 않아요.\n\n모래알 카페 체험단에 선정되신 것을 축하드립니다. 아래 내용을 지켜 원고를 작성해 주세요.\n\n1. 필수 키워드 \"전포동 카페\"를 본문에 5회 이상 넣어 주세요.\n2. 본문은 공백 제외 450자 이상으로 작성해 주세요.\n3. 사진은 10장 이상 올려 주세요. 매장 외관 사진 1장을 꼭 포함해 주세요.\n4. 글 첫 부분에 \"업체로부터 음료를 제공받아 작성한 글입니다\" 문구를 넣어 주세요.\n5. 글 하단에 매장 지도를 첨부해 주세요.\n6. 매장 분위기와 좌석에 대한 솔직한 느낌을 적어 주세요.\n7. 다른 카페와 비교하는 내용은 넣지 말아 주세요.\n\n원고는 방문 후 7일 안에 제출해 주세요.\n",
   "doc": {
    "version": "0.3",
    "guide_id": "sample-moraeal",
    "platform": null,
    "campaign_type": "체험",
    "conditions": [
     {
      "id": "c1",
      "type": "keyword_count",
      "label": "필수 키워드 \"전포동 카페\" 5회 이상",
      "countable": true,
      "params": {
       "keywords": [
        "전포동 카페"
       ],
       "min": 5,
       "pick": "any",
       "scope": "body"
      },
      "guide_quote": {
       "text": "필수 키워드 \"전포동 카페\"를 본문에 5회 이상 넣어 주세요.",
       "start": 137,
       "end": 171
      }
     },
     {
      "id": "c2",
      "type": "length",
      "label": "본문 공백 제외 450자 이상",
      "countable": true,
      "params": {
       "min": 450,
       "count_spaces": false
      },
      "guide_quote": {
       "text": "본문은 공백 제외 450자 이상으로 작성해 주세요.",
       "start": 175,
       "end": 203
      }
     },
     {
      "id": "c3",
      "type": "photo_count",
      "label": "사진 10장 이상",
      "countable": true,
      "params": {
       "min": 10
      },
      "guide_quote": {
       "text": "사진은 10장 이상 올려 주세요.",
       "start": 207,
       "end": 225
      }
     },
     {
      "id": "c4",
      "type": "disclosure",
      "label": "글 첫 부분에 대가성 문구",
      "countable": true,
      "params": {
       "phrase": "업체로부터 음료를 제공받아 작성한 글입니다",
       "position": "top"
      },
      "guide_quote": {
       "text": "글 첫 부분에 \"업체로부터 음료를 제공받아 작성한 글입니다\" 문구를 넣어 주세요.",
       "start": 253,
       "end": 298
      }
     },
     {
      "id": "c5",
      "type": "map",
      "label": "글 하단에 지도 첨부",
      "countable": true,
      "params": {
       "position": "bottom"
      },
      "guide_quote": {
       "text": "글 하단에 매장 지도를 첨부해 주세요.",
       "start": 302,
       "end": 323
      }
     },
     {
      "id": "c6",
      "type": "judgment",
      "label": "매장 분위기와 좌석에 대한 느낌",
      "countable": false,
      "params": {
       "question": "매장 분위기와 좌석에 대한 느낌이 있는가"
      },
      "guide_quote": {
       "text": "매장 분위기와 좌석에 대한 솔직한 느낌을 적어 주세요.",
       "start": 327,
       "end": 357
      }
     },
     {
      "id": "c7",
      "type": "judgment",
      "label": "다른 카페와 비교하지 않기",
      "countable": false,
      "params": {
       "question": "다른 카페와 비교하는 내용이 없는가"
      },
      "guide_quote": {
       "text": "다른 카페와 비교하는 내용은 넣지 말아 주세요.",
       "start": 361,
       "end": 387
      }
     },
     {
      "id": "c8",
      "type": "photo_count",
      "label": "매장 외관 사진 1장 포함",
      "countable": false,
      "params": {
       "min": 1,
       "subject": "매장 외관"
      },
      "guide_quote": {
       "text": "매장 외관 사진 1장을 꼭 포함해 주세요.",
       "start": 226,
       "end": 249
      }
     }
    ]
   },
   "dropped": [],
   "request": {
    "version": "0.3",
    "input_mode": "text",
    "counts_source": "user",
    "title": null,
    "draft_text": "업체로부터 음료를 제공받아 작성한 글입니다.\n\n주말 오후에 전포동 카페 거리를 걷다가 모래알 카페에 들렀어요. 큰 창으로 햇빛이 길게 들어와서 들어가자마자 기분이 좋아지는 곳이었어요.\n\n[사진]\n[사진]\n\n창가 자리는 콘센트가 있어서 노트북을 펴 두기 좋았고, 안쪽에는 여럿이 앉을 수 있는 긴 테이블이 있었어요. 음악 소리가 크지 않아서 대화하기도 편했어요.\n\n[사진]\n[사진]\n[사진]\n\n시그니처 메뉴인 모래알 라떼는 우유 맛이 진하고 단맛이 적었어요. 위에 올라간 흑당 크림도 너무 달지 않아서 끝까지 맛있게 마셨어요. 같이 간 친구는 바닐라 빈 라떼를 골랐는데, 바닐라 향이 은은해서 좋았다고 해요.\n\n[사진]\n[사진]\n\n디저트는 매일 아침 매장에서 굽는다고 해요. 소금빵과 버터 쿠키를 먹어 봤는데 소금빵은 겉이 바삭하고 속이 쫄깃했어요. 오후 늦게 가면 몇 가지는 다 팔리고 없다고 하니 디저트가 목적이라면 일찍 가는 게 좋아요.\n\n[사진]\n\n전포동 카페 중에서 조용히 오래 머물 곳을 찾는다면 한 번 가 볼 만한 곳이에요. 주차는 근처 공영 주차장을 쓰면 되고, 역에서는 걸어서 7분 정도 걸려요. 다음에는 평일 오전에 전포동 카페 투어를 하면서 다시 들러 보려고요.\n",
    "photo_count": 8,
    "video_count": null,
    "has_map": false,
    "links": [],
    "hashtags": [],
    "media": [
     {
      "kind": "photo",
      "start": 104
     },
     {
      "kind": "photo",
      "start": 109
     },
     {
      "kind": "photo",
      "start": 203
     },
     {
      "kind": "photo",
      "start": 208
     },
     {
      "kind": "photo",
      "start": 213
     },
     {
      "kind": "photo",
      "start": 341
     },
     {
      "kind": "photo",
      "start": 346
     },
     {
      "kind": "photo",
      "start": 472
     }
    ],
    "banner_count": null,
    "banner_top": null
   },
   "form": null,
   "rules": {
    "doc": {
     "version": "0.3",
     "platform": null,
     "campaign_type": null,
     "conditions": []
    },
    "dropped": [],
    "result": {
     "version": "0.3",
     "summary": {
      "kept": 0,
      "missing": 0,
      "hold": 0
     },
     "results": [],
     "principles": [
      {
       "rule_id": "p1",
       "label": "대가성 표시가 제목 또는 첫 부분에 있음",
       "status": "kept",
       "basis": "공정위 추천·보증 심사지침(2024-12-01 시행), 네이버 D.I.A.+(2020-11-18)",
       "note": "본문 첫 문단에 있어요. \"첫 부분\" = 본문 첫 문단(우리 기준)",
       "draft_spans": [
        {
         "start": 0,
         "end": 24
        }
       ]
      },
      {
       "rule_id": "p2",
       "label": "모호한 대가성 표현 없음",
       "status": "kept",
       "basis": "공정위 추천·보증 심사지침(2024-12-01 시행)",
       "note": "\"수수료를 지급받을 수 있음\" 같은 조건부 표현이 없어요",
       "draft_spans": []
      },
      {
       "rule_id": "p3",
       "label": "키워드 과다 반복 없음",
       "status": "hold",
       "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"맥락과 관계 없는 키워드를 억지로 끼워 넣지 마세요\"",
       "note": "가이드에 키워드 횟수 조건이 없어서 판단 보류예요",
       "draft_spans": []
      },
      {
       "rule_id": "p4",
       "label": "외부 링크 과다 없음",
       "status": "kept",
       "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"외부로 이동하는 URL을 과도하게\"",
       "note": "외부 링크 0개. 가이드 필수 링크 밖의 링크가 3개를 넘으면 알려요(우리 기준)",
       "draft_spans": []
      },
      {
       "rule_id": "p5",
       "label": "사진에 비해 글이 충분함",
       "status": "kept",
       "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"핵심 내용은 텍스트로도\"",
       "note": "사진 1장당 약 52자. 30자보다 적으면 알려요(우리 기준)",
       "draft_spans": []
      }
     ],
     "tips": []
    }
   },
   "result": {
    "version": "0.3",
    "summary": {
     "kept": 1,
     "missing": 4,
     "hold": 3
    },
    "results": [
     {
      "condition_id": "c1",
      "label": "필수 키워드 \"전포동 카페\" 5회 이상",
      "status": "missing",
      "expected": 5,
      "actual": 3,
      "unit": "회",
      "note": "2회 더 필요해요. 글 앞부분(본문 앞 300자)에 키워드가 나와요(안내, 우리 기준)",
      "draft_spans": [
       {
        "start": 33,
        "end": 39
       },
       {
        "start": 478,
        "end": 484
       },
       {
        "start": 578,
        "end": 584
       }
      ]
     },
     {
      "condition_id": "c2",
      "label": "본문 공백 제외 450자 이상",
      "status": "missing",
      "expected": 450,
      "actual": 414,
      "unit": "자",
      "note": "공백 포함 550자(줄바꿈은 세지 않아요), 공백 제외 414자. 공백 제외 기준으로 판정했어요. 36자 더 필요해요. 본문 글 블록의 글자만 셌어요 ([사진] 줄, 링크 카드·동영상 제목 제외). 글자만으로 센 값이에요. 서식(HTML)이 없어서 보기 화면 줄은 규칙으로 뺐어요",
      "draft_spans": []
     },
     {
      "condition_id": "c3",
      "label": "사진 10장 이상",
      "status": "missing",
      "expected": 10,
      "actual": 8,
      "unit": "장",
      "note": "2장 더 필요해요 (입력한 사진 수 기준)",
      "draft_spans": []
     },
     {
      "condition_id": "c4",
      "label": "글 첫 부분에 대가성 문구",
      "status": "kept",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "본문 첫 문단에 있어요",
      "draft_spans": [
       {
        "start": 0,
        "end": 23
       }
      ]
     },
     {
      "condition_id": "c5",
      "label": "글 하단에 지도 첨부",
      "status": "missing",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "지도를 첨부하지 않았다고 입력했어요",
      "draft_spans": []
     },
     {
      "condition_id": "c6",
      "label": "매장 분위기와 좌석에 대한 느낌",
      "status": "hold",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "셀 수 없는 조건이라 판단 보류예요. 이 조건은 직접 확인해 주세요",
      "draft_spans": []
     },
     {
      "condition_id": "c7",
      "label": "다른 카페와 비교하지 않기",
      "status": "hold",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "셀 수 없는 조건이라 판단 보류예요. 이 조건은 직접 확인해 주세요",
      "draft_spans": []
     },
     {
      "condition_id": "c8",
      "label": "매장 외관 사진 1장 포함",
      "status": "hold",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "사진에 무엇이 찍혔는지는 확인할 수 없어요. 이 조건은 직접 확인해 주세요",
      "draft_spans": []
     }
    ],
    "principles": [
     {
      "rule_id": "p1",
      "label": "대가성 표시가 제목 또는 첫 부분에 있음",
      "status": "kept",
      "basis": "공정위 추천·보증 심사지침(2024-12-01 시행), 네이버 D.I.A.+(2020-11-18)",
      "note": "본문 첫 문단에 있어요. \"첫 부분\" = 본문 첫 문단(우리 기준)",
      "draft_spans": [
       {
        "start": 0,
        "end": 23
       }
      ]
     },
     {
      "rule_id": "p2",
      "label": "모호한 대가성 표현 없음",
      "status": "kept",
      "basis": "공정위 추천·보증 심사지침(2024-12-01 시행)",
      "note": "\"수수료를 지급받을 수 있음\" 같은 조건부 표현이 없어요",
      "draft_spans": []
     },
     {
      "rule_id": "p3",
      "label": "키워드 과다 반복 없음",
      "status": "kept",
      "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"맥락과 관계 없는 키워드를 억지로 끼워 넣지 마세요\"",
      "note": "\"전포동 카페\" 3회. 가이드 요구(5회)의 2배를 넘으면 알려요(우리 기준)",
      "draft_spans": []
     },
     {
      "rule_id": "p4",
      "label": "외부 링크 과다 없음",
      "status": "kept",
      "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"외부로 이동하는 URL을 과도하게\"",
      "note": "외부 링크 0개. 가이드 필수 링크 밖의 링크가 3개를 넘으면 알려요(우리 기준)",
      "draft_spans": []
     },
     {
      "rule_id": "p5",
      "label": "사진에 비해 글이 충분함",
      "status": "kept",
      "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"핵심 내용은 텍스트로도\"",
      "note": "사진 1장당 약 52자. 30자보다 적으면 알려요(우리 기준)",
      "draft_spans": []
     }
    ],
    "tips": [
     {
      "tip_id": "t1",
      "kind": "keyword_place",
      "condition_id": "c1",
      "label": "넣을 자리 추천: \"전포동 카페\"",
      "note": "\"전포동 카페\" 2회가 더 필요할 때 표시한 문단에 넣으면 더 자연스러워요. 지역 이름이나 \"다녀왔\", \"추천\", \"메뉴\" 같은 말이 있는 문단과 첫·끝 문단에서 골랐어요(우리 기준). 같은 키워드가 든 문장 바로 옆은 뺐어요. 문장은 직접 써 주세요. 아래 짧은 틀은 참고용이고 ○○은 직접 채워요",
      "templates": [
       "○○ 찾다가 알게 된 전포동 카페",
       "전포동 카페로 유명한 ○○",
       "○○하기 좋은 전포동 카페"
      ],
      "draft_spans": [
       {
        "start": 219,
        "end": 339
       }
      ]
     }
    ]
   }
  },
  {
   "id": "sample-2",
   "name": "예시 2: 리뷰플레이스 형식 가이드",
   "guide": "# 예시 가이드 2: 바다숲 녹차 스틱 (리뷰플레이스 형식)\n\n> 지어낸 예시예요. 실제 광고주·제품·블로거와 관계없어요. 리뷰플레이스 캠페인 페이지의 칸 구성만 본떴어요.\n\n[블로그] 바다숲 녹차 스틱을 소개해주세요\n\n제목키워드\n녹차스틱 , 바다숲녹차 , 간편녹차\n# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.\n\n본문키워드\n녹차스틱 , 바다숲녹차 , 간편녹차 , 사무실차\n# 키워드 중 1개를 선택하여 본문에 4번 이상 넣어주세요.\n\n캠페인 안내\n공정위 대가성 문구는 반드시 리뷰 상단에 기재해주세요.\n1. 포스팅 제목에 제품명을 언급할 경우, 반드시 '바다숲 녹차'로 작성해주세요. ('바다숲 녹차 스틱' x)\n2. '효능', '효과' 단어는 사용하지 말아주세요.\n3. 원료 특징을 적는 문장 아래에는 \"*제품이 아닌 원료에 관한 내용입니다\" 문구를 넣어주세요.\n4. 필수 해시태그 #바다숲녹차 를 넣어주세요.\n5. 사무실 책상 위에서 찍은 제품 사진을 1장 이상 넣어주세요.\n\n리뷰어 미션\n키워드\n링크 삽입\n1,000자 이상\n15장 이상\n동영상 첨부\n미션이 지켜지지 않을 경우 제공된 서비스 및 포인트의 환수 혹은 미지급 처리가 될 수 있습니다\n\n리뷰 등록기간 12.02 ~ 12.09\n",
   "doc": {
    "version": "0.3",
    "guide_id": "sample-badasoop",
    "platform": "reviewplace",
    "campaign_type": null,
    "conditions": [
     {
      "id": "c1",
      "type": "title_keyword",
      "label": "제목에 키워드 1개 (녹차스틱/바다숲녹차/간편녹차)",
      "countable": true,
      "params": {
       "keywords": [
        "녹차스틱",
        "바다숲녹차",
        "간편녹차"
       ],
       "pick": "any"
      },
      "guide_quote": {
       "text": "# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.",
       "start": 149,
       "end": 182
      }
     },
     {
      "id": "c2",
      "type": "hashtag",
      "label": "#태그에 키워드 1개 (녹차스틱/바다숲녹차/간편녹차)",
      "countable": true,
      "params": {
       "tags": [
        "#녹차스틱",
        "#바다숲녹차",
        "#간편녹차"
       ],
       "pick": "any"
      },
      "guide_quote": {
       "text": "# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.",
       "start": 149,
       "end": 182
      }
     },
     {
      "id": "c3",
      "type": "keyword_count",
      "label": "본문 키워드 1개를 4번 이상",
      "countable": true,
      "params": {
       "keywords": [
        "녹차스틱",
        "바다숲녹차",
        "간편녹차",
        "사무실차"
       ],
       "min": 4,
       "pick": "any",
       "scope": "body"
      },
      "guide_quote": {
       "text": "# 키워드 중 1개를 선택하여 본문에 4번 이상 넣어주세요.",
       "start": 217,
       "end": 250
      }
     },
     {
      "id": "c4",
      "type": "disclosure",
      "label": "대가성 문구를 리뷰 상단에",
      "countable": true,
      "params": {
       "phrase": null,
       "position": "top"
      },
      "guide_quote": {
       "text": "공정위 대가성 문구는 반드시 리뷰 상단에 기재해주세요.",
       "start": 259,
       "end": 289
      }
     },
     {
      "id": "c5",
      "type": "exact_phrase",
      "label": "제목의 제품명은 '바다숲 녹차'로",
      "countable": true,
      "params": {
       "allowed": "바다숲 녹차",
       "forbidden": [
        "바다숲 녹차 스틱"
       ],
       "scope": "title"
      },
      "guide_quote": {
       "text": "포스팅 제목에 제품명을 언급할 경우, 반드시 '바다숲 녹차'로 작성해주세요. ('바다숲 녹차 스틱' x)",
       "start": 293,
       "end": 351
      }
     },
     {
      "id": "c6",
      "type": "banned_terms",
      "label": "'효능', '효과' 쓰지 않기",
      "countable": true,
      "params": {
       "terms": [
        "효능",
        "효과"
       ],
       "category": null,
       "scope": "title_and_body"
      },
      "guide_quote": {
       "text": "'효능', '효과' 단어는 사용하지 말아주세요.",
       "start": 355,
       "end": 381
      }
     },
     {
      "id": "c7",
      "type": "required_phrase",
      "label": "원료 문장 아래 안내 문구",
      "countable": true,
      "params": {
       "phrase": "*제품이 아닌 원료에 관한 내용입니다",
       "scope": "body",
       "after": "원료 특징 문장"
      },
      "guide_quote": {
       "text": "원료 특징을 적는 문장 아래에는 \"*제품이 아닌 원료에 관한 내용입니다\" 문구를 넣어주세요.",
       "start": 385,
       "end": 436
      }
     },
     {
      "id": "c8",
      "type": "hashtag",
      "label": "필수 해시태그 #바다숲녹차",
      "countable": true,
      "params": {
       "tags": [
        "#바다숲녹차"
       ],
       "pick": "each"
      },
      "guide_quote": {
       "text": "필수 해시태그 #바다숲녹차 를 넣어주세요.",
       "start": 440,
       "end": 463
      }
     },
     {
      "id": "c9",
      "type": "photo_count",
      "label": "사무실 책상 위 제품 사진 1장 이상",
      "countable": false,
      "params": {
       "min": 1,
       "subject": "사무실 책상 위에서 찍은 제품"
      },
      "guide_quote": {
       "text": "사무실 책상 위에서 찍은 제품 사진을 1장 이상 넣어주세요.",
       "start": 467,
       "end": 500
      }
     },
     {
      "id": "c10",
      "type": "link",
      "label": "링크 삽입",
      "countable": true,
      "params": {
       "min": 1,
       "url": null
      },
      "guide_quote": {
       "text": "링크 삽입",
       "start": 513,
       "end": 518
      }
     },
     {
      "id": "c11",
      "type": "length",
      "label": "1,000자 이상",
      "countable": true,
      "params": {
       "min": 1000,
       "count_spaces": null
      },
      "guide_quote": {
       "text": "1,000자 이상",
       "start": 519,
       "end": 528
      }
     },
     {
      "id": "c12",
      "type": "photo_count",
      "label": "사진 15장 이상",
      "countable": true,
      "params": {
       "min": 15,
       "needs_review": true
      },
      "guide_quote": {
       "text": "15장 이상",
       "start": 529,
       "end": 535
      }
     },
     {
      "id": "c13",
      "type": "video_count",
      "label": "동영상 첨부",
      "countable": true,
      "params": {
       "min": 1
      },
      "guide_quote": {
       "text": "동영상 첨부",
       "start": 536,
       "end": 542
      }
     },
     {
      "id": "c14",
      "type": "outside_draft",
      "label": "리뷰 등록기간 12.02 ~ 12.09",
      "countable": false,
      "params": {
       "what": "기간"
      },
      "guide_quote": {
       "text": "리뷰 등록기간 12.02 ~ 12.09",
       "start": 597,
       "end": 618
      }
     }
    ]
   },
   "dropped": [
    {
     "code": "MISSION_KEYWORD_LINE",
     "reason": "리뷰어 미션의 \"키워드\" 줄은 위의 키워드 조건과 같은 조건이에요",
     "type": "keyword_count",
     "label": "키워드 (예시로 넣은 버린 조건)",
     "quote": "키워드"
    }
   ],
   "request": {
    "version": "0.3",
    "input_mode": "html",
    "counts_source": "parsed",
    "title": "바다숲녹차 일주일 후기, 바다숲 녹차 맛은",
    "draft_text": "업체로부터 제품을 제공받아 작성한 글입니다.\n\n사무실에서 마시기 좋은 바다숲녹차를 일주일 마셔 봤어요 🍵\n[사진]\n바다숲녹차는 찬물에도 잘 녹아요. 바다숲녹차 한 포면 한 잔이 돼요.\n찻잎을 곱게 갈아 만든 가루예요.\n*제품이 아닌 원료에 관한 내용입니다\n[동영상]\n오후에 바다숲녹차를 타 두면 퇴근할 때까지 마셔요.\n\n#바다숲녹차 #간편녹차",
    "photo_count": 15,
    "video_count": 1,
    "has_map": false,
    "links": [
     {
      "url": "https://example.invalid/shop",
      "start": null
     }
    ],
    "hashtags": [
     "#바다숲녹차",
     "#간편녹차"
    ],
    "media": [
     {
      "kind": "photo",
      "start": 59
     },
     {
      "kind": "video",
      "start": 143
     }
    ]
   },
   "form": "reviewplace",
   "rules": {
    "doc": {
     "version": "0.3",
     "platform": "reviewplace",
     "campaign_type": null,
     "conditions": [
      {
       "id": "c1",
       "type": "title_keyword",
       "label": "제목에 키워드 1개 이상",
       "countable": true,
       "params": {
        "keywords": [
         "녹차스틱",
         "바다숲녹차",
         "간편녹차"
        ],
        "pick": "any"
       },
       "guide_quote": {
        "text": "# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.",
        "start": 149,
        "end": 182
       },
       "source": "rule"
      },
      {
       "id": "c2",
       "type": "hashtag",
       "label": "#태그에 키워드 1개 이상",
       "countable": true,
       "params": {
        "tags": [
         "#녹차스틱",
         "#바다숲녹차",
         "#간편녹차"
        ],
        "pick": "any"
       },
       "guide_quote": {
        "text": "# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.",
        "start": 149,
        "end": 182
       },
       "source": "rule"
      },
      {
       "id": "c3",
       "type": "keyword_count",
       "label": "본문 키워드 1개를 4번 이상",
       "countable": true,
       "params": {
        "keywords": [
         "녹차스틱",
         "바다숲녹차",
         "간편녹차",
         "사무실차"
        ],
        "min": 4,
        "pick": "any",
        "scope": "body"
       },
       "guide_quote": {
        "text": "# 키워드 중 1개를 선택하여 본문에 4번 이상 넣어주세요.",
        "start": 217,
        "end": 250
       },
       "source": "rule"
      },
      {
       "id": "c4",
       "type": "disclosure",
       "label": "대가성 문구를 리뷰 상단에",
       "countable": true,
       "params": {
        "phrase": null,
        "position": "top"
       },
       "guide_quote": {
        "text": "공정위 대가성 문구는 반드시 리뷰 상단에 기재해주세요.",
        "start": 259,
        "end": 289
       },
       "source": "rule"
      },
      {
       "id": "c5",
       "type": "link",
       "label": "링크 삽입",
       "countable": true,
       "params": {
        "min": 1,
        "url": null
       },
       "guide_quote": {
        "text": "링크 삽입",
        "start": 513,
        "end": 518
       },
       "source": "rule"
      },
      {
       "id": "c6",
       "type": "length",
       "label": "1,000자 이상",
       "countable": true,
       "params": {
        "min": 1000,
        "count_spaces": null
       },
       "guide_quote": {
        "text": "1,000자 이상",
        "start": 519,
        "end": 528
       },
       "source": "rule"
      },
      {
       "id": "c7",
       "type": "photo_count",
       "label": "사진 15장 이상",
       "countable": true,
       "params": {
        "min": 15
       },
       "guide_quote": {
        "text": "15장 이상",
        "start": 529,
        "end": 535
       },
       "source": "rule"
      },
      {
       "id": "c8",
       "type": "video_count",
       "label": "동영상 첨부",
       "countable": true,
       "params": {
        "min": 1
       },
       "guide_quote": {
        "text": "동영상 첨부",
        "start": 536,
        "end": 542
       },
       "source": "rule"
      },
      {
       "id": "c9",
       "type": "outside_draft",
       "label": "리뷰 등록기간",
       "countable": false,
       "params": {
        "what": "기간"
       },
       "guide_quote": {
        "text": "리뷰 등록기간 12.02 ~ 12.09",
        "start": 597,
        "end": 618
       },
       "source": "rule"
      }
     ]
    },
    "dropped": [],
    "result": {
     "version": "0.3",
     "summary": {
      "kept": 7,
      "missing": 1,
      "hold": 0
     },
     "results": [
      {
       "condition_id": "c1",
       "label": "제목에 키워드 1개 이상",
       "status": "kept",
       "expected": 1,
       "actual": 1,
       "unit": "개",
       "note": "제목에 \"바다숲녹차\" 있어요. 제목 앞쪽에 있어요(안내, 우리 기준)",
       "draft_spans": [
        {
         "start": 0,
         "end": 5,
         "field": "title"
        }
       ]
      },
      {
       "condition_id": "c2",
       "label": "#태그에 키워드 1개 이상",
       "status": "kept",
       "expected": 1,
       "actual": 2,
       "unit": "개",
       "note": "#바다숲녹차, #간편녹차 태그가 있어요",
       "draft_spans": [
        {
         "start": 179,
         "end": 185
        },
        {
         "start": 186,
         "end": 191
        }
       ]
      },
      {
       "condition_id": "c3",
       "label": "본문 키워드 1개를 4번 이상",
       "status": "kept",
       "expected": 4,
       "actual": 5,
       "unit": "회",
       "note": "\"바다숲녹차\" 5회 있어요. 키워드별: \"녹차스틱\" 0회, \"바다숲녹차\" 5회(본문 글 4번 + 해시태그 1번)(4회 이상), \"간편녹차\" 1회(본문 글 0번 + 해시태그 1번), \"사무실차\" 0회. 글 앞부분(본문 앞 300자)에 키워드가 나와요(안내, 우리 기준)",
       "draft_spans": [
        {
         "start": 39,
         "end": 44
        },
        {
         "start": 64,
         "end": 69
        },
        {
         "start": 83,
         "end": 88
        },
        {
         "start": 153,
         "end": 158
        },
        {
         "start": 180,
         "end": 185
        }
       ]
      },
      {
       "condition_id": "c4",
       "label": "대가성 문구를 리뷰 상단에",
       "status": "kept",
       "expected": null,
       "actual": null,
       "unit": null,
       "note": "본문 첫 문단에 있어요 (대가성 표현 목록은 우리 기준)",
       "draft_spans": [
        {
         "start": 0,
         "end": 24
        }
       ]
      },
      {
       "condition_id": "c5",
       "label": "링크 삽입",
       "status": "kept",
       "expected": 1,
       "actual": 1,
       "unit": "개",
       "note": "링크 1개 (같은 주소는 1개로 셈)",
       "draft_spans": []
      },
      {
       "condition_id": "c6",
       "label": "1,000자 이상",
       "status": "missing",
       "expected": 1000,
       "actual": 172,
       "unit": "자",
       "note": "공백 포함 172자(줄바꿈은 세지 않아요), 공백 제외 137자. 공백 포함 기준으로 판정했어요 (가이드가 공백 기준을 정하지 않음). 828자 더 필요해요. 본문 글 블록의 글자만 셌어요 ([사진] 줄, 링크 카드·동영상 제목 제외)",
       "draft_spans": []
      },
      {
       "condition_id": "c7",
       "label": "사진 15장 이상",
       "status": "kept",
       "expected": 15,
       "actual": 15,
       "unit": "장",
       "note": "사진 15장 (자동으로 센 사진 수 기준)",
       "draft_spans": []
      },
      {
       "condition_id": "c8",
       "label": "동영상 첨부",
       "status": "kept",
       "expected": 1,
       "actual": 1,
       "unit": "개",
       "note": "동영상 1개 (자동으로 센 동영상 수 기준)",
       "draft_spans": []
      },
      {
       "condition_id": "c9",
       "label": "리뷰 등록기간",
       "status": "hold",
       "expected": null,
       "actual": null,
       "unit": null,
       "note": "원고 밖 조건이라 여기서는 확인할 수 없어요. 이 조건은 직접 확인해 주세요",
       "draft_spans": []
      }
     ],
     "principles": [
      {
       "rule_id": "p1",
       "label": "대가성 표시가 제목 또는 첫 부분에 있음",
       "status": "kept",
       "basis": "공정위 추천·보증 심사지침(2024-12-01 시행), 네이버 D.I.A.+(2020-11-18)",
       "note": "본문 첫 문단에 있어요. \"첫 부분\" = 본문 첫 문단(우리 기준)",
       "draft_spans": [
        {
         "start": 0,
         "end": 24
        }
       ]
      },
      {
       "rule_id": "p2",
       "label": "모호한 대가성 표현 없음",
       "status": "kept",
       "basis": "공정위 추천·보증 심사지침(2024-12-01 시행)",
       "note": "\"수수료를 지급받을 수 있음\" 같은 조건부 표현이 없어요",
       "draft_spans": []
      },
      {
       "rule_id": "p3",
       "label": "키워드 과다 반복 없음",
       "status": "missing",
       "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"맥락과 관계 없는 키워드를 억지로 끼워 넣지 마세요\"",
       "note": "이어진 두 문장에 \"바다숲녹차\"가 반복돼요(우리 기준). 네이버는 관련 없는 키워드를 억지로 넣지 말라고 안내해요. 확인해 보세요",
       "draft_spans": [
        {
         "start": 39,
         "end": 44
        },
        {
         "start": 64,
         "end": 69
        },
        {
         "start": 83,
         "end": 88
        }
       ]
      },
      {
       "rule_id": "p4",
       "label": "외부 링크 과다 없음",
       "status": "kept",
       "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"외부로 이동하는 URL을 과도하게\"",
       "note": "외부 링크 0개. 가이드 필수 링크 밖의 링크가 3개를 넘으면 알려요(우리 기준)",
       "draft_spans": []
      },
      {
       "rule_id": "p5",
       "label": "사진에 비해 글이 충분함",
       "status": "missing",
       "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"핵심 내용은 텍스트로도\"",
       "note": "사진 1장당 약 9자. 30자보다 적으면 알려요(우리 기준). 네이버가 불리하다고 밝힌 패턴이에요",
       "draft_spans": []
      }
     ],
     "tips": []
    }
   },
   "result": {
    "version": "0.3",
    "summary": {
     "kept": 10,
     "missing": 1,
     "hold": 2
    },
    "results": [
     {
      "condition_id": "c1",
      "label": "제목에 키워드 1개 (녹차스틱/바다숲녹차/간편녹차)",
      "status": "kept",
      "expected": 1,
      "actual": 1,
      "unit": "개",
      "note": "제목에 \"바다숲녹차\" 있어요. 제목 앞쪽에 있어요(안내, 우리 기준)",
      "draft_spans": [
       {
        "start": 0,
        "end": 5,
        "field": "title"
       }
      ]
     },
     {
      "condition_id": "c2",
      "label": "#태그에 키워드 1개 (녹차스틱/바다숲녹차/간편녹차)",
      "status": "kept",
      "expected": 1,
      "actual": 2,
      "unit": "개",
      "note": "#바다숲녹차, #간편녹차 태그가 있어요",
      "draft_spans": [
       {
        "start": 179,
        "end": 185
       },
       {
        "start": 186,
        "end": 191
       }
      ]
     },
     {
      "condition_id": "c3",
      "label": "본문 키워드 1개를 4번 이상",
      "status": "kept",
      "expected": 4,
      "actual": 5,
      "unit": "회",
      "note": "\"바다숲녹차\" 5회 있어요. 키워드별: \"녹차스틱\" 0회, \"바다숲녹차\" 5회(본문 글 4번 + 해시태그 1번)(4회 이상), \"간편녹차\" 1회(본문 글 0번 + 해시태그 1번), \"사무실차\" 0회. 글 앞부분(본문 앞 300자)에 키워드가 나와요(안내, 우리 기준)",
      "draft_spans": [
       {
        "start": 39,
        "end": 44
       },
       {
        "start": 64,
        "end": 69
       },
       {
        "start": 83,
        "end": 88
       },
       {
        "start": 153,
        "end": 158
       },
       {
        "start": 180,
        "end": 185
       }
      ]
     },
     {
      "condition_id": "c4",
      "label": "대가성 문구를 리뷰 상단에",
      "status": "kept",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "본문 첫 문단에 있어요 (대가성 표현 목록은 우리 기준)",
      "draft_spans": [
       {
        "start": 0,
        "end": 24
       }
      ]
     },
     {
      "condition_id": "c5",
      "label": "제목의 제품명은 '바다숲 녹차'로",
      "status": "kept",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "\"바다숲 녹차\"(으)로 썼어요",
      "draft_spans": [
       {
        "start": 14,
        "end": 20,
        "field": "title"
       }
      ]
     },
     {
      "condition_id": "c6",
      "label": "'효능', '효과' 쓰지 않기",
      "status": "kept",
      "expected": 0,
      "actual": 0,
      "unit": "곳",
      "note": "금지어가 없어요",
      "draft_spans": []
     },
     {
      "condition_id": "c7",
      "label": "원료 문장 아래 안내 문구",
      "status": "hold",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "문구는 있어요. \"원료 특징 문장\" 아래에 있는지는 판단 보류예요. 이 조건은 직접 확인해 주세요",
      "draft_spans": [
       {
        "start": 122,
        "end": 142
       }
      ]
     },
     {
      "condition_id": "c8",
      "label": "필수 해시태그 #바다숲녹차",
      "status": "kept",
      "expected": 1,
      "actual": 1,
      "unit": "개",
      "note": "#바다숲녹차 태그가 있어요",
      "draft_spans": [
       {
        "start": 179,
        "end": 185
       }
      ]
     },
     {
      "condition_id": "c9",
      "label": "사무실 책상 위 제품 사진 1장 이상",
      "status": "hold",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "사진에 무엇이 찍혔는지는 확인할 수 없어요. 이 조건은 직접 확인해 주세요",
      "draft_spans": []
     },
     {
      "condition_id": "c10",
      "label": "링크 삽입",
      "status": "kept",
      "expected": 1,
      "actual": 1,
      "unit": "개",
      "note": "링크 1개 (같은 주소는 1개로 셈)",
      "draft_spans": []
     },
     {
      "condition_id": "c11",
      "label": "1,000자 이상",
      "status": "missing",
      "expected": 1000,
      "actual": 172,
      "unit": "자",
      "note": "공백 포함 172자(줄바꿈은 세지 않아요), 공백 제외 137자. 공백 포함 기준으로 판정했어요 (가이드가 공백 기준을 정하지 않음). 828자 더 필요해요. 본문 글 블록의 글자만 셌어요 ([사진] 줄, 링크 카드·동영상 제목 제외)",
      "draft_spans": []
     },
     {
      "condition_id": "c12",
      "label": "사진 15장 이상",
      "status": "kept",
      "expected": 15,
      "actual": 15,
      "unit": "장",
      "note": "사진 15장 (자동으로 센 사진 수 기준). 기준 숫자는 가이드에서 확인하지 못한 값이에요. 조건표에서 확인해 주세요",
      "draft_spans": []
     },
     {
      "condition_id": "c13",
      "label": "동영상 첨부",
      "status": "kept",
      "expected": 1,
      "actual": 1,
      "unit": "개",
      "note": "동영상 1개 (자동으로 센 동영상 수 기준)",
      "draft_spans": []
     },
     {
      "condition_id": "c14",
      "label": "리뷰 등록기간 12.02 ~ 12.09",
      "status": "hold",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "원고 밖 조건이라 여기서는 확인할 수 없어요. 이 조건은 직접 확인해 주세요",
      "draft_spans": []
     }
    ],
    "principles": [
     {
      "rule_id": "p1",
      "label": "대가성 표시가 제목 또는 첫 부분에 있음",
      "status": "kept",
      "basis": "공정위 추천·보증 심사지침(2024-12-01 시행), 네이버 D.I.A.+(2020-11-18)",
      "note": "본문 첫 문단에 있어요. \"첫 부분\" = 본문 첫 문단(우리 기준)",
      "draft_spans": [
       {
        "start": 0,
        "end": 24
       }
      ]
     },
     {
      "rule_id": "p2",
      "label": "모호한 대가성 표현 없음",
      "status": "kept",
      "basis": "공정위 추천·보증 심사지침(2024-12-01 시행)",
      "note": "\"수수료를 지급받을 수 있음\" 같은 조건부 표현이 없어요",
      "draft_spans": []
     },
     {
      "rule_id": "p3",
      "label": "키워드 과다 반복 없음",
      "status": "missing",
      "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"맥락과 관계 없는 키워드를 억지로 끼워 넣지 마세요\"",
      "note": "이어진 두 문장에 \"바다숲녹차\"가 반복돼요(우리 기준). 네이버는 관련 없는 키워드를 억지로 넣지 말라고 안내해요. 확인해 보세요",
      "draft_spans": [
       {
        "start": 39,
        "end": 44
       },
       {
        "start": 64,
        "end": 69
       },
       {
        "start": 83,
        "end": 88
       }
      ]
     },
     {
      "rule_id": "p4",
      "label": "외부 링크 과다 없음",
      "status": "kept",
      "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"외부로 이동하는 URL을 과도하게\"",
      "note": "외부 링크 0개. 가이드 필수 링크 밖의 링크가 3개를 넘으면 알려요(우리 기준)",
      "draft_spans": []
     },
     {
      "rule_id": "p5",
      "label": "사진에 비해 글이 충분함",
      "status": "missing",
      "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"핵심 내용은 텍스트로도\"",
      "note": "사진 1장당 약 9자. 30자보다 적으면 알려요(우리 기준). 네이버가 불리하다고 밝힌 패턴이에요",
      "draft_spans": []
     }
    ],
    "tips": []
   }
  },
  {
   "id": "sample-3",
   "name": "예시 3: 화장품 배송 가이드",
   "guide": "# 예시 가이드 4: 이슬결 수분크림 (리뷰플레이스 형식, 배송형)\n\n> 지어낸 예시예요. 실제 광고주·제품·블로거와 관계없어요. 리뷰플레이스 캠페인 페이지의 칸 구성만 본떴어요.\n\n[블로그] 이슬결 수분크림을 소개해주세요\n\n제목키워드\n수분크림 추천 , 이슬결 크림 , 건성 수분크림\n# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.\n\n본문키워드\n수분크림 추천 , 이슬결 크림 , 건성 수분크림 , 겨울 수분크림\n# 키워드 중 1개를 선택하여 본문에 4번 이상 넣어주세요.\n\n캠페인 안내\n공정위 대가성 문구는 반드시 리뷰 상단에 기재해주세요.\n1. 제품명을 언급할 경우, 반드시 '이슬결 수분크림'으로 작성해주세요. ('이슬결 보습크림' x)\n2. '치료', '완치', '효과' 단어는 사용하지 말아주세요.\n3. 성분을 소개하는 문장 아래에는 \"*개인에 따라 차이가 있을 수 있습니다\" 문구를 넣어주세요.\n4. 본문에 구매 링크를 넣어주세요. https://example.invalid/iseulgyeol\n5. 제품을 손등에 바른 사진을 1장 이상 넣어주세요.\n\n리뷰어 미션\n키워드\n링크 삽입\n800자 이상\n12장 이상\n미션이 지켜지지 않을 경우 제공된 제품 및 포인트의 환수 혹은 미지급 처리가 될 수 있습니다\n\n리뷰 등록기간 12.03 ~ 12.10\n",
   "doc": {
    "version": "0.3",
    "guide_id": "sample-iseulgyeol",
    "platform": "reviewplace",
    "campaign_type": "체험",
    "conditions": [
     {
      "id": "c1",
      "type": "title_keyword",
      "label": "제목에 키워드 1개 이상",
      "countable": true,
      "params": {
       "keywords": [
        "수분크림 추천",
        "이슬결 크림",
        "건성 수분크림"
       ],
       "pick": "any"
      },
      "guide_quote": {
       "text": "# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.",
       "start": 159,
       "end": 192
      }
     },
     {
      "id": "c2",
      "type": "hashtag",
      "label": "#태그에 키워드 1개 이상",
      "countable": true,
      "params": {
       "tags": [
        "#수분크림추천",
        "#이슬결크림",
        "#건성수분크림"
       ],
       "pick": "any"
      },
      "guide_quote": {
       "text": "# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.",
       "start": 159,
       "end": 192
      }
     },
     {
      "id": "c3",
      "type": "keyword_count",
      "label": "본문 키워드 1개를 4번 이상",
      "countable": true,
      "params": {
       "keywords": [
        "수분크림 추천",
        "이슬결 크림",
        "건성 수분크림",
        "겨울 수분크림"
       ],
       "min": 4,
       "pick": "any",
       "scope": "body"
      },
      "guide_quote": {
       "text": "# 키워드 중 1개를 선택하여 본문에 4번 이상 넣어주세요.",
       "start": 237,
       "end": 270
      }
     },
     {
      "id": "c4",
      "type": "disclosure",
      "label": "대가성 문구를 리뷰 상단에",
      "countable": true,
      "params": {
       "phrase": null,
       "position": "top"
      },
      "guide_quote": {
       "text": "공정위 대가성 문구는 반드시 리뷰 상단에 기재해주세요.",
       "start": 279,
       "end": 309
      }
     },
     {
      "id": "c5",
      "type": "exact_phrase",
      "label": "제품명 표기 이슬결 수분크림",
      "countable": true,
      "params": {
       "allowed": "이슬결 수분크림",
       "forbidden": [
        "이슬결 보습크림"
       ],
       "scope": "title_and_body"
      },
      "guide_quote": {
       "text": "제품명을 언급할 경우, 반드시 '이슬결 수분크림'으로 작성해주세요. ('이슬결 보습크림' x)",
       "start": 313,
       "end": 365
      }
     },
     {
      "id": "c6",
      "type": "banned_terms",
      "label": "치료·완치·효과 사용 금지",
      "countable": true,
      "params": {
       "terms": [
        "치료",
        "완치",
        "효과"
       ],
       "category": null,
       "scope": "title_and_body"
      },
      "guide_quote": {
       "text": "'치료', '완치', '효과' 단어는 사용하지 말아주세요.",
       "start": 369,
       "end": 401
      }
     },
     {
      "id": "c7",
      "type": "required_phrase",
      "label": "성분 문장 아래 개인차 문구",
      "countable": true,
      "params": {
       "phrase": "*개인에 따라 차이가 있을 수 있습니다",
       "scope": "body",
       "after": "성분을 소개하는 문장"
      },
      "guide_quote": {
       "text": "성분을 소개하는 문장 아래에는 \"*개인에 따라 차이가 있을 수 있습니다\" 문구를 넣어주세요.",
       "start": 405,
       "end": 456
      }
     },
     {
      "id": "c8",
      "type": "link",
      "label": "구매 링크 1개 이상",
      "countable": true,
      "params": {
       "min": 1,
       "url": "https://example.invalid/iseulgyeol"
      },
      "guide_quote": {
       "text": "본문에 구매 링크를 넣어주세요. https://example.invalid/iseulgyeol",
       "start": 460,
       "end": 512
      },
      "extra_quotes": [
       {
        "text": "링크 삽입",
        "start": 556,
        "end": 561
       }
      ]
     },
     {
      "id": "c9",
      "type": "photo_count",
      "label": "손등 사진 1장 이상",
      "countable": false,
      "params": {
       "min": 1,
       "subject": "제품을 손등에 바른 사진"
      },
      "guide_quote": {
       "text": "제품을 손등에 바른 사진을 1장 이상 넣어주세요.",
       "start": 516,
       "end": 543
      }
     },
     {
      "id": "c10",
      "type": "length",
      "label": "800자 이상",
      "countable": true,
      "params": {
       "min": 800,
       "count_spaces": null
      },
      "guide_quote": {
       "text": "800자 이상",
       "start": 562,
       "end": 569
      }
     },
     {
      "id": "c11",
      "type": "photo_count",
      "label": "사진 12장 이상",
      "countable": true,
      "params": {
       "min": 12
      },
      "guide_quote": {
       "text": "12장 이상",
       "start": 570,
       "end": 576
      }
     },
     {
      "id": "c12",
      "type": "outside_draft",
      "label": "리뷰 등록기간",
      "countable": false,
      "params": {
       "what": "기간"
      },
      "guide_quote": {
       "text": "리뷰 등록기간 12.03 ~ 12.10",
       "start": 630,
       "end": 651
      }
     }
    ]
   },
   "dropped": [],
   "request": {
    "version": "0.3",
    "input_mode": "html",
    "counts_source": "parsed",
    "title": "이슬결 보습크림 두 주 사용 후기, 겨울철 건성 피부 관리",
    "draft_text": "이 글은 업체로부터 제품을 제공받아 직접 써 보고 작성했습니다.\n\n날이 추워지니 세수만 하고 나와도 볼이 땅겨서, 겨울 수분크림을 하나 찾고 있었어요. 마침 이슬결 수분크림을 써 볼 기회가 생겨서 이 주 동안 아침저녁으로 발라 봤어요. 원래 쓰던 크림도 거의 바닥나던 참이라 때가 잘 맞았어요.\n\n[사진]\n[사진]\n\n상자를 열면 크림 본품과 작은 주걱이 같이 들어 있어요. 용기는 불투명한 유리라서 묵직하고, 뚜껑을 열면 속마개가 한 번 더 있어서 여행 갈 때 챙겨도 샐 걱정이 없겠더라고요. 화장대 위에 올려 두면 깔끔해 보여서 마음에 들었어요.\n\n[사진]\n[사진]\n[사진]\n\n제형은 묽은 젤과 크림의 중간쯤이에요. 주걱으로 조금 떠서 손등에 올려 보면 금방 펴 발리고, 문지르면 물방울처럼 풀리면서 스며들어요. 향은 거의 없는 편이라 향에 예민한 분도 쓰기 편할 것 같아요. 색은 살짝 푸른빛이 도는 흰색이에요.\n\n[사진]\n[사진]\n[사진]\n\n건성 수분크림을 고를 때 저는 바른 뒤에 끈적임이 남는지를 제일 먼저 봐요. 이 제품은 바르고 일 분쯤 지나면 겉은 보송한데 속은 촉촉한 느낌이 남았어요. 겨울 수분크림으로 쓰기에 무겁지 않아서, 아침에 화장하기 전에 발라도 밀리지 않았어요. 선크림을 덧발라도 뭉치지 않아서 출근 준비가 편했어요.\n\n[사진]\n[사진]\n\n성분표를 보면 보리 발효 추출물과 세 가지 히알루론산이 들어 있다고 적혀 있어요.\n*개인에 따라 차이가 있을 수 있습니다\n\n밤에는 조금 도톰하게 올려서 수면 팩처럼 썼어요. 다음 날 아침에 세수할 때 손에 닿는 느낌이 부드러워서 만족스러웠어요. 히터를 오래 트는 사무실에서도 오후까지 땅김이 덜했고, 건조해서 일어나던 각질에도 효과가 있었어요. 코 옆이나 입가처럼 자주 트는 곳에는 한 번 더 덧발랐어요.\n\n[사진]\n[사진]\n\n같이 사는 동생도 며칠 빌려 썼는데, 지성 피부인데도 번들거리지 않는다고 했어요. 겨울 수분크림은 무거워서 싫다던 동생이 먼저 찾을 정도였어요. 다만 아주 건조한 날에는 오일을 한 방울 섞어 바르는 편이 더 좋았어요.\n\n용량은 오십 밀리리터인데 하루 두 번 써도 두 달은 넉넉히 쓸 것 같아요. 겨울 수분크림을 찾는 분이라면 한 번 살펴보세요. 구매는 아래 링크에서 할 수 있어요.\n\nhttps://example.invalid/iseulgyeol\n\n#겨울수분크림 #이슬결 #보습\n",
    "photo_count": 12,
    "video_count": 0,
    "has_map": false,
    "links": [
     {
      "url": "https://example.invalid/iseulgyeol",
      "start": 1107
     }
    ],
    "hashtags": [
     "#겨울수분크림",
     "#이슬결",
     "#보습"
    ],
    "media": [
     {
      "kind": "photo",
      "start": 166
     },
     {
      "kind": "photo",
      "start": 171
     },
     {
      "kind": "photo",
      "start": 308
     },
     {
      "kind": "photo",
      "start": 313
     },
     {
      "kind": "photo",
      "start": 318
     },
     {
      "kind": "photo",
      "start": 458
     },
     {
      "kind": "photo",
      "start": 463
     },
     {
      "kind": "photo",
      "start": 468
     },
     {
      "kind": "photo",
      "start": 642
     },
     {
      "kind": "photo",
      "start": 647
     },
     {
      "kind": "photo",
      "start": 881
     },
     {
      "kind": "photo",
      "start": 886
     }
    ]
   },
   "form": "reviewplace",
   "rules": {
    "doc": {
     "version": "0.3",
     "platform": "reviewplace",
     "campaign_type": null,
     "conditions": [
      {
       "id": "c1",
       "type": "title_keyword",
       "label": "제목에 키워드 1개 이상",
       "countable": true,
       "params": {
        "keywords": [
         "수분크림 추천",
         "이슬결 크림",
         "건성 수분크림"
        ],
        "pick": "any"
       },
       "guide_quote": {
        "text": "# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.",
        "start": 159,
        "end": 192
       },
       "source": "rule"
      },
      {
       "id": "c2",
       "type": "hashtag",
       "label": "#태그에 키워드 1개 이상",
       "countable": true,
       "params": {
        "tags": [
         "#수분크림추천",
         "#이슬결크림",
         "#건성수분크림"
        ],
        "pick": "any"
       },
       "guide_quote": {
        "text": "# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.",
        "start": 159,
        "end": 192
       },
       "source": "rule"
      },
      {
       "id": "c3",
       "type": "keyword_count",
       "label": "본문 키워드 1개를 4번 이상",
       "countable": true,
       "params": {
        "keywords": [
         "수분크림 추천",
         "이슬결 크림",
         "건성 수분크림",
         "겨울 수분크림"
        ],
        "min": 4,
        "pick": "any",
        "scope": "body"
       },
       "guide_quote": {
        "text": "# 키워드 중 1개를 선택하여 본문에 4번 이상 넣어주세요.",
        "start": 237,
        "end": 270
       },
       "source": "rule"
      },
      {
       "id": "c4",
       "type": "disclosure",
       "label": "대가성 문구를 리뷰 상단에",
       "countable": true,
       "params": {
        "phrase": null,
        "position": "top"
       },
       "guide_quote": {
        "text": "공정위 대가성 문구는 반드시 리뷰 상단에 기재해주세요.",
        "start": 279,
        "end": 309
       },
       "source": "rule"
      },
      {
       "id": "c5",
       "type": "link",
       "label": "링크 삽입",
       "countable": true,
       "params": {
        "min": 1,
        "url": null
       },
       "guide_quote": {
        "text": "링크 삽입",
        "start": 556,
        "end": 561
       },
       "source": "rule"
      },
      {
       "id": "c6",
       "type": "length",
       "label": "800자 이상",
       "countable": true,
       "params": {
        "min": 800,
        "count_spaces": null
       },
       "guide_quote": {
        "text": "800자 이상",
        "start": 562,
        "end": 569
       },
       "source": "rule"
      },
      {
       "id": "c7",
       "type": "photo_count",
       "label": "사진 12장 이상",
       "countable": true,
       "params": {
        "min": 12
       },
       "guide_quote": {
        "text": "12장 이상",
        "start": 570,
        "end": 576
       },
       "source": "rule"
      },
      {
       "id": "c8",
       "type": "outside_draft",
       "label": "리뷰 등록기간",
       "countable": false,
       "params": {
        "what": "기간"
       },
       "guide_quote": {
        "text": "리뷰 등록기간 12.03 ~ 12.10",
        "start": 630,
        "end": 651
       },
       "source": "rule"
      }
     ]
    },
    "dropped": [],
    "result": {
     "version": "0.3",
     "summary": {
      "kept": 5,
      "missing": 2,
      "hold": 0
     },
     "results": [
      {
       "condition_id": "c1",
       "label": "제목에 키워드 1개 이상",
       "status": "missing",
       "expected": 1,
       "actual": 0,
       "unit": "개",
       "note": "제목에 키워드가 없어요 (\"수분크림 추천\", \"이슬결 크림\", \"건성 수분크림\" 중 1개 필요)",
       "draft_spans": []
      },
      {
       "condition_id": "c2",
       "label": "#태그에 키워드 1개 이상",
       "status": "missing",
       "expected": 1,
       "actual": 0,
       "unit": "개",
       "note": "태그가 없어요 (#수분크림추천, #이슬결크림, #건성수분크림 중 1개 필요). 본문과 입력한 태그에서 찾았어요",
       "draft_spans": []
      },
      {
       "condition_id": "c3",
       "label": "본문 키워드 1개를 4번 이상",
       "status": "kept",
       "expected": 4,
       "actual": 4,
       "unit": "회",
       "note": "\"겨울 수분크림\" 4회 있어요. 키워드별: \"수분크림 추천\" 0회, \"이슬결 크림\" 0회, \"건성 수분크림\" 1회, \"겨울 수분크림\" 4회(4회 이상). 글 앞부분(본문 앞 300자)에 키워드가 나와요(안내, 우리 기준)",
       "draft_spans": [
        {
         "start": 64,
         "end": 71
        },
        {
         "start": 561,
         "end": 568
        },
        {
         "start": 938,
         "end": 945
        },
        {
         "start": 1057,
         "end": 1064
        }
       ]
      },
      {
       "condition_id": "c4",
       "label": "대가성 문구를 리뷰 상단에",
       "status": "kept",
       "expected": null,
       "actual": null,
       "unit": null,
       "note": "본문 첫 문단에 있어요 (대가성 표현 목록은 우리 기준)",
       "draft_spans": [
        {
         "start": 0,
         "end": 35
        }
       ]
      },
      {
       "condition_id": "c5",
       "label": "링크 삽입",
       "status": "kept",
       "expected": 1,
       "actual": 1,
       "unit": "개",
       "note": "링크 1개 (같은 주소는 1개로 셈)",
       "draft_spans": [
        {
         "start": 1107,
         "end": 1141
        }
       ]
      },
      {
       "condition_id": "c6",
       "label": "800자 이상",
       "status": "kept",
       "expected": 800,
       "actual": 1073,
       "unit": "자",
       "note": "공백 포함 1073자(줄바꿈은 세지 않아요), 공백 제외 813자. 공백 포함 기준으로 판정했어요 (가이드가 공백 기준을 정하지 않음). 본문 글 블록의 글자만 셌어요 ([사진] 줄, 링크 카드·동영상 제목 제외)",
       "draft_spans": []
      },
      {
       "condition_id": "c7",
       "label": "사진 12장 이상",
       "status": "kept",
       "expected": 12,
       "actual": 12,
       "unit": "장",
       "note": "사진 12장 (자동으로 센 사진 수 기준)",
       "draft_spans": []
      },
      {
       "condition_id": "c8",
       "label": "리뷰 등록기간",
       "status": "hold",
       "expected": null,
       "actual": null,
       "unit": null,
       "note": "원고 밖 조건이라 여기서는 확인할 수 없어요. 이 조건은 직접 확인해 주세요",
       "draft_spans": []
      }
     ],
     "principles": [
      {
       "rule_id": "p1",
       "label": "대가성 표시가 제목 또는 첫 부분에 있음",
       "status": "kept",
       "basis": "공정위 추천·보증 심사지침(2024-12-01 시행), 네이버 D.I.A.+(2020-11-18)",
       "note": "본문 첫 문단에 있어요. \"첫 부분\" = 본문 첫 문단(우리 기준)",
       "draft_spans": [
        {
         "start": 0,
         "end": 35
        }
       ]
      },
      {
       "rule_id": "p2",
       "label": "모호한 대가성 표현 없음",
       "status": "kept",
       "basis": "공정위 추천·보증 심사지침(2024-12-01 시행)",
       "note": "\"수수료를 지급받을 수 있음\" 같은 조건부 표현이 없어요",
       "draft_spans": []
      },
      {
       "rule_id": "p3",
       "label": "키워드 과다 반복 없음",
       "status": "kept",
       "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"맥락과 관계 없는 키워드를 억지로 끼워 넣지 마세요\"",
       "note": "\"겨울 수분크림\" 4회. 가이드 요구(4회)의 2배를 넘으면 알려요(우리 기준)",
       "draft_spans": []
      },
      {
       "rule_id": "p4",
       "label": "외부 링크 과다 없음",
       "status": "kept",
       "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"외부로 이동하는 URL을 과도하게\"",
       "note": "외부 링크 0개. 가이드 필수 링크 밖의 링크가 3개를 넘으면 알려요(우리 기준)",
       "draft_spans": []
      },
      {
       "rule_id": "p5",
       "label": "사진에 비해 글이 충분함",
       "status": "kept",
       "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"핵심 내용은 텍스트로도\"",
       "note": "사진 1장당 약 68자. 30자보다 적으면 알려요(우리 기준)",
       "draft_spans": []
      }
     ],
     "tips": []
    }
   },
   "result": {
    "version": "0.3",
    "summary": {
     "kept": 5,
     "missing": 4,
     "hold": 2
    },
    "results": [
     {
      "condition_id": "c1",
      "label": "제목에 키워드 1개 이상",
      "status": "missing",
      "expected": 1,
      "actual": 0,
      "unit": "개",
      "note": "제목에 키워드가 없어요 (\"수분크림 추천\", \"이슬결 크림\", \"건성 수분크림\" 중 1개 필요)",
      "draft_spans": []
     },
     {
      "condition_id": "c2",
      "label": "#태그에 키워드 1개 이상",
      "status": "missing",
      "expected": 1,
      "actual": 0,
      "unit": "개",
      "note": "태그가 없어요 (#수분크림추천, #이슬결크림, #건성수분크림 중 1개 필요). 본문과 입력한 태그에서 찾았어요",
      "draft_spans": []
     },
     {
      "condition_id": "c3",
      "label": "본문 키워드 1개를 4번 이상",
      "status": "kept",
      "expected": 4,
      "actual": 4,
      "unit": "회",
      "note": "\"겨울 수분크림\" 4회 있어요. 키워드별: \"수분크림 추천\" 0회, \"이슬결 크림\" 0회, \"건성 수분크림\" 1회, \"겨울 수분크림\" 4회(4회 이상). 글 앞부분(본문 앞 300자)에 키워드가 나와요(안내, 우리 기준)",
      "draft_spans": [
       {
        "start": 64,
        "end": 71
       },
       {
        "start": 561,
        "end": 568
       },
       {
        "start": 938,
        "end": 945
       },
       {
        "start": 1057,
        "end": 1064
       }
      ]
     },
     {
      "condition_id": "c4",
      "label": "대가성 문구를 리뷰 상단에",
      "status": "kept",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "본문 첫 문단에 있어요 (대가성 표현 목록은 우리 기준)",
      "draft_spans": [
       {
        "start": 0,
        "end": 35
       }
      ]
     },
     {
      "condition_id": "c5",
      "label": "제품명 표기 이슬결 수분크림",
      "status": "missing",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "쓰면 안 되는 표기가 1곳 있어요: \"이슬결 보습크림\"",
      "draft_spans": [
       {
        "start": 0,
        "end": 8,
        "field": "title"
       }
      ]
     },
     {
      "condition_id": "c6",
      "label": "치료·완치·효과 사용 금지",
      "status": "missing",
      "expected": 0,
      "actual": 1,
      "unit": "곳",
      "note": "금지어가 있어요: \"효과\" 1곳",
      "draft_spans": [
       {
        "start": 836,
        "end": 838
       }
      ]
     },
     {
      "condition_id": "c7",
      "label": "성분 문장 아래 개인차 문구",
      "status": "hold",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "문구는 있어요. \"성분을 소개하는 문장\" 아래에 있는지는 판단 보류예요. 이 조건은 직접 확인해 주세요",
      "draft_spans": [
       {
        "start": 699,
        "end": 720
       }
      ]
     },
     {
      "condition_id": "c8",
      "label": "구매 링크 1개 이상",
      "status": "kept",
      "expected": 1,
      "actual": 1,
      "unit": "개",
      "note": "가이드가 정한 주소의 링크가 있어요",
      "draft_spans": [
       {
        "start": 1107,
        "end": 1141
       }
      ]
     },
     {
      "condition_id": "c9",
      "label": "손등 사진 1장 이상",
      "status": "hold",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "사진에 무엇이 찍혔는지는 확인할 수 없어요. 이 조건은 직접 확인해 주세요",
      "draft_spans": []
     },
     {
      "condition_id": "c10",
      "label": "800자 이상",
      "status": "kept",
      "expected": 800,
      "actual": 1073,
      "unit": "자",
      "note": "공백 포함 1073자(줄바꿈은 세지 않아요), 공백 제외 813자. 공백 포함 기준으로 판정했어요 (가이드가 공백 기준을 정하지 않음). 본문 글 블록의 글자만 셌어요 ([사진] 줄, 링크 카드·동영상 제목 제외)",
      "draft_spans": []
     },
     {
      "condition_id": "c11",
      "label": "사진 12장 이상",
      "status": "kept",
      "expected": 12,
      "actual": 12,
      "unit": "장",
      "note": "사진 12장 (자동으로 센 사진 수 기준)",
      "draft_spans": []
     },
     {
      "condition_id": "c12",
      "label": "리뷰 등록기간",
      "status": "hold",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "원고 밖 조건이라 여기서는 확인할 수 없어요. 이 조건은 직접 확인해 주세요",
      "draft_spans": []
     }
    ],
    "principles": [
     {
      "rule_id": "p1",
      "label": "대가성 표시가 제목 또는 첫 부분에 있음",
      "status": "kept",
      "basis": "공정위 추천·보증 심사지침(2024-12-01 시행), 네이버 D.I.A.+(2020-11-18)",
      "note": "본문 첫 문단에 있어요. \"첫 부분\" = 본문 첫 문단(우리 기준)",
      "draft_spans": [
       {
        "start": 0,
        "end": 35
       }
      ]
     },
     {
      "rule_id": "p2",
      "label": "모호한 대가성 표현 없음",
      "status": "kept",
      "basis": "공정위 추천·보증 심사지침(2024-12-01 시행)",
      "note": "\"수수료를 지급받을 수 있음\" 같은 조건부 표현이 없어요",
      "draft_spans": []
     },
     {
      "rule_id": "p3",
      "label": "키워드 과다 반복 없음",
      "status": "kept",
      "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"맥락과 관계 없는 키워드를 억지로 끼워 넣지 마세요\"",
      "note": "\"겨울 수분크림\" 4회. 가이드 요구(4회)의 2배를 넘으면 알려요(우리 기준)",
      "draft_spans": []
     },
     {
      "rule_id": "p4",
      "label": "외부 링크 과다 없음",
      "status": "kept",
      "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"외부로 이동하는 URL을 과도하게\"",
      "note": "외부 링크 0개. 가이드 필수 링크 밖의 링크가 3개를 넘으면 알려요(우리 기준)",
      "draft_spans": []
     },
     {
      "rule_id": "p5",
      "label": "사진에 비해 글이 충분함",
      "status": "kept",
      "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"핵심 내용은 텍스트로도\"",
      "note": "사진 1장당 약 68자. 30자보다 적으면 알려요(우리 기준)",
      "draft_spans": []
     }
    ],
    "tips": []
   }
  },
  {
   "id": "sample-4",
   "name": "예시 4: 확인하지 못한 조건이 있는 가이드",
   "guide": "# 예시 가이드 5: 새벽곡물 선식 (리뷰플레이스 형식, 배송형)\n\n> 지어낸 예시예요. 실제 광고주·제품·블로거와 관계없어요. 리뷰플레이스 캠페인 페이지의 칸 구성만 본떴어요.\n\n[블로그] 새벽곡물 선식을 소개해주세요\n\n제목키워드\n아침 선식 , 새벽곡물 , 간편 아침식사\n# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.\n\n본문키워드\n아침 선식 , 새벽곡물 , 간편 아침식사\n# 키워드 중 1개를 선택하여 본문에 3번 이상 넣어주세요.\n\n캠페인 안내\n공정위 대가성 문구는 반드시 리뷰 상단에 기재해주세요.\n1. 질병 이름은 직접 언급하지 말아주세요.\n2. '다이어트', '감량' 단어는 사용하지 말아주세요.\n3. 원료를 소개하는 문장 아래에는 \"*제품이 아닌 원료에 관한 설명입니다\" 문구를 넣어주세요.\n4. 필수 해시태그 #새벽곡물 #아침선식 을 모두 넣어주세요.\n5. 물이나 우유에 타는 모습을 사진으로 1장 이상 넣어주세요.\n\n리뷰어 미션\n키워드\n1,000자 이상\n15장 이상\n동영상 첨부\n미션이 지켜지지 않을 경우 제공된 제품 및 포인트의 환수 혹은 미지급 처리가 될 수 있습니다\n\n리뷰 등록기간 12.08 ~ 12.15\n",
   "doc": {
    "version": "0.3",
    "guide_id": "guide-05",
    "platform": "reviewplace",
    "campaign_type": "체험",
    "conditions": [
     {
      "id": "c1",
      "type": "title_keyword",
      "label": "제목에 키워드 1개 이상",
      "countable": true,
      "params": {
       "keywords": [
        "아침 선식",
        "새벽곡물",
        "간편 아침식사"
       ],
       "pick": "any"
      },
      "guide_quote": {
       "text": "# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.",
       "start": 153,
       "end": 186
      },
      "source": "rule"
     },
     {
      "id": "c2",
      "type": "hashtag",
      "label": "#태그에 키워드 1개 이상",
      "countable": true,
      "params": {
       "tags": [
        "#아침선식",
        "#새벽곡물",
        "#간편아침식사"
       ],
       "pick": "any"
      },
      "guide_quote": {
       "text": "# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.",
       "start": 153,
       "end": 186
      },
      "source": "rule"
     },
     {
      "id": "c3",
      "type": "keyword_count",
      "label": "본문 키워드 1개를 3번 이상",
      "countable": true,
      "params": {
       "keywords": [
        "아침 선식",
        "새벽곡물",
        "간편 아침식사"
       ],
       "min": 3,
       "pick": "any",
       "scope": "body"
      },
      "guide_quote": {
       "text": "# 키워드 중 1개를 선택하여 본문에 3번 이상 넣어주세요.",
       "start": 217,
       "end": 250
      },
      "source": "rule"
     },
     {
      "id": "c4",
      "type": "disclosure",
      "label": "대가성 문구를 리뷰 상단에",
      "countable": true,
      "params": {
       "phrase": null,
       "position": "top"
      },
      "guide_quote": {
       "text": "공정위 대가성 문구는 반드시 리뷰 상단에 기재해주세요.",
       "start": 259,
       "end": 289
      },
      "source": "rule"
     },
     {
      "id": "c5",
      "type": "banned_terms",
      "label": "질병 이름 직접 언급 금지",
      "countable": false,
      "params": {
       "terms": [],
       "category": "질병 이름",
       "scope": "title_and_body"
      },
      "guide_quote": {
       "text": "질병 이름은 직접 언급하지 말아주세요.",
       "start": 293,
       "end": 314
      }
     },
     {
      "id": "c6",
      "type": "banned_terms",
      "label": "다이어트·감량 단어 금지",
      "countable": true,
      "params": {
       "terms": [
        "다이어트",
        "감량"
       ],
       "category": null,
       "scope": "title_and_body"
      },
      "guide_quote": {
       "text": "'다이어트', '감량' 단어는 사용하지 말아주세요.",
       "start": 318,
       "end": 346
      }
     },
     {
      "id": "c7",
      "type": "required_phrase",
      "label": "원료 설명 아래 안내 문구",
      "countable": true,
      "params": {
       "phrase": "*제품이 아닌 원료에 관한 설명입니다",
       "scope": "body",
       "after": "원료를 소개하는 문장"
      },
      "guide_quote": {
       "text": "원료를 소개하는 문장 아래에는 \"*제품이 아닌 원료에 관한 설명입니다\" 문구를 넣어주세요.",
       "start": 350,
       "end": 400
      }
     },
     {
      "id": "c8",
      "type": "hashtag",
      "label": "필수 해시태그 #새벽곡물 #아침선식",
      "countable": true,
      "params": {
       "tags": [
        "#새벽곡물",
        "#아침선식"
       ],
       "pick": "each"
      },
      "guide_quote": {
       "text": "필수 해시태그 #새벽곡물 #아침선식 을 모두 넣어주세요.",
       "start": 404,
       "end": 435
      }
     },
     {
      "id": "c9",
      "type": "photo_count",
      "label": "물이나 우유에 타는 모습 사진 1장 이상",
      "countable": false,
      "params": {
       "min": 1,
       "subject": "물이나 우유에 타는 모습"
      },
      "guide_quote": {
       "text": "물이나 우유에 타는 모습을 사진으로 1장 이상 넣어주세요.",
       "start": 439,
       "end": 471
      }
     },
     {
      "id": "c10",
      "type": "length",
      "label": "1,000자 이상",
      "countable": true,
      "params": {
       "min": 1000,
       "count_spaces": null
      },
      "guide_quote": {
       "text": "1,000자 이상",
       "start": 484,
       "end": 493
      },
      "source": "rule"
     },
     {
      "id": "c11",
      "type": "photo_count",
      "label": "사진 15장 이상",
      "countable": true,
      "params": {
       "min": 15
      },
      "guide_quote": {
       "text": "15장 이상",
       "start": 494,
       "end": 500
      },
      "source": "rule"
     },
     {
      "id": "c12",
      "type": "video_count",
      "label": "동영상 첨부",
      "countable": true,
      "params": {
       "min": 1
      },
      "guide_quote": {
       "text": "동영상 첨부",
       "start": 501,
       "end": 507
      },
      "source": "rule"
     },
     {
      "id": "c13",
      "type": "judgment",
      "label": "조건 하나를 확인하지 못했어요",
      "countable": false,
      "params": {
       "question": "가이드의 이 부분을 직접 봐 주세요",
       "unverified": true
      },
      "guide_quote": {
       "text": "미션이 지켜지지 않을 경우 제공된 제품 및 포인트의 환수 혹은 미지급 처리가 될 수 있습니다",
       "start": 508,
       "end": 559
      }
     },
     {
      "id": "c14",
      "type": "outside_draft",
      "label": "리뷰 등록기간",
      "countable": false,
      "params": {
       "what": "기간"
      },
      "guide_quote": {
       "text": "리뷰 등록기간 12.08 ~ 12.15",
       "start": 561,
       "end": 582
      },
      "source": "rule"
     }
    ]
   },
   "dropped": [
    {
     "code": "SCHEMA_INVALID",
     "reason": "기준 숫자가 없어요",
     "type": "length",
     "label": "글자 수",
     "quote": "미션이 지켜지지 않을 경우 제공된 제품 및 포인트의 환수 혹은 미지급 처리가 될 수 있습니다"
    }
   ],
   "request": {
    "version": "0.3",
    "input_mode": "html",
    "counts_source": "parsed",
    "title": "바쁜 아침에 챙겨 먹는 아침 선식, 새벽곡물 한 달 후기",
    "draft_text": "업체로부터 제품을 제공받아 솔직하게 작성한 글입니다.\n\n아침마다 십 분만 더 자고 싶어서 밥을 거르는 날이 많았어요. 그러다 보니 오전 내내 힘이 없어서, 간편 아침식사로 먹을 만한 걸 찾다가 새벽곡물 선식을 먹어 보게 됐어요. 한 달 가까이 먹어 본 이야기를 적어 볼게요.\n\n[사진]\n[사진]\n[사진]\n\n상자 안에는 한 포씩 나뉜 선식이 서른 개 들어 있어요. 포장이 길쭉한 스틱 모양이라 가방 앞주머니에 두세 개 넣어 다니기 좋아요. 회사 서랍에도 열 개쯤 넣어 뒀어요. 상자 옆면에는 먹는 법과 보관하는 법이 그림으로 그려져 있어서 처음 먹는 사람도 헷갈리지 않아요.\n\n[사진]\n[사진]\n[사진]\n\n먹는 법은 간단해요. 컵에 가루를 붓고 우유나 물을 이백 밀리리터쯤 넣은 다음 잘 흔들면 끝이에요. 저는 흔들 수 있는 통에 우유를 먼저 넣고 가루를 나중에 넣는데, 이렇게 하면 바닥에 뭉치는 게 없어요. 물에 타면 맛이 깔끔하고, 우유에 타면 더 고소하고 든든해요. 두유에 타 먹는 분도 많다고 해요.\n\n[사진]\n[사진]\n[사진]\n[동영상]\n\n맛은 미숫가루보다 덜 달고 고소한 쪽이에요. 검은콩과 현미 맛이 먼저 나고 끝에 귀리 향이 남아요. 단맛이 거의 없어서 저는 꿀을 반 숟가락 넣어 먹어요. 바나나를 반 개 썰어 넣고 갈아 마시면 아이들도 잘 먹는다고 해서 주말에 조카에게 만들어 줬더니 한 컵을 다 비웠어요.\n\n[사진]\n[사진]\n\n원료는 국내산 현미, 검은콩, 귀리, 보리 등 열두 가지 곡물이라고 해요. 곡물을 볶아서 갈았기 때문에 물에 타도 비린 맛이 없다고 설명서에 적혀 있었어요.\n\n한 포를 먹으면 점심때까지 배가 든든했어요. 예전에는 열한 시만 되면 과자를 찾았는데 요즘은 그런 일이 줄었어요. 다이어트 중인 동료도 아침 대신 먹기 좋겠다고 하나 얻어 갔어요. 저는 운동하러 가기 전에 한 포를 타 마시기도 하는데, 속이 부대끼지 않아서 좋았어요.\n\n[사진]\n[사진]\n\n출근 준비가 늦은 날에는 통에 가루만 넣어 가서 회사에서 우유를 부어 먹어요. 설거지할 것도 통 하나뿐이라 편해요. 여행 갈 때도 몇 포 챙겨 갔는데, 숙소에서 생수만 있으면 되니 아침을 사 먹으러 나가지 않아도 됐어요.\n\n보관은 서늘하고 햇빛이 들지 않는 곳에 두면 돼요. 한 포씩 따로 포장되어 있어서 눅눅해질 걱정이 없고, 유통기한도 넉넉한 편이에요. 간편 아침식사를 찾는 직장인이나 학생에게 잘 맞을 것 같아요. 저는 다 먹으면 한 상자 더 주문할 생각이에요.\n\n한 가지 아쉬운 점은 통에 타서 오래 두면 가루가 가라앉는다는 거예요. 마시기 전에 한 번 더 흔들어 주면 되니 큰 문제는 아니었어요. 그리고 찬 우유보다는 미지근한 우유에 훨씬 잘 풀려요. 겨울에는 우유를 전자레인지에 삼십 초쯤 데워서 타 먹으면 따뜻한 곡물 라떼 같아서 좋아요. 부모님께도 몇 포 드렸는데, 달지 않아서 입에 맞는다고 하셨어요. 씹을 필요가 없어서 이가 불편한 어르신께 드리기에도 괜찮을 것 같아요.\n\n[사진]\n[사진]\n\n#새벽곡물 #간편아침\n",
    "photo_count": 15,
    "video_count": 1,
    "has_map": false,
    "links": [],
    "hashtags": [
     "#새벽곡물",
     "#간편아침"
    ],
    "media": [
     {
      "kind": "photo",
      "start": 155
     },
     {
      "kind": "photo",
      "start": 160
     },
     {
      "kind": "photo",
      "start": 165
     },
     {
      "kind": "photo",
      "start": 322
     },
     {
      "kind": "photo",
      "start": 327
     },
     {
      "kind": "photo",
      "start": 332
     },
     {
      "kind": "photo",
      "start": 509
     },
     {
      "kind": "photo",
      "start": 514
     },
     {
      "kind": "photo",
      "start": 519
     },
     {
      "kind": "video",
      "start": 524
     },
     {
      "kind": "photo",
      "start": 686
     },
     {
      "kind": "photo",
      "start": 691
     },
     {
      "kind": "photo",
      "start": 937
     },
     {
      "kind": "photo",
      "start": 942
     },
     {
      "kind": "photo",
      "start": 1447
     },
     {
      "kind": "photo",
      "start": 1452
     }
    ]
   },
   "form": "reviewplace",
   "rules": {
    "doc": {
     "version": "0.3",
     "platform": "reviewplace",
     "campaign_type": null,
     "conditions": [
      {
       "id": "c1",
       "type": "title_keyword",
       "label": "제목에 키워드 1개 이상",
       "countable": true,
       "params": {
        "keywords": [
         "아침 선식",
         "새벽곡물",
         "간편 아침식사"
        ],
        "pick": "any"
       },
       "guide_quote": {
        "text": "# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.",
        "start": 153,
        "end": 186
       },
       "source": "rule"
      },
      {
       "id": "c2",
       "type": "hashtag",
       "label": "#태그에 키워드 1개 이상",
       "countable": true,
       "params": {
        "tags": [
         "#아침선식",
         "#새벽곡물",
         "#간편아침식사"
        ],
        "pick": "any"
       },
       "guide_quote": {
        "text": "# 키워드 중 1개를 선택하여 제목 및 #태그에 넣어주세요.",
        "start": 153,
        "end": 186
       },
       "source": "rule"
      },
      {
       "id": "c3",
       "type": "keyword_count",
       "label": "본문 키워드 1개를 3번 이상",
       "countable": true,
       "params": {
        "keywords": [
         "아침 선식",
         "새벽곡물",
         "간편 아침식사"
        ],
        "min": 3,
        "pick": "any",
        "scope": "body"
       },
       "guide_quote": {
        "text": "# 키워드 중 1개를 선택하여 본문에 3번 이상 넣어주세요.",
        "start": 217,
        "end": 250
       },
       "source": "rule"
      },
      {
       "id": "c4",
       "type": "disclosure",
       "label": "대가성 문구를 리뷰 상단에",
       "countable": true,
       "params": {
        "phrase": null,
        "position": "top"
       },
       "guide_quote": {
        "text": "공정위 대가성 문구는 반드시 리뷰 상단에 기재해주세요.",
        "start": 259,
        "end": 289
       },
       "source": "rule"
      },
      {
       "id": "c5",
       "type": "length",
       "label": "1,000자 이상",
       "countable": true,
       "params": {
        "min": 1000,
        "count_spaces": null
       },
       "guide_quote": {
        "text": "1,000자 이상",
        "start": 484,
        "end": 493
       },
       "source": "rule"
      },
      {
       "id": "c6",
       "type": "photo_count",
       "label": "사진 15장 이상",
       "countable": true,
       "params": {
        "min": 15
       },
       "guide_quote": {
        "text": "15장 이상",
        "start": 494,
        "end": 500
       },
       "source": "rule"
      },
      {
       "id": "c7",
       "type": "video_count",
       "label": "동영상 첨부",
       "countable": true,
       "params": {
        "min": 1
       },
       "guide_quote": {
        "text": "동영상 첨부",
        "start": 501,
        "end": 507
       },
       "source": "rule"
      },
      {
       "id": "c8",
       "type": "outside_draft",
       "label": "리뷰 등록기간",
       "countable": false,
       "params": {
        "what": "기간"
       },
       "guide_quote": {
        "text": "리뷰 등록기간 12.08 ~ 12.15",
        "start": 561,
        "end": 582
       },
       "source": "rule"
      }
     ]
    },
    "dropped": [],
    "result": {
     "version": "0.3",
     "summary": {
      "kept": 6,
      "missing": 1,
      "hold": 0
     },
     "results": [
      {
       "condition_id": "c1",
       "label": "제목에 키워드 1개 이상",
       "status": "kept",
       "expected": 1,
       "actual": 2,
       "unit": "개",
       "note": "제목에 \"아침 선식\", \"새벽곡물\" 있어요. 제목 앞쪽에 있어요(안내, 우리 기준)",
       "draft_spans": [
        {
         "start": 13,
         "end": 18,
         "field": "title"
        },
        {
         "start": 20,
         "end": 24,
         "field": "title"
        }
       ]
      },
      {
       "condition_id": "c2",
       "label": "#태그에 키워드 1개 이상",
       "status": "kept",
       "expected": 1,
       "actual": 1,
       "unit": "개",
       "note": "#새벽곡물 태그가 있어요",
       "draft_spans": [
        {
         "start": 1458,
         "end": 1463
        }
       ]
      },
      {
       "condition_id": "c3",
       "label": "본문 키워드 1개를 3번 이상",
       "status": "missing",
       "expected": 3,
       "actual": 2,
       "unit": "회",
       "note": "가장 많이 쓴 키워드는 \"새벽곡물\", \"간편 아침식사\" 각 2회예요. 1회 더 필요해요. 키워드별: \"아침 선식\" 0회, \"새벽곡물\" 2회(본문 글 1번 + 해시태그 1번), \"간편 아침식사\" 2회. 글 앞부분(본문 앞 300자)에 키워드가 나와요(안내, 우리 기준)",
       "draft_spans": [
        {
         "start": 87,
         "end": 94
        },
        {
         "start": 108,
         "end": 112
        },
        {
         "start": 1148,
         "end": 1155
        },
        {
         "start": 1459,
         "end": 1463
        }
       ]
      },
      {
       "condition_id": "c4",
       "label": "대가성 문구를 리뷰 상단에",
       "status": "kept",
       "expected": null,
       "actual": null,
       "unit": null,
       "note": "본문 첫 문단에 있어요 (대가성 표현 목록은 우리 기준)",
       "draft_spans": [
        {
         "start": 0,
         "end": 29
        }
       ]
      },
      {
       "condition_id": "c5",
       "label": "1,000자 이상",
       "status": "kept",
       "expected": 1000,
       "actual": 1362,
       "unit": "자",
       "note": "공백 포함 1362자(줄바꿈은 세지 않아요), 공백 제외 1005자. 공백 포함 기준으로 판정했어요 (가이드가 공백 기준을 정하지 않음). 본문 글 블록의 글자만 셌어요 ([사진] 줄, 링크 카드·동영상 제목 제외)",
       "draft_spans": []
      },
      {
       "condition_id": "c6",
       "label": "사진 15장 이상",
       "status": "kept",
       "expected": 15,
       "actual": 15,
       "unit": "장",
       "note": "사진 15장 (자동으로 센 사진 수 기준)",
       "draft_spans": []
      },
      {
       "condition_id": "c7",
       "label": "동영상 첨부",
       "status": "kept",
       "expected": 1,
       "actual": 1,
       "unit": "개",
       "note": "동영상 1개 (자동으로 센 동영상 수 기준)",
       "draft_spans": []
      },
      {
       "condition_id": "c8",
       "label": "리뷰 등록기간",
       "status": "hold",
       "expected": null,
       "actual": null,
       "unit": null,
       "note": "원고 밖 조건이라 여기서는 확인할 수 없어요. 이 조건은 직접 확인해 주세요",
       "draft_spans": []
      }
     ],
     "principles": [
      {
       "rule_id": "p1",
       "label": "대가성 표시가 제목 또는 첫 부분에 있음",
       "status": "kept",
       "basis": "공정위 추천·보증 심사지침(2024-12-01 시행), 네이버 D.I.A.+(2020-11-18)",
       "note": "본문 첫 문단에 있어요. \"첫 부분\" = 본문 첫 문단(우리 기준)",
       "draft_spans": [
        {
         "start": 0,
         "end": 29
        }
       ]
      },
      {
       "rule_id": "p2",
       "label": "모호한 대가성 표현 없음",
       "status": "kept",
       "basis": "공정위 추천·보증 심사지침(2024-12-01 시행)",
       "note": "\"수수료를 지급받을 수 있음\" 같은 조건부 표현이 없어요",
       "draft_spans": []
      },
      {
       "rule_id": "p3",
       "label": "키워드 과다 반복 없음",
       "status": "kept",
       "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"맥락과 관계 없는 키워드를 억지로 끼워 넣지 마세요\"",
       "note": "\"간편 아침식사\" 2회. 가이드 요구(3회)의 2배를 넘으면 알려요(우리 기준)",
       "draft_spans": []
      },
      {
       "rule_id": "p4",
       "label": "외부 링크 과다 없음",
       "status": "kept",
       "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"외부로 이동하는 URL을 과도하게\"",
       "note": "외부 링크 0개. 가이드 필수 링크 밖의 링크가 3개를 넘으면 알려요(우리 기준)",
       "draft_spans": []
      },
      {
       "rule_id": "p5",
       "label": "사진에 비해 글이 충분함",
       "status": "kept",
       "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"핵심 내용은 텍스트로도\"",
       "note": "사진 1장당 약 67자. 30자보다 적으면 알려요(우리 기준)",
       "draft_spans": []
      }
     ],
     "tips": [
      {
       "tip_id": "t1",
       "kind": "keyword_place",
       "condition_id": "c3",
       "label": "넣을 자리 추천: \"새벽곡물\"",
       "note": "\"새벽곡물\" 1회가 더 필요할 때 표시한 문단에 넣으면 더 자연스러워요. 지역 이름이나 \"다녀왔\", \"추천\", \"메뉴\" 같은 말이 있는 문단과 첫·끝 문단에서 골랐어요(우리 기준). 같은 키워드가 든 문장 바로 옆은 뺐어요. 문장은 직접 써 주세요. 아래 짧은 틀은 참고용이고 ○○은 직접 채워요",
       "templates": [
        "○○ 찾다가 알게 된 새벽곡물",
        "새벽곡물을 고른 이유는 ○○",
        "○○할 때 쓰기 좋은 새벽곡물"
       ],
       "draft_spans": [
        {
         "start": 1211,
         "end": 1445
        }
       ]
      }
     ]
    }
   },
   "result": {
    "version": "0.3",
    "summary": {
     "kept": 6,
     "missing": 4,
     "hold": 3
    },
    "results": [
     {
      "condition_id": "c1",
      "label": "제목에 키워드 1개 이상",
      "status": "kept",
      "expected": 1,
      "actual": 2,
      "unit": "개",
      "note": "제목에 \"아침 선식\", \"새벽곡물\" 있어요. 제목 앞쪽에 있어요(안내, 우리 기준)",
      "draft_spans": [
       {
        "start": 13,
        "end": 18,
        "field": "title"
       },
       {
        "start": 20,
        "end": 24,
        "field": "title"
       }
      ]
     },
     {
      "condition_id": "c2",
      "label": "#태그에 키워드 1개 이상",
      "status": "kept",
      "expected": 1,
      "actual": 1,
      "unit": "개",
      "note": "#새벽곡물 태그가 있어요",
      "draft_spans": [
       {
        "start": 1458,
        "end": 1463
       }
      ]
     },
     {
      "condition_id": "c3",
      "label": "본문 키워드 1개를 3번 이상",
      "status": "missing",
      "expected": 3,
      "actual": 2,
      "unit": "회",
      "note": "가장 많이 쓴 키워드는 \"새벽곡물\", \"간편 아침식사\" 각 2회예요. 1회 더 필요해요. 키워드별: \"아침 선식\" 0회, \"새벽곡물\" 2회(본문 글 1번 + 해시태그 1번), \"간편 아침식사\" 2회. 글 앞부분(본문 앞 300자)에 키워드가 나와요(안내, 우리 기준)",
      "draft_spans": [
       {
        "start": 87,
        "end": 94
       },
       {
        "start": 108,
        "end": 112
       },
       {
        "start": 1148,
        "end": 1155
       },
       {
        "start": 1459,
        "end": 1463
       }
      ]
     },
     {
      "condition_id": "c4",
      "label": "대가성 문구를 리뷰 상단에",
      "status": "kept",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "본문 첫 문단에 있어요 (대가성 표현 목록은 우리 기준)",
      "draft_spans": [
       {
        "start": 0,
        "end": 29
       }
      ]
     },
     {
      "condition_id": "c5",
      "label": "질병 이름 직접 언급 금지",
      "status": "hold",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "셀 수 없는 조건이라 판단 보류예요. 이 조건은 직접 확인해 주세요",
      "draft_spans": []
     },
     {
      "condition_id": "c6",
      "label": "다이어트·감량 단어 금지",
      "status": "missing",
      "expected": 0,
      "actual": 1,
      "unit": "곳",
      "note": "금지어가 있어요: \"다이어트\" 1곳",
      "draft_spans": [
       {
        "start": 850,
        "end": 854
       }
      ]
     },
     {
      "condition_id": "c7",
      "label": "원료 설명 아래 안내 문구",
      "status": "missing",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "필수 문구가 없어요: \"*제품이 아닌 원료에 관한 설명입니다\"",
      "draft_spans": []
     },
     {
      "condition_id": "c8",
      "label": "필수 해시태그 #새벽곡물 #아침선식",
      "status": "missing",
      "expected": 2,
      "actual": 1,
      "unit": "개",
      "note": "없는 태그: #아침선식. 본문과 입력한 태그에서 찾았어요",
      "draft_spans": [
       {
        "start": 1458,
        "end": 1463
       }
      ]
     },
     {
      "condition_id": "c9",
      "label": "물이나 우유에 타는 모습 사진 1장 이상",
      "status": "hold",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "사진에 무엇이 찍혔는지는 확인할 수 없어요. 이 조건은 직접 확인해 주세요",
      "draft_spans": []
     },
     {
      "condition_id": "c10",
      "label": "1,000자 이상",
      "status": "kept",
      "expected": 1000,
      "actual": 1362,
      "unit": "자",
      "note": "공백 포함 1362자(줄바꿈은 세지 않아요), 공백 제외 1005자. 공백 포함 기준으로 판정했어요 (가이드가 공백 기준을 정하지 않음). 본문 글 블록의 글자만 셌어요 ([사진] 줄, 링크 카드·동영상 제목 제외)",
      "draft_spans": []
     },
     {
      "condition_id": "c11",
      "label": "사진 15장 이상",
      "status": "kept",
      "expected": 15,
      "actual": 15,
      "unit": "장",
      "note": "사진 15장 (자동으로 센 사진 수 기준)",
      "draft_spans": []
     },
     {
      "condition_id": "c12",
      "label": "동영상 첨부",
      "status": "kept",
      "expected": 1,
      "actual": 1,
      "unit": "개",
      "note": "동영상 1개 (자동으로 센 동영상 수 기준)",
      "draft_spans": []
     },
     {
      "condition_id": "c13",
      "label": "조건 하나를 확인하지 못했어요",
      "status": "hold",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "가이드에서 조건을 제대로 읽지 못했어요. 가이드의 이 부분을 직접 보고 원고를 확인해 주세요",
      "draft_spans": []
     },
     {
      "condition_id": "c14",
      "label": "리뷰 등록기간",
      "status": "hold",
      "expected": null,
      "actual": null,
      "unit": null,
      "note": "원고 밖 조건이라 여기서는 확인할 수 없어요. 이 조건은 직접 확인해 주세요",
      "draft_spans": []
     }
    ],
    "principles": [
     {
      "rule_id": "p1",
      "label": "대가성 표시가 제목 또는 첫 부분에 있음",
      "status": "kept",
      "basis": "공정위 추천·보증 심사지침(2024-12-01 시행), 네이버 D.I.A.+(2020-11-18)",
      "note": "본문 첫 문단에 있어요. \"첫 부분\" = 본문 첫 문단(우리 기준)",
      "draft_spans": [
       {
        "start": 0,
        "end": 29
       }
      ]
     },
     {
      "rule_id": "p2",
      "label": "모호한 대가성 표현 없음",
      "status": "kept",
      "basis": "공정위 추천·보증 심사지침(2024-12-01 시행)",
      "note": "\"수수료를 지급받을 수 있음\" 같은 조건부 표현이 없어요",
      "draft_spans": []
     },
     {
      "rule_id": "p3",
      "label": "키워드 과다 반복 없음",
      "status": "kept",
      "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"맥락과 관계 없는 키워드를 억지로 끼워 넣지 마세요\"",
      "note": "\"간편 아침식사\" 2회. 가이드 요구(3회)의 2배를 넘으면 알려요(우리 기준)",
      "draft_spans": []
     },
     {
      "rule_id": "p4",
      "label": "외부 링크 과다 없음",
      "status": "kept",
      "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"외부로 이동하는 URL을 과도하게\"",
      "note": "외부 링크 0개. 가이드 필수 링크 밖의 링크가 3개를 넘으면 알려요(우리 기준)",
      "draft_spans": []
     },
     {
      "rule_id": "p5",
      "label": "사진에 비해 글이 충분함",
      "status": "kept",
      "basis": "네이버 콘텐츠 작성 가이드(2026-05-26) \"핵심 내용은 텍스트로도\"",
      "note": "사진 1장당 약 67자. 30자보다 적으면 알려요(우리 기준)",
      "draft_spans": []
     }
    ],
    "tips": [
     {
      "tip_id": "t1",
      "kind": "keyword_place",
      "condition_id": "c3",
      "label": "넣을 자리 추천: \"새벽곡물\"",
      "note": "\"새벽곡물\" 1회가 더 필요할 때 표시한 문단에 넣으면 더 자연스러워요. 지역 이름이나 \"다녀왔\", \"추천\", \"메뉴\" 같은 말이 있는 문단과 첫·끝 문단에서 골랐어요(우리 기준). 같은 키워드가 든 문장 바로 옆은 뺐어요. 문장은 직접 써 주세요. 아래 짧은 틀은 참고용이고 ○○은 직접 채워요",
      "templates": [
       "○○ 찾다가 알게 된 새벽곡물",
       "새벽곡물을 고른 이유는 ○○",
       "○○할 때 쓰기 좋은 새벽곡물"
      ],
      "draft_spans": [
       {
        "start": 1211,
        "end": 1445
       }
      ]
     }
    ]
   }
  }
 ]
};
