"""Generate a synthetic Korean review dataset for local and UI validation."""

from __future__ import annotations

import csv
import json
from pathlib import Path


DATASET = [
    ("wireless_earbuds", 5, "positive", "배송이 빠르고 음질이 정말 좋아요. 배터리도 오래가서 출퇴근할 때 만족스럽습니다."),
    ("wireless_earbuds", 5, "positive", "착용감이 편하고 통화 품질도 안정적이에요. 재구매 의사가 있습니다."),
    ("wireless_earbuds", 4, "positive", "디자인이 깔끔하고 연결이 쉬워서 사용하기 편했습니다."),
    ("wireless_earbuds", 2, "negative", "배터리가 너무 빨리 닳고 연결이 자주 끊겨서 불편했습니다."),
    ("wireless_earbuds", 1, "negative", "음질이 기대보다 별로고 잡음이 심해서 실망했어요."),
    ("wireless_earbuds", 3, "neutral", "기본 기능은 무난하지만 가격을 생각하면 아주 특별하진 않습니다."),
    ("wireless_earbuds", 3, "neutral", "케이스 크기는 적당하고 사용법도 단순해서 무난한 편이에요."),
    ("wireless_earbuds", 5, "positive", "노이즈 캔슬링이 훌륭하고 착용해도 귀가 편해서 만족합니다."),
    ("wireless_earbuds", 2, "negative", "마이크 품질이 나쁘고 통화할 때 상대방이 잘 안 들린다고 했어요."),
    ("skin_care_set", 5, "positive", "보습력이 뛰어나고 자극이 없어서 민감한 피부에도 잘 맞았어요."),
    ("skin_care_set", 4, "positive", "향이 은은하고 흡수가 빨라서 아침에 쓰기 좋습니다."),
    ("skin_care_set", 5, "positive", "패키지가 깔끔하고 크림 질감도 부드러워서 만족합니다."),
    ("skin_care_set", 2, "negative", "향이 너무 강하고 바른 뒤에 피부가 따가워서 사용을 멈췄어요."),
    ("skin_care_set", 1, "negative", "가격은 비싼데 효과가 거의 없고 트러블까지 올라왔습니다."),
    ("skin_care_set", 3, "neutral", "수분감은 괜찮지만 기대했던 미백 효과는 아직 모르겠어요."),
    ("skin_care_set", 3, "neutral", "용량은 적당하지만 재구매할 정도로 인상적이진 않았습니다."),
    ("skin_care_set", 5, "positive", "세럼이 산뜻하고 피부결이 부드러워져서 매일 쓰고 있어요."),
    ("skin_care_set", 2, "negative", "펌프가 고장 나서 사용하기 불편했고 내용물도 새어 나왔습니다."),
    ("office_chair", 5, "positive", "조립이 쉬웠고 허리 지지력이 좋아서 장시간 앉아도 편안합니다."),
    ("office_chair", 4, "positive", "쿠션감이 좋고 바퀴가 부드럽게 움직여서 사무실에서 쓰기 좋아요."),
    ("office_chair", 5, "positive", "등받이 각도 조절이 잘 되고 마감도 튼튼해서 만족합니다."),
    ("office_chair", 2, "negative", "나사가 잘 맞지 않고 흔들림이 있어서 안정감이 부족했습니다."),
    ("office_chair", 1, "negative", "앉으면 소음이 크고 쿠션이 금방 꺼져서 품질이 아쉬워요."),
    ("office_chair", 3, "neutral", "기본적인 의자 기능은 충분하지만 특별한 장점은 없습니다."),
    ("office_chair", 3, "neutral", "배송 포장은 괜찮았지만 조립 설명서는 조금 더 친절했으면 좋겠어요."),
    ("office_chair", 5, "positive", "등판 메쉬가 시원하고 팔걸이 높이 조절도 부드러워서 좋습니다."),
    ("office_chair", 2, "negative", "볼트가 부족해서 조립이 번거로웠고 마감 스크래치도 있었습니다."),
    ("robot_vacuum", 5, "positive", "청소가 꼼꼼하고 소음도 적어서 매일 돌리기 좋습니다."),
    ("robot_vacuum", 4, "positive", "앱 연동이 쉬워서 예약 청소를 설정하기 편리했어요."),
    ("robot_vacuum", 5, "positive", "먼지 흡입력이 강하고 배터리도 오래가서 만족합니다."),
    ("robot_vacuum", 2, "negative", "문턱을 잘 넘지 못하고 지도 인식이 자주 꼬여서 답답했어요."),
    ("robot_vacuum", 1, "negative", "흡입력이 약하고 센서가 둔해서 청소가 제대로 안 됩니다."),
    ("robot_vacuum", 3, "neutral", "기본 청소는 가능하지만 앱 기능은 아직 개선이 필요해 보여요."),
    ("robot_vacuum", 3, "neutral", "가격 대비 기능은 무난하지만 프리미엄 느낌은 아닙니다."),
    ("robot_vacuum", 5, "positive", "물걸레 기능도 깔끔하고 코너 먼지까지 잘 잡아줘서 만족해요."),
    ("robot_vacuum", 2, "negative", "충전 도크를 자주 못 찾고 지도 저장도 불안정해서 아쉬웠습니다."),
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
