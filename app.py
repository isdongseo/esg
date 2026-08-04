import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO

st.set_page_config(page_title="ESG 환경데이터 통합 시스템", layout="wide", page_icon="🌍")

# ==========================================
# 1. 통합 데이터베이스(DB) 세팅
# ==========================================
conn = sqlite3.connect('esg_environment_all.db', check_same_thread=False)

# 4개의 카테고리별 테이블 생성
queries = [
    "CREATE TABLE IF NOT EXISTS energy (branch TEXT PRIMARY KEY, elec REAL, gas REAL, gasoline REAL, diesel REAL, kerosene REAL)",
    "CREATE TABLE IF NOT EXISTS water (branch TEXT PRIMARY KEY, tap_water REAL, ground_water REAL, discharge REAL, reuse REAL)",
    "CREATE TABLE IF NOT EXISTS waste (branch TEXT PRIMARY KEY, general_recycle REAL, general_landfill REAL, general_incin REAL, spec_waste REAL)",
    "CREATE TABLE IF NOT EXISTS material (branch TEXT PRIMARY KEY, cement REAL, remicon REAL, aggregate REAL, slag REAL)"
]
for q in queries: conn.execute(q)
conn.commit()

# 지점 목록 (Row)
branches = ["본사/지사", "건축공사", "이천공장", "청양공장", "음성공장"]

# ==========================================
# 2. 공통 함수: DB에서 읽고 저장하기
# ==========================================
def load_data(table_name, columns):
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    if df.empty:
        # 데이터가 없으면 0으로 채워진 빈 표 생성
        df = pd.DataFrame(0.0, index=branches, columns=columns)
        df.index.name = "branch"
    else:
        df = df.set_index("branch")
        # 누락된 지점이 있으면 0으로 추가
        for b in branches:
            if b not in df.index: df.loc[b] = 0.0
    return df[columns] # 열 순서 맞추기

def save_data(table_name, df):
    df.to_sql(table_name, conn, if_exists='replace', index=True, index_label='branch')
    conn.commit()
    st.toast("💾 데이터가 안전하게 저장되었습니다!", icon="✅")

# ==========================================
# 3. 화면 구성: 사이드바 및 카테고리별 입력장
# ==========================================
st.sidebar.title("🌍 2026 환경 데이터 입력")
menu = st.sidebar.radio("작업할 항목을 선택하세요:", 
                        ["⚡ 1. 조직 내외부 에너지", "💧 2. 용수 (물)", "♻️ 3. 폐기물", "🧱 4. 자재 사용량", "📥 5. 최종 리포트 (엑셀 다운로드)"])

st.title(menu)

if menu == "⚡ 1. 조직 내외부 에너지":
    st.write("각 연료별 **원시 사용량(단위 확인 필수)**을 입력하세요. (TJ 단위 변환은 최종 리포트에서 자동 계산됩니다.)")
    cols = ["elec", "gas", "gasoline", "diesel", "kerosene"]
    display_cols = ["전기_소비(kWh)", "도시가스(Nm3)", "휘발유(L)", "경유(L)", "등유(L)"]
    
    df = load_data('energy', cols)
    df.columns = display_cols # 화면에 보여줄 한글 이름
    
    edited_df = st.data_editor(df, use_container_width=True)
    if st.button("💾 에너지 데이터 저장"):
        edited_df.columns = cols # DB에 넣을 영어 이름으로 원복
        save_data('energy', edited_df)

elif menu == "💧 2. 용수 (물)":
    st.write("**용수 취수량, 방류량, 사용량(ton)**을 입력하세요.")
    cols = ["tap_water", "ground_water", "discharge", "reuse"]
    display_cols = ["상하수도 취수량(ton)", "지하수 취수량(ton)", "총 폐수방류량(ton)", "용수 재사용량(ton)"]
    
    df = load_data('water', cols)
    df.columns = display_cols
    
    edited_df = st.data_editor(df, use_container_width=True)
    if st.button("💾 용수 데이터 저장"):
        edited_df.columns = cols
        save_data('water', edited_df)

