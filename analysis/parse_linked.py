"""data/raw/linked/*.json → data/linked_hourly.csv (ts, value, visitors, temp, rain, holiday, event, event_name, audience)

DESCRIPTION 예: "주차대수:19,방문객:57, 기온:-3.4, 풍향:3.6, 강수량:, 습도:27,휴일:,공연명:,공연관람객수:0"
"""
import json, re, sys
from pathlib import Path
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
W = Path(__file__).resolve().parents[1]


def items(o):
    if isinstance(o, dict):
        if 'DESCRIPTION' in o or 'description' in o:
            yield o
        for v in o.values():
            yield from items(v)
    elif isinstance(o, list):
        for v in o:
            yield from items(v)


def num(s):
    try:
        return float(s.replace(',', ''))
    except (ValueError, AttributeError):
        return None


rows = {}
for f in sorted((W / 'data/raw/linked').glob('*.json')):
    for it in items(json.loads(f.read_text(encoding='utf-8'))):
        it = {k.upper(): v for k, v in it.items()}
        kv = dict(re.findall(r'\s*([^:,]+):([^,]*)', it['DESCRIPTION']))
        kv = {k.strip(): v.strip() for k, v in kv.items()}
        rows[it.get('LOCAL_ID') or it['ISSUED_DATE']] = {
            'ts': it['ISSUED_DATE'], 'value': num(kv.get('주차대수')), 'visitors': num(kv.get('방문객')),
            'temp': num(kv.get('기온')), 'rain_mm': num(kv.get('강수량')) or 0.0, 'humidity': num(kv.get('습도')),
            'holiday': kv.get('휴일', ''), 'event_name': kv.get('공연명', ''), 'audience': num(kv.get('공연관람객수')) or 0.0}
df = pd.DataFrame(rows.values())
df['ts'] = pd.to_datetime(df.ts)
df = df.sort_values('ts')
df['event'] = ((df.event_name != '') | (df.audience > 0)).astype(int)
df['rain'] = (df.rain_mm > 0).astype(int)
df.to_csv(W / 'data/linked_hourly.csv', index=False, encoding='utf-8')
print(len(df), df.ts.min(), df.ts.max())
print(df.describe().T[['mean', 'min', 'max']].to_string())
print('event hours', df.event.sum(), 'rain hours', df.rain.sum())
