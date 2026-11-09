"""data/raw → web/data/*.json (안내 검색 문서, 공연 일정, 혼잡 예보 모델)."""
import json, re, sys, html
from pathlib import Path
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
W = Path(__file__).resolve().parents[1]
RAW, OUT = W / 'data/raw', W / 'web/data'
OUT.mkdir(parents=True, exist_ok=True)
FAQ_URL = 'https://www.ksponco.or.kr/board.es?mid=a10309000000&bid=0067'


def read(name):
    return pd.read_csv(RAW / f'{name}.csv', encoding='cp949', dtype=str).fillna('')


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(str(s))).strip()


def build_docs():
    docs = []
    for r in read('faq').itertuples():
        docs.append({'type': 'FAQ', 'cat': clean(r.카테고리), 'title': clean(r.제목), 'body': clean(r.내용),
                     'date': r.등록일, 'url': FAQ_URL, 'src': '한국체육산업개발_자주 묻는 질문정보'})
    for r in read('hotnews').itertuples():
        docs.append({'type': '공지', 'cat': '올림픽공원 핫뉴스', 'title': clean(r.제목),
                     'body': f'게시 기간 {r.시작일} ~ {r.종료일}', 'date': r.등록일, 'url': r._6,
                     'src': '한국체육산업개발_올림픽공원 핫뉴스 정보'})
    (OUT / 'docs.json').write_text(json.dumps(docs, ensure_ascii=False), encoding='utf-8')
    return len(docs)


def build_events():
    ev = []
    for r in read('perf_en').itertuples():
        ev.append({'date': r.공연일자, 'title': clean(r.공연제목), 'url': r.상세주소, 'src': '한국체육산업개발_영문 공연정보'})
    extra = W / 'data/events_extra.json'  # 공연정보 API 수집분(있으면)
    if extra.exists():
        ev += json.loads(extra.read_text(encoding='utf-8'))
    ev.sort(key=lambda e: e['date'])
    (OUT / 'events.json').write_text(json.dumps(ev, ensure_ascii=False), encoding='utf-8')
    return len(ev)


def build_month_factor():
    m = read('monthly_parking')
    m = m[m.주차장소 == '올림픽공원'].copy()
    m['월'] = m.월.str.replace('월', '').astype(int)
    m['주차대수'] = m.주차대수.astype(int)
    by = m.groupby('월').주차대수.mean()
    return {int(k): round(float(v / by.mean()), 3) for k, v in by.items()}


if __name__ == '__main__':
    print('docs', build_docs())
    print('events', build_events())
    mf = build_month_factor()
    (OUT / 'month_factor.json').write_text(json.dumps(mf), encoding='utf-8')
    print('month_factor', mf)
