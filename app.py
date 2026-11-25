import os, json
from pathlib import Path
import pandas as pd
import streamlit as st
import folium, requests
from geopy.distance import geodesic
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from google import genai
from google.genai import types
import streamlit.components.v1 as components

BASE=Path(__file__).parent
DATA=BASE/"data"
MODEL="gemini-3.1-flash-lite"
st.set_page_config(page_title="안심길 | 건강·안전 도우미",page_icon="🧭",layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700;800&display=swap');
html,body,[class*="css"]{font-family:Pretendard,sans-serif}
.block-container{padding-top:1.5rem;max-width:1280px}
.hero{padding:28px 30px;border-radius:22px;background:linear-gradient(115deg,#102c4e,#176b70);color:white;margin-bottom:18px}
.hero h1{font-size:2rem;font-weight:800;margin:0 0 8px}.hero p{margin:0;color:#e1f1f3}
.notice{padding:14px 16px;border-radius:12px;background:#fff5e8;border-left:4px solid #e79a32;color:#533a1b}
</style>""",unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load_csv(pattern):
    fs=list(DATA.glob(pattern))
    if not fs:return pd.DataFrame()
    for enc in ("utf-8-sig","cp949","euc-kr","utf-8"):
        try:return pd.read_csv(fs[0],encoding=enc,low_memory=False)
        except Exception:pass
    return pd.DataFrame()
hosp=load_csv("1.병원정보서비스*.csv")
pharm=load_csv("2.약국정보서비스*.csv")
facilities=load_csv("3.의료기관별상세정보서비스_01*.csv")
details=load_csv("4.의료기관별상세정보서비스_02*.csv")
specialties=load_csv("5.의료기관별상세정보서비스_03*.csv")
equipment=load_csv("7.의료기관별상세정보서비스_05*.csv")
special_care=load_csv("10.의료기관별상세정보서비스_08*.csv")
special_hospitals=load_csv("11.의료기관별상세정보서비스_09*.csv")
other_staff=load_csv("12.의료기관별상세정보서비스_10*.csv")
police_sub=load_csv("*지구대 파출소 주소*.csv")
police_center=load_csv("*치안센터 주소*.csv")
police_station=load_csv("*경찰서 명칭 및 주소*.csv")
fire_counts=load_csv("*전국소방관서*.csv")

def s(v): return "" if pd.isna(v) else str(v).strip()
def csv_points(df,kind):
    out=[]
    if df.empty:return out
    for _,r in df.iterrows():
        try:
            y=float(r["좌표(Y)"]);x=float(r["좌표(X)"])
            if -90<=y<=90 and -180<=x<=180:
                out.append(dict(name=s(r.get("요양기관명",kind)),address=s(r.get("주소","")),phone=s(r.get("전화번호","")),lat=y,lon=x,kind=kind,hours="운영시간 정보 미포함"))
        except Exception:continue
    return out

def osm_points(lat,lon,kind):
    amenity="fire_station" if kind=="소방서" else "police"
    q=f'[out:json][timeout:15];(node["amenity"="{amenity}"](around:10000,{lat},{lon});way["amenity"="{amenity}"](around:10000,{lat},{lon}););out center tags;'
    try:
        r=requests.post("https://overpass-api.de/api/interpreter",data=q,timeout=20);r.raise_for_status()
        out=[]
        for e in r.json().get("elements",[]):
            t=e.get("tags",{}); c=e.get("center",{})
            y=e.get("lat",c.get("lat"));x=e.get("lon",c.get("lon"))
            if y is None or x is None:continue
            out.append(dict(name=t.get("name",kind),address=t.get("addr:full",t.get("addr:street","주소 정보 없음")),phone=t.get("phone",""),lat=float(y),lon=float(x),kind=kind,hours=t.get("opening_hours","정보 없음")))
        return out
    except Exception:return []

def ai_answer(symptoms,duration,age,sex,extra):
    key=st.secrets.get("GEMINI_API_KEY",os.getenv("GEMINI_API_KEY",""))
    if not key:raise ValueError("GEMINI_API_KEY가 없습니다. 환경변수 또는 .streamlit/secrets.toml에 설정하세요.")
    client=genai.Client(api_key=key)
    prompt=f"""한국 사용자를 위한 안전한 건강정보 안내 도우미로 답하세요. 확진·처방하지 마세요.
응답은 한국어로: 1) 119/응급실이 필요한 위험 신호 2) 가능한 원인 후보 2~4개와 근거·불확실성(확률 단정 금지) 3) 권장 진료과와 진료 시점 4) 일반적인 자가 대처 및 피할 행동 5) 의료진에게 전달할 정보.
심한 호흡곤란, 의식저하, 흉통, 한쪽 마비/말 어눌함, 심한 출혈, 경련, 아나필락시스 등 응급 징후면 AI 안내보다 119가 우선임을 첫머리에 명시. 약 용량을 임의로 만들지 말 것.
나이:{age or '미입력'}, 성별:{sex}, 지속기간:{duration}, 추가정보:{extra or '없음'}, 증상:{symptoms}"""
    return client.models.generate_content(model=MODEL,contents=prompt,config=types.GenerateContentConfig(temperature=0.2)).text

st.markdown('<div class="hero"><h1>🧭 안심길</h1><p>건강 상황별 대처부터 주변 의료·안전기관 찾기까지 한 곳에서</p></div>',unsafe_allow_html=True)
st.markdown('<div class="notice"><b>긴급 상황인가요?</b> 생명·신체에 즉각적인 위험이 있으면 이 서비스를 기다리지 말고 <b>119(구급·소방)</b> 또는 <b>112(경찰)</b>에 바로 전화하세요. 이 앱은 신고를 직접 접수하거나 출동시키지 않습니다.</div>',unsafe_allow_html=True)
t1,t2,t3=st.tabs(["🩺 증상별 대처 안내","📍 주변 기관 지도","🚨 긴급 위치 전달"])
with t1:
    st.subheader("증상별 대처 및 진료 방향 안내")
    c1,c2,c3=st.columns([2,1,1])
    with c1:symptoms=st.text_area("현재 증상",placeholder="예: 어제부터 목이 아프고 열이 38도이며 기침이 납니다.",height=110)
    with c2:age=st.text_input("나이(선택)",placeholder="예: 32세")
    with c3:sex=st.selectbox("성별(선택)",["미입력","여성","남성","기타"])
    duration=st.selectbox("증상 지속 기간",["","갑자기 발생","몇 시간","1~2일","3~7일","1주 이상","반복적으로 발생"])
    extra=st.text_input("기저질환·복용약·알레르기 등(선택)")
    if st.button("AI 대처 방법 및 진료과 안내 받기",type="primary",use_container_width=True):
        if not symptoms.strip():st.warning("증상을 입력해 주세요.")
        else:
            with st.spinner("안전한 건강정보를 정리하고 있습니다..."):
                try:st.session_state["answer"]=ai_answer(symptoms,duration,age,sex,extra)
                except Exception as e:st.error(str(e))
    if st.session_state.get("answer"):
        st.markdown("#### 안내 결과");st.markdown(st.session_state["answer"])
        st.caption("AI 참고 정보이며 진단·처방이 아닙니다. 증상이 심해지거나 걱정되면 의료진에게 상담하세요.")
with t2:
    st.subheader("주변 의료·긴급 기관 찾기")
    st.caption("병원·약국은 업로드 CSV 좌표, 경찰·소방은 OpenStreetMap 공개 데이터를 이용합니다.")
    loc=streamlit_geolocation()
    ly=loc.get("latitude") if isinstance(loc,dict) else None
    lx=loc.get("longitude") if isinstance(loc,dict) else None
    if ly and lx:st.success("브라우저 현재 위치를 확인했습니다.")
    a,b,c=st.columns(3)
    with a:lat=st.number_input("위도",value=float(ly or 36.3504),format="%.6f")
    with b:lon=st.number_input("경도",value=float(lx or 127.3845),format="%.6f")
    with c:radius=st.selectbox("검색 반경", [2,5,10,20],index=1,format_func=lambda z:f"{z} km")
    cats=st.multiselect("표시할 기관",["병원","약국","경찰","소방서"],default=["병원","약국"])
    specialty_options=sorted(specialties["진료과목코드명"].dropna().astype(str).unique().tolist()) if not specialties.empty else []
    chosen_specialty=st.selectbox("병원 진료과목 필터",["전체 진료과목"]+specialty_options) if "병원" in cats and specialty_options else None
    if chosen_specialty=="전체 진료과목":chosen_specialty=None
    if st.button("주변 기관 검색",type="primary"):
        pts=[]
        if "병원" in cats:
            hospital_rows=hosp
            if chosen_specialty and not specialties.empty:
                matching_ids=set(specialties.loc[specialties["진료과목코드명"].astype(str)==chosen_specialty,"암호화요양기호"].astype(str))
                hospital_rows=hosp[hosp["암호화요양기호"].astype(str).isin(matching_ids)]
            pts+=csv_points(hospital_rows,"병원")
        if "약국" in cats:pts+=csv_points(pharm,"약국")
        if "경찰" in cats:pts+=osm_points(lat,lon,"경찰")
        if "소방서" in cats:pts+=osm_points(lat,lon,"소방서")
        near=[]
        for p in pts:
            d=geodesic((lat,lon),(p["lat"],p["lon"])).km
            if d<=radius:p["distance"]=d;near.append(p)
        near.sort(key=lambda z:z["distance"])
        # 상세 CSV를 암호화 요양기관기호로 연결해 병원 결과에 추가 정보 부착
        if not hosp.empty:
            name_to_key=dict(zip(hosp["요양기관명"].astype(str),hosp["암호화요양기호"].astype(str)))
            for p in near:
                if p["kind"]!="병원":continue
                key=name_to_key.get(p["name"],"")
                def matching(frame):
                    if frame.empty:return pd.DataFrame()
                    return frame[frame["암호화요양기호"].astype(str)==key]
                sd=matching(specialties); dd=matching(details); ed=matching(equipment)
                cd=matching(special_care); hd=matching(special_hospitals); fd=matching(facilities); od=matching(other_staff)
                p["specialties"]=", ".join(sd["진료과목코드명"].dropna().astype(str).unique()[:10]) if not sd.empty else "정보 없음"
                p["equipment"]=", ".join((ed["장비코드명"].astype(str)+" "+ed["장비대수"].astype(str)+"대").tolist()[:6]) if not ed.empty else "정보 없음"
                p["special_care"]=", ".join(cd["검색코드명"].dropna().astype(str).unique()[:6]) if not cd.empty else "정보 없음"
                p["designated"]=", ".join(hd["검색코드명"].dropna().astype(str).unique()[:4]) if not hd.empty else "해당 정보 없음"
                p["staff"]=", ".join((od["기타인력코드명"].astype(str)+" "+od["기타인력수"].astype(str)+"명").tolist()[:6]) if not od.empty else "정보 없음"
                if not dd.empty:
                    d=dd.iloc[0]
                    p["hours"]="평일 접수 "+s(d.get("접수시간_평일","정보 없음"))+" / 토요일 "+s(d.get("접수시간_토요일","정보 없음"))
                    p["closed"]="일요일 "+s(d.get("휴진안내_일요일","정보 없음"))+" / 공휴일 "+s(d.get("휴진안내_공휴일","정보 없음"))
                if not fd.empty:
                    f=fd.iloc[0]
                    p["facility"]=f"응급실 {s(f.get('응급실병상수',0))}병상 · 수술실 {s(f.get('수술실병상수',0))}실 · 성인중환자실 {s(f.get('성인중환자병상수',0))}병상"
        st.session_state["nearby"]=near;st.session_state["center"]=(lat,lon)
    near=st.session_state.get("nearby",[])
    if near:
        m=folium.Map(location=st.session_state.get("center",(lat,lon)),zoom_start=13,control_scale=True)
        folium.Marker(st.session_state.get("center",(lat,lon)),tooltip="내 위치",icon=folium.Icon(color="red")).add_to(m)
        colors={"병원":"blue","약국":"green","경찰":"darkblue","소방서":"orange"}
        for p in near:
            html=f"<b>{p['name']}</b><br>{p['kind']} · {p['distance']:.1f}km<br>{p['address']}<br>전화: {p['phone'] or '정보 없음'}<br>운영: {p['hours']}"
            folium.Marker([p["lat"],p["lon"]],tooltip=p["name"],popup=folium.Popup(html,max_width=300),icon=folium.Icon(color=colors[p["kind"]])).add_to(m)
        st_folium(m,use_container_width=True,height=460)
        st.markdown(f"**검색 결과 {len(near)}곳**")
        for p in near[:60]:
            with st.container(border=True):
                st.markdown(f"**{p['name']}** · {p['kind']} · {p['distance']:.1f} km")
                st.caption(f"{p['address']} | 전화: {p['phone'] or '정보 없음'} | 운영시간: {p['hours']}")
                if p["kind"]=="병원":
                    st.caption("진료과목: "+p.get("specialties","정보 없음"))
                    st.caption("진료시간: "+p.get("hours","정보 없음")+" · 휴진: "+p.get("closed","정보 없음"))
                    st.caption("의료장비: "+p.get("equipment","정보 없음"))
                    st.caption("특수진료: "+p.get("special_care","정보 없음")+" · 전문병원: "+p.get("designated","정보 없음"))
                    st.caption("시설: "+p.get("facility","정보 없음")+" · 기타 인력: "+p.get("staff","정보 없음"))
                if p["kind"]=="약국":st.caption("💊 품목별 실시간 재고/판매 데이터 미연계 — 방문 전 전화 확인 필요")
    elif "nearby" in st.session_state:st.info("검색 결과가 없습니다. 검색 반경을 넓혀 보세요.")
    st.caption("CSV에 운영시간이 없거나 일부 정보만 있어 영업 여부를 보장하지 않습니다. 좌표·정보의 최신성을 전화로 확인하세요.")
with t3:
    st.subheader("긴급 신고 시 현재 위치 전달")
    st.warning("위치 문구 생성과 음성 읽기 보조 기능입니다. 실제 신고 접수·문자 발송은 하지 않습니다.")
    loc2=streamlit_geolocation()
    yy=loc2.get("latitude") if isinstance(loc2,dict) else None
    xx=loc2.get("longitude") if isinstance(loc2,dict) else None
    if yy and xx:
        st.success("현재 위치 좌표를 가져왔습니다.")
        yy=st.number_input("위도",value=float(yy),format="%.6f",key="em_y")
        xx=st.number_input("경도",value=float(xx),format="%.6f",key="em_x")
    else:
        a,b=st.columns(2)
        with a:yy=st.number_input("위도",value=36.3504,format="%.6f",key="em_y")
        with b:xx=st.number_input("경도",value=127.3845,format="%.6f",key="em_x")
    msg=f"제 현재 위치 좌표는 위도 {yy:.6f}, 경도 {xx:.6f}입니다. 주소 확인을 부탁드립니다."
    st.text_area("신고 시 전달할 위치 문구",value=msg,height=80)
    a,b,c=st.columns(3)
    with a:st.link_button("📞 112 경찰 신고","tel:112",use_container_width=True)
    with b:st.link_button("🚑 119 구급·소방","tel:119",use_container_width=True)
    with c:st.link_button("🗺️ 지도에서 위치 보기",f"https://www.google.com/maps?q={yy},{xx}",use_container_width=True)
    components.html(f"""<button onclick='const u=new SpeechSynthesisUtterance({json.dumps(msg,ensure_ascii=False)});speechSynthesis.cancel();speechSynthesis.speak(u)' style="padding:12px 18px;border:0;border-radius:10px;background:#176b70;color:white;font-weight:700">🔊 위치 문구 음성으로 읽기</button>""",height=55)
    st.caption("좌표가 도로명 주소를 보장하지 않습니다. 통화 중 주변 건물명·층수·출입구도 알려주세요.")
with st.sidebar:
    st.title("안심길")
    st.markdown("**빠른 연락**")
    st.link_button("112 경찰","tel:112",use_container_width=True)
    st.link_button("119 구급·소방","tel:119",use_container_width=True)
    st.divider();st.markdown("**업로드 데이터**")
    st.write(f"병원 {len(hosp):,}건 · 약국 {len(pharm):,}건")
    st.write(f"진료과목 정보 {len(specialties):,}건")
    st.write(f"의료장비 {len(equipment):,}건 · 시설 {len(facilities):,}건")
    st.write(f"특수진료 {len(special_care):,}건 · 전문병원 지정 {len(special_hospitals):,}건")
    st.write(f"기타 인력 {len(other_staff):,}건")
    st.write(f"경찰 지구대/파출소 주소 {len(police_sub):,}건")
    st.write(f"경찰 치안센터 주소 {len(police_center):,}건 · 경찰서 {len(police_station):,}건")
    st.write("소방관서 파일은 관서별 주소가 아닌 기관 수 통계")
    st.caption("파일명 기준 데이터: 2026년 9월")
