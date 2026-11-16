
from pathlib import Path
import re

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="데이터 살펴보기 | LOL PICK",
    page_icon="📊",
    layout="wide"
)

st.title("📊 챔피언 데이터 살펴보기")
st.write("추천 모델을 만들기 전에 수집한 데이터의 상태와 특징을 확인해 보자!")


# -----------------------------
# 데이터 불러오기
# -----------------------------
@st.cache_data
def load_data():
    paths = [
        Path("champions.csv"),
        Path("data/champions.csv")
    ]

    for path in paths:
        if path.exists():
            return pd.read_csv(path, encoding="utf-8-sig")

    return None


df = load_data()

if df is None:
    st.error("champions.csv 파일을 찾을 수 없어.")
    st.stop()


# 빈 문자열을 결측치로 통일
df = df.replace(r"^\s*$", pd.NA, regex=True)


# 여러 값으로 구성된 항목 분리
def split_values(value):
    if pd.isna(value):
        return []

    return [
        x.strip()
        for x in re.split(r"[;,|]", str(value))
        if x.strip()
    ]


# -----------------------------
# 1. 데이터 기본 정보
# -----------------------------
st.header("1. 데이터 기본 정보")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("전체 데이터 수", f"{len(df):,}개")

with c2:
    st.metric("전체 열의 수", f"{len(df.columns):,}개")

with c3:
    st.metric(
        "중복 챔피언 이름",
        int(df["champion"].duplicated().sum())
        if "champion" in df.columns else "확인 불가"
    )

with c4:
    st.metric(
        "결측값 총합",
        f"{int(df.isna().sum().sum()):,}개"
    )

st.write("**데이터 미리보기**")
st.dataframe(df.head(10), use_container_width=True)


# -----------------------------
# 2. 결측값 확인
# -----------------------------
st.header("2. 결측값 확인")
st.write(
    "비어 있는 데이터가 얼마나 있는지 확인해 보자. "
    "결측값이 많으면 추천 결과에 영향을 줄 수 있어."
)

missing = pd.DataFrame({
    "열 이름": df.columns,
    "결측값 수": df.isna().sum().values,
    "결측 비율(%)": (
        df.isna().mean().values * 100
    ).round(2)
})

missing = missing.sort_values(
    "결측 비율(%)",
    ascending=False
)

st.dataframe(missing, use_container_width=True)

missing_columns = missing[missing["결측값 수"] > 0]

if len(missing_columns) == 0:
    st.success("결측값이 없어!")
else:
    st.warning(
        f"결측값이 있는 열이 {len(missing_columns)}개 있어. "
        "모델링 전에 처리 방법을 정해야 해."
    )


# -----------------------------
# 3. 포지션별 챔피언 수
# -----------------------------
st.header("3. 포지션별 챔피언 분포")

if "position" in df.columns:

    position_counts = {}

    for value in df["position"]:
        for position in split_values(value):
            position_counts[position] = (
                position_counts.get(position, 0) + 1
            )

    if position_counts:
        position_data = pd.DataFrame({
            "포지션": list(position_counts.keys()),
            "챔피언 수": list(position_counts.values())
        }).sort_values("챔피언 수", ascending=False)

        st.bar_chart(
            position_data.set_index("포지션")
        )

        st.dataframe(position_data, use_container_width=True)
    else:
        st.info("포지션 데이터가 비어 있어.")
else:
    st.warning("position 열을 찾을 수 없어.")


# -----------------------------
# 4. 챔피언 유형별 분포
# -----------------------------
st.header("4. 챔피언 유형별 분포")

if "type" in df.columns:

    type_counts = {}

    for value in df["type"]:
        for champion_type in split_values(value):
            type_counts[champion_type] = (
                type_counts.get(champion_type, 0) + 1
            )

    if type_counts:
        type_data = pd.DataFrame({
            "챔피언 유형": list(type_counts.keys()),
            "챔피언 수": list(type_counts.values())
        }).sort_values("챔피언 수", ascending=False)

        st.bar_chart(
            type_data.set_index("챔피언 유형")
        )

        st.dataframe(type_data, use_container_width=True)
    else:
        st.info("유형 데이터가 비어 있어.")
else:
    st.warning("type 열을 찾을 수 없어.")


# -----------------------------
# 5. 능력 및 플레이 스타일 점수
# -----------------------------
st.header("5. 플레이 스타일 데이터 확인")

trait_columns = [
    "difficulty",
    "attack",
    "defense",
    "mobility",
    "late_game",
    "survivability",
    "team_support",
    "cc_level"
]

available_traits = [
    column for column in trait_columns
    if column in df.columns
]

if available_traits:

    trait_df = df[available_traits].apply(
        pd.to_numeric,
        errors="coerce"
    )

    trait_summary = pd.DataFrame({
        "항목": available_traits,
        "입력된 데이터 수": trait_df.count().values,
        "결측값 수": trait_df.isna().sum().values,
        "평균": trait_df.mean().round(2).values,
        "최솟값": trait_df.min().values,
        "최댓값": trait_df.max().values
    })

    st.dataframe(
        trait_summary,
        use_container_width=True
    )

    st.caption(
        "평균과 최솟값, 최댓값은 숫자로 입력된 데이터만 계산했어."
    )

else:
    st.warning("확인할 플레이 스타일 점수 열이 없어.")


# -----------------------------
# 6. 분석 결과 요약
# -----------------------------
st.header("6. 데이터 탐색 결과 요약")

st.write(
    "아래 내용을 바탕으로 추천 모델 제작 전에 "
    "어떤 데이터를 보완해야 하는지 생각해 보자."
)

if "position" in df.columns:
    position_missing = int(df["position"].isna().sum())
    st.write(f"- 포지션 결측값: **{position_missing}개**")

if "type" in df.columns:
    type_missing = int(df["type"].isna().sum())
    st.write(f"- 유형 결측값: **{type_missing}개**")

if available_traits:
    total_trait_values = len(df) * len(available_traits)
    filled_trait_values = int(
        df[available_traits].apply(
            pd.to_numeric,
            errors="coerce"
        ).notna().sum().sum()
    )

    st.write(
        f"- 플레이 스타일 점수 입력률: "
        f"**{filled_trait_values:,} / {total_trait_values:,}개**"
    )

st.info(
    "다음 단계에서는 결측값과 플레이 스타일 점수를 정리하고, "
    "추천 모델에 사용할 데이터를 준비할 거야."
)
