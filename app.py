import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO

st.set_page_config(page_title="ESG 환경데이터 컨트롤 타워", layout="wide")

# 1. 엑셀을 대체할 '내부 데이터베이스(DB)' 만들기 (저장 기능)
conn = sqlite3.connect('esg_database.db', check_same_thread=False)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS energy_data (
        branch TEXT PRIMARY KEY,
        elec_kwh REAL, gas_nm3 REAL, gasoline_l REAL, diesel_l REAL, kerosene_l REAL
    )
''')
conn.commit()

# 2. 단위 변환 계수 (TJ 변환)
FACTORS = {
    "전기": 0.000010, "도시가스": 0.000043, "휘발유": 0.000033, "경유": 0.000038, "등유": 0.000037
}

st.title("🌱 아이에스동서 '2. 환경' 통합 데이터 시스템")
st.write("지점별 Raw Data를 입력하면 [조직 내외부 에너지 소비] TJ 단위로 자동 변환 및 저장됩니다.")

# 상단 탭 3개 생성
tab1, tab2, tab3 = st.tabs(["📝 1. 지점별 Raw Data 입력", "📊 2. [조직 내외부 에너지 소비] 확인", "📥 3. 최종 엑셀 다운로드"])

# ==========================================
# 탭 1: 지점 담당자용 입력 화면
# ==========================================
with tab1:
    st.subheader("지점별 에너지 사용량 직접 입력")
    branch_list = ["본사/지사", "건축공사", "이천공장", "청양공장", "음성공장"]
    selected_branch = st.selectbox("데이터를 입력할 지점을 선택하세요.", branch_list)
    
    # DB에서 기존에 저장된 데이터 불러오기
    c.execute("SELECT elec_kwh, gas_nm3, gasoline_l, diesel_l, kerosene_l FROM energy_data WHERE branch=?", (selected_branch,))
    row = c.fetchone()
    default = row if row else (0.0, 0.0, 0.0, 0.0, 0.0)

    # 입력 폼
    with st.form("data_input_form"):
        st.info("※ 영수증/고지서 기준의 원시 데이터(Raw Data) 단위를 그대로 입력해 주세요.")
        col1, col2 = st.columns(2)
        with col1:
            elec = st.number_input("전기 사용량 (kWh)", value=float(default[0]), format="%f")
            gasoline = st.number_input("휘발유 사용량 (L)", value=float(default[2]), format="%f")
            kerosene = st.number_input("등유 사용량 (L)", value=float(default[4]), format="%f")
        with col2:
            gas = st.number_input("도시가스 사용량 (Nm3)", value=float(default[1]), format="%f")
            diesel = st.number_input("경유 사용량 (L)", value=float(default[3]), format="%f")
        
        # 저장 버튼
        if st.form_submit_button("💾 데이터 DB에 영구 저장"):
            c.execute('''
                REPLACE INTO energy_data (branch, elec_kwh, gas_nm3, gasoline_l, diesel_l, kerosene_l)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (selected_branch, elec, gas, gasoline, diesel, kerosene))
            conn.commit()
            st.success(f"[{selected_branch}] 데이터가 안전하게 저장되었습니다! (탭 2에서 결과를 확인하세요)")

# ==========================================
# 탭 2: 지현 님용 (자동 변환된 '2. 환경' 시트 뷰)
# ==========================================
with tab2:
    st.subheader("📊 [조직 내외부 에너지 소비] 자동 계산 결과 (단위: TJ)")
    
    # DB에서 전체 데이터 읽어오기
    df = pd.read_sql_query("SELECT * FROM energy_data", conn)
    
    if not df.empty:
        # 지점명을 인덱스로 설정
        df.set_index("branch", inplace=True)
        
        # 새로운 결과용 데이터프레임 생성
        result_df = pd.DataFrame(index=df.index)
        
        # Raw Data를 매뉴얼 계수를 곱해 TJ로 변환하여 저장
        result_df["연료(Scope 1) 사용량 (TJ)"] = (
            df["gas_nm3"] * FACTORS["도시가스"] +
            df["gasoline_l"] * FACTORS["휘발유"] +
            df["diesel_l"] * FACTORS["경유"] +
            df["kerosene_l"] * FACTORS["등유"]
        )
        result_df["전기(Scope 2) 사용량 (TJ)"] = df["elec_kwh"] * FACTORS["전기"]
        result_df["총 에너지 소비량 (TJ)"] = result_df["연료(Scope 1) 사용량 (TJ)"] + result_df["전기(Scope 2) 사용량 (TJ)"]
        
        # 엑셀 양식처럼 보기 좋게 행/열을 뒤집기(Transpose)
        display_df = result_df.T
        display_df["합계(전체)"] = display_df.sum(axis=1) # 전체 합산 열 추가
        
        # 화면에 표 출력
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("아직 저장된 지점 데이터가 없습니다. 탭 1에서 데이터를 입력해 주세요.")

# ==========================================
# 탭 3: 최종 엑셀 파일 생성
# ==========================================
with tab3:
    st.subheader("📥 작성 완료된 '2. 환경' 양식 다운로드")
    st.write("DB에 저장된 데이터와 위에서 변환된 TJ 값을 바탕으로 최종 엑셀을 생성합니다.")
    
    if not df.empty and st.button("✨ 최종 엑셀 파일 만들기"):
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            # 원시 데이터(Raw) 시트 백업
            df.to_excel(writer, sheet_name="Raw Data(입력값)")
            # 2.환경 (TJ 변환) 시트 생성
            display_df.to_excel(writer, sheet_name="2. 환경")
            
        st.download_button(
            label="엑셀 다운로드 (2026_지속가능경영보고서_환경.xlsx)",
            data=excel_buffer.getvalue(),
            file_name="2026_지속가능경영보고서_환경.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
