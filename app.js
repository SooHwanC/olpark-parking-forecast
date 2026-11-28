'use strict';
const HOURS = Array.from({ length: 15 }, (_, i) => i + 8); // 8~22시
const $ = (id) => document.getElementById(id);
let M, EVENTS, DOCS, IDX;

const ymd = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 10);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

async function load() {
  const get = (f) => fetch('data/' + f).then((r) => r.json());
  [M, EVENTS, DOCS] = await Promise.all([get('model.json'), get('events.json'), get('docs.json')]);
  IDX = buildIndex(DOCS);
  const hp = new URLSearchParams(location.hash.slice(1)); // #date=YYYY-MM-DD&q=질문 으로 바로 열기
  $('date').value = /^\d{4}-\d{2}-\d{2}$/.test(hp.get('date') || '') ? hp.get('date') : ymd(new Date());
  $('date').addEventListener('change', () => { autoEvent(); render(); });
  $('event').addEventListener('change', render);
  $('askForm').addEventListener('submit', (e) => { e.preventDefault(); ask($('q').value); });
  ['주차 요금은 얼마예요?', '공연 끝나고 분실물은?', '반려견 데리고 가도 되나요?', '대중교통으로 가는 법', '토요일 공연날 주차 붐비나요?']
    .forEach((t) => { const b = document.createElement('button'); b.textContent = t; b.onclick = () => { $('q').value = t; ask(t); }; $('chips').append(b); });
  $('sources').innerHTML = [
    '한국체육산업개발 올림픽공원 입출차정보(전체구역) (2025, API)',
    '한국체육산업개발 올림픽공원 2025 차량입출차·공연·날씨정보 등 연계 데이터 (공연명·관람객 수)',
    '한국체육산업개발 영문 공연정보',
    '한국체육산업개발 자주 묻는 질문정보 · 올림픽공원 핫뉴스 정보',
  ].map((s) => `<li>${esc(s)}</li>`).join('');
  const v = M.validation.model;
  $('modelNote').textContent = `예보 근거: ${M.source} (${M.days}일). 1~7월로 만든 예보를 처음 보는 10~12월 ${v.days}일에 맞춰 본 주차 중 차량 오차 중앙값 ${(v.median_ape * 100).toFixed(1)}%, 혼잡 등급 일치율 ${(v.level_acc * 100).toFixed(0)}%(한 단계 이내 ${(v.level_within1 * 100).toFixed(0)}%). 혼잡은 2025 관측값(8~21시) 상위 20%, 보통은 상위 50%.`;
  autoEvent();
  render();
  if (hp.get('q')) { $('q').value = hp.get('q'); ask(hp.get('q')); }
}

function eventsOn(date) { return EVENTS.filter((e) => e.date === date); }

function autoEvent() {
  const ev = eventsOn($('date').value);
  // 관람객 수가 있으면(2025 연계 데이터) 1만 명 이상일 때만, 없으면(공연정보) 등록된 공연을 대형으로 본다
  $('event').checked = ev.some((e) => (e.audience == null ? true : e.audience >= M.big_audience));
  const aud = ev.find((e) => e.audience != null);
  $('eventList').innerHTML = ev.length
    ? '이날 공연·행사: ' + ev.slice(0, 4).map((e) => (e.url ? `<a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.title)}</a>` : esc(e.title))).join(', ')
      + (aud ? ` (관람객 ${aud.audience.toLocaleString()}명, 연계 데이터)` : '')
    : '공개 데이터에 등록된 이날 공연·행사가 없어요. 알고 있는 대형 공연이 있으면 위에서 체크하세요.';
}

function predict(date, event) {
  const d = new Date(date + 'T00:00:00');
  const dt = d.getDay() === 0 || d.getDay() === 6 ? 'weekend' : 'weekday';
  const curve = M.curves[`${dt}_${event ? 1 : 0}`];
  return HOURS.map((h) => curve[h] || 0);
}

const level = (v) => (v >= M.thresholds.busy ? 2 : v >= M.thresholds.normal ? 1 : 0);

function render() {
  const vals = predict($('date').value, $('event').checked);
  const max = Math.max(...vals, M.thresholds.busy * 1.1);
  $('chart').innerHTML = vals.map((v, i) =>
    `<div class="bar lv${level(v)}" style="height:${Math.max(2, (v / max) * 100)}%" title="${HOURS[i]}시: ${['원활', '보통', '혼잡'][level(v)]}"><span>${HOURS[i]}</span></div>`).join('');
  $('summary').innerHTML = summarize(vals);
}

