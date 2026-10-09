"""
ARFEZ AI - Ornek Veri Doldurucu
ONCE yukaridaki SQL'i calistir, SONRA bunu calistir.
"""
import pyodbc
from datetime import datetime, timedelta
import random
import time

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=DESKTOP-L7INTLS,1433;"
    "DATABASE=ARFEZ;"
    "UID=sa;"
    "PWD=2209;"
    "TrustServerCertificate=yes;"
)

def get_db():
    return pyodbc.connect(CONN_STR)


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
    run(cursor, "DELETE FROM daily_scores WITH (TABLOCK)")
    run(cursor, "DELETE FROM stocks WITH (TABLOCK)")
    for s in stocks:
        run(cursor, "INSERT INTO stocks (symbol, name, sector) VALUES (?, ?, ?)", s)
    print("[OK] stocks: {} hisse eklendi".format(len(stocks)))

def seed_daily_scores(cursor):
    symbols = ['ABT', 'AKR', 'AAMI', 'ACMR', 'ADEA', 'ADBE', 'AMD', 'AKTS', 'ALMR', 'ALLY', 'GOOGL', 'AMZN', 'AMTM', 'AS', 'AEP', 'AHR', 'AIG', 'ANDG', 'APGE', 'APO', 'AAPL', 'AADX', 'ADM', 'ACA', 'ARES', 'ATI', 'TEAM', 'AVLN', 'BKU', 'BRK-B', 'BGC', 'BILL', 'TECH', 'BX', 'OBDC', 'OWL', 'BOTZ', 'BWA', 'BHF', 'AVGO', 'BG', 'CZR', 'CCJ', 'CEPV', 'COF', 'CTRE', 'CG', 'CRS', 'CPRX', 'CX', 'CBRS', 'GTLS', 'CB', 'CFG', 'NET', 'CME', 'CMS', 'KO', 'CEG', 'CNM', 'CORZ', 'CRBG', 'CRWV', 'CPNG', 'CRH', 'DDOG', 'DLR', 'DBRG', 'DIS', 'D', 'DASH', 'DPC', 'ENRD', 'EA', 'LLY', 'EME', 'ETR', 'EROC', 'ESPR', 'ETSY', 'ES', 'EVGO', 'FVR', 'FIGR', 'FSLR', 'FE', 'FBC', 'FPS', 'FCX', 'GLXY', 'GFL', 'GBTG', 'SJW', 'Hawk', 'COAG', 'HTZ', 'HONA', 'HON', 'HUBG', 'HUM', 'HUN', 'IDA', 'PI', 'INGM', 'INNO', 'INTC', 'IBKR', 'EMXC', 'MUB', 'ITRI', 'ITT', 'J', 'JAN', 'JNJ', 'JPM', 'KLRA', 'KARD', 'KEEL', 'KVUE', 'KRG', 'KKR', 'KDK', 'KWEB', 'LGN', 'LIFT', 'LINC', 'LIN', 'LCID', 'MAC', 'MASI', 'MRVL', 'MTZ', 'MA', 'MTRN', 'MCD', 'MDLN', 'META', 'MCB', 'MGEE', 'MGM', 'MCHP', 'MU', 'MSFT', 'MFIC', 'MIDD', 'MS', 'NATL', 'NBIS', 'NPI', 'NFLX', 'NOC', 'NUVL', 'NVDA', 'ON', 'PZZA', 'PAYO', 'PM', 'PNFP', 'PONY', 'POR', 'PPL', 'PRIM', 'PGR', 'PEG', 'QNTM', 'QXO', 'RDNT', 'USAR', 'RBC', 'RDDT', 'ROKU', 'RUSHA', 'RSI', 'SPGI', 'XLF', 'SRE', 'NOW', 'SNAI', 'SILA', 'SITM', 'SW', 'SNOW', 'SOLV', 'SGI', 'SFST', 'SPSB', 'SARO', 'SPY', 'STLA', 'STM', 'SUNB', 'RUN', 'SMCI', 'TE', 'TSM', 'TLN', 'TALK', 'TMHC', 'TNC', 'TEX', 'TSLA', 'TXN', 'TKR', 'TKO', 'BLD', 'TPG', 'UBER', 'ULS', 'UNH', 'VRNS', 'VRSK', 'VZ', 'VSGN', 'VSH', 'VST', 'VSEC', 'WMT', 'WBD', 'WBS', 'WEC', 'WIX', 'WWD', 'XEL', 'XE', 'YSWY', 'YSS', 'ZETA', 'ZTS']
    today = datetime.now().strftime('%Y-%m-%d')
    run(cursor, "DELETE FROM daily_scores WHERE date = ?", (today,))
    
    for sym in symbols:
        arfez = random.randint(45, 98)
        final = min(arfez + random.randint(-10, 5), 100)
        signal = 'AL' if final >= 80 else 'SAT' if final < 50 else 'BEKLE'
        target = round(random.uniform(50, 500), 2)
        stop = round(target * 0.85, 2)
        expected = round((target - stop) / stop * 100, 1)
        
        run(cursor, """
            INSERT INTO daily_scores (symbol, date, arfez_score, new_world, technical, fundamental, risk, confidence,
            macro, valuation, capital_flow, theme, final_score, signal, target_price, stop_loss, expected_return)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (sym, today, arfez, random.randint(50,95), random.randint(40,90), random.randint(50,95),
              random.randint(20,70), random.randint(60,99), random.randint(40,85), random.randint(50,90),
              random.randint(45,88), random.randint(55,92), final, signal, target, stop, expected))
    print("[OK] daily_scores: {} gunluk skor eklendi ({})".format(len(symbols), today))

def seed_macro(cursor):
    run(cursor, "DELETE FROM macro_data WITH (TABLOCK)")
    today = datetime.now().strftime('%Y-%m-%d')
    regimes = ["risk-on", "risk-off", "neutral", "bullish", "bearish"]
    run(cursor, """
        INSERT INTO macro_data (date, vix, dxy, us10y, sp500, nasdaq, regime)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (today, round(random.uniform(14, 28), 2), round(random.uniform(100, 108), 2),
          round(random.uniform(3.8, 4.8), 2), round(random.uniform(5500, 6100), 2),
          round(random.uniform(17500, 19500), 2), random.choice(regimes)))
    print("[OK] macro_data: 1 makro kaydi eklendi")

