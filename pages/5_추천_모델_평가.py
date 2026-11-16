
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import silhouette_score, pairwise_distances


st.set_page_config(
    page_title="추천 모델 평가 | LOL PICK",
    page_icon="📊",
    layout="wide"
)

st.title("📊 추천 모델 평가")
st.write(
    "추천 결과를 직접 평가하고, "
    "추천 방식의 장단점을 분석하는 페이지입니다."
)

ROOT = Path(__file__).resolve().parent.parent

DATA_PATHS = [
    ROOT / "champions.csv",
    ROOT / "data" / "champions.csv"
]

data_path = next(
    (p for p in DATA_PATHS if p.exists()),
    None
)

if data_path is None:
    st.error("champions.csv 파일을 찾을 수 없습니다.")
    st.stop()

df = pd.read_csv(data_path, encoding="utf-8")

name_candidates = ["name", "champion", "champion_name", "Name"]
name_col = next(
    (c for c in name_candidates if c in df.columns),
    None
)

if name_col is None:
    st.error("챔피언 이름 열을 찾을 수 없습니다.")
    st.stop()

df[name_col] = df[name_col].astype("string").str.strip()
df = df.dropna(subset=[name_col])
df = df.drop_duplicates(subset=[name_col]).reset_index(drop=True)

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
    st.error("평가에 사용할 수 있는 능력치가 부족합니다.")
    st.stop()

st.subheader("1️⃣ 평가할 추천 방식")

method = st.radio(
    "추천 방식을 선택해 주세요.",
    ["조건 기반 추천", "군집 기반 추천"],
    horizontal=True
)

# --------------------------------------------------
# 조건 기반 추천
# --------------------------------------------------

if method == "조건 기반 추천":

    st.subheader("조건 선택")

    positions = sorted({
        str(value).strip()
        for cell in df["position"].dropna()
        for value in str(cell).replace(",", ";").replace("|", ";").split(";")
        if str(value).strip()
    }) if "position" in df.columns else []

    selected_position = None

    if positions:
        selected_position = st.selectbox(
            "포지션",
            positions
        )

    types = sorted({
        str(value).strip()
        for cell in df["type"].dropna()
        for value in str(cell).replace(",", ";").replace("|", ";").split(";")
        if str(value).strip()
    }) if "type" in df.columns else []

    selected_types = st.multiselect(
        "챔피언 유형",
        types
    )

    style_options = {
        "단단함": "defense",
        "후반 성장형": "late_game",
        "강한 공격형": "attack",
        "기동성": "mobility",
        "안정적인 플레이": "survivability",
        "팀원 지원형": "team_support",
        "CC기 중심": "cc_level"
    }

    selected_styles = st.multiselect(
        "선호 플레이 스타일",
        [
            label for label, col in style_options.items()
            if col in available_features
        ]
    )

    candidates = df.copy()

    if selected_position and "position" in candidates.columns:
        candidates = candidates[
            candidates["position"].fillna("").apply(
                lambda x: selected_position in [
                    v.strip()
                    for v in str(x).replace(",", ";").replace("|", ";").split(";")
                ]
            )
        ]

    if selected_types and "type" in candidates.columns:
        candidates = candidates[
            candidates["type"].fillna("").apply(
                lambda x: any(
                    t in [
                        v.strip()
                        for v in str(x).replace(",", ";").replace("|", ";").split(";")
                    ]
                    for t in selected_types
                )
            )
        ]

    score_columns = [
        style_options[s]
        for s in selected_styles
        if style_options[s] in available_features
    ]

    if score_columns:
        candidates = candidates.copy()
        candidates["추천 점수"] = candidates[score_columns].mean(axis=1)
        candidates = candidates.sort_values(
            "추천 점수",
            ascending=False
        )

    candidates = candidates.head(5)

    st.write("추천 결과")

    if len(candidates) == 0:
        st.warning("조건에 맞는 챔피언이 없습니다.")
        st.stop()

    st.dataframe(
        candidates[[name_col] + score_columns],
        use_container_width=True,
        hide_index=True
    )

    recommended_names = candidates[name_col].astype(str).tolist()

# --------------------------------------------------
# 군집 기반 추천
# --------------------------------------------------

