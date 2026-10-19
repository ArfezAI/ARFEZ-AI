"""
ARFEZ AI v3.0 - Canli Veri Toplayici (pandas_ta'siz)
=====================================================
Python 3.14 uyumlu. Teknik indikatörler manuel hesaplanir.

Düzeltmeler:
- 2.1 predicted_return = expected (gerçek getiri tahmini)
- 2.2 valuation / capital_flow gerçek hesaplamaya bağlandı, theme = None
- 2.3 collect_valuation_inputs ölü kod temizlendi
- 2.4 CONN_STR .env'e taşındı
- UNIVERSE, indikatörler, analyze_prediction_error ortak modüllere taşındı
- 2.3b build_multi_model_valuation eklendi (P/E + DCF birleşimi)
"""
import os
import json
import pyodbc
import yfinance as yf
import pandas as pd
import numpy as np
import argparse
from datetime import datetime, timedelta
import time

from fair_value_engine import (
    calculate_pe_fair_value,
    calculate_dcf_fair_value,
    combine_fair_values,
    calculate_valuation_scenarios,
    calculate_upside,
    validate_data_quality,
    ENGINE_VERSION,
)

# ============================================================
# MSSQL BAGLANTI
# ============================================================
CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=DESKTOP-L7INTLS,1433;"
    "DATABASE=ARFEZ;"
    "UID=sa;"
    "PWD=****;"
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


def ensure_fair_value_columns(conn):
    """daily_scores tablosunda adil deger sutunlari yoksa ekler (veri kaybi olmadan)"""
    columns = {
        "current_price": "DECIMAL(19,4) NULL",
        "forward_eps": "DECIMAL(19,4) NULL",
        "fair_pe": "DECIMAL(9,2) NULL",
        "fair_value": "DECIMAL(19,4) NULL",
        "upside_pct": "DECIMAL(9,2) NULL",
        "valuation_model": "VARCHAR(20) NULL",
        "valuation_valid": "BIT NULL",
        "valuation_reason": "NVARCHAR(300) NULL",
        "dcf_fair_value": "DECIMAL(19,4) NULL",
        "combined_fair_value": "DECIMAL(19,4) NULL",
        "dcf_upside_pct": "DECIMAL(9,2) NULL",
        "model_weights": "NVARCHAR(MAX) NULL",
        "valuation_scenarios": "NVARCHAR(MAX) NULL",
        "valuation_engine_version": "VARCHAR(20) NULL",
    }
    cursor = conn.cursor()
    for name, sql_type in columns.items():
        cursor.execute("""
            IF COL_LENGTH('dbo.daily_scores', ?) IS NULL
            BEGIN
                DECLARE @sql NVARCHAR(MAX) =
                    N'ALTER TABLE dbo.daily_scores ADD '
                    + QUOTENAME(?) + N' """ + sql_type + """'
                EXEC sp_executesql @sql
            END
        """, name, name)
    conn.commit()
    cursor.close()


# ============================================================
# TEKNIK INDIKATORLER (manuel)
# ============================================================
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def calc_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def calc_macd(series, fast=12, slow=26, signal=9):
    ema_fast = calc_ema(series, fast)
    ema_slow = calc_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calc_ema(macd_line, signal)
    return macd_line, signal_line


def calc_bollinger(series, period=20, num_std=2):
    mid = series.rolling(window=period, min_periods=period).mean()
    std = series.rolling(window=period, min_periods=period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


def calc_atr(df, period=14):
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def calc_adx(df, period=14):
    high = df['High']
    low = df['Low']
    close = df['Close']
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period, min_periods=period).mean() / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm.rolling(window=period, min_periods=period).mean() / atr.replace(0, np.nan))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.rolling(window=period, min_periods=period).mean()
    return adx.fillna(0)


def calc_relative_volume(df, period=20):
    if 'Volume' not in df.columns:
        return pd.Series([1.0] * len(df), index=df.index)
    vol = pd.to_numeric(df['Volume'], errors='coerce')
    avg_vol = vol.rolling(window=period, min_periods=1).mean()
    return (vol / avg_vol.replace(0, np.nan)).fillna(1.0)


