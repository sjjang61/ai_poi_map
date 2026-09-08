#!/usr/bin/env python3
"""
서울 초·중·고 학교 위치 지도 뷰어 — Flask + Leaflet
실행: python app.py (또는 .venv/bin/python app.py)
접속: http://localhost:5000
"""

import json
import re
from pathlib import Path
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
DATA_FILES = {
    "elementary": BASE_DIR / "data" / "seoul_elementary.json",
    "middle": BASE_DIR / "data" / "seoul_middle.json",
    "high": BASE_DIR / "data" / "seoul_high.json",
}
TYPE_LABELS = {
    "elementary": "초등학교",
    "middle": "중학교",
    "high": "고등학교",
}
TYPE_ORDER = ["elementary", "middle", "high"]
TYPE_COLORS = {
    "elementary": "#4a90d9",
    "middle": "#e67e22",
    "high": "#8e44ad",
}


def extract_district(address: str) -> str:
    if not address:
        return "기타"
    m = re.search(r"서울특별시\s+([^\s]+)", address)
    return m.group(1) if m else "기타"


def extract_dong(address: str) -> str:
    """지번주소에서 동 정보를 추출 (예: '서울특별시 강남구 신사동 550-11' → '신사동')"""
    if not address:
        return "기타"
    m = re.search(r"서울특별시\s+\S+\s+(\S+동)\s", address)
    return m.group(1) if m else "기타"


def normalize_school(raw: dict, school_type: str) -> dict:
    road = (raw.get("address_road") or raw.get("소재지도로명주소") or "").strip()
    jiban = (raw.get("address_jiban") or raw.get("소재지지번주소") or "").strip()
    district = (raw.get("district") or extract_district(road or jiban)).strip() or "기타"
    dong = (raw.get("dong") or extract_dong(jiban)).strip() or "기타"
    return {
        "id": (raw.get("id") or raw.get("학교ID") or "").strip(),
        "name": (raw.get("name") or raw.get("학교명") or "").strip(),
        "school_type": raw.get("school_type", school_type),
        "district": district,
        "dong": dong,
        "address_road": road,
        "address_jiban": jiban,
        "lat": float(raw["lat"] if "lat" in raw else raw["위도"]) if (raw.get("lat") or raw.get("위도")) else None,
        "lng": float(raw["lng"] if "lng" in raw else raw["경도"]) if (raw.get("lng") or raw.get("경도")) else None,
        "established": (raw.get("established") or raw.get("설립일자") or "").strip(),
        "type": (raw.get("type") or raw.get("설립형태") or "").strip(),
    }


def load_schools() -> list[dict]:
    schools: list[dict] = []
    for school_type, path in DATA_FILES.items():
        if not path.exists():
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        schools.extend(normalize_school(r, school_type) for r in raw)
    return schools


def load_districts() -> list[str]:
    districts = sorted({s["district"] for s in load_schools() if s.get("district") and s["district"] != "기타"})
    return districts


def load_dongs_by_district() -> dict[str, list[str]]:
    """구별 동 목록을 반환 (예: {"강남구": ["신사동", "역삼동", ...], ...})"""
    schools = load_schools()
    dongs_map: dict[str, set[str]] = {}
    for s in schools:
        district = s.get("district", "기타")
        dong = s.get("dong", "기타")
        if district != "기타" and dong != "기타":
            if district not in dongs_map:
                dongs_map[district] = set()
            dongs_map[district].add(dong)
    return {d: sorted(list(dongs)) for d, dongs in dongs_map.items()}


HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>서울 초·중·고 학교 위치 지도</title>
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
    width:340px; max-height:calc(100vh - 24px); overflow:auto;
  }
  #panel h1 { font-size:16px; margin-bottom:4px; color:#222; }
  #panel .count { font-size:12px; color:#666; margin-bottom:10px; line-height:1.4; }
  .filter-bar { display:flex; gap:4px; margin-bottom:10px; flex-wrap:wrap; }
  .filter-btn {
    flex:1; min-width:80px; padding:6px 8px; border:1px solid #ddd; background:#fafafa;
    border-radius:4px; cursor:pointer; font-size:12px; text-align:center;
  }
  .filter-btn.active { background:#4a90d9; color:#fff; border-color:#4a90d9; }
  .filter-btn:hover:not(.active) { background:#e8f4fd; }
  .control-row { margin-bottom:8px; }
  .control-label { display:block; font-size:11px; color:#666; margin-bottom:4px; }
  #district-select, #dong-select, #search-box {
    width:100%; padding:8px 10px; border:1px solid #ccc; border-radius:6px;
    font-size:13px; outline:none;
  }
  #district-select { margin-bottom:8px; }
  #dong-select { margin-bottom:8px; }
  #search-box { margin-bottom:8px; }
  #district-select:focus, #dong-select:focus, #search-box:focus {
    border-color:#4a90d9; box-shadow:0 0 0 2px rgba(74,144,217,0.2);
  }
  #dong-select:disabled {
    background:#f5f5f5; color:#999;
  }
  .legend { font-size:11px; color:#666; margin:8px 0 10px; display:flex; gap:12px; flex-wrap:wrap; }
  .legend span::before {
    content:''; display:inline-block; width:10px; height:10px; border-radius:50%;
    margin-right:4px; vertical-align:middle;
  }
  .legend .elem::before { background:#4a90d9; }
  .legend .mid::before { background:#e67e22; }
  .legend .high::before { background:#8e44ad; }
  #school-list { list-style:none; max-height:420px; overflow-y:auto; }
  #school-list li {
    padding:6px 8px; cursor:pointer; border-bottom:1px solid #eee;
    font-size:13px; display:flex; justify-content:space-between; gap:8px; align-items:center;
  }
  #school-list li:hover { background:#e8f4fd; }
  #school-list li .addr { color:#888; font-size:11px; text-align:right; }
  .type-badge {
    font-size:10px; padding:1px 5px; border-radius:3px; color:#fff; flex-shrink:0;
  }
  .type-badge.elementary { background:#4a90d9; }
  .type-badge.middle { background:#e67e22; }
  .type-badge.high { background:#8e44ad; }
  .leaflet-popup-content { font-family:'Malgun Gothic',sans-serif; font-size:13px; }
</style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <h1>서울 초·중·고 학교 위치</h1>
  <div class="count" id="count">{{ total_count }}개교 / 전체 {{ total_count }}개교</div>
  <div class="filter-bar">
    <button class="filter-btn active" data-type="all">전체</button>
    <button class="filter-btn" data-type="elementary">초등학교</button>
    <button class="filter-btn" data-type="middle">중학교</button>
    <button class="filter-btn" data-type="high">고등학교</button>
  </div>
  <div class="legend">
    <span class="elem">초등학교</span>
    <span class="mid">중학교</span>
    <span class="high">고등학교</span>
  </div>
  <div class="control-row">
    <label class="control-label" for="district-select">구 단위 조회</label>
    <select id="district-select">
      <option value="all">전체 구</option>
      {% for district in districts %}
      <option value="{{ district }}">{{ district }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="control-row">
    <label class="control-label" for="dong-select">동 단위 조회</label>
    <select id="dong-select" disabled>
      <option value="all">전체 동 (구를 먼저 선택)</option>
    </select>
  </div>
  <input id="search-box" type="text" placeholder="학교명 검색 (예: 서울, 강남)" />
  <ul id="school-list"></ul>
</div>

<script>
const schools = {{ schools | tojson }};
const dongsByDistrict = {{ dongs_by_district | tojson }};

const map = L.map('map', { center:[37.54, 126.99], zoom:12, zoomControl:true });
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom:19, attribution:'&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

const markers = [];
const markerMap = new Map();

function getIcon(schoolType) {
  const color = {{ colors | tojson }}[schoolType] || '#4a90d9';
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="width:14px;height:14px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.4);"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

schools.forEach(s => {
  const marker = L.marker([s.lat, s.lng], { icon: getIcon(s.school_type) }).addTo(map);
  marker.bindPopup(`
    <strong>${s.name}</strong><br>
    <span class="type-badge ${s.school_type}">${s.school_type === 'elementary' ? '초등학교' : s.school_type === 'middle' ? '중학교' : '고등학교'}</span><br>
    ${s.district} ${s.dong || ''}<br>
    ${s.address_road || s.address_jiban || ''}<br>
    <span style="color:#888; font-size:11px">${s.lat?.toFixed(6)}, ${s.lng?.toFixed(6)}</span>
  `);
  marker.on('click', () => highlightSchool(s.name));
  markers.push(marker);
  markerMap.set(s.name, marker);
});

const listEl = document.getElementById('school-list');
const countEl = document.getElementById('count');
const districtSelect = document.getElementById('district-select');
const dongSelect = document.getElementById('dong-select');
const searchBox = document.getElementById('search-box');

function updateDongOptions(district) {
  dongSelect.innerHTML = '';
  if (district === 'all') {
    dongSelect.innerHTML = '<option value="all">전체 동 (구를 먼저 선택)</option>';
    dongSelect.disabled = true;
  } else {
    const dongs = dongsByDistrict[district] || [];
    dongSelect.innerHTML = '<option value="all">전체 동</option>';
    dongs.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d;
      dongSelect.appendChild(opt);
    });
    dongSelect.disabled = false;
  }
}

function renderList(list) {
  listEl.innerHTML = '';
  list.forEach(s => {
    const li = document.createElement('li');
    li.innerHTML = `
      <span>
        ${s.name}
        <span class="type-badge ${s.school_type}">${s.school_type === 'elementary' ? '초' : s.school_type === 'middle' ? '중' : '고'}</span>
      </span>
      <span class="addr">${s.district} ${s.dong || ''}<br>${s.address_road ? s.address_road.slice(0,16) : ''}</span>
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

districtSelect.addEventListener('change', () => {
  updateDongOptions(districtSelect.value);
  applyFilters();
});
dongSelect.addEventListener('change', applyFilters);
searchBox.addEventListener('input', applyFilters);

function applyFilters() {
  const q = searchBox.value.trim().toLowerCase();
  const selectedDistrict = districtSelect.value;
  const selectedDong = dongSelect.value;
  let filtered = schools;

  if (activeType !== 'all') {
    filtered = filtered.filter(s => s.school_type === activeType);
  }
  if (selectedDistrict !== 'all') {
    filtered = filtered.filter(s => s.district === selectedDistrict);
  }
  if (selectedDong !== 'all') {
    filtered = filtered.filter(s => s.dong === selectedDong);
  }
  if (q) {
    filtered = filtered.filter(s =>
      s.name.toLowerCase().includes(q) ||
      s.district.toLowerCase().includes(q) ||
      (s.dong || '').toLowerCase().includes(q) ||
      (s.address_road || '').toLowerCase().includes(q)
    );
  }

  const sorted = [...filtered].sort((a, b) => a.name.localeCompare(b.name, 'ko'));
  renderList(sorted);
  countEl.textContent = `${filtered.length}개교 / 전체 ${schools.length}개교`;
}

applyFilters();

const group = L.featureGroup(markers);
map.fitBounds(group.getBounds().pad(0.05));
</script>
</body>
</html>
"""


@app.route("/")
def index():
    schools = load_schools()
    return render_template_string(
        HTML_TEMPLATE,
        schools=schools,
        districts=load_districts(),
        dongs_by_district=load_dongs_by_district(),
        colors=TYPE_COLORS,
        total_count=len(schools),
    )

@app.route("/api/schools")
def api_schools():
    schools = load_schools()
    school_type = request.args.get("type", "all")
    district = request.args.get("district", "all")
    dong = request.args.get("dong", "all")

    if school_type != "all":
        schools = [s for s in schools if s["school_type"] == school_type]
    if district != "all":
        schools = [s for s in schools if s["district"] == district]
    if dong != "all":
        schools = [s for s in schools if s["dong"] == dong]

    counts = {t: 0 for t in TYPE_ORDER}
    for s in load_schools():
        counts[s["school_type"]] = counts.get(s["school_type"], 0) + 1

    return jsonify({
        "count": len(schools),
        "schools": schools,
        "elementary_count": counts["elementary"],
        "middle_count": counts["middle"],
        "high_count": counts["high"],
        "districts": load_districts(),
        "dongs_by_district": load_dongs_by_district(),
    })


if __name__ == "__main__":
    schools = load_schools()
    print(f"🏫 서울 초·중·고 학교 지도 서버 시작")
    print(f"   초등학교: {sum(1 for s in schools if s['school_type'] == 'elementary')}개교")
    print(f"   중학교: {sum(1 for s in schools if s['school_type'] == 'middle')}개교")
    print(f"   고등학교: {sum(1 for s in schools if s['school_type'] == 'high')}개교")
    print(f"   합계: {len(schools)}개교")
    print(f"   http://localhost:5000")
    print(f"   http://223.130.153.155:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
