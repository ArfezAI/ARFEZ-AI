"""
ARFEZ AI v3.0 - Canli Veri Toplayici (pandas_ta'siz)
=====================================================
Python 3.14 uyumlu. Teknik indikatörler manuel hesaplanir.
"""
import pyodbc
import yfinance as yf
import pandas as pd
import numpy as np
import argparse
from datetime import datetime, timedelta
import time

# ============================================================
# MSSQL BAGLANTI
# ============================================================
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

def ensure_period_column(conn):
    """predictions tablosunda 'period' sutunu yoksa ekler (veri kaybi olmadan)"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'predictions' AND COLUMN_NAME = 'period'
    """)
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute("""
            ALTER TABLE predictions
            ADD period VARCHAR(10) NOT NULL DEFAULT 'daily'
        """)
        conn.commit()
        print("[SCHEMA] predictions tablosuna 'period' sutunu eklendi")
    cursor.close()

# ============================================================
# HISSE EVRENI
# ============================================================
UNIVERSE = [
    "ABT",
    "AKR",
    "AAMI",
    "ACMR",
    "ADEA",
    "ADBE",
    "AMD",
    "AKTS",
    "ALMR",
    "ALLY",
    "GOOGL",
    "AMZN",
    "AMTM",
    "AS",
    "AEP",
    "AHR",
    "AIG",
    "ANDG",
    "APGE",
    "APO",
    "AAPL",
    "AADX",
    "ADM",
    "ACA",
    "ARES",
    "ATI",
    "TEAM",
    "AVLN",
    "BKU",
    "BRK-B",
    "BGC",
    "BILL",
    "TECH",
    "BX",
    "OBDC",
    "OWL",
    "BOTZ",
    "BWA",
    "BHF",
    "AVGO",
    "BG",
    "CZR",
    "CCJ",
    "CEPV",
    "COF",
    "CTRE",
    "CG",
    "CRS",
    "CPRX",
    "CX",
    "CBRS",
    "GTLS",
    "CB",
    "CFG",
    "NET",
    "CME",
    "CMS",
    "KO",
    "CEG",
    "CNM",
    "CORZ",
    "CRBG",
    "CRWV",
    "CPNG",
    "CRH",
    "DDOG",
    "DLR",
    "DBRG",
    "DIS",
    "D",
    "DASH",
    "DPC",
    "ENRD",
    "EA",
    "LLY",
    "EME",
    "ETR",
    "EROC",
    "ESPR",
    "ETSY",
    "ES",
    "EVGO",
    "FVR",
    "FIGR",
    "FSLR",
    "FE",
    "FBC",
    "FPS",
    "FCX",
    "GLXY",
    "GFL",
    "GBTG",
    "SJW",
    "Hawk",
    "COAG",
    "HTZ",
    "HONA",
    "HON",
    "HUBG",
    "HUM",
    "HUN",
    "IDA",
    "PI",
    "INGM",
    "INNO",
    "INTC",
    "IBKR",
    "EMXC",
    "MUB",
    "ITRI",
    "ITT",
    "J",
    "JAN",
    "JNJ",
    "JPM",
    "KLRA",
    "KARD",
    "KEEL",
    "KVUE",
    "KRG",
    "KKR",
    "KDK",
    "KWEB",
    "LGN",
    "LIFT",
    "LINC",
    "LIN",
    "LCID",
    "MAC",
    "MASI",
    "MRVL",
    "MTZ",
    "MA",
    "MTRN",
    "MCD",
    "MDLN",
    "META",
    "MCB",
    "MGEE",
    "MGM",
    "MCHP",
    "MU",
    "MSFT",
    "MFIC",
    "MIDD",
    "MS",
    "NATL",
    "NBIS",
    "NPI",
    "NFLX",
    "NOC",
    "NUVL",
    "NVDA",
    "ON",
    "PZZA",
    "PAYO",
    "PM",
    "PNFP",
    "PONY",
    "POR",
    "PPL",
    "PRIM",
    "PGR",
    "PEG",
    "QNTM",
    "QXO",
    "RDNT",
    "USAR",
    "RBC",
    "RDDT",
    "ROKU",
    "RUSHA",
    "RSI",
    "SPGI",
    "XLF",
    "SRE",
    "NOW",
    "SNAI",
    "SILA",
    "SITM",
    "SW",
    "SNOW",
    "SOLV",
    "SGI",
    "SFST",
    "SPSB",
    "SARO",
    "SPY",
    "STLA",
    "STM",
    "SUNB",
    "RUN",
    "SMCI",
    "TE",
    "TSM",
    "TLN",
    "TALK",
    "TMHC",
    "TNC",
    "TEX",
    "TSLA",
    "TXN",
    "TKR",
    "TKO",
    "BLD",
    "TPG",
    "UBER",
    "ULS",
    "UNH",
    "VRNS",
    "VRSK",
    "VZ",
    "VSGN",
    "VSH",
    "VST",
    "VSEC",
    "WMT",
    "WBD",
    "WBS",
    "WEC",
    "WIX",
    "WWD",
    "XEL",
    "XE",
    "YSWY",
    "YSS",
    "ZETA",
    "ZTS",
]

