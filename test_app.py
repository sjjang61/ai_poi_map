#!/usr/bin/env python3
"""서울 초등학교 지도 앱 테스트 코드"""

import json
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "seoul_elementary.json"
APP_PY = Path(__file__).parent / "app.py"


def test_data_load():
    """테스트 1: 데이터 JSON 로드 검증"""
    print("=" * 50)
    print("TEST 1: 데이터 JSON 파일 로드 검증")
    print("=" * 50)
    assert DATA_PATH.exists(), f"데이터 파일이 없음: {DATA_PATH}"
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list), "데이터가 리스트여야 함"
    assert len(data) == 606, f"606개교여야 함 (현재 {len(data)}개)"
    
    # 필드 검증
    required_fields = {"id", "name", "lat", "lng", "address_road"}
    for school in data:
        for f in required_fields:
            assert f in school, f"필드 누락: {f} in {school.get('name', '?')}"
        assert -90 <= school["lat"] <= 90, f"위도 범위 초과: {school['name']}"
        assert -180 <= school["lng"] <= 180, f"경도 범위 초과: {school['name']}"
    
    # 서울시 좌표 범위 검증
    lats = [s["lat"] for s in data]
    lngs = [s["lng"] for s in data]
    assert 37.4 <= min(lats) <= 37.7, f"서울 위도 범위 이상: {min(lats):.5f}"
    assert 37.4 <= max(lats) <= 37.7, f"서울 위도 범위 이상: {max(lats):.5f}"
    assert 126.8 <= min(lngs) <= 127.2, f"서울 경도 범위 이상: {min(lngs):.5f}"
    assert 126.8 <= max(lngs) <= 127.2, f"서울 경도 범위 이상: {max(lngs):.5f}"
    
    # 샘플 학교명 검증
    names = [s["name"] for s in data]
    assert "서울신구초등학교" in names, "서울신구초등학교가 있어야 함"
    assert "서울봉화초등학교" in names, "서울봉화초등학교가 있어야 함"
    
    print(f"  ✓ 데이터 파일 로드 OK ({len(data)}개교)")
    print(f"  ✓ 필수 필드 검증 OK")
    print(f"  ✓ 좌표 범위 검증 OK (위도 {min(lats):.4f}~{max(lats):.4f}, 경도 {min(lngs):.4f}~{max(lngs):.4f})")
    print(f"  ✓ 샘플 학교명 검증 OK")
    return True


def test_app_server():
    """테스트 2: Flask 앱 서버 기동 및 응답 검증"""
    print("\n" + "=" * 50)
    print("TEST 2: Flask 앱 서버 기동 + API 응답 검증")
    print("=" * 50)
    
    # 가상환경 파이썬 경로
    venv_python = Path(__file__).parent / ".venv" / "bin" / "python"
    python_exe = venv_python if venv_python.exists() else sys.executable
    
    # 서버 시작
    print(f"  서버 시작: {python_exe} app.py")
    proc = subprocess.Popen(
        [str(python_exe), str(APP_PY)],
        cwd=Path(__file__).parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # 기동 대기
    base_url = "http://localhost:5000"
    max_wait = 15
    started = False
    for i in range(max_wait * 2):
        time.sleep(0.5)
        try:
            resp = urllib.request.urlopen(f"{base_url}/api/schools", timeout=2)
            if resp.status == 200:
                started = True
                break
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            pass
    
    if not started:
        proc.terminate()
        raise AssertionError(f"서버가 {max_wait}초 내에 기동하지 않음")
    
    print(f"  ✓ 서버 기동 OK (localhost:5000)")
    
    try:
        # /api/schools 검증
        resp = urllib.request.urlopen(f"{base_url}/api/schools", timeout=5)
        assert resp.status == 200
        body = json.loads(resp.read().decode("utf-8"))
        assert body["count"] == 606, f"API 카운트 mismatch: {body['count']}"
        assert len(body["schools"]) == 606
        print(f"  ✓ /api/schools OK (count={body['count']})")
        
        # / (메인 페이지) 검증
        resp = urllib.request.urlopen(base_url, timeout=5)
        assert resp.status == 200
        html = resp.read().decode("utf-8")
        assert "leaflet" in html.lower(), "Leaflet 스크립트 없음"
        assert "서울 초등학교 지도" in html, "타이틀 없음"
        assert "37.54" in html, "초기 중심 좌표 없음"
        print(f"  ✓ / (메인 페이지) OK")
        
        print("\n  🎉 모든 테스트 통과!")
        print(f"  접속 URL: http://localhost:5000")
        return True
    finally:
        proc.terminate()
        proc.wait(timeout=5)
        print(f"  서버 종료")


if __name__ == "__main__":
    results = []
    try:
        results.append(("데이터 로드", test_data_load()))
    except Exception as e:
        print(f"\n❌ TEST 1 실패: {e}")
        results.append(("데이터 로드", False))
    
    try:
        results.append(("서버 기동+응답", test_app_server()))
    except Exception as e:
        print(f"\n❌ TEST 2 실패: {e}")
        results.append(("서버 기동+응답", False))
    
    print("\n" + "=" * 50)
    print("최종 결과")
    print("=" * 50)
    for name, ok in results:
        print(f"  {'✓' if ok else '❌'} {name}")
    
    all_ok = all(ok for _, ok in results)
    sys.exit(0 if all_ok else 1)
