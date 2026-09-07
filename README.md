# 서울 초·중·고 학교 위치 지도

공공데이터포털 data.go.kr 의 전국초중등학교위치표준데이터(15021148)를 기반으로
서울 초등학교·중학교·고등학교 위치를 Leaflet 지도에 표시하는 웹 앱.

## 빠른 실행

```bash
cd /home/ec2-user/ai_poi_map
.venv/bin/python app.py
```

서버 실행 후 `http://localhost:5000` 또는 `http://223.130.153.155:5000` 으로 접속.

## 데이터

- 원본: `data/한국교육시설안전원_초중등학교위치.csv`
- 출처: 공공데이터포털 (https://www.data.go.kr/data/15021148/standard.do)
- 제공기관: 한국교육시설안전원
- 서울 학교 수:
  - 초등학교: 606개교
  - 중학교: 388개교
  - 고등학교: 319개교
  - 합계: 1,313개교
- 전처리 결과:
  - `data/seoul_elementary.json`
  - `data/seoul_middle.json`
  - `data/seoul_high.json`

## 기능

- 서울 지도 위에 초등학교(파랑)·중학교(주황)·고등학교(보라) 마커 표시
- 좌측 패널:
  - 학교급 필터: 전체 / 초등학교 / 중학교 / 고등학교
  - 구(자치구) 필터: 전체 구 / 특정 구
  - 학교명, 구명, 주소 검색
- 마커 클릭/리스트 클릭 → 지도 확대 + 팝업 (학교명, 학교급, 구, 주소, 좌표)
- 초기 화면: 전체 마커가 보이는 범위로 자동 줌

## 앱 구성

- `app.py` — Flask 앱 + Leaflet 단일 HTML 페이지
- `data/` — 원본 CSV + 전처리 JSON
- `scripts/preprocess_schools.py` — 서울 초·중·고 JSON 재생성
- `test_app.py` — API/데이터 단위 테스트
- `test_e2e.py` — 학교급 필터, 구 필터, 검색, 렌더링 E2E 테스트

## 필터 API

- `/api/schools?type=elementary`
- `/api/schools?type=middle`
- `/api/schools?type=high`
- `/api/schools?district=강남구`
- `/api/schools?type=high&district=노원구`

## 테스트

```bash
.venv/bin/python test_app.py
.venv/bin/python test_e2e.py
```

E2E 테스트는 서버가 localhost:5000 에서 실행 중이어야 한다.
