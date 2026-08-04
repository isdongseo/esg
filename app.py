import streamlit as st

st.set_page_config(page_title="온실가스 자동 계산기", page_icon="🌍")

st.title("🌍 아이에스동서 온실가스 마법 계산기")
st.write("숫자만 입력하면 단위(TJ)가 자동으로 계산되는 마법의 웹사이트입니다!")

# 단위 변환 마법 공식 (2025년 기준)
factors = {
    "전기": 0.000010,
    "도시가스": 0.000043,
    "휘발유": 0.000033,
    "경유": 0.000038,
    "등유": 0.000037
}

# 1. 지점 고르기
location = st.selectbox("어느 지점의 데이터를 입력할까요?", 
                        ["본사/지사", "건축공사", "이천공장", "청양공장", "음성공장"])

st.subheader(f"📍 {location} 에너지 사용량 입력")

# 2. 숫자 입력하는 칸 만들기
col1, col2 = st.columns(2)
with col1:
    elec = st.number_input("전기 사용량 (kWh)", value=0)
    gasoline = st.number_input("휘발유 사용량 (L)", value=0)
    kerosene = st.number_input("등유 사용량 (L)", value=0)
with col2:
    gas = st.number_input("도시가스 사용량 (Nm3)", value=0)
    diesel = st.number_input("경유 사용량 (L)", value=0)

# 3. 계산 버튼과 마법 결과
if st.button("✨ 마법으로 계산하기"):
    st.balloons() # 축하 풍선이 날아오르는 마법!
    
    tj_elec = elec * factors["전기"]
    tj_gas = gas * factors["도시가스"]
    tj_gasoline = gasoline * factors["휘발유"]
    tj_diesel = diesel * factors["경유"]
    tj_kerosene = kerosene * factors["등유"]
    
    st.success("계산이 완료되었습니다! 👏")
    st.info(f"🔥 직접 연료 사용량(Scope 1) 변환: {tj_gas + tj_gasoline + tj_diesel + tj_kerosene:.4f} TJ")
    st.info(f"⚡ 전기 사용량(Scope 2) 변환: {tj_elec:.4f} TJ")
