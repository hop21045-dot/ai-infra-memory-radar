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

## 리포트 업데이트 원칙

이 앱의 메인 화면은 `AI 인프라 CAPEX와 메모리 반도체 투자전략` HTML 리포트처럼 읽히도록 구성했습니다.

- 기준 데이터: 회사 실적발표자료, IR deck, 10-Q/10-K, 컨퍼런스콜 transcript
- 수동 관리 지표: Oracle RPO, Dell/HPE AI orders/backlog, Broadcom AI semiconductor revenue, CoreWeave/Nebius CAPEX
- 자동 보조 지표: SEC XBRL로 안정적으로 잡히는 매출, CAPEX, 재고
- proxy 또는 추정값은 `note`에 표시하고 확정 수치와 구분합니다.

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
