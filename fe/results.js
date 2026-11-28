// 결과를 보여 주는 부분. 점검 결과(contracts/check-result 0.3)와 원고를 "교정지"로 그려요.
// 원고 글 위에 빨간 표시를 붙이고, 옆 여백에 짧은 메모를 달아요.
//
// - 상태(S)와 서버(Api)를 몰라요. 받은 결과와 원고만 그려요. 그래서 나중에 크롬 확장의 옆 패널로 옮길 때
//   이 파일을 그대로 쓸 수 있어요.
// - 글은 글자(textContent)로만 넣어요. 서식(HTML)으로 넣지 않고, 사진을 불러오지 않아요.
'use strict';

// 화면에 넣을 것만 남겨요: 겹친 목록은 펴고, 없는 값(null, false)은 빼요. 이걸 거치지 않으면 "false"가 글자로 찍혀요.
const tidy = (...items) => items.flat(Infinity).filter(k => k != null && k !== false);
const h = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === 'text') e.textContent = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? '' : v);
  }
  e.append(...tidy(kids));
  return e;
};
const button = (label, cls, onclick, attrs = {}) => h('button', { type: 'button', class: cls, text: label, onclick, ...attrs });

// 화면 글자: 개발 용어(missing, hold) 대신 쉬운 말
const STATUS = { missing: '고칠 곳', hold: '직접 확인', kept: '지킴' };
const ORDER = { missing: 0, hold: 1, kept: 2 };
const MARK_LINES = new Set(Object.values(MARK));
const keyOf = (kind, r) => `${kind}:${kind === 'condition' ? r.condition_id : r.rule_id}`;
const AI_NOTE = 'AI 판단(참고용)';

// 여백 메모에 쓰는 짧은 한 줄. 자세한 설명(note)은 "자세히"에서 보여 줘요.
function shortLine(r) {
  const unit = r.unit || '';
  if (r.status === 'missing' && Number.isInteger(r.expected) && Number.isInteger(r.actual) && unit) {
    if (r.actual < r.expected) return `${r.expected - r.actual}${unit} 더 필요해요`;
    if (r.expected === 0 && r.actual > 0) return `${r.actual}${unit} 있어요`;
  }
  const first = String(r.note || '').split(/(?<=[요다])\.\s/)[0];
  return first.length > 70 ? first.slice(0, 68) + '…' : first;
}

// 글을 코드 포인트로 잘라, 표시(mark)와 메모 번호(sup)와 사진 자리 줄을 글자 노드로 만들어요.
// layers: [{ spans, cls, n }] — n이 있으면 그 표시의 첫 자리에 메모 번호를 붙여요.
function paint(text, field, layers) {
  const chars = Array.from(text);
  const ranges = [];
  if (field === 'body') {
    let pos = 0;
    for (const line of text.split('\n')) {
      const n = Array.from(line).length;
      if (MARK_LINES.has(line.trim())) ranges.push({ start: pos, end: pos + n, cls: 'media' });
      pos += n + 1;
    }
  }
  for (const layer of layers) {
    const mine = layer.spans.filter(s => (s.field || 'body') === field);
    mine.forEach((s, i) => ranges.push({ start: Math.max(0, s.start), end: Math.min(chars.length, s.end), cls: layer.cls,
      n: i === 0 ? layer.n : null }));
  }
  const cuts = [...new Set([0, chars.length, ...ranges.flatMap(r => [r.start, r.end])])].sort((a, b) => a - b);
  const out = [];
  for (let i = 0; i < cuts.length - 1; i++) {
    const a = cuts[i], b = cuts[i + 1], piece = chars.slice(a, b).join('');
    for (const r of ranges) {
      if (r.n && r.start === a) out.push(h('sup', { class: 'n', 'data-n': String(r.n), 'aria-hidden': 'true', text: String(r.n) }));
    }
    const cover = ranges.filter(r => r.start <= a && b <= r.end);
    if (!cover.length) out.push(piece);
    else if (cover.some(r => r.cls === 'media')) out.push(h('span', { class: 'media', text: piece }));
    else out.push(h('mark', { class: [...new Set(cover.map(r => r.cls))].join(' '), text: piece }));
  }
  return out;
}

