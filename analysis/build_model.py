"""시간대별 주차 수요 예보 모델 → web/data/model.json.

입력: data/occ2025.csv (parse_2025.py: 2025 입출차 재차 대수 + 연계 데이터 관람객 수)
쓰는 날: 기록이 온전한 1~7·10월, 11·12월 1~6일(8·9월은 65,534건 표본, 11·12월은 7일 이후 없음).
        명절 연휴 등 기록이 그달 중앙값의 60% 미만인 날은 뺀다.
모델 = (요일유형 × 대형 공연[관람객 1만 명 이상]) 시간대 평균 곡선.
  월별주차현황 계수를 곱하면 검증 오차가 커져(2025 재차 대수는 월별 변동이 작다) 쓰지 않는다.
등급 = 학습 기간 8~21시 관측값 분위: 상위 20% 이상 혼잡, 상위 50% 이상 보통.
검증 = 1~7월로 만들고 처음 보는 10~12월을 예측(시간순 분할).
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
W = Path(__file__).resolve().parents[1]
OUT = W / 'web/data'
BIG = 10000
SRC = '2025 올림픽공원 입출차정보(전체구역) 재차 대수 + 2025 연계 데이터 공연관람객수'


def load():
    h = pd.read_csv(W / 'data/occ2025.csv', parse_dates=['ts'])
    h['day'] = h.ts.dt.day
    last = h[h.n_day > 0].groupby('month').day.max()
    cut = h.month.isin([11, 12]) & (h.day >= h.month.map(last))  # 건수 상한에서 잘린 마지막 날
    h = h[(h.ok == 1) & ~h.month.isin([8, 9]) & ~cut].copy()
    h['hour'] = h.ts.dt.hour
    h['dt'] = np.where(h.weekend == 1, 'weekend', 'weekday')
    h['big'] = (h.audience >= BIG).astype(int)
    return h


def fit(h, use_event=True):
    key = h.dt + '_' + (h.big if use_event else h.big * 0).astype(str)
    curves = {k: [round(float(x), 1) for x in g.groupby('hour').occ.mean().reindex(range(24)).fillna(0)]
              for k, g in h.groupby(key)}
    for dt in ['weekday', 'weekend']:
        curves.setdefault(f'{dt}_1', curves[f'{dt}_0'])
    day = h[(h.hour >= 8) & (h.hour <= 21)].occ
    thr = {'busy': round(float(day.quantile(0.8)), 1), 'normal': round(float(day.quantile(0.5)), 1)}
    return curves, thr


def score(h, curves, thr):
    d = h[(h.hour >= 8) & (h.hour <= 21)]
    act = d.occ.values
    pred = np.array([curves[f'{a}_{b}'][t] for a, b, t in zip(d.dt, d.big, d.hour)])
    lv = lambda x: np.where(x >= thr['busy'], 2, np.where(x >= thr['normal'], 1, 0))
    ape = np.abs(pred - act) / np.clip(act, 1, None)
    big, busy, eve = d.big.values == 1, lv(act) == 2, d.hour.between(17, 21).values
    return {'days': int(d.ts.dt.date.nunique()), 'big_days': int(d[big].ts.dt.date.nunique()), 'hours': int(len(d)),
            'level_acc': round(float((lv(act) == lv(pred)).mean()), 3),
            'level_within1': round(float((np.abs(lv(act) - lv(pred)) <= 1).mean()), 3),
            'median_ape': round(float(np.median(ape)), 3),
            'evening_median_ape': round(float(np.median(ape[eve])), 3),
            'big_evening_median_ape': round(float(np.median(ape[big & eve])), 3) if big.any() else None,
            'busy_hours': int(busy.sum()), 'busy_recall': round(float((lv(pred)[busy] == 2).mean()), 3) if busy.any() else None,
            'busy_precision': round(float((lv(act)[lv(pred) == 2] == 2).mean()), 3) if (lv(pred) == 2).any() else None}


if __name__ == '__main__':
    h = load()
    tr, te = h[h.month <= 7], h[h.month >= 10]
    val = {}
    for name, ue in [('model', True), ('no_event', False)]:
        c, t = fit(tr, ue)
        val[name] = score(te, c, t)
    curves, thr = fit(h)
    n = h[h.hour == 0].groupby(['dt', 'big']).size()
    model = {'source': SRC, 'days': int(h.ts.dt.date.nunique()), 'months': sorted(int(m) for m in h.month.unique()),
             'big_audience': BIG, 'curve_days': {f'{a}_{b}': int(v) for (a, b), v in n.items()},
             'unit': 'cars', 'curves': curves, 'thresholds': thr,
             'validation': {'train': '2025-01~07', 'test': '2025-10~12', **val}}
    (OUT / 'model.json').write_text(json.dumps(model, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in model.items() if k != 'curves'}, ensure_ascii=False, indent=1))
    for k, c in sorted(curves.items()):
        print(k, [int(x) for x in c[8:23]])