# ============================================================
# MANUEL TEKNIK INDIKATORLER (pandas_ta'siz)
# ============================================================
def calc_rsi(series, period=14):
    """Wilder RSI"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calc_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def calc_macd(series, fast=12, slow=26, signal=9):
    ema_fast = calc_ema(series, fast)
    ema_slow = calc_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calc_ema(macd_line, signal)
    return macd_line, signal_line

def calc_bollinger(series, period=20, std_dev=2):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, sma, lower

def calc_atr(df, period=14):
    """Average True Range"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def calc_relative_volume(df, period=20):
    """Relative Volume (RVOL): son hacim / ortalama hacim."""
    if df is None or len(df) < period:
        return pd.Series([1.0] * (len(df) if df is not None else 0),
                         index=df.index if df is not None else None)

    volume = pd.to_numeric(df['Volume'], errors='coerce')
    avg_volume = volume.rolling(window=period).mean()
    rvol = volume / avg_volume
    return rvol.replace([np.inf, -np.inf], np.nan).fillna(1.0)


def calc_adx(df, period=14):
    """Average Directional Index (basitlestirilmis)"""
    high = df['High']
    low = df['Low']
    close = df['Close']

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()

    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(window=period).mean()
    return adx

# ============================================================
# TEK SATIR ICIN INDIKATOR HESAPLAMA
# (harici veri toplama akislarinda tek bir row_data'ya indikator eklemek icin)
# ============================================================
def add_technical_indicators_to_row(row_data):
    """
    Veri satirina teknik indikator ekler (RSI, MACD, Bollinger Bands).
    row_data: dict, 'close_history' anahtari altinda kapanis fiyatlari listesini icermeli.
    Guncellenmis row_data dict'ini geri doner.

    Not: Mevcut calc_rsi / calc_macd / calc_bollinger fonksiyonlarini kullanir,
    boylece hesaplama mantigi calculate_technical_score ile birebir tutarlidir.
    """
    closes = row_data.get('close_history', [])
    volumes = row_data.get('volume_history', [])

    if not closes or len(closes) < 14:
        row_data['rsi'] = 50
        row_data['macd'] = 0
        row_data['macd_signal'] = 0
        row_data['macd_histogram'] = 0
        row_data['bb_middle'] = 0
        row_data['bb_upper'] = 0
        row_data['bb_lower'] = 0
        row_data['rvol'] = 1.0
        return row_data

    close_series = pd.Series(closes, dtype=float)

    # --- RSI ---
    rsi_series = calc_rsi(close_series, 14)
    rsi_val = rsi_series.iloc[-1]
    row_data['rsi'] = round(float(rsi_val), 2) if not pd.isna(rsi_val) else 50

    # --- MACD (line, signal, histogram) ---
    macd_line, signal_line = calc_macd(close_series)
    macd_val = macd_line.iloc[-1]
    signal_val = signal_line.iloc[-1]
    if pd.isna(macd_val) or pd.isna(signal_val):
        macd_val, signal_val, hist_val = 0, 0, 0
    else:
        hist_val = macd_val - signal_val
    row_data['macd'] = round(float(macd_val), 4)
    row_data['macd_signal'] = round(float(signal_val), 4)
    row_data['macd_histogram'] = round(float(hist_val), 4)

    # --- Bollinger Bands (yeterli veri yoksa 20 periyot yerine NaN gelebilir) ---
    bb_upper, bb_mid, bb_lower = calc_bollinger(close_series, 20)
    mb, ub, lb = bb_mid.iloc[-1], bb_upper.iloc[-1], bb_lower.iloc[-1]
    row_data['bb_middle'] = round(float(mb), 2) if not pd.isna(mb) else 0
    row_data['bb_upper'] = round(float(ub), 2) if not pd.isna(ub) else 0
    row_data['bb_lower'] = round(float(lb), 2) if not pd.isna(lb) else 0

    # --- RVOL (Relative Volume) ---
    # row_data içinde volume_history varsa hesaplanır.
    # Hacim verisi yoksa nötr değer olan 1.0 kullanılır.
    if volumes:
        volume_df = pd.DataFrame({'Volume': pd.to_numeric(volumes, errors='coerce')})
        rvol_series = calc_relative_volume(volume_df, 20)
        rvol_val = rvol_series.iloc[-1]
        row_data['rvol'] = round(float(rvol_val), 2) if not pd.isna(rvol_val) else 1.0
    else:
        row_data['rvol'] = 1.0

    return row_data

