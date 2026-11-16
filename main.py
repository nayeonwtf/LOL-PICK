
from pathlib import Path
import random

import pandas as pd
import streamlit as st


# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(
    page_title="LOL PICK",
    page_icon="🎮",
    layout="wide"
)

st.title("🎮 LOL PICK")
st.subheader("오늘의 협곡, 어떤 챔피언과 함께할까?")
st.write("나에게 맞는 챔피언을 찾아보자!")


# -----------------------------
# 챔피언 데이터 불러오기
# -----------------------------
@st.cache_data
def load_data():
    possible_paths = [
        Path("champions.csv"),
        Path("data/champions.csv")
    ]

    for path in possible_paths:
        if path.exists():
            return pd.read_csv(path, encoding="utf-8-sig")

    return None


df = load_data()

if df is None:
    st.error("champions.csv 파일을 찾을 수 없어!")
    st.info("CSV 파일이 main.py와 같은 폴더 또는 data 폴더에 있는지 확인해 줘.")
    st.stop()

if "champion" not in df.columns:
    st.error("CSV에 champion 열이 없어. 데이터 파일을 확인해 줘.")
    st.stop()


# -----------------------------
# 데이터 정리 함수
# -----------------------------
def split_values(value):
    """세미콜론으로 구분된 포지션·유형 데이터를 목록으로 변환"""
    if pd.isna(value) or not str(value).strip():
        return []

    return [
        item.strip()
        for item in str(value).split(";")
        if item.strip()
    ]


def get_display_value(value, default="정보 없음"):
    if pd.isna(value) or str(value).strip() == "":
        return default
    return str(value)


def get_champion_image(champion, image_type="icon"):
    """챔피언 이미지 주소 가져오기"""
    if image_type == "splash":
        image_url = champion.get("splash_url")
    else:
        image_url = champion.get("image_url")

    if pd.notna(image_url) and str(image_url).strip():
        return str(image_url)

    # 이미지 주소가 없으면 챔피언 ID로 기본 주소 생성
    champion_id = champion.get("champion_id")

    if pd.notna(champion_id) and str(champion_id).strip():
        if image_type == "splash":
            return (
                "https://ddragon.leagueoflegends.com/cdn/img/"
                f"champion/splash/{champion_id}_0.jpg"
            )

        version = champion.get("version", "16.22.1")
        return (
            f"https://ddragon.leagueoflegends.com/cdn/"
            f"{version}/img/champion/{champion_id}.png"
        )

    return None


# -----------------------------
# 데이터 요약
# -----------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("전체 챔피언", f"{len(df)}명")

with col2:
    st.metric(
        "포지션 정보",
        "수집 완료" if "position" in df.columns else "확인 필요"
    )

with col3:
    st.metric(
        "챔피언 유형",
        df["type"].nunique() if "type" in df.columns else "확인 필요"
    )


st.divider()


# -----------------------------
# 시작 메뉴
# -----------------------------
st.markdown("## 어떤 방법으로 챔피언을 고를까?")

left, right = st.columns(2)

with left:
    st.markdown("### 🎲 완전 랜덤")
    st.write("고민은 그만! 무작위로 챔피언을 골라보자.")

    if st.button("랜덤 챔피언 뽑기", use_container_width=True):
        champion = df.sample(1).iloc[0]
        st.session_state["random_champion"] = champion.to_dict()
        st.session_state["show_conditions"] = False
        st.session_state.pop("condition_results", None)

with right:
    st.markdown("### 🔍 조건으로 찾기")
    st.write("원하는 포지션과 플레이 스타일을 선택해 보자.")

    if st.button("조건 선택하러 가기", use_container_width=True):
        st.session_state["show_conditions"] = True
        st.session_state.pop("random_champion", None)


# -----------------------------
# 랜덤 결과
# -----------------------------
if "random_champion" in st.session_state:
    champion = st.session_state["random_champion"]

    st.divider()
    st.markdown("# 🎉 빠밤!")
    st.markdown(f"## 오늘의 챔피언은 {champion['champion']}!")

    image_url = get_champion_image(champion, "splash")

    if image_url:
        st.image(image_url, use_container_width=True)

    if pd.notna(champion.get("title")):
        st.write(champion["title"])

    if pd.notna(champion.get("position")):
        st.write(f"**추천 포지션:** {champion['position']}")

    if pd.notna(champion.get("type")):
        st.write(f"**챔피언 유형:** {champion['type']}")

    st.markdown("### 빠밤~ 이제 협곡으로 가보까?!")

    if st.button("다시 뽑기"):
        st.session_state.pop("random_champion", None)
        st.rerun()


