#!/usr/bin/env python3
"""서울 초·중·고 학교 지도 앱 E2E 테스트"""

import json
import urllib.request
from collections import Counter
from urllib.parse import quote

from app import load_schools

BASE_URL = "http://localhost:5000"


def fetch_json(path):
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=10) as resp:
        return json.loads(resp.read().decode())


def fetch_html():
    with urllib.request.urlopen(f"{BASE_URL}/", timeout=10) as resp:
        return resp.read().decode()


def main():
    schools = load_schools()
    type_counts = Counter(s["school_type"] for s in schools)
    district_counts = Counter(s["district"] for s in schools)
    target_district = "강남구"

    print("=" * 60)
    print("서울 초·중·고 학교 지도 앱 — E2E 테스트")
    print("=" * 60)
    print()

    # 1. 서버 기동
    print("[TEST 1] 서버 기동 확인")
    root = fetch_html()
    print("  ✓ 서버 응답 (HTTP 200)")
    print()

    # 2. 전체 API 응답
    print("[TEST 2] /api/schools 전체 응답")
    d = fetch_json("/api/schools")
    assert d["count"] == len(schools), f"전체 수 불일치: {d['count']} != {len(schools)}"
    assert d["elementary_count"] == type_counts["elementary"]
    assert d["middle_count"] == type_counts["middle"]
    assert d["high_count"] == type_counts["high"]
    assert all("school_type" in s for s in d["schools"][:20])
    print(f"  ✓ 전체 {d['count']}개교 / 초 {d['elementary_count']} / 중 {d['middle_count']} / 고 {d['high_count']}")
    print()

    # 3. 학교급 필터 API
    for t in ("elementary", "middle", "high"):
        print(f"[TEST 3-{t}] /api/schools?type={t}")
        d = fetch_json(f"/api/schools?type={t}")
        assert d["count"] == type_counts[t], f"{t} count mismatch: {d['count']} != {type_counts[t]}"
        assert all(s["school_type"] == t for s in d["schools"])
        print(f"  ✓ {t}: {d['count']}개교")
        print()

    # 4. 구 필터 API
    print(f"[TEST 4] /api/schools?district={target_district}")
    d = fetch_json(f"/api/schools?district={quote(target_district)}")
    assert d["count"] == district_counts[target_district], f"district mismatch: {d['count']} != {district_counts[target_district]}"
    assert all(s["district"] == target_district for s in d["schools"])
    print(f"  ✓ {target_district}: {d['count']}개교")
    print()

    # 5. 복합 필터 API
    print(f"[TEST 5] /api/schools?type=high&district={target_district}")
    d = fetch_json(f"/api/schools?type=high&district={quote(target_district)}")
    expected_combo = sum(1 for s in schools if s["school_type"] == "high" and s["district"] == target_district)
    assert d["count"] == expected_combo, f"combined mismatch: {d['count']} != {expected_combo}"
    assert all(s["school_type"] == "high" and s["district"] == target_district for s in d["schools"])
    print(f"  ✓ 고등학교 + {target_district}: {d['count']}개교")
    print()

    # 6. HTML 렌더링 확인
    print("[TEST 6] HTML 렌더링 검증")
    checks = []
    checks.append(("전체 카운트", f"{len(schools)}개교" in root))
    checks.append(("초등학교 버튼", 'data-type="elementary"' in root))
    checks.append(("중학교 버튼", 'data-type="middle"' in root))
    checks.append(("고등학교 버튼", 'data-type="high"' in root))
    checks.append(("구 필터 select", 'id="district-select"' in root))
    checks.append(("강남구 옵션", '강남구' in root))
    checks.append(("검색창", 'id="search-box"' in root))
    checks.append(("고등학교 색상", '#8e44ad' in root))
    checks.append(("고등학교 배지", '.type-badge.high' in root))

    for label, ok in checks:
        print(f"  {'✓' if ok else '✗'} {label}")
    assert all(ok for _, ok in checks), "HTML 렌더링 체크 실패"
    print()

    # 7. 검색 필터 기준 데이터 검증 (JS와 동일한 조건)
    print("[TEST 7] 검색 필터 동작 ('강남')")
    q = "강남"
    matches = [s for s in schools if q in s["name"] or q in s["district"] or q in (s["address_road"] or "")]
    assert matches, "검색어 강남 매칭 없음"
    print(f"  ✓ 검색어 '{q}' 매칭 {len(matches)}개")
    print()

    print("=" * 60)
    print("모든 E2E 테스트 통과")


if __name__ == "__main__":
    main()
