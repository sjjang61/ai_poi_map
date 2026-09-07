#!/usr/bin/env python3
"""서울 중학교 위치 데이터 전처리 스크립트"""

import csv
import json
from pathlib import Path

src = Path("/home/ec2-user/ai_poi_map/data/한국교육시설안전원_초중등학교위치.csv")
out = Path("/home/ec2-user/ai_poi_map/data/seoul_middle.json")

rows = []
with src.open("r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

print(f"전체 행수: {len(rows)}")

# 서울 중학교 필터링
seoul_middle = []
for r in rows:
    if r.get("시도교육청명", "").strip() == "서울특별시교육청" and r.get("학교급구분", "").strip() == "중학교":
        seoul_middle.append({
            "id": r.get("학교ID", "").strip(),
            "name": r.get("학교명", "").strip(),
            "address_road": r.get("소재지도로명주소", "").strip(),
            "address_jiban": r.get("소재지지번주소", "").strip(),
            "lat": float(r["위도"]) if r.get("위도") else None,
            "lng": float(r["경도"]) if r.get("경도") else None,
            "established": r.get("설립일자", "").strip(),
            "type": r.get("설립형태", "").strip(),
        })

print(f"\n서울 중학교 수: {len(seoul_middle)}")

with_coord = [s for s in seoul_middle if s["lat"] is not None and s["lng"] is not None]
print(f"좌표 있는 중학교 수: {len(with_coord)}")

lats = [s["lat"] for s in with_coord]
lngs = [s["lng"] for s in with_coord]
print(f"위도 범위: {min(lats):.5f} ~ {max(lats):.5f}")
print(f"경도 범위: {min(lngs):.5f} ~ {max(lngs):.5f}")

print("\n샘플 (처음 10개):")
for s in with_coord[:10]:
    print(f"  {s['name']} | {s['address_road']} | ({s['lat']:.5f}, {s['lng']:.5f})")

out.write_text(json.dumps(with_coord, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n저장 완료: {out} ({len(with_coord)}개교)")
