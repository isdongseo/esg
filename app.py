import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO

st.set_page_config(page_title="아이에스동서 온실가스 배출량 자동 변환", layout="wide")

# ==========================================
# 1. 새로 적용할 DB 및 요청하신 8개 에너지원 세팅
# ==========================================
# DB 파일명을 새로 변경하여 기존 용수/폐기물 데이터 잔재를 완벽히 제거합니다.
conn = sqlite3.connect('esg_energy_only_v2.db', check_same_thread=False)

BRANCHES = ["본사/지사", "건축공사", "이천공장", "청양공장", "음성공장"]

# 지현 님이 정확히 요청하신 8개 항목만 지정!
METRICS = [
    "전기(소비전력기준)",
    "도시가스(LNG)",
    "휘발유",
    "경유",
    "등유",
    "프로판(LPG)",
    "천연가스(LNG)",
    "휘발류"
]

# Ref. 2025 Manual 기준 공식 TJ 환산 계수
MANUAL_FACTORS_2025 = {
    "전기(소비전력기준)": 0.000010,  # kWh -> TJ
    "도시가스(LNG)": 0.000043,    # Nm3 -> TJ
    "휘발유": 0.000033,            # L -> TJ
    "경유": 0.000038,              # L -> TJ
    "등유": 0.000037,              # L -> TJ
    "프로판(LPG)": 0.000050,       # kg -> TJ
    "천연가스(LNG)": 0.000055,     # kg -> TJ
    "휘발류": 0.000033             # 오타 항목도 휘발유와 동일 계수 적용
}

def load_data():
    try:
        df = pd.read_sql("SELECT * FROM energy_only_data", conn, index_col="에너지원")
        df = df.reindex(METRICS).fillna(0.0)
    except:
        df = pd.DataFrame(0.0, index=METRICS, columns=BRANCHES)
        df.index.name = "에너지원"
    return df

# ==========================================
# 2. 메인 화면 구성
# ==========================================
st.title("🌍 아이에스동서 지점별 에너지 사용량 (TJ 자동 변환)")
st.write("각 지점별 에너지 사용량(Raw Data)을 입력하세요. 아래 8개 에너지원만 수집 및 계산됩니다.")

df = load_data()
edited_df = st.data_editor(df, use_container_width=True, height=380)

st.markdown("---")
st.subheader("📥 데이터 저장 및 TJ 변환 엑셀 다운로드")

col1, col2 = st.columns(2)

# 왼쪽: DB 저장 버튼
with col1:
    if st.button("💾 1. 현재 입력 데이터 저장하기", use_container_width=True):
        edited_df.to_sql('energy_only_data', conn, if_exists='replace', index=True)
        st.success("✅ 8개 에너지원 데이터가 안전하게 저장되었습니다!")

# TJ 자동 변환 및 엑셀 리포트 생성 함수
@st.cache_data
def create_excel(df_to_save):
    # 각 에너지원별 TJ 변환 결과를 담을 표
    calc_df = pd.DataFrame(index=[
        "전기(소비전력기준) TJ", "도시가스(LNG) TJ", "휘발유 TJ", "경유 TJ", 
        "등유 TJ", "프로판(LPG) TJ", "천연가스(LNG) TJ", "휘발류 TJ",
        "Scope 1 직접배출 (TJ)", "Scope 2 간접배출 (TJ)", "총 에너지 사용량 (TJ)"
    ], columns=BRANCHES)
    calc_df.index.name = "Manual 변환 항목"
    
    for b in BRANCHES:
        elec_tj = df_to_save.loc["전기(소비전력기준)", b] * MANUAL_FACTORS_2025["전기(소비전력기준)"]
        gas_tj = df_to_save.loc["도시가스(LNG)", b] * MANUAL_FACTORS_2025["도시가스(LNG)"]
        gasoline_tj = df_to_save.loc["휘발유", b] * MANUAL_FACTORS_2025["휘발유"]
        diesel_tj = df_to_save.loc["경유", b] * MANUAL_FACTORS_2025["경유"]
        kerosene_tj = df_to_save.loc["등유", b] * MANUAL_FACTORS_2025["등유"]
        lpg_tj = df_to_save.loc["프로판(LPG)", b] * MANUAL_FACTORS_2025["프로판(LPG)"]
        lng_tj = df_to_save.loc["천연가스(LNG)", b] * MANUAL_FACTORS_2025["천연가스(LNG)"]
        gasoline2_tj = df_to_save.loc["휘발류", b] * MANUAL_FACTORS_2025["휘발류"]
        
        # Scope 1 (전기 제외 연료 합산) 및 Scope 2 (전기)
        scope1_sum = gas_tj + gasoline_tj + diesel_tj + kerosene_tj + lpg_tj + lng_tj + gasoline2_tj
        scope2_sum = elec_tj
        
        calc_df.loc["전기(소비전력기준) TJ", b] = elec_tj
        calc_df.loc["도시가스(LNG) TJ", b] = gas_tj
        calc_df.loc["휘발유 TJ", b] = gasoline_tj
        calc_df.loc["경유 TJ", b] = diesel_tj
        calc_df.loc["등유 TJ", b] = kerosene_tj
        calc_df.loc["프로판(LPG) TJ", b] = lpg_tj
        calc_df.loc["천연가스(LNG) TJ", b] = lng_tj
        calc_df.loc["휘발류 TJ", b] = gasoline2_tj
        calc_df.loc["Scope 1 직접배출 (TJ)", b] = scope1_sum
        calc_df.loc["Scope 2 간접배출 (TJ)", b] = scope2_sum
        calc_df.loc["총 에너지 사용량 (TJ)", b] = scope1_sum + scope2_sum

    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df_to_save.to_excel(writer, sheet_name="Raw Data (수집값)")
        calc_df.to_excel(writer, sheet_name="Ref. 2025 TJ 변환 결과")
    
    return excel_buffer.getvalue()

# 오른쪽: 엑셀 다운로드 버튼
with col2:
    excel_data = create_excel(edited_df)
    st.download_button(
        label="📊 2. TJ 변환 결과 엑셀 다운로드",
        data=excel_data,
        file_name="2026_아이에스동서_에너지_TJ변환결과.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
