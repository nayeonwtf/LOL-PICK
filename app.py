
import random

import pandas as pd
import streamlit as st


# ==========================================
# 기본 설정
# ==========================================

st.set_page_config(
    page_title="LOL PICK",
    page_icon="⚔️",
    layout="wide"
)

DATA_URL = (
    "https://raw.githubusercontent.com/"
    "nayeonwtf/LOL-PICK/main/champions.csv"
)


# ==========================================
# 화면 디자인
# ==========================================

st.markdown("""
<style>
    .main-title {
        text-align: center;
        font-size: 65px;
        font-weight: 900;
        color: #C89B3C;
        margin-top: 35px;
        margin-bottom: 0px;
    }

    .sub-title {
        text-align: center;
        font-size: 20px;
        color: #A09B8C;
        margin-bottom: 45px;
    }

    .choice-title {
        text-align: center;
        font-size: 27px;
        font-weight: bold;
        margin-bottom: 12px;
    }

    .choice-description {
        text-align: center;
        color: #A09B8C;
        font-size: 16px;
        min-height: 55px;
    }

    .champion-name {
        text-align: center;
        font-size: 38px;
        font-weight: bold;
        color: #C89B3C;
    }

    div.stButton > button {
        width: 100%;
        height: 65px;
        border-radius: 12px;
        font-size: 20px;
        font-weight: bold;
        border: 1px solid #C89B3C;
    }

    .footer {
        text-align: center;
        color: #777777;
        margin-top: 80px;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 데이터 불러오기
# ==========================================

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL, encoding="utf-8-sig")
    df = df.dropna(subset=["champion"])
    return df


try:
    champions = load_data()

except Exception as e:
    st.error("챔피언 데이터를 불러오지 못했어.")
    st.info("인터넷 연결이나 GitHub 데이터 주소를 확인해 줘.")
    st.stop()


# ==========================================
# 세션 상태 초기화
# ==========================================

if "view" not in st.session_state:
    st.session_state.view = "home"

if "selected_champion" not in st.session_state:
    st.session_state.selected_champion = None


# ==========================================
# 첫 화면
# ==========================================

st.markdown(
    '<div class="main-title">⚔️ LOL PICK</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">'
    '오늘은 어떤 챔피언과 함께 협곡으로 떠나볼까?'
    '</div>',
    unsafe_allow_html=True
)

if st.session_state.view == "home":

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown(
            '<div class="choice-title">🎲 완전 랜덤 추천</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="choice-description">'
            '아무것도 고민하기 싫다면!<br>'
            '운명에 맡기고 챔피언을 뽑아 보자.'
            '</div>',
            unsafe_allow_html=True
        )

        if st.button("랜덤으로 뽑기!", key="random_button"):
            random_index = random.randrange(len(champions))

            st.session_state.selected_champion = (
                champions.iloc[random_index].to_dict()
            )

            st.session_state.view = "random"

            st.rerun()

    with right:
        st.markdown(
            '<div class="choice-title">🎯 조건에 맞춰 찾기</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="choice-description">'
            '내가 원하는 포지션과 챔피언 유형,<br>'
            '플레이 스타일에 맞는 챔피언을 찾아보자.'
            '</div>',
            unsafe_allow_html=True
        )

        if st.button("조건 선택하러 가기!", key="condition_button"):
            st.session_state.view = "condition"
            st.rerun()


# ==========================================
# 랜덤 추천 결과
# ==========================================

elif st.session_state.view == "random":

    champion = st.session_state.selected_champion

    st.markdown("---")
    st.markdown(
        '<div class="champion-name">🎉 오늘의 운명 챔피언!</div>',
        unsafe_allow_html=True
    )

    st.markdown("")

    image_url = champion.get("splash_url")

    if pd.isna(image_url) or not image_url:
        image_url = champion.get("image_url")

    if image_url and not pd.isna(image_url):
        st.image(image_url, use_container_width=True)

    st.markdown(
        f'<div class="champion-name">'
        f'{champion.get("champion", "이름 없음")}'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div style="text-align:center; font-size:20px;">'
        f'{champion.get("title", "")}'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown("")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("포지션", champion.get("position", "정보 없음"))

    with col2:
        st.metric("챔피언 유형", champion.get("type", "정보 없음"))

    with col3:
        st.metric("난이도", champion.get("difficulty", "정보 없음"))

    st.markdown("")

    if st.button("🎲 다른 챔피언 뽑기"):
        random_index = random.randrange(len(champions))

        st.session_state.selected_champion = (
            champions.iloc[random_index].to_dict()
        )

        st.rerun()

    if st.button("🏠 처음으로 돌아가기"):
        st.session_state.view = "home"
        st.rerun()


# ==========================================
# 조건별 추천 준비 화면
# ==========================================

elif st.session_state.view == "condition":

    st.markdown("---")

    st.markdown(
        '<div class="champion-name">🎯 조건별 챔피언 찾기</div>',
        unsafe_allow_html=True
    )

    st.info(
        "이제 나에게 맞는 챔피언을 찾아보자!\n\n"
        "다음 단계에서 포지션, 챔피언 유형, "
        "플레이 스타일을 선택하는 기능을 추가할 예정이야."
    )

    if st.button("🏠 처음으로 돌아가기"):
        st.session_state.view = "home"
        st.rerun()


# ==========================================
# 하단 문구
# ==========================================

st.markdown(
    '<div class="footer">'
    'LOL PICK | 나에게 맞는 챔피언을 찾아보자!'
    '</div>',
    unsafe_allow_html=True
)
