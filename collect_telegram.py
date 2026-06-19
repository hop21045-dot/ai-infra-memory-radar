from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path

import pandas as pd


WATCHLIST_COLUMNS = [
    "date",
    "category",
    "company",
    "ticker",
    "topic",
    "channel_summary",
    "channel_url",
    "official_material",
    "official_url",
    "verification_status",
    "correction",
    "reflected_indicator",
    "action",
]

KEYWORDS = {
    "Oracle": ["oracle", "orcl", "oci", "rpo"],
    "Dell Technologies": ["dell", "dell technologies", "isg", "ai server"],
    "Hewlett Packard Enterprise": ["hpe", "hewlett", "ai systems", "greenlake"],
    "Broadcom": ["broadcom", "avgo", "브로드컴", "asic", "xp u", "xpu"],
    "NVIDIA": ["nvidia", "nvda", "엔비디아", "gpu", "blackwell", "feynman"],
    "TSMC": ["tsmc", "cowos", "copos", "advanced packaging", "패키징"],
    "Memory": ["hbm", "dram", "nand", "memory", "메모리", "sk hynix", "samsung", "micron"],
    "AI infrastructure": ["data center", "datacenter", "데이터센터", "capex", "backlog", "ai infrastructure"],
}

HIGH_SIGNAL_TERMS = [
    "rpo",
    "backlog",
    "수주잔고",
    "orders",
    "capex",
    "설비투자",
    "data center",
    "데이터센터",
    "oci",
    "ai server",
    "ai systems",
    "asic",
    "xpu",
    "hbm",
    "dram",
    "nand",
    "cowos",
    "copos",
    "advanced packaging",
]

LOW_SIGNAL_TERMS = ["목표주가", "투자의견", "헤지펀드", "주가", "관세", "트럼프"]

TICKERS = {
    "Oracle": "ORCL",
    "Dell Technologies": "DELL",
    "Hewlett Packard Enterprise": "HPE",
    "Broadcom": "AVGO",
    "NVIDIA": "NVDA",
    "TSMC": "TSM",
    "Memory": "",
    "AI infrastructure": "",
}


@dataclass
class Channel:
    channel: str
    display_name: str


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_channels(path: Path = Path("telegram_channels.csv")) -> list[Channel]:
    if not path.exists():
        return [Channel("bornlupin", "루팡 Invest")]
    rows = pd.read_csv(path).fillna("")
    return [Channel(row["channel"], row.get("display_name", row["channel"])) for _, row in rows.iterrows()]


def score_message(text: str, company: str) -> int:
    lower = text.lower()
    score = 2 if company else 0
    score += sum(1 for term in HIGH_SIGNAL_TERMS if term.lower() in lower)
    score -= sum(1 for term in LOW_SIGNAL_TERMS if term.lower() in lower)
    return max(score, 0)


def classify_message(text: str) -> tuple[str, str, str, str, int]:
    lower = text.lower()
    matches = []
    for company, words in KEYWORDS.items():
        hit_count = sum(1 for word in words if word.lower() in lower)
        if hit_count:
            matches.append((company, hit_count))
    if not matches:
        return "", "", "", "", 0
    matches.sort(key=lambda item: (score_message(text, item[0]), item[1]), reverse=True)
    company = matches[0][0]
    ticker = TICKERS.get(company, "")
    topic = " / ".join(company for company, _ in matches[:3])
    indicators = []
    if any(word in lower for word in ["rpo", "backlog", "수주잔고"]):
        indicators.append("rpo/backlog")
    if any(word in lower for word in ["capex", "설비투자"]):
        indicators.append("capex")
    if any(word in lower for word in ["revenue", "매출"]):
        indicators.append("revenue")
    if any(word in lower for word in ["hbm", "dram", "nand", "메모리"]):
        indicators.append("memory_comment")
    return company, ticker, topic, "; ".join(indicators) or "company_comment", score_message(text, company)


def compact_summary(text: str, max_len: int = 240) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1].rstrip() + "..."


def existing_keys(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    rows = pd.read_csv(path).fillna("")
    return set(zip(rows.get("date", ""), rows.get("channel_url", "")))


async def collect(args: argparse.Namespace) -> int:
    try:
        from telethon import TelegramClient
    except ImportError as exc:
        raise SystemExit("telethon이 필요합니다. `pip install telethon pandas` 실행 후 다시 시도하세요.") from exc

    load_dotenv()
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    if not api_id or not api_hash:
        raise SystemExit(".env에 TELEGRAM_API_ID와 TELEGRAM_API_HASH를 설정하세요.")

    watchlist_path = Path(args.output)
    seen = existing_keys(watchlist_path)
    channels = load_channels(Path(args.channels))
    new_rows = []

    async with TelegramClient(args.session, int(api_id), api_hash) as client:
        for channel in channels:
            async for message in client.iter_messages(channel.channel, limit=args.limit):
                text = message.message or ""
                if not text.strip():
                    continue
                company, ticker, topic, reflected, relevance_score = classify_message(text)
                if not topic or relevance_score < args.min_score:
                    continue
                msg_date = message.date.astimezone(timezone.utc).date().isoformat()
                url = f"https://t.me/{channel.channel}/{message.id}"
                key = (msg_date, url)
                if key in seen:
                    continue
                new_rows.append(
                    {
                        "date": msg_date,
                        "category": f"Telegram:{channel.display_name}",
                        "company": company,
                        "ticker": ticker,
                        "topic": topic,
                        "channel_summary": compact_summary(text),
                        "channel_url": url,
                        "official_material": "Earnings release / IR deck / 10-Q or 10-K / conference call transcript",
                        "official_url": "",
                        "verification_status": "공식자료 확인 필요",
                        "correction": "채널 글은 수요 신호로만 사용하고 숫자는 공식자료로 재확인",
                        "reflected_indicator": reflected,
                        "action": "공식자료 링크와 수치 확인 후 관련 CSV 업데이트",
                    }
                )

    if not new_rows:
        return 0

    file_exists = watchlist_path.exists()
    with watchlist_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=WATCHLIST_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)
    return len(new_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Telegram posts into source_watchlist.csv")
    parser.add_argument("--channels", default="telegram_channels.csv")
    parser.add_argument("--output", default="source_watchlist.csv")
    parser.add_argument("--session", default="telegram_collector")
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--min-score", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    import asyncio

    added = asyncio.run(collect(parse_args()))
    print(f"added_rows={added}")


if __name__ == "__main__":
    main()