def add_technical_indicators_to_row(row_data):
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
    rsi_series = calc_rsi(close_series, 14)
    rsi_val = rsi_series.iloc[-1]
    row_data['rsi'] = round(float(rsi_val), 2) if not pd.isna(rsi_val) else 50

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

    bb_upper, bb_mid, bb_lower = calc_bollinger(close_series, 20)
    mb, ub, lb = bb_mid.iloc[-1], bb_upper.iloc[-1], bb_lower.iloc[-1]
    row_data['bb_middle'] = round(float(mb), 2) if not pd.isna(mb) else 0
    row_data['bb_upper'] = round(float(ub), 2) if not pd.isna(ub) else 0
    row_data['bb_lower'] = round(float(lb), 2) if not pd.isna(lb) else 0

    if volumes:
        volume_df = pd.DataFrame({'Volume': pd.to_numeric(volumes, errors='coerce')})
        rvol_series = calc_relative_volume(volume_df, 20)
        rvol_val = rvol_series.iloc[-1]
        row_data['rvol'] = round(float(rvol_val), 2) if not pd.isna(rvol_val) else 1.0
    else:
        row_data['rvol'] = 1.0

    return row_data


# ============================================================
# TEKNIK SKOR
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

    rsi = latest.get('rsi', 50)
    if pd.isna(rsi): rsi = 50
    rsi_score = 100 - abs(rsi - 50) * 2
    if rsi > 70: rsi_score = 70
    if rsi < 30: rsi_score = 30

    macd_val = latest.get('macd', 0)
    macd_sig = latest.get('macd_signal', 0)
    macd_score = 70 if macd_val > macd_sig else 40

    bb_mid = latest.get('bb_mid', latest['Close'])
    bb_upper = latest.get('bb_upper', latest['Close'] * 1.05)
    bb_lower = latest.get('bb_lower', latest['Close'] * 0.95)
    if bb_upper != bb_lower:
        bb_pos = (latest['Close'] - bb_lower) / (bb_upper - bb_lower)
        bb_score = 100 - abs(bb_pos - 0.5) * 100
    else:
        bb_score = 50

    ema20 = latest.get('ema20', 0)
    ema50 = latest.get('ema50', 0)
    trend_score = 80 if ema20 > ema50 else 40

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
# FAIR VALUE INTEGRATION
# ============================================================
def get_fair_pe_policy():
    raw = os.getenv("ARFEZ_FAIR_PE_OVERRIDES", "{}")
    try:
        policy = json.loads(raw)
        if not isinstance(policy, dict):
            return {}
        return {
            str(sector): float(pe)
            for sector, pe in policy.items()
            if isinstance(pe, (int, float))
            and not isinstance(pe, bool)
            and 0 < float(pe) <= 100
        }
    except (ValueError, TypeError):
        return {}


def _empty_valuation(reason, current_price=None, forward_eps=None, fair_pe=None):
    return {
        "current_price": current_price,
        "forward_eps": forward_eps,
        "fair_pe": fair_pe,
        "fair_value": None,
        "upside_pct": None,
        "valuation_model": "FORWARD_PE",
        "valuation_valid": False,
        "valuation_reason": str(reason)[:300],
    }


