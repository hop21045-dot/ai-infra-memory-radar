from __future__ import annotations

import pandas as pd
import streamlit as st

from data_sources import add_growth, latest_by_metric, load_latest_filings, load_metrics, utc_now_label
from metrics_config import COMPANIES, CONCEPTS, SIGNAL_WEIGHTS

st.set_page_config(
    page_title="AI 인프라 메모리 레이더",
    page_icon="",
    layout="wide",
)

GROUP_LABELS = {company["group"]: company.get("group_ko", company["group"]) for company in COMPANIES}
METRIC_LABELS = {key: concept["label"] for key, concept in CONCEPTS.items()}
TABLE_COLUMNS = {
    "ticker": "티커",
    "company": "기업",
    "group": "분류",
    "metric_label": "지표",
    "period": "분기",
    "Value": "값",
    "QoQ": "QoQ",
    "YoY": "YoY",
    "tag": "XBRL 태그",
    "source": "출처",
    "filed": "공시일",
    "form": "양식",
    "report_date": "보고기간",
    "title": "제목",
    "url": "링크",
}


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
            score += yoy * SIGNAL_WEIGHTS.get(metric, 0)
            parts.append(f"{METRIC_LABELS.get(metric, metric)}: {pct(yoy)} YoY")
        company = company_map.get(ticker, {})
        rows.append(
            {
                "티커": ticker,
                "기업": company.get("name", ticker),
                "분류": company.get("group_ko", company.get("group", "")),
                "메모리 투자 관점": company.get("memory_angle", ""),
                "시그널 점수": score,
                "최근 변화": ", ".join(parts) if parts else "태그된 과거 데이터가 더 필요함",
            }
        )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values("시그널 점수", ascending=False)


