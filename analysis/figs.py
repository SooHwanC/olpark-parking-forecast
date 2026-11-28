"""기획서용 그림 → 작업/figs/*.png (web/data/model.json, data/occ2025.csv 기준)"""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
W = Path(__file__).resolve().parent
sys.path.insert(0, str(W))
import build_model as B

W = W.parent
FIG = W / 'figs'; FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family': 'Malgun Gothic', 'axes.unicode_minus': False, 'font.size': 11,
                     'axes.spines.top': False, 'axes.spines.right': False})
M = json.loads((W / 'web/data/model.json').read_text(encoding='utf-8'))
H = list(range(8, 23))
n, thr = M['curve_days'], M['thresholds']
h = B.load()

# 1) 대형 공연일과 다른 날의 시간대별 주차 중 차량
fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.5), sharey=True)
for ax, dt, name in [(axes[0], 'weekday', '평일'), (axes[1], 'weekend', '주말')]:
    a, b = M['curves'][f'{dt}_0'], M['curves'][f'{dt}_1']
    ax.axhspan(thr['busy'], 2700, color='#fde2e1', lw=0)
    ax.fill_between(H, [a[x] for x in H], color='#9aa4b2', alpha=.35, label=f'다른 날 ({n[f"{dt}_0"]}일 평균)')
    ax.plot(H, [b[x] for x in H], color='#e5484d', lw=2.2, label=f'대형 공연일 ({n[f"{dt}_1"]}일 평균)')
    ax.set_xticks(H[::2]); ax.set_xlabel('시각'); ax.set_title(name, loc='left', fontsize=11); ax.set_ylim(0, 2700)
    ax.legend(frameon=False, fontsize=8.5, loc='lower center')
axes[0].set_ylabel('주차 중인 차량(대)')
axes[1].text(22, thr['busy'] + 40, '혼잡 구간', ha='right', va='bottom', fontsize=8, color='#b42318')
fig.suptitle('대형 공연(관람객 1만 명 이상)일은 저녁까지 주차 차량이 남는다 (2025 입출차)', x=0.01, ha='left', fontsize=12)
fig.tight_layout(); fig.savefig(FIG / 'fig1_event_weekend.png', dpi=200)

# 2) 관람객 규모별 저녁(18~21시) 주차 중 차량
e = h[h.hour.between(18, 21)]
d = e.groupby(e.ts.dt.date).agg(occ=('occ', 'mean'), aud=('audience', 'max'), we=('weekend', 'max'))
d['cls'] = pd.cut(d.aud, [-1, 0, 9999, 14999, 10**6], labels=['공연 없음', '1만 명 미만', '1만~1.5만 명', '1.5만 명 이상'])
g2 = d.groupby(['we', 'cls'], observed=False).occ.agg(['mean', 'size'])
fig, ax = plt.subplots(figsize=(7.5, 3.2))
for i, (we, name, c) in enumerate([(0, '평일', '#9fb6dc'), (1, '주말', '#1f5fbf')]):
    g = g2.loc[we]
    x = [k + (i - .5) * .38 for k in range(len(g))]
    ax.bar(x, g['mean'].fillna(0), width=.36, color=c, label=name)
    for xi, (m, s) in zip(x, g.values):
        if s: ax.text(xi, m, f'{int(s)}일', ha='center', va='bottom', fontsize=8)
ax.set_xticks(range(4)); ax.set_xticklabels(d.cls.cat.categories)
ax.set_ylabel('18~21시 평균(대)'); ax.legend(frameon=False, fontsize=9, loc='upper left')
ax.set_title('관람객이 많은 날일수록 저녁 주차 차량이 많다 (2025, 공연관람객수 기준)', loc='left', fontsize=12)
fig.tight_layout(); fig.savefig(FIG / 'fig2_daily.png', dpi=200)

# 3) 검증: 1~7월로 만든 예보 vs 처음 보는 12월 1~6일 실제
c, _ = B.fit(h[h.month <= 7])
t = h[(h.month == 12) & h.hour.between(8, 22)].sort_values('ts')
pred = [c[f'{a}_{b}'][x] for a, b, x in zip(t.dt, t.big, t.hour)]
fig, ax = plt.subplots(figsize=(8.6, 3.0))
xs = np.arange(len(t))
ax.plot(xs, t.occ, color='#1f2937', lw=1.6, label='실제(2025 입출차)')
ax.plot(xs, pred, color='#e5484d', lw=1.6, ls='--', label='예보(1~7월 데이터로 계산)')
days = t.ts.dt.date.values
ticks = [i for i in range(len(t)) if i == 0 or days[i] != days[i - 1]]
wd = '월화수목금토일'
ax.set_xticks(ticks); ax.set_xticklabels([f'12/{t.ts.iloc[i].day}({wd[t.ts.iloc[i].day_of_week]})' + ('\n대형 공연' if t.big.iloc[i] else '') for i in ticks], fontsize=9)
ax.set_ylabel('주차 중인 차량(대)'); ax.legend(frameon=False, fontsize=9, loc='upper left', ncol=2)
ax.set_title('처음 보는 12월 1~6일: 평일은 예보와 실제가 가깝고, 관람객 2만 명 넘는 날 저녁은 실제가 더 많다', loc='left', fontsize=11)
fig.tight_layout(); fig.savefig(FIG / 'fig3_validation.png', dpi=200)
print(g2.round(0).to_string())
print('ok', sorted(p.name for p in FIG.glob('*.png')))

# 0) 처리 구조도: 데이터 → 가공 → 모델 → 화면
fig, ax = plt.subplots(figsize=(8.6, 2.9)); ax.axis('off'); ax.set_xlim(0, 100); ax.set_ylim(0, 34)
boxes = [
    (1, 20, '입출차정보(전체구역)\n2025, 241만 건', '#dbe7f7'), (1, 3, '연계 데이터\n공연명·관람객 수 7,803건', '#dbe7f7'),
    (27, 20, '시간대별\n주차 중 차량 복원', '#eef2f7'), (27, 3, '날짜별 공연 규모\n(1만 명 이상 = 대형)', '#eef2f7'),
    (53, 11.5, '요일 × 대형 공연\n시간대 곡선\n(10~12월로 검증)', '#eef2f7'),
    (77, 20, '날짜별 혼잡 예보\n권장 도착 시각', '#fde2e1'), (77, 3, 'FAQ·핫뉴스 175건\n출처 달린 안내 답변', '#fde2e1')]
for x, y, t, c in boxes:
    ax.add_patch(matplotlib.patches.FancyBboxPatch((x, y), 21, 10, boxstyle='round,pad=0.4', fc=c, ec='#667085', lw=.8))
    ax.text(x + 10.5, y + 5, t, ha='center', va='center', fontsize=9)
arrow = dict(arrowstyle='->', color='#475467', lw=1.2)
for (x0, y0), (x1, y1) in [((22.6, 25), (26.4, 25)), ((22.6, 8), (26.4, 8)), ((48.6, 25), (52.4, 19)), ((48.6, 8), (52.4, 14)),
                           ((74.6, 19), (76.4, 24))]:
    ax.annotate('', (x1, y1), (x0, y0), arrowprops=arrow)
ax.text(87.5, 33.5, '정적 웹(서버·외부 AI 호출 없음)', ha='center', fontsize=8.5, color='#b42318')
fig.tight_layout(); fig.savefig(FIG / 'fig0_flow.png', dpi=200)
