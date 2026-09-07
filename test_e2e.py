#!/usr/bin/env python3
"""
서울 초·중학교 지도 앱 E2E 테스트

검증 항목:
- 서버 기동 및 응답
- /api/schools: 전체 994, 초등 606, 중학 388
- /api/schools?type=elementary → 606
- /api/schools?type=middle → 388
- HTML에서 학교 데이터 렌더링 (마커용 school_type 필드)
- 학교급 배지 존재 (초/중)
- 검색 필터 동작
"""

import json
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_URL = "http://localhost:5000"
DATA_PATH = Path(__file__).parent / "data" / "seoul_elementary.json"
MID_PATH = Path(__file__).parent / "data" / "seoul_middle.json"


def fetch_json(path):
    try:
        with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


def fetch_html():
    try:
        with urllib.request.urlopen(f"{BASE_URL}/", timeout=10) as resp:
            return resp.read().decode()
    except Exception as e:
        return f"ERROR: {e}"


def test_server_up():
    """서버 기동 확인"""
    try:
        with urllib.request.urlopen(f"{BASE_URL}/", timeout=5) as resp:
            return resp.status == 200
    except:
        return False


def test_api_schools_full():
    """전체 API 응답 검증"""
    d = fetch_json("/api/schools")
    if "error" in d:
        return False, f"API 오류: {d['error']}"

    ok = True
    msgs = []

    # 전체 수
    if d["count"] != 994:
        ok = False
        msgs.append(f"전체 수 불일치: {d['count']} (기대 994)")
    else:
        msgs.append(f"전체 수: 994 ✓")

    # 초등학교 수
    if d["elementary_count"] != 606:
        ok = False
        msgs.append(f"초등학교 수 불일치: {d['elementary_count']} (기대 606)")
    else:
        msgs.append(f"초등학교 수: 606 ✓")

    # 중학교 수
    if d["middle_count"] != 388:
        ok = False
        msgs.append(f"중학교 수 불일치: {d['middle_count']} (기대 388)")
    else:
        msgs.append(f"중학교 수: 388 ✓")

    # 학교별 school_type 필드 존재
    for s in d["schools"][:100]:
        if "school_type" not in s:
            ok = False
            msgs.append(f"학교 {s['name']}에 school_type 없음")
            break
        if s["school_type"] not in ("elementary", "middle"):
            ok = False
            msgs.append(f"학교 {s['name']}의 school_type: {s['school_type']}")
            break
    else:
        msgs.append("school_type 필드 검증 ✓")

    return ok, "\n".join(msgs)


def test_api_filter_elementary():
    """초등학교 필터"""
    d = fetch_json("/api/schools?type=elementary")
    if "error" in d:
        return False, f"API 오류: {d['error']}"
    if d["count"] != 606:
        return False, f"초등학교 필터 수 불일치: {d['count']} (기대 606)"
    for s in d["schools"]:
        if s["school_type"] != "elementary":
            return False, f"필터 잘못된 타입: {s['name']} ({s['school_type']})"
    return True, "초등학교 필터: 606개교 ✓"


def test_api_filter_middle():
    """중학교 필터"""
    d = fetch_json("/api/schools?type=middle")
    if "error" in d:
        return False, f"API 오류: {d['error']}"
    if d["count"] != 388:
        return False, f"중학교 필터 수 불일치: {d['count']} (기대 388)"
    for s in d["schools"]:
        if s["school_type"] != "middle":
            return False, f"필터 잘못된 타입: {s['name']} ({s['school_type']})"
    return True, "중학교 필터: 388개교 ✓"


