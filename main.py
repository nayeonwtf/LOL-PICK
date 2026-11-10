
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
# 데이터 요약
# -----------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("전체 챔피언", f"{len(df)}명")

with col2:
    if "position" in df.columns:
        st.metric("포지션 정보", "수집 완료")
    else:
        st.metric("포지션 정보", "확인 필요")

with col3:
    if "type" in df.columns:
        st.metric("챔피언 유형", df["type"].nunique())
    else:
        st.metric("챔피언 유형", "확인 필요")


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

with right:
    st.markdown("### 🔍 조건으로 찾기")
    st.write("포지션과 플레이 스타일을 선택해서 찾아보자.")

    if st.button("조건 선택하러 가기", use_container_width=True):
        st.session_state["show_conditions"] = True


# -----------------------------
# 랜덤 결과
# -----------------------------
if "random_champion" in st.session_state:
    champion = st.session_state["random_champion"]

    st.divider()
    st.markdown("# 🎉 빠밤!")
    st.markdown(f"## 오늘의 챔피언은 {champion['champion']}!")

    image_url = champion.get("splash_url")

    if pd.notna(image_url) and image_url:
        st.image(image_url, use_container_width=True)
    elif pd.notna(champion.get("image_url")):
        st.image(champion["image_url"], width=180)

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
# 조건 선택 화면 (다음 단계에서 구현)
# -----------------------------
if st.session_state.get("show_conditions", False):
    st.divider()
    st.markdown("## 🔍 조건으로 챔피언 찾기")
    st.info("다음 단계에서 포지션, 챔피언 유형, 플레이 스타일 선택 기능을 추가할 거야!")