// 교정지 한 장: 제목 줄과 본문. notes는 고칠 곳 메모(번호와 위치), picked는 고른 항목(그 자리를 더 진하게).
// tips는 펼쳐 둔 "도움이 될 팁"이에요. 번호 없이 차분한 색(m-tip)으로만 표시해요.
function proofSheet(request, notes, picked, tips = []) {
  const layers = notes.map(({ r, n }) => ({ spans: r.draft_spans, cls: 'm-miss', n }));
  tips.forEach((t, i) => layers.push({ spans: t.draft_spans, cls: `m-tip tip-${i}` }));
  if (picked) layers.push({ spans: picked.draft_spans, cls: `on m-${picked.status}` });
  return h('article', { class: 'sheet', id: 'manuscript', 'aria-label': '원고' },
    h('h2', { class: 'ms-title', id: 'ms-title' },
      request.title ? paint(request.title, 'title', layers) : h('span', { class: 'unknown', text: '제목을 몰라요' })),
    h('div', { class: 'manuscript', id: 'ms-body' }, paint(request.draft_text, 'body', layers)));
}

const numbersOf = r => r.expected != null
  ? `원고 ${r.actual == null ? '모름' : r.actual + (r.unit || '')} / 기준 ${r.expected}${r.unit || ''}` : null;

// 메모 한 장 (여백) 또는 목록 한 줄. n: 메모 번호, onPick: 눌렀을 때, foot: "판정이 틀렸어요" 같은 것, changed: 지난 점검과 달라짐
// edit: 조건 고치기 단추와 칸(app.js가 만들어 줘요), edited: 블로거가 고친 조건
function noteCard(kind, r, { n = null, onPick, foot = null, changed = false, cls = 'note-card', edit = null, edited = false } = {}) {
  const ai = String(r.note || '').startsWith(AI_NOTE);
  return h('li', { class: `${cls} ${r.status}`, 'data-key': keyOf(kind, r), 'data-n': n ? String(n) : null },
    h('button', { type: 'button', class: 'pick', 'aria-pressed': 'false', onclick: onPick },
      n ? h('span', { class: 'num', text: String(n) })
        : cls === 'note-card' ? h('span', { class: 'num whole', text: '전체', title: '원고 전체에 대한 메모예요' }) : null,
      h('span', { class: 'card-text' },
        h('strong', { class: 'label', text: r.label }),
        h('span', { class: 'line', text: shortLine(r) }),
        r.unit === '자' ? h('span', { class: 'count-note', text: '줄바꿈은 세지 않아요' }) : null,     // 글자 수 기준 (2026-11-28)
        tidy(ai && h('span', { class: 'tag', text: 'AI 참고' }),
          kind === 'principle' && r.rule_id !== 'p7' && h('span', { class: 'tag', text: '네이버·공정위' }),
          r.rule_id === 'p7' && h('span', { class: 'tag', text: '참고' }),
          edited && h('span', { class: 'tag edited', text: '고쳤어요' }),
          changed && h('span', { class: 'tag changed', text: '지난 점검과 달라졌어요' })))),
    edit ? h('div', { class: 'card-tools' }, edit) : null,
    h('details', { class: 'more' },
      h('summary', { text: '자세히' }),
      numbersOf(r) && h('p', { class: 'numbers', text: numbersOf(r) }),
      h('p', { class: 'note', text: r.note }),
      r.draft_spans.length ? h('p', { class: 'where', text: `원고에서 ${r.draft_spans.length}곳` }) : null,
      r.basis ? h('p', { class: 'basis', text: `근거: ${r.basis}` }) : null,
      foot));
}

// 도움이 될 팁 (점검 결과의 tips). 판정이 아니라서 고칠 곳 메모·개수와 따로, 결과 아래에 접어 둬요.
// 펼쳤을 때만 원고에 표시해요 (onToggle이 원고를 다시 그려요). 글은 서버가 준 그대로 보여 줘요.
// 틀은 글자로만 보여 주고 복사 단추를 두지 않아요. 문장은 블로거가 직접 써요.
function tipsBlock(tips, open, onToggle) {
  if (!tips.length) return null;
  const calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const show = i => {
    const first = document.querySelector(`#manuscript mark.tip-${i}`);
    if (first) first.scrollIntoView({ block: 'center', behavior: calm ? 'auto' : 'smooth' });
  };
  return h('details', { class: 'fold tips', id: 'tips', open, ontoggle: e => onToggle(e.target.open) },
    h('summary', { text: `도움이 될 팁 ${tips.length}개` }),
    h('p', { class: 'hint', text: '꼭 고쳐야 하는 것은 아니에요. 위의 점검 결과와 고칠 곳 개수에는 넣지 않았어요. 펼쳐 둔 동안 원고에 연한 색으로 자리를 표시해요.' }),
    h('ul', { class: 'tip-list' }, tips.map((t, i) => h('li', { class: 'tip', 'data-tip': t.tip_id },
      h('span', { class: 'tag tip-tag', text: '팁' }),
      h('strong', { class: 'label', text: t.label }),
      h('p', { class: 'note', text: t.note }),
      (t.templates || []).length ? h('ul', { class: 'tip-frames', 'aria-label': '짧은 틀' }, t.templates.map(f => h('li', { text: f }))) : null,
      t.draft_spans.length ? button(`원고에서 ${t.draft_spans.length}곳 보기`, 'link', () => show(i), { 'data-tip-show': t.tip_id }) : null))));
}