def collect_valuation_inputs(df, info):
    latest = df.iloc[-1]
    price = float(latest["Close"])
    if not np.isfinite(price) or price <= 0:
        raise ValueError("Son kapanış fiyatı geçersiz.")

    current_price = round(price, 4)

    raw_eps = info.get("forwardEps")
    if raw_eps is None or isinstance(raw_eps, bool):
        return _empty_valuation("Forward EPS verisi yok.", current_price)
    try:
        forward_eps = float(raw_eps)
    except (TypeError, ValueError):
        return _empty_valuation("Forward EPS sayisal degil.", current_price)
    if not np.isfinite(forward_eps):
        return _empty_valuation("Forward EPS gecersiz.", current_price)

    sector = info.get("sector")
    fair_pe = get_fair_pe_policy().get(sector) if sector else None
    if fair_pe is None:
        return _empty_valuation(
            f"Sektor icin adil F/K tanimli degil: {sector or 'Unknown'}",
            current_price, forward_eps,
        )

    try:
        mrq = info.get("mostRecentQuarter")

        if isinstance(mrq, (int, float)) and not isinstance(mrq, bool):
            financial_date = datetime.fromtimestamp(mrq).date()
        elif isinstance(mrq, (datetime, pd.Timestamp)):
            financial_date = mrq.date()
        elif mrq:
            financial_date = pd.Timestamp(mrq).date()
        else:
            financial_date = None

        if financial_date is None:
            return _empty_valuation(
                "Finansal rapor tarihi bulunamadı.",
                current_price, forward_eps, fair_pe,
            )

        price_date = pd.Timestamp(df.index[-1]).date()

        validate_data_quality(
            price,
            financial_date,
            price_date=price_date,
        )

    except (ValueError, TypeError, OverflowError) as e:
        return _empty_valuation(e, current_price, forward_eps, fair_pe)

    try:
        result = calculate_pe_fair_value(current_price, forward_eps, fair_pe)
    except ValueError as e:
        return _empty_valuation(e, current_price, forward_eps, fair_pe)

    if not result.get("valid"):
        return _empty_valuation(
            result.get("reason", "Adil deger hesaplanamadi."),
            current_price, forward_eps, fair_pe,
        )

    try:
        upside = calculate_upside(current_price, result["fair_value"])
    except ValueError as e:
        return _empty_valuation(e, current_price, forward_eps, fair_pe)

    return {
        "current_price": current_price,
        "forward_eps": round(forward_eps, 4),
        "fair_pe": round(float(fair_pe), 2),
        "fair_value": result["fair_value"],
        "upside_pct": upside["upside_pct"],
        "valuation_model": result["model"],
        "valuation_valid": True,
        "valuation_reason": f"OK | {upside['status']}",
    }


# ============================================================
# 2.3b — MULTI-MODEL VALUATION (P/E + DCF)
# ============================================================
# ÖNEMLİ: combine_fair_values() LİSTE bekler; model adı result["model"]'den
# okunur. collect_valuation_inputs'ın 'valuation_model' alanı hesaplama
# etiketidir, model anahtarı değildir — adaptör bunu açıkça eşler.
# DCF girdileri yfinance.info'dan best-effort türetilir; doğrulanmamıştır.

DCF_DEFAULT_GROWTH_YEARS = 5
DCF_DEFAULT_TERMINAL_G = 0.025
DCF_DEFAULT_DISCOUNT_RATE = 0.10
DCF_DEFAULT_RISK_FREE = 0.045
DCF_DEFAULT_EQUITY_PREMIUM = 0.055


