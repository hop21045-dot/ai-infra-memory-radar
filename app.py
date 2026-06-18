from __future__ import annotations

import pandas as pd
import streamlit as st

from data_sources import add_growth, latest_by_metric, load_latest_filings, load_metrics, utc_now_label
from metrics_config import COMPANIES, CONCEPTS, SIGNAL_WEIGHTS

st.set_page_config(page_title="AI 인프라 메모리 레이더", layout="wide")

GROUP_LABELS = {company["group"]: company.get("group_ko", company["group"]) for company in COMPANIES}
METRIC_LABELS = {key: concept["label"] for key, concept in CONCEPTS.items()}


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


def format_usd_bn(value: float) -> str:
    if pd.isna(value):
        return "-"
    return f"${value:,.1f}B"


def pct(value: float) -> str:
    if pd.isna(value):
        return "-"
    return f"{value * 100:,.1f}%"


def signal_label(score: float) -> str:
    score_pct = score * 100
    if score_pct >= 20:
        return "강한 개선"
    if score_pct >= 5:
        return "개선"
    if score_pct > -5:
        return "중립"
    if score_pct > -20:
        return "둔화"
    return "강한 둔화"


def signal_table(latest: pd.DataFrame) -> pd.DataFrame:
    rows = []
    company_map = {company["ticker"]: company for company in COMPANIES}
    for ticker, group in latest.groupby("ticker"):
        score = 0.0
        parts = []
        for _, row in group.iterrows():
            yoy = row.get("yoy")
            metric = row["metric"]
            if pd.isna(yoy):
                continue
            score += yoy * SIGNAL_WEIGHTS.get(metric, 0)
            parts.append(f"{METRIC_LABELS.get(metric, metric)} {pct(yoy)} YoY")
        company = company_map.get(ticker, {})
        rows.append(
            {
                "티커": ticker,
                "기업": company.get("name", ticker),
                "분류": company.get("group_ko", company.get("group", "")),
                "메모리 투자 관점": company.get("memory_angle", ""),
                "가중 YoY 점수": score * 100,
                "판정": signal_label(score),
                "최근 변화": ", ".join(parts) if parts else "태그된 과거 데이터가 더 필요함",
            }
        )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values("가중 YoY 점수", ascending=False)


def metric_quarterly_chart(data: pd.DataFrame, metric: str) -> pd.DataFrame:
    rows = data[data["metric"] == metric].copy()
    if rows.empty:
        return pd.DataFrame()
    return rows.pivot_table(index="period", columns="ticker", values="value", aggfunc="last").sort_index()


def manual_indicator_chart(data: pd.DataFrame, indicator: str, selected_groups: list[str] | None = None) -> pd.DataFrame:
    rows = data[data["indicator"] == indicator].copy()
    if selected_groups:
        rows = rows[rows["group"].isin(selected_groups)]
    if rows.empty:
        return pd.DataFrame()
    return rows.pivot_table(index="period", columns="ticker", values="value", aggfunc="last").sort_index()


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


def manual_comparison_table(data: pd.DataFrame, indicators: list[str]) -> pd.DataFrame:
    rows = data[data["indicator"].isin(indicators)].copy()
    if rows.empty:
        return pd.DataFrame()
    rows["표시값"] = rows.apply(lambda row: format_manual_value(row["value"], row["unit"]), axis=1)
    return rows.pivot_table(index=["ticker", "company"], columns=["period", "indicator"], values="표시값", aggfunc="last")


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
            "단계": "3. 서버/OEM 전환",
            "핵심 지표": "Dell/HPE AI 서버 매출, 주문, 수주잔고",
            "현재 확인값": f"Dell AI backlog {latest_manual_value(manual_quarterly, 'DELL', 'ai_backlog')}, HPE AI backlog {latest_manual_value(manual_quarterly, 'HPE', 'ai_backlog')}",
            "메모리 해석": "HBM 탑재 GPU 서버와 DDR5/eSSD 수요 확인",
        },
        {
            "단계": "4. ASIC/네트워킹",
            "핵심 지표": "Broadcom AI 반도체 매출",
            "현재 확인값": f"Broadcom AI semi {latest_manual_value(manual_quarterly, 'AVGO', 'ai_semiconductor_revenue')}",
            "메모리 해석": "커스텀 ASIC, 스위치, 광통신 수요 확산",
        },
        {
            "단계": "5. 메모리 실적",
            "핵심 지표": "HBM/DRAM/NAND 매출, 가격, 재고",
            "현재 확인값": f"Micron 재고 {money(latest[(latest['ticker'] == 'MU') & (latest['metric'] == 'inventory')]['value'].sum())}",
            "메모리 해석": "수요가 실제 가격, 출하, 재고 개선으로 연결되는지 검증",
        },
    ]
    return pd.DataFrame(rows)


