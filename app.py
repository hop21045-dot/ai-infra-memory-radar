from __future__ import annotations

import pandas as pd
import streamlit as st

from data_sources import add_growth, latest_by_metric, load_latest_filings, load_metrics, utc_now_label
from metrics_config import COMPANIES, CONCEPTS, SIGNAL_WEIGHTS

st.set_page_config(page_title="AI 인프라 메모리 레이더", layout="wide")

st.markdown(
    """
    <style>
    .report-hero {
        border: 1px solid #dce3ee;
        border-radius: 6px;
        background: #f8fbff;
        padding: 22px 24px;
        margin: 8px 0 18px;
    }
    .report-kicker {
        color: #687384;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .report-title {
        color: #0b2d5b;
        font-size: 2rem;
        line-height: 1.18;
        font-weight: 800;
        margin: 0 0 10px;
    }
    .report-lead {
        color: #263244;
        font-size: 1.02rem;
        font-weight: 650;
        line-height: 1.55;
        margin: 0;
    }
    .report-callout {
        background: #eaf3ff;
        border-left: 5px solid #1d65a6;
        padding: 14px 16px;
        margin: 12px 0 18px;
        color: #113b66;
        font-weight: 700;
        line-height: 1.55;
    }
    .report-warning {
        background: #fff7e6;
        border-left: 5px solid #c78f11;
        padding: 14px 16px;
        margin: 12px 0 18px;
        color: #5d4211;
        font-weight: 650;
        line-height: 1.55;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

GROUP_LABELS = {company["group"]: company.get("group_ko", company["group"]) for company in COMPANIES}
METRIC_LABELS = {key: concept["label"] for key, concept in CONCEPTS.items()}

FOCUS_COMPANIES = {
    "Oracle",
    "Microsoft",
    "Alphabet",
    "Amazon",
    "Meta",
    "CoreWeave",
    "Nebius",
    "Dell Technologies",
    "Hewlett Packard Enterprise",
    "Broadcom",
    "NVIDIA",
    "TSMC",
    "Memory",
    "AI infrastructure",
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
    "broadcom",
    "hbm",
    "dram",
    "nand",
    "cowos",
    "copos",
    "advanced packaging",
]

LOW_SIGNAL_TERMS = [
    "목표주가",
    "투자의견",
    "헤지펀드",
    "주가",
    "관세",
    "트럼프",
    "속보",
]


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


def short_text(value: object, limit: int = 170) -> str:
    text = "" if pd.isna(value) else " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def source_score(row: pd.Series) -> int:
    text = " ".join(
        str(row.get(col, ""))
        for col in ["company", "topic", "channel_summary", "reflected_indicator", "correction"]
        if not pd.isna(row.get(col, ""))
    ).lower()
    score = 0
    if str(row.get("표시기업", row.get("company", ""))) in FOCUS_COMPANIES:
        score += 2
    for term in HIGH_SIGNAL_TERMS:
        if term.lower() in text:
            score += 1
    for term in LOW_SIGNAL_TERMS:
        if term.lower() in text:
            score -= 1
    return max(score, 0)


def source_bucket(row: pd.Series) -> str:
    company = str(row.get("표시기업", row.get("company", "")))
    text = " ".join(str(row.get(col, "")) for col in ["topic", "channel_summary", "reflected_indicator"]).lower()
    if company in {"Oracle", "Microsoft", "Alphabet", "Amazon", "Meta"}:
        return "빅테크"
    if company in {"CoreWeave", "Nebius"}:
        return "네오클라우드"
    if company in {"Dell Technologies", "Hewlett Packard Enterprise"}:
        return "서버/OEM"
    if company in {"Broadcom", "NVIDIA"}:
        return "AI 반도체/네트워킹"
    if company == "TSMC" or "cowos" in text or "copos" in text or "packaging" in text:
        return "파운드리/패키징"
    if company == "Memory" or any(term in text for term in ["hbm", "dram", "nand", "메모리"]):
        return "메모리"
    return "기타"


def normalize_source_company(row: pd.Series) -> str:
    company = str(row.get("company", ""))
    text = " ".join(str(row.get(col, "")) for col in ["topic", "channel_summary", "reflected_indicator"]).lower()
    if company == "Dell Technologies" and not any(term in text for term in ["dell", "isg", "ai server"]):
        if any(term in text for term in ["micron", "마이크론", "sk하이닉스", "sk hynix", "samsung", "hbm", "dram", "nand", "메모리"]):
            return "Memory"
        if any(term in text for term in ["broadcom", "avgo", "asic", "xpu", "mlcc"]):
            return "Broadcom"
        return "AI infrastructure"
    return company


def prepare_sources(data: pd.DataFrame, min_score: int = 3) -> pd.DataFrame:
    if data.empty:
        return data.copy()
    rows = data.copy().fillna("")
    rows["표시기업"] = rows.apply(normalize_source_company, axis=1)
    rows["관심점수"] = rows.apply(source_score, axis=1)
    rows["분류"] = rows.apply(source_bucket, axis=1)
    rows["요약"] = rows["channel_summary"].map(lambda value: short_text(value, 190))
    rows["우선순위"] = rows["관심점수"].map(lambda value: "높음" if value >= 6 else "보통" if value >= min_score else "낮음")
    rows = rows[rows["관심점수"] >= min_score]
    return rows.sort_values(["관심점수", "date"], ascending=[False, False])


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


@st.cache_data(ttl=300, show_spinner=False)
def cached_source_watchlist() -> pd.DataFrame:
    columns = [
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
    try:
        return pd.read_csv("source_watchlist.csv")
    except FileNotFoundError:
        return pd.DataFrame(columns=columns)


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


def report_metric_cards(data: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "핵심 지표": "Oracle RPO",
            "최근값": latest_manual_value(data, "ORCL", "rpo"),
            "해석": "AI capacity 계약이 매출보다 먼저 쌓이는 선행 수요",
        },
        {
            "핵심 지표": "Oracle Cloud / IaaS",
            "최근값": f"{latest_manual_value(data, 'ORCL', 'cloud_revenue')} / {latest_manual_value(data, 'ORCL', 'iaas_revenue')}",
            "해석": "RPO가 실제 OCI/IaaS 매출로 전환되는 속도",
        },
        {
            "핵심 지표": "Dell AI orders / backlog",
            "최근값": f"{latest_manual_value(data, 'DELL', 'ai_orders')} / {latest_manual_value(data, 'DELL', 'ai_backlog')}",
            "해석": "AI 서버 주문이 실제 출하와 수주잔고로 이어지는지 확인",
        },
        {
            "핵심 지표": "HPE AI backlog",
            "최근값": latest_manual_value(data, "HPE", "ai_backlog"),
            "해석": "엔터프라이즈·sovereign AI systems 수요 확산",
        },
        {
            "핵심 지표": "Broadcom AI semiconductor",
            "최근값": latest_manual_value(data, "AVGO", "ai_semiconductor_revenue"),
            "해석": "커스텀 ASIC·네트워킹 수요가 반도체 매출로 전환",
        },
    ]
    return pd.DataFrame(rows)


metrics, mode, metrics_updated = cached_metrics()
filings, filings_updated = cached_filings()
manual_quarterly = cached_manual_quarterly()
report_series = cached_report_series()
source_watchlist = cached_source_watchlist()

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
    min_source_score = st.slider("관심글 최소 점수", 0, 8, 3)
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
focused_sources = prepare_sources(source_watchlist, min_source_score)

top_cols = st.columns(4)
top_cols[0].metric("Oracle RPO", latest_manual_value(manual_quarterly, "ORCL", "rpo"))
top_cols[1].metric("Dell AI Backlog", latest_manual_value(manual_quarterly, "DELL", "ai_backlog"))
top_cols[2].metric("HPE AI Backlog", latest_manual_value(manual_quarterly, "HPE", "ai_backlog"))
top_cols[3].metric("Broadcom AI Semi", latest_manual_value(manual_quarterly, "AVGO", "ai_semiconductor_revenue"))

tabs = st.tabs(["리포트", "관심글", "회사별 차트", "지표 비교", "소스 검증", "분기·AI 비교", "최신 공시", "방법론"])

with tabs[0]:
    st.markdown(
        """
        <div class="report-hero">
            <div class="report-kicker">AI Infrastructure CAPEX/RPO Strategy</div>
            <div class="report-title">AI 인프라 CAPEX와 메모리 반도체 투자전략</div>
            <p class="report-lead">RPO·수주잔고 → CAPEX → 서버/OEM·ASIC 매출 → HBM·DRAM·NAND 출하로 이어지는 선행지표 프레임입니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="report-callout">
        핵심 한 줄: 메모리 반도체 투자자는 CAPEX 총액보다 RPO·수주잔고의 질과 매출 전환률을 먼저 봐야 합니다.
        Oracle RPO, Dell/HPE AI 수주잔고, Broadcom AI 반도체 매출은 AI 인프라 투자가 실제 장비와 메모리 수요로 넘어가는지를 확인하는 중간 검증 지표입니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("핵심 지표")
    st.dataframe(report_metric_cards(manual_quarterly), width="stretch", hide_index=True)

    st.subheader("오늘 볼 관심글")
    if focused_sources.empty:
        st.info("관심점수 조건에 맞는 글이 없습니다. 사이드바의 관심글 최소 점수를 낮춰보세요.")
    else:
        focus_view = focused_sources.head(8)[
            ["date", "분류", "표시기업", "topic", "요약", "verification_status", "reflected_indicator", "channel_url", "관심점수"]
        ].rename(
            columns={
                "date": "날짜",
                "표시기업": "기업",
                "topic": "주제",
                "verification_status": "검증 상태",
                "reflected_indicator": "반영 후보 지표",
                "channel_url": "링크",
            }
        )
        st.dataframe(focus_view, column_config={"링크": st.column_config.LinkColumn("원문")}, width="stretch", hide_index=True)

    st.subheader("지표 흐름")
    st.dataframe(build_chain_snapshot(latest, manual_quarterly), width="stretch", hide_index=True)

    st.subheader("핵심 차트")
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Oracle - RPO / Cloud / IaaS")
        oracle_chart = chart_from_series(report_series, "ORCL", ["rpo", "cloud_revenue", "iaas_revenue"])
        if oracle_chart.empty:
            st.info("Oracle 리포트 시계열이 없습니다.")
        else:
            st.bar_chart(oracle_chart, width="stretch")
    with col2:
        st.caption("Dell - AI 서버 vs 전통 서버/스토리지")
        dell_chart = chart_from_series(report_series, "DELL", ["ai_server_revenue", "traditional_server_revenue"])
        if dell_chart.empty:
            st.info("Dell 리포트 시계열이 없습니다.")
        else:
            st.line_chart(dell_chart, width="stretch")

    col3, col4 = st.columns(2)
    with col3:
        st.caption("HPE - AI 매출 vs AI 수주잔고")
        hpe_chart = chart_from_series(report_series, "HPE", ["ai_revenue", "ai_backlog"])
        if hpe_chart.empty:
            st.info("HPE 리포트 시계열이 없습니다.")
        else:
            st.bar_chart(hpe_chart, width="stretch")
    with col4:
        st.caption("검증 데이터 업데이트 원칙")
        st.markdown(
            """
            - 회사 실적발표자료, IR deck, 10-Q/10-K, 컨퍼런스콜 transcript만 기준으로 업데이트
            - RPO, backlog, AI orders처럼 XBRL 표준화가 약한 지표는 수동 CSV에 출처와 함께 입력
            - 매출, CAPEX, 재고처럼 표준화된 항목은 SEC 자동 수집을 보조로 사용
            - 값이 proxy이면 note에 반드시 표시하고, 확정값과 같은 차트에서 구분
            """
        )

    st.markdown(
        """
        <div class="report-warning">
        메모리 해석: 수요가 강하다는 말만으로는 부족합니다. RPO와 backlog가 늘고, 이후 Dell/HPE 서버 매출과 Broadcom AI 반도체 매출로 전환되며,
        마지막으로 HBM·DDR5·eSSD 가격/출하/재고가 개선되는 순서를 확인해야 합니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

with tabs[1]:
    st.subheader("관심글만 보기")
    st.caption("텔레그램/뉴스 글 중 AI 인프라, 메모리, 서버/OEM, Broadcom, Oracle RPO 등 투자 프레임과 관련성이 높은 글만 추립니다.")
    if focused_sources.empty:
        st.info("조건에 맞는 관심글이 없습니다.")
    else:
        buckets = sorted(focused_sources["분류"].dropna().unique())
        selected_buckets = st.multiselect("분류", buckets, default=buckets)
        companies = sorted(focused_sources["표시기업"].dropna().unique())
        selected_companies = st.multiselect("기업", companies, default=companies)
        rows = focused_sources[
            focused_sources["분류"].isin(selected_buckets) & focused_sources["표시기업"].isin(selected_companies)
        ].copy()
        st.metric("표시 글 수", len(rows))
        table = rows[
            [
                "date",
                "우선순위",
                "관심점수",
                "분류",
                "표시기업",
                "topic",
                "요약",
                "verification_status",
                "correction",
                "reflected_indicator",
                "channel_url",
            ]
        ].rename(
            columns={
                "date": "날짜",
                "표시기업": "기업",
                "topic": "주제",
                "verification_status": "검증 상태",
                "correction": "검증/수정 메모",
                "reflected_indicator": "반영 후보 지표",
                "channel_url": "링크",
            }
        )
        st.dataframe(table, column_config={"링크": st.column_config.LinkColumn("원문")}, width="stretch", hide_index=True)

with tabs[2]:
    st.subheader("회사별 차트")
    st.write("검증된 실적발표/컨퍼런스콜 숫자만 분기별 차트로 관리합니다.")
    report_options = {
        "Oracle: RPO / Cloud / IaaS": ("ORCL", ["rpo", "cloud_revenue", "iaas_revenue"]),
        "Dell: AI 서버 vs 전통 서버": ("DELL", ["ai_server_revenue", "traditional_server_revenue"]),
        "HPE: AI 매출 vs AI 수주잔고": ("HPE", ["ai_revenue", "ai_backlog"]),
    }
    selected_report = st.radio("차트", list(report_options.keys()), horizontal=True)
    ticker, indicators = report_options[selected_report]
    chart = chart_from_series(report_series, ticker, indicators)
    if chart.empty:
        st.info("리포트 시계열이 없습니다.")
    else:
        st.bar_chart(chart, width="stretch")

with tabs[3]:
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

with tabs[4]:
    st.subheader("소스 검증")
    st.write(
        "관심점수 기준으로 한 번 거른 뒤, 공식 실적자료/IR 자료/컨퍼런스콜로 확인할 글만 검증 큐에 남깁니다."
    )
    display_sources = focused_sources if not focused_sources.empty else prepare_sources(source_watchlist, 0)
    if display_sources.empty:
        st.info("source_watchlist.csv에 등록된 소스가 없습니다.")
    else:
        status_options = sorted(display_sources["verification_status"].dropna().unique())
        selected_status = st.multiselect("검증 상태", status_options, default=status_options)
        source_options = sorted(display_sources["category"].dropna().unique())
        selected_source_types = st.multiselect("소스 유형", source_options, default=source_options)
        source_rows = display_sources[
            display_sources["verification_status"].isin(selected_status)
            & display_sources["category"].isin(selected_source_types)
        ].copy()
        source_rows = source_rows.sort_values(["관심점수", "date"], ascending=[False, False])
        view = source_rows.rename(
            columns={
                "date": "날짜",
                "category": "소스",
                "표시기업": "기업",
                "ticker": "티커",
                "topic": "주제",
                "channel_summary": "원문 요약",
                "channel_url": "링크",
                "official_material": "공식 확인 자료",
                "official_url": "공식자료 링크",
                "verification_status": "검증 상태",
                "correction": "검증/수정 메모",
                "reflected_indicator": "반영 후보 지표",
                "action": "다음 작업",
            }
        )
        st.dataframe(
            view[
                [
                    "날짜",
                    "관심점수",
                    "분류",
                    "소스",
                    "기업",
                    "주제",
                    "요약",
                    "검증 상태",
                    "검증/수정 메모",
                    "반영 후보 지표",
                    "링크",
                ]
            ],
            column_config={"링크": st.column_config.LinkColumn("원문")},
            width="stretch",
            hide_index=True,
        )

with tabs[5]:
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

with tabs[6]:
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

with tabs[7]:
    st.subheader("데이터 원칙")
    st.write(
        "자동 SEC XBRL은 총매출, CAPEX, 일부 재고처럼 표준화된 재무항목에 적합합니다. 반면 Oracle RPO, Dell/HPE AI 수주잔고, "
        "Broadcom AI 반도체 매출처럼 회사가 컨퍼런스콜이나 실적발표에서 설명하는 항목은 수동 분기 지표로 관리합니다."
    )
    st.subheader("관심글 필터")
    st.write(
        "텔레그램 글은 회사명, RPO/backlog/CAPEX/AI 서버/HBM/DRAM/NAND/ASIC/패키징 키워드로 관심점수를 계산합니다. "
        "목표주가, 단순 수급, 정치성 코멘트는 점수를 낮춰 별도 검증 우선순위에서 제외합니다."
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
