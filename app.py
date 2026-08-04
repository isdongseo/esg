import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO

st.set_page_config(page_title="ESG 환경데이터 통합 시스템", layout="wide")

# ==========================================
# 1. 통합 데이터베이스(DB) 세팅
# ==========================================
conn = sqlite3.connect('esg_smart_unified.db', check_same_thread=False)

# 가로(Columns): 지점명 / 세로(Index): 항목명
BRANCHES = ["본사/지사", "건축공사", "이천공장", "청양공장", "음성공장"]
METRICS = [
    "[에너지] 전기_소비(kWh)", "[에너지] 도시가스(Nm3)", "[에너지] 휘발유(L)", "[에너지] 경유(L)", "[에너지] 등유(L)",
    "[용수] 상하수도 취수량(ton)", "[용수] 지하수 취수량(ton)", "[용수] 총 폐수방류량(ton)", "[용수] 용수 재사용량(ton)",
    "[폐기물] 일반폐기물_재활용(ton)", "[폐기물] 일반폐기물_매립(ton)", "[폐기물] 일반폐기물_소각(ton)", "[폐기물] 지정폐기물_총량(ton)",
    "[자재] 시멘트(ton)", "[자재] 레미콘(m3)", "[자재] 골재(m3)", "[자재] 고로슬래그_재활용(ton)"
]

def load_data():
    try:
        # DB에 저장된 표를 그대로 불러옴
        df = pd.read_sql("SELECT * FROM unified_data", conn, index_col="항목명")
    except:
        # 처음 실행해서 DB가 없을 경우 빈 표 생성
        df = pd.DataFrame(0.0, index=METRICS, columns=BRANCHES)
        df.index.name = "항목명"
    return df

# ==========================================
# 2. 메인 화면 (엑셀과 똑같은 가로/세로 표 띄우기)
# ==========================================
st.title("🌍 2026 환경 데이터 원페이지 입력 시스템")
st.write("가로(지점) x 세로(항목) 구조입니다. 엑셀처럼 클릭하고 바로 숫자를 입력하세요!")

# DB에서 표 불러오기
df = load_data()

# 화면에 거대한 미니 엑셀 띄우기 (height를 길게 줘서 스크롤 최소화)
edited_df = st.data_editor(df, use_container_width=True, height=650)

st.markdown("---")

# ==========================================
# 3. 저장 및 엑셀 다운로드 (단위 변환 자동 계산)
# ==========================================
if st.button("💾 데이터 저장 및 엑셀 리포트 만들기", type="primary"):
    # 1. 화면에 보이는 그대로 DB에 통째로 덮어쓰기 (가장 스마트한 방식!)
    edited_df.to_sql('unified_data', conn, if_exists='replace', index=True)
    st.success("✅ 모든 항목이 성공적으로 저장되었습니다!")
    
    # 2. 온실가스 / 에너지(TJ) 자동 계산
    FACTORS = {"전기": 0.000010, "가스": 0.000043, "휘발유": 0.000033, "경유": 0.000038, "등유": 0.000037}
    
    # 계산 결과를 담을 새로운 표 만들기 (가로는 동일하게 지점명)
    calc_df = pd.DataFrame(index=["Scope 1 직접배출 (TJ)", "Scope 2 간접배출 (TJ)", "총 에너지 사용량 (TJ)"], columns=BRANCHES)
    calc_df.index.name = "산출 항목"
    
    for b in BRANCHES:
        s1 = (edited_df.loc["[에너지] 도시가스(Nm3)", b] * FACTORS["가스"] +
              edited_df.loc["[에너지] 휘발유(L)", b] * FACTORS["휘발유"] +
              edited_df.loc["[에너지] 경유(L)", b] * FACTORS["경유"] +
              edited_df.loc["[에너지] 등유(L)", b] * FACTORS["등유"])
        
        s2 = edited_df.loc["[에너지] 전기_소비(kWh)", b] * FACTORS["전기"]
        
        calc_df.loc["Scope 1 직접배출 (TJ)", b] = s1
        calc_df.loc["Scope 2 간접배출 (TJ)", b] = s2
        calc_df.loc["총 에너지 사용량 (TJ)", b] = s1 + s2

    # 3. 엑셀 파일로 압축하기
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        # Sheet 1: Raw Data (담당자들이 입력한 전체 데이터)
        edited_df.to_excel(writer, sheet_name="Raw Data (전체입력값)")
        # Sheet 2: 계산 완료된 에너지/온실가스 데이터
        calc_df.to_excel(writer, sheet_name="1. 에너지 및 온실가스 (TJ)")
    
    # 다운로드 버튼 띄우기
    st.download_button(
        label="📊 [2026_환경데이터_통합결과.xlsx] 다운로드",
        data=excel_buffer.getvalue(),
        file_name="2026_아이에스동서_환경데이터_통합.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.balloons()
