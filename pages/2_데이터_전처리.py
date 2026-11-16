
from pathlib import Path
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="데이터 전처리 | LOL PICK",
    page_icon="🧹",
    layout="wide"
)

st.title("🧹 데이터 전처리")
st.write("챔피언 데이터를 분석과 추천 모델에 사용할 수 있도록 정리합니다.")


# --------------------------------------------------
# 1. 데이터 불러오기
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

possible_paths = [
    ROOT / "champions.csv",
    ROOT / "data" / "champions.csv"
]

data_path = next(
    (path for path in possible_paths if path.exists()),
    None
)

if data_path is None:
    st.error("champions.csv 파일을 찾을 수 없습니다.")
    st.stop()

try:
    original_df = pd.read_csv(data_path, encoding="utf-8")
except Exception as e:
    st.error(f"데이터를 읽는 중 오류가 발생했습니다: {e}")
    st.stop()

df = original_df.copy()

st.success("챔피언 데이터를 불러왔습니다!")


# --------------------------------------------------
# 2. 전처리 전 데이터 확인
# --------------------------------------------------

st.subheader("1️⃣ 전처리 전 데이터")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("전체 데이터 수", f"{len(df):,}개")

with col2:
    st.metric("전체 열 개수", f"{len(df.columns):,}개")

with col3:
    st.metric(
        "전체 결측치",
        f"{int(df.isna().sum().sum()):,}개"
    )

st.dataframe(df.head(10), use_container_width=True)


# --------------------------------------------------
# 3. 문자열 데이터 정리
# --------------------------------------------------

st.subheader("2️⃣ 문자열 데이터 정리")

# 문자열 앞뒤 공백 제거
for col in df.select_dtypes(include=["object"]).columns:
    df[col] = df[col].apply(
        lambda x: x.strip() if isinstance(x, str) else x
    )

# 빈 문자열을 결측치로 변경
df = df.replace(r"^\s*$", pd.NA, regex=True)

st.write(
    "문자열 앞뒤의 공백을 제거하고, "
    "내용이 없는 문자열을 결측치로 통일했습니다."
)


# --------------------------------------------------
# 4. 중복 데이터 확인 및 제거
# --------------------------------------------------

st.subheader("3️⃣ 중복 데이터 처리")

# 챔피언 이름 열 찾기
name_candidates = ["name", "champion", "champion_name", "Name"]

name_col = next(
    (col for col in name_candidates if col in df.columns),
    None
)

if name_col is not None:
    duplicate_count = int(df.duplicated(subset=[name_col]).sum())

    st.write(f"챔피언 이름 기준 중복 데이터: **{duplicate_count}개**")

    df = df.drop_duplicates(subset=[name_col], keep="first")
else:
    duplicate_count = int(df.duplicated().sum())

    st.write(f"전체 행 기준 중복 데이터: **{duplicate_count}개**")

    df = df.drop_duplicates(keep="first")

st.write("중복 데이터는 첫 번째 행만 남기고 제거했습니다.")


# --------------------------------------------------
# 5. 숫자형 데이터 변환
# --------------------------------------------------

st.subheader("4️⃣ 숫자형 데이터 변환")

numeric_candidates = [
    "difficulty",
    "attack",
    "defense",
    "mobility",
    "late_game",
    "survivability",
    "team_support",
    "cc_level"
]

converted_columns = []

for col in numeric_candidates:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        converted_columns.append(col)

if converted_columns:
    st.write("숫자형으로 변환한 열:")
    st.write(", ".join(converted_columns))
else:
    st.info("변환할 숫자형 능력치 열을 찾지 못했습니다.")


# --------------------------------------------------
# 6. 결측치 확인
# --------------------------------------------------

st.subheader("5️⃣ 결측치 확인")

missing_df = pd.DataFrame({
    "열 이름": df.columns,
    "결측치 개수": df.isna().sum().values,
    "결측치 비율(%)": (
        df.isna().mean().values * 100
    ).round(2)
})

missing_df = missing_df.sort_values(
    by="결측치 개수",
    ascending=False
)

st.dataframe(missing_df, use_container_width=True)

st.info(
    "이번 단계에서는 결측치를 임의의 값으로 채우지 않았습니다. "
    "능력치나 포지션이 없는 챔피언에게 임의의 정보를 부여하면 "
    "추천 결과가 왜곡될 수 있기 때문입니다."
)


# --------------------------------------------------
# 7. 전처리 후 데이터 확인
# --------------------------------------------------

st.subheader("6️⃣ 전처리 후 데이터")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("전처리 후 데이터 수", f"{len(df):,}개")

with col2:
    st.metric(
        "제거된 중복 데이터",
        f"{len(original_df) - len(df):,}개"
    )

with col3:
    st.metric(
        "전처리 후 결측치",
        f"{int(df.isna().sum().sum()):,}개"
    )

st.dataframe(df.head(10), use_container_width=True)


# --------------------------------------------------
# 8. 전처리 결과 다운로드
# --------------------------------------------------

st.subheader("7️⃣ 전처리 결과 저장")

csv_data = df.to_csv(
    index=False,
    encoding="utf-8-sig"
)

st.download_button(
    label="📥 전처리된 데이터 CSV 다운로드",
    data=csv_data,
    file_name="champions_cleaned.csv",
    mime="text/csv"
)

st.success(
    "전처리가 완료되었습니다! "
    "원본 champions.csv는 수정하지 않았습니다."
)
