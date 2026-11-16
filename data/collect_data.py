
from pathlib import Path
import re
import html
import time

import pandas as pd
import requests


# ==========================================
# 기본 설정
# ==========================================

BASE_URL = "https://ddragon.leagueoflegends.com"
LANGUAGE = "ko_KR"

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_DIR / "champions.csv"

TYPE_TRANSLATION = {
    "Fighter": "전사",
    "Tank": "탱커",
    "Mage": "마법사",
    "Assassin": "암살자",
    "Marksman": "원거리 딜러",
    "Support": "서포터",
}


# ==========================================
# 데이터 수집 함수
# ==========================================

def get_json(url):
    """주소에서 JSON 데이터를 가져온다."""
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()


def clean_text(text):
    """HTML 태그와 특수문자를 정리한다."""
    if not text:
        return ""

    text = re.sub(r"<[^>]*>", " ", str(text))
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_latest_version():
    """Data Dragon의 최신 버전을 가져온다."""
    versions = get_json(
        f"{BASE_URL}/api/versions.json"
    )

    if not versions:
        raise ValueError("Data Dragon 버전을 가져오지 못했습니다.")

    return versions[0]


def get_champion_list(version):
    """한국어 챔피언 목록을 가져온다."""
    url = (
        f"{BASE_URL}/cdn/{version}/data/"
        f"{LANGUAGE}/champion.json"
    )

    data = get_json(url)
    return data["data"]


def get_champion_detail(version, champion_id):
    """챔피언 한 명의 상세 정보를 가져온다."""
    url = (
        f"{BASE_URL}/cdn/{version}/data/"
        f"{LANGUAGE}/champion/{champion_id}.json"
    )

    data = get_json(url)
    return data["data"][champion_id]


# ==========================================
# 스킬 설명 기반 점수 계산
# ==========================================

def count_keyword_groups(text, keyword_groups):
    """
    키워드 묶음 중 실제로 등장한 묶음의 개수를 센다.
    같은 묶음에 있는 단어가 여러 번 나와도 1회로 계산한다.
    """
    count = 0

    for group in keyword_groups:
        if any(re.search(keyword, text, re.IGNORECASE) for keyword in group):
            count += 1

    return count


def make_score(text, keyword_groups, base=2):
    """키워드 분석 결과를 1~10점으로 변환한다."""
    count = count_keyword_groups(text, keyword_groups)
    return min(10, max(1, base + count))


MOBILITY_KEYWORDS = [
    [r"돌진", r"질주", r"대시", r"dash"],
    [r"순간이동", r"텔레포트", r"이동한다", r"이동합니다"],
    [r"도약", r"점프", r"뛰어오", r"뛰어넘"],
    [r"굴러", r"구른", r"날아가", r"날아오"],
    [r"이동 속도 증가", r"이동 속도가 증가"],
    [r"벽을 넘", r"지형을 통과", r"공간 이동"],
]

SURVIVABILITY_KEYWORDS = [
    [r"보호막", r"방어막", r"실드"],
    [r"체력을 회복", r"체력 회복", r"치유", r"회복합니다"],
    [r"피해를 감소", r"피해 감소", r"받는 피해"],
    [r"무적", r"피해를 받지 않", r"대상 지정 불가"],
    [r"부활", r"되살아", r"다시 살아"],
    [r"은신", r"투명 상태", r"위장"],
]

TEAM_SUPPORT_KEYWORDS = [
    [r"아군", r"아군 챔피언", r"팀원"],
    [r"보호막", r"방어막", r"실드"],
    [r"회복", r"치유", r"체력을 회복"],
    [r"이동 속도 증가", r"공격 속도 증가"],
    [r"강화", r"능력치를 증가", r"피해량을 증가"],
    [r"정화", r"군중 제어 효과를 제거", r"제거합니다"],
    [r"부활", r"시야를 제공", r"시야를 밝혀"],
]

