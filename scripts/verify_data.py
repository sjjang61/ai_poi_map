#!/usr/bin/env python3
"""데이터 검증 스크립트"""

import json
from pathlib import Path

elem = Path("/home/ec2-user/ai_poi_map/data/seoul_elementary.json")
middle = Path("/home/ec2-user/ai_poi_map/data/seoul_middle.json")

elem_data = json.loads(elem.read_text(encoding="utf-8"))
mid_data = json.loads(middle.read_text(encoding="utf-8"))

print("=== 데이터 검증 ===")
print(f"초등학교: {len(elem_data)}개교")
print(f"중학교: {len(mid_data)}개교")
print(f"합계: {len(elem_data) + len(mid_data)}개교")
print()

# 좌표 검증
elem_coords = [s for s in elem_data if s.get("lat") and s.get("lng")]
mid_coords = [s for s in mid_data if s.get("lat") and s.get("lng")]
print(f"초등학교 좌표 포함: {len(elem_coords)}/{len(elem_data)}")
print(f"중학교 좌표 포함: {len(mid_coords)}/{len(mid_data)}")
print()

# 학교급 타입 검증
elem_types = set(s.get("school_type") for s in elem_data)
mid_types = set(s.get("school_type") for s in mid_data)
print(f"초등학교 school_type: {elem_types}")
print(f"중학교 school_type: {mid_types}")
print()

# 샘플 출력
print("=== 초등학교 샘플 (처음 3) ===")
for s in elem_data[:3]:
    print(f"  [{s.get('school_type')}] {s['name']} | {s['address_road']} | ({s['lat']}, {s['lng']})")
print()
print("=== 중학교 샘플 (처음 3) ===")
for s in mid_data[:3]:
    print(f"  [{s.get('school_type')}] {s['name']} | {s['address_road']} | ({s['lat']}, {s['lng']})")
print()

# 좌표 범위
elem_lats = [s['lat'] for s in elem_coords]
elem_lngs = [s['lng'] for s in elem_coords]
mid_lats = [s['lat'] for s in mid_coords]
mid_lngs = [s['lng'] for s in mid_coords]
print(f"초등학교 위도: {min(elem_lats):.4f} ~ {max(elem_lats):.4f}")
print(f"초등학교 경도: {min(elem_lngs):.4f} ~ {max(elem_lngs):.4f}")
print(f"중학교 위도: {min(mid_lats):.4f} ~ {max(mid_lats):.4f}")
print(f"중학교 경도: {min(mid_lngs):.4f} ~ {max(mid_lngs):.4f}")

# 필드명 검증
print()
print("=== 필드 검증 ===")
print(f"초등학교 필드: {list(elem_data[0].keys())}")
print(f"중학교 필드: {list(mid_data[0].keys())}")

print()
print("=== 검증 완료 ===")