def ai_non_ai_rows(data: pd.DataFrame) -> pd.DataFrame:
    indicators = [
        "total_revenue",
        "servers_networking_revenue",
        "cloud_ai_revenue_proxy",
        "semiconductor_revenue",
        "ai_semiconductor_revenue",
        "non_ai_semiconductor_revenue",
        "infrastructure_software_revenue",
        "ai_orders",
        "ai_backlog",
    ]
    rows = data[data["indicator"].isin(indicators)].copy()
    if rows.empty:
        return rows
    label_map = {
        "total_revenue": "총매출",
        "servers_networking_revenue": "서버/네트워킹 매출",
        "cloud_ai_revenue_proxy": "Cloud/AI 매출 proxy",
        "semiconductor_revenue": "반도체 매출",
        "ai_semiconductor_revenue": "AI 반도체 매출",
        "non_ai_semiconductor_revenue": "비AI 반도체 매출",
        "infrastructure_software_revenue": "인프라 소프트웨어 매출",
        "ai_orders": "AI 주문",
        "ai_backlog": "AI 수주잔고",
    }
    rows["지표"] = rows["indicator"].map(label_map).fillna(rows["indicator"])
    rows["표시값"] = rows.apply(lambda row: format_manual_value(row["value"], row["unit"]), axis=1)
    return rows


@st.cache_data(ttl=900, show_spinner=False)
def cached_metrics() -> tuple[pd.DataFrame, str, str]:
    data, mode = load_metrics()
    return add_growth(data), mode, utc_now_label()


@st.cache_data(ttl=300, show_spinner=False)
def cached_filings() -> tuple[pd.DataFrame, str]:
    return load_latest_filings(), utc_now_label()


@st.cache_data(ttl=300, show_spinner=False)
def cached_manual_quarterly() -> pd.DataFrame:
    try:
        return pd.read_csv("manual_quarterly_indicators.csv")
    except FileNotFoundError:
        return pd.DataFrame(columns=["ticker", "company", "group", "period", "indicator", "value", "unit", "source", "url", "note"])


@st.cache_data(ttl=300, show_spinner=False)
def cached_report_series() -> pd.DataFrame:
    try:
        return pd.read_csv("company_report_series.csv")
    except FileNotFoundError:
        return pd.DataFrame(columns=["company", "ticker", "period", "indicator", "value", "unit", "source", "note"])


def chart_from_series(series: pd.DataFrame, ticker: str, indicators: list[str]) -> pd.DataFrame:
    rows = series[(series["ticker"] == ticker) & (series["indicator"].isin(indicators))].copy()
    if rows.empty:
        return pd.DataFrame()
    labels = {
        "ai_server_revenue": "AI 서버 매출",
        "traditional_server_revenue": "전통 서버/스토리지",
        "ai_revenue": "AI 매출",
        "ai_backlog": "AI 수주잔고",
        "rpo": "RPO",
        "iaas_revenue": "IaaS 매출",
        "cloud_revenue": "Cloud 매출",
    }
    rows["지표"] = rows["indicator"].map(labels).fillna(rows["indicator"])
    return rows.pivot_table(index="period", columns="지표", values="value", aggfunc="last")


metrics, mode, metrics_updated = cached_metrics()
filings, filings_updated = cached_filings()
manual_quarterly = cached_manual_quarterly()
report_series = cached_report_series()

st.title("AI 인프라 메모리 레이더")
st.caption("CAPEX만 보지 않고 RPO/수주잔고, 서버 매출, AI 반도체 매출, 메모리 병목 코멘트를 함께 추적합니다.")