else:

    st.subheader("군집 기반 추천 설정")

    selected_features = st.multiselect(
        "모델에 사용할 능력치",
        available_features,
        default=available_features,
        format_func=lambda x: feature_labels.get(x, x)
    )

    if len(selected_features) < 2:
        st.warning("능력치를 최소 2개 선택해 주세요.")
        st.stop()

    model_df = df[selected_features].copy()

    imputer = SimpleImputer(strategy="median")
    imputed = imputer.fit_transform(model_df)

    scaler = StandardScaler()
    scaled = scaler.fit_transform(imputed)

    if len(df) < 3:
        st.error("챔피언 데이터가 최소 3개 필요합니다.")
        st.stop()

    max_k = min(8, len(df) - 1)

    scores = []

    for k in range(2, max_k + 1):
        model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=10
        )

        labels = model.fit_predict(scaled)

        if len(set(labels)) < 2 or len(set(labels)) >= len(df):
            continue

        scores.append((
            k,
            silhouette_score(scaled, labels)
        ))

    if not scores:
        st.error("군집 모델을 평가할 수 없습니다.")
        st.stop()

    best_k = max(scores, key=lambda x: x[1])[0]

    selected_k = st.selectbox(
        "군집 수",
        [x[0] for x in scores],
        index=[x[0] for x in scores].index(best_k)
    )

    model = KMeans(
        n_clusters=selected_k,
        random_state=42,
        n_init=10
    )

    labels = model.fit_predict(scaled)

    champion = st.selectbox(
        "기준 챔피언",
        df[name_col].astype(str).tolist()
    )

    selected_index = df.index[
        df[name_col].astype(str) == champion
    ][0]

    same_cluster = [
        i for i in range(len(df))
        if labels[i] == labels[selected_index]
        and i != selected_index
    ]

    if not same_cluster:
        st.warning("같은 군집에 다른 챔피언이 없습니다.")
        st.stop()

    distances = pairwise_distances(
        scaled[[selected_index]],
        scaled[same_cluster]
    )[0]

    recommendation_df = pd.DataFrame({
        "index": same_cluster,
        "거리": distances
    }).sort_values("거리").head(5)

    candidates = df.iloc[
        recommendation_df["index"].tolist()
    ]

    recommended_names = candidates[name_col].astype(str).tolist()

    st.write(f"기준 챔피언: **{champion}**")

    st.dataframe(
        candidates[[name_col] + selected_features],
        use_container_width=True,
        hide_index=True
    )

# --------------------------------------------------
# 추천 결과 평가
# --------------------------------------------------

st.divider()
st.subheader("2️⃣ 추천 결과 직접 평가")

st.write(
    "추천된 챔피언을 확인하고, "
    "얼마나 마음에 드는지 평가해 주세요."
)

st.caption(
    "별점과 의견은 사용자의 주관적인 평가입니다. "
    "평가가 쌓이면 추천 만족도를 분석할 수 있습니다."
)

rating = st.slider(
    "추천 결과 만족도",
    min_value=1,
    max_value=5,
    value=3
)

feedback = st.text_area(
    "추천 결과에 대한 의견",
    placeholder="예: 내가 선호하는 플레이 스타일과 잘 맞았어요."
)

if st.button("평가 저장", type="primary"):

    if not recommended_names:
        st.warning("저장할 추천 결과가 없습니다.")
        st.stop()

    feedback_path = ROOT / "recommendation_feedback.csv"

    new_feedback = pd.DataFrame([{
        "평가 시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "추천 방식": method,
        "추천 챔피언": ", ".join(recommended_names),
        "만족도": rating,
        "의견": feedback
    }])

    if feedback_path.exists():
        old_feedback = pd.read_csv(
            feedback_path,
            encoding="utf-8-sig"
        )

        all_feedback = pd.concat(
            [old_feedback, new_feedback],
            ignore_index=True
        )
    else:
        all_feedback = new_feedback

    all_feedback.to_csv(
        feedback_path,
        index=False,
        encoding="utf-8-sig"
    )

    st.success(
        "평가가 저장되었습니다! "
        "소중한 평가 감사합니다."
    )

# --------------------------------------------------
# 평가 데이터 분석
# --------------------------------------------------

st.divider()
st.subheader("3️⃣ 누적 평가 결과")

feedback_path = ROOT / "recommendation_feedback.csv"

if feedback_path.exists():

    feedback_df = pd.read_csv(
        feedback_path,
        encoding="utf-8-sig"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("누적 평가 수", len(feedback_df))

    with col2:
        st.metric(
            "평균 만족도",
            f"{feedback_df['만족도'].mean():.2f} / 5"
        )

    with col3:
        st.metric(
            "5점 평가 비율",
            f"{(feedback_df['만족도'] == 5).mean() * 100:.1f}%"
        )

    method_summary = (
        feedback_df.groupby("추천 방식")["만족도"]
        .agg(["count", "mean"])
        .reset_index()
    )

    method_summary.columns = [
        "추천 방식",
        "평가 수",
        "평균 만족도"
    ]

    st.write("추천 방식별 만족도")
    st.dataframe(
        method_summary,
        use_container_width=True,
        hide_index=True
    )

    st.write("전체 평가 기록")
    st.dataframe(
        feedback_df.sort_values(
            "평가 시각",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "📥 평가 데이터 다운로드",
        data=feedback_df.to_csv(
            index=False,
            encoding="utf-8-sig"
        ),
        file_name="recommendation_feedback.csv",
        mime="text/csv"
    )

else:
    st.info(
        "아직 저장된 평가가 없습니다. "
        "추천 결과를 확인하고 평가를 남겨 보세요."
    )
