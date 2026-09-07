#!/usr/bin/env python3
"""
서울 초·중학교 위치 지도 뷰어 — Flask + Leaflet
실행: python app.py (또는 .venv/bin/python app.py)
접속: http://localhost:5000
"""

import json
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
ELEM_PATH = BASE_DIR / "data" / "seoul_elementary.json"
MID_PATH = BASE_DIR / "data" / "seoul_middle.json"


def load_elementary():
    if not ELEM_PATH.exists():
        return []
    return json.loads(ELEM_PATH.read_text(encoding="utf-8"))


def load_middle():
    if not MID_PATH.exists():
        return []
    return json.loads(MID_PATH.read_text(encoding="utf-8"))


def enrich_schools(schools, school_type):
    """학교 타입 태그 추가"""
    return [{"school_type": school_type, **s} for s in schools]


HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>서울 초·중학교 위치 지도</title>
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
  .filter-bar { display:flex; gap:4px; margin-bottom:10px; }
  .filter-btn {
    flex:1; padding:6px 8px; border:1px solid #ddd; background:#fafafa;
    border-radius:4px; cursor:pointer; font-size:12px; text-align:center;
  }
  .filter-btn.active { background:#4a90d9; color:#fff; border-color:#4a90d9; }
  .filter-btn:hover:not(.active) { background:#e8f4fd; }
  #school-list { list-style:none; max-height:400px; overflow-y:auto; }
  #school-list li {
    padding:6px 8px; cursor:pointer; border-bottom:1px solid #eee;
    font-size:13px; display:flex; justify-content:space-between; gap:8px; align-items:center;
  }
  #school-list li:hover { background:#e8f4fd; }
  #school-list li .addr { color:#888; font-size:11px; }
  .type-badge {
    font-size:10px; padding:1px 5px; border-radius:3px; color:#fff; flex-shrink:0;
  }
  .type-badge.elementary { background:#4a90d9; }
  .type-badge.middle { background:#e67e22; }
  #search-box {
    width:100%; padding:8px 10px; border:1px solid #ccc; border-radius:6px;
    font-size:13px; margin-bottom:8px; outline:none;
  }
  #search-box:focus { border-color:#4a90d9; box-shadow:0 0 0 2px rgba(74,144,217,0.2); }
  .legend { font-size:11px; color:#666; margin:8px 0; display:flex; gap:12px; }
  .legend span::before {
    content:''; display:inline-block; width:10px; height:10px; border-radius:50%;
    margin-right:4px; vertical-align:middle;
  }
  .legend .elem::before { background:#4a90d9; }
  .legend .mid::before { background:#e67e22; }
  .leaflet-popup-content { font-family:'Malgun Gothic',sans-serif; font-size:13px; }
</style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <h1>서울 초·중학교 위치</h1>
  <div class="count" id="count">로딩 중...</div>
  <div class="filter-bar">
    <button class="filter-btn active" data-type="all">전체</button>
    <button class="filter-btn" data-type="elementary">초등학교</button>
    <button class="filter-btn" data-type="middle">중학교</button>
  </div>
  <div class="legend">
    <span class="elem">초등학교</span>
    <span class="mid">중학교</span>
  </div>
  <input id="search-box" type="text" placeholder="학교명 검색 (예: 서울중)" />
  <ul id="school-list"></ul>
</div>

<script>
const schools = {{ schools | tojson }};

const map = L.map('map', { center:[37.54, 126.99], zoom:12, zoomControl:true });
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom:19, attribution:'&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

const markers = {};
const markerMap = new Map();

function getIcon(schoolType) {
  const color = schoolType === 'elementary' ? '#4a90d9' : '#e67e22';
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      width:14px; height:14px; border-radius:50%;
      background:${color}; border:2px solid #fff;
      box-shadow:0 1px 4px rgba(0,0,0,0.4);
    "></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

schools.forEach(s => {
  const marker = L.marker([s.lat, s.lng], { icon: getIcon(s.school_type) }).addTo(map);
  marker.bindPopup(`
    <strong>${s.name}</strong><br>
    <span class="type-badge ${s.school_type}">${s.school_type === 'elementary' ? '초등학교' : '중학교'}</span><br>
    ${s.address_road || s.address_jiban || ''}<br>
    <span style="color:#888; font-size:11px">${s.lat?.toFixed(6)}, ${s.lng?.toFixed(6)}</span>
  `);
  marker.on('click', () => highlightSchool(s.name));
  markers[s.name] = marker;
  markerMap.set(s.name, marker);
});

const listEl = document.getElementById('school-list');
const countEl = document.getElementById('count');

function renderList(list) {
  listEl.innerHTML = '';
  list.forEach(s => {
    const li = document.createElement('li');
    li.innerHTML = `
      <span>
        ${s.name}
        <span class="type-badge ${s.school_type}">${s.school_type === 'elementary' ? '초' : '중'}</span>
      </span>
      <span class="addr">${s.address_road ? s.address_road.slice(0,16) : ''}</span>
    `;
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
    li.style.background = li.textContent.includes(name) ? '#cce5ff' : '';
  });
}

// 필터 버튼
const filterBtns = document.querySelectorAll('.filter-btn');
let activeType = 'all';

filterBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    filterBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeType = btn.dataset.type;
    applyFilters();
  });
});

function applyFilters() {
  const q = document.getElementById('search-box').value.trim().toLowerCase();
  let filtered = schools;
  if (activeType !== 'all') {
    filtered = filtered.filter(s => s.school_type === activeType);
  }
  if (q) {
    filtered = filtered.filter(s => s.name.toLowerCase().includes(q));
  }
  const sorted = [...filtered].sort((a,b) => a.name.localeCompare(b.name, 'ko'));
  renderList(sorted);
  countEl.textContent = `${filtered.length}개교`;
}

countEl.textContent = `${schools.length}개교`;
applyFilters();

document.getElementById('search-box').addEventListener('input', applyFilters);

const group = L.featureGroup(Object.values(markers));
map.fitBounds(group.getBounds().pad(0.05));
</script>
</body>
</html>
"""


@app.route("/")
def index():
    elementary = load_elementary()
    middle = load_middle()
    schools = enrich_schools(elementary, "elementary") + enrich_schools(middle, "middle")
    return render_template_string(HTML_TEMPLATE, schools=schools)


@app.route("/api/schools")
def api_schools():
    elementary = load_elementary()
    middle = load_middle()
    schools = enrich_schools(elementary, "elementary") + enrich_schools(middle, "middle")

    # type 필터
    school_type = request.args.get("type", "all")
    if school_type != "all":
        schools = [s for s in schools if s["school_type"] == school_type]

    return jsonify({
        "count": len(schools),
        "schools": schools,
        "elementary_count": len(elementary),
        "middle_count": len(middle),
    })


if __name__ == "__main__":
    elem = load_elementary()
    mid = load_middle()
    print(f"📍 서울 초·중학교 지도 뷰어")
    print(f"   초등학교: {len(elem)}개교 ({ELEM_PATH})")
    print(f"   중학교: {len(mid)}개교 ({MID_PATH})")
    print(f"   합계: {len(elem) + len(mid)}개교")
    print(f"   http://localhost:5000 에서 확인하세요.")
    app.run(host="0.0.0.0", port=5000, debug=False)
