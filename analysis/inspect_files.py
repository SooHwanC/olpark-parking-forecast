import sys, pandas as pd
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
R = Path(__file__).resolve().parents[1] / 'data/raw'
for n in ['faq','perf_en','poster','hotnews','sports_event','monthly_parking','congestion']:
    df = pd.read_csv(R/f'{n}.csv', encoding='cp949')
    print('==', n, df.shape, list(df.columns))
    print(df.head(2).to_string()[:700])
df = pd.read_csv(R/'perf_en.csv', encoding='cp949'); print('perf_en date range', df['공연일자'].min(), df['공연일자'].max()); print(df.sort_values('공연일자').tail(5)[['공연제목','공연일자']].to_string())
df = pd.read_csv(R/'faq.csv', encoding='cp949'); print(df['카테고리'].str.strip().value_counts().to_string()); print(df['제목'].tolist())
