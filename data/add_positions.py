
from pathlib import Path
from io import StringIO
import re

import pandas as pd
import requests


# ==========================================
# 파일 위치
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
CSV_FILE = PROJECT_DIR / "champions.csv"

GIST_API_URL = (
    "https://api.github.com/gists/"
    "4dcc62d4dc444d7f71c50f78bacfbf71"
)


# ==========================================
# 이름 정리
# ==========================================

def normalize(value):
    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).lower()
    )


# ==========================================
# 외부 포지션 데이터 가져오기
# ==========================================

def get_position_data():

    print("공개 챔피언 데이터 접속 중...")

    response = requests.get(
        GIST_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "LOL-PICK"
        },
        timeout=30
    )

    response.raise_for_status()

    gist = response.json()

    csv_file = None

    for filename, info in gist["files"].items():

        if "champions.csv" in filename.lower():
            csv_file = info
            break

    if csv_file is None:
        raise ValueError(
            "공개 데이터에서 champions.csv를 찾지 못했습니다."
        )

    content = csv_file.get("content")

    if not content:
        raw_url = csv_file["raw_url"]

        raw_response = requests.get(
            raw_url,
            headers={"User-Agent": "LOL-PICK"},
            timeout=30
        )

        raw_response.raise_for_status()
        content = raw_response.text

    data = pd.read_csv(
        StringIO(content),
        encoding="utf-8"
    )

    print("공개 챔피언 데이터 가져오기 성공!")

    return data


# ==========================================
# 포지션 이름 변환
# ==========================================

POSITION_MAP = {
    "top": "탑",
    "jungle": "정글",
    "middle": "미드",
    "mid": "미드",
    "bottom": "원딜",
    "bot": "원딜",
    "support": "서포터",
}


# ==========================================
# 챔피언 이름 예외 처리
# ==========================================

ALIASES = {
    "monkeyking": "wukong",
    "nunu": "nunuandwillump",
    "drmundo": "drmundo",
}


# ==========================================
# 메인 실행
# ==========================================

def main():

    print("포지션 데이터 수집 시작")

    if not CSV_FILE.exists():
        raise FileNotFoundError(
            "champions.csv 파일이 없습니다."
        )

    champions = pd.read_csv(
        CSV_FILE,
        encoding="utf-8-sig"
    )

    source = get_position_data()

    required_columns = ["Name", "Role"]

    for column in required_columns:
        if column not in source.columns:
            raise ValueError(
                f"외부 데이터에 {column} 열이 없습니다. "
                f"현재 열: {list(source.columns)}"
            )

    role_data = {}

    for _, row in source.iterrows():

        name = normalize(row["Name"])
        role_text = str(row["Role"])

        if not name or name == "nan":
            continue

        positions = []

        for role in role_text.split(","):

            key = normalize(role)

            for english, korean in POSITION_MAP.items():

                if key == normalize(english):
                    if korean not in positions:
                        positions.append(korean)

        role_data[name] = positions

    result = []
    unmatched = []

    for _, champion in champions.iterrows():

        champion_id = normalize(
            champion["champion_id"]
        )

        lookup_id = ALIASES.get(
            champion_id,
            champion_id
        )

        positions = role_data.get(lookup_id)

        if positions is None:

            unmatched.append(
                champion["champion_id"]
            )

            result.append("")

        else:

            result.append(
                ";".join(positions)
            )

    champions["position"] = result

    champions.to_csv(
        CSV_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print("==============================")
    print("포지션 데이터 수집 완료")
    print(f"전체 챔피언: {len(champions)}명")
    print(
        f"포지션 확인: "
        f"{len(champions) - len(unmatched)}명"
    )
    print(f"확인 필요: {len(unmatched)}명")

    if unmatched:
        print("확인하지 못한 챔피언:")
        print(unmatched)

    print("==============================")


if __name__ == "__main__":
    main()