# ============================================================
# TEKNIK SKOR HESAPLAMA
# ============================================================
def calculate_technical_score(df):
    if df is None or len(df) < 50:
        return 50, {}

    df = df.copy()
    df['rsi'] = calc_rsi(df['Close'], 14)
    df['macd'], df['macd_signal'] = calc_macd(df['Close'])
    df['bb_upper'], df['bb_mid'], df['bb_lower'] = calc_bollinger(df['Close'])
    df['ema20'] = calc_ema(df['Close'], 20)
    df['ema50'] = calc_ema(df['Close'], 50)
    df['adx'] = calc_adx(df)
    df['rvol'] = calc_relative_volume(df, 20)

    latest = df.iloc[-1]

    # RSI skoru
    rsi = latest.get('rsi', 50)
    if pd.isna(rsi): rsi = 50
    rsi_score = 100 - abs(rsi - 50) * 2
    if rsi > 70: rsi_score = 70
    if rsi < 30: rsi_score = 30

    # MACD skoru
    macd_val = latest.get('macd', 0)
    macd_sig = latest.get('macd_signal', 0)
    macd_score = 70 if macd_val > macd_sig else 40

    # Bollinger skoru
    bb_mid = latest.get('bb_mid', latest['Close'])
    bb_upper = latest.get('bb_upper', latest['Close'] * 1.05)
    bb_lower = latest.get('bb_lower', latest['Close'] * 0.95)
    if bb_upper != bb_lower:
        bb_pos = (latest['Close'] - bb_lower) / (bb_upper - bb_lower)
        bb_score = 100 - abs(bb_pos - 0.5) * 100
    else:
        bb_score = 50

    # Trend skoru
    ema20 = latest.get('ema20', 0)
    ema50 = latest.get('ema50', 0)
    trend_score = 80 if ema20 > ema50 else 40

    # ADX skoru
    adx_val = latest.get('adx', 0)
    adx_score = 80 if adx_val > 25 else 60 if adx_val > 20 else 40

    technical = int(rsi_score * 0.25 + macd_score * 0.20 + bb_score * 0.20 + trend_score * 0.20 + adx_score * 0.15)
    technical = max(0, min(100, technical))

    details = {
        'rsi': round(float(rsi), 1) if not pd.isna(rsi) else 50,
        'macd': round(float(macd_val), 2) if not pd.isna(macd_val) else 0,
        'adx': round(float(adx_val), 1) if not pd.isna(adx_val) else 0,
        'ema20': round(float(ema20), 2) if not pd.isna(ema20) else 0,
        'ema50': round(float(ema50), 2) if not pd.isna(ema50) else 0,
        'rvol': round(float(latest.get('rvol', 1.0)), 2) if not pd.isna(latest.get('rvol', 1.0)) else 1.0,
        'bb_upper': round(float(bb_upper), 2) if not pd.isna(bb_upper) else 0,
        'bb_lower': round(float(bb_lower), 2) if not pd.isna(bb_lower) else 0
    }
    return technical, details