with st.sidebar:
    st.header("필터")
    groups = sorted({company["group"] for company in COMPANIES})
    selected_groups = st.multiselect("기업 분류", groups, default=groups, format_func=lambda value: GROUP_LABELS.get(value, value))
    selected_metrics = st.multiselect(
        "자동 SEC 지표",
        list(CONCEPTS.keys()),
        default=["capex", "revenue", "rpo"],
        format_func=lambda key: CONCEPTS[key]["label"],
    )
    periods = sorted(metrics["period"].dropna().unique()) if not metrics.empty else []
    selected_periods = st.slider("최근 분기 수", 4, 16, 8)
    st.divider()
    st.write(f"SEC 지표: {'실시간' if mode == 'live' else '샘플'}")
    st.write(f"지표 업데이트: {metrics_updated}")
    st.write(f"공시 업데이트: {filings_updated}")
    if st.button("지금 새로고침"):
        st.cache_data.clear()
        st.rerun()

filtered = metrics[metrics["group"].isin(selected_groups) & metrics["metric"].isin(selected_metrics)].copy()
if periods:
    filtered = filtered[filtered["period"].isin(periods[-selected_periods:])]

latest = latest_by_metric(filtered)
signals = signal_table(latest)

top_cols = st.columns(4)
top_cols[0].metric("Oracle RPO", latest_manual_value(manual_quarterly, "ORCL", "rpo"))
top_cols[1].metric("Dell AI Backlog", latest_manual_value(manual_quarterly, "DELL", "ai_backlog"))
top_cols[2].metric("HPE AI Backlog", latest_manual_value(manual_quarterly, "HPE", "ai_backlog"))
top_cols[3].metric("Broadcom AI Semi", latest_manual_value(manual_quarterly, "AVGO", "ai_semiconductor_revenue"))

tabs = st.tabs(["요약", "회사별 리포트", "AI 인프라 체인", "분기별 비교", "AI/비AI 분리", "최신 공시", "방법론"])

with tabs[0]:
    st.subheader("메모리 수요 시그널")
    st.caption("가중 YoY 점수는 빠른 스크리닝용 온도계입니다. 투자 결론이 아니라 변화 방향을 보기 위한 보조 지표입니다.")
    if signals.empty:
        st.info("아직 표시할 시그널 데이터가 없습니다.")
    else:
        display = signals.copy()
        display["가중 YoY 점수"] = display["가중 YoY 점수"].map(lambda value: f"{value:,.1f}")
        st.dataframe(display, width="stretch", hide_index=True)

    st.subheader("지표별 분기 추세")
    if not selected_metrics:
        st.info("사이드바에서 하나 이상의 지표를 선택하세요.")
    else:
        metric_tabs = st.tabs([METRIC_LABELS.get(metric, metric) for metric in selected_metrics])
        for metric_tab, metric in zip(metric_tabs, selected_metrics):
            with metric_tab:
                chart_data = metric_quarterly_chart(filtered, metric)
                if chart_data.empty:
                    manual_chart = manual_indicator_chart(manual_quarterly, metric, selected_groups)
                    if manual_chart.empty:
                        st.info(f"{METRIC_LABELS.get(metric, metric)} 데이터가 없습니다.")
                    else:
                        st.info(
                            f"{METRIC_LABELS.get(metric, metric)}는 자동 SEC XBRL보다 실적발표/IR 기준 수동 지표로 관리합니다."
                        )
                        st.line_chart(manual_chart, width="stretch")
                        manual_rows = manual_quarterly[
                            (manual_quarterly["indicator"] == metric) & (manual_quarterly["group"].isin(selected_groups))
                        ].copy()
                        manual_rows["표시값"] = manual_rows.apply(
                            lambda row: format_manual_value(row["value"], row["unit"]), axis=1
                        )
                        st.dataframe(
                            manual_rows[["ticker", "company", "period", "indicator", "표시값", "source", "note"]],
                            width="stretch",
                            hide_index=True,
                        )
                else:
                    st.line_chart(chart_data, width="stretch")
                    table = chart_data.copy()
                    for col in table.columns:
                        table[col] = table[col].map(money)
                    st.dataframe(table, width="stretch")

