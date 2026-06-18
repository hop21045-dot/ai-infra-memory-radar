from __future__ import annotations

import pandas as pd
import streamlit as st

from data_sources import add_growth, latest_by_metric, load_latest_filings, load_metrics, utc_now_label
from metrics_config import COMPANIES, CONCEPTS, SIGNAL_WEIGHTS

st.set_page_config(
    page_title="AI Infra Memory Radar",
    page_icon="",
    layout="wide",
)


def money(value: float) -> str:
    if pd.isna(value):
        return "-"
    sign = "-" if value < 0 else ""
    value = abs(float(value))
    if value >= 1_000_000_000:
        return f"{sign}${value / 1_000_000_000:,.1f}B"
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:,.1f}M"
    return f"{sign}${value:,.0f}"


def pct(value: float) -> str:
    if pd.isna(value):
        return "-"
    return f"{value * 100:,.1f}%"


def signal_table(latest: pd.DataFrame) -> pd.DataFrame:
    rows = []
    company_map = {company["ticker"]: company for company in COMPANIES}
    for ticker, group in latest.groupby("ticker"):
        score = 0.0
        parts = []
        for _, row in group.iterrows():
            metric = row["metric"]
            yoy = row.get("yoy")
            if pd.isna(yoy):
                continue
            weighted = yoy * SIGNAL_WEIGHTS.get(metric, 0)
            score += weighted
            parts.append(f"{metric}: {pct(yoy)} YoY")
        company = company_map.get(ticker, {})
        rows.append(
            {
                "Ticker": ticker,
                "Company": company.get("name", ticker),
                "Group": company.get("group", ""),
                "Memory Read-Through": company.get("memory_angle", ""),
                "Signal Score": score,
                "Latest Detail": ", ".join(parts) if parts else "Needs more tagged history",
            }
        )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values("Signal Score", ascending=False)


@st.cache_data(ttl=900, show_spinner=False)
def cached_metrics() -> tuple[pd.DataFrame, str, str]:
    data, mode = load_metrics()
    return add_growth(data), mode, utc_now_label()


@st.cache_data(ttl=300, show_spinner=False)
def cached_filings() -> tuple[pd.DataFrame, str]:
    return load_latest_filings(), utc_now_label()


@st.cache_data(ttl=300, show_spinner=False)
def cached_manual_indicators() -> pd.DataFrame:
    try:
        return pd.read_csv("manual_indicators.csv")
    except FileNotFoundError:
        return pd.DataFrame(
            columns=["ticker", "date", "indicator", "value", "unit", "period", "source", "url", "memory_readthrough"]
        )


st.title("AI Infra Memory Radar")
st.caption("Public-data dashboard for memory semiconductor investors: hyperscaler capex, AI server demand, AI silicon/networking, and latest SEC filings.")

metrics, mode, metrics_updated = cached_metrics()
filings, filings_updated = cached_filings()
manual = cached_manual_indicators()

with st.sidebar:
    st.header("Filters")
    groups = sorted({company["group"] for company in COMPANIES})
    selected_groups = st.multiselect("Company groups", groups, default=groups)
    selected_metrics = st.multiselect(
        "Metrics",
        list(CONCEPTS.keys()),
        default=["capex", "revenue", "rpo"],
        format_func=lambda key: CONCEPTS[key]["label"],
    )
    periods = sorted(metrics["period"].dropna().unique()) if not metrics.empty else []
    selected_periods = st.slider("Recent periods", 4, 16, 8)
    st.divider()
    st.write(f"Metric data: {'SEC live' if mode == 'live' else 'seed fallback'}")
    st.write(f"Metrics updated: {metrics_updated}")
    st.write(f"Filings updated: {filings_updated}")
    if st.button("Refresh now"):
        st.cache_data.clear()
        st.rerun()

filtered = metrics[
    metrics["group"].isin(selected_groups) & metrics["metric"].isin(selected_metrics)
].copy()
if periods:
    keep_periods = periods[-selected_periods:]
    filtered = filtered[filtered["period"].isin(keep_periods)]

latest = latest_by_metric(filtered)
signals = signal_table(latest)

top_cols = st.columns(4)
capex_latest = latest[latest["metric"] == "capex"]["value"].sum()
revenue_latest = latest[latest["metric"] == "revenue"]["value"].sum()
rpo_latest = latest[latest["metric"] == "rpo"]["value"].sum()
filing_count = len(filings)
top_cols[0].metric("Tracked Companies", len(COMPANIES))
top_cols[1].metric("Latest Capex Snapshot", money(capex_latest))
top_cols[2].metric("Latest Revenue Snapshot", money(revenue_latest))
top_cols[3].metric("Recent SEC Filings", filing_count)

if mode != "live":
    st.warning("SEC live fetch was unavailable, so the app is showing bundled seed data. Check network access or SEC rate limits.")

