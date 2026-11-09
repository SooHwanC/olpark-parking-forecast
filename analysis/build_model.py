"""시간대별 주차 수요 예보 모델 → web/data/model.json.

입력이 있으면 2025 연계 데이터(data/linked_hourly.csv), 없으면 2024-07 입출차로 만든다.
모델 = (요일유형 × 공연 여부)별 시간대 평균 곡선 × 월 계수. 등급은 관측 최대 수준(99.5% 분위) 대비 비율.
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
W = Path(__file__).resolve().parents[1]
OUT = W / 'web/data'
EVENT_DAYS_2024_07 = {'2024-07-20', '2024-07-21'}  # 백현 KSPO DOME 공연 주말(영문 공연정보 7/20 등록)로 가정


def daytype(ts):
    return 'weekend' if ts.day_of_week >= 5 else 'weekday'


def hourly_from_inout():
    df = pd.read_csv(W / 'data/raw/입출차_202407.csv', encoding='cp949')
    df.columns = ['day', 'tin', 'tout']
    df['tin'], df['tout'] = pd.to_datetime(df.tin), pd.to_datetime(df.tout)
    d = (df.tout - df.tin).dt.total_seconds() / 60
    v = df[(d > 10) & (d <= 1440)]  # 10분 이하는 승하차·통과로 보고 제외
    idx = pd.date_range('2024-07-01', '2024-08-01', freq='h', inclusive='left')
    occ = (v.tin.dt.floor('h').value_counts().reindex(idx, fill_value=0)
           - v.tout.dt.floor('h').value_counts().reindex(idx, fill_value=0)).cumsum()
    h = pd.DataFrame({'ts': idx, 'value': occ.values})
    h['event'] = h.ts.dt.strftime('%Y-%m-%d').isin(EVENT_DAYS_2024_07).astype(int)
    h['rain'] = 0
    return h, '2024-07 입출차(동2·남2·북2문) 재차 대수', 'cars'


def hourly_from_linked():
    h = pd.read_csv(W / 'data/linked_hourly.csv', parse_dates=['ts'])
    return h, '2025 차량입출차·공연·날씨 연계 데이터 주차대수', 'cars'


def fit(h):
    h = h.copy()
    h['hour'] = h.ts.dt.hour
    h['dt'] = h.ts.map(daytype)
    month_f = json.loads((OUT / 'month_factor.json').read_text())
    h['mf'] = h.ts.dt.month.map(lambda m: month_f[str(m)])
    h['base'] = h.value / h.mf  # 월 효과 제거한 값으로 곡선 학습
    curves = {}
    for (dt, ev), g in h.groupby(['dt', 'event']):
        c = g.groupby('hour').base.mean().reindex(range(24))
        curves[f'{dt}_{ev}'] = [None if np.isnan(x) else round(float(x), 1) for x in c]
    # 공연 곡선이 없는 요일유형은 다른 요일유형의 시간대별 공연 배율을 빌려 채운다
    hr_ratio = [1.0] * 24
    for dt in ['weekend', 'weekday']:
        a, b = curves.get(f'{dt}_1'), curves.get(f'{dt}_0')
        if a and b:
            hr_ratio = [max(1.0, x / y) if x and y else 1.0 for x, y in zip(a, b)]
            break
    ev_ratio = float(np.median(hr_ratio[14:21]))
    for dt in ['weekday', 'weekend']:
        if f'{dt}_1' not in curves:
            curves[f'{dt}_1'] = [None if x is None else round(x * r, 1) for x, r in zip(curves[f'{dt}_0'], hr_ratio)]
    rain_f = 1.0
    if h.rain.sum() > 0:
        day = h[(h.hour >= 10) & (h.hour <= 20)]
        rain_f = round(float(day[day.rain == 1].base.mean() / day[day.rain == 0].base.mean()), 3)
    day = h[(h.hour >= 8) & (h.hour <= 21)].value
    ref = float(day.quantile(0.995))  # 관측 최대 수준; 혼잡=70%, 보통=45% 이상
    thr = {'busy': round(0.7 * ref, 1), 'normal': round(0.45 * ref, 1), 'ref': round(ref, 1)}
    return curves, ev_ratio, rain_f, thr


def backtest(h, curves, thr):
    """학습 곡선으로 각 시간을 다시 예측해 등급 일치율·오차를 본다(같은 데이터, 참고용)."""
    month_f = json.loads((OUT / 'month_factor.json').read_text())
    pred = [curves[f'{daytype(t)}_{e}'][t.hour] * month_f[str(t.month)] for t, e in zip(h.ts, h.event)]
    h = h.assign(pred=pred)
    d = h[(h.ts.dt.hour >= 8) & (h.ts.dt.hour <= 21)]
    lv = lambda x: 2 if x >= thr['busy'] else 1 if x >= thr['normal'] else 0
    acc = float((d.value.map(lv) == d.pred.map(lv)).mean())
    mape = float((abs(d.pred - d.value) / d.value.clip(lower=1)).median())
    return round(acc, 3), round(mape, 3)


if __name__ == '__main__':
    src = hourly_from_linked if (W / 'data/linked_hourly.csv').exists() else hourly_from_inout
    h, name, unit = src()
    curves, ev_ratio, rain_f, thr = fit(h)
    acc, mape = backtest(h, curves, thr)
    model = {'source': name, 'rows': len(h), 'unit': unit, 'curves': curves, 'event_ratio': round(ev_ratio, 3),
             'rain_factor': rain_f, 'thresholds': thr, 'backtest': {'level_acc': acc, 'median_ape': mape}}
    (OUT / 'model.json').write_text(json.dumps(model, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in model.items() if k != 'curves'}, ensure_ascii=False))
    for k, c in curves.items():
        print(k, [None if x is None else int(x) for x in c[8:22]])
