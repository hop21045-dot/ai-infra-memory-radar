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


@st.cache_data(ttl=300, show_spinner=False)
def cached_manual_quarterly() -> pd.DataFrame:
    try:
        return pd.read_csv("manual_quarterly_indicators.csv")
    except FileNotFoundError:
        return pd.DataFrame(
            columns=["ticker", "company", "group", "period", "indicator", "value", "unit", "source", "url", "note"]
        )


def format_manual_value(value: float, unit: str) -> str:
    if pd.isna(value):
        return "-"
    if unit == "USD_BN":
        return f"${value:,.1f}B"
    if unit == "USD_MN":
        return f"${value:,.0f}M"
    if unit == "PCT":
        return f"{value:,.1f}%"
    return f"{value:,.1f}"


def latest_manual_value(data: pd.DataFrame, ticker: str, indicator: str) -> str:
    rows = data[(data["ticker"] == ticker) & (data["indicator"] == indicator)].sort_values("period")
    if rows.empty:
        return "-"
    row = rows.iloc[-1]
    return format_manual_value(row["value"], row["unit"])


def build_chain_snapshot(latest: pd.DataFrame, manual_quarterly: pd.DataFrame) -> pd.DataFrame:
    big4 = latest[(latest["ticker"].isin(["MSFT", "GOOGL", "META", "AMZN"])) & (latest["metric"] == "capex")]
    big4_period = big4["period"].max() if not big4.empty else "-"
    big4_capex = money(big4["value"].sum()) if not big4.empty else "-"
    rows = [
        {
            "단계": "1. 수요 예약",
            "핵심 지표": "RPO / 수주잔고 / 장기계약",
            "현재 확인값": f"Oracle RPO {latest_manual_value(manual_quarterly, 'ORCL', 'rpo')}",
            "메모리 해석": "향후 데이터센터 증설과 서버 주문의 선행 신호",
        },
        {
            "단계": "2. 설비투자",
            "핵심 지표": "하이퍼스케일러 CAPEX",
            "현재 확인값": f"Big4 {big4_period} {big4_capex}",
            "메모리 해석": "AI 클러스터, 전력, 데이터센터 투자 강도",
        },
        {
            "단계": "3. 서버/시스템 전환",
            "핵심 지표": "Dell/HPE AI 서버 주문 및 수주잔고",
            "현재 확인값": f"Dell {latest_manual_value(manual_quarterly, 'DELL', 'ai_backlog')}, HPE {latest_manual_value(manual_quarterly, 'HPE', 'ai_backlog')}",
            "메모리 해석": "HBM 탑재 GPU 서버와 DDR5/eSSD 수요 확인",
        },
        {
            "단계": "4. ASIC/네트워킹",
            "핵심 지표": "Broadcom AI 반도체 매출",
            "현재 확인값": f"Broadcom {latest_manual_value(manual_quarterly, 'AVGO', 'ai_semiconductor_revenue')}",
            "메모리 해석": "커스텀 ASIC, 스위치, 광통신까지 확산되는지 확인",
        },
        {
            "단계": "5. 메모리 실적",
            "핵심 지표": "HBM/DRAM/NAND 매출, 재고, CAPEX",
            "현재 확인값": f"Micron 재고 {money(latest[(latest['ticker'] == 'MU') & (latest['metric'] == 'inventory')]['value'].sum())}",
            "메모리 해석": "수요가 실제 가격, 출하, 재고 개선으로 연결되는지 검증",
        },
    ]
    return pd.DataFrame(rows)


def manual_comparison_table(data: pd.DataFrame, indicators: list[str]) -> pd.DataFrame:
    rows = data[data["indicator"].isin(indicators)].copy()
    if rows.empty:
        return pd.DataFrame()
    rows["표시값"] = rows.apply(lambda row: format_manual_value(row["value"], row["unit"]), axis=1)
    return rows.pivot_table(index=["ticker", "company"], columns=["period", "indicator"], values="표시값", aggfunc="last")


st.title("AI 인프라 메모리 레이더")
st.caption("메모리 반도체 투자자를 위한 공개 데이터 대시보드: 하이퍼스케일러 설비투자, AI 서버 수요, AI 반도체/네트워킹, 최신 SEC 공시를 추적합니다.")

metrics, mode, metrics_updated = cached_metrics()
filings, filings_updated = cached_filings()
manual = cached_manual_indicators()
manual_quarterly = cached_manual_quarterly()

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

tab_overview, tab_chain, tab_quarterly, tab_company, tab_backlog, tab_filings, tab_method = st.tabs(
    ["요약", "AI 인프라 체인", "분기별 비교", "기업별 상세", "수주/주문 코멘트", "최신 공시", "방법론"]
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

with tab_chain:
    st.subheader("AI 인프라 투자 체인")
    st.write("CAPEX 총액만 보지 않고 수요 예약, 설비투자, 서버/OEM 전환, ASIC/네트워킹, 메모리 실적으로 이어지는지 순서대로 확인합니다.")
    st.dataframe(build_chain_snapshot(latest, manual_quarterly), width="stretch", hide_index=True)

    st.subheader("핵심 선행지표 비교")
    chain_indicators = ["rpo", "ai_backlog", "ai_orders", "ai_semiconductor_revenue", "cloud_revenue", "iaas_revenue"]
    comparison = manual_comparison_table(manual_quarterly, chain_indicators)
    if comparison.empty:
        st.info("manual_quarterly_indicators.csv에 수동 분기 지표를 추가하면 여기서 비교할 수 있습니다.")
    else:
        st.dataframe(comparison, width="stretch")

with tab_quarterly:
    st.subheader("분기별 자동 지표 비교")
    st.write("SEC XBRL에서 자동으로 가져오는 설비투자, 매출, RPO, 재고를 기업별로 비교합니다.")
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

    st.subheader("수동 관리 지표 비교")
    manual_metric_options = sorted(manual_quarterly["indicator"].dropna().unique()) if not manual_quarterly.empty else []
    if not manual_metric_options:
        st.info("수동 분기 지표가 없습니다.")
    else:
        manual_metric = st.selectbox("수동 지표", manual_metric_options)
        rows = manual_quarterly[manual_quarterly["indicator"] == manual_metric].copy()
        chart = rows.pivot_table(index="period", columns="ticker", values="value", aggfunc="last").sort_index()
        st.bar_chart(chart, width="stretch")
        rows["표시값"] = rows.apply(lambda row: format_manual_value(row["value"], row["unit"]), axis=1)
        st.dataframe(
            rows[["ticker", "company", "period", "indicator", "표시값", "source", "note"]],
            width="stretch",
            hide_index=True,
        )

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
