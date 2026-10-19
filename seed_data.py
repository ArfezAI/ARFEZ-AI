"""
ARFEZ AI - Ornek Veri Doldurucu (yalnizca DEVELOPMENT / ARFEZ_DEV)

UYARI:
- Bu script sadece ARFEZ_ENV=development ve ARFEZ_SEED_DATABASE=ARFEZ_DEV iken calisir.
- Uretilen tum fiyat/skor/sinyaller RASTGELE TEST VERISIDIR; canli yatirim analizi degildir.
- Gercek fiyat, adil deger ve yatirim sinyalleri data_collector.py,
  fair_value_engine.py ve canli veri akisindan gelmelidir.
- Calistirmadan once: ARFEZ_DB_PASSWORD ortam degiskenini tanimla.
"""
import os
import pyodbc
from datetime import datetime, timedelta
import random
import time

from universe import SYMBOL_UNIVERSE

# Uyumluluk: eski kod SYMBOLS adini kullaniyordu.
SYMBOLS = SYMBOL_UNIVERSE

# ---------------------------------------------------------------------------
# 1. ADIM - Guvenli baglanti  (DEGISTIRILMEDI)
# ---------------------------------------------------------------------------
APP_ENV = os.getenv("ARFEZ_ENV", "development").strip().lower()
if APP_ENV != "development":
    raise RuntimeError(
        "seed_data.py yalnizca development ortaminda calistirilabilir."
    )

DB_NAME = os.getenv("ARFEZ_SEED_DATABASE", "ARFEZ_DEV").strip()
if DB_NAME != "ARFEZ_DEV":
    raise RuntimeError(
        "Ornek veri icin yalnizca ARFEZ_DEV veritabani kullanilabilir."
    )

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=DESKTOP-L7INTLS,1433;"
    f"DATABASE={DB_NAME};"
    "UID=sa;"
    f"PWD={os.environ.get('ARFEZ_DB_PASSWORD', '')};"
    "TrustServerCertificate=yes;"
)


def get_db():
    if APP_ENV != "development" or DB_NAME != "ARFEZ_DEV":
        raise RuntimeError("Guvenlik kontrolu basarisiz.")
    if not os.environ.get("ARFEZ_DB_PASSWORD"):
        raise RuntimeError("ARFEZ_DB_PASSWORD ortam degiskeni tanimli degil.")
    return pyodbc.connect(CONN_STR)


# ---------------------------------------------------------------------------
# Yardimci
# ---------------------------------------------------------------------------
def run(cursor, sql, params=None, max_retries=5):
    """Deadlock (1205/40001) durumunda otomatik tekrar dener."""
    for attempt in range(max_retries):
        try:
            if params is not None:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return
        except pyodbc.Error as ex:
            msg = str(ex)
            if '40001' in msg or '1205' in msg:
                wait = min(2 ** attempt, 10)
                print("[RETRY] Deadlock tespit edildi - {}. deneme, {}s bekleniyor...".format(attempt + 1, wait))
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("Deadlock {} deneme sonrasinda cozulemedi".format(max_retries))


