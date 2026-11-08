"""Default stock universes. No broker orders are placed by importing this file.

All sector constituents are candidates. ETFs are sector-confirmation references
and optional single substitutes; leveraged SOXL is NOT automatically selected.
"""
SECTORS = {
    "semiconductors": (
        "AMD","NVDA","MU","SNDK","WDC","TSM","AVGO","QCOM","INTC",
        "AMAT","LRCX","KLAC","ASML","MRVL","TXN","ON","MCHP","ALAB"
    ),
    "oil_energy": (
        "XOM","CVX","COP","OXY","EOG","SLB","HAL","FANG","DVN",
        "MPC","VLO","PSX","BKR","KMI","WMB","APA"
    ),
    "cybersecurity": (
        "CRWD","PANW","ZS","FTNT","OKTA","NET","CYBR","CHKP",
        "S","TENB","RPD","VRNS"
    ),
    "ai_infrastructure": (
        "ANET","VRT","DELL","SMCI","HPE","ETN","CARR","APH"
    ),
}
SECTOR_ETFS = {
    "semiconductors":"SOXX",
    "oil_energy":"XLE",
    "cybersecurity":"CIBR",
    "ai_infrastructure":"XLK"
}
# One leveraged alternative only by a later separately tested strategy;
# never buy SOXX and SOXL together just because the sector is strong.
LEVERAGED_ALTERNATIVES = {"semiconductors":"SOXL"}

# Three representative active equities confirm sector direction. Overnight,
# many other constituents legitimately have no one-minute trades. Those
# missing bars must not prevent liquid peers being assessed individually.
SECTOR_ANCHORS = {
    "semiconductors": ("AMD", "MU", "SNDK"),
    "oil_energy": ("XOM", "CVX", "OXY"),
    "cybersecurity": ("CRWD", "PANW", "ZS"),
    "ai_infrastructure": ("ANET", "VRT", "DELL"),
}