with tabs[1]:
    st.subheader("Dell - 서버 매출 구조")
    st.write("AI 서버 매출이 전통 서버/스토리지와 다른 기울기로 올라오는지 봅니다. 이 탭의 일부 과거값은 블로그식 정리를 위한 수동/근사 시계열입니다.")
    dell_chart = chart_from_series(report_series, "DELL", ["ai_server_revenue", "traditional_server_revenue"])
    if dell_chart.empty:
        st.info("Dell 리포트 시계열이 없습니다.")
    else:
        st.line_chart(dell_chart, width="stretch")
    st.markdown(
        """
        **투자 포인트:** Dell 서버 매출은 하이퍼스케일러향 비중이 낮고 자체 서버 설계 노출도가 높아 AI 서버 수요를 비교적 직접적으로 보여줍니다.

        **메모리 연결:** AI 서버 한 대당 HBM, DDR5/RDIMM, eSSD 탑재량이 커지므로 AI 서버 매출과 수주잔고가 메모리 수요의 중간 검증 지표가 됩니다.
        """
    )

    st.subheader("HPE - AI 매출 vs 수주잔고")
    hpe_chart = chart_from_series(report_series, "HPE", ["ai_revenue", "ai_backlog"])
    if hpe_chart.empty:
        st.info("HPE 리포트 시계열이 없습니다.")
    else:
        st.bar_chart(hpe_chart, width="stretch")
    st.markdown(
        """
        **투자 포인트:** HPE는 Dell처럼 순수 AI 서버 출하만 보기보다 enterprise/sovereign AI systems와 networking attach를 같이 봐야 합니다.

        **메모리 연결:** AI systems 수주잔고가 매출보다 빠르게 쌓이면, 이후 서버 DRAM/eSSD와 네트워킹 부품 수요로 전환될 가능성이 커집니다.
        """
    )

    st.subheader("Oracle - RPO가 먼저 움직인다")
    oracle_chart = chart_from_series(report_series, "ORCL", ["rpo", "cloud_revenue", "iaas_revenue"])
    if oracle_chart.empty:
        st.info("Oracle 리포트 시계열이 없습니다.")
    else:
        st.bar_chart(oracle_chart, width="stretch")
    st.markdown(
        """
        **왜 RPO가 중요한가:** Oracle은 AI 인프라 계약이 먼저 RPO로 쌓이고, 데이터센터와 GPU capacity가 준비되면서 OCI/IaaS 매출로 전환됩니다.

        **정정:** Oracle RPO가 없는 것이 아닙니다. 자동 SEC XBRL 태그로 안정적으로 잡히지 않아서, 실적발표/컨퍼런스콜 기반 수동 지표로 따로 관리하는 것이 맞습니다.
        """
    )

    st.subheader("부품 병목 체크")
    st.warning("수요는 여전히 공급을 초과하고 있으며, 주요 제약 요인은 메모리입니다. 특히 DRAM, NAND, CPU/마이크로프로세서, 스토리지 부품 코멘트를 추적해야 합니다.")

with tabs[2]:
    st.subheader("AI 인프라 투자 체인")
    st.write("RPO/수주잔고 -> CAPEX 집행 -> 서버/OEM 전환 -> ASIC/네트워킹 -> 메모리 실적으로 이어지는지 확인합니다.")
    st.dataframe(build_chain_snapshot(latest, manual_quarterly), width="stretch", hide_index=True)

    st.subheader("핵심 선행지표 비교")
    comparison = manual_comparison_table(
        manual_quarterly,
        ["rpo", "ai_backlog", "ai_orders", "ai_semiconductor_revenue", "cloud_revenue", "iaas_revenue", "capex"],
    )
    if comparison.empty:
        st.info("수동 분기 지표가 없습니다.")
    else:
        st.dataframe(comparison, width="stretch")