# ---------------------------------------------------------------------------
# 2. ADIM - seed_stocks (inserted/skipped/before kaldirildi)
# ---------------------------------------------------------------------------
def seed_stocks(cursor):
    stocks = [
        ('ABT', 'ABBOTT LABORATORIES', 'Healthcare'),
        ('AKR', 'ACADIA RLTY TR', 'Real Estate'),
        ('AAMI', 'ACADIAN ASSET MANAGEMENT INC', 'Financial Services'),
        ('ACMR', 'ACM RESH INC', 'Technology'),
        ('ADEA', 'ADEIA INC', 'Technology'),
        ('ADBE', 'ADOBE INC', 'Technology'),
        ('AMD', 'ADVANCED MICRO DEVICES INC', 'Technology'),
        ('AKTS', 'AKTIS ONCOLOGY INC', 'Healthcare'),
        ('ALMR', 'ALAMAR BIOSCIENCES INC', 'Healthcare'),
        ('ALLY', 'ALLY FINL INC', 'Financial Services'),
        ('GOOGL', 'ALPHABET INC', 'Communication Services'),
        ('AMZN', 'AMAZON COM INC', 'Consumer Cyclical'),
        ('AMTM', 'AMENTUM HOLDINGS INC', 'Industrials'),
        ('AS', 'AMER SPORTS INC', 'Consumer Cyclical'),
        ('AEP', 'AMERICAN ELEC PWR CO INC', 'Utilities'),
        ('AHR', 'AMERICAN HEALTHCARE REIT INC', 'Real Estate'),
        ('AIG', 'AMERICAN INTL GROUP INC', 'Financial Services'),
        ('ANDG', 'ANDERSEN GROUP INC', 'Industrials'),
        ('APGE', 'APOGEE THERAPEUTICS INC', 'Healthcare'),
        ('APO', 'APOLLO GLOBAL MGMT INC', 'Financial Services'),
        ('AAPL', 'APPLE INC', 'Technology'),
        ('AADX', 'APPLIED AEROSPACE & DEFENSE', 'Industrials'),
        ('ADM', 'ARCHER DANIELS MIDLAND CO', 'Consumer Defensive'),
        ('ACA', 'ARCOSA INC', 'Industrials'),
        ('ARES', 'ARES MANAGEMENT CORPORATION', 'Financial Services'),
        ('ATI', 'ATI INC', 'Industrials'),
        ('TEAM', 'ATLASSIAN CORPORATION', 'Technology'),
        ('AVLN', 'AVALYN PHARMACEUTICALS INC', 'Healthcare'),
        ('BKU', 'BANKUNITED INC', 'Financial Services'),
        ('BRK-B', 'BERKSHIRE HATHAWAY INC DEL', 'Financial Services'),
        ('BGC', 'BGC GROUP INC', 'Financial Services'),
        ('BILL', 'BILL HOLDINGS INC', 'Technology'),
        ('TECH', 'BIO-TECHNE CORP', 'Healthcare'),
        ('BX', 'BLACKSTONE INC', 'Financial Services'),
        ('OBDC', 'BLUE OWL CAPITAL CORPORATION', 'Financial Services'),
        ('OWL', 'BLUE OWL CAPITAL INC', 'Financial Services'),
        ('BOTZ', 'BLUE OWL TECHNOLOGY FIN CORP', 'Financial Services'),
        ('BWA', 'BORGWARNER INC', 'Consumer Cyclical'),
        ('BHF', 'BRIGHTHOUSE FINL INC', 'Financial Services'),
        ('AVGO', 'BROADCOM INC', 'Technology'),
        ('BG', 'BUNGE GLOBAL SA', 'Consumer Defensive'),
        ('CZR', 'CAESARS ENTERTAINMENT INC NE', 'Consumer Cyclical'),
        ('CCJ', 'CAMECO CORP', 'Energy'),
        ('CEPV', 'CANTOR EQUITY PARTNERS V INC', 'Financial Services'),
        ('COF', 'CAPITAL ONE FINL CORP', 'Financial Services'),
        ('CTRE', 'CARETRUST REIT INC', 'Real Estate'),
        ('CG', 'CARLYLE GROUP INC', 'Financial Services'),
        ('CRS', 'CARPENTER TECHNOLOGY CORP', 'Industrials'),
        ('CPRX', 'CATALYST PHARMACEUTICALS INC', 'Healthcare'),
        ('CX', 'CEMEX SA EURO MTN BE 144A', 'Materials'),
        ('CBRS', 'CEREBRAS SYSTEMS INC', 'Technology'),
        ('GTLS', 'CHART INDS INC', 'Industrials'),
        ('CB', 'CHUBB LIMITED', 'Financial Services'),
        ('CFG', 'CITIZENS FINL GROUP INC', 'Financial Services'),
        ('NET', 'CLOUDFLARE INC', 'Technology'),
        ('CME', 'CME GROUP INC', 'Financial Services'),
        ('CMS', 'CMS ENERGY CORP', 'Utilities'),
        ('KO', 'COCA COLA CO', 'Consumer Defensive'),
        ('CEG', 'CONSTELLATION ENERGY CORP', 'Utilities'),
        ('CNM', 'CORE & MAIN INC', 'Industrials'),
        ('CORZ', 'CORE SCIENTIFIC INC NEW', 'Technology'),
        ('CRBG', 'COREBRIDGE FINL INC', 'Financial Services'),
        ('CRWV', 'COREWEAVE INC', 'Technology'),
        ('CPNG', 'COUPANG INC', 'Consumer Cyclical'),
        ('CRH', 'CRH PLC', 'Materials'),
        ('DDOG', 'DATADOG INC', 'Technology'),
        ('DLR', 'DIGITAL RLTY TR INC', 'Real Estate'),
        ('DBRG', 'DIGITALBRIDGE GROUP INC', 'Real Estate'),
        ('DIS', 'DISNEY WALT CO', 'Communication Services'),
        ('D', 'DOMINION ENERGY INC', 'Utilities'),
        ('DASH', 'DOORDASH INC', 'Consumer Cyclical'),
        ('DPC', 'DPC HOLDINGS PLC', 'Industrials'),
        ('ENRD', 'EINRIDE AB', 'Industrials'),
        ('EA', 'ELECTRONIC ARTS INC', 'Communication Services'),
        ('LLY', 'ELI LILLY & CO', 'Healthcare'),
        ('EME', 'EMCOR GROUP INC', 'Industrials'),
        ('ETR', 'ENTERGY CORP NEW', 'Utilities'),
        ('EROC', 'EROCK INC', 'Industrials'),
        ('ESPR', 'ESPERION THERAPEUTICS INC NE', 'Healthcare'),
        ('ETSY', 'ETSY INC', 'Consumer Cyclical'),
        ('ES', 'EVERSOURCE ENERGY', 'Utilities'),
        ('EVGO', 'EVGO INC', 'Consumer Cyclical'),
        ('FVR', 'FERVO ENERGY CO', 'Energy'),
        ('FIGR', 'FIGURE TECHNOLOGY SOLUTIO', 'Financial Services'),
        ('FSLR', 'FIRST SOLAR INC', 'Technology'),
        ('FE', 'FIRSTENERGY CORP', 'Utilities'),
        ('FBC', 'FLAGSTAR BANK NATIONAL ASSOC', 'Financial Services'),
        ('FPS', 'FORGENT POWER SOLUTIONS INC', 'Industrials'),
        ('FCX', 'FREEPORT MCMORAN INC', 'Materials'),
        ('GLXY', 'GALAXY DIGITAL INC.', 'Financial Services'),
        ('GFL', 'GFL ENVIRONMENTAL INC', 'Industrials'),
        ('GBTG', 'GLOBAL BUSINESS TRAVEL GROUP', 'Consumer Cyclical'),
        ('SJW', 'H2O AMERICA', 'Utilities'),
        ('Hawk', 'HAWKEYE 360 INC', 'Technology'),
        ('COAG', 'HEMAB THERAPEUTICS HLDGS INC', 'Healthcare'),
        ('HTZ', 'HERTZ GLOBAL HLDGS INC', 'Industrials'),
        ('HONA', 'HONEYWELL AEROSPACE INC', 'Industrials'),
        ('HON', 'HONEYWELL INTL INC', 'Industrials'),
        ('HUBG', 'HUB GROUP INC', 'Industrials'),
        ('HUM', 'HUMANA INC', 'Healthcare'),
        ('HUN', 'HUNTSMAN CORP', 'Materials'),
        ('IDA', 'IDACORP INC', 'Utilities'),
        ('PI', 'IMPINJ INC', 'Technology'),
        ('INGM', 'INGRAM MICRO HLDG CORP', 'Technology'),
        ('INNO', 'INNIO NV', 'Industrials'),
        ('INTC', 'INTEL CORP', 'Technology'),
        ('IBKR', 'INTERACTIVE BROKERS GROUP IN', 'Financial Services'),
        ('EMXC', 'ISHARES INC', 'Financial Services'),
        ('MUB', 'ISHARES TR', 'Financial Services'),
        ('ITRI', 'ITRON INC', 'Technology'),
        ('ITT', 'ITT INC', 'Industrials'),
        ('J', 'JACOBS SOLUTIONS INC', 'Industrials'),
        ('JAN', 'JANUS LIVING INC', 'Real Estate'),
        ('JNJ', 'JOHNSON & JOHNSON', 'Healthcare'),
        ('JPM', 'JPMORGAN CHASE & CO', 'Financial Services'),
        ('KLRA', 'KAILERA THERAPEUTICS INC', 'Healthcare'),
        ('KARD', 'KARDIGAN INC', 'Healthcare'),
        ('KEEL', 'KEEL INFRASTRUCTURE CORP', 'Technology'),
        ('KVUE', 'KENVUE INC', 'Consumer Defensive'),
        ('KRG', 'KITE REALTY GROUP TRUST', 'Real Estate'),
        ('KKR', 'KKR & CO INC', 'Financial Services'),
        ('KDK', 'KODIAK AI INC.', 'Technology'),
        ('KWEB', 'KRANESHARES TRUST', 'Financial Services'),
        ('LGN', 'LEGENCE CORP', 'Industrials'),
        ('LIFT', 'LIFTOFF MOBILE INC', 'Technology'),
        ('LINC', 'LINCOLN INTL INC', 'Industrials'),
        ('LIN', 'LINDE PLC', 'Materials'),
        ('LCID', 'LUCID GROUP INC', 'Consumer Cyclical'),
        ('MAC', 'MACERICH CO', 'Real Estate'),
        ('MASI', 'MADISON AIR SOLUTIONS CORP', 'Industrials'),
        ('MRVL', 'MARVELL TECHNOLOGY INC', 'Technology'),
        ('MTZ', 'MASTEC INC', 'Industrials'),
        ('MA', 'MASTERCARD INCORPORATED', 'Financial Services'),
        ('MTRN', 'MATERION CORP', 'Materials'),
        ('MCD', 'MCDONALDS CORP', 'Consumer Cyclical'),
        ('MDLN', 'MEDLINE INC', 'Healthcare'),
        ('META', 'META PLATFORMS INC', 'Communication Services'),
        ('MCB', 'METROPOLITAN BK HLDG CORP', 'Financial Services'),
        ('MGEE', 'MGE ENERGY INC', 'Utilities'),
        ('MGM', 'MGM RESORTS INTERNATIONAL', 'Consumer Cyclical'),
        ('MCHP', 'MICROCHIP TECHNOLOGY INC.', 'Technology'),
        ('MU', 'MICRON TECHNOLOGY INC', 'Technology'),
        ('MSFT', 'MICROSOFT CORP', 'Technology'),
        ('MFIC', 'MIDCAP FINANCIAL INVSTMNT CO', 'Financial Services'),
        ('MIDD', 'MIDDLEBY CORP', 'Industrials'),
        ('MS', 'MORGAN STANLEY', 'Financial Services'),
        ('NATL', 'NCR ATLEOS CORPORATION', 'Technology'),
        ('NBIS', 'NEBIUS GROUP N.V.', 'Technology'),
        ('NPI', 'NEPTUNE INS HLDGS INC', 'Financial Services'),
        ('NFLX', 'NETFLIX INC.', 'Communication Services'),
        ('NOC', 'NORTHROP GRUMMAN CORP', 'Industrials'),
        ('NUVL', 'NUVALENT INC', 'Healthcare'),
        ('NVDA', 'NVIDIA CORPORATION', 'Technology'),
        ('ON', 'ON SEMICONDUCTOR CORP', 'Technology'),
        ('PZZA', 'PAPA JOHNS INTL INC', 'Consumer Cyclical'),
        ('PAYO', 'PAYONEER GLOBAL INC', 'Technology'),
        ('PM', 'PHILIP MORRIS INTL INC', 'Consumer Defensive'),
        ('PNFP', 'PINNACLE FINL PARTNERS INC', 'Financial Services'),
        ('PONY', 'PONY AI INC', 'Technology'),
        ('POR', 'PORTLAND GEN ELEC CO', 'Utilities'),
        ('PPL', 'PPL CORP', 'Utilities'),
        ('PRIM', 'PRIMORIS SVCS CORP', 'Industrials'),
        ('PGR', 'PROGRESSIVE CORP', 'Financial Services'),
        ('PEG', 'PUBLIC SVC ENTERPRISE GROUP', 'Utilities'),
        ('QNTM', 'QUANTINUUM INC', 'Technology'),
        ('QXO', 'QXO INC', 'Industrials'),
        ('RDNT', 'RADNET INC', 'Healthcare'),
        ('USAR', 'RARE EARTHS AMERICAS INC', 'Materials'),
        ('RBC', 'RBC BEARINGS INC', 'Industrials'),
        ('RDDT', 'REDDIT INC', 'Communication Services'),
        ('ROKU', 'ROKU INC', 'Communication Services'),
        ('RUSHA', 'RUSH ENTERPRISES INC', 'Industrials'),
        ('RSI', 'RUSH STREET INTERACTIVE INC', 'Consumer Cyclical'),
        ('SPGI', 'S&P GLOBAL INC', 'Financial Services'),
        ('XLF', 'SELECT SECTOR SPDR TR', 'Financial Services'),
        ('SRE', 'SEMPRA', 'Utilities'),
        ('NOW', 'SERVICENOW INC', 'Technology'),
        ('SNAI', 'SHARONAI HOLDINGS INC', 'Healthcare'),
        ('SILA', 'SILA REALTY TRUST INC', 'Real Estate'),
        ('SITM', 'SITIME CORP', 'Technology'),
        ('SW', 'SMURFIT WESTROCK PLC', 'Materials'),
        ('SNOW', 'SNOWFLAKE INC', 'Technology'),
        ('SOLV', 'SOLV ENERGY INC', 'Energy'),
        ('SGI', 'SOMNIGROUP INTERNATIONAL INC', 'Healthcare'),
        ('SFST', 'SOUTHERN FIRST BANCSHARES', 'Financial Services'),
        ('SPSB', 'SPDR SERIES TRUST', 'Financial Services'),
        ('SARO', 'STANDARDAERO INC', 'Industrials'),
        ('SPY', 'STATE STR SPDR S&P 500 ETF T', 'Financial Services'),
        ('STLA', 'STELLANTIS N.V', 'Consumer Cyclical'),
        ('STM', 'STMICROELECTRONICS N V', 'Technology'),
        ('SUNB', 'SUNBELT RENTALS HOLDINGS INC', 'Industrials'),
        ('RUN', 'SUNRUN INC', 'Technology'),
        ('SMCI', 'SUPER MICRO COMPUTER INC', 'Technology'),
        ('TE', 'T1 ENERGY INC', 'Energy'),
        ('TSM', 'TAIWAN SEMICONDUCTOR MANUFAC', 'Technology'),
        ('TLN', 'TALEN ENERGY CORP', 'Utilities'),
        ('TALK', 'TALKSPACE INC', 'Healthcare'),
        ('TMHC', 'TAYLOR MORRISON HOME CORP', 'Consumer Cyclical'),
        ('TNC', 'TENNANT CO', 'Industrials'),
        ('TEX', 'TEREX CORP NEW', 'Industrials'),
        ('TSLA', 'TESLA INC', 'Consumer Cyclical'),
        ('TXN', 'TEXAS INSTRS INC', 'Technology'),
        ('TKR', 'TIMKEN CO', 'Industrials'),
        ('TKO', 'TKO GROUP HOLDINGS INC', 'Communication Services'),
        ('BLD', 'TOPBUILD COR', 'Industrials'),
        ('TPG', 'TPG INC', 'Financial Services'),
        ('UBER', 'UBER TECHNOLOGIES INC', 'Technology'),
        ('ULS', 'UL SOLUTIONS INC', 'Industrials'),
        ('UNH', 'UNITEDHEALTH GROUP INC', 'Healthcare'),
        ('VRNS', 'VARONIS SYS INC', 'Technology'),
        ('VRSK', 'VERISK ANALYTICS INC', 'Industrials'),
        ('VZ', 'VERIZON COMMUNICATIONS INC', 'Communication Services'),
        ('VSGN', 'VERSIGENT PLC', 'Technology'),
        ('VSH', 'VISHAY INTERTECHNOLOGY INC', 'Technology'),
        ('VST', 'VISTRA CORP', 'Utilities'),
        ('VSEC', 'VSE CORP', 'Industrials'),
        ('WMT', 'WALMART INC', 'Consumer Defensive'),
        ('WBD', 'WARNER BROS DISCOVERY INC', 'Communication Services'),
        ('WBS', 'WEBSTER FINL CORP', 'Financial Services'),
        ('WEC', 'WEC ENERGY GROUP INC', 'Utilities'),
        ('WIX', 'WIX COM LTD', 'Technology'),
        ('WWD', 'WOODWARD INC', 'Industrials'),
        ('XEL', 'XCEL ENERGY INC', 'Utilities'),
        ('XE', 'X-ENERGY INC', 'Energy'),
        ('YSWY', 'YESWAY INC', 'Consumer Defensive'),
        ('YSS', 'YORK SPACE SYSTEMS INC', 'Industrials'),
        ('ZETA', 'ZETA GLOBAL HOLDINGS CORP', 'Technology'),
        ('ZTS', 'ZOETIS INC', 'Healthcare'),
    ]

    for s in stocks:
        # Toplu DELETE yok; yalnizca olmayan sembolleri ekle.
        # NOT: Bu yaklasim mevcut sembollerin name/sector bilgisini GUNCELLEMEZ.
        run(
            cursor,
            """
            IF NOT EXISTS (SELECT 1 FROM stocks WHERE symbol = ?)
                INSERT INTO stocks (symbol, name, sector)
                VALUES (?, ?, ?)
            """,
            (s[0], s[0], s[1], s[2]),
        )
    print("[OK] stocks: {} sembol kontrol edildi (mevcut olanlara dokunulmadi)".format(len(stocks)))


