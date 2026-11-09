import sys, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
df=pd.read_csv(sys.argv[1], encoding='cp949'); df.columns=['day','tin','tout']
df['tin']=pd.to_datetime(df.tin); df['tout']=pd.to_datetime(df.tout)
d=(df.tout-df.tin).dt.total_seconds()/60
print('<=10min share',round((d<=10).mean(),3))
v=df[(d>10)&(d<=1440)]
idx=pd.date_range('2024-07-01','2024-08-01',freq='h',inclusive='left')
occ=(v.tin.dt.floor('h').value_counts().reindex(idx,fill_value=0)-v.tout.dt.floor('h').value_counts().reindex(idx,fill_value=0)).cumsum()
for day in ['2024-07-20','2024-07-21','2024-07-27','2024-07-14']:
    s=occ[day]; print(day, {h:int(x) for h,x in zip(s.index.hour,s.values) if h>=8 and h<=22})
