# AI 인프라 메모리 레이더

메모리 반도체 투자자를 위한 Streamlit 리포트형 대시보드입니다. 사용자가 검증한 실적발표/컨퍼런스콜 기반 숫자를 누적하고, 공개 SEC 지표는 보조 데이터로 함께 추적합니다.

## 추적 대상

- 하이퍼스케일러 설비투자: MSFT, GOOGL, META, AMZN, ORCL
- AI 서버 OEM: DELL, HPE
- AI 반도체/네트워킹: AVGO, NVDA
- 메모리 투자 시그널: MU 및 설비투자/매출/재고 지표
- SEC EDGAR 최신 공시
- `manual_indicators.csv`에 관리하는 AI 수주잔고/주문 코멘트
- `manual_quarterly_indicators.csv`에 관리하는 RPO, 수주잔고, AI 주문, NeoCloud CAPEX 같은 수동 분기 지표
- `company_report_series.csv`에 관리하는 Dell/HPE/Oracle 회사별 리포트형 시계열
- `source_watchlist.csv`에 관리하는 텔레그램/뉴스/기업 코멘트 검증 큐
- `telegram_channels.csv`에 관리하는 텔레그램 수집 대상 채널 목록

## 리포트 업데이트 원칙

이 앱의 메인 화면은 `AI 인프라 CAPEX와 메모리 반도체 투자전략` HTML 리포트처럼 읽히도록 구성했습니다.

- 기준 데이터: 회사 실적발표자료, IR deck, 10-Q/10-K, 컨퍼런스콜 transcript
- 수동 관리 지표: Oracle RPO, Dell/HPE AI orders/backlog, Broadcom AI semiconductor revenue, CoreWeave/Nebius CAPEX
- 자동 보조 지표: SEC XBRL로 안정적으로 잡히는 매출, CAPEX, 재고
- proxy 또는 추정값은 `note`에 표시하고 확정 수치와 구분합니다.

## 텔레그램/뉴스 소스 관리

텔레그램 채널과 뉴스 기사는 공식 데이터가 아니라 아이디어 발견용 소스로 사용합니다.

1. 텔레그램/뉴스/기업 코멘트를 `source_watchlist.csv`에 등록합니다.
2. 공식 실적발표자료, IR deck, 10-Q/10-K, 컨퍼런스콜 transcript로 숫자를 검증합니다.
3. 잘못된 내용이나 표현 차이는 `correction`에 기록합니다.
4. 검증이 끝난 숫자만 `manual_quarterly_indicators.csv` 또는 `company_report_series.csv`에 반영합니다.

Telegram API를 쓰면 공개 프리뷰보다 안정적으로 채널 히스토리를 조회할 수 있지만, API ID/API Hash와 1회 로그인 인증이 필요합니다. 세션 파일은 개인 계정 권한을 포함하므로 GitHub에 올리면 안 됩니다. 자동화는 로컬 수집 스크립트에서 `source_watchlist.csv`까지 생성하고, 앱은 CSV만 읽는 구조가 안전합니다.

현재 수집 대상 후보:

- `bornlupin` / 루팡 Invest
- `cahier_de_market` / 카이에 de market

로컬 수집 방식:

```powershell
pip install telethon pandas
```

`.env` 파일을 로컬에만 생성합니다.

```text
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=your_api_hash
```

그 다음 실행합니다.

```powershell
python collect_telegram.py --limit 100
```

생성되는 `.session` 파일은 Telegram 로그인 세션이므로 GitHub에 올리면 안 됩니다. `.gitignore`에 제외 규칙을 포함했습니다.

## AI/반도체 뉴스 코멘트

AI 관련 뉴스, 반도체 뉴스, 기업 코멘트도 `source_watchlist.csv`에 같은 방식으로 관리합니다.

- 뉴스/텔레그램 글: 수요 신호, 리스크, 아이디어 발견
- 공식자료: 숫자 확정, 오류 수정, 차트 반영 기준
- Streamlit 표시: 짧은 요약, 링크, 공식자료 검증 상태, 수정 메모, 반영 지표

뉴스 전문을 복사하지 않고 요약과 링크만 저장합니다. 수치가 포함된 뉴스는 공식자료 또는 원문 기사로 재확인한 뒤 차트 CSV에 반영합니다.

## 데이터 업데이트

앱은 SEC EDGAR JSON API를 사용합니다.

- `data.sec.gov/submissions/CIK##########.json`
- `data.sec.gov/api/xbrl/companyfacts/CIK##########.json`

Streamlit은 지표 데이터를 15분, 공시 데이터를 5분 캐시합니다. 사이드바의 **지금 새로고침**을 누르면 캐시를 비웁니다.

SEC 접근이 네트워크나 요청 제한 때문에 실패하면 샘플 데이터를 표시합니다.

수주잔고/주문 코멘트는 표준 XBRL로 제공되지 않는 경우가 많습니다. 기업이 공개한 AI 서버 주문, 수주잔고, RPO 코멘트, 컨퍼런스콜 메모는 `manual_indicators.csv`에 출처 링크와 함께 관리하세요.

분기별 수동 지표는 `manual_quarterly_indicators.csv`에 추가합니다. 이 파일은 Oracle RPO, Dell/HPE AI backlog, Broadcom AI semiconductor revenue, CoreWeave/Nebius CAPEX처럼 SEC XBRL에 표준화되어 있지 않은 지표를 비교하기 위한 보조 데이터입니다.

회사별 차트 시계열은 `company_report_series.csv`에 추가합니다. Dell AI 서버 매출, HPE AI revenue/backlog, Oracle RPO/Cloud/IaaS처럼 리포트에 들어갈 차트용 수치를 분기별로 관리합니다.

## 로컬 실행

Windows 권장 방식:

```powershell
.\run_local.cmd
```

그 다음 브라우저에서 엽니다.

```text
http://127.0.0.1:8501
```

대시보드를 보는 동안 터미널 창을 열어두세요. 창을 닫으면 로컬 서버도 꺼집니다.

대안:

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## 배포

파일을 GitHub에 올린 뒤 Streamlit Community Cloud에서 배포합니다. 현재 SEC 데이터 소스에는 API 키가 필요 없습니다.

## 한계

이 앱은 공개 데이터 대시보드이지 기업 내부 주문장부가 아닙니다. 일부 AI 수주잔고 항목은 XBRL 태그가 없어서 기업 코멘트, IR 자료, 실적발표 대본, 수동 구조화 노트로 보완해야 합니다.