def flatten_chart_columns(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data
    flattened = data.copy()
    flattened.columns = [
        f"{ticker} - {METRIC_LABELS.get(metric, metric)}"
        for ticker, metric in flattened.columns.to_flat_index()
    ]
    return flattened


def quarterly_metric_table(data: pd.DataFrame, metric: str) -> pd.DataFrame:
    rows = data[data["metric"] == metric].copy()
    if rows.empty:
        return pd.DataFrame()
    return rows.pivot_table(index="period", columns="ticker", values="value", aggfunc="last").sort_index()


def rename_table_columns(data: pd.DataFrame) -> pd.DataFrame:
    return data.rename(columns=TABLE_COLUMNS)


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


st.title("AI 인프라 메모리 레이더")
st.caption("메모리 반도체 투자자를 위한 공개 데이터 대시보드: 하이퍼스케일러 설비투자, AI 서버 수요, AI 반도체/네트워킹, 최신 SEC 공시를 추적합니다.")

metrics, mode, metrics_updated = cached_metrics()
filings, filings_updated = cached_filings()
manual = cached_manual_indicators()

with st.sidebar:
    st.header("필터")
    groups = sorted({company["group"] for company in COMPANIES})
    selected_groups = st.multiselect("기업 분류", groups, default=groups, format_func=lambda value: GROUP_LABELS.get(value, value))
    selected_metrics = st.multiselect(
        "지표",
        list(CONCEPTS.keys()),
        default=["capex", "revenue", "rpo"],
        format_func=lambda key: CONCEPTS[key]["label"],
    )
    periods = sorted(metrics["period"].dropna().unique()) if not metrics.empty else []
    selected_periods = st.slider("최근 분기 수", 4, 16, 8)
    st.divider()
    st.write(f"지표 데이터: {'SEC 실시간' if mode == 'live' else '샘플 데이터'}")
    st.write(f"지표 업데이트: {metrics_updated}")
    st.write(f"공시 업데이트: {filings_updated}")
    if st.button("지금 새로고침"):
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
top_cols[0].metric("추적 기업", len(COMPANIES))
top_cols[1].metric("최근 설비투자 합계", money(capex_latest))
top_cols[2].metric("최근 매출 합계", money(revenue_latest))
top_cols[3].metric("최근 SEC 공시", filing_count)

if mode != "live":
    st.warning("SEC 실시간 조회가 실패해 샘플 데이터를 표시하고 있습니다. 네트워크 또는 SEC 요청 제한을 확인하세요.")

tab_overview, tab_quarterly, tab_company, tab_backlog, tab_filings, tab_method = st.tabs(
    ["요약", "분기별 차트", "기업별 상세", "수주/주문 코멘트", "최신 공시", "방법론"]
)

with tab_overview:
    st.subheader("메모리 수요 시그널")
    if signals.empty:
        st.info("아직 표시할 시그널 데이터가 없습니다.")
    else:
        display = signals.copy()
        display["시그널 점수"] = display["시그널 점수"].map(lambda value: f"{value:,.2f}")
        st.dataframe(display, width="stretch", hide_index=True)

    st.subheader("분기별 추세")
    chart_data = filtered.pivot_table(
        index="period",
        columns=["ticker", "metric"],
        values="value",
        aggfunc="last",
    ).sort_index()
    st.line_chart(flatten_chart_columns(chart_data), width="stretch")

    st.subheader("최근 지표")
    latest_display = latest.copy()
    if not latest_display.empty:
        latest_display["Value"] = latest_display["value"].map(money)
        latest_display["QoQ"] = latest_display["qoq"].map(pct)
        latest_display["YoY"] = latest_display["yoy"].map(pct)
        latest_display = rename_table_columns(
            latest_display[["ticker", "company", "group", "metric_label", "period", "Value", "QoQ", "YoY", "tag", "source"]]
        )
        st.dataframe(latest_display, width="stretch", hide_index=True)

with tab_quarterly:
    st.subheader("PDF형 분기별 모니터링")
    st.write("분기 데이터가 누적되면 이 탭에서 지표별 차트와 표를 계속 관리할 수 있습니다.")
    chart_metric = st.selectbox(
        "차트 지표",
        selected_metrics if selected_metrics else list(CONCEPTS.keys()),
        format_func=lambda key: CONCEPTS[key]["label"],
    )
    quarterly = quarterly_metric_table(filtered, chart_metric)
    if quarterly.empty:
        st.info("선택한 조건에 해당하는 분기 데이터가 없습니다.")
    else:
        st.bar_chart(quarterly, width="stretch")
        table = quarterly.copy()
        for col in table.columns:
            table[col] = table[col].map(money)
        st.dataframe(table, width="stretch")

with tab_company:
    tickers = [company["ticker"] for company in COMPANIES if company["group"] in selected_groups]
    selected_ticker = st.selectbox("기업", tickers)
    company_rows = metrics[metrics["ticker"] == selected_ticker].sort_values(["metric", "period"])
    company = next(company for company in COMPANIES if company["ticker"] == selected_ticker)
    st.write(company["memory_angle"])
    if company_rows.empty:
        st.info("이 기업에서 태그된 XBRL 지표를 찾지 못했습니다.")
    else:
        metric_options = company_rows["metric"].unique().tolist()
        metric_choice = st.radio(
            "지표",
            metric_options,
            horizontal=True,
            format_func=lambda key: CONCEPTS.get(key, {}).get("label", key),
        )
        chart_rows = company_rows[company_rows["metric"] == metric_choice]
        st.bar_chart(chart_rows.set_index("period")["value"], width="stretch")
        table = chart_rows.copy()
        table["Value"] = table["value"].map(money)
        table["QoQ"] = table["qoq"].map(pct)
        table["YoY"] = table["yoy"].map(pct)
        st.dataframe(
            rename_table_columns(table[["period", "Value", "QoQ", "YoY", "filed", "tag", "source"]]),
            width="stretch",
            hide_index=True,
        )

with tab_backlog:
    st.subheader("AI 수주잔고, 주문, 코멘트")
    st.write(
        "이 항목들은 표준 XBRL 숫자로 제공되지 않는 경우가 많습니다. 기업이 밝힌 AI 서버 주문, 수주잔고, RPO 코멘트는 "
        "manual_indicators.csv에 출처 링크와 함께 관리하면 SEC 지표 옆에서 함께 볼 수 있습니다."
    )
    if manual.empty:
        st.info("아직 수동 관리 지표가 없습니다.")
    else:
        shown = manual[manual["ticker"].isin([company["ticker"] for company in COMPANIES])].copy()
        shown = shown.rename(
            columns={
                "ticker": "티커",
                "date": "일자",
                "indicator": "지표/코멘트",
                "value": "값",
                "unit": "단위",
                "period": "기간",
                "source": "출처",
                "url": "링크",
                "memory_readthrough": "메모리 투자 관점",
            }
        )
        st.dataframe(
            shown,
            column_config={"링크": st.column_config.LinkColumn("출처 링크")},
            width="stretch",
            hide_index=True,
        )

with tab_filings:
    st.subheader("최신 SEC 공시")
    selected_filing_groups = set(selected_groups)
    filing_display = filings[filings["group"].isin(selected_filing_groups)].copy() if "group" in filings else filings
    if filing_display.empty:
        st.info("표시할 최근 공시가 없습니다.")
    else:
        filing_display = rename_table_columns(
            filing_display[["ticker", "company", "group", "form", "filed", "report_date", "title", "url"]]
        )
        st.dataframe(
            filing_display,
            column_config={"링크": st.column_config.LinkColumn("SEC 문서")},
            width="stretch",
            hide_index=True,
        )

with tab_method:
    st.subheader("자동 업데이트되는 것")
    st.write(
        "앱은 SEC submissions와 XBRL company facts를 주기적으로 조회합니다. 매출, 설비투자, 일부 RPO처럼 SEC에 "
        "태그된 숫자는 공시 반영 후 자동으로 업데이트될 수 있습니다. 다만 기업별 AI 수주잔고 코멘트는 XBRL 태그가 없는 "
        "경우가 많아 IR 자료, 실적발표, 컨퍼런스콜, 수동 구조화 노트가 필요합니다."
    )
    st.subheader("추적 지표")
    concept_rows = []
    for key, concept in CONCEPTS.items():
        concept_rows.append(
            {
                "지표": key,
                "이름": concept["label"],
                "재무제표": concept["statement"],
                "조회 XBRL 태그": ", ".join(concept["tags"]),
            }
        )
    st.dataframe(pd.DataFrame(concept_rows), width="stretch", hide_index=True)
    st.subheader("해석 기준")
    st.write(
        "하이퍼스케일러 설비투자 증가, AI 서버 OEM 매출/수주잔고 증가, AI 네트워킹/커스텀 반도체 매출 증가, NVIDIA "
        "데이터센터 매출 증가는 HBM과 고용량 서버 DRAM에 대체로 긍정적입니다. 반대로 메모리 재고 증가는 수요와 가격이 "
        "따라오기 전까지 부정적 신호로 봅니다."
    )
