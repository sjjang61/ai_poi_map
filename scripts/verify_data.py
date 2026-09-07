#!/usr/bin/env python3
"""서울 초·중·고 학교 데이터 검증 스크립트"""

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path("/home/ec2-user/ai_poi_map/data")
FILES = {
    "elementary": BASE / "seoul_elementary.json",
    "middle": BASE / "seoul_middle.json",
    "high": BASE / "seoul_high.json",
}
EXPECTED = {
    "elementary": 606,
    "middle": 388,
    "high": 319,
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    print("=== 데이터 검증 ===")
    totals = {}
    all_schools = []

    for school_type, path in FILES.items():
        data = load(path)
        totals[school_type] = len(data)
        all_schools.extend(data)
        coords = [s for s in data if s.get("lat") and s.get("lng")]
        districts = Counter(s["district"] for s in data)

        print(f"{school_type}: {len(data)}개교 (좌표 {len(coords)}/{len(data)})")
        print(f"  예상 수: {EXPECTED[school_type]}개교")
        print(f"  상위 5개 구: {districts.most_common(5)}")
        print(f"  샘플 2개: {data[:2][0]['name']} / {data[:2][1]['name']}")
        print()

    total = sum(totals.values())
    print(f"합계: {total}개교")
    print("구 분포 상위 10:")
    gu_counter = Counter(s["district"] for s in all_schools)
    for gu, n in gu_counter.most_common(10):
        print(f"  {gu}: {n}")

    # 무결성 체크
    ok = True
    for school_type, expected in EXPECTED.items():
        if totals[school_type] != expected:
            ok = False
            print(f"[FAIL] {school_type} 수 불일치: {totals[school_type]} != {expected}")

    if total != sum(EXPECTED.values()):
        ok = False
        print(f"[FAIL] 전체 수 불일치: {total} != {sum(EXPECTED.values())}")

    for school_type in FILES:
        data = load(FILES[school_type])
        if any(not s.get("district") for s in data):
            ok = False
            print(f"[FAIL] {school_type} district 누락")
        if any(not s.get("lat") or not s.get("lng") for s in data):
            ok = False
            print(f"[FAIL] {school_type} 좌표 누락")

    if ok:
        print("\n=== 모든 검증 통과 ===")
    else:
        print("\n=== 검증 실패 ===")
        sys.exit(1)


if __name__ == "__main__":
    main()