# ============================================================
# FUNDAMENTAL SKOR
# ============================================================
def calculate_fundamental_score(info):
    score = 50
    pe = info.get('trailingPE') or info.get('forwardPE') or 20
    if pe < 15: pe_score = 80
    elif pe < 25: pe_score = 70
    elif pe < 40: pe_score = 50
    else: pe_score = 30

    eps_growth = info.get('earningsGrowth') or 0
    if eps_growth > 0.30: eps_score = 90
    elif eps_growth > 0.15: eps_score = 75
    elif eps_growth > 0.05: eps_score = 60
    else: eps_score = 40

    rev_growth = info.get('revenueGrowth') or 0
    if rev_growth > 0.25: rev_score = 85
    elif rev_growth > 0.15: rev_score = 70
    elif rev_growth > 0.05: rev_score = 55
    else: rev_score = 40

    margin = info.get('profitMargins') or 0
    if margin > 0.25: margin_score = 85
    elif margin > 0.15: margin_score = 70
    elif margin > 0.05: margin_score = 55
    else: margin_score = 35

    fundamental = int(pe_score * 0.25 + eps_score * 0.30 + rev_score * 0.25 + margin_score * 0.20)
    return max(0, min(100, fundamental))

# ============================================================
# RISK SKORU
# ============================================================
def calculate_risk_score(df, info):
    if df is None or len(df) < 20:
        return 50
    atr = calc_atr(df, 14)
    latest_atr = atr.iloc[-1] if atr is not None else 0
    price = df['Close'].iloc[-1]
    vol_pct = (latest_atr / price) * 100 if price > 0 else 5

    beta = info.get('beta') or 1.0
    recent_high = df['Close'].max()
    recent_low = df['Close'].min()
    drawdown = ((recent_high - recent_low) / recent_high) * 100 if recent_high > 0 else 0

    vol_score = 100 - min(vol_pct * 5, 100)
    beta_score = 100 - abs(beta - 1) * 30
    dd_score = 100 - min(drawdown * 2, 100)

    risk = int(vol_score * 0.40 + beta_score * 0.30 + dd_score * 0.30)
    return max(0, min(100, risk))

# ============================================================
# MAKRO ETKISI
# ============================================================
def get_macro_effect(cursor):
    cursor.execute("SELECT TOP 1 vix, dxy, regime FROM macro_data ORDER BY date DESC")
    row = cursor.fetchone()
    if not row:
        return 50, "neutral"
    vix, dxy, regime = row
    if regime == "risk-on": return 75, "risk-on"
    elif regime == "risk-off": return 35, "risk-off"
    elif vix > 25: return 40, "high-volatility"
    elif dxy > 105: return 45, "strong-dollar"
    else: return 60, "neutral"

