#!/usr/bin/env python3
"""서울 초·중·고 학교 지도 앱 단위 테스트"""

import json
from collections import Counter

from app import app, load_schools


def expected_counts():
    schools = load_schools()
    counts = Counter(s["school_type"] for s in schools)
    districts = Counter(s["district"] for s in schools)
    return schools, counts, districts


def assert_ok(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    schools, counts, districts = expected_counts()
    client = app.test_client()

    # 전체 API
    resp = client.get("/api/schools")
    assert_ok(resp.status_code == 200, f"/api/schools status {resp.status_code}")
    data = resp.get_json()
    assert_ok(data["count"] == len(schools), f"count mismatch: {data['count']} != {len(schools)}")
    assert_ok(data["elementary_count"] == counts["elementary"], "elementary_count mismatch")
    assert_ok(data["middle_count"] == counts["middle"], "middle_count mismatch")
    assert_ok(data["high_count"] == counts["high"], "high_count mismatch")
    assert_ok("강남구" in data["districts"], "district list missing 강남구")

    # 필터 API
    for school_type in ("elementary", "middle", "high"):
        resp = client.get(f"/api/schools?type={school_type}")
        assert_ok(resp.status_code == 200, f"/api/schools?type={school_type} status {resp.status_code}")
        d = resp.get_json()
        assert_ok(d["count"] == counts[school_type], f"{school_type} count mismatch")
        assert_ok(all(s["school_type"] == school_type for s in d["schools"]), f"{school_type} filter leaked wrong type")

    # 구 필터
    gu = "강남구"
    resp = client.get(f"/api/schools?district={gu}")
    assert_ok(resp.status_code == 200, f"district filter status {resp.status_code}")
    d = resp.get_json()
    assert_ok(d["count"] == districts[gu], f"district count mismatch: {d['count']} != {districts[gu]}")
    assert_ok(all(s["district"] == gu for s in d["schools"]), "district filter leaked wrong district")

    # 복합 필터
    resp = client.get(f"/api/schools?type=high&district={gu}")
    assert_ok(resp.status_code == 200, f"combined filter status {resp.status_code}")
    d = resp.get_json()
    expected_combo = sum(1 for s in schools if s["school_type"] == "high" and s["district"] == gu)
    assert_ok(d["count"] == expected_combo, f"combined filter mismatch: {d['count']} != {expected_combo}")
    assert_ok(all(s["school_type"] == "high" and s["district"] == gu for s in d["schools"]), "combined filter leaked wrong rows")

    print("모든 단위 테스트 통과")
    print(json.dumps({
        "total": len(schools),
        "counts": dict(counts),
        "district_sample": {gu: districts[gu]},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