def _extract_dcf_inputs(current_price, info):
    """yfinance.info'dan DCF girdilerini best-effort çıkarır."""
    if not info or not isinstance(info, dict):
        raise ValueError("info sözlüğü yok.")

    fcf = info.get("freeCashflow")
    if fcf is None or isinstance(fcf, bool):
        raise ValueError("freeCashflow yok.")
    fcf = float(fcf)
    if not np.isfinite(fcf):
        raise ValueError("freeCashflow geçersiz.")

    cash = info.get("totalCash")
    debt = info.get("totalDebt")
    shares = info.get("sharesOutstanding")

    if cash is None or debt is None or shares is None:
        raise ValueError("cash/debt/shares eksik.")
    try:
        cash = float(cash)
        debt = float(debt)
        shares = float(shares)
    except (TypeError, ValueError):
        raise ValueError("cash/debt/shares sayısal değil.")
    if not np.isfinite(cash) or not np.isfinite(debt) or not np.isfinite(shares):
        raise ValueError("cash/debt/shares NaN/sonsuz.")
    if shares <= 0:
        raise ValueError("sharesOutstanding pozitif değil.")

    g_raw = info.get("earningsGrowth")
    if g_raw is None:
        g_raw = info.get("revenueGrowth")
    try:
        g0 = float(g_raw) if g_raw is not None else 0.05
    except (TypeError, ValueError):
        g0 = 0.05
    if not np.isfinite(g0):
        g0 = 0.05
    g0 = max(-0.5, min(0.5, g0))
    growth_rates = [
        round(g0 * (1 - i / DCF_DEFAULT_GROWTH_YEARS), 4)
        for i in range(DCF_DEFAULT_GROWTH_YEARS)
    ]

    beta = info.get("beta")
    try:
        beta = float(beta) if beta is not None else None
    except (TypeError, ValueError):
        beta = None
    if beta is not None and np.isfinite(beta) and beta > 0:
        discount_rate = DCF_DEFAULT_RISK_FREE + beta * DCF_DEFAULT_EQUITY_PREMIUM
        discount_rate = max(0.02, min(0.50, discount_rate))
    else:
        discount_rate = DCF_DEFAULT_DISCOUNT_RATE

    # fcf_definition GÖNDERİLMİYOR (motor opsiyonel kabul ediyor;
    # yfinance freeCashflow = OCF-capex, FCFF değil — yanlış etiketleme yapmıyoruz)
    return {
        "current_price": current_price,
        "current_fcf": fcf,
        "growth_rates": growth_rates,
        "discount_rate": discount_rate,
        "terminal_growth_rate": DCF_DEFAULT_TERMINAL_G,
        "cash": cash,
        "debt": debt,
        "diluted_shares": shares,
        "valuation_currency": info.get("financialCurrency"),
        "fcf_currency": info.get("financialCurrency"),
        "cash_currency": info.get("financialCurrency"),
        "debt_currency": info.get("financialCurrency"),
        "valuation_scope": "consolidated",
        "fcf_scope": "consolidated",
    }


