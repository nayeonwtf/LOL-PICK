
from pathlib import Path

import pandas as pd
import streamlit as st

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from sklearn.impute import SimpleImputer
from sklearn.metrics import pairwise_distances


st.set_page_config(
    page_title="군집 기반 추천 | LOL PICK",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 비슷한 챔피언 추천")
st.write(
    "선택한 챔피언과 능력치가 비슷한 챔피언을 "
    "군집 모델을 활용해 추천합니다."
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

name_candidates = ["name", "champion", "champion_name", "Name"]

name_col = next(
    (col for col in name_candidates if col in df.columns),
    None
)

if name_col is None:
    st.error("챔피언 이름 열을 찾을 수 없습니다.")
    st.write("현재 데이터 열:", list(df.columns))
    st.stop()

df[name_col] = df[name_col].astype("string").str.strip()
df = df.dropna(subset=[name_col])
df = df.drop_duplicates(subset=[name_col]).reset_index(drop=True)


# --------------------------------------------------
# 2. 모델에 사용할 능력치
# --------------------------------------------------

st.subheader("1️⃣ 추천 기준 설정")

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

available_features = []

for col in feature_candidates:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

        if df[col].notna().sum() > 0 and df[col].nunique() > 1:
            available_features.append(col)

if len(available_features) < 2:
    st.error("추천 모델을 만들려면 사용할 수 있는 능력치가 2개 이상 필요합니다.")
    st.stop()

selected_features = st.multiselect(
    "추천에 사용할 능력치를 선택해 주세요.",
    options=available_features,
    default=available_features,
    format_func=lambda x: feature_labels.get(x, x)
)

if len(selected_features) < 2:
    st.warning("능력치를 최소 2개 선택해 주세요.")
    st.stop()


# --------------------------------------------------
# 3. 결측치 처리 및 표준화
# --------------------------------------------------

model_df = df[selected_features].copy()

imputer = SimpleImputer(strategy="median")
imputed_data = imputer.fit_transform(model_df)

scaler = StandardScaler()
scaled_data = scaler.fit_transform(imputed_data)

st.caption(
    "결측치는 각 능력치의 중앙값으로 채우고, "
    "능력치별 단위 차이를 줄이기 위해 표준화했습니다."
)


# --------------------------------------------------
# 4. K-means 군집 모델
# --------------------------------------------------

st.subheader("2️⃣ 챔피언 군집 모델")

n_samples = len(df)

if n_samples < 3:
    st.error("군집 분석을 하려면 챔피언 데이터가 최소 3개 필요합니다.")
    st.stop()

max_k = min(8, n_samples - 1)

score_results = []

for k in range(2, max_k + 1):
    model = KMeans(
        n_clusters=k,
        random_state=42,
        n_init=10
    )

    labels = model.fit_predict(scaled_data)

    if len(set(labels)) < 2 or len(set(labels)) >= n_samples:
        continue

    score = silhouette_score(scaled_data, labels)

    score_results.append({
        "군집 수": k,
        "실루엣 점수": score
    })

if not score_results:
    st.error("군집 모델을 평가할 수 없습니다.")
    st.stop()

score_df = pd.DataFrame(score_results)

best_k = int(
    score_df.loc[
        score_df["실루엣 점수"].idxmax(),
        "군집 수"
    ]
)

selected_k = st.selectbox(
    "추천 모델의 군집 수",
    options=score_df["군집 수"].astype(int).tolist(),
    index=score_df["군집 수"].astype(int).tolist().index(best_k)
)

kmeans = KMeans(
    n_clusters=selected_k,
    random_state=42,
    n_init=10
)

labels = kmeans.fit_predict(scaled_data)

final_score = silhouette_score(scaled_data, labels)

result_df = df.copy()
result_df["군집"] = labels + 1

st.metric("모델 실루엣 점수", f"{final_score:.4f}")


# --------------------------------------------------
# 5. 기준 챔피언 선택
# --------------------------------------------------

st.subheader("3️⃣ 기준 챔피언 선택")

champion_names = result_df[name_col].astype(str).tolist()

selected_champion = st.selectbox(
    "어떤 챔피언과 비슷한 챔피언을 찾을까요?",
    options=champion_names
)

selected_index = result_df.index[
    result_df[name_col].astype(str) == selected_champion
][0]

selected_cluster = int(labels[selected_index] + 1)

st.write(
    f"**{selected_champion}**은 "
    f"**{selected_cluster}번 군집**에 속합니다."
)


# --------------------------------------------------
# 6. 같은 군집 안에서 유사 챔피언 찾기
# --------------------------------------------------

st.subheader("4️⃣ 비슷한 챔피언 추천")

same_cluster_indices = [
    i for i, label in enumerate(labels)
    if label == labels[selected_index] and i != selected_index
]

if not same_cluster_indices:
    st.info(
        "같은 군집에 다른 챔피언이 없습니다. "
        "군집 수를 바꾸어 다시 확인해 보세요."
    )
    st.stop()

distances = pairwise_distances(
    scaled_data[[selected_index]],
    scaled_data[same_cluster_indices],
    metric="euclidean"
)[0]

recommendations = pd.DataFrame({
    "index": same_cluster_indices,
    "거리": distances
}).sort_values("거리")

recommendations = recommendations.head(5)

recommendation_indices = recommendations["index"].tolist()

recommendation_df = result_df.iloc[
    recommendation_indices
].copy()

recommendation_df["능력치 유사도"] = (
    1 / (1 + recommendations["거리"].values)
).round(3)

recommendation_df.insert(
    0,
    "추천 순위",
    range(1, len(recommendation_df) + 1)
)

display_columns = (
    ["추천 순위", name_col, "능력치 유사도"]
    + selected_features
)

st.dataframe(
    recommendation_df[display_columns].rename(
        columns=feature_labels
    ),
    use_container_width=True,
    hide_index=True
)

st.caption(
    "능력치 유사도는 표준화된 능력치 간 거리로 계산한 참고 지표입니다. "
    "1에 가까울수록 선택한 챔피언과 능력치가 비슷합니다."
)


# --------------------------------------------------
# 7. 추천 결과 해석
# --------------------------------------------------

st.subheader("5️⃣ 추천 결과 해석")

st.write(
    f"선택한 **{selected_champion}**과 같은 군집에 속한 "
    f"챔피언 중 능력치 차이가 작은 순서로 "
    f"{len(recommendation_df)}명을 추천했습니다."
)

st.write(
    "추천 결과는 선택한 능력치와 군집 수에 따라 달라질 수 있습니다. "
    "실제 게임에서의 승률이나 사용자 만족도를 직접 예측하는 결과는 아닙니다."
)


# --------------------------------------------------
# 8. 결과 다운로드
# --------------------------------------------------

st.subheader("6️⃣ 추천 결과 저장")

csv_data = recommendation_df[display_columns].rename(
    columns=feature_labels
).to_csv(
    index=False,
    encoding="utf-8-sig"
)

st.download_button(
    label="📥 추천 결과 CSV 다운로드",
    data=csv_data,
    file_name="champion_recommendations.csv",
    mime="text/csv"
)
