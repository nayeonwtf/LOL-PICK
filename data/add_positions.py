
from pathlib import Path
from io import StringIO
import re

import pandas as pd


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


def normalize(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def main():
    print("포지션 데이터 수집 시작")

    champions = pd.read_csv(CSV_FILE, encoding="utf-8-sig")

    response = pd.io.common.urlopen(WIKI_URL)
    html = response.read().decode("utf-8")

    tables = pd.read_html(StringIO(html))

    role_table = None

    for table in tables:
        table.columns = [
            " ".join(map(str, col)).lower()
            if isinstance(col, tuple)
            else str(col).lower()
            for col in table.columns
        ]

        columns = " ".join(table.columns)

        if (
            "champion" in columns
            and "jungle" in columns
            and "support" in columns
        ):
            role_table = table
            break

    if role_table is None:
        raise ValueError("포지션 표를 찾지 못했습니다.")

    def find_column(keyword):
        for col in role_table.columns:
            if keyword in col:
                return col
        raise ValueError(f"{keyword} 열을 찾지 못했습니다.")

    champion_col = find_column("champion")

    role_data = {}

    for _, row in role_table.iterrows():
        name = str(row[champion_col]).strip()

        if not name or name.lower() == "nan":
            continue

        positions = []

        for english, korean in POSITION_COLUMNS.items():
            col = find_column(english)
            value = str(row[col]).lower()

            if "yes" in value or "3p" in value:
                positions.append(korean)

        role_data[normalize(name)] = positions

    # 위키와 Data Dragon의 챔피언 ID 차이 보정
    aliases = {
        "monkeyking": "wukong",
    }

    result = []
    unmatched = []

    for _, champion in champions.iterrows():
        champion_id = normalize(champion["champion_id"])
        lookup_id = aliases.get(champion_id, champion_id)

        positions = role_data.get(lookup_id)

        if positions is None:
            unmatched.append(champion["champion_id"])
            result.append("")
        else:
            result.append(";".join(positions))

    champions["position"] = result

    champions.to_csv(
        CSV_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print("포지션 데이터 저장 완료")
    print(f"전체 챔피언: {len(champions)}명")
    print(f"포지션 확인: {len(champions) - len(unmatched)}명")
    print(f"확인 필요: {len(unmatched)}명")

    if unmatched:
        print("확인하지 못한 챔피언:", unmatched)


if __name__ == "__main__":
    main()