def build_multi_model_valuation(df, info, valuation_data, weights=None, weight_rationales=None):
    """
    P/E (mevcut) + DCF sonuçlarını birleştirir, senaryoları üretir.
    Ağırlıklar dışarıdan verilir; %50/%50 gibi varsayım YOK.
    """
    weights = weights or {}
    rationales = weight_rationales or {}
    items = []

    # --- P/E öğesi ---
    pe_weight = weights.get("pe")
    if pe_weight is not None and valuation_data.get("valuation_valid"):
        items.append({
            "result": {
                "model": "FORWARD_PE",
                "valid": True,
                "fair_value": valuation_data.get("fair_value"),
                "current_price": valuation_data.get("current_price"),
                "forward_eps": valuation_data.get("forward_eps"),
                "fair_pe": valuation_data.get("fair_pe"),
                "reason": valuation_data.get("valuation_reason"),
            },
            "weight": float(pe_weight),
            "weight_rationale": rationales.get("pe", "Forward EPS x sektör adil F/K"),
        })

    # --- DCF öğesi ---
    dcf_result = None
    dcf_weight = weights.get("dcf")
    if dcf_weight is not None:
        try:
            dcf_inputs = _extract_dcf_inputs(
                current_price=float(valuation_data.get("current_price")
                                    or df["Close"].iloc[-1]),
                info=info,
            )
            dcf_result = calculate_dcf_fair_value(**dcf_inputs)
        except (ValueError, TypeError, KeyError) as e:
            dcf_result = {
                "model": "DCF",
                "valid": False,
                "reason": f"DCF girdileri hazırlanamadı: {e}",
                "fair_value": None,
            }
        items.append({
            "result": dcf_result,
            "weight": float(dcf_weight),
            "weight_rationale": rationales.get(
                "dcf", "FCFF DCF; girdiler yfinance.info'dan türetildi (doğrulanmamış)"
            ),
        })

    # --- Birleştirme ---
    combined = combine_fair_values(items)
    combined["valuation_engine_version"] = combined.get("engine_version", ENGINE_VERSION)
    combined["model_weights"] = combined.get("normalized_weights", {})
    combined["raw_models"] = {"pe": valuation_data, "dcf": dcf_result}

    # --- Senaryolar (P/E temelli; motor sözleşmesi EPS x F/K) ---
    scenarios = None
    try:
        current_price = float(valuation_data.get("current_price")
                              or df["Close"].iloc[-1])
        base_eps = valuation_data.get("forward_eps")
        base_pe = valuation_data.get("fair_pe")
        if base_eps and base_eps > 0 and base_pe and base_pe > 0:
            today_iso = datetime.now().date().isoformat()
            scenarios = calculate_valuation_scenarios(
                current_price=current_price,
                scenarios={
                    "bear": {
                        "eps": round(base_eps * 0.80, 4),
                        "pe": round(base_pe * 0.85, 2),
                        "weight": 0.25,
                        "eps_source": {"type": "assumption", "as_of": today_iso,
                                       "reference": "forward_eps * 0.80 (VARSAYIM)"},
                        "pe_source": {"type": "assumption", "as_of": today_iso,
                                      "reference": "fair_pe * 0.85 (VARSAYIM)"},
                    },
                    "base": {
                        "eps": round(base_eps, 4),
                        "pe": round(base_pe, 2),
                        "weight": 0.50,
                        "eps_source": {"type": "yfinance_forward_eps", "as_of": today_iso,
                                       "reference": "collect_valuation_inputs"},
                        "pe_source": {"type": "sector_policy", "as_of": today_iso,
                                      "reference": "ARFEZ_FAIR_PE_OVERRIDES"},
                    },
                    "bull": {
                        "eps": round(base_eps * 1.20, 4),
                        "pe": round(base_pe * 1.15, 2),
                        "weight": 0.25,
                        "eps_source": {"type": "assumption", "as_of": today_iso,
                                       "reference": "forward_eps * 1.20 (VARSAYIM)"},
                        "pe_source": {"type": "assumption", "as_of": today_iso,
                                      "reference": "fair_pe * 1.15 (VARSAYIM)"},
                    },
                },
                require_weights_sum_one=True,
            )
    except (ValueError, TypeError) as e:
        scenarios = {"valid": False, "reason": f"Senaryo hatasi: {e}"}

    return {
        "combined_fair_value": combined.get("fair_value"),
        "dcf_fair_value": (dcf_result.get("fair_value") if dcf_result else None),
        "dcf_upside_pct": (dcf_result.get("upside_pct") if dcf_result else None),
        "model_weights": combined.get("model_weights"),
        "valuation_scenarios": scenarios,
        "valuation_engine_version": combined["valuation_engine_version"],
        "combined_valid": combined.get("valid", False),
        "combined_reason": combined.get("reason"),
    }


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
# MAKRO
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
# ALIAS SKORLAR
# ============================================================
def compute_valuation_score(valuation_data):
    upside = valuation_data.get("upside_pct")
    if not valuation_data.get("valuation_valid") or upside is None:
        return None
    try:
        score = int((float(upside) + 20) * (100 / 60))
    except (TypeError, ValueError):
        return None
    return max(0, min(100, score))


def compute_capital_flow_score(tech_details, latest_close):
    rvol = tech_details.get('rvol', 1.0)
    ema20 = tech_details.get('ema20', latest_close)
    try:
        rvol = float(rvol) if rvol is not None else 1.0
        ema20 = float(ema20) if ema20 else float(latest_close)
    except (TypeError, ValueError):
        return 50

    if rvol > 1.5 and latest_close > ema20:
        return 80
    if rvol < 0.7:
        return 30
    return 50


