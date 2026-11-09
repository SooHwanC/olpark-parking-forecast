"""연계 API(API_CPM_009) 전체를 페이지 단위로 받아 data/raw/linked/에 저장. 504면 재시도."""
import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path
W = Path(__file__).resolve().parents[1]
key = dict(l.strip().split('=', 1) for l in open(W / '.env', encoding='utf-8') if '=' in l)['KCISA_KEY']
out = W / 'data/raw/linked'; out.mkdir(parents=True, exist_ok=True)
rows = int(sys.argv[1]) if len(sys.argv) > 1 else 100
total = 7803
pages = (total + rows - 1) // rows
for p in range(1, pages + 1):
    f = out / f'p{rows}_{p:04d}.json'
    if f.exists(): continue
    url = f'https://api.kcisa.kr/openapi/API_CPM_009/request?serviceKey={key}&numOfRows={rows}&pageNo={p}'
    for attempt in range(1, 145):  # 504가 길게 이어져 최대 약 12시간 재시도
        try:
            req = urllib.request.Request(url, headers={'Accept': 'application/json'})
            body = urllib.request.urlopen(req, timeout=60).read()
            f.write_bytes(body); print('ok', p, len(body), flush=True); break
        except Exception as e:
            print('fail', p, attempt, e, flush=True); time.sleep(300)
    else:
        sys.exit(f'gave up at page {p}')
print('done', flush=True)
