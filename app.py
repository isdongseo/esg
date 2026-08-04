import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO

st.set_page_config(page_title="ESG 환경데이터 통합 시스템", layout="wide")

# ==========================================
# 1. 통합 데이터베이스(DB) 및 Manual 계수 세팅
# ==========================================
conn = sqlite3.connect('esg_manual_unified.db', check_same_thread=False)

BRANCHES = ["본사/지사", "건축공사", "이천공장", "청양공장", "음성공장"]
METRICS = [
    "[에너지] 전기_소비(kWh)", "[에너지] 도시가스(Nm3)", "[에너지] 휘발유(L)", "[에너지] 경유(L)", "[에너지] 등유(L)",
    "[용수] 상하수도 취수량(ton)", "[용수] 지하수 취수량(ton)", "[용수] 총 폐수방류량(ton)", "[용수] 용수 재사용량(ton)",
    "[폐기물] 일반폐기물_재활용(ton)", "[폐기물] 일반폐기물_매립(ton)", "[폐기물] 일반폐기물_소각(ton)", "[폐기물] 지정폐기물_총량(ton)",
    "[자재] 시멘트(ton)", "[자재] 레미콘(m3)", "[자재] 골재(m3)", "[자재] 고로슬래그_재활용(ton)"
]

# 'Ref. 2025 단위변환 및 온실가스 Manual' 공식 TJ 환산 계수 반영
MANUAL_FACTORS_2025 = {
    "[에너지] 전기_소비(kWh)": 0.000010,     # 전기(소비기준) MJ 9.6 -> TJ 0.000010
    "[에너지] 도시가스(Nm3)": 0.000043,    # 도시가스(LNG) Nm3 기준
    "[에너지] 휘발유(L)": 0.000033,        # 휘발유 L 기준
    "[에너지] 경유(L)": 0.000038,          # 경유 L 기준
    "[에너지] 등유(L)": 0.000037           # 등유 L 기준
}

def load_data():
    try:
        df = pd.read_sql("SELECT * FROM unified_data", conn, index_col="항목명")
    except:
        df = pd.DataFrame(0.0, index=METRICS, columns=BRANCHES)
        df.index.name = "항목명"
    return df

# ==========================================
# 2. 메인 화면 구성
# ==========================================
st.title("🌍 2026 환경 데이터 원페이지 입력 시스템")
st.write("지점별 데이터를 입력하면 **[Ref. 2025 단위변환 및 온실가스 Manual]** 기준으로 TJ가 자동 계산됩니다.")

df = load_data()
edited_df = st.data_editor(df, use_container_width=True, height=650)

st.markdown("---")
st.subheader("📥 데이터 저장 및 Manual 기준 엑셀 리포트 다운로드")

col1, col2 = st.columns(2)

# 왼쪽: DB 저장 버튼
with col1:
    if st.button("💾 1. 현재 화면 데이터 저장하기", use_container_width=True):
        edited_df.to_sql('unified_data', conn, if_exists='replace', index=True)
        st.success("✅ 모든 항목이 성공적으로 저장되었습니다!")

# Manual 계수 기반 TJ 자동 계산 및 엑셀 생성 함수
@st.cache_data
def create_excel_with_manual(df_to_save):
    calc_df = pd.DataFrame(index=[
        "전기_소비 TJ", "도시가스 TJ", "휘발유 TJ", "경유 TJ", "등유 TJ",
        "Scope 1 직접배출 합계 (TJ)", "Scope 2 간접배출 합계 (TJ)", "총 에너지 사용량 (TJ)"
    ], columns=BRANCHES)
    calc_df.index.name = "Manual 변환 항목"
    
    for b in BRANCHES:
        # 개별 에너지원별 Manual 계수 곱하기
        elec_tj = df_to_save.loc["[에너지] 전기_소비(kWh)", b] * MANUAL_FACTORS_2025["[에너지] 전기_소비(kWh)"]
        gas_tj = df_to_save.loc["[에너지] 도시가스(Nm3)", b] * MANUAL_FACTORS_2025["[에너지] 도시가스(Nm3)"]
        gasoline_tj = df_to_save.loc["[에너지] 휘발유(L)", b] * MANUAL_FACTORS_2025["[에너지] 휘발유(L)"]
        diesel_tj = df_to_save.loc["[에너지] 경유(L)", b] * MANUAL_FACTORS_2025["[에너지] 경유(L)"]
        kerosene_tj = df_to_save.loc["[에너지] 등유(L)", b] * MANUAL_FACTORS_2025["[에너지] 등유(L)"]
        
        scope1_sum = gas_tj + gasoline_tj + diesel_tj + kerosene_tj
        scope2_sum = elec_tj
        
        calc_df.loc["전기_소비 TJ", b] = elec_tj
        calc_df.loc["도시가스 TJ", b] = gas_tj
        calc_df.loc["휘발유 TJ", b] = gasoline_tj
        calc_df.loc["경유 TJ", b] = diesel_tj
        calc_df.loc["등유 TJ", b] = kerosene_tj
        calc_df.loc["Scope 1 직접배출 합계 (TJ)", b] = scope1_sum
        calc_df.loc["Scope 2 간접배출 합계 (TJ)", b] = scope2_sum
        calc_df.loc["총 에너지 사용량 (TJ)", b] = scope1_sum + scope2_sum

    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df_to_save.to_excel(writer, sheet_name="Raw Data")
        calc_df.to_excel(writer, sheet_name="Ref. 2025 Manual 변환 결과")
    
    return excel_buffer.getvalue()

# 오른쪽: 엑셀 다운로드 버튼
with col2:
    excel_data = create_excel_with_manual(edited_df)
    st.download_button(
        label="📊 2. Manual 변환 결과 엑셀 다운로드",
        data=excel_data,
        file_name="2026_아이에스동서_Manual변환_환경데이터.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