def seed_pipeline(cursor):
    today = datetime.now().strftime('%Y-%m-%d')
    run(cursor, "DELETE FROM pipeline_status WHERE date = ?", (today,))
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
        ("Final Decision", "done", "10:10")
    ]
    for s in steps:
        run(cursor, "INSERT INTO pipeline_status (date, step_name, status, time) VALUES (?, ?, ?, ?)",
                      (today, s[0], s[1], s[2]))
    print("[OK] pipeline_status: 10 adim eklendi")

def seed_fund_holdings(cursor):
    run(cursor, "DELETE FROM fund_holdings WHERE quarter = '2026Q2'")
    funds = ["Buffett", "Soros", "Druckenmiller", "Tepper", "Ackman", "Tiger Global", "Coatue", "Bridgewater", "ARK", "Viking"]
    symbols = ["NVDA", "PLTR", "MSFT", "AAPL", "TSLA", "AMD", "META", "AMZN", "GOOGL", "AVGO"]
    
    count = 0
    for fund in funds:
        picks = random.sample(symbols, random.randint(3, 7))
        for sym in picks:
            weight = round(random.uniform(1.5, 8.5), 2)
            change = round(random.uniform(-15, 25), 2)
            run(cursor, """
                INSERT INTO fund_holdings (fund_name, symbol, weight, change_qoq, quarter)
                VALUES (?, ?, ?, ?, '2026Q2')
            """, (fund, sym, weight, change))
            count += 1
    print("[OK] fund_holdings: {} fon, toplam {} pozisyon eklendi".format(len(funds), count))

