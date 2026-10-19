"""
ARFEZ AI v3.0 - Tek Kaynak Hisse Evreni
========================================
data_collector.py, seed_data.py ve app_mssql.py buradan import eder.
Bu listeyi burada güncelle; başka yerde kopya tutma.
"""

UNIVERSE = [
    "ABT", "AKR", "AAMI", "ACMR", "ADEA", "ADBE", "AMD", "AKTS", "ALMR", "ALLY",
    "GOOGL", "AMZN", "AMTM", "AS", "AEP", "AHR", "AIG", "ANDG", "APGE", "APO",
    "AAPL", "AADX", "ADM", "ACA", "ARES", "ATI", "TEAM", "AVLN", "BKU", "BRK-B",
    "BGC", "BILL", "TECH", "BX", "OBDC", "OWL", "BOTZ", "BWA", "BHF", "AVGO",
    "BG", "CZR", "CCJ", "CEPV", "COF", "CTRE", "CG", "CRS", "CPRX", "CX",
    "CBRS", "GTLS", "CB", "CFG", "NET", "CME", "CMS", "KO", "CEG", "CNM",
    "CORZ", "CRBG", "CRWV", "CPNG", "CRH", "DDOG", "DLR", "DBRG", "DIS", "D",
    "DASH", "DPC", "ENRD", "EA", "LLY", "EME", "ETR", "EROC", "ESPR", "ETSY",
    "ES", "EVGO", "FVR", "FIGR", "FSLR", "FE", "FBC", "FPS", "FCX", "GLXY",
    "GFL", "GBTG", "SJW", "Hawk", "COAG", "HTZ", "HONA", "HON", "HUBG", "HUM",
    "HUN", "IDA", "PI", "INGM", "INNO", "INTC", "IBKR", "EMXC", "MUB", "ITRI",
    "ITT", "J", "JAN", "JNJ", "JPM", "KLRA", "KARD", "KEEL", "KVUE", "KRG",
    "KKR", "KDK", "KWEB", "LGN", "LIFT", "LINC", "LIN", "LCID", "MAC", "MASI",
    "MRVL", "MTZ", "MA", "MTRN", "MCD", "MDLN", "META", "MCB", "MGEE", "MGM",
    "MCHP", "MU", "MSFT", "MFIC", "MIDD", "MS", "NATL", "NBIS", "NPI", "NFLX",
    "NOC", "NUVL", "NVDA", "ON", "PZZA", "PAYO", "PM", "PNFP", "PONY", "POR",
    "PPL", "PRIM", "PGR", "PEG", "QNTM", "QXO", "RDNT", "USAR", "RBC", "RDDT",
    "ROKU", "RUSHA", "RSI", "SPGI", "XLF", "SRE", "NOW", "SNAI", "SILA", "SITM",
    "SW", "SNOW", "SOLV", "SGI", "SFST", "SPSB", "SARO", "SPY", "STLA", "STM",
    "SUNB", "RUN", "SMCI", "TE", "TSM", "TLN", "TALK", "TMHC", "TNC", "TEX",
    "TSLA", "TXN", "TKR", "TKO", "BLD", "TPG", "UBER", "ULS", "UNH", "VRNS",
    "VRSK", "VZ", "VSGN", "VSH", "VST", "VSEC", "WMT", "WBD", "WBS", "WEC",
    "WIX", "WWD", "XEL", "XE", "YSWY", "YSS", "ZETA", "ZTS",
]
