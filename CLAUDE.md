# 서울 초등학교 위치 지도 (ai_poi_map)

공공데이터포털 data.go.kr 의 전국초중등학교위치표준데이터(15021148)를 기반으로 서울 초등학교 위치를 Leaflet 지도에 마커로 표시하는 웹 앱.

## 데이터

- 원본 CSV: `data/한국교육시설안전원_초중등학교위치.csv`
- 출처: 공공데이터포털 (https://www.data.go.kr/data/15021148/standard.do)
- 제공기관: 한국교육시설안전원
- 파일 내 컬럼: 학교ID, 학교명, 학교급구분, 설립일자, 설립형태, 본교분교구분, 운영상태, 소재지지번주소, 소재지도로명주소, 시도교육청코드, 시도교육청명, 교육지원청코드, 교육지원청명, 생성일자, 변경일자, 위도, 경도, 데이터기준일자
- 필터링: `시도교육청명 == "서울특별시교육청"` AND `학교급구분 == "초등학교"` → 606개교
- 전처리 결과: `data/seoul_elementary.json` (좌표 포함 606개)

## 실행 방법

```bash
cd /home/ec2-user/ai_poi_map
uv venv .venv && .venv/bin/pip install flask
.venv/bin/python app.py
```

실행 후 브라우저에서 `http://localhost:5000` 또는 서버 IP:5000 으로 접속.

## 앱 구성

- `app.py` — Flask 서버 + Leaflet 지도 (단일 파일)
- `data/` — 원본 CSV + 전처리 JSON
- 외부 의존성: Flask, Leaflet (CDN)

## 검색 기능

좌측 패널에서 학교명 검색 가능. 마커 클릭 시 팝업で 학교명·주소·좌표 표시.

## 테스트

`test_app.py` — 데이터 파싱 및 JSON 로드 검증.
