"""기획서용 그림 → 작업/figs/*.png"""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
W = Path(__file__).resolve().parents[1]
FIG = W / 'figs'; FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family': 'Malgun Gothic', 'axes.unicode_minus': False, 'font.size': 11,
                     'axes.spines.top': False, 'axes.spines.right': False})

df = pd.read_csv(W / 'data/raw/입출차_202407.csv', encoding='cp949'); df.columns = ['day', 'tin', 'tout']
df['tin'], df['tout'] = pd.to_datetime(df.tin), pd.to_datetime(df.tout)
d = (df.tout - df.tin).dt.total_seconds() / 60
v = df[(d > 10) & (d <= 1440)]
idx = pd.date_range('2024-07-01', '2024-08-01', freq='h', inclusive='left')
occ = (v.tin.dt.floor('h').value_counts().reindex(idx, fill_value=0)
       - v.tout.dt.floor('h').value_counts().reindex(idx, fill_value=0)).cumsum()
H = range(8, 23)

# 1) 공연 주말 vs 다른 주말
fig, ax = plt.subplots(figsize=(7.5, 3.6))
others = [x for x in ['2024-07-06', '2024-07-07', '2024-07-13', '2024-07-14', '2024-07-27', '2024-07-28']]
oth = pd.concat([occ[x] for x in others]).groupby(lambda t: t.hour).mean()
ax.fill_between(H, [oth[h] for h in H], color='#9aa4b2', alpha=.35, label='다른 주말 6일 평균')
for day, c in [('2024-07-20', '#e5484d'), ('2024-07-21', '#b42318')]:
    s = occ[day]; ax.plot(H, [s[s.index.hour == h].iloc[0] for h in H], color=c, lw=2.2, label=f'{day[5:].replace("-", "/")} (공연 주말)')
ax.set_xticks(list(H)); ax.set_xlabel('시각'); ax.set_ylabel('주차 중인 차량(대)')
ax.set_title('공연 주말 오후에는 주차 차량이 평소 주말의 약 2배', loc='left', fontsize=12)
ax.legend(frameon=False, fontsize=9); fig.tight_layout(); fig.savefig(FIG / 'fig1_event_weekend.png', dpi=200)

# 2) 하루 입차 수는 비슷하다
daily = df.groupby(df.tin.dt.date).size()
peak = occ.groupby(occ.index.date).max()
fig, ax = plt.subplots(figsize=(7.5, 3.2))
x = pd.to_datetime(daily.index)
ax.bar(x, daily.values, color='#c9d3e3', label='하루 입차 수')
ax2 = ax.twinx(); ax2.plot(x, peak.values, color='#1f5fbf', marker='o', ms=3, lw=1.6, label='하루 최대 주차 중 차량')
ax.set_ylabel('입차(대)'); ax2.set_ylabel('최대 주차 중(대)'); ax2.spines['top'].set_visible(False)
ax.set_title('입차 수는 비슷해도, 행사일엔 "동시에 서 있는 차"가 급증', loc='left', fontsize=12)
ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%m/%d'))
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc='upper left'); fig.tight_layout(); fig.savefig(FIG / 'fig2_daily.png', dpi=200)

# 3) 월별 주차 계수
mf = json.loads((W / 'web/data/month_factor.json').read_text())
fig, ax = plt.subplots(figsize=(7.5, 2.8))
ax.bar([int(k) for k in mf], list(mf.values()), color=['#1f5fbf' if v >= 1.2 else '#9fb6dc' for v in mf.values()])
ax.axhline(1, color='#667085', lw=.8, ls='--'); ax.set_xticks(range(1, 13)); ax.set_xlabel('월'); ax.set_ylabel('평균 대비')
ax.set_title('월별 주차 수요 계수 (월별주차현황, 올림픽공원)', loc='left', fontsize=12)
fig.tight_layout(); fig.savefig(FIG / 'fig3_month.png', dpi=200)
print('ok', sorted(p.name for p in FIG.glob('*.png')))
