# 올팍 주차예보

올림픽공원 시간대별 주차 혼잡 예보와 방문 안내. 한국체육산업개발(주) 개방 공공데이터로 만든 정적 웹 서비스입니다.
2026년도 한국체육산업개발 공공데이터 활용 경진대회 출품작 (팀 AnIma).

- `web/` — 서비스(HTML·JS·JSON). 서버 없이 동작
- `analysis/` — 데이터 수집·가공·예보 모델 스크립트
- `figs/` — 분석 그림

## 데이터 갱신

원자료(`data/raw/`)는 공공데이터포털에서 내려받는다. 연계 API는 `.env`에 `KCISA_KEY`가 필요하다.

```
uv run --no-project --with pandas python analysis/build_site_data.py
uv run --no-project --with pandas python analysis/build_model.py
```

## 사용 데이터

한국체육산업개발주식회사 올림픽공원 입출차 정보, 올림픽공원 2025 차량입출차·공연·날씨정보 등 연계 데이터, 월별주차현황, 영문 공연정보, 자주 묻는 질문정보, 올림픽공원 핫뉴스 정보 (공공데이터포털, 이용허락범위 제한 없음)