// 고른 항목을 표시하고 원고에서 그 자리로 움직여요.
function markPicked(key) {
  for (const li of document.querySelectorAll('[data-key]')) {
    const on = li.dataset.key === key;
    li.classList.toggle('on', on);
    const pick = li.querySelector('.pick');
    if (pick) pick.setAttribute('aria-pressed', String(on));
  }
  const first = document.querySelector('#manuscript mark.on');
  if (!first) return;
  const calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const box = first.getBoundingClientRect();
  if (box.top < 80 || box.bottom > window.innerHeight - 40) first.scrollIntoView({ block: 'center', behavior: calm ? 'auto' : 'smooth' });
}

// 넓은 화면: 여백 메모를 원고의 번호 높이에 맞춰 세워요. 겹치면 아래로 밀어요. 좁은 화면에서는 원고 아래에 차례로 놓여요.
function alignNotes() {
  const margin = document.getElementById('notes');
  if (!margin) return;
  const cards = [...margin.querySelectorAll('.note-card')];
  const wide = getComputedStyle(margin).position === 'relative';
  if (!wide) {
    for (const c of cards) c.style.top = '';
    margin.style.minHeight = '';
    return;
  }
  const base = margin.getBoundingClientRect().top;
  let floor = 0;
  for (const c of cards) {
    const sup = document.querySelector(`#manuscript sup.n[data-n="${c.dataset.n}"]`);
    const want = sup && c.dataset.n ? sup.getBoundingClientRect().top - base - 6 : floor;
    const top = Math.max(want, floor);
    c.style.top = `${Math.round(top)}px`;
    floor = top + c.offsetHeight + 14;
  }
  margin.style.minHeight = `${Math.round(floor)}px`;
}

// 7-2: 키워드를 누르면 네이버 화면을 새 탭으로 열어요. 링크만 만들어요.
// 우리 서버도 이 화면도 네이버에 요청하지 않고, 결과를 가져오거나 저장·가공하지 않아요.
const NAVER_SEARCH = 'https://search.naver.com/search.naver?query=';
const NAVER_DATALAB = 'https://datalab.naver.com/keyword/trendSearch.naver';     // 키워드를 미리 채운 주소는 확인 못 해서 첫 화면만
const KEYWORD_LINKS_MAX = 10;

function keywordLinks(doc) {
  const words = [...new Set(doc.conditions
    .filter(c => c.countable && (c.type === 'title_keyword' || c.type === 'keyword_count'))
    .flatMap(c => (c.params && c.params.keywords) || [])
    .map(k => String(k).trim()).filter(Boolean))].slice(0, KEYWORD_LINKS_MAX);
  if (!words.length) return null;
  const out = (href, text, attrs = {}) => h('a', { href, target: '_blank', rel: 'noopener noreferrer', class: 'out', text, ...attrs });
  return h('details', { class: 'fold', id: 'keyword-links' },
    h('summary', { text: '네이버에서 키워드 직접 보기' }),
    h('p', { class: 'hint', text: '키워드를 누르면 네이버 검색 결과가 새 탭으로 열려요. 이 서비스는 검색 결과를 가져오거나 저장하지 않아요.' }),
    h('ul', { class: 'kw-list' }, words.map(k => h('li', {}, out(NAVER_SEARCH + encodeURIComponent(k), k, { 'data-keyword': k })))),
    h('p', { class: 'hint' }, '검색량 흐름은 ', out(NAVER_DATALAB, '네이버 데이터랩 검색어트렌드', { id: 'datalab-link' }),
      '에서 키워드를 직접 넣어 보세요. 상댓값이라 실제 검색 횟수와 달라요.'));
}
