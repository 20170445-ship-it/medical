# 안심길 — Streamlit 건강·안전 안내 앱

## 실행
1. Python 3.10+ 설치
2. `pip install -r requirements.txt`
3. Gemini API 키 설정
   - Windows PowerShell: `$env:GEMINI_API_KEY="발급받은_API_키"`
   - macOS/Linux: `export GEMINI_API_KEY="발급받은_API_키"`
   - 또는 `.streamlit/secrets.toml`에 `GEMINI_API_KEY = "..."` 입력
4. `streamlit run app.py`

Gemini 모델 ID: `gemini-3.1-flash-lite`

## 구현
- 증상 입력 후 Gemini 기반 가능한 원인 후보, 대처법, 진료과 안내
- 병원·약국 CSV 좌표 기반 지도 및 거리순 목록
- 진료과목 선택 필터 및 병원 상세정보(시설·진료시간·의료장비·특수진료·전문병원 지정·기타 인력) 연계
- OpenStreetMap Overpass 기반 주변 경찰·소방서 검색
- 브라우저 위치 권한, 112/119 전화 바로가기, 위치 문구 및 브라우저 음성 읽기

## 데이터/안전상 한계
- 약국 CSV에는 약국명·주소·전화·좌표만 있고 마스크·의약품 품목별 실시간 재고/판매 데이터가 없습니다. 재고 수량을 임의 표시하지 않습니다.
- 소방청 파일은 관서별 주소 목록이 아니라 본부별 기관 수 통계입니다. 주변 소방서는 OpenStreetMap 검색으로 보완하며 누락될 수 있습니다.
- 경찰 CSV는 주소만 포함하므로 지도는 OpenStreetMap 결과를 이용합니다. 업로드 경찰 CSV 전수 지오코딩은 하지 않습니다.
- 운영시간 정보가 CSV에 완전하게 없으므로 영업 여부를 보장하지 않습니다.
- 112/119에 실제 신고하거나 문자를 자동 발송하지 않습니다. 전화 연결·위치 문구·음성 안내만 제공합니다.
- 현재 위치 자동 수집은 브라우저 권한과 HTTPS/localhost 환경에 따라 달라집니다.
- AI는 진단·처방이 아닙니다. 응급 징후가 있으면 AI 이용보다 119 신고가 우선입니다.
- CSV 기준일은 파일명 기준 2026년 9월이며 실제 현황과 다를 수 있습니다. 이번 추가 자료의 진료과목·의료장비·특수진료·전문병원 지정·기타 인력 데이터는 암호화 요양기관기호로 병원 기본정보와 연결합니다.

배포 시 `data/` 폴더를 함께 포함하고 Streamlit Secrets에 API 키를 등록하세요. API 키를 코드나 Git에 넣지 마세요.
