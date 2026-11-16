
from pathlib import Path

import pandas as pd
import streamlit as st

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA


st.set_page_config(
    page_title="챔피언 군집 모델 | LOL PICK",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 챔피언 군집 모델 만들기")
st.write(
    "챔피언의 능력치를 분석해 비슷한 특징을 가진 챔피언끼리 "
    "자동으로 묶어 보는 비지도학습 모델입니다."
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

df = df.copy()

# 챔피언 이름 열 찾기
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
# 2. 사용할 능력치 선택
# --------------------------------------------------

st.subheader("1️⃣ 모델에 사용할 능력치 선택")

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

        # 모든 값이 결측치이거나 값이 하나뿐인 열은 제외
        if df[col].notna().sum() > 0 and df[col].nunique() > 1:
            available_features.append(col)

if len(available_features) < 2:
    st.error("군집 모델을 만들려면 사용할 수 있는 능력치가 2개 이상 필요합니다.")
    st.stop()

default_features = available_features

selected_features = st.multiselect(
    "군집 분석에 사용할 능력치를 골라 주세요.",
    options=available_features,
    default=default_features,
    format_func=lambda x: feature_labels.get(x, x)
)

if len(selected_features) < 2:
    st.warning("능력치를 최소 2개 선택해 주세요.")
    st.stop()


# --------------------------------------------------
# 3. 결측치 처리 및 데이터 표준화
# --------------------------------------------------

st.subheader("2️⃣ 데이터 전처리")

model_df = df[selected_features].copy()

# 숫자가 아닌 값은 결측치로 처리
for col in selected_features:
    model_df[col] = pd.to_numeric(
        model_df[col],
        errors="coerce"
    )

# 선택한 능력치의 결측치를 각 열의 중앙값으로 채움
for col in selected_features:
    median_value = model_df[col].median()

    if pd.isna(median_value):
        st.error(f"{feature_labels.get(col, col)} 열에 사용할 수 있는 값이 없습니다.")
        st.stop()

    model_df[col] = model_df[col].fillna(median_value)

# 표준화
scaler = StandardScaler()
scaled_data = scaler.fit_transform(model_df)

st.write("선택한 능력치:")
st.write(", ".join(
    feature_labels.get(col, col)
    for col in selected_features
))

st.write(
    "결측치는 각 능력치의 중앙값으로 채웠고, "
    "표준화를 통해 능력치별 측정 단위 차이를 줄였습니다."
)


# --------------------------------------------------
# 4. 적절한 군집 수 평가
# --------------------------------------------------

st.subheader("3️⃣ 적절한 군집 수 찾기")

st.write(
    "군집 수를 여러 가지로 바꾸어 실루엣 점수를 비교합니다. "
    "실루엣 점수는 -1부터 1 사이이며, 일반적으로 높을수록 "
    "군집이 서로 잘 구분된다는 의미입니다."
)

n_samples = len(scaled_data)

if n_samples < 3:
    st.error("군집 분석을 하려면 챔피언 데이터가 최소 3개 필요합니다.")
    st.stop()

max_k = min(8, n_samples - 1)

score_results = []

for k in range(2, max_k + 1):
    try:
        temp_model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=10
        )

        temp_labels = temp_model.fit_predict(scaled_data)

        # 모든 데이터가 서로 다른 군집에 들어가는 경우 등 제외
        if len(set(temp_labels)) < 2:
            continue

        if len(set(temp_labels)) >= n_samples:
            continue

        score = silhouette_score(
            scaled_data,
            temp_labels
        )

        score_results.append({
            "군집 수": k,
            "실루엣 점수": round(score, 4)
        })

    except Exception:
        continue

if not score_results:
    st.error("실루엣 점수를 계산할 수 없습니다. 데이터를 확인해 주세요.")
    st.stop()

score_df = pd.DataFrame(score_results)

st.dataframe(
    score_df,
    use_container_width=True,
    hide_index=True
)

st.line_chart(
    score_df.set_index("군집 수"),
    y="실루엣 점수"
)

best_row = score_df.loc[score_df["실루엣 점수"].idxmax()]

st.info(
    f"실루엣 점수가 가장 높은 군집 수는 "
    f"**{int(best_row['군집 수'])}개**입니다. "
    f"(점수: {best_row['실루엣 점수']:.4f})"
)


# --------------------------------------------------
# 5. 최종 K-means 모델 만들기
# --------------------------------------------------

st.subheader("4️⃣ 최종 군집 모델")

valid_k_values = score_df["군집 수"].astype(int).tolist()

selected_k = st.selectbox(
    "최종 모델에 사용할 군집 수를 선택해 주세요.",
    options=valid_k_values,
    index=valid_k_values.index(int(best_row["군집 수"]))
)

kmeans = KMeans(
    n_clusters=selected_k,
    random_state=42,
    n_init=10
)

cluster_labels = kmeans.fit_predict(scaled_data)

result_df = df.copy()
result_df["군집"] = cluster_labels + 1

final_score = silhouette_score(
    scaled_data,
    cluster_labels
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("분석한 챔피언 수", f"{len(result_df):,}명")

with col2:
    st.metric("군집 개수", f"{selected_k}개")

with col3:
    st.metric("실루엣 점수", f"{final_score:.4f}")


# --------------------------------------------------
# 6. 군집별 챔피언 확인
# --------------------------------------------------

st.subheader("5️⃣ 군집별 챔피언 확인")

cluster_counts = (
    result_df["군집"]
    .value_counts()
    .sort_index()
)

count_df = pd.DataFrame({
    "군집": [f"{i}번 군집" for i in cluster_counts.index],
    "챔피언 수": cluster_counts.values
})

st.bar_chart(
    count_df.set_index("군집"),
    y="챔피언 수"
)

for cluster_number in sorted(result_df["군집"].unique()):
    cluster_champions = result_df[
        result_df["군집"] == cluster_number
    ]

    with st.expander(
        f"{cluster_number}번 군집 ({len(cluster_champions)}명)"
    ):
        st.dataframe(
            cluster_champions[
                [name_col] + selected_features
            ],
            use_container_width=True,
            hide_index=True
        )


# --------------------------------------------------
# 7. 비슷한 챔피언 찾아보기
# --------------------------------------------------

st.subheader("6️⃣ 선택한 챔피언과 비슷한 챔피언 찾기")

champion_names = result_df[name_col].astype(str).tolist()

selected_champion = st.selectbox(
    "기준으로 삼을 챔피언을 선택해 주세요.",
    options=champion_names
)

selected_cluster = int(
    result_df.loc[
        result_df[name_col].astype(str) == selected_champion,
        "군집"
    ].iloc[0]
)

similar_champions = result_df[
    (result_df["군집"] == selected_cluster)
    & (result_df[name_col].astype(str) != selected_champion)
]

st.write(
    f"**{selected_champion}**은 "
    f"**{selected_cluster}번 군집**에 속합니다."
)

if len(similar_champions) > 0:
    st.write("같은 군집에 속한 다른 챔피언입니다.")

    st.dataframe(
        similar_champions[
            [name_col] + selected_features
        ],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("같은 군집에 다른 챔피언이 없습니다.")


# --------------------------------------------------
# 8. 군집 시각화
# --------------------------------------------------

st.subheader("7️⃣ 군집 시각화")

if len(selected_features) >= 2:
    pca = PCA(n_components=2)
    pca_data = pca.fit_transform(scaled_data)

    plot_df = pd.DataFrame({
        "주성분 1": pca_data[:, 0],
        "주성분 2": pca_data[:, 1],
        "군집": [
            f"{label}번 군집"
            for label in cluster_labels + 1
        ],
        "챔피언": result_df[name_col].astype(str)
    })

    st.scatter_chart(
        plot_df,
        x="주성분 1",
        y="주성분 2",
        color="군집",
        size=100
    )

    explained = pca.explained_variance_ratio_.sum() * 100

    st.caption(
        f"PCA 2차원 시각화입니다. "
        f"선택한 능력치 정보의 약 {explained:.1f}%를 "
        f"두 축으로 표현했습니다."
    )


# --------------------------------------------------
# 9. 모델 평가 및 해석
# --------------------------------------------------

st.subheader("8️⃣ 모델 평가")

st.write(
    f"이번 모델의 실루엣 점수는 **{final_score:.4f}**입니다."
)

if final_score >= 0.5:
    st.success(
        "군집이 비교적 뚜렷하게 구분되는 편입니다."
    )
elif final_score >= 0.25:
    st.info(
        "어느 정도 군집 구조가 있지만, "
        "군집 사이의 구분이 아주 뚜렷하지는 않습니다."
    )
else:
    st.warning(
        "군집 사이의 구분이 약할 수 있습니다. "
        "능력치 선택이나 군집 수를 바꾸어 비교해 보세요."
    )

st.caption(
    "주의: 실루엣 점수는 능력치 기준으로 군집이 얼마나 잘 나뉘었는지를 "
    "평가합니다. 실제 사용자의 챔피언 선호도나 추천 만족도를 "
    "직접 평가한 점수는 아닙니다."
)
