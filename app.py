#!/usr/bin/env python3
"""
서울 초등학교 위치 지도 (ai_poi_map)
Flask + Leaflet 기반 단일 페이지 앱.
실행: python app.py  (또는 .venv/bin/python app.py)
접속: http://localhost:5000  또는  http://223.130.153.155:5000
"""

import json
from pathlib import Path
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

DATA_PATH = Path(__file__).parent / "data" / "seoul_elementary.json"


def load_schools():
    if not DATA_PATH.exists():
        return []
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


HTML = r"""
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>서울 초등학교 위치 지도</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  html,body { height:100%; font-family:'맑은 고딕','Apple SD Gothic Neo',sans-serif; background:#f5f5f5; }
  #map { height:100vh; width:100%; }
  #panel {
    position:absolute; top:12px; left:12px; z-index:1000;
    background:#fff; border-radius:10px; padding:14px 16px;
    box-shadow:0 3px 15px rgba(0,0,0,0.18); width:300px;
    max-height:calc(100vh - 24px); overflow:auto;
  }
  #panel h1 { font-size:17px; margin-bottom:2px; color:#1a1a2e; }
  #panel .sub { font-size:12px; color:#777; margin-bottom:10px; }
  #school-count { font-size:13px; color:#333; margin-bottom:8px; }
  #search { width:100%; padding:9px 11px; border:1px solid #ccc; border-radius:6px;
             font-size:13px; outline:none; transition:border 0.15s; }
  #search:focus { border-color:#4361ee; box-shadow:0 0 0 3px rgba(67,97,238,0.15); }
  #list { list-style:none; margin-top:6px; max-height:50vh; overflow-y:auto; }
  #list li {
    padding:7px 9px; cursor:pointer; border-radius:5px; font-size:13px;
    display:flex; justify-content:space-between; gap:6px; align-items:center;
    border-bottom:1px solid #f0f0f0;
  }
  #list li:hover { background:#eef3ff; }
  #list li .nm { font-weight:600; color:#222; }
  #list li .ad { color:#999; font-size:11px; }
  #list li.active { background:#dbeafe; }
  .popup-title { font-weight:700; font-size:14px; }
  .popup-addr { color:#555; font-size:12px; margin-top:3px; }
  .popup-coord { color:#999; font-size:11px; margin-top:2px; }
</style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <h1>🏫 서울 초등학교 지도</h1>
  <div class="sub">공공데이터포털 · 전국초중등학교위치표준데이터</div>
  <div id="school-count">로딩 중…</div>
  <input id="search" type="text" placeholder="학교명 검색 (예: 서울초등)" autocomplete="off" />
  <ul id="list"></ul>
</div>

<script>
const SCHOOLS = {{ schools | tojson }};
const map = L.map('map', { center:[37.54, 126.99], zoom:12, zoomControl:true });
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom:19,
  attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> 기여자'
}).addTo(map);

const markers = [];
const byName = new Map();

SCHOOLS.forEach(s => {
  const m = L.marker([s.lat, s.lng])
    .bindPopup(`
      <div class="popup-title">${s.name}</div>
      <div class="popup-addr">${s.address_road || s.address_jiban || '-'}</div>
      <div class="popup-coord">${s.lat?.toFixed(6)}, ${s.lng?.toFixed(6)}</div>
    `)
    .addTo(map);
  markers.push(m);
  byName.set(s.name, { marker:m, data:s });
});

// 마커 클러스터링 없이 전체 표시
const bounds = L.featureGroup(markers).getBounds();
map.fitBounds(bounds, { padding:[30,30] });

// 리스트 렌더링
const listEl = document.getElementById('list');
const countEl = document.getElementById('school-count');
const searchEl = document.getElementById('search');

function renderList(items) {
  listEl.innerHTML = '';
  items.forEach(s => {
    const li = document.createElement('li');
    li.dataset.name = s.name;
    const addr = (s.address_road || s.address_jiban || '').slice(0, 22);
    li.innerHTML = `<span class="nm">${s.name}</span><span class="ad">${addr}</span>`;
    li.addEventListener('click', () => {
      map.setView([s.lat, s.lng], 15, { animate:true });
      byName.get(s.name).marker.openPopup();
      highlight(s.name);
    });
    listEl.appendChild(li);
  });
}

function highlight(name) {
  document.querySelectorAll('#list li').forEach(li => {
    li.classList.toggle('active', li.dataset.name === name);
  });
}

countEl.textContent = `${SCHOOLS.length}개교 · 좌표가 있는 학교`;

// 가나다순 정렬 → 초기 렌더링
const sorted = [...SCHOOLS].sort((a,b) => a.name.localeCompare(b.name, 'ko'));
renderList(sorted);

// 검색
searchEl.addEventListener('input', () => {
  const q = searchEl.value.trim();
  if (!q) { renderList(sorted); return; }
  const matched = SCHOOLS.filter(s => s.name.includes(q));
  renderList(matched.length ? matched : sorted.filter(s => s.name.includes(q)));
});

// 마커 클릭 시 리스트 하이라이트
markers.forEach(m => {
  m.on('click', () => {
    const s = byName.get(m.getPopup()?.getContent()?.match(/<div class="popup-title">([^<]+)<\/div>/)?.[1])?.data;
    if (s) highlight(s.name);
  });
});
</script>
</body>
</html>
"""


@app.route("/")
def index():
    schools = load_schools()
    return render_template_string(HTML, schools=schools)


@app.route("/api/schools")
def api_schools():
    schools = load_schools()
    return jsonify({"count": len(schools), "schools": schools})


if __name__ == "__main__":
    n = len(load_schools())
    print(f"🏫 서울 초등학교 지도 서버 시작")
    print(f"   데이터: {DATA_PATH} ({n}개교)")
    print(f"   http://localhost:5000")
    print(f"   http://223.130.153.155:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
