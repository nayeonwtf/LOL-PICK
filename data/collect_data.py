
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

# 이 파일의 상위 폴더(LOL_PICK)를 프로젝트 폴더로 설정
PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_DIR / "champions.csv"

# 라이엇의 분류명을 우리 앱에서 사용할 한국어로 변환
TYPE_TRANSLATION = {
    "Fighter": "전사",
    "Tank": "탱커",
    "Mage": "마법사",
    "Assassin": "암살자",
    "Marksman": "원거리 딜러",
    "Support": "서포터",
}


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


def extract_champion_data(champion, version):
    """챔피언 기본 정보와 스킬 정보를 한 행으로 정리한다."""

    champion_id = champion["id"]

    # 상세 정보 요청
    detail = get_champion_detail(version, champion_id)

    # 챔피언 분류
    types = [
        TYPE_TRANSLATION.get(tag, tag)
        for tag in champion.get("tags", [])
    ]

    # 기본 스킬 정보
    passive = detail.get("passive", {})
    spells = detail.get("spells", [])

    row = {
        # 기본 정보
        "champion": champion["name"],
        "champion_id": champion_id,
        "title": champion.get("title", ""),
        "position": "",
        "type": ";".join(types),

        # 공식 난이도 및 능력치 평가
        "difficulty": champion.get("info", {}).get("difficulty", ""),
        "attack": champion.get("info", {}).get("attack", ""),
        "defense": champion.get("info", {}).get("defense", ""),
        "magic": champion.get("info", {}).get("magic", ""),

        # 추천 시스템에서 직접 채울 항목
        "mobility": "",
        "late_game": "",
        "survivability": "",
        "team_support": "",
        "aoe": "",
        "ranged": "",
        "cc_level": "",
        "cc_types": "",

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

        # 챔피언 기본 배경 이야기
        "lore": clean_text(detail.get("lore", "")),

        # 데이터 출처 버전
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


def main():
    print("=" * 50)
    print("LOL PICK 챔피언 데이터 수집 시작")
    print("=" * 50)

    # 최신 버전 확인
    version = get_latest_version()
    print(f"\nData Dragon 버전: {version}")

    # 전체 챔피언 목록
    champions = get_champion_list(version)

    print(f"수집할 챔피언 수: {len(champions)}명\n")

    collected_data = []
    failed_champions = []

    # 전체 챔피언 상세 정보 수집
    for index, champion in enumerate(
        champions.values(), start=1
    ):
        name = champion["name"]
        champion_id = champion["id"]

        try:
            row = extract_champion_data(
                champion, version
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

        # 서버에 짧은 간격을 두고 요청
        time.sleep(0.05)

    if not collected_data:
        print("\n수집된 데이터가 없습니다.")
        return

    # CSV 저장
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

    print("\n추천 시스템용 수동 입력 항목:")
    print("- position")
    print("- mobility")
    print("- late_game")
    print("- survivability")
    print("- team_support")
    print("- aoe")
    print("- ranged")
    print("- cc_level")
    print("- cc_types")


if __name__ == "__main__":
    main()
