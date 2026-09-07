#!/usr/bin/env python3
"""서울 초·중·고 학교 위치 데이터 전처리"""

import csv
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SRC = BASE_DIR / "data" / "한국교육시설안전원_초중등학교위치.csv"
OUTS = {
    "초등학교": BASE_DIR / "data" / "seoul_elementary.json",
    "중학교": BASE_DIR / "data" / "seoul_middle.json",
    "고등학교": BASE_DIR / "data" / "seoul_high.json",
}
TYPE_MAP = {
    "초등학교": "elementary",
    "중학교": "middle",
    "고등학교": "high",
}


def extract_district(address: str) -> str:
    if not address:
        return "기타"
    m = re.search(r"서울특별시\s+([^\s]+)", address)
    return m.group(1) if m else "기타"


def normalize(row: dict, school_type: str) -> dict:
    district = extract_district(row.get("소재지도로명주소", "") or row.get("소재지지번주소", ""))
    return {
        "id": row.get("학교ID", "").strip(),
        "name": row.get("학교명", "").strip(),
        "school_type": school_type,
        "district": district,
        "address_road": row.get("소재지도로명주소", "").strip(),
        "address_jiban": row.get("소재지지번주소", "").strip(),
        "lat": float(row["위도"]) if row.get("위도") else None,
        "lng": float(row["경도"]) if row.get("경도") else None,
        "established": row.get("설립일자", "").strip(),
        "type": row.get("설립형태", "").strip(),
    }


def main() -> None:
    rows = list(csv.DictReader(SRC.open("r", encoding="utf-8-sig")))
    print(f"전체 행수: {len(rows)}")

    for label, out_path in OUTS.items():
        school_type = TYPE_MAP[label]
        subset = [
            normalize(r, school_type)
            for r in rows
            if r.get("시도교육청명", "").strip() == "서울특별시교육청"
            and r.get("학교급구분", "").strip() == label
            and r.get("위도")
            and r.get("경도")
        ]
        out_path.write_text(json.dumps(subset, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{label}: {len(subset)}개교 -> {out_path.name}")

    print("완료")


if __name__ == "__main__":
    main()
