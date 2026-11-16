
from pathlib import Path

import pandas as pd
import streamlit as st

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import pairwise_distances


st.set_page_config(
    page_title="비슷한 챔피언 추천 | LOL PICK",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 비슷한 챔피언 추천")
st.write(
    "마음에 드는 챔피언을 선택하면 능력치가 비슷한 챔피언을 찾아줍니다."
)


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
    df = pd.read_csv(data_path, encoding="utf-8")
except Exception as e:
    st.error(f"데이터를 읽을 수 없습니다: {e}")
    st.stop()

if "champion" not in df.columns:
    st.error("champion 열을 찾을 수 없습니다.")
    st.stop()

df = df.copy()
df["champion"] = df["champion"].astype("string").str.strip()
df = df.dropna(subset=["champion"])
df = df.drop_duplicates(subset=["champion"]).reset_index(drop=True)


# --------------------------------------------------
# 2. 모델에 사용할 능력치
# --------------------------------------------------

feature_candidates = [
    "difficulty",
    "attack",
    "defense",
    "mobility",
    "late_game",
    "survivability",
    "team_support",
    "cc_level"
]

feature_labels = {
    "difficulty": "난이도",
    "attack": "공격력",
    "defense": "방어력",
    "mobility": "기동성",
    "late_game": "후반 성장력",
    "survivability": "생존력",
    "team_support": "팀 지원 능력",
    "cc_level": "군중 제어 능력"
}

features = []

for col in feature_candidates:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

        if df[col].notna().sum() > 0 and df[col].nunique() > 1:
            features.append(col)

if len(features) < 2:
    st.error("추천 모델을 만들 수 있는 능력치가 부족합니다.")
    st.stop()

model_df = df[features].copy()

for col in features:
    median_value = model_df[col].median()

    if pd.isna(median_value):
        st.error(f"{col} 열에 사용할 수 있는 값이 없습니다.")
        st.stop()

    model_df[col] = model_df[col].fillna(median_value)


# --------------------------------------------------
# 3. K-means 모델 학습
# --------------------------------------------------

scaler = StandardScaler()
scaled_data = scaler.fit_transform(model_df)

# 앞서 만든 군집 모델 페이지와 같은 방식으로 군집 수 결정
max_k = min(8, len(df) - 1)

if max_k < 2:
    st.error("챔피언 데이터가 너무 적습니다.")
    st.stop()

score_results = []

from sklearn.metrics import silhouette_score

for k in range(2, max_k + 1):
    try:
        temp_model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=10
        )

        labels = temp_model.fit_predict(scaled_data)

        if len(set(labels)) < 2:
            continue

        score = silhouette_score(scaled_data, labels)

        score_results.append((k, score))

    except Exception:
        continue

if not score_results:
    st.error("군집 모델을 학습할 수 없습니다.")
    st.stop()

best_k = max(score_results, key=lambda x: x[1])[0]

model = KMeans(
    n_clusters=best_k,
    random_state=42,
    n_init=10
)

df["cluster"] = model.fit_predict(scaled_data)


# --------------------------------------------------
# 4. 챔피언 선택
# --------------------------------------------------

st.subheader("1️⃣ 기준 챔피언 선택")

champion_list = sorted(df["champion"].astype(str).tolist())

selected_champion = st.selectbox(
    "어떤 챔피언과 비슷한 챔피언을 찾을까요?",
    champion_list
)

selected_index = df.index[
    df["champion"].astype(str) == selected_champion
][0]

selected_cluster = int(df.loc[selected_index, "cluster"])

st.info(
    f"**{selected_champion}**은 "
    f"현재 모델에서 **{selected_cluster + 1}번 군집**에 속합니다."
)


# --------------------------------------------------
# 5. 비슷한 챔피언 계산
# --------------------------------------------------

st.subheader("2️⃣ 비슷한 챔피언 찾기")

st.write(
    "같은 군집에 속한 챔피언 중에서 "
    "선택한 챔피언과 능력치 거리가 가까운 순서로 추천합니다."
)

distances = pairwise_distances(
    scaled_data,
    scaled_data[[selected_index]],
    metric="euclidean"
).flatten()

result = df.copy()
result["유사도 거리"] = distances

# 자기 자신은 추천에서 제외
result = result[
    (result.index != selected_index)
    & (result["cluster"] == selected_cluster)
].copy()

result = result.sort_values("유사도 거리")

# 추천 개수
recommend_count = st.slider(
    "추천받을 챔피언 수",
    min_value=1,
    max_value=10,
    value=5
)

recommendations = result.head(recommend_count)


# --------------------------------------------------
# 6. 추천 결과 표시
# --------------------------------------------------

st.subheader("3️⃣ 추천 결과")

if recommendations.empty:
    st.warning(
        "같은 군집에 속한 다른 챔피언이 없습니다. "
        "군집 모델 페이지에서 군집 수를 바꾸어 확인해 보세요."
    )
else:
    st.success(
        f"{selected_champion}과 비슷한 챔피언 "
        f"{len(recommendations)}명을 찾았습니다!"
    )

    for _, row in recommendations.iterrows():
        champion_name = str(row["champion"])

        with st.container(border=True):
            st.markdown(f"### 🎮 {champion_name}")

            if "title" in row.index and pd.notna(row["title"]):
                st.write(row["title"])

            if "image_url" in row.index and pd.notna(row["image_url"]):
                st.image(
                    row["image_url"],
                    width=110
                )
            elif "splash_url" in row.index and pd.notna(row["splash_url"]):
                st.image(
                    row["splash_url"],
                    width=220
                )

            st.caption(
                f"같은 군집: {int(row['cluster']) + 1}번 군집"
                f" | 능력치 거리: {row['유사도 거리']:.3f}"
            )

            available_values = []

            for feature in features:
                value = row[feature]

                if pd.notna(value):
                    available_values.append({
                        "능력치": feature_labels.get(feature, feature),
                        "값": round(float(value), 2)
                    })

            st.dataframe(
                pd.DataFrame(available_values),
                use_container_width=True,
                hide_index=True
            )


# --------------------------------------------------
# 7. 모델 설명
# --------------------------------------------------

with st.expander("📘 추천 원리 알아보기"):
    st.markdown(
        """
        **① 표준화**

        능력치마다 값의 범위가 다를 수 있으므로
        평균 0, 표준편차 1을 기준으로 변환합니다.

        **② K-means 군집화**

        능력치가 비슷한 챔피언끼리 같은 군집으로 묶습니다.

        **③ 유클리드 거리**

        같은 군집 안에서 기준 챔피언과 능력치 거리가
        가까운 챔피언을 우선 추천합니다.

        **주의할 점**

        이 추천은 챔피언의 능력치 데이터가 비슷하다는 뜻이지,
        실제 게임에서 플레이 방식이나 승률이 같다는 의미는 아닙니다.
        """
    )