def seed_predictions(cursor):
    run(cursor, "DELETE FROM predictions WITH (TABLOCK)")

    symbols = ["NVDA", "PLTR", "MSFT", "AAPL", "TSLA"]

    # Post-Mortem icin baslangic hata dagilimi
    initial_errors = {
        "M1": 5,   # Makro hatasi
        "H1": 3,   # Haber hatasi
        "S1": 2,   # Sektor hatasi
        "T1": 10,  # Teknik hatasi
        "R1": 8,   # Rejim hatasi
        "B1": 3,   # Band hatasi
        "C1": 7    # Cross-Asset hatasi
    }

    # Hata kodlarinin toplami 38, kalan 12 kayit hatasiz olacak.
    seeded_count = 0

    for error_code, count in initial_errors.items():
        for _ in range(count):
            sym = random.choice(symbols)
            date = (datetime.now() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d")
            signal = random.choice(["AL", "SAT", "BEKLE"])
            pred_return = round(random.uniform(-5, 15), 2)
            actual = round(pred_return + random.uniform(-8, 8), 2)
            target_hit = 1 if actual >= pred_return * 0.8 else 0
            stop_hit = 1 if actual < -5 else 0

            run(cursor, """
                INSERT INTO predictions
                (symbol, date, prediction_signal, predicted_return, actual_return,
                 target_hit, stop_hit, error_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (sym, date, signal, pred_return, actual,
                  target_hit, stop_hit, error_code))
            seeded_count += 1

    # Toplam 50 tahmini tamamlamak icin 12 hatasiz kayit ekle.
    for _ in range(50 - seeded_count):
        sym = random.choice(symbols)
        date = (datetime.now() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d")
        signal = random.choice(["AL", "SAT", "BEKLE"])
        pred_return = round(random.uniform(-5, 15), 2)
        actual = round(pred_return + random.uniform(-8, 8), 2)
        target_hit = 1 if actual >= pred_return * 0.8 else 0
        stop_hit = 1 if actual < -5 else 0

        run(cursor, """
            INSERT INTO predictions
            (symbol, date, prediction_signal, predicted_return, actual_return,
             target_hit, stop_hit, error_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
        """, (sym, date, signal, pred_return, actual,
              target_hit, stop_hit))
        seeded_count += 1

    print("[OK] predictions: {} tahmin eklendi (Post-Mortem hata dagilimi dahil)".format(seeded_count))

def seed_memory_logs(cursor):
    run(cursor, "DELETE FROM memory_logs WITH (TABLOCK)")
    logs = [
        ("companies", "NVDA Profili", "NVIDIA, AI devriminin merkezinde. Data center gelirleri yuzde 400 artti.", "AI,GPU,DataCenter"),
        ("mistakes", "TSLA Hatasi", "Makro rejim degisikligini gormezden geldik. VIX 25+ iken AL sinyali urettik.", "M1,T1"),
        ("patterns", "Earnings Gap", "EPS beklentisini yuzde 20 asan hisseler 3 gun icinde yuzde 8 ortalama geri cekilme yapiyor.", "Earnings,Volatility"),
        ("macro", "FED Pivot", "25bps indirim sonrasi 30 gun icinde tech sektoru ortalama yuzde 12 yukseliyor.", "FED,InterestRate"),
        ("thesis", "AI Altyapisi", "GPU -> HBM -> TSMC -> ASML zinciri 2026'da yuzde 35 buyume bekleniyor.", "AI,Semiconductor"),
    ]
    for log in logs:
        run(cursor, """
            INSERT INTO memory_logs (category, title, content, tags, created_at)
            VALUES (?, ?, ?, ?, GETDATE())
        """, log)
    print("[OK] memory_logs: {} kayit eklendi".format(len(logs)))

def main():
    print("=" * 60)
    print("ARFEZ AI - Ornek Veri Doldurucu")
    print("=" * 60)
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        seed_stocks(cursor)
        seed_daily_scores(cursor)
        seed_macro(cursor)
        seed_pipeline(cursor)
        seed_fund_holdings(cursor)
        seed_predictions(cursor)
        seed_memory_logs(cursor)
        conn.commit()
        print("=" * 60)
        print("TUM TABLOLAR BASARIYLA DOLDURULDU!")
        print("Simdi http://127.0.0.1:5000 adresine git.")
        print("=" * 60)
    except Exception as e:
        print("[HATA] {}".format(e))
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    main()