AOE_KEYWORDS = [
    [r"주변의 적", r"주변 적", r"주변에"],
    [r"모든 적", r"적 모두", r"적 챔피언 모두"],
    [r"범위 내", r"범위 안", r"일정 범위"],
    [r"폭발", r"폭발시", r"폭발하여"],
    [r"지역에", r"지역 내", r"지면에"],
    [r"일직선", r"직선상의", r"관통"],
    [r"광역", r"넓은 범위"],
]

LATE_GAME_KEYWORDS = [
    [r"영구적으로", r"영구히"],
    [r"중첩", r"중첩을 획득", r"중첩이 쌓"],
    [r"최대 중첩", r"중첩에 따라"],
    [r"레벨에 따라", r"레벨이 오를수록"],
    [r"처치할 때마다", r"적을 처치하면", r"처치 시"],
    [r"추가 공격력", r"추가 주문력"],
    [r"최대 체력에 비례", r"잃은 체력에 비례"],
    [r"시간이 지날수록", r"시간에 따라"],
]

CC_KEYWORDS = {
    "기절": [r"기절", r"스턴"],
    "속박": [r"속박", r"움직일 수 없"],
    "둔화": [r"둔화", r"이동 속도를 감소"],
    "공중에 띄움": [r"공중에 띄", r"공중으로 띄", r"공중에"],
    "넉백": [r"밀쳐", r"밀어내", r"넉백"],
    "도발": [r"도발"],
    "공포": [r"공포"],
    "매혹": [r"매혹"],
    "침묵": [r"침묵"],
    "제압": [r"제압"],
    "실명": [r"실명"],
    "변이": [r"변이"],
}


def analyze_champion(champion, detail):
    """
    챔피언의 패시브와 QWER 스킬 설명을 분석해
    추천 시스템에서 사용할 점수를 계산한다.
    """

    passive = detail.get("passive", {})

    skill_texts = [
        passive.get("description", "")
    ]

    for spell in detail.get("spells", []):
        skill_texts.append(spell.get("description", ""))
        skill_texts.append(spell.get("tooltip", ""))

    text = clean_text(" ".join(skill_texts))

    # 기동성
    mobility = make_score(text, MOBILITY_KEYWORDS)

    # 생존력
    survivability = make_score(
        text,
        SURVIVABILITY_KEYWORDS
    )

    # 팀 지원 능력
    team_support = make_score(
        text,
        TEAM_SUPPORT_KEYWORDS
    )

    # 광역 공격 능력
    aoe = make_score(text, AOE_KEYWORDS)

    # 후반 성장 가능성
    late_game = make_score(
        text,
        LATE_GAME_KEYWORDS
    )

    # 사거리: Data Dragon의 기본 공격 사거리 사용
    attack_range = champion.get("stats", {}).get(
        "attackrange", 0
    )

    if attack_range >= 500:
        ranged = 9
    elif attack_range >= 400:
        ranged = 7
    elif attack_range >= 300:
        ranged = 4
    else:
        ranged = 2

    # 군중 제어(CC) 종류 분석
    cc_types = []

    for cc_name, patterns in CC_KEYWORDS.items():
        if any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in patterns
        ):
            cc_types.append(cc_name)

    # CC 종류가 다양할수록 점수 상승
    cc_level = min(10, max(1, 1 + len(cc_types) * 2))

    return {
        "mobility": mobility,
        "late_game": late_game,
        "survivability": survivability,
        "team_support": team_support,
        "aoe": aoe,
        "ranged": ranged,
        "cc_level": cc_level,
        "cc_types": ";".join(cc_types),
    }


# ==========================================
# 챔피언 데이터 정리
# ==========================================