# ============================================================
# TAHMIN HATA ANALIZI / POST-MORTEM
# ============================================================
def analyze_prediction_error(signal, predicted_return, actual_return):
    """
    Tahmin hatasını analiz eder ve hata kodunu belirler.
    """
    diff = abs(predicted_return - actual_return)

    if signal == 'AL' and actual_return < -3:
        return 'T1'  # Teknik
    elif signal == 'SAT' and actual_return > 3:
        return 'S1'  # Sektor
    elif signal == 'BEKLE' and abs(actual_return) > 2:
        return 'B1'  # Bant
    elif diff > 5:
        return 'C1'  # Cross-Asset
    elif actual_return < 0:
        return 'R1'  # Rejim
    else:
        return 'A1'  # Basarili


# ============================================================
# TEK HISSE ISLE
# ============================================================
def process_symbol(symbol, cursor, macro_effect, regime, period='daily'):
    try:
        print(f"  [{symbol}] Veri cekiliyor...", end=" ")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="3mo")
        if df.empty or len(df) < 30:
            print("YETERSIZ VERI")
            return None

        info = ticker.info
        technical, tech_details = calculate_technical_score(df)
        fundamental = calculate_fundamental_score(info)
        risk = calculate_risk_score(df, info)

        new_world = min(100, int((technical * 0.4 + fundamental * 0.4 + risk * 0.2) * 1.1))
        confidence = int(50 + (technical + fundamental) / 4)
        valuation = fundamental
        capital_flow = technical
        theme = new_world

        final = int(
            technical * 0.20 + fundamental * 0.20 + risk * 0.15 +
            new_world * 0.15 + macro_effect * 0.10 + confidence * 0.10 +
            valuation * 0.05 + capital_flow * 0.05
        )
        final = max(0, min(100, final))

        signal = 'AL' if final >= 80 and risk >= 50 else 'SAT' if final < 45 or risk < 30 else 'BEKLE'

        latest = df.iloc[-1]
        atr = calc_atr(df, 14)
        latest_atr = atr.iloc[-1] if atr is not None else latest['Close'] * 0.02

        if signal == 'AL':
            target = round(latest['Close'] + latest_atr * 3, 2)
            stop = round(latest['Close'] - latest_atr * 2, 2)
        elif signal == 'SAT':
            target = round(latest['Close'] - latest_atr * 3, 2)
            stop = round(latest['Close'] + latest_atr * 2, 2)
        else:
            target = round(latest['Close'] + latest_atr * 2, 2)
            stop = round(latest['Close'] - latest_atr * 1.5, 2)

        expected = round(((target - latest['Close']) / latest['Close']) * 100, 1) if latest['Close'] > 0 else 0

        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            MERGE daily_scores AS target
            USING (VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)) AS source 
            (symbol, date, arfez_score, new_world, technical, fundamental, risk, confidence,
             macro, valuation, capital_flow, theme, final_score, signal, target_price, stop_loss, expected_return)
            ON target.symbol = source.symbol AND target.date = source.date
            WHEN MATCHED THEN UPDATE SET
                arfez_score=source.arfez_score, new_world=source.new_world, technical=source.technical,
                fundamental=source.fundamental, risk=source.risk, confidence=source.confidence,
                macro=source.macro, valuation=source.valuation, capital_flow=source.capital_flow,
                theme=source.theme, final_score=source.final_score, signal=source.signal,
                target_price=source.target_price, stop_loss=source.stop_loss, expected_return=source.expected_return
            WHEN NOT MATCHED THEN INSERT
                (symbol, date, arfez_score, new_world, technical, fundamental, risk, confidence,
                 macro, valuation, capital_flow, theme, final_score, signal, target_price, stop_loss, expected_return)
            VALUES (source.symbol, source.date, source.arfez_score, source.new_world, source.technical,
                    source.fundamental, source.risk, source.confidence, source.macro, source.valuation,
                    source.capital_flow, source.theme, source.final_score, source.signal,
                    source.target_price, source.stop_loss, source.expected_return);
        """, (symbol, today, final, new_world, technical, fundamental, risk, confidence,
              macro_effect, valuation, capital_flow, theme, final, signal, target, stop, expected))

        sector = info.get('sector', 'Unknown') or 'Unknown'
        name = info.get('longName') or info.get('shortName') or symbol
        cursor.execute("""
            MERGE stocks AS target
            USING (VALUES (?, ?, ?)) AS source (symbol, name, sector)
            ON target.symbol = source.symbol
            WHEN MATCHED THEN UPDATE SET name=source.name, sector=source.sector
            WHEN NOT MATCHED THEN INSERT (symbol, name, sector) VALUES (source.symbol, source.name, source.sector);
        """, (symbol, name[:100], sector[:50]))

        # ------------------------------------------------------------
        # PREDICTIONS: tahmini getiri + gerceklesen (haftalik) getiri
        # ------------------------------------------------------------
        predicted_return = final * 0.01

        # Haftalık gerçek getiri hesapla (son 7 günlük fiyat değişimi)
        week_ago_data = ticker.history(period="2mo")  # 2 ay veri al
        if len(week_ago_data) >= 8:
            price_now = latest['Close']
            price_week_ago = week_ago_data.iloc[-8]['Close']  # 7 gün öncesi
            weekly_return = round(((price_now - price_week_ago) / price_week_ago) * 100, 2)
        else:
            weekly_return = 0.0

        error_code = analyze_prediction_error(signal, predicted_return, weekly_return)

        cursor.execute("""
            MERGE predictions AS target
            USING (VALUES (?, ?, ?, ?, ?, ?, ?)) AS source
                (symbol, date, period, prediction_signal, predicted_return,
                 actual_return, error_code)
            ON target.symbol = source.symbol
               AND target.date = source.date
               AND target.period = source.period
            WHEN MATCHED THEN
                UPDATE SET
                    prediction_signal = source.prediction_signal,
                    predicted_return = source.predicted_return,
                    actual_return = source.actual_return,
                    error_code = source.error_code,
                    updated_at = GETDATE()
            WHEN NOT MATCHED THEN
                INSERT (symbol, date, period, prediction_signal, predicted_return,
                        actual_return, error_code)
                VALUES (source.symbol, source.date, source.period, source.prediction_signal,
                        source.predicted_return, source.actual_return, source.error_code);
        """, (symbol, today, period, signal, predicted_return, weekly_return, error_code))

        print(f"OK | Final:{final} | Signal:{signal} | Price:${round(latest['Close'],2)} | ActualRet(7g):{weekly_return}% | Err:{error_code}")
        return {
            'symbol': symbol, 'final': final, 'signal': signal,
            'technical': technical, 'fundamental': fundamental, 'risk': risk,
            'price': round(latest['Close'], 2)
        }
    except Exception as e:
        print(f"HATA: {e}")
        return None

# ============================================================
# MAKRO VERILERI
# ============================================================
def update_macro(cursor):
    print("\n[Makro Verileri Cekiliyor...]")
    try:
        vix_ticker = yf.Ticker("^VIX")
        vix_hist = vix_ticker.history(period="5d")
        vix = round(vix_hist['Close'].iloc[-1], 2) if not vix_hist.empty else 18.0

        dxy_ticker = yf.Ticker("UUP")
        dxy_hist = dxy_ticker.history(period="5d")
        dxy = round(dxy_hist['Close'].iloc[-1], 2) if not dxy_hist.empty else 103.0

        tnx = yf.Ticker("^TNX")
        tnx_hist = tnx.history(period="5d")
        us10y = round(tnx_hist['Close'].iloc[-1], 2) if not tnx_hist.empty else 4.2

        spx = yf.Ticker("^GSPC")
        spx_hist = spx.history(period="5d")
        sp500 = round(spx_hist['Close'].iloc[-1], 2) if not spx_hist.empty else 5800.0

        ndx = yf.Ticker("^IXIC")
        ndx_hist = ndx.history(period="5d")
        nasdaq = round(ndx_hist['Close'].iloc[-1], 2) if not ndx_hist.empty else 18500.0

        if vix < 18 and dxy < 104: regime = "risk-on"
        elif vix > 25 or dxy > 106: regime = "risk-off"
        elif vix > 20: regime = "neutral"
        else: regime = "bullish"

        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            MERGE macro_data AS target
            USING (VALUES (?, ?, ?, ?, ?, ?, ?)) AS source (date, vix, dxy, us10y, sp500, nasdaq, regime)
            ON target.date = source.date
            WHEN MATCHED THEN UPDATE SET vix=source.vix, dxy=source.dxy, us10y=source.us10y,
                sp500=source.sp500, nasdaq=source.nasdaq, regime=source.regime
            WHEN NOT MATCHED THEN INSERT (date, vix, dxy, us10y, sp500, nasdaq, regime)
            VALUES (source.date, source.vix, source.dxy, source.us10y, source.sp500, source.nasdaq, source.regime);
        """, (today, vix, dxy, us10y, sp500, nasdaq, regime))

        print(f"  VIX:{vix} | DXY:{dxy} | US10Y:{us10y}% | S&P500:{sp500} | Regime:{regime}")
        return True
    except Exception as e:
        print(f"  [HATA] Makro veri cekilemedi: {e}")
        return False

