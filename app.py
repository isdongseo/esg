import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO

st.set_page_config(page_title="ESG 환경데이터 통합 시스템", layout="wide")

# ==========================================
# 1. 통합 데이터베이스(DB) 세팅
# ==========================================
conn = sqlite3.connect('esg_smart_unified.db', check_same_thread=False)

BRANCHES = ["본사/지사", "건축공사", "이천공장", "청양공장", "음성공장"]
METRICS = [
    "[에너지] 전기_소비(kWh)", "[에너지] 도시가스(Nm3)", "[에너지] 휘발유(L)", "[에너지] 경유(L)", "[에너지] 등유(L)",
    "[용수] 상하수도 취수량(ton)", "[용수] 지하수 취수량(ton)", "[용수] 총 폐수방류량(ton)", "[용수] 용수 재사용량(ton)",
    "[폐기물] 일반폐기물_재활용(ton)", "[폐기물] 일반폐기물_매립(ton)", "[폐기물] 일반폐기물_소각(ton)", "[폐기물] 지정폐기물_총량(ton)",
    "[자재] 시멘트(ton)", "[자재] 레미콘(m3)", "[자재] 골재(m3)", "[자재] 고로슬래그_재활용(ton)"
]

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
st.write("가로(지점) x 세로(항목) 구조입니다. 엑셀처럼 클릭하고 바로 숫자를 입력하세요!")

df = load_data()
edited_df = st.data_editor(df, use_container_width=True, height=650)

st.markdown("---")
st.subheader("📥 데이터 저장 및 엑셀 리포트 다운로드")

# ==========================================
# 3. [수정 포인트] 버튼 충돌 방지를 위한 좌우 배치
# ==========================================
col1, col2 = st.columns(2)

# 왼쪽: DB에 데이터 영구 저장 버튼
with col1:
    if st.button("💾 1. 현재 화면 데이터 저장하기", use_container_width=True):
        edited_df.to_sql('unified_data', conn, if_exists='replace', index=True)
        st.success("✅ 모든 항목이 성공적으로 저장되었습니다!")

# 엑셀 구워내는 함수 (openpyxl 사용)
@st.cache_data
def create_excel(df_to_save):
    FACTORS = {"전기": 0.000010, "가스": 0.000043, "휘발유": 0.000033, "경유": 0.000038, "등유": 0.000037}
    calc_df = pd.DataFrame(index=["Scope 1 직접배출 (TJ)", "Scope 2 간접배출 (TJ)", "총 에너지 사용량 (TJ)"], columns=BRANCHES)
    calc_df.index.name = "산출 항목"
    
    for b in BRANCHES:
        s1 = (df_to_save.loc["[에너지] 도시가스(Nm3)", b] * FACTORS["가스"] +
              df_to_save.loc["[에너지] 휘발유(L)", b] * FACTORS["휘발유"] +
              df_to_save.loc["[에너지] 경유(L)", b] * FACTORS["경유"] +
              df_to_save.loc["[에너지] 등유(L)", b] * FACTORS["등유"])
        
        s2 = df_to_save.loc["[에너지] 전기_소비(kWh)", b] * FACTORS["전기"]
        
        calc_df.loc["Scope 1 직접배출 (TJ)", b] = s1
        calc_df.loc["Scope 2 간접배출 (TJ)", b] = s2
        calc_df.loc["총 에너지 사용량 (TJ)", b] = s1 + s2

    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df_to_save.to_excel(writer, sheet_name="Raw Data")
        calc_df.to_excel(writer, sheet_name="1. 에너지 및 온실가스 (TJ)")
    
    return excel_buffer.getvalue()

# 오른쪽: 엑셀 파일 다운로드 버튼 (항상 떠 있도록 밖으로 뺌)
with col2:
    excel_data = create_excel(edited_df)
    st.download_button(
        label="📊 2. 통합 결과 엑셀 다운로드",
        data=excel_data,
        file_name="2026_아이에스동서_환경데이터_통합.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
