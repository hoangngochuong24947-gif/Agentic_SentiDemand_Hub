"""Generate a small synthetic Korean review dataset for local validation."""

from __future__ import annotations

import csv
import json
from pathlib import Path


DATASET = [
    ("wireless_earbuds", 5, "positive", "배송이 빠르고 음질도 깔끔해서 정말 만족스러워요."),
    ("wireless_earbuds", 4, "positive", "착용감이 편하고 배터리도 오래가서 추천합니다."),
    ("wireless_earbuds", 2, "negative", "연결이 자주 끊기고 통화 품질이 별로예요."),
    ("wireless_earbuds", 3, "neutral", "가격 대비 무난하지만 특별한 장점은 잘 모르겠어요."),
    ("skin_care_set", 5, "positive", "향이 부드럽고 피부가 촉촉해져서 재구매하고 싶어요."),
    ("skin_care_set", 4, "positive", "포장이 깔끔하고 선물용으로도 괜찮습니다."),
    ("skin_care_set", 2, "negative", "트러블이 올라와서 환불을 고민 중입니다."),
    ("skin_care_set", 3, "neutral", "흡수는 빠르지만 기대했던 만큼 드라마틱하진 않아요."),
    ("office_chair", 5, "positive", "조립이 쉬웠고 허리를 잘 잡아줘서 오래 앉아도 편해요."),
    ("office_chair", 4, "positive", "바퀴가 부드럽고 디자인도 예뻐서 만족합니다."),
    ("office_chair", 1, "negative", "등받이가 흔들리고 마감이 엉성해서 실망했어요."),
    ("office_chair", 3, "neutral", "쿠션감은 보통이고 가격도 그냥 무난한 편입니다."),
]


def build_rows() -> list[dict]:
    rows = []
    for index, (product, rating, sentiment, comment) in enumerate(DATASET, start=1):
        rows.append(
            {
                "review_id": index,
                "product_id": product,
                "rating": rating,
                "expected_sentiment": sentiment,
                "comment": comment,
                "source": "synthetic_ko",
            }
        )
    return rows


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = repo_root / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = build_rows()
    csv_path = output_dir / "korean_reviews_mock.csv"
    json_path = output_dir / "korean_reviews_mock.json"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)

    print(f"Wrote {len(rows)} mock Korean reviews to {csv_path}")
    print(f"Wrote JSON copy to {json_path}")


if __name__ == "__main__":
    main()