elif menu == "♻️ 3. 폐기물":
    st.write("**일반폐기물(처리방식별) 및 지정폐기물 발생량(ton)**을 입력하세요.")
    cols = ["general_recycle", "general_landfill", "general_incin", "spec_waste"]
    display_cols = ["일반폐기물_재활용(ton)", "일반폐기물_매립(ton)", "일반폐기물_소각(ton)", "지정폐기물_총량(ton)"]
    
    df = load_data('waste', cols)
    df.columns = display_cols
    
    edited_df = st.data_editor(df, use_container_width=True)
    if st.button("💾 폐기물 데이터 저장"):
        edited_df.columns = cols
        save_data('waste', edited_df)

elif menu == "🧱 4. 자재 사용량":
    st.write("**건설 및 제조 자재 사용량**을 입력하세요.")
    cols = ["cement", "remicon", "aggregate", "slag"]
    display_cols = ["시멘트(ton)", "레미콘(m3)", "골재(m3)", "고로슬래그_재활용(ton)"]
    
    df = load_data('material', cols)
    df.columns = display_cols
    
    edited_df = st.data_editor(df, use_container_width=True)
    if st.button("💾 자재 데이터 저장"):
        edited_df.columns = cols
        save_data('material', edited_df)

# ==========================================
# 4. 최종 리포트 및 엑셀 다운로드
# ==========================================
elif menu == "📥 5. 최종 리포트 (엑셀 다운로드)":
    st.write("저장된 모든 환경 데이터를 취합하고 계산하여 '2. 환경' 통합 엑셀 파일을 생성합니다.")
    
    if st.button("✨ 전체 데이터 취합 및 엑셀 만들기"):
        # DB에서 전체 테이블 가져오기
        df_eng = pd.read_sql("SELECT * FROM energy", conn).set_index('branch')
        df_wat = pd.read_sql("SELECT * FROM water", conn).set_index('branch')
        df_was = pd.read_sql("SELECT * FROM waste", conn).set_index('branch')
        df_mat = pd.read_sql("SELECT * FROM material", conn).set_index('branch')
        
        # [자동 계산 1] 에너지 TJ 변환 및 Scope 배출량
        FACTORS = {"elec": 0.000010, "gas": 0.000043, "gasoline": 0.000033, "diesel": 0.000038, "kerosene": 0.000037}
        
        # 안전한 계산을 위해 빈 데이터프레임 방지
        if not df_eng.empty:
            df_eng_calc = pd.DataFrame(index=df_eng.index)
            df_eng_calc["Scope 1 직접배출 (TJ)"] = (df_eng["gas"]*FACTORS["gas"] + df_eng["gasoline"]*FACTORS["gasoline"] + df_eng["diesel"]*FACTORS["diesel"] + df_eng["kerosene"]*FACTORS["kerosene"])
            df_eng_calc["Scope 2 간접배출 (TJ)"] = df_eng["elec"]*FACTORS["elec"]
            df_eng_calc["총 에너지 사용량 (TJ)"] = df_eng_calc["Scope 1 직접배출 (TJ)"] + df_eng_calc["Scope 2 간접배출 (TJ)"]
        else:
            df_eng_calc = pd.DataFrame()

        # 엑셀 파일로 작성 (여러 시트로 깔끔하게 분리)
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            # 1. 종합 계산 완료 시트 (여기서 단위 변환 등 처리)
            if not df_eng_calc.empty: df_eng_calc.T.to_excel(writer, sheet_name="1. 에너지_온실가스_계산완료")
            if not df_wat.empty: df_wat.T.to_excel(writer, sheet_name="2. 용수_취합")
            if not df_was.empty: df_was.T.to_excel(writer, sheet_name="3. 폐기물_취합")
            if not df_mat.empty: df_mat.T.to_excel(writer, sheet_name="4. 자재_취합")
            
        st.success("데이터 취합 및 자동 계산이 완료되었습니다!")
        st.download_button(
            label="📊 [2026_아이에스동서_환경데이터_통합본.xlsx] 다운로드",
            data=excel_buffer.getvalue(),
            file_name="2026_아이에스동서_환경데이터_통합본.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