def extract_champion_data(champion, version):
    """챔피언 기본 정보와 스킬 정보를 한 행으로 정리한다."""

    champion_id = champion["id"]

    detail = get_champion_detail(version, champion_id)

    types = [
        TYPE_TRANSLATION.get(tag, tag)
        for tag in champion.get("tags", [])
    ]

    passive = detail.get("passive", {})
    spells = detail.get("spells", [])

    # 스킬 설명을 분석해 추천용 점수 생성
    analyzed = analyze_champion(champion, detail)

    row = {
        # 기본 정보
        "champion": champion["name"],
        "champion_id": champion_id,
        "title": champion.get("title", ""),
        "position": "",
        "type": ";".join(types),

        # 라이엇 공식 평가
        "difficulty": champion.get("info", {}).get("difficulty", ""),
        "attack": champion.get("info", {}).get("attack", ""),
        "defense": champion.get("info", {}).get("defense", ""),
        "magic": champion.get("info", {}).get("magic", ""),

        # 스킬 설명 기반 자체 평가
        "mobility": analyzed["mobility"],
        "late_game": analyzed["late_game"],
        "survivability": analyzed["survivability"],
        "team_support": analyzed["team_support"],
        "aoe": analyzed["aoe"],
        "ranged": analyzed["ranged"],
        "cc_level": analyzed["cc_level"],
        "cc_types": analyzed["cc_types"],

        # 이미지 주소
        "image_url": (
            f"{BASE_URL}/cdn/{version}/img/champion/"
            f"{champion_id}.png"
        ),
        "splash_url": (
            f"{BASE_URL}/cdn/img/champion/splash/"
            f"{champion_id}_0.jpg"
        ),

        # 패시브 스킬
        "passive_name": passive.get("name", ""),
        "passive_description": clean_text(
            passive.get("description", "")
        ),

        # 배경 이야기
        "lore": clean_text(detail.get("lore", "")),

        # 데이터 버전
        "data_version": version,
    }

    # Q, W, E, R 스킬 정보
    skill_keys = ["Q", "W", "E", "R"]

    for index, key in enumerate(skill_keys):
        if index < len(spells):
            spell = spells[index]

            row[f"{key.lower()}_name"] = spell.get(
                "name", ""
            )

            row[f"{key.lower()}_description"] = clean_text(
                spell.get("description", "")
            )

            row[f"{key.lower()}_tooltip"] = clean_text(
                spell.get("tooltip", "")
            )
        else:
            row[f"{key.lower()}_name"] = ""
            row[f"{key.lower()}_description"] = ""
            row[f"{key.lower()}_tooltip"] = ""

    return row


# ==========================================
# 전체 데이터 수집 및 CSV 저장
# ==========================================

def main():
    print("=" * 50)
    print("LOL PICK 챔피언 데이터 수집 시작")
    print("=" * 50)

    version = get_latest_version()
    print(f"\nData Dragon 버전: {version}")

    champions = get_champion_list(version)

    print(f"수집할 챔피언 수: {len(champions)}명\n")

    collected_data = []
    failed_champions = []

    for index, champion in enumerate(
        champions.values(),
        start=1
    ):
        name = champion["name"]

        try:
            row = extract_champion_data(
                champion,
                version
            )

            collected_data.append(row)

            print(
                f"[{index}/{len(champions)}] "
                f"{name} 수집 완료"
            )

        except requests.RequestException as error:
            print(f"[오류] {name}: {error}")
            failed_champions.append(name)

        except (KeyError, ValueError, TypeError) as error:
            print(f"[오류] {name}: {error}")
            failed_champions.append(name)

        time.sleep(0.05)

    if not collected_data:
        print("\n수집된 데이터가 없습니다.")
        return

    df = pd.DataFrame(collected_data)

    df = df.sort_values(
        by="champion",
        ascending=True
    ).reset_index(drop=True)

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n" + "=" * 50)
    print("데이터 수집 완료!")
    print("=" * 50)

    print(f"저장 위치: {OUTPUT_FILE}")
    print(f"수집 성공: {len(collected_data)}명")
    print(f"수집 실패: {len(failed_champions)}명")

    if failed_champions:
        print("\n수집 실패 챔피언:")
        print(", ".join(failed_champions))

    print("\n자동 계산된 추천용 항목:")
    print("- mobility: 기동성")
    print("- late_game: 후반 성장 가능성")
    print("- survivability: 생존력")
    print("- team_support: 팀 지원 능력")
    print("- aoe: 광역 공격 능력")
    print("- ranged: 사거리")
    print("- cc_level: 군중 제어 능력")
    print("- cc_types: 군중 제어 종류")


if __name__ == "__main__":
    main()
