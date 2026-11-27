"""2025 API 원자료 → 모델 입력.

data/raw/inout2025/p*_*.json (API_CPM_008) → data/inout2025.csv.gz (id, tin, tout)
data/raw/linked/p1000_*.json (API_CPM_009)  → data/events2025_hourly.csv (ts, event_name, audience)
→ data/occ2025.csv: 날짜·시각별 재차 대수(받은 기록 기준), 그날 기록 수, 공연·관람객, 같은 달 기준값 대비 비율(rel)

2025 입출차는 달마다 일부 기록만 들어 있다(8·9·12월은 65,534건, 매달 말일 없음). 그래서 절대 대수 대신
같은 달 '공연 없는 평일 8~21시 평균'으로 나눈 비율을 쓴다.
"""
import json, re, sys
from pathlib import Path
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
W = Path(__file__).resolve().parents[1]
D = W / 'data'


def items(pattern):
    for f in sorted((D / 'raw').glob(pattern)):
        yield from json.loads(f.read_text(encoding='utf-8'))['response']['body']['items']['item']


def inout():
    rows = {}
    for it in items('inout2025/p*_*.json'):
        kv = dict(re.findall(r'(입차시간|출차시간):([^,]*)', it['DESCRIPTION'] or ''))
        rows[it['LOCAL_ID']] = (it['TITLE'][:8], kv.get('입차시간', '').strip(), kv.get('출차시간', '').strip())
    df = pd.DataFrame(rows.values(), columns=['day', 'tin', 'tout'])
    df['tin'] = pd.to_datetime(df.tin, errors='coerce')
    df['tout'] = pd.to_datetime(df.tout, errors='coerce')
    df.to_csv(D / 'inout2025.csv.gz', index=False)
    return df


def events():
    rows = {}
    for it in items('linked/p1000_*.json'):
        m = re.match(r'공연명:(.*?)\s*,공연관람객수:(\d*)', it['TITLE'] or '', re.S)
        rows[it['LOCAL_ID']] = (it['ISSUED_DATE'], m.group(1).strip() if m else '', int(m.group(2) or 0) if m else 0)
    ev = pd.DataFrame(rows.values(), columns=['ts', 'event_name', 'audience'])
    ev['ts'] = pd.to_datetime(ev.ts)
    ev = ev.sort_values('ts')
    ev.to_csv(D / 'events2025_hourly.csv', index=False)
    return ev


def occupancy(df, ev):
    d = (df.tout - df.tin).dt.total_seconds() / 60
    v = df[(d > 10) & (d <= 1440)]  # 10분 이하 통과·승하차, 24시간 초과 장기주차 제외 (2024-07과 같은 기준)
    print('records', len(df), 'used', len(v), f'({len(v) / len(df):.1%})', 'no tout', int(df.tout.isna().sum()))
    out = []
    for mon, g in v.groupby(v.tin.dt.to_period('M')):
        idx = pd.date_range(mon.start_time, mon.end_time.floor('h'), freq='h')
        occ = (g.tin.dt.floor('h').value_counts().reindex(idx, fill_value=0)
               - g.tout.dt.floor('h').value_counts().reindex(idx, fill_value=0)).cumsum()  # 달마다 0에서 시작
        h = pd.DataFrame({'ts': idx, 'occ': occ.values})
        n = g.tin.dt.date.value_counts()
        h['n_day'] = h.ts.dt.date.map(n).fillna(0).astype(int)
        out.append(h)
    h = pd.concat(out, ignore_index=True)
    day_aud = ev.groupby(ev.ts.dt.date).audience.max()
    h['audience'] = h.ts.dt.date.map(day_aud).fillna(0).astype(int)
    h['event'] = (h.audience > 0).astype(int)
    h['weekend'] = (h.ts.dt.day_of_week >= 5).astype(int)
    h['month'] = h.ts.dt.month
    med = h.month.map(h[h.n_day > 0].groupby('month').n_day.median())
    h['ok'] = ((h.n_day > 0) & (h.n_day >= 0.6 * med)).astype(int)  # 기록이 없거나 잘린 날(그달 중앙값의 60% 미만)은 제외
    base = h[(h.ok == 1) & (h.event == 0) & (h.weekend == 0) & h.ts.dt.hour.between(8, 21)].groupby('month').occ.mean()
    h['rel'] = (h.occ / h.month.map(base)).round(4)
    h.to_csv(D / 'occ2025.csv', index=False)
    s = h[h.ts.dt.hour == 0].groupby('month').agg(days=('ok', 'size'), ok_days=('ok', 'sum'), ev_days=('event', 'sum'),
                                                   rec_per_day=('n_day', 'median'))
    s['base'] = base.round(0)
    print(s.to_string())
    return h


if __name__ == '__main__':
    occupancy(inout(), events())