# ---------------------------------------------------------------------------
# 3. ADIM - seed_daily_scores (yerel liste kaldirildi, SYMBOLS kullaniliyor)
# ---------------------------------------------------------------------------
def seed_daily_scores(cursor):
    today = datetime.now().strftime('%Y-%m-%d')

    for sym in SYMBOLS:
        arfez = random.randint(45, 98)
        final = min(arfez + random.randint(-10, 5), 100)
        signal = 'AL' if final >= 80 else 'SAT' if final < 50 else 'BEKLE'
        target = round(random.uniform(50, 500), 2)
        stop = round(target * 0.85, 2)
        expected = round((target - stop) / stop * 100, 1)

        run(cursor, """
            IF NOT EXISTS (
                SELECT 1 FROM daily_scores WHERE symbol = ? AND date = ?
            )
            INSERT INTO daily_scores
                (symbol, date, arfez_score, new_world, technical, fundamental,
                 risk, confidence, macro, valuation, capital_flow, theme,
                 final_score, signal, target_price, stop_loss, expected_return)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sym, today,
            sym, today, arfez, random.randint(50, 95), random.randint(40, 90),
            random.randint(50, 95), random.randint(20, 70), random.randint(60, 99),
            random.randint(40, 85), random.randint(50, 90), random.randint(45, 88),
            random.randint(55, 92), final, signal, target, stop, expected,
        ))
    print("[OK] daily_scores: {} sembol icin gunluk skor kontrol edildi ({})".format(len(SYMBOLS), today))


# ---------------------------------------------------------------------------
# 3. ADIM - seed_macro
# ---------------------------------------------------------------------------
def seed_macro(cursor):
    today = datetime.now().strftime('%Y-%m-%d')
    regimes = ["risk-on", "risk-off", "neutral", "bullish", "bearish"]
    run(cursor, """
        IF NOT EXISTS (SELECT 1 FROM macro_data WHERE date = ?)
        INSERT INTO macro_data (date, vix, dxy, us10y, sp500, nasdaq, regime)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        today,
        today, round(random.uniform(14, 28), 2), round(random.uniform(100, 108), 2),
        round(random.uniform(3.8, 4.8), 2), round(random.uniform(5500, 6100), 2),
        round(random.uniform(17500, 19500), 2), random.choice(regimes),
    ))
    print("[OK] macro_data: bugunun makro kaydi kontrol edildi/eklendi")