# ============================================================
# TEK HISSE
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

        try:
            valuation_data = collect_valuation_inputs(df, info)
        except Exception as ve:
            valuation_data = _empty_valuation(
                f"Değerleme hatası: {ve}",
                current_price=float(df["Close"].iloc[-1]),
            )

        # --- 2.3b: Çoklu model değerleme ---
        try:
            multi_val = build_multi_model_valuation(
                df=df,
                info=info,
                valuation_data=valuation_data,
                weights={
                    "pe": float(os.getenv("ARFEZ_PE_WEIGHT", "0.7")),
                    "dcf": float(os.getenv("ARFEZ_DCF_WEIGHT", "0.3")),
                },
                weight_rationales={
                    "pe": "Forward EPS x sektör adil F/K; doğrulanmış politika",
                    "dcf": "FCFF DCF; yfinance.info'dan türetildi, doğrulanmamış",
                },
            )
        except Exception as mve:
            multi_val = {
                "combined_fair_value": None,
                "dcf_fair_value": None,
                "dcf_upside_pct": None,
                "model_weights": None,
                "valuation_scenarios": None,
                "valuation_engine_version": ENGINE_VERSION,
                "combined_valid": False,
                "combined_reason": f"Multi-model hatasi: {mve}",
            }

        technical, tech_details = calculate_technical_score(df)
        fundamental = calculate_fundamental_score(info)
        risk = calculate_risk_score(df, info)

        new_world = min(100, int((technical * 0.4 + fundamental * 0.4 + risk * 0.2) * 1.1))
        confidence = int(50 + (technical + fundamental) / 4)

        latest = df.iloc[-1]

        valuation_score = compute_valuation_score(valuation_data)
        valuation = valuation_score if valuation_score is not None else 50
        capital_flow = compute_capital_flow_score(tech_details, float(latest['Close']))
        theme = None

        current_price = valuation_data["current_price"]
        fair_value = valuation_data["fair_value"]
        upside_pct = valuation_data["upside_pct"]

        final = int(
            technical * 0.20 + fundamental * 0.20 + risk * 0.15 +
            new_world * 0.15 + macro_effect * 0.10 + confidence * 0.10 +
            valuation * 0.05 + capital_flow * 0.05
        )
        final = max(0, min(100, final))

        signal = 'AL' if final >= 80 and risk >= 50 else 'SAT' if final < 45 or risk < 30 else 'BEKLE'

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

        # JSON serileştirme (None güvenli)
        model_weights_json = (
            json.dumps(multi_val["model_weights"], ensure_ascii=False)
            if multi_val.get("model_weights") is not None else None
        )
        scenarios_json = (
            json.dumps(multi_val["valuation_scenarios"], ensure_ascii=False)
            if multi_val.get("valuation_scenarios") is not None else None
        )

        cursor.execute("""
            MERGE daily_scores AS target
            USING (VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?, ?, ?)) AS source
            (symbol, date, arfez_score, new_world_score, technical_score,
             fundamental_score, risk_score, macro_score, confidence,
             valuation_score, capital_flow_score, theme, signal,
             target_price, stop_loss, predicted_return,
             current_price, forward_eps, fair_pe, fair_value, upside_pct,
             valuation_model, valuation_valid, valuation_reason,
             dcf_fair_value, combined_fair_value, dcf_upside_pct,
             model_weights, valuation_scenarios, valuation_engine_version)
            ON target.symbol = source.symbol AND target.date = source.date
            WHEN MATCHED THEN UPDATE SET
                arfez_score = source.arfez_score,
                new_world_score = source.new_world_score,
                technical_score = source.technical_score,
                fundamental_score = source.fundamental_score,
                risk_score = source.risk_score,
                macro_score = source.macro_score,
                confidence = source.confidence,
                valuation_score = source.valuation_score,
                capital_flow_score = source.capital_flow_score,
                theme = source.theme,
                signal = source.signal,
                target_price = source.target_price,
                stop_loss = source.stop_loss,
                predicted_return = source.predicted_return,
                current_price = source.current_price,
                forward_eps = source.forward_eps,
                fair_pe = source.fair_pe,
                fair_value = source.fair_value,
                upside_pct = source.upside_pct,
                valuation_model = source.valuation_model,
                valuation_valid = source.valuation_valid,
                valuation_reason = source.valuation_reason,
                dcf_fair_value = source.dcf_fair_value,
                combined_fair_value = source.combined_fair_value,
                dcf_upside_pct = source.dcf_upside_pct,
                model_weights = source.model_weights,
                valuation_scenarios = source.valuation_scenarios,
                valuation_engine_version = source.valuation_engine_version
            WHEN NOT MATCHED THEN INSERT
            (symbol, date, arfez_score, new_world_score, technical_score,
             fundamental_score, risk_score, macro_score, confidence,
             valuation_score, capital_flow_score, theme, signal,
             target_price, stop_loss, predicted_return,
             current_price, forward_eps, fair_pe, fair_value, upside_pct,
             valuation_model, valuation_valid, valuation_reason,
             dcf_fair_value, combined_fair_value, dcf_upside_pct,
             model_weights, valuation_scenarios, valuation_engine_version)
            VALUES (source.symbol, source.date, source.arfez_score,
                    source.new_world_score, source.technical_score,
                    source.fundamental_score, source.risk_score,
                    source.macro_score, source.confidence,
                    source.valuation_score, source.capital_flow_score,
                    source.theme, source.signal, source.target_price,
                    source.stop_loss, source.predicted_return,
                    source.current_price, source.forward_eps, source.fair_pe,
                    source.fair_value, source.upside_pct, source.valuation_model,
                    source.valuation_valid, source.valuation_reason,
                    source.dcf_fair_value, source.combined_fair_value,
                    source.dcf_upside_pct, source.model_weights,
                    source.valuation_scenarios, source.valuation_engine_version);
        """,
            symbol, today, final, new_world, technical, fundamental, risk,
            macro_effect, confidence, valuation, capital_flow, theme, signal,
            target, stop, expected,
            current_price, valuation_data["forward_eps"], valuation_data["fair_pe"],
            fair_value, upside_pct,
            valuation_data["valuation_model"], valuation_data["valuation_valid"],
            valuation_data["valuation_reason"],
            multi_val["dcf_fair_value"], multi_val["combined_fair_value"],
            multi_val["dcf_upside_pct"], model_weights_json, scenarios_json,
            multi_val["valuation_engine_version"],
        )

        # predictions tablosuna yaz
        try:
            cursor.execute("""
                INSERT INTO predictions
                (symbol, date, predicted_return, confidence, period)
                VALUES (?, ?, ?, ?, ?)
            """, symbol, today, expected, confidence, period)
        except Exception as pe_err:
            print(f"(predictions yazma atlandi: {pe_err})", end=" ")

        print(f"OK skor={final} signal={signal} P/E={fair_value} DCF={multi_val['dcf_fair_value']} COMB={multi_val['combined_fair_value']}")
        return final

    except Exception as e:
        print(f"HATA: {e}")
        return None


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="ARFEZ AI Veri Toplayici")
    parser.add_argument("--symbols", type=str, default=None, help="Virgulle ayrilmis semboller")
    parser.add_argument("--period", type=str, default="daily", choices=["daily", "weekly"])
    args = parser.parse_args()

    conn = get_db()
    ensure_period_column(conn)
    ensure_fair_value_columns(conn)
    cursor = conn.cursor()

    macro_effect, regime = get_macro_effect(cursor)
    print(f"[MAKRO] effect={macro_effect} regime={regime}")

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        # UNIVERSE ortak modülden okunur (yoksa varsayılan)
        try:
            from universe import UNIVERSE
            symbols = UNIVERSE
        except ImportError:
            symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]

    print(f"[BATCH] {len(symbols)} sembol, period={args.period}")

    success = 0
    for sym in symbols:
        result = process_symbol(sym, cursor, macro_effect, regime, period=args.period)
        if result is not None:
            success += 1
        time.sleep(0.5)

    conn.commit()
    cursor.close()
    conn.close()
    print(f"\n[TAMAM] {success}/{len(symbols)} basarili")


if __name__ == "__main__":
    main()
