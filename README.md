# 서울 초·중학교 위치 지도

공공데이터포털 data.go.kr 의 전국초중등학교위치표준데이터(15021148)를 기반으로
서울 초등학교·중학교 위치를 Leaflet 지도에 마커로 표시하는 웹 앱.

## 빠른 실행

```bash
cd /home/ec2-user/ai_poi_map
.venv/bin/python app.py
```

서버 실행 후 `http://localhost:5000` 또는 서버 IP:5000 으로 접속.

## 데이터

- 원본: `data/한국교육시설안전원_초중등학교위치.csv`
- 출처: 공공데이터포털 (https://www.data.go.kr/data/15021148/standard.do)
- 제공기관: 한국교육시설안전원
- 필터:
  - 초등학교: 시도교육청명=서울특별시교육청, 학교급구분=초등학교 → 606개교
  - 중학교: 동일 조건, 학교급구분=중학교 → 388개교
- 전처리 결과: `data/seoul_elementary.json`, `data/seoul_middle.json`

## 기능

- 서울 지도 위에 초등학교(파랑)·중학교(주황) 마커 표시
- 좌측 패널: 학교급 필터(전체/초등학교/중학교) + 학교명 검색
- 마커 클릭/리스트 클릭 → 지도 확대 + 팝업 (학교명, 학교급, 주소, 좌표)
- 초기 화면: 전체 마커가 보이는 범위로 자동 줌

## 앱 구성

- `app.py` — Flask 앱 + Leaflet 단일 HTML 페이지
- `data/` — 원본 CSV + 전처리 JSON (초등·중학교 각각)
- `test_app.py` — 데이터 + 서버 응답 단위 테스트
- `test_e2e.py` — E2E 테스트 (학교급 필터·검색·마커 검증)

## 학교급 필터

좌측 패널의 버튼으로 전체/초등학교/중학교를 전환할 수 있다.
API 경로 `/api/schools?type=elementary`(또는 middle) 도 지원.

## 테스트 실행

```bash
.venv/bin/python test_app.py
.venv/bin/python test_e2e.py
```

## 레포 정보

- 원격: https://github.com/sjjang61/ai_poi_map.git
- 브랜치: `feature/middle_school` (PR 대상)
- 병합 대상: `master`
