import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO

st.set_page_config(page_title="ESG 환경데이터 통합 시스템", layout="wide", page_icon="🌍")

# ==========================================
# 1. 통합 데이터베이스(DB) 세팅
# ==========================================
conn = sqlite3.connect('esg_environment_all.db', check_same_thread=False)

queries = [
    "CREATE TABLE IF NOT EXISTS energy (branch TEXT PRIMARY KEY, elec REAL, gas REAL, gasoline REAL, diesel REAL, kerosene REAL)",
    "CREATE TABLE IF NOT EXISTS water (branch TEXT PRIMARY KEY, tap_water REAL, ground_water REAL, discharge REAL, reuse REAL)",
    "CREATE TABLE IF NOT EXISTS waste (branch TEXT PRIMARY KEY, general_recycle REAL, general_landfill REAL, general_incin REAL, spec_waste REAL)",
    "CREATE TABLE IF NOT EXISTS material (branch TEXT PRIMARY KEY, cement REAL, remicon REAL, aggregate REAL, slag REAL)"
]
for q in queries: conn.execute(q)
conn.commit()

branches = ["본사/지사", "건축공사", "이천공장", "청양공장", "음성공장"]

# ==========================================
# 2. 공통 함수: DB에서 읽기
# ==========================================
def load_data(table_name, columns):
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    if df.empty:
        df = pd.DataFrame(0.0, index=branches, columns=columns)
        df.index.name = "branch"
    else:
        df = df.set_index("branch")
        for b in branches:
            if b not in df.index: df.loc[b] = 0.0
    return df[columns]

# ==========================================
# 3. 메인 화면 (모든 입력 폼을 한 페이지에 배치)
# ==========================================
st.title("🌍 2026 환경 데이터 통합 입력 시스템")
st.write("각 지점별 Raw Data를 입력하세요. 입력창에서 데이터를 수정하면 자동으로 반영됩니다. 모든 입력이 끝나면 맨 아래의 다운로드 버튼을 눌러주세요.")
st.markdown("---") # 구분선

# [1] 에너지
st.subheader("⚡ 1. 조직 내외부 에너지 (Raw Data)")
st.caption("※ 전기(kWh), 가스(Nm3), 연료(L) 등 영수증/고지서 기준의 원시 사용량을 입력하세요.")
eng_cols = ["elec", "gas", "gasoline", "diesel", "kerosene"]
eng_disp = ["전기_소비(kWh)", "도시가스(Nm3)", "휘발유(L)", "경유(L)", "등유(L)"]
df_eng = load_data('energy', eng_cols)
df_eng.columns = eng_disp
edited_eng = st.data_editor(df_eng, use_container_width=True, key="eng_editor")

st.markdown("<br>", unsafe_allow_html=True) # 줄바꿈 여백

# [2] 용수
st.subheader("💧 2. 용수 (물)")
st.caption("※ 취수량, 방류량, 사용량(ton)을 입력하세요.")
wat_cols = ["tap_water", "ground_water", "discharge", "reuse"]
wat_disp = ["상하수도 취수량(ton)", "지하수 취수량(ton)", "총 폐수방류량(ton)", "용수 재사용량(ton)"]
df_wat = load_data('water', wat_cols)
df_wat.columns = wat_disp
edited_wat = st.data_editor(df_wat, use_container_width=True, key="wat_editor")

st.markdown("<br>", unsafe_allow_html=True)

# [3] 폐기물
st.subheader("♻️ 3. 폐기물")
st.caption("※ 일반폐기물 및 지정폐기물 발생량(ton)을 입력하세요.")
was_cols = ["general_recycle", "general_landfill", "general_incin", "spec_waste"]
was_disp = ["일반폐기물_재활용(ton)", "일반폐기물_매립(ton)", "일반폐기물_소각(ton)", "지정폐기물_총량(ton)"]
df_was = load_data('waste', was_cols)
df_was.columns = was_disp
edited_was = st.data_editor(df_was, use_container_width=True, key="was_editor")

st.markdown("<br>", unsafe_allow_html=True)

# [4] 자재
st.subheader("🧱 4. 자재 사용량")
st.caption("※ 건설 및 제조 자재 사용량을 입력하세요.")
mat_cols = ["cement", "remicon", "aggregate", "slag"]
mat_disp = ["시멘트(ton)", "레미콘(m3)", "골재(m3)", "고로슬래그_재활용(ton)"]
df_mat = load_data('material', mat_cols)
df_mat.columns = mat_disp
edited_mat = st.data_editor(df_mat, use_container_width=True, key="mat_editor")

st.markdown("---")

# ==========================================
# 4. 저장 및 자동 계산 다운로드 버튼
# ==========================================
st.subheader("📥 데이터 저장 및 최종 리포트 생성")
st.write("위 표에 입력한 내용이 모두 반영된 '2. 환경' 통합 엑셀 파일을 다운로드합니다.")

if st.button("💾 위 내용 모두 저장하고 엑셀 파일 다운로드 준비하기", type="primary"):
    # 1. 화면에 있는(수정된) 표 데이터를 다시 원래 컬럼명으로 돌려서 DB에 저장
    edited_eng.columns = eng_cols
    edited_wat.columns = wat_cols
    edited_was.columns = was_cols
    edited_mat.columns = mat_cols
    
    edited_eng.to_sql('energy', conn, if_exists='replace', index=True, index_label='branch')
    edited_wat.to_sql('water', conn, if_exists='replace', index=True, index_label='branch')
    edited_was.to_sql('waste', conn, if_exists='replace', index=True, index_label='branch')
    edited_mat.to_sql('material', conn, if_exists='replace', index=True, index_label='branch')
    conn.commit()
    
    st.success("모든 데이터가 안전하게 저장되었습니다!")
    
    # 2. 다운로드할 엑셀 파일 백그라운드 계산 로직
    FACTORS = {"elec": 0.000010, "gas": 0.000043, "gasoline": 0.000033, "diesel": 0.000038, "kerosene": 0.000037}
    
    # 단위 변환 및 Scope 배출량 계산 (에너지)
    df_eng_calc = pd.DataFrame(index=edited_eng.index)
    df_eng_calc["Scope 1 직접배출 (TJ)"] = (edited_eng["gas"]*FACTORS["gas"] + edited_eng["gasoline"]*FACTORS["gasoline"] + edited_eng["diesel"]*FACTORS["diesel"] + edited_eng["kerosene"]*FACTORS["kerosene"])
    df_eng_calc["Scope 2 간접배출 (TJ)"] = edited_eng["elec"]*FACTORS["elec"]
    df_eng_calc["총 에너지 사용량 (TJ)"] = df_eng_calc["Scope 1 직접배출 (TJ)"] + df_eng_calc["Scope 2 간접배출 (TJ)"]
    
    # 엑셀 파일 생성
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df_eng_calc.T.to_excel(writer, sheet_name="1. 에너지_온실가스_계산완료")
        edited_wat.T.to_excel(writer, sheet_name="2. 용수_취합")
        edited_was.T.to_excel(writer, sheet_name="3. 폐기물_취합")
        edited_mat.T.to_excel(writer, sheet_name="4. 자재_취합")
    
    # 진짜 다운로드 버튼 띄우기
    st.download_button(
        label="📊 [2026_아이에스동서_환경데이터_통합본.xlsx] 클릭하여 다운로드",
        data=excel_buffer.getvalue(),
        file_name="2026_아이에스동서_환경데이터_통합본.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.balloons()
