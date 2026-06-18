COMPANIES = [
    {
        "ticker": "MSFT",
        "name": "Microsoft",
        "cik": "0000789019",
        "group": "Hyperscaler",
        "group_ko": "하이퍼스케일러",
        "memory_angle": "Azure AI 설비투자, 데이터센터 증설, HBM/서버 DRAM 수요",
    },
    {
        "ticker": "GOOGL",
        "name": "Alphabet",
        "cik": "0001652044",
        "group": "Hyperscaler",
        "group_ko": "하이퍼스케일러",
        "memory_angle": "Google Cloud, TPU/GPU 인프라 설비투자",
    },
    {
        "ticker": "META",
        "name": "Meta Platforms",
        "cik": "0001326801",
        "group": "Hyperscaler",
        "group_ko": "하이퍼스케일러",
        "memory_angle": "AI 학습/추론 클러스터와 데이터센터 설비투자",
    },
    {
        "ticker": "AMZN",
        "name": "Amazon",
        "cik": "0001018724",
        "group": "Hyperscaler",
        "group_ko": "하이퍼스케일러",
        "memory_angle": "AWS 인프라와 AI 서버 증설",
    },
    {
        "ticker": "ORCL",
        "name": "Oracle",
        "cik": "0001341439",
        "group": "Hyperscaler",
        "group_ko": "하이퍼스케일러",
        "memory_angle": "OCI GPU 클러스터, 잔여수행의무(RPO)",
    },
    {
        "ticker": "DELL",
        "name": "Dell Technologies",
        "cik": "0001571996",
        "group": "AI server OEM",
        "group_ko": "AI 서버 OEM",
        "memory_angle": "AI 서버 매출/주문/수주잔고, 기업 서버 메모리 탑재량",
    },
    {
        "ticker": "HPE",
        "name": "Hewlett Packard Enterprise",
        "cik": "0001645590",
        "group": "AI server OEM",
        "group_ko": "AI 서버 OEM",
        "memory_angle": "서버, HPC, AI 시스템 주문/수주잔고",
    },
    {
        "ticker": "AVGO",
        "name": "Broadcom",
        "cik": "0001730168",
        "group": "AI silicon/networking",
        "group_ko": "AI 반도체/네트워킹",
        "memory_angle": "커스텀 AI 가속기, 스위칭, AI 연결 인프라 수요",
    },
    {
        "ticker": "NVDA",
        "name": "NVIDIA",
        "cik": "0001045810",
        "group": "AI accelerator",
        "group_ko": "AI 가속기",
        "memory_angle": "데이터센터 매출을 HBM 수요 선행지표로 추적",
    },
    {
        "ticker": "MU",
        "name": "Micron",
        "cik": "0000723125",
        "group": "Memory",
        "group_ko": "메모리",
        "memory_angle": "HBM, DRAM/NAND 가격, 재고와 설비투자 시그널",
    },
]

CONCEPTS = {
    "capex": {
        "label": "설비투자 / 유형자산 취득",
        "taxonomy": "us-gaap",
        "tags": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquireProductiveAssets",
        ],
        "statement": "현금흐름표",
        "unit": "USD",
    },
    "revenue": {
        "label": "매출",
        "taxonomy": "us-gaap",
        "tags": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ],
        "statement": "손익계산서",
        "unit": "USD",
    },
    "rpo": {
        "label": "잔여수행의무(RPO)",
        "taxonomy": "us-gaap",
        "tags": [
            "TransactionPriceAllocatedToRemainingPerformanceObligations",
            "RemainingPerformanceObligation",
        ],
        "statement": "주석",
        "unit": "USD",
    },
    "inventory": {
        "label": "재고",
        "taxonomy": "us-gaap",
        "tags": [
            "InventoryNet",
            "InventoryFinishedGoodsNetOfReserves",
        ],
        "statement": "재무상태표",
        "unit": "USD",
    },
}

SIGNAL_WEIGHTS = {
    "capex": 0.45,
    "revenue": 0.25,
    "rpo": 0.20,
    "inventory": -0.10,
}
