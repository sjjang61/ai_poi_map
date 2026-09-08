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
        "students": raw.get("students", 0),
        "teachers": raw.get("teachers", 0),
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
  #locate-btn {
    position:absolute; top:80px; right:12px; z-index:1000;
    background:#fff; border:2px solid rgba(0,0,0,0.2); border-radius:4px;
    padding:8px 12px; cursor:pointer; font-size:14px;
    box-shadow:0 2px 6px rgba(0,0,0,0.2);
    display:flex; align-items:center; gap:6px;
  }
  #locate-btn:hover { background:#f4f4f4; }
  #locate-btn:disabled { opacity:0.6; cursor:wait; }
  #locate-btn .icon { font-size:16px; }
  #context-menu {
    position:absolute; z-index:2000; display:none;
    background:#fff; border-radius:8px; padding:6px 0;
    box-shadow:0 4px 16px rgba(0,0,0,0.25);
    min-width:160px;
  }
  #context-menu .menu-item {
    padding:10px 16px; cursor:pointer; font-size:13px;
    display:flex; align-items:center; gap:8px;
  }
  #context-menu .menu-item:hover { background:#f0f7ff; }
  #context-menu .menu-item .icon { font-size:16px; }

  /* === 즐겨찾기 기능 스타일 === */
  .favorite-star {
    cursor:pointer; font-size:16px; color:#ccc;
    margin-right:6px; transition:color 0.2s, transform 0.2s;
  }
  .favorite-star:hover { transform:scale(1.2); color:#f1c40f; }
  .favorite-star.favorited { color:#f1c40f; }
  .favorites-filter {
    display:flex; align-items:center; gap:8px;
    margin-bottom:10px; padding:8px; background:#fffbea;
    border-radius:6px; border:1px solid #f1c40f;
  }
  .favorites-filter label {
    font-size:12px; cursor:pointer; display:flex; align-items:center; gap:6px;
  }
  .favorites-filter input[type="checkbox"] { accent-color:#f1c40f; }
  #favorites-count { font-size:11px; color:#e67e22; font-weight:bold; }
  #school-list li.favorited-item { background:#fffef0; }

  /* === 학교 비교 기능 스타일 === */
  .school-checkbox {
    margin-right:6px; cursor:pointer; accent-color:#27ae60;
    width:14px; height:14px;
  }
  #compare-btn {
    display:none; width:100%; padding:10px; margin-bottom:8px;
    background:#27ae60; color:#fff; border:none; border-radius:6px;
    cursor:pointer; font-size:13px; font-weight:bold;
  }
  #compare-btn:hover { background:#219a52; }
  #compare-modal {
    display:none; position:fixed; top:0; left:0; right:0; bottom:0;
    background:rgba(0,0,0,0.5); z-index:3000;
    justify-content:center; align-items:center;
  }
  .compare-modal-content {
    background:#fff; border-radius:12px; padding:24px;
    max-width:90vw; max-height:80vh; overflow:auto; position:relative;
  }
  .compare-modal-close {
    position:absolute; top:12px; right:16px;
    font-size:24px; cursor:pointer; color:#666;
  }
  .compare-modal-close:hover { color:#333; }
  .compare-grid {
    display:flex; gap:16px; flex-wrap:wrap; justify-content:center;
  }
  .compare-card {
    background:#f8f9fa; border-radius:8px; padding:16px;
    min-width:180px; max-width:220px; flex:1;
  }
  .compare-card h3 {
    font-size:14px; margin-bottom:12px; padding-bottom:8px;
    border-bottom:2px solid #4a90d9; color:#333;
  }
  .compare-row {
    display:flex; justify-content:space-between;
    font-size:12px; padding:4px 0; border-bottom:1px solid #eee;
  }
  .compare-row span:first-child { color:#666; }
  .compare-row span:last-child { font-weight:500; color:#333; }
  .compare-row.highlight {
    background:#e8f4fd; padding:6px 4px; border-radius:4px;
    font-weight:bold; margin-top:8px; border:none;
  }
</style>
</head>
<body>
<div id="map"></div>
<button id="locate-btn" onclick="locateMe()">
  <span class="icon">📍</span>
  <span>현재 위치</span>
</button>
<div id="context-menu">
  <div class="menu-item" onclick="searchNearbySchools()">
    <span class="icon">🏫</span>
    <span>근처 학교 검색</span>
  </div>
</div>
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
  <div class="favorites-filter">
    <label>
      <input type="checkbox" id="favorites-toggle" onchange="toggleFavoritesOnly()">
      <span style="color:#f1c40f;">★</span> 즐겨찾기만 보기 <span id="favorites-count"></span>
    </label>
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
  <button id="compare-btn" onclick="openCompareModal()">선택한 학교 비교</button>
  <ul id="school-list"></ul>
</div>

<!-- 학교 비교 모달 -->
<div id="compare-modal" onclick="if(event.target===this)closeCompareModal()">
  <div class="compare-modal-content">
    <span class="compare-modal-close" onclick="closeCompareModal()">&times;</span>
    <h2 style="margin-bottom:16px;color:#333;">📊 학교 비교</h2>
    <div id="compare-content"></div>
    <div style="text-align:center;margin-top:16px;">
      <button onclick="clearSelection();closeCompareModal()" style="padding:8px 16px;background:#95a5a6;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-right:8px;">선택 초기화</button>
      <button onclick="closeCompareModal()" style="padding:8px 24px;background:#4a90d9;color:#fff;border:none;border-radius:4px;cursor:pointer;">닫기</button>
    </div>
  </div>
</div>

<script>
const schools = {{ schools | tojson }};
const dongsByDistrict = {{ dongs_by_district | tojson }};

// === 즐겨찾기 및 비교 기능 상태 변수 ===
const FAVORITES_KEY = 'seoul_school_favorites';
let favorites = new Set();
let selectedSchools = new Set();
let showFavoritesOnly = false;

// === localStorage 관리 함수 ===
function loadFavorites() {
  try {
    const saved = localStorage.getItem(FAVORITES_KEY);
    return saved ? JSON.parse(saved) : [];
  } catch (e) {
    console.error('Failed to load favorites:', e);
    return [];
  }
}

function saveFavorites() {
  try {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify([...favorites]));
  } catch (e) {
    console.error('Failed to save favorites:', e);
  }
}

// === 즐겨찾기 기능 ===
function toggleFavorite(schoolId, event) {
  event.stopPropagation();
  if (favorites.has(schoolId)) {
    favorites.delete(schoolId);
  } else {
    favorites.add(schoolId);
  }
  saveFavorites();
  updateFavoriteIcons();
  if (showFavoritesOnly) {
    applyFilters();
  }
}

function updateFavoriteIcons() {
  document.querySelectorAll('.favorite-star').forEach(star => {
    const schoolId = star.dataset.schoolId;
    if (favorites.has(schoolId)) {
      star.textContent = '★';
      star.classList.add('favorited');
    } else {
      star.textContent = '☆';
      star.classList.remove('favorited');
    }
  });
  // 즐겨찾기 개수 업데이트
  const countEl = document.getElementById('favorites-count');
  if (countEl) {
    countEl.textContent = favorites.size > 0 ? `(${favorites.size})` : '';
  }
}

function toggleFavoritesOnly() {
  showFavoritesOnly = document.getElementById('favorites-toggle').checked;
  applyFilters();
}

function initFavorites() {
  favorites = new Set(loadFavorites());
  updateFavoriteIcons();
}

// 팝업 즐겨찾기 버튼 상태 업데이트
function updatePopupFavoriteButton(schoolId) {
  const icon = document.getElementById(`popup-fav-icon-${schoolId}`);
  const text = document.getElementById(`popup-fav-text-${schoolId}`);
  const btn = document.getElementById(`popup-fav-btn-${schoolId}`);
  if (!icon || !text || !btn) return;

  if (favorites.has(schoolId)) {
    icon.textContent = '★';
    text.textContent = '즐겨찾기 해제';
    btn.style.background = '#f1c40f';
    btn.style.color = '#fff';
    btn.style.borderColor = '#f1c40f';
  } else {
    icon.textContent = '☆';
    text.textContent = '즐겨찾기 추가';
    btn.style.background = '#fffbea';
    btn.style.color = '#333';
    btn.style.borderColor = '#f1c40f';
  }
}

// 팝업에서 즐겨찾기 토글
function togglePopupFavorite(schoolId) {
  if (favorites.has(schoolId)) {
    favorites.delete(schoolId);
  } else {
    favorites.add(schoolId);
  }
  saveFavorites();
  updateFavoriteIcons();
  updatePopupFavoriteButton(schoolId);
  if (showFavoritesOnly) {
    applyFilters();
  }
}

// === 학교 비교 기능 ===
function toggleSchoolSelection(schoolId, checkbox) {
  if (checkbox.checked) {
    if (selectedSchools.size >= 5) {
      alert('최대 5개 학교까지 비교할 수 있습니다.');
      checkbox.checked = false;
      return;
    }
    selectedSchools.add(schoolId);
  } else {
    selectedSchools.delete(schoolId);
  }
  updateCompareButton();
}

function updateCompareButton() {
  const btn = document.getElementById('compare-btn');
  const count = selectedSchools.size;
  if (count >= 2) {
    btn.style.display = 'block';
    btn.textContent = `선택한 ${count}개 학교 비교`;
  } else {
    btn.style.display = 'none';
  }
}

function clearSelection() {
  selectedSchools.clear();
  document.querySelectorAll('.school-checkbox').forEach(cb => cb.checked = false);
  updateCompareButton();
}

function openCompareModal() {
  const modal = document.getElementById('compare-modal');
  const content = document.getElementById('compare-content');
  const selected = schools.filter(s => selectedSchools.has(s.id));
  content.innerHTML = generateComparisonHTML(selected);
  modal.style.display = 'flex';
}

function closeCompareModal() {
  document.getElementById('compare-modal').style.display = 'none';
}

function generateComparisonHTML(schoolList) {
  let html = '<div class="compare-grid">';
  schoolList.forEach(s => {
    const ratio = s.teachers > 0 ? (s.students / s.teachers).toFixed(1) : '-';
    const typeLabel = s.school_type === 'elementary' ? '초등학교' :
                      s.school_type === 'middle' ? '중학교' : '고등학교';
    const typeColor = s.school_type === 'elementary' ? '#4a90d9' :
                      s.school_type === 'middle' ? '#e67e22' : '#8e44ad';
    const year = s.established ? s.established.split('-')[0] : '-';
    const fundLabel = s.type || '공립';
    const fundColor = s.type === '사립' ? '#e74c3c' : '#27ae60';

    html += `
      <div class="compare-card">
        <h3 style="border-bottom-color:${typeColor};">${s.name}</h3>
        <div class="compare-row"><span>학교급</span><span style="color:${typeColor};font-weight:bold;">${typeLabel}</span></div>
        <div class="compare-row"><span>설립형태</span><span style="color:${fundColor};">${fundLabel}</span></div>
        <div class="compare-row"><span>소재지</span><span>${s.district} ${s.dong || ''}</span></div>
        <div class="compare-row"><span>설립연도</span><span>${year}년</span></div>
        <div class="compare-row"><span>학생수</span><span style="color:#3498db;font-weight:bold;">${s.students || '-'}명</span></div>
        <div class="compare-row"><span>교원수</span><span style="color:#27ae60;font-weight:bold;">${s.teachers || '-'}명</span></div>
        <div class="compare-row highlight"><span>학생/교원 비율</span><span style="color:#e67e22;">${ratio}</span></div>
      </div>
    `;
  });
  html += '</div>';
  return html;
}

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
  const schoolTypeLabel = s.school_type === 'elementary' ? '초등학교' : s.school_type === 'middle' ? '중학교' : '고등학교';
  const schoolInfoUrl = `https://www.schoolinfo.go.kr/ng/go/pnnggo_a01_l0.do?schulNm=${encodeURIComponent(s.name)}`;
  const establishedYear = s.established ? s.established.split('-')[0] + '년' : '';
  const studentTeacherRatio = s.teachers > 0 ? (s.students / s.teachers).toFixed(1) : '-';

  marker.bindPopup(`
    <div style="min-width:220px;">
      <strong style="font-size:14px;">${s.name}</strong><br>
      <span class="type-badge ${s.school_type}">${schoolTypeLabel}</span>
      <span style="background:#${s.type === '사립' ? 'e74c3c' : '27ae60'};color:#fff;padding:1px 5px;border-radius:3px;font-size:10px;margin-left:4px;">${s.type || '공립'}</span>
      <hr style="margin:6px 0;border:none;border-top:1px solid #eee;">
      <div style="font-size:12px;color:#555;">
        <div>📍 ${s.district} ${s.dong || ''}</div>
        <div style="color:#777;font-size:11px;">${s.address_road || s.address_jiban || ''}</div>
        ${establishedYear ? `<div style="margin-top:4px;">🏫 설립: ${establishedYear}</div>` : ''}
      </div>
      <hr style="margin:6px 0;border:none;border-top:1px solid #eee;">
      <div style="background:#f8f9fa;padding:8px;border-radius:4px;margin-bottom:6px;">
        <div style="font-size:11px;color:#666;margin-bottom:4px;">📊 학교 현황 (2025년 공시)</div>
        <div style="display:flex;gap:12px;justify-content:space-around;">
          <div style="text-align:center;">
            <div style="font-size:16px;font-weight:bold;color:#3498db;">👨‍🎓 ${s.students || '-'}</div>
            <div style="font-size:9px;color:#999;">학생수</div>
          </div>
          <div style="text-align:center;">
            <div style="font-size:16px;font-weight:bold;color:#27ae60;">👩‍🏫 ${s.teachers || '-'}</div>
            <div style="font-size:9px;color:#999;">교원수</div>
          </div>
          <div style="text-align:center;">
            <div style="font-size:16px;font-weight:bold;color:#e67e22;">📐 ${studentTeacherRatio}</div>
            <div style="font-size:9px;color:#999;">학생/교원</div>
          </div>
        </div>
      </div>
      <div style="font-size:11px;margin-bottom:6px;">
        <button id="popup-fav-btn-${s.id}" onclick="togglePopupFavorite('${s.id}')" style="width:100%;padding:6px;border:1px solid #f1c40f;background:#fffbea;border-radius:4px;cursor:pointer;font-size:11px;display:flex;align-items:center;justify-content:center;gap:4px;">
          <span id="popup-fav-icon-${s.id}">☆</span> <span id="popup-fav-text-${s.id}">즐겨찾기 추가</span>
        </button>
      </div>
      <div style="font-size:11px;">
        <a href="${schoolInfoUrl}" target="_blank" style="color:#3498db;text-decoration:none;display:block;padding:6px;background:#e8f4fd;border-radius:4px;text-align:center;">
          📊 학교알리미에서 상세정보 보기 →
        </a>
      </div>
      <div style="color:#999;font-size:10px;margin-top:4px;">
        좌표: ${s.lat?.toFixed(5)}, ${s.lng?.toFixed(5)}
      </div>
    </div>
  `, { maxWidth: 300 });

  // 팝업 열릴 때 즐겨찾기 버튼 상태 업데이트
  marker.on('popupopen', () => {
    updatePopupFavoriteButton(s.id);
  });

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
    const isFavorited = favorites.has(s.id);
    const isSelected = selectedSchools.has(s.id);
    if (isFavorited) li.classList.add('favorited-item');

    li.innerHTML = `
      <span style="display:flex;align-items:center;">
        <input type="checkbox" class="school-checkbox"
               ${isSelected ? 'checked' : ''}
               onclick="event.stopPropagation();toggleSchoolSelection('${s.id}', this)">
        <span class="favorite-star ${isFavorited ? 'favorited' : ''}"
              data-school-id="${s.id}"
              onclick="toggleFavorite('${s.id}', event)">${isFavorited ? '★' : '☆'}</span>
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
  // 비교 버튼 상태 업데이트
  updateCompareButton();
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

  // 즐겨찾기 필터
  if (showFavoritesOnly) {
    filtered = filtered.filter(s => favorites.has(s.id));
  }
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

// 즐겨찾기 초기화 및 필터 적용
initFavorites();
applyFilters();

const group = L.featureGroup(markers);
map.fitBounds(group.getBounds().pad(0.05));

// --- 거리 계산 기능 ---
// Encoded Polyline 디코딩 함수 (Valhalla 6자리 정밀도)
function decodePolyline(encoded) {
  const coords = [];
  let index = 0, lat = 0, lng = 0;
  while (index < encoded.length) {
    let b, shift = 0, result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlat = ((result & 1) ? ~(result >> 1) : (result >> 1));
    lat += dlat;
    shift = 0;
    result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlng = ((result & 1) ? ~(result >> 1) : (result >> 1));
    lng += dlng;
    coords.push([lat / 1e6, lng / 1e6]); // Valhalla uses 6 decimal precision
  }
  return coords;
}

// Haversine 공식으로 두 좌표 간 거리 계산 (km 단위)
function haversineDistance(lat1, lng1, lat2, lng2) {
  const R = 6371; // 지구 반지름 (km)
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// 클릭 마커와 반경 원을 저장할 변수
let clickMarker = null;
let radiusCircle = null;
let routeLine = null;
let routeInfoBox = null;
let currentClickLat = null;
let currentClickLng = null;
let currentRadius = 1; // 기본 반경 1km

// 반경 변경 시 학교 목록 업데이트 함수
function updateRadius(radiusKm) {
  currentRadius = radiusKm;
  if (!currentClickLat || !currentClickLng) return;

  // 반경 원 업데이트
  if (radiusCircle) {
    radiusCircle.setRadius(radiusKm * 1000);
  }

  // 학교 목록 업데이트
  updateSchoolList();
}

// 학교 목록 업데이트 함수
function updateSchoolList() {
  if (!currentClickLat || !currentClickLng) return;

  // 현재 필터에 맞는 학교만 필터링
  let filteredSchools = schools;
  if (activeType !== 'all') {
    filteredSchools = filteredSchools.filter(s => s.school_type === activeType);
  }

  // 반경 내 학교 찾기
  const nearbySchools = filteredSchools
    .map(s => ({ ...s, distance: haversineDistance(currentClickLat, currentClickLng, s.lat, s.lng) }))
    .filter(s => s.distance <= currentRadius)
    .sort((a, b) => a.distance - b.distance);

  // 학교 목록 HTML 업데이트
  const listContainer = document.getElementById('nearby-school-list');
  const countEl = document.getElementById('nearby-count');
  if (!listContainer || !countEl) return;

  if (nearbySchools.length === 0) {
    countEl.textContent = '0개교 발견';
    listContainer.innerHTML = '<p style="color:#999;font-size:12px;padding:8px 0;">반경 내 학교가 없습니다.</p>';
  } else {
    countEl.textContent = `${nearbySchools.length}개교 발견`;
    let listHtml = '';
    nearbySchools.forEach(s => {
      const typeColor = s.school_type === 'elementary' ? '#4a90d9' :
                        s.school_type === 'middle' ? '#e67e22' : '#8e44ad';
      const typeShort = s.school_type === 'elementary' ? '초' :
                        s.school_type === 'middle' ? '중' : '고';
      const escapedName = s.name.replace(/'/g, "\\'");
      const fundColor = s.type === '사립' ? '#e74c3c' : '#27ae60';
      const fundLabel = s.type || '공립';
      listHtml += `<li onclick="showWalkingRoute(${s.lat}, ${s.lng}, '${escapedName}')" style="padding:6px 4px;border-bottom:1px solid #eee;font-size:12px;cursor:pointer;transition:background 0.2s;" onmouseover="this.style.background='#e8f8f0'" onmouseout="this.style.background=''">
        <span style="background:${typeColor};color:#fff;padding:1px 4px;border-radius:3px;font-size:10px;margin-right:2px;">${typeShort}</span>
        <span style="background:${fundColor};color:#fff;padding:1px 4px;border-radius:3px;font-size:9px;">${fundLabel}</span>
        ${s.name}
        <br><span style="color:#ff6b6b;font-weight:bold;font-size:11px;">📏 ${(s.distance * 1000).toFixed(0)}m</span>
        <span style="color:#999;font-size:10px;"> (${s.distance.toFixed(2)}km)</span>
        <span style="color:#2ecc71;font-size:10px;float:right;">🚶 경로</span>
      </li>`;
    });
    listContainer.innerHTML = listHtml;
  }
}

// 도보 경로 표시 함수
async function showWalkingRoute(endLat, endLng, schoolName) {
  if (!currentClickLat || !currentClickLng) return;

  // 기존 경로 제거
  if (routeLine) {
    map.removeLayer(routeLine);
  }
  if (routeInfoBox) {
    map.removeLayer(routeInfoBox);
  }

  // 팝업 닫기
  map.closePopup();

  try {
    // Valhalla API로 도보 경로 조회 (pedestrian costing)
    const valhallaRequest = {
      locations: [
        { lat: currentClickLat, lon: currentClickLng },
        { lat: endLat, lon: endLng }
      ],
      costing: "pedestrian",
      directions_options: { units: "kilometers" }
    };

    const response = await fetch('https://valhalla1.openstreetmap.de/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(valhallaRequest)
    });
    const data = await response.json();

    if (!data.trip || !data.trip.legs || data.trip.legs.length === 0) {
      alert('도보 경로를 찾을 수 없습니다.');
      return;
    }

    const leg = data.trip.legs[0];
    const distanceKm = leg.summary.length; // km 단위
    const distanceM = distanceKm * 1000;
    const durationMin = Math.round(leg.summary.time / 60); // 초 -> 분

    // shape 디코딩 (Valhalla는 encoded polyline 사용)
    const coords = decodePolyline(leg.shape);

    // 경로 폴리라인 그리기
    routeLine = L.polyline(coords, {
      color: '#2ecc71',
      weight: 5,
      opacity: 0.8,
      dashArray: null
    }).addTo(map);

    // 경로에 맞춰 지도 뷰 조정
    map.fitBounds(routeLine.getBounds().pad(0.1));

    const minutes = durationMin;

    // 경로 정보 박스 표시 (목적지 마커에)
    const infoContent = `
      <div style="min-width:180px;">
        <strong style="color:#2ecc71;">🚶 도보 경로</strong><br>
        <span style="font-size:13px;font-weight:bold;">${schoolName}</span>
        <hr style="margin:6px 0;">
        <div style="font-size:12px;">
          <span style="color:#2ecc71;font-weight:bold;">⏱ ${minutes}분</span> (도보 예상)<br>
          <span style="color:#666;">📏 ${distanceKm}km (${distanceM.toFixed(0)}m)</span>
        </div>
        <hr style="margin:6px 0;">
        <button onclick="clearRoute()" style="width:100%;padding:6px;background:#ff6b6b;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:11px;">경로 지우기</button>
      </div>
    `;

    routeInfoBox = L.popup({ closeOnClick: false, autoClose: false })
      .setLatLng([endLat, endLng])
      .setContent(infoContent)
      .openOn(map);

  } catch (error) {
    console.error('경로 조회 실패:', error);
    alert('경로 조회 중 오류가 발생했습니다.');
  }
}

// 경로 지우기 함수
function clearRoute() {
  if (routeLine) {
    map.removeLayer(routeLine);
    routeLine = null;
  }
  if (routeInfoBox) {
    map.removeLayer(routeInfoBox);
    routeInfoBox = null;
  }
}

// 현재 위치 찾기 함수
function locateMe() {
  const btn = document.getElementById('locate-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="icon">⏳</span><span>위치 확인 중...</span>';

  if (!navigator.geolocation) {
    alert('이 브라우저에서는 위치 서비스를 지원하지 않습니다.');
    btn.disabled = false;
    btn.innerHTML = '<span class="icon">📍</span><span>현재 위치</span>';
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lat = position.coords.latitude;
      const lng = position.coords.longitude;

      // 현재 위치 저장
      currentClickLat = lat;
      currentClickLng = lng;

      // 기존 마커/원/경로 제거
      clearRoute();
      if (clickMarker) map.removeLayer(clickMarker);
      if (radiusCircle) map.removeLayer(radiusCircle);

      // 지도 이동
      map.setView([lat, lng], 15);

      // 현재 필터에 맞는 학교만 필터링
      let filteredSchools = schools;
      if (activeType !== 'all') {
        filteredSchools = filteredSchools.filter(s => s.school_type === activeType);
      }

      // 기본 반경 1km로 초기화
      currentRadius = 1;

      // 반경 내 학교 찾기
      const nearbySchools = filteredSchools
        .map(s => ({ ...s, distance: haversineDistance(lat, lng, s.lat, s.lng) }))
        .filter(s => s.distance <= currentRadius)
        .sort((a, b) => a.distance - b.distance);

      // 반경 원 그리기
      radiusCircle = L.circle([lat, lng], {
        radius: currentRadius * 1000,
        color: '#3498db',
        fillColor: '#3498db',
        fillOpacity: 0.1,
        weight: 2,
        dashArray: '5, 5'
      }).addTo(map);

      // 현재 위치 마커
      clickMarker = L.marker([lat, lng], {
        icon: L.divIcon({
          className: 'my-location-marker',
          html: '<div style="width:24px;height:24px;border-radius:50%;background:#3498db;border:4px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,0.4);"></div>',
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        })
      }).addTo(map);

      // 팝업 내용 생성
      const typeLabel = activeType === 'all' ? '전체' :
                        activeType === 'elementary' ? '초등학교' :
                        activeType === 'middle' ? '중학교' : '고등학교';

      let popupContent = '<div style="max-height:350px;overflow-y:auto;min-width:220px;">';
      popupContent += '<strong style="color:#3498db;">📍 내 현재 위치</strong><br>';
      popupContent += `<span style="font-size:11px;color:#666;">${lat.toFixed(5)}, ${lng.toFixed(5)}</span>`;
      popupContent += `<span style="font-size:11px;color:#666;"> / 필터: ${typeLabel}</span>`;
      popupContent += '<hr style="margin:6px 0;">';

      // 반경 슬라이더
      popupContent += '<div style="margin-bottom:8px;">';
      popupContent += `<label style="font-size:11px;color:#666;">반경: <strong id="radius-label">${currentRadius}km</strong></label>`;
      popupContent += `<input type="range" id="radius-slider" min="0.5" max="3" step="0.5" value="${currentRadius}"
        style="width:100%;margin-top:4px;cursor:pointer;"
        oninput="document.getElementById('radius-label').textContent=this.value+'km'; updateRadius(parseFloat(this.value));">`;
      popupContent += '<div style="display:flex;justify-content:space-between;font-size:9px;color:#999;"><span>500m</span><span>1.5km</span><span>3km</span></div>';
      popupContent += '</div>';
      popupContent += '<hr style="margin:6px 0;">';

      popupContent += `<p style="font-size:12px;margin-bottom:6px;" id="nearby-count"><strong>${nearbySchools.length}개교</strong> 발견</p>`;
      popupContent += '<ul id="nearby-school-list" style="list-style:none;padding:0;margin:0;max-height:180px;overflow-y:auto;">';

      if (nearbySchools.length === 0) {
        popupContent += '<li style="color:#999;font-size:12px;padding:8px 0;">반경 내 학교가 없습니다.</li>';
      } else {
        nearbySchools.forEach(s => {
          const typeColor = s.school_type === 'elementary' ? '#4a90d9' :
                            s.school_type === 'middle' ? '#e67e22' : '#8e44ad';
          const typeShort = s.school_type === 'elementary' ? '초' :
                            s.school_type === 'middle' ? '중' : '고';
          const escapedName = s.name.replace(/'/g, "\\'");
          const fundColor = s.type === '사립' ? '#e74c3c' : '#27ae60';
          const fundLabel = s.type || '공립';
          popupContent += `<li onclick="showWalkingRoute(${s.lat}, ${s.lng}, '${escapedName}')" style="padding:6px 4px;border-bottom:1px solid #eee;font-size:12px;cursor:pointer;transition:background 0.2s;" onmouseover="this.style.background='#e8f8f0'" onmouseout="this.style.background=''">
            <span style="background:${typeColor};color:#fff;padding:1px 4px;border-radius:3px;font-size:10px;margin-right:2px;">${typeShort}</span>
            <span style="background:${fundColor};color:#fff;padding:1px 4px;border-radius:3px;font-size:9px;">${fundLabel}</span>
            ${s.name}
            <br><span style="color:#3498db;font-weight:bold;font-size:11px;">📏 ${(s.distance * 1000).toFixed(0)}m</span>
            <span style="color:#999;font-size:10px;"> (${s.distance.toFixed(2)}km)</span>
            <span style="color:#2ecc71;font-size:10px;float:right;">🚶 경로</span>
          </li>`;
        });
      }
      popupContent += '</ul></div>';

      clickMarker.bindPopup(popupContent, { maxWidth: 320 }).openPopup();

      // 버튼 복원
      btn.disabled = false;
      btn.innerHTML = '<span class="icon">📍</span><span>현재 위치</span>';
    },
    (error) => {
      let msg = '위치를 가져올 수 없습니다.';
      if (error.code === 1) msg = '위치 권한이 거부되었습니다.';
      else if (error.code === 2) msg = '위치 정보를 사용할 수 없습니다.';
      else if (error.code === 3) msg = '위치 요청 시간이 초과되었습니다.';
      alert(msg);
      btn.disabled = false;
      btn.innerHTML = '<span class="icon">📍</span><span>현재 위치</span>';
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
  );
}

// 컨텍스트 메뉴 관련 변수
const contextMenu = document.getElementById('context-menu');
let pendingClickLat = null;
let pendingClickLng = null;

// 컨텍스트 메뉴 표시
function showContextMenu(x, y, lat, lng) {
  pendingClickLat = lat;
  pendingClickLng = lng;
  contextMenu.style.left = x + 'px';
  contextMenu.style.top = y + 'px';
  contextMenu.style.display = 'block';
}

// 컨텍스트 메뉴 숨기기
function hideContextMenu() {
  contextMenu.style.display = 'none';
}

// 근처 학교 검색 실행 (컨텍스트 메뉴에서 호출)
function searchNearbySchools() {
  hideContextMenu();
  if (pendingClickLat === null || pendingClickLng === null) return;

  const clickLat = pendingClickLat;
  const clickLng = pendingClickLng;
  currentRadius = 1; // 기본 반경 1km로 초기화

  // 현재 클릭 위치 저장 (경로 표시용)
  currentClickLat = clickLat;
  currentClickLng = clickLng;

  // 기존 경로 제거
  clearRoute();

  // 기존 마커와 원 제거
  if (clickMarker) {
    map.removeLayer(clickMarker);
  }
  if (radiusCircle) {
    map.removeLayer(radiusCircle);
  }

  // 현재 필터 상태에 맞는 학교만 필터링
  let filteredSchools = schools;
  if (activeType !== 'all') {
    filteredSchools = filteredSchools.filter(s => s.school_type === activeType);
  }

  // 반경 내 학교 찾기 및 거리 계산
  const nearbySchools = filteredSchools
    .map(s => ({
      ...s,
      distance: haversineDistance(clickLat, clickLng, s.lat, s.lng)
    }))
    .filter(s => s.distance <= currentRadius)
    .sort((a, b) => a.distance - b.distance);

  // 반경 원 그리기
  radiusCircle = L.circle([clickLat, clickLng], {
    radius: currentRadius * 1000,
    color: '#ff6b6b',
    fillColor: '#ff6b6b',
    fillOpacity: 0.1,
    weight: 2,
    dashArray: '5, 5'
  }).addTo(map);

  // 클릭 위치에 마커 추가
  clickMarker = L.marker([clickLat, clickLng], {
    icon: L.divIcon({
      className: 'click-marker',
      html: `<div style="width:20px;height:20px;border-radius:50%;background:#ff6b6b;border:3px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;"><span style="color:#fff;font-size:10px;font-weight:bold;">📍</span></div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10],
    })
  }).addTo(map);

  // 팝업 내용 생성
  const typeLabel = activeType === 'all' ? '전체' :
                    activeType === 'elementary' ? '초등학교' :
                    activeType === 'middle' ? '중학교' : '고등학교';

  let popupContent = `<div style="max-height:350px;overflow-y:auto;min-width:220px;">`;
  popupContent += `<strong style="color:#ff6b6b;">📍 주변 학교 검색</strong><br>`;
  popupContent += `<span style="font-size:11px;color:#666;">위치: ${clickLat.toFixed(5)}, ${clickLng.toFixed(5)}</span><br>`;
  popupContent += `<span style="font-size:11px;color:#666;">필터: ${typeLabel}</span>`;
  popupContent += `<hr style="margin:6px 0;">`;

  // 반경 슬라이더
  popupContent += `<div style="margin-bottom:8px;">`;
  popupContent += `<label style="font-size:11px;color:#666;">반경: <strong id="radius-label">${currentRadius}km</strong></label>`;
  popupContent += `<input type="range" id="radius-slider" min="0.5" max="3" step="0.5" value="${currentRadius}"
    style="width:100%;margin-top:4px;cursor:pointer;"
    oninput="document.getElementById('radius-label').textContent=this.value+'km'; updateRadius(parseFloat(this.value));">`;
  popupContent += `<div style="display:flex;justify-content:space-between;font-size:9px;color:#999;"><span>500m</span><span>1.5km</span><span>3km</span></div>`;
  popupContent += `</div>`;
  popupContent += `<hr style="margin:6px 0;">`;

  popupContent += `<p style="font-size:12px;margin-bottom:6px;" id="nearby-count"><strong>${nearbySchools.length}개교</strong> 발견</p>`;
  popupContent += `<ul id="nearby-school-list" style="list-style:none;padding:0;margin:0;max-height:180px;overflow-y:auto;">`;

  if (nearbySchools.length === 0) {
    popupContent += `<li style="color:#999;font-size:12px;padding:8px 0;">반경 내 학교가 없습니다.</li>`;
  } else {
    nearbySchools.forEach(s => {
      const typeColor = s.school_type === 'elementary' ? '#4a90d9' :
                        s.school_type === 'middle' ? '#e67e22' : '#8e44ad';
      const typeShort = s.school_type === 'elementary' ? '초' :
                        s.school_type === 'middle' ? '중' : '고';
      const escapedName = s.name.replace(/'/g, "\\'");
      const fundColor = s.type === '사립' ? '#e74c3c' : '#27ae60';
      const fundLabel = s.type || '공립';
      popupContent += `<li onclick="showWalkingRoute(${s.lat}, ${s.lng}, '${escapedName}')" style="padding:6px 4px;border-bottom:1px solid #eee;font-size:12px;cursor:pointer;transition:background 0.2s;" onmouseover="this.style.background='#e8f8f0'" onmouseout="this.style.background=''">
        <span style="background:${typeColor};color:#fff;padding:1px 4px;border-radius:3px;font-size:10px;margin-right:2px;">${typeShort}</span>
        <span style="background:${fundColor};color:#fff;padding:1px 4px;border-radius:3px;font-size:9px;">${fundLabel}</span>
        ${s.name}
        <br><span style="color:#ff6b6b;font-weight:bold;font-size:11px;">📏 ${(s.distance * 1000).toFixed(0)}m</span>
        <span style="color:#999;font-size:10px;"> (${s.distance.toFixed(2)}km)</span>
        <span style="color:#2ecc71;font-size:10px;float:right;">🚶 경로</span>
      </li>`;
    });
  }
  popupContent += `</ul></div>`;

  clickMarker.bindPopup(popupContent, { maxWidth: 320 }).openPopup();
}

// 지도 우클릭 이벤트 핸들러 (컨텍스트 메뉴 표시)
map.on('contextmenu', function(e) {
  e.originalEvent.preventDefault();
  const containerPoint = map.latLngToContainerPoint(e.latlng);
  showContextMenu(containerPoint.x, containerPoint.y, e.latlng.lat, e.latlng.lng);
});

// 지도 클릭 시 컨텍스트 메뉴 숨기기
map.on('click', function() {
  hideContextMenu();
});

// 페이지 클릭 시 컨텍스트 메뉴 숨기기
document.addEventListener('click', function(e) {
  if (!contextMenu.contains(e.target)) {
    hideContextMenu();
  }
});
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