tab_overview, tab_company, tab_backlog, tab_filings, tab_method = st.tabs(
    ["Overview", "Company Drilldown", "Backlog & Orders", "Latest Filings", "Method"]
)

with tab_overview:
    st.subheader("Memory Demand Signal")
    if signals.empty:
        st.info("No signal rows available yet.")
    else:
        display = signals.copy()
        display["Signal Score"] = display["Signal Score"].map(lambda value: f"{value:,.2f}")
        st.dataframe(display, use_container_width=True, hide_index=True)

    st.subheader("Quarterly Trend")
    chart_data = filtered.pivot_table(
        index="period",
        columns=["ticker", "metric"],
        values="value",
        aggfunc="last",
    ).sort_index()
    st.line_chart(chart_data, use_container_width=True)

    st.subheader("Latest Metrics")
    latest_display = latest.copy()
    if not latest_display.empty:
        latest_display["Value"] = latest_display["value"].map(money)
        latest_display["QoQ"] = latest_display["qoq"].map(pct)
        latest_display["YoY"] = latest_display["yoy"].map(pct)
        st.dataframe(
            latest_display[
                ["ticker", "company", "group", "metric_label", "period", "Value", "QoQ", "YoY", "tag", "source"]
            ],
            use_container_width=True,
            hide_index=True,
        )

with tab_company:
    tickers = [company["ticker"] for company in COMPANIES if company["group"] in selected_groups]
    selected_ticker = st.selectbox("Company", tickers)
    company_rows = metrics[metrics["ticker"] == selected_ticker].sort_values(["metric", "period"])
    company = next(company for company in COMPANIES if company["ticker"] == selected_ticker)
    st.write(company["memory_angle"])
    if company_rows.empty:
        st.info("No tagged XBRL metrics found for this company.")
    else:
        metric_options = company_rows["metric"].unique().tolist()
        metric_choice = st.radio(
            "Metric",
            metric_options,
            horizontal=True,
            format_func=lambda key: CONCEPTS.get(key, {}).get("label", key),
        )
        chart_rows = company_rows[company_rows["metric"] == metric_choice]
        st.bar_chart(chart_rows.set_index("period")["value"], use_container_width=True)
        table = chart_rows.copy()
        table["Value"] = table["value"].map(money)
        table["QoQ"] = table["qoq"].map(pct)
        table["YoY"] = table["yoy"].map(pct)
        st.dataframe(
            table[["period", "Value", "QoQ", "YoY", "filed", "tag", "source"]],
            use_container_width=True,
            hide_index=True,
        )

with tab_backlog:
    st.subheader("AI Backlog, Orders and Commentary")
    st.write(
        "These items are often not standardized XBRL facts. Keep them in manual_indicators.csv with source links, "
        "then let the dashboard show them beside SEC-derived metrics."
    )
    if manual.empty:
        st.info("No manual indicators found yet.")
    else:
        shown = manual[manual["ticker"].isin([company["ticker"] for company in COMPANIES])].copy()
        st.dataframe(
            shown,
            column_config={"url": st.column_config.LinkColumn("Source link")},
            use_container_width=True,
            hide_index=True,
        )

with tab_filings:
    st.subheader("Latest SEC Filings")
    selected_filing_groups = set(selected_groups)
    filing_display = filings[filings["group"].isin(selected_filing_groups)].copy() if "group" in filings else filings
    if filing_display.empty:
        st.info("No recent filings available.")
    else:
        st.dataframe(
            filing_display[["ticker", "company", "group", "form", "filed", "report_date", "title", "url"]],
            column_config={"url": st.column_config.LinkColumn("SEC document")},
            use_container_width=True,
            hide_index=True,
        )

with tab_method:
    st.subheader("What Updates Automatically")
    st.write(
        "The app polls SEC submissions and XBRL company facts. SEC-tagged figures such as revenue, capex and some "
        "remaining-performance-obligation disclosures can update shortly after filings are disseminated. Company-specific "
        "AI backlog commentary still requires filings, IR releases, earnings-call transcripts, or manual structured notes "
        "when it is not XBRL-tagged."
    )
    st.subheader("Tracked Concepts")
    concept_rows = []
    for key, concept in CONCEPTS.items():
        concept_rows.append(
            {
                "Metric": key,
                "Label": concept["label"],
                "Statement": concept["statement"],
                "XBRL Tags Tried": ", ".join(concept["tags"]),
            }
        )
    st.dataframe(pd.DataFrame(concept_rows), use_container_width=True, hide_index=True)
    st.subheader("Interpretation")
    st.write(
        "Higher hyperscaler capex, AI server OEM revenue/backlog, AI networking/custom silicon revenue and NVIDIA data center "
        "revenue are generally positive read-throughs for HBM and high-capacity server DRAM. Rising memory inventory is treated "
        "as a negative signal until demand or pricing catches up."
    )
