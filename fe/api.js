// 서버와 만나는 곳은 이 파일 하나예요. 화면(app.js)은 Api.extract, Api.check, Api.judge, Api.feedback만 불러요.
//
// - 서버에서 열었을 때(http, https): 우리 서버의 /api/ 주소만 불러요. 다른 곳으로는 아무것도 보내지 않아요.
//   가이드와 원고는 점검하려고 우리 서버로 보내고, 서버는 저장하지 않아요.
// - 파일로 열었을 때(index.html 더블클릭): 예시 모드예요. mock-data.js(엔진이 미리 계산한 예시)에서 골라 돌려주고,
//   아무 요청도 보내지 않아요.
'use strict';

const Api = (() => {
  const squash = s => s.replace(/\r\n?/g, '\n').replace(/[ \t]+$/gm, '').trim();
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const copy = v => JSON.parse(JSON.stringify(v));
  const live = location.protocol !== 'file:';

  // 우리 서버의 /api/ 아래로만 보내요. 주소는 여기 한 곳에서만 만들어요.
  // wait: 기다리는 시간(밀리초). 넘으면 멈추고 사람이 알아들을 말로 알려요
  async function post(path, payload, wait = 90000) {
    let res;
    try {
      res = await fetch('/api/' + path, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
        credentials: 'omit', referrerPolicy: 'no-referrer', cache: 'no-store', signal: AbortSignal.timeout(wait),
      });
    } catch (why) {
      if (why && why.name === 'TimeoutError') throw new Error('시간이 너무 오래 걸려서 멈췄어요. 다시 시도해 주세요.');
      throw new Error('서버에 닿지 못했어요. 인터넷 연결을 확인하고 다시 해 주세요.');
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || '서버에서 문제가 생겼어요. 잠시 뒤에 다시 해 주세요.');
    return data;
  }

  return {
    mock: !live,
    scenarios: MOCK.scenarios.map(s => ({ id: s.id, name: s.name, guide: s.guide, request: copy(s.request) })),

    // 가이드 원문 → { doc: 조건 목록, dropped: 버린 목록, form: 가이드 형식(레뷰 등, 모르면 null) }. 예시 모드에서는 예시 가이드만 알아봐요(모르면 null).
    // ai: false면 AI 없이 코드가 고정 칸에서 읽은 조건만 바로 받아요 (나눠 보여 주기 1단계). form: "바꾸기"로 고른 형식
    async extract(guide, { ai = true, form = null } = {}) {
      if (live) {
        const got = await post('extract', { guide, ai, ...(form ? { form } : {}) }, ai ? 90000 : 20000);
        return { doc: got.conditions, dropped: got.dropped, form: got.form || null, scenario: null };
      }
      const hit = MOCK.scenarios.find(s => squash(s.guide) === squash(guide));
      if (!hit) return null;
      if (ai) await new Promise(r => setTimeout(r, 60));      // AI가 읽는 데 걸리는 시간을 흉내 내요 (나눠 보여 주기를 볼 수 있게)
      const part = ai ? hit : hit.rules;
      return { doc: copy(part.doc), dropped: copy(part.dropped), form: form || hit.form || null, scenario: hit.id };
    },

    // 조건 목록 + 점검 요청 → { result, request, doc, exact }.
    // request와 doc은 이 결과를 계산한 것이에요. exact가 false면 "미리 계산한 예시 결과"라서
    // 고친 조건·숫자·붙여 넣은 원고가 반영되지 않은 거예요 (예시 모드에서만).
    async check(doc, request, scenarioId) {
      if (live) {
        const result = await post('check', { conditions: doc, request });
        return { result, request: copy(request), doc: copy(doc), exact: true };
      }
      const hit = MOCK.scenarios.find(s => s.id === scenarioId) || MOCK.scenarios[0];
      const part = same(doc, hit.rules.doc) ? hit.rules : hit;        // 1단계(코드가 읽은 조건만)인지 다 읽은 뒤인지
      return {
        result: copy(part.result),
        request: copy(hit.request),
        doc: copy(part.doc),
        exact: same(doc, part.doc) && same(request, hit.request),
      };
    },

    // 정성 조건(셀 수 없는 조건)만 AI로 판단한 점검 결과. 블로거가 켰을 때만 불러요 (원고 글이 AI 서비스로 가요).
    // 실패하면 Error("정성 판단은 잠시 뒤 다시 시도해 주세요." 등). 예시 모드에서는 AI가 없어서 null이에요.
    async judge(doc, request) {
      if (!live) return null;
      return post('judge', { conditions: doc, request });
    },

    // 걸린 시간(숫자만): 첫 결과까지, 전체 결과까지. 서버 기록에 숫자로만 남아요. 실패해도 화면에는 알리지 않아요
    async timing({ first_ms, full_ms, ai }) {
      if (!live) return;
      try { await post('timing', { first_ms, full_ms, ai }, 5000); } catch { /* 숫자 기록이라 실패해도 그대로 둬요 */ }
    },

    // "판정이 틀렸어요": 동의한 경우에만 부르고, 조건 이름과 판정만 보내요. 원고 글과 note는 보내지 않아요.
    async feedback({ kind, id, label, status }) {
      const payload = { consent: true, kind, id, label, status };
      if (live) return post('feedback', payload);
      console.log('[판정이 틀렸어요]', payload);     // 예시 모드에서는 저장하지 않고 콘솔에만
      return { saved: false };
    },
  };
})();
