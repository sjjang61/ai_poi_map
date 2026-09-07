#!/usr/bin/env python3
"""
서울 초등학교 위치 지도 뷰어 — Flask + Leaflet
실행: python app.py (또는 .venv/bin/python app.py)
접속: http://localhost:5000
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


HTML_TEMPLATE = r"""
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
  html, body { height:100%; font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif; }
  #map { height:100vh; width:100%; }
  #panel {
    position:absolute; top:12px; left:12px; z-index:1000;
    background:#fff; border-radius:8px; padding:12px 16px;
    box-shadow:0 2px 12px rgba(0,0,0,0.15);
    max-width:320px; max-height:calc(100vh - 24px); overflow:auto;
  }
  #panel h1 { font-size:16px; margin-bottom:4px; color:#222; }
  #panel .count { font-size:12px; color:#666; margin-bottom:10px; }
  #school-list { list-style:none; max-height:400px; overflow-y:auto; }
  #school-list li {
    padding:6px 8px; cursor:pointer; border-bottom:1px solid #eee;
    font-size:13px; display:flex; justify-content:space-between; gap:8px;
  }
  #school-list li:hover { background:#e8f4fd; }
  #school-list li .addr { color:#888; font-size:11px; }
  #search-box {
    width:100%; padding:8px 10px; border:1px solid #ccc; border-radius:6px;
    font-size:13px; margin-bottom:8px; outline:none;
  }
  #search-box:focus { border-color:#4a90d9; box-shadow:0 0 0 2px rgba(74,144,217,0.2); }
  .leaflet-popup-content { font-family:'Malgun Gothic',sans-serif; font-size:13px; }
</style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <h1>서울 초등학교 위치</h1>
  <div class="count" id="count">로딩 중...</div>
  <input id="search-box" type="text" placeholder="학교명 검색 (예: 서울초등)" />
  <ul id="school-list"></ul>
</div>

<script>
const schools = {{ schools | tojson }};

const map = L.map('map', { center:[37.54, 126.99], zoom:12, zoomControl:true });
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom:19, attribution:'&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

const markers = [];
const markerMap = new Map();

schools.forEach(s => {
  const marker = L.marker([s.lat, s.lng]).addTo(map);
  marker.bindPopup(`
    <strong>${s.name}</strong><br>
    ${s.address_road || s.address_jiban || ''}<br>
    <span style="color:#888">${s.lat?.toFixed(6)}, ${s.lng?.toFixed(6)}</span>
  `);
  marker.on('click', () => highlightSchool(s.name));
  markers.push(marker);
  markerMap.set(s.name, marker);
});

const listEl = document.getElementById('school-list');
const countEl = document.getElementById('count');
function renderList(list) {
  listEl.innerHTML = '';
  list.forEach(s => {
    const li = document.createElement('li');
    li.innerHTML = `<span>${s.name}</span><span class="addr">${s.address_road ? s.address_road.slice(0,18) : ''}</span>`;
    li.addEventListener('click', () => {
      map.setView([s.lat, s.lng], 15);
      markerMap.get(s.name)?.openPopup();
      highlightSchool(s.name);
    });
    listEl.appendChild(li);
  });
}

function highlightSchool(name) {
  document.querySelectorAll('#school-list li').forEach(li => {
    li.style.background = li.textContent.startsWith(name) ? '#cce5ff' : '';
  });
}

countEl.textContent = `${schools.length}개교`;

const sorted = [...schools].sort((a,b) => a.name.localeCompare(b.name, 'ko'));
renderList(sorted);

document.getElementById('search-box').addEventListener('input', e => {
  const q = e.target.value.trim();
  if (!q) { renderList(sorted); return; }
  const filtered = schools.filter(s => s.name.includes(q));
  renderList(filtered);
});

const group = L.featureGroup(markers);
map.fitBounds(group.getBounds().pad(0.05));
</script>
</body>
</html>
"""


@app.route("/")
def index():
    schools = load_schools()
    return render_template_string(HTML_TEMPLATE, schools=schools)


@app.route("/api/schools")
def api_schools():
    schools = load_schools()
    return jsonify({"count": len(schools), "schools": schools})


if __name__ == "__main__":
    print(f"📍 서울 초등학교 지도 뷰어")
    print(f"   데이터: {DATA_PATH} ({len(load_schools())}개교)")
    print(f"   http://localhost:5000 에서 확인하세요.")
    app.run(host="0.0.0.0", port=5000, debug=False)