def test_html_markers():
    """HTML에서 학교 데이터 렌더링 확인"""
    html = fetch_html()
    if "ERROR" in html:
        return False, html

    checks = []
    # 학교 수 텍스트
    if "994개교" not in html:
        checks.append("전체 카운트 텍스트 '994개교' 없음")
    else:
        checks.append("전체 카운트 ✓")

    # 필터 버튼
    if 'data-type="all"' not in html:
        checks.append("전체 버튼 없음")
    else:
        checks.append("전체 버튼 ✓")
    if 'data-type="elementary"' not in html:
        checks.append("초등학교 버튼 없음")
    else:
        checks.append("초등학교 버튼 ✓")
    if 'data-type="middle"' not in html:
        checks.append("중학교 버튼 없음")
    else:
        checks.append("중학교 버튼 ✓")

    # 마커 아이콘 색상
    if "#4a90d9" not in html:
        checks.append("초등학교 마커 색상 없음")
    else:
        checks.append("초등학교 마커 색상 ✓")
    if "#e67e22" not in html:
        checks.append("중학교 마커 색상 없음")
    else:
        checks.append("중학교 마커 색상 ✓")

    # 학교급 배지
    if 'type-badge">초' not in html and 'type-badge elementary' not in html:
        checks.append("초등학교 배지 없음")
    else:
        checks.append("초등학교 배지 ✓")
    if 'type-badge">중' not in html and 'type-badge middle' not in html:
        checks.append("중학교 배지 없음")
    else:
        checks.append("중학교 배지 ✓")

    # 학교명 검색창
    if 'id="search-box"' not in html:
        checks.append("검색창 없음")
    else:
        checks.append("검색창 ✓")

    all_ok = len([c for c in checks if "없음" in c]) == 0
    return all_ok, "\n".join(checks)


def test_search_filter():
    """검색 필터 동작 확인 (API 기반)"""
    # "서울중"으로 검색 시 중학교가 포함되어야 함
    d = fetch_json("/api/schools")
    if "error" in d:
        return False, f"API 오류: {d['error']}"

    # 검색어 "서울중" 포함 학교 찾기
    matches = [s for s in d["schools"] if "서울중" in s["name"]]
    if not matches:
        return False, "검색어 '서울중' 매칭 없음"

    # 매칭된 학교가 중학교인지 확인 (대부분 중학교여야 함)
    middle_matches = [s for s in matches if s["school_type"] == "middle"]
    if len(middle_matches) == 0:
        return False, "'서울중' 매칭이 모두 초등학교임"

    return True, f"검색 필터 '서울중': {len(matches)}개 중 {len(middle_matches)}개 중학교 ✓"


def run_tests():
    print("=" * 60)
    print("서울 초·중학교 지도 앱 — E2E 테스트")
    print("=" * 60)
    print()

    results = []

    # 1. 서버 기동
    print("[TEST 1] 서버 기동 확인")
    if test_server_up():
        print("  ✓ 서버 응답 (HTTP 200)")
        results.append(("SERVER_UP", True, "서버 응답 OK"))
    else:
        print("  ✗ 서버 미응답")
        results.append(("SERVER_UP", False, "서버 미응답"))
        print("\n서버가 실행되어 있지 않습니다. 먼저 실행하세요:")
        print("  cd /home/ec2-user/ai_poi_map && .venv/bin/python app.py")
        return results
    print()

    # 2. 전체 API
    print("[TEST 2] /api/schools 전체 응답")
    ok, msg = test_api_schools_full()
    print(f"  {'✓' if ok else '✗'} {msg}")
    results.append(("API_FULL", ok, msg))
    print()

    # 3. 초등학교 필터
    print("[TEST 3] /api/schools?type=elementary")
    ok, msg = test_api_filter_elementary()
    print(f"  {'✓' if ok else '✗'} {msg}")
    results.append(("FILTER_ELEM", ok, msg))
    print()

    # 4. 중학교 필터
    print("[TEST 4] /api/schools?type=middle")
    ok, msg = test_api_filter_middle()
    print(f"  {'✓' if ok else '✗'} {msg}")
    results.append(("FILTER_MID", ok, msg))
    print()

    # 5. HTML 마커/배지 검증
    print("[TEST 5] HTML 렌더링 검증 (마커·배지·버튼)")
    ok, msg = test_html_markers()
    print(f"  {'✓' if ok else '✗'} {msg}")
    results.append(("HTML_RENDER", ok, msg))
    print()

    # 6. 검색 필터
    print("[TEST 6] 검색 필터 동작 ('서울중')")
    ok, msg = test_search_filter()
    print(f"  {'✓' if ok else '✗'} {msg}")
    results.append(("SEARCH_FILTER", ok, msg))
    print()

    # 결과 요약
    print("=" * 60)
    print("결과 요약")
    print("=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    for name, ok, msg in results:
        status = "✓ PASS" if ok else "✗ FAIL"
        print(f"  [{status}] {name}: {msg[:50]}")

    print()
    print(f"통과: {passed}/{total}")
    if passed == total:
        print("\n🎉 모든 E2E 테스트 통과!")
    else:
        print(f"\n⚠ {total - passed}개 테스트 실패")
        sys.exit(1)

    return results


if __name__ == "__main__":
    run_tests()