function summarize(vals) {
  const lv = vals.map(level);
  const peak = vals.indexOf(Math.max(...vals));
  const runsOf = (k) => { const rs = []; HOURS.forEach((h, i) => { if (lv[i] !== k) return; const r = rs[rs.length - 1]; if (r && r[1] === h - 1) r[1] = h; else rs.push([h, h]); }); return rs; };
  const fmt = (rs) => rs.map(([a, b]) => (a === b ? `${a}시` : `${a}~${b}시`)).join(', ');
  const busy = runsOf(2), calm = runsOf(0);
  const d = new Date($('date').value + 'T00:00:00');
  const dt = d.getDay() === 0 || d.getDay() === 6 ? 'weekend' : 'weekday';
  const eve = (k) => [18, 19, 20].reduce((s, h) => s + M.curves[`${dt}_${k}`][h], 0);
  const big = $('event').checked
    ? ` 대형 공연일 18~20시 주차 차량은 대형 공연이 없는 ${dt === 'weekend' ? '주말' : '평일'}의 약 ${(eve(1) / eve(0)).toFixed(1)}배예요(2025 평균). 저녁 공연이라면 일찍 도착하거나 지하철을 이용하세요.` : '';
  if (!busy.length) {
    const q = calm.length ? `${fmt(calm)}는 대체로 원활해요.` : '';
    return `이날은 크게 붐비지 않을 것으로 보여요. 가장 차가 많은 시간은 <b>${HOURS[peak]}시</b> 무렵이에요. ${q}${big}`;
  }
  const arrive = busy[0][0] - 1; // FAQ: 공연 임박 시 1시간 여유 권장
  const morning = dt === 'weekday' && !$('event').checked && busy[0][0] <= 11
    ? ` 평일 오전 붐빔은 대형 공연이 없는 날에도 나타나요(2025년 대형 공연 없는 평일 10시 평균 ${Math.round(M.curves.weekday_0[10]).toLocaleString()}대).` : '';
  return `<b>${fmt(busy)} 혼잡</b>, 가장 붐비는 때는 <b>${HOURS[peak]}시</b>예요. 차를 가져오신다면 <b>${arrive}시 이전 도착</b>을 권해요. 가능하면 지하철(5·9호선 올림픽공원역, 8호선 몽촌토성역)을 이용하세요.${morning}${big}`;
}

/* ---------- 안내 검색: 글자 2-gram BM25, 브라우저 안에서만 동작 ---------- */
const grams = (s) => { const t = s.toLowerCase().replace(/[^0-9a-z가-힣]/g, ''); const g = []; for (let i = 0; i < t.length - 1; i++) g.push(t.slice(i, i + 2)); return g; };

function buildIndex(docs) {
  const df = new Map(), tfs = [];
  let total = 0;
  docs.forEach((d) => {
    const tf = new Map();
    grams(d.title + d.title + d.body).forEach((g) => tf.set(g, (tf.get(g) || 0) + 1)); // 제목 가중치 2배
    tfs.push(tf); total += [...tf.values()].reduce((a, b) => a + b, 0);
    tf.forEach((_, g) => df.set(g, (df.get(g) || 0) + 1));
  });
  return { df, tfs, avg: total / docs.length, n: docs.length };
}

function search(q, k = 3) {
  const qs = [...new Set(grams(q))], { df, tfs, avg, n } = IDX;
  const scores = tfs.map((tf, i) => {
    const len = [...tf.values()].reduce((a, b) => a + b, 0);
    let s = 0;
    qs.forEach((g) => { const f = tf.get(g); if (!f) return; const idf = Math.log(1 + (n - df.get(g) + 0.5) / (df.get(g) + 0.5)); s += idf * (f * 2.2) / (f + 1.2 * (0.25 + 0.75 * len / avg)); });
    return [s, i];
  }).filter(([s]) => s > 0).sort((a, b) => b[0] - a[0]);
  if (!scores.length) return [];
  const top = scores[0][0];
  return scores.filter(([s]) => s >= top * 0.45).slice(0, k).map(([s, i]) => DOCS[i]);
}

function parseDate(q) {
  const now = new Date(), d = new Date(now);
  if (/모레/.test(q)) d.setDate(d.getDate() + 2);
  else if (/내일/.test(q)) d.setDate(d.getDate() + 1);
  else if (/오늘/.test(q)) {}
  else {
    const m = q.match(/(\d{1,2})\s*월\s*(\d{1,2})\s*일/);
    if (m) { d.setMonth(+m[1] - 1, +m[2]); if (d < now) d.setFullYear(d.getFullYear() + 1); }
    else {
      const w = '일월화수목금토'.split('').findIndex((c) => new RegExp(c + '요일').test(q));
      if (w < 0) return null;
      d.setDate(d.getDate() + ((w - d.getDay() + 7) % 7 || 7));
    }
  }
  return ymd(d);
}

function ask(q) {
  q = q.trim(); if (!q) return;
  let html = '';
  if (/(주차|차|혼잡|붐비|복잡|자리)/.test(q) && /(언제|몇\s*시|붐비|혼잡|복잡|자리|요일|오늘|내일|모레|\d+\s*월)/.test(q)) {
    const date = parseDate(q);
    if (date) { $('date').value = date; autoEvent(); if (/공연|콘서트|행사/.test(q)) $('event').checked = true; render(); }
    html += `<div class="ans"><h3><span class="tag">예보</span>${date ? esc(date) + ' ' : ''}시간대별 주차 혼잡 예보</h3><p>${summarize(predict($('date').value, $('event').checked))}</p><div class="meta"><a href="#forecast">예보 그래프 보기</a> · 근거: ${esc(M.source)}</div></div>`;
  }
  const hits = search(q);
  html += hits.map((d) => `<div class="ans"><h3><span class="tag">${esc(d.type)}</span>${esc(d.title)}</h3><p>${esc(d.body)}</p><div class="meta">출처: ${esc(d.src)}${d.date ? ' · ' + esc(d.date) : ''} · <a href="${esc(d.url)}" target="_blank" rel="noopener">원문 보기</a></div></div>`).join('');
  $('answers').innerHTML = html || '<p class="note">관련 안내를 찾지 못했어요. 올림픽공원 안내센터(02-2180-3564)로 문의해 주세요.</p>';
}

load();
