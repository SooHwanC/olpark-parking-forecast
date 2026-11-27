"""받은 입출차 쪽들로 월별 완전성 확인. LOCAL_ID는 월 단위로 연속(월 안에서는 날짜가 섞여 있음)."""
import json, glob, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
m = collections.defaultdict(list); days = collections.defaultdict(set)
for f in glob.glob('data/raw/inout2025/p*_*.json'):
    for i in json.load(open(f, encoding='utf-8'))['response']['body']['items']['item']:
        m[i['TITLE'][:6]].append(int(i['LOCAL_ID'].split('-')[1])); days[i['TITLE'][:6]].add(i['TITLE'][:8])
tot = 0
for k in sorted(m):
    ids = set(m[k]); tot += len(ids)
    print(k, 'rows', len(ids), 'id', min(ids), max(ids), 'fill', round(len(ids) / (max(ids) - min(ids) + 1), 3), 'days', len(days[k]))
print('total unique', tot)