with tabs[3]:
    st.subheader("SEC 자동 지표 비교")
    chart_metric = st.selectbox(
        "차트 지표",
        selected_metrics if selected_metrics else list(CONCEPTS.keys()),
        format_func=lambda key: CONCEPTS[key]["label"],
    )
    quarterly = metric_quarterly_chart(filtered, chart_metric)
    if quarterly.empty:
        manual_chart = manual_indicator_chart(manual_quarterly, chart_metric, selected_groups)
        if manual_chart.empty:
            st.info("선택한 조건에 해당하는 분기 데이터가 없습니다.")
        else:
            st.info("이 지표는 자동 SEC XBRL 대신 실적발표/IR 기반 수동 지표로 표시합니다.")
            st.bar_chart(manual_chart, width="stretch")
    else:
        st.bar_chart(quarterly, width="stretch")
        table = quarterly.copy()
        for col in table.columns:
            table[col] = table[col].map(money)
        st.dataframe(table, width="stretch")

    st.subheader("수동 관리 지표 비교")
    manual_metric_options = sorted(manual_quarterly["indicator"].dropna().unique()) if not manual_quarterly.empty else []
    if manual_metric_options:
        manual_metric = st.selectbox(
            "수동 지표",
            manual_metric_options,
            index=manual_metric_options.index("rpo") if "rpo" in manual_metric_options else 0,
        )
        rows = manual_quarterly[
            (manual_quarterly["indicator"] == manual_metric) & (manual_quarterly["group"].isin(selected_groups))
        ].copy()
        chart = rows.pivot_table(index="period", columns="ticker", values="value", aggfunc="last").sort_index()
        st.bar_chart(chart, width="stretch")
        rows["표시값"] = rows.apply(lambda row: format_manual_value(row["value"], row["unit"]), axis=1)
        st.dataframe(rows[["ticker", "company", "period", "indicator", "표시값", "source", "note"]], width="stretch", hide_index=True)

with tabs[4]:
    st.subheader("Dell / HPE / Broadcom AI vs 비AI")
    st.write("Dell과 HPE는 AI 주문·수주잔고 중심으로, Broadcom은 AI 반도체 매출과 비AI 반도체 매출로 분리해서 봅니다.")
    split_rows = ai_non_ai_rows(manual_quarterly)
    if split_rows.empty:
        st.info("AI/비AI 분리 지표가 없습니다.")
    else:
        split_view = split_rows[["ticker", "company", "period", "지표", "표시값", "source", "url", "note"]].rename(
            columns={"ticker": "티커", "company": "기업", "period": "분기", "source": "출처", "url": "링크", "note": "비고"}
        )
        st.dataframe(split_view, column_config={"링크": st.column_config.LinkColumn("출처 링크")}, width="stretch", hide_index=True)
        chart_source = split_rows[split_rows["indicator"].isin(["ai_semiconductor_revenue", "non_ai_semiconductor_revenue", "infrastructure_software_revenue"])]
        if not chart_source.empty:
            st.subheader("Broadcom 매출 분해")
            chart = chart_source.pivot_table(index="period", columns="지표", values="value", aggfunc="last").sort_index()
            st.bar_chart(chart, width="stretch")

with tabs[5]:
    st.subheader("최신 SEC 공시")
    if filings.empty:
        st.info("표시할 최근 공시가 없습니다.")
    else:
        filing_display = filings.copy()
        if "group" in filing_display:
            filing_display = filing_display[filing_display["group"].isin(set(selected_groups))]
        filing_display = filing_display[["ticker", "company", "group", "form", "filed", "report_date", "title", "url"]].rename(
            columns={
                "ticker": "티커",
                "company": "기업",
                "group": "분류",
                "form": "양식",
                "filed": "공시일",
                "report_date": "보고기간",
                "title": "제목",
                "url": "링크",
            }
        )
        st.dataframe(filing_display, column_config={"링크": st.column_config.LinkColumn("SEC 문서")}, width="stretch", hide_index=True)

with tabs[6]:
    st.subheader("데이터 원칙")
    st.write(
        "자동 SEC XBRL은 총매출, CAPEX, 일부 재고처럼 표준화된 재무항목에 적합합니다. 반면 Oracle RPO, Dell/HPE AI 수주잔고, "
        "Broadcom AI 반도체 매출처럼 회사가 컨퍼런스콜이나 실적발표에서 설명하는 항목은 수동 분기 지표로 관리합니다."
    )
    st.subheader("Oracle RPO")
    st.write(
        "Oracle RPO는 분명히 존재하고 핵심 지표입니다. 다만 앱의 자동 SEC 지표 목록에서 안정적으로 잡히지 않을 수 있어 "
        "수동 IR 지표로 별도 관리하며, 상단 KPI와 회사별 리포트 탭에 전면 표시했습니다."
    )
    st.subheader("가중 YoY 점수")
    st.write(
        "가중 YoY 점수는 CAPEX YoY 45%, 매출 YoY 25%, RPO YoY 20%, 재고 YoY -10%를 더한 스크리닝용 온도계입니다."
    )
