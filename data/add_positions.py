
from pathlib import Path
from io import StringIO
import re
import time

import pandas as pd
import requests


# ==========================================
# 기본 설정
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
CSV_FILE = PROJECT_DIR / "champions.csv"

WIKI_URL = (
    "https://wiki.leagueoflegends.com/"
    "en-us/List_of_champions_by_draft_position"
)

POSITION_COLUMNS = {
    "top": "탑",
    "jungle": "정글",
    "middle": "미드",
    "bottom": "원딜",
    "support": "서포터",
}


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
# 위키 데이터 가져오기
# ==========================================

def get_wiki_tables():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }

    print("위키 페이지 접속 중...")

    response = requests.get(
        WIKI_URL,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    print("위키 페이지 접속 성공!")

    return pd.read_html(StringIO(response.text))


# ==========================================
# 포지션 표 찾기
# ==========================================

def find_role_table(tables):

    for table in tables:

        columns = []

        for col in table.columns:

            if isinstance(col, tuple):
                name = " ".join(map(str, col))
            else:
                name = str(col)

            columns.append(name.lower())

        table.columns = columns

        all_columns = " ".join(columns)

        if (
            "champion" in all_columns
            and "jungle" in all_columns
            and "support" in all_columns
        ):
            print("챔피언 포지션 표 발견!")
            return table

    raise ValueError(
        "위키에서 포지션 표를 찾지 못했습니다. "
        "위키 표의 구조가 변경되었을 수 있습니다."
    )


# ==========================================
# 열 이름 찾기
# ==========================================

def find_column(table, keyword):

    for col in table.columns:

        if keyword in str(col).lower():
            return col

    raise ValueError(
        f"'{keyword}' 포지션 열을 찾지 못했습니다."
    )


# ==========================================
# 포지션 데이터 정리
# ==========================================

def make_position_data(table):

    champion_col = find_column(
        table,
        "champion"
    )

    position_cols = {}

    for english, korean in POSITION_COLUMNS.items():

        position_cols[english] = find_column(
            table,
            english
        )

    role_data = {}

    for _, row in table.iterrows():

        name = str(row[champion_col]).strip()

        if not name or name.lower() == "nan":
            continue

        positions = []

        for english, korean in POSITION_COLUMNS.items():

            value = str(
                row[position_cols[english]]
            ).lower()

            if (
                "yes" in value
                or "3p" in value
                or value.strip() == "true"
            ):
                positions.append(korean)

        role_data[normalize(name)] = positions

    return role_data


# ==========================================
# CSV에 포지션 저장
# ==========================================

def main():

    print("포지션 데이터 수집 시작")

    if not CSV_FILE.exists():
        raise FileNotFoundError(
            "champions.csv 파일을 찾을 수 없습니다."
        )

    champions = pd.read_csv(
        CSV_FILE,
        encoding="utf-8-sig"
    )

    tables = get_wiki_tables()

    role_table = find_role_table(tables)

    role_data = make_position_data(role_table)

    aliases = {
        "monkeyking": "wukong",
    }

    positions_result = []
    unmatched = []

    for _, champion in champions.iterrows():

        champion_id = normalize(
            champion["champion_id"]
        )

        lookup_id = aliases.get(
            champion_id,
            champion_id
        )

        positions = role_data.get(lookup_id)

        if positions is None:
            unmatched.append(
                champion["champion_id"]
            )
            positions_result.append("")
        else:
            positions_result.append(
                ";".join(positions)
            )

    champions["position"] = positions_result

    champions.to_csv(
        CSV_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    matched = len(champions) - len(unmatched)

    print("==============================")
    print("포지션 데이터 수집 완료")
    print(f"전체 챔피언: {len(champions)}명")
    print(f"포지션 확인: {matched}명")
    print(f"확인 필요: {len(unmatched)}명")

    if unmatched:
        print("확인하지 못한 챔피언:")
        print(unmatched)

    print("==============================")


if __name__ == "__main__":
    main()