# ---------------------------------------------------------------------------
# 3. ADIM - seed_pipeline
# ---------------------------------------------------------------------------
def seed_pipeline(cursor):
    today = datetime.now().strftime('%Y-%m-%d')
    steps = [
        ("Makro Tarama", "done", "09:31"),
        ("Rejim Belirleme", "done", "09:32"),
        ("Tema Analizi", "done", "09:35"),
        ("New World Radar", "done", "09:40"),
        ("Opportunity Engine", "done", "09:45"),
        ("Fundamental Analiz", "done", "09:50"),
        ("Options Analizi", "done", "09:55"),
        ("Risk Degerlendirmesi", "done", "10:00"),
        ("Confidence Kalibrasyonu", "done", "10:05"),
        ("Final Decision", "done", "10:10"),
    ]
    for s in steps:
        run(cursor, """
            IF NOT EXISTS (
                SELECT 1 FROM pipeline_status WHERE date = ? AND step_name = ?
            )
            INSERT INTO pipeline_status (date, step_name, status, time)
            VALUES (?, ?, ?, ?)
        """, (today, s[0], today, s[0], s[1], s[2]))
    print("[OK] pipeline_status: 10 adim kontrol edildi/eklendi")


# ---------------------------------------------------------------------------
# 3. ADIM - seed_fund_holdings (count korundu, log'da kullaniliyor)
# ---------------------------------------------------------------------------
def seed_fund_holdings(cursor):
    funds = ["Buffett", "Soros", "Druckenmiller", "Tepper", "Ackman",
             "Tiger Global", "Coatue", "Bridgewater", "ARK", "Viking"]
    symbols = ["NVDA", "PLTR", "MSFT", "AAPL", "TSLA", "AMD", "META", "AMZN", "GOOGL", "AVGO"]
    quarter = "2026Q2"

    count = 0
    for fund in funds:
        picks = random.sample(symbols, random.randint(3, 7))
        for sym in picks:
            weight = round(random.uniform(1.5, 8.5), 2)
            change = round(random.uniform(-15, 25), 2)
            run(cursor, """
                IF NOT EXISTS (
                    SELECT 1 FROM fund_holdings
                    WHERE fund_name = ? AND symbol = ? AND quarter = ?
                )
                INSERT INTO fund_holdings (fund_name, symbol, weight, change_qoq, quarter)
                VALUES (?, ?, ?, ?, ?)
            """, (fund, sym, quarter, fund, sym, weight, change, quarter))
            count += 1
    print("[OK] fund_holdings: {} fon, {} pozisyon kontrol edildi ({})".format(
        len(funds), count, quarter))