# ============================================================
# ANA MOTOR
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='ARFEZ AI Canli Veri Toplayici')
    parser.add_argument('--symbol', type=str, help='Tek hisse sembolu')
    parser.add_argument('--macro', action='store_true', help='Sadece makro verileri guncelle')
    parser.add_argument('--limit', type=int, default=0, help='Islenecek hisse sayisi (0=tum evren)')
    parser.add_argument('--period', type=str, default='daily', choices=['daily', 'weekly'],
                         help="Tahmin donemi: 'daily' veya 'weekly' (varsayilan: daily)")
    args = parser.parse_args()

    print("=" * 70)
    print("ARFEZ AI v3.0 - Canli Veri Toplayici (Python 3.14 Uyumlu)")
    print("=" * 70)
    print(f"Baslangic: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    conn = get_db()
    cursor = conn.cursor()

    try:
        ensure_period_column(conn)

        if args.macro or not args.symbol:
            update_macro(cursor)
            conn.commit()

        if args.macro:
            print("\n[Makro guncelleme tamamlandi]")
            return

        macro_effect, regime = get_macro_effect(cursor)
        print(f"\n[Makro Etkisi: {regime.upper()} | Skor: {macro_effect}]")

        symbols = [args.symbol.upper()] if args.symbol else UNIVERSE
        if args.limit > 0 and not args.symbol:
            symbols = symbols[:args.limit]

        print(f"\n[Islenecek Hisse Sayisi: {len(symbols)}] [Period: {args.period}]")
        print("-" * 70)

        results = []
        for i, sym in enumerate(symbols, 1):
            result = process_symbol(sym, cursor, macro_effect, regime, period=args.period)
            if result:
                results.append(result)
            time.sleep(0.5)

        conn.commit()

        print("\n" + "=" * 70)
        print("OZET")
        print("=" * 70)
        al_count = sum(1 for r in results if r['signal'] == 'AL')
        sat_count = sum(1 for r in results if r['signal'] == 'SAT')
        bekle_count = sum(1 for r in results if r['signal'] == 'BEKLE')
        print(f"Toplam Islenen: {len(results)}")
        print(f"  AL Sinyali  : {al_count}")
        print(f"  SAT Sinyali : {sat_count}")
        print(f"  BEKLE       : {bekle_count}")
        if results:
            top_pick = max(results, key=lambda x: x['final'])
            print(f"\nEn Yuksek Skor: {top_pick['symbol']} ({top_pick['final']})")
        print(f"\nBitis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

    except Exception as e:
        print(f"\n[Kritik Hata]: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    main()
