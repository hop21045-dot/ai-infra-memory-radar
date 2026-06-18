from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests

from metrics_config import COMPANIES, CONCEPTS
from seed_data import SEED_FILINGS, SEED_METRICS

SEC_HEADERS = {
    "User-Agent": "ai-infra-memory-dashboard contact@example.com",
    "Accept-Encoding": "gzip, deflate",
}


def utc_now_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def sec_get_json(url: str, timeout: int = 20) -> dict[str, Any]:
    response = requests.get(url, headers=SEC_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.json()


def load_latest_filings(limit_per_company: int = 6) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    forms = {"10-K", "10-Q", "8-K", "6-K", "20-F"}

    for company in COMPANIES:
        url = f"https://data.sec.gov/submissions/CIK{company['cik']}.json"
        try:
            data = sec_get_json(url)
            recent = data.get("filings", {}).get("recent", {})
            for idx, form in enumerate(recent.get("form", [])):
                if form not in forms:
                    continue
                accession = recent.get("accessionNumber", [""])[idx]
                accession_path = accession.replace("-", "")
                primary_doc = recent.get("primaryDocument", [""])[idx]
                rows.append(
                    {
                        "ticker": company["ticker"],
                        "company": company["name"],
                        "group": company["group"],
                        "form": form,
                        "filed": recent.get("filingDate", [""])[idx],
                        "report_date": recent.get("reportDate", [""])[idx],
                        "title": recent.get("primaryDocDescription", [""])[idx] or form,
                        "url": (
                            "https://www.sec.gov/Archives/edgar/data/"
                            f"{int(company['cik'])}/{accession_path}/{primary_doc}"
                        ),
                    }
                )
                if len([r for r in rows if r["ticker"] == company["ticker"]]) >= limit_per_company:
                    break
        except Exception:
            continue

    if not rows:
        seed = pd.DataFrame(SEED_FILINGS)
        companies = pd.DataFrame(COMPANIES)
        seed = seed.merge(companies[["ticker", "name", "group"]], on="ticker", how="left")
        seed["company"] = seed["name"]
        return seed.drop(columns=["name"])
    return pd.DataFrame(rows).sort_values("filed", ascending=False)


def load_company_facts(company: dict[str, str]) -> dict[str, Any] | None:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company['cik']}.json"
    try:
        return sec_get_json(url, timeout=30)
    except Exception:
        return None


def _period_from_fact(fact: dict[str, Any]) -> str | None:
    frame = fact.get("frame")
    if isinstance(frame, str) and frame.startswith("CY") and "Q" in frame:
        year = frame[2:6]
        quarter = frame.split("Q", 1)[1][:1]
        return f"{year}Q{quarter}"

    fp = fact.get("fp")
    fy = fact.get("fy")
    if isinstance(fp, str) and fp.startswith("Q") and fy:
        return f"{fy}{fp}"
    return None


def _facts_for_tags(facts: dict[str, Any], concept: dict[str, Any]) -> list[dict[str, Any]]:
    taxonomy = concept["taxonomy"]
    unit = concept["unit"]
    results: list[dict[str, Any]] = []
    for tag in concept["tags"]:
        tag_facts = facts.get("facts", {}).get(taxonomy, {}).get(tag, {})
        unit_facts = tag_facts.get("units", {}).get(unit, [])
        for fact in unit_facts:
            form = fact.get("form")
            if form not in {"10-Q", "10-K", "20-F", "6-K"}:
                continue
            period = _period_from_fact(fact)
            value = fact.get("val")
            if period and isinstance(value, (int, float)):
                results.append(
                    {
                        "period": period,
                        "value": float(value),
                        "form": form,
                        "filed": fact.get("filed", ""),
                        "tag": tag,
                    }
                )
    return results


def load_metrics() -> tuple[pd.DataFrame, str]:
    rows: list[dict[str, Any]] = []
    for company in COMPANIES:
        facts = load_company_facts(company)
        if not facts:
            continue
        for metric_key, concept in CONCEPTS.items():
            for fact in _facts_for_tags(facts, concept):
                rows.append(
                    {
                        "ticker": company["ticker"],
                        "company": company["name"],
                        "group": company["group"],
                        "metric": metric_key,
                        "metric_label": concept["label"],
                        "period": fact["period"],
                        "value": fact["value"],
                        "filed": fact["filed"],
                        "tag": fact["tag"],
                        "source": "SEC XBRL",
                    }
                )

    if not rows:
        seed = pd.DataFrame(SEED_METRICS)
        companies = pd.DataFrame(COMPANIES)
        seed = seed.merge(companies[["ticker", "name", "group"]], on="ticker", how="left")
        seed["company"] = seed["name"]
        seed["metric_label"] = seed["metric"].map(lambda key: CONCEPTS[key]["label"])
        seed["filed"] = ""
        seed["tag"] = "seed"
        seed["source"] = "Seed fallback"
        return seed.drop(columns=["name"]), "seed"

    data = pd.DataFrame(rows)
    data = data.sort_values(["ticker", "metric", "period", "filed"])
    data = data.drop_duplicates(["ticker", "metric", "period"], keep="last")
    return data, "live"


def add_growth(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data
    data = data.sort_values(["ticker", "metric", "period"]).copy()
    data["qoq"] = data.groupby(["ticker", "metric"])["value"].pct_change()
    data["yoy"] = data.groupby(["ticker", "metric"])["value"].pct_change(4)
    return data


def latest_by_metric(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data
    idx = data.sort_values("period").groupby(["ticker", "metric"])["period"].idxmax()
    return data.loc[idx].sort_values(["group", "ticker", "metric"])
