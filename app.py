import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="아이에스동서 환경데이터 자동화", layout="wide")

st.title("📊 지속가능경영보고서 환경데이터 자동 취합 시스템")
st.write("각 지점별 Raw Data를 아래 표에 입력하면, '2. 환경' 시트 양식에 맞게 온실가스 배출량이 자동 계산된 엑셀 파일을 만들어 줍니다.")

# 1. 2025년 단위변환 매뉴얼 계수 (TJ 변환용)
factors = {
    "휘발유(L)": 0.000033,
    "등유(L)": 0.000037,
    "경유(L)": 0.000038,
    "천연가스(kg)": 0.000055,
    "도시가스(Nm3)": 0.000043,
    "전기_소비(kWh)": 0.000010
}

# 2. 지점별 미니 엑셀 표(데이터 에디터) 만들기
st.subheader("📝 지점별 Raw Data 입력 (숫자만 입력하세요)")

# 기본 표 뼈대 만들기
branches = ["본사/지사", "건축공사", "이천공장", "청양공장", "음성공장"]
columns = ["전기_소비(kWh)", "도시가스(Nm3)", "휘발유(L)", "경유(L)", "등유(L)", "천연가스(kg)"]

# 빈 데이터프레임(표) 생성
raw_data_df = pd.DataFrame(0, index=branches, columns=columns)

# 웹페이지에 수정 가능한 표 띄우기
edited_df = st.data_editor(raw_data_df, use_container_width=True)

# 3. 엑셀 다운로드 마법진 구성
st.subheader("📥 완성된 '2. 환경' 시트 엑셀 다운로드")

if st.button("✨ 데이터 계산 및 엑셀 만들기"):
    # Scope 1 (직접배출: 전기 제외 나머지 연료 합산) 및 Scope 2 (전기) 계산 로직
    result_data = []
    
    for branch in branches:
        # 각 연료별 사용량 * 변환계수
        scope1_tj = (
            edited_df.loc[branch, "도시가스(Nm3)"] * factors["도시가스(Nm3)"] +
            edited_df.loc[branch, "휘발유(L)"] * factors["휘발유(L)"] +
            edited_df.loc[branch, "경유(L)"] * factors["경유(L)"] +
            edited_df.loc[branch, "등유(L)"] * factors["등유(L)"] +
            edited_df.loc[branch, "천연가스(kg)"] * factors["천연가스(kg)"]
        )
        scope2_tj = edited_df.loc[branch, "전기_소비(kWh)"] * factors["전기_소비(kWh)"]
        
        result_data.append([branch, scope1_tj, scope2_tj])
    
    # 계산된 결과를 '2. 환경' 양식처럼 표로 만들기
    final_df = pd.DataFrame(result_data, columns=["지점명", "Scope 1 (TJ)", "Scope 2 (TJ)"])
    final_df = final_df.set_index("지점명").T # 행과 열을 뒤집어서 원본 엑셀 양식처럼 배치
    
    # 합산 열(합계) 추가
    final_df["합산"] = final_df.sum(axis=1)
    
    st.write("✅ **미리보기 (계산 완료)**")
    st.dataframe(final_df)

    # 엑셀 파일로 굽기 (저장)
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        final_df.to_excel(writer, sheet_name="2. 환경_자동계산결과")
    
    excel_data = excel_buffer.getvalue()
    
    # 다운로드 버튼 생성
    st.download_button(
        label="📊 [2026 지속가능경영보고서_환경데이터_완성본.xlsx] 다운로드",
        data=excel_data,
        file_name="2026_지속가능경영보고서_환경데이터_완성본.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )
    st.balloons()