# ---------------------------------------------------------------------------
# 3. ADIM - seed_predictions (inserted kaldirildi, fonksiyon tamamlandi)
# ---------------------------------------------------------------------------
def seed_predictions(cursor):
    symbols = ["NVDA", "PLTR", "MSFT", "AAPL", "TSLA"]

    # Post-Mortem icin baslangic hata dagilimi (toplam 38, kalan 12 hatasiz)
    initial_errors = {
        "M1": 5,   # Makro hatasi
        "H1": 3,   # Haber hatasi
        "S1": 2,   # Sektor hatasi
        "T1": 10,  # Teknik hatasi
        "R1": 8,   # Rejim hatasi
        "B1": 3,   # Band hatasi
        "C1": 7,   # Cross-Asset hatasi
    }

    for error_code, count in initial_errors.items():
        for _ in range(count):
            sym = random.choice(symbols)
            date = (datetime.now() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d")
            run(cursor, """
                IF NOT EXISTS (
                    SELECT 1 FROM prediction_errors
                    WHERE symbol = ? AND date = ? AND error_code = ?
                )
                INSERT INTO prediction_errors (symbol, date, error_code)
                VALUES (?, ?, ?)
            """, (sym, date, error_code, sym, date, error_code))
    print("[OK] prediction_errors: {} hata kodu kontrol edildi/eklendi".format(
        len(initial_errors)))
