COMPANIES = [
    {
        "ticker": "MSFT",
        "name": "Microsoft",
        "cik": "0000789019",
        "group": "Hyperscaler",
        "memory_angle": "Azure AI capex, data center buildout, HBM/server DRAM pull",
    },
    {
        "ticker": "GOOGL",
        "name": "Alphabet",
        "cik": "0001652044",
        "group": "Hyperscaler",
        "memory_angle": "Google Cloud and TPU/GPU infrastructure capex",
    },
    {
        "ticker": "META",
        "name": "Meta Platforms",
        "cik": "0001326801",
        "group": "Hyperscaler",
        "memory_angle": "AI training/inference clusters and data center capex",
    },
    {
        "ticker": "AMZN",
        "name": "Amazon",
        "cik": "0001018724",
        "group": "Hyperscaler",
        "memory_angle": "AWS infrastructure and AI server fleet expansion",
    },
    {
        "ticker": "ORCL",
        "name": "Oracle",
        "cik": "0001341439",
        "group": "Hyperscaler",
        "memory_angle": "OCI GPU clusters, remaining performance obligations",
    },
    {
        "ticker": "DELL",
        "name": "Dell Technologies",
        "cik": "0001571996",
        "group": "AI server OEM",
        "memory_angle": "AI server revenue/orders/backlog, enterprise server memory content",
    },
    {
        "ticker": "HPE",
        "name": "Hewlett Packard Enterprise",
        "cik": "0001645590",
        "group": "AI server OEM",
        "memory_angle": "Server, HPC and AI systems orders/backlog",
    },
    {
        "ticker": "AVGO",
        "name": "Broadcom",
        "cik": "0001730168",
        "group": "AI silicon/networking",
        "memory_angle": "Custom AI accelerators, switching, AI connectivity demand",
    },
    {
        "ticker": "NVDA",
        "name": "NVIDIA",
        "cik": "0001045810",
        "group": "AI accelerator",
        "memory_angle": "Data center revenue as a leading HBM demand proxy",
    },
    {
        "ticker": "MU",
        "name": "Micron",
        "cik": "0000723125",
        "group": "Memory",
        "memory_angle": "HBM, DRAM/NAND pricing, inventory and capex read-through",
    },
]

CONCEPTS = {
    "capex": {
        "label": "Capex / PP&E purchases",
        "taxonomy": "us-gaap",
        "tags": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquireProductiveAssets",
            "CapitalExpendituresIncurredButNotYetPaid",
        ],
        "statement": "cash flow",
        "unit": "USD",
    },
    "revenue": {
        "label": "Revenue",
        "taxonomy": "us-gaap",
        "tags": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ],
        "statement": "income",
        "unit": "USD",
    },
    "rpo": {
        "label": "Remaining performance obligations",
        "taxonomy": "us-gaap",
        "tags": [
            "TransactionPriceAllocatedToRemainingPerformanceObligations",
            "RemainingPerformanceObligation",
        ],
        "statement": "footnote",
        "unit": "USD",
    },
    "inventory": {
        "label": "Inventory",
        "taxonomy": "us-gaap",
        "tags": [
            "InventoryNet",
            "InventoryFinishedGoodsNetOfReserves",
        ],
        "statement": "balance sheet",
        "unit": "USD",
    },
}

SIGNAL_WEIGHTS = {
    "capex": 0.45,
    "revenue": 0.25,
    "rpo": 0.20,
    "inventory": -0.10,
}
