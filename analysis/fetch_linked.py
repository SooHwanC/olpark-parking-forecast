"""KCISA API를 페이지 단위로 받아 저장. 429·504·0건이면 쉬었다 재시도.

사용법: python fetch_linked.py [건수/쪽] [API_CPM_009|API_CPM_008]
  009 = 2025 연계 데이터(7,803건, KCISA_KEY) → data/raw/linked/
  008 = 2025 입출차 전체구역(2,411,225건, KCISA_KEY_INOUT) → data/raw/inout2025/
  한 쪽 최대 10,000건. 뒤쪽 페이지는 서버가 느려 504가 나므로, 실패하면 같은 구간을 더 작은 쪽으로 나눠 받는다.
"""
import json, sys, time, urllib.request, urllib.error
from pathlib import Path
W = Path(__file__).resolve().parents[1]
env = dict(l.strip().split('=', 1) for l in open(W / '.env', encoding='utf-8') if '=' in l)
rows = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
api = sys.argv[2] if len(sys.argv) > 2 else 'API_CPM_009'
key, out, total = (env['KCISA_KEY'], W / 'data/raw/linked', 7803) if api == 'API_CPM_009' else (env['KCISA_KEY_INOUT'], W / 'data/raw/inout2025', 2411225)
out.mkdir(parents=True, exist_ok=True)
SPLIT = [rows, 2000, 500]  # 504가 이어지면 이 크기로 나눠 받는다


def get(size, page, tries):
    """한 쪽을 받아 저장. 성공 True, 504만 계속되면 False."""
    f = out / f'p{size}_{page:04d}.json'
    if f.exists() and f.stat().st_size > 1000: return True
    url = f'https://api.kcisa.kr/openapi/{api}/request?serviceKey={key}&numOfRows={size}&pageNo={page}'
    n504 = 0
    while True:
        time.sleep(6)  # 호출 간격 제한(5초에 1번)
        try:
            body = urllib.request.urlopen(urllib.request.Request(url, headers={'Accept': 'application/json'}), timeout=300).read()
            n = len(json.loads(body)['response']['body']['items']['item'])
            if n == 0: raise ValueError('empty')
            f.write_bytes(body); print('ok', size, page, n, flush=True); return True
        except urllib.error.HTTPError as e:
            print('fail', size, page, e.code, flush=True)
            if e.code == 429: continue
            n504 += 1
            if n504 >= tries: return False
            time.sleep(30)
        except Exception as e:
            print('fail', size, page, repr(e)[:80], flush=True); time.sleep(30)


def chunk(start, end, level):
    """[start, end) 구간을 SPLIT[level] 크기 쪽으로 받는다."""
    size = SPLIT[level]
    for off in range(start, end, size):
        last = level == len(SPLIT) - 1
        if not get(size, off // size + 1, 10**6 if last else 1 if level == 0 else 3):  # 큰 쪽은 한 번만 시도
            chunk(off, min(off + size, end), level + 1)


for off in range(0, total, rows):
    chunk(off, min(off + rows, total), 0)
print('done', flush=True)
