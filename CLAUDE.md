# 서울 초등학교 위치 지도 (ai_poi_map)

공공데이터포털 data.go.kr 의 전국초중등학교위치표준데이터(15021148)를 기반으로 서울 초등학교 위치를 Leaflet 지도에 마커로 표시하는 웹 앱.

## 데이터

- 원본 CSV: `data/한국교육시설안전원_초중등학교위치.csv`
- 출처: 공공데이터포털 (https://www.data.go.kr/data/15021148/standard.do)
- 제공기관: 한국교육시설안전원
- 컬럼: 학교ID, 학교명, 학교급구분, 설립일자, 설립형태, 본교분교구분, 운영상태, 소재지지번주소, 소재지도로명주소, 시도교육청코드, 시도교육청명, 교육지원청코드, 교육지원청명, 생성일자, 변경일자, 위도, 경도, 데이터기준일자
- 필터: 시도교육청명=서울특별시교육청, 학교급구분=초등학교 → 606개교
- 전처리 결과: `data/seoul_elementary.json`

## 실행 방법

```bash
cd /home/ec2-user/ai_poi_map
uv venv .venv && .venv/bin/pip install flask
.venv/bin/python app.py
```

서버 실행 후 `http://localhost:5000` 또는 서버 IP:5000 으로 접속.

## 앱 구성

- `app.py` — Flask + Leaflet 단일 페이지
- `data/` — 원본 CSV + 전처리 JSON
- 외부 의존성: Flask, Leaflet (CDN)

## 검색

좌측 패널에서 학교명 검색 가능. 마커 클릭 시 학교명·주소·좌표 팝업.

## 테스트

`test_app.py` — 데이터 파싱 및 Flask 앱 응답 검증.

## 레포 정보

- 원격: `https://github.com/sjjang61/ai_poi_map.git` (빈 레포)
- 현재 브랜치: master (로컬 커밋만 존재, 푸시 전)