# -----------------------------
# 조건 선택 화면
# -----------------------------
if st.session_state.get("show_conditions", False):

    st.divider()
    st.markdown("# 🔍 조건으로 챔피언 찾기")
    st.write("원하는 조건을 선택하면 어울리는 챔피언을 찾아줄게!")

    # 포지션 선택
    st.markdown("### 1. 어떤 포지션을 플레이할까?")

    positions = ["탑", "정글", "미드", "원딜", "서포터"]

    selected_position = st.radio(
        "포지션",
        positions,
        horizontal=True,
        key="selected_position"
    )

    # 챔피언 유형 선택
    st.markdown("### 2. 어떤 유형의 챔피언을 원해?")

    all_types = set()

    if "type" in df.columns:
        for value in df["type"]:
            all_types.update(split_values(value))

    type_order = [
        "전사", "탱커", "마법사",
        "암살자", "원거리 딜러", "서포터"
    ]

    available_types = [
        item for item in type_order if item in all_types
    ]

    available_types += sorted(
        all_types - set(available_types)
    )

    selected_types = st.multiselect(
        "챔피언 유형 (여러 개 선택 가능)",
        available_types,
        help="아무것도 선택하지 않으면 모든 유형을 대상으로 찾아."
    )

    # 플레이 스타일 선택
    st.markdown("### 3. 어떤 플레이 스타일을 좋아해?")

    style_options = [
        "단단함",
        "후반 성장형",
        "강한 공격형",
        "기동성",
        "안정적인 플레이",
        "팀원 지원형",
        "CC기 중심"
    ]

    selected_styles = st.multiselect(
        "마음에 드는 스타일을 모두 골라 줘!",
        style_options,
        help="여러 개를 골라도 괜찮아. 선택한 스타일을 고르게 반영할게."
    )

    # 스타일과 CSV 점수 열 연결
    style_columns = {
        "단단함": "defense",
        "후반 성장형": "late_game",
        "강한 공격형": "attack",
        "기동성": "mobility",
        "안정적인 플레이": "survivability",
        "팀원 지원형": "team_support",
        "CC기 중심": "cc_level"
    }

    st.divider()

    # -----------------------------
    # 추천 실행
    # -----------------------------
    if st.button("✨ 조건에 맞는 챔피언 찾기!", use_container_width=True):

        # 1) 포지션 필터
        filtered = df[
            df["position"].apply(
                lambda x: selected_position in split_values(x)
            )
        ].copy()

        # 2) 유형 필터
        if selected_types:
            filtered = filtered[
                filtered["type"].apply(
                    lambda x: bool(
                        set(split_values(x)) & set(selected_types)
                    )
                )
            ]

        if filtered.empty:
            st.session_state.pop("condition_results", None)
            st.error("조건에 맞는 챔피언을 찾지 못했어. 다른 조건으로 시도해 줘!")

        else:
            # 3) 선택한 스타일의 점수 계산
            usable_columns = [
                style_columns[style]
                for style in selected_styles
                if style_columns[style] in filtered.columns
            ]

            for column in usable_columns:
                filtered[column] = pd.to_numeric(
                    filtered[column],
                    errors="coerce"
                )

            def calculate_score(row):
                scores = []

                for style in selected_styles:
                    column = style_columns[style]

                    if column in row.index and pd.notna(row[column]):
                        scores.append(float(row[column]))

                if scores:
                    return sum(scores) / len(scores)

                return None

            if selected_styles:
                filtered["recommendation_score"] = filtered.apply(
                    calculate_score,
                    axis=1
                )

                # 점수가 있는 챔피언을 우선 추천
                scored = filtered[
                    filtered["recommendation_score"].notna()
                ].copy()

                if not scored.empty:
                    scored = scored.sort_values(
                        "recommendation_score",
                        ascending=False
                    )

                    results = scored.head(5)
                    st.session_state["score_available"] = True

                else:
                    # 아직 성향 점수가 없으면 포지션·유형에 맞는 후보 중 무작위
                    results = filtered.sample(
                        min(5, len(filtered))
                    )

                    st.session_state["score_available"] = False

            else:
                # 스타일을 선택하지 않았다면 조건에 맞는 후보 중 무작위
                results = filtered.sample(
                    min(5, len(filtered))
                )

                st.session_state["score_available"] = False

            # 이전에 선택했던 챔피언 초기화
            st.session_state.pop("selected_recommended_champion", None)

            st.session_state["condition_results"] = results.to_dict("records")
            st.session_state["condition_selected_styles"] = selected_styles
            st.session_state["condition_selected_position"] = selected_position
            st.session_state["condition_selected_types"] = selected_types


    # -----------------------------
    # 추천 결과
    # -----------------------------
    if "condition_results" in st.session_state:

        results = st.session_state["condition_results"]

        st.divider()
        st.markdown("# 🎉 추천 챔피언!")

        if st.session_state.get("score_available", False):
            st.success("선택한 플레이 스타일의 점수를 반영해서 추천했어!")

        elif st.session_state.get("condition_selected_styles"):
            st.warning(
                "아직 선택한 스타일의 점수 데이터가 충분하지 않아. "
                "포지션과 유형에 맞는 챔피언을 먼저 보여줄게!"
            )

        else:
            st.info("플레이 스타일을 선택하지 않아 조건에 맞는 챔피언을 무작위로 골랐어!")

        st.write(
            f"**선택한 포지션:** "
            f"{st.session_state['condition_selected_position']}"
        )

        if st.session_state["condition_selected_types"]:
            st.write(
                "**선택한 유형:** "
                + ", ".join(st.session_state["condition_selected_types"])
            )
        else:
            st.write("**선택한 유형:** 전체 유형")

        if st.session_state["condition_selected_styles"]:
            st.write(
                "**선택한 스타일:** "
                + ", ".join(st.session_state["condition_selected_styles"])
            )

        st.write("아래 후보 중 마음에 드는 챔피언을 살펴보자!")

        # -----------------------------
        # 후보별 이미지와 정보 표시
        # -----------------------------
        for index, champion in enumerate(results, start=1):

            with st.container(border=True):

                image_col, info_col = st.columns([1, 3])

                with image_col:
                    image_url = get_champion_image(champion, "icon")

                    if image_url:
                        st.image(image_url, width=130)
                    else:
                        st.caption("이미지 없음")

                with info_col:
                    st.markdown(
                        f"### {index}. {champion['champion']}"
                    )

                    if pd.notna(champion.get("title")):
                        st.write(champion["title"])

                    st.write(
                        f"**포지션:** "
                        f"{get_display_value(champion.get('position'))}"
                    )

                    st.write(
                        f"**유형:** "
                        f"{get_display_value(champion.get('type'))}"
                    )

                    st.write(
                        f"**난이도:** "
                        f"{get_display_value(champion.get('difficulty'))}"
                    )

                    if st.session_state.get("score_available", False):
                        st.write(
                            f"**스타일 점수:** "
                            f"{champion['recommendation_score']:.2f}"
                        )

        # -----------------------------
        # 추천 후보 중 한 명 선택
        # -----------------------------
        st.divider()
        st.markdown("## ⭐ 마음에 드는 챔피언 선택하기")

        champion_names = [
            champion["champion"]
            for champion in results
        ]

        selected_champion_name = st.selectbox(
            "추천받은 챔피언 중 한 명을 골라 줘!",
            champion_names,
            key="selected_recommended_champion"
        )

        selected_champion = next(
            champion
            for champion in results
            if champion["champion"] == selected_champion_name
        )

        st.markdown(f"## 🎉 선택한 챔피언은 {selected_champion_name}!")

        # 선택한 챔피언의 큰 이미지
        splash_url = get_champion_image(
            selected_champion,
            "splash"
        )

        if splash_url:
            st.image(splash_url, use_container_width=True)
        else:
            st.warning("이 챔피언의 큰 이미지를 찾지 못했어.")

        if pd.notna(selected_champion.get("title")):
            st.subheader(selected_champion["title"])

        st.write(
            f"**포지션:** "
            f"{get_display_value(selected_champion.get('position'))}"
        )

        st.write(
            f"**유형:** "
            f"{get_display_value(selected_champion.get('type'))}"
        )

        st.write(
            f"**난이도:** "
            f"{get_display_value(selected_champion.get('difficulty'))}"
        )

        if st.session_state.get("score_available", False):
            st.write(
                f"**스타일 점수:** "
                f"{selected_champion['recommendation_score']:.2f}"
            )

        st.success(
            f"{selected_champion_name} 선택 완료! "
            "이제 협곡으로 출발해 보자!"
        )
