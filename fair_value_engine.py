# fair_value_engine.py
# ENGINE_VERSION 1.1.0
"""
ARFEZ AI - Fair Value Engine
============================

Entegrasyon notları
-------------------
1. P/E, DCF ve birleşik değerleme API/collector katmanlarından çağrılmalıdır.
2. DCF yalnızca doğrulanmış, aynı para biriminde ve aynı kapsamda olan
   girdilerle hesaplanmalıdır.
3. Geçersiz modeller birleşik değerlemeye alınmamalıdır.
4. Senaryo varsayımlarının kaynakları saklanmalıdır.
5. Model ağırlıkları ve motor sürümü sonuçlarla birlikte kaydedilmelidir.
6. Demo verileri gerçek piyasa verilerinden ayrı tutulmalıdır.

Sürüm kaynağı
-------------
Tek sürüm kaynağı: ``ENGINE_VERSION``. API ve collector katmanları bu sabiti
import etmelidir; ayrı bir sürüm sabiti tanımlamak sürüm kaymasına yol açar.
(Geriye dönük uyumluluk için ``FAIR_VALUE_ENGINE_VERSION`` bu sabite alias'dır.)

Revizyon notları (madde numaraları 1. Revize edilecek yerler.txt ile eşleşir):
  1. validate_number: iş kuralı kontrolü genişletildi, hata mesajları netleştirildi.
  2. validate_data_quality: rapor tarihi ile çekim tarihi ayrıldı; price_date zorunlu;
     güncellik sınırları veri türü/piyasa takvimine göre parametrize edildi.
  3. calculate_pe_fair_value: hesaplama ile F/K tahmini ayrıştırıldı; tahmin meta verisi
     (kaynak, tarih, dayanak) ayrı bir sarmalayıcıda tutuluyor; çekirdek hesap korundu.
  4. calculate_dcf_fair_value: negatif/sıfır FCF için alternatif mod, oran makullük
     kontrolleri, terminal değer payı raporlaması, negatif nakit/borç ele alımı,
     birim/kapsam uyum kontrolü eklendi.
  5. combine_fair_values: yinelenen model adları tespit edilip hata fırlatılıyor;
     ağırlık gerekçesi opsiyonel olarak raporlanıyor.
  6. calculate_upside: eşikler parametreleştirildi; yatırım tavsiyesi olmadığı notu eklendi.
  7. calculate_valuation_scenarios: kullanılmayan forward_eps kaldırıldı (uyumluluk için
     opsiyonel tutuldu, kullanılırsa uyarı verir); ağırlık kuralları netleştirildi;
     senaryo varsayım kaynakları saklanıyor.
  8. __main__: örnek kullanım olarak korundu ama gerçek veri akışından izole edildi;
     demo olduğu açıkça belirtildi.
"""

from datetime import date, datetime
from math import isfinite


# ============================================================
# ARFEZ AI - FAIR VALUE ENGINE VERSION
# ============================================================
# Tek sürüm kaynağı. API (/api/health) ve collector bu sabiti import eder.
# Her yeni değerleme mantığı değişikliğinde bu sabiti güncelle.
ENGINE_VERSION = "1.1.0"

# Geriye dönük uyumluluk alias'ı (yeni kod ENGINE_VERSION kullanmalı).
FAIR_VALUE_ENGINE_VERSION = ENGINE_VERSION


# --- 1. Revizyon: merkezi iş kuralları sabitleri --------------------------------
# Tek yerde toplanan eşikler ve sınırlar; çağrılar bunları override edebilir.
DEFAULT_MAX_FINANCIAL_AGE_DAYS = 550
DEFAULT_MAX_PRICE_AGE_DAYS = 7
DEFAULT_UPSIDE_UPPER_PCT = 15.0     # 6. madde: eşik parametreleştirildi
DEFAULT_UPSIDE_LOWER_PCT = -15.0
DEFAULT_MIN_WACC = 0.02             # 4. madde: ekonomik makullük alt sınırı
DEFAULT_MAX_WACC = 0.50             # 4. madde: ekonomik makullük üst sınırı
DEFAULT_MIN_TERMINAL_G = -0.02      # 4. madde: terminal büyüme makul aralığı
DEFAULT_MAX_TERMINAL_G = 0.06
DEFAULT_MAX_TERMINAL_VALUE_SHARE = 0.90  # 4. madde: terminal değer payı uyarı eşiği
DEFAULT_FCF_STABILITY_YEARS = 5


# --- 1. Revizyon: validate_number ---------------------------------------------
def validate_number(
    value,
    field_name,
    minimum=None,
    maximum=None,
    allow_zero=True,
    allow_negative=True,
    strictly_positive=False,
):
    """
    Sayısal girdiyi doğrular ve iş kurallarına uygunluğunu denetler.

    Ek kontroller (madde 1):
      - bool reddedilir (Python'da bool int alt sınıfıdır; finansal alan değildir).
      - NaN ve sonsuz değerler reddedilir.
      - minimum/maximum aralık kontrolü.
      - allow_zero=False ise sıfır reddedilir.
      - allow_negative=False ise negatif değer reddedilir.
      - strictly_positive=True ise > 0 zorunludur.
    """
    if value is None or isinstance(value, bool):
        raise ValueError(f"{field_name}: veri eksik veya geçersiz tür.")

    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name}: sayısal değer gerekli.")

    if not isfinite(value):
        raise ValueError(f"{field_name}: geçersiz sayı (NaN/sonsuz).")

    if strictly_positive and value <= 0:
        raise ValueError(f"{field_name}: sıfırdan büyük olmalı.")

    if not allow_negative and value < 0:
        raise ValueError(f"{field_name}: negatif olamaz.")

    if not allow_zero and value == 0:
        raise ValueError(f"{field_name}: sıfır olamaz.")

    if minimum is not None and value < minimum:
        raise ValueError(f"{field_name}: minimum değer {minimum}.")

    if maximum is not None and value > maximum:
        raise ValueError(f"{field_name}: maksimum değer {maximum}.")

    return value


# --- 2. Revizyon: validate_data_quality --------------------------------------
def validate_data_quality(
    price,
    financial_date,
    price_date=None,
    fetched_at=None,
    max_financial_age_days=DEFAULT_MAX_FINANCIAL_AGE_DAYS,
    max_price_age_days=DEFAULT_MAX_PRICE_AGE_DAYS,
    require_price_date=True,
    today=None,
):
    """
    Finansal verinin ve fiyatın tarihini kontrol eder.

    Revizyonlar (madde 2):
      - financial_date: raporun ait olduğu dönem sonu tarihi.
      - fetched_at: verinin sisteme çekildiği tarih (opsiyonel; ayrı raporlanır).
      - price_date: artık varsayılan olarak ZORUNLU (require_price_date=True).
      - Güncellik sınırları parametreleştirildi; piyasa takvimine göre override edilebilir.
      - today enjekte edilebilir (deterministik test için).
    """
    def parse_date(value, field):
        if value is None:
            raise ValueError(f"{field}: tarih eksik.")
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value)[:10])
        except (TypeError, ValueError):
            raise ValueError(f"{field}: tarih formatı geçersiz.")

    price = validate_number(
        price, "price", strictly_positive=True
    )
    fin_date = parse_date(financial_date, "financial_date")
    reference_today = today or date.today()

    if fin_date > reference_today:
        raise ValueError("Finansal veri tarihi gelecekte olamaz.")

    fin_age = (reference_today - fin_date).days

    if fin_age > max_financial_age_days:
        raise ValueError(
            f"Finansal veri eski: {fin_age} gün (sınır "
            f"{max_financial_age_days})."
        )

    result = {
        "valid": True,
        "price": price,
        "financial_date": fin_date.isoformat(),
        "financial_age_days": fin_age,
        "financial_age_limit_days": max_financial_age_days,
        "price_age_days": None,
        "price_age_limit_days": max_price_age_days,
        "fetched_at": None,
        "engine_version": ENGINE_VERSION,
    }

    if fetched_at is not None:
        fetched_date = parse_date(fetched_at, "fetched_at")
        if fetched_date > reference_today:
            raise ValueError("Veri çekim tarihi gelecekte olamaz.")
        if fetched_date < fin_date:
            raise ValueError(
                "Veri çekim tarihi, finansal rapor tarihinden önce olamaz."
            )
        result["fetched_at"] = fetched_date.isoformat()

    if price_date is None:
        if require_price_date:
            raise ValueError(
                "price_date zorunlu; fiyat güncelliği denetlenemedi."
            )
        return result

    p_date = parse_date(price_date, "price_date")
    if p_date > reference_today:
        raise ValueError("Fiyat tarihi gelecekte olamaz.")

    price_age = (reference_today - p_date).days

    if price_age > max_price_age_days:
        raise ValueError(
            f"Hisse fiyatı eski: {price_age} gün (sınır "
            f"{max_price_age_days})."
        )

    result["price_date"] = p_date.isoformat()
    result["price_age_days"] = price_age
    return result


# --- 3. Revizyon: calculate_pe_fair_value ------------------------------------
def calculate_pe_fair_value(
    current_price,
    forward_eps,
    fair_pe,
    pe_estimate=None,
):
    """
    İleriye dönük EPS x gerekçelendirilmiş F/K.

    Revizyon (madde 3): Hesap ile F/K tahmini ayrıştırıldı.
      - fair_pe: hesaplamada kullanılan değer (çekirdek hesap değişmedi).
      - pe_estimate: opsiyonel meta veri; F/K tahmininin kaynağı, tarihi ve
        dayanağını taşır ve sonuca eklenir. Örnek:
            {
              "source": "analyst_consensus",
              "as_of": "2026-10-01",
              "rationale": "5 yıllık sektör medyanı, büyüme düzeltmeli",
              "value": 30.0,
            }
      - pe_estimate verilirse ve içindeki "value" fair_pe ile tutarsızsa
        uyarı raporlanır (hesap durdurulmaz; üst katman kararı verir).
    """
    price = validate_number(
        current_price, "current_price", strictly_positive=True
    )
    eps = validate_number(forward_eps, "forward_eps")
    pe = validate_number(
        fair_pe, "fair_pe", minimum=0.01
    )

    estimate_meta = None
    estimate_warning = None
    if pe_estimate is not None:
        if not isinstance(pe_estimate, dict):
            raise ValueError("pe_estimate: sözlük olmalı.")
        estimate_meta = {
            "source": pe_estimate.get("source"),
            "as_of": pe_estimate.get("as_of"),
            "rationale": pe_estimate.get("rationale"),
            "value": pe_estimate.get("value"),
        }
        est_value = pe_estimate.get("value")
        if est_value is not None:
            try:
                if abs(float(est_value) - pe) > 1e-6:
                    estimate_warning = (
                        "pe_estimate.value ile fair_pe tutarsız."
                    )
            except (TypeError, ValueError):
                estimate_warning = (
                    "pe_estimate.value sayısal değil."
                )

    if eps <= 0:
        return {
            "model": "FORWARD_PE",
            "valid": False,
            "reason": "EPS pozitif değil; standart F/K modeli uygun değil.",
            "fair_value": None,
            "pe_estimate": estimate_meta,
            "pe_estimate_warning": estimate_warning,
        }

    fair_value = eps * pe

    return {
        "model": "FORWARD_PE",
        "valid": True,
        "current_price": round(price, 4),
        "forward_eps": eps,
        "fair_pe": pe,
        "pe_estimate": estimate_meta,
        "pe_estimate_warning": estimate_warning,
        "fair_value": round(fair_value, 4),
        "upside_pct": round((fair_value / price - 1) * 100, 2),
    }


# --- 4. Revizyon: calculate_dcf_fair_value -----------------------------------
def calculate_dcf_fair_value(
    current_price,
    current_fcf,
    growth_rates,
    discount_rate,
    terminal_growth_rate,
    cash,
    debt,
    diluted_shares,
    net_debt=None,
    min_wacc=DEFAULT_MIN_WACC,
    max_wacc=DEFAULT_MAX_WACC,
    min_terminal_g=DEFAULT_MIN_TERMINAL_G,
    max_terminal_g=DEFAULT_MAX_TERMINAL_G,
    max_terminal_value_share=DEFAULT_MAX_TERMINAL_VALUE_SHARE,
    allow_negative_fcf=False,
    valuation_currency=None,
    fcf_currency=None,
    cash_currency=None,
    debt_currency=None,
    shares_currency=None,
    valuation_scope=None,
    fcf_scope=None,
    fcf_history=None,
    fcf_is_normalized=False,
    normalized_by=None,
    fcf_definition=None,
    capex=None,
    depreciation_amortization=None,
):
    """
    Basitleştirilmiş FCFF DCF modeli.

    Birim/kapsam doğrulaması (madde 4 tamamlayıcı):
      - valuation_currency / fcf_currency / cash_currency / debt_currency
        verilirse ve tutarsızsa hata fırlatılır.
      - shares_currency verilirse hata fırlatılır (hisse sayısı birimsizdir).
      - valuation_scope / fcf_scope verilirse ve tutarsızsa hata fırlatılır.
        Konsolide değerleme ile segment FCF karıştırılamaz.

    FCF niteliği (madde 4 tamamlayıcı):
      - fcf_definition verilirse yalnızca "FCFF" kabul edilir (bu model FCFF).
      - fcf_history verilirse:
          * negatif yıl oranı > %50 ise hata (FCF sürdürülemez),
          * varyasyon katsayısı çok yüksekse uyarı,
      - fcf_is_normalized=False ise uyarı (normalize edilmemiş FCF).
      - capex ve D&A verilirse capex/D&A oranı > 3 ise uyarı (yatırım yoğunluğu).
    """
    price = validate_number(
        current_price, "current_price", strictly_positive=True
    )
    fcf = validate_number(current_fcf, "current_fcf")
    wacc = validate_number(discount_rate, "discount_rate")
    terminal_g = validate_number(
        terminal_growth_rate, "terminal_growth_rate"
    )
    shares = validate_number(
        diluted_shares, "diluted_shares", strictly_positive=True
    )

    # 4a. Birim doğrulaması
    if shares_currency is not None:
        raise ValueError(
            "shares_currency verilmemeli; seyreltilmiş hisse sayısı birimsizdir."
        )

    currencies = {
        "valuation_currency": valuation_currency,
        "fcf_currency": fcf_currency,
        "cash_currency": cash_currency,
        "debt_currency": debt_currency,
    }
    provided_currencies = {
        k: v for k, v in currencies.items() if v is not None
    }
    if len(set(provided_currencies.values())) > 1:
        raise ValueError(
            f"Para birimi tutarsızlığı: {provided_currencies}. "
            "FCFF, nakit, borç ve değerleme aynı para biriminde olmalı."
        )

    # 4b. Kapsam doğrulaması
    if (
        valuation_scope is not None
        and fcf_scope is not None
        and valuation_scope != fcf_scope
    ):
        raise ValueError(
            f"Değerleme kapsamı uyumsuz: valuation_scope={valuation_scope}, "
            f"fcf_scope={fcf_scope}. Aynı kapsamda olmalı."
        )

    # 4c. FCF tanımı
    if fcf_definition is not None:
        if fcf_definition not in ("FCFF", "FCFE", "OCF-capex"):
            raise ValueError(
                f"fcf_definition geçersiz: {fcf_definition}. "
                "Beklenen: FCFF, FCFE, OCF-capex."
            )
        if fcf_definition != "FCFF":
            raise ValueError(
                f"Bu model FCFF bekler; verilen: {fcf_definition}. "
                "FCFE için özkaynak DCF modeli kullanın."
            )

    warnings = []

    # 4d. FCF geçmişi niteliği
    fcf_quality = {}
    if fcf_history is not None:
        if not isinstance(fcf_history, (list, tuple)) or not fcf_history:
            raise ValueError("fcf_history dolu bir liste olmalı.")
        hist = [
            validate_number(x, "fcf_history[]") for x in fcf_history
        ]
        neg_count = sum(1 for x in hist if x <= 0)
        neg_ratio = neg_count / len(hist)
        mean = sum(hist) / len(hist)
        var = sum((x - mean) ** 2 for x in hist) / len(hist)
        std = var ** 0.5
        cv = (std / abs(mean)) if mean != 0 else None

        fcf_quality = {
            "years": len(hist),
            "negative_years": neg_count,
            "negative_ratio": round(neg_ratio, 4),
            "coefficient_of_variation": (
                round(cv, 4) if cv is not None else None
            ),
        }

        if neg_ratio > 0.5:
            raise ValueError(
                f"FCF geçmişinin %{neg_ratio*100:.0f}'i negatif; "
                "FCFF DCF bu şirket için uygun değil."
            )
        if neg_ratio > 0:
            warnings.append(
                f"FCF geçmişinde {neg_count} negatif yıl var; "
                "sürdürülebilirlik belirsiz."
            )
        if cv is not None and cv > 0.5:
            warnings.append(
                f"FCF oynaklığı yüksek (CV={cv:.2f}); projeksiyonlar "
                "düşük güvenilirlikte olabilir."
            )

    # 4e. Normalizasyon kontrolü
    if not fcf_is_normalized:
        warnings.append(
            "FCF normalize edilmemiş; tek seferlik kalemler sonucu saptırabilir."
        )
    else:
        fcf_quality["normalized_by"] = normalized_by

    # 4f. Capex / D&A dengesi
    capex_da_ratio = None
    if capex is not None and depreciation_amortization is not None:
        capex_val = validate_number(capex, "capex", minimum=0)
        da_val = validate_number(
            depreciation_amortization, "depreciation_amortization",
            minimum=0,
        )
        if da_val > 0:
            capex_da_ratio = capex_val / da_val
            if capex_da_ratio > 3.0:
                warnings.append(
                    f"Capex/D&A oranı yüksek: {capex_da_ratio:.2f}. "
                    "Yatırım yoğunluğu FCF'yi baskılıyor olabilir."
                )

    # Negatif FCF davranışı
    if fcf <= 0:
        if not allow_negative_fcf:
            raise ValueError(
                "FCF pozitif değil; negatif FCF için allow_negative_fcf=True "
                "veya alternatif model (ör. EV/Sales, P/B) kullanın."
            )
        return {
            "model": "DCF",
            "valid": False,
            "reason": "FCF pozitif değil; bu DCF sürümü uygun değil.",
            "suggested_alternatives": ["EV/SALES", "P/B", "NAV", "DDM"],
            "fair_value": None,
            "fcf_quality": fcf_quality or None,
            "warnings": warnings,
        }

    # Oran makullük kontrolleri
    if not (min_wacc <= wacc <= max_wacc):
        raise ValueError(
            f"WACC makul aralık dışında: {wacc} ({min_wacc}–{max_wacc})."
        )
    if not (min_terminal_g <= terminal_g <= max_terminal_g):
        raise ValueError(
            f"Terminal büyüme makul aralık dışında: {terminal_g} "
            f"({min_terminal_g}–{max_terminal_g})."
        )
    if wacc <= terminal_g:
        raise ValueError("WACC, terminal büyüme oranından büyük olmalı.")

    if net_debt is not None:
        net_debt_val = validate_number(net_debt, "net_debt")
        equity_adjustment = -net_debt_val
        cash_used = None
        debt_used = None
    else:
        cash_used = validate_number(cash, "cash", minimum=0)
        debt_used = validate_number(debt, "debt", minimum=0)
        equity_adjustment = cash_used - debt_used

    if not isinstance(growth_rates, (list, tuple)) or not growth_rates:
        raise ValueError("growth_rates dolu bir liste olmalı.")

    rates = [validate_number(g, "growth_rate") for g in growth_rates]
    if any(g <= -1 for g in rates):
        raise ValueError("Yıllık büyüme oranı -100%'den büyük olmalı.")

    projected_fcf = []
    pv_fcf = 0.0
    previous_fcf = fcf
    for year, growth in enumerate(rates, start=1):
        previous_fcf *= (1 + growth)
        projected_fcf.append(previous_fcf)
        pv_fcf += previous_fcf / ((1 + wacc) ** year)

    terminal_fcf = projected_fcf[-1] * (1 + terminal_g)
    terminal_value = terminal_fcf / (wacc - terminal_g)
    terminal_pv = terminal_value / ((1 + wacc) ** len(rates))

    enterprise_value = pv_fcf + terminal_pv
    equity_value = enterprise_value + equity_adjustment
    fair_value = equity_value / shares

    if fair_value <= 0:
        return {
            "model": "DCF",
            "valid": False,
            "reason": "Hesaplanan özkaynak değeri pozitif değil.",
            "fair_value": None,
            "enterprise_value": round(enterprise_value, 2),
            "equity_value": round(equity_value, 2),
            "fcf_quality": fcf_quality or None,
            "warnings": warnings,
        }

    terminal_share = (
        terminal_pv / enterprise_value if enterprise_value != 0 else None
    )
    if (
        terminal_share is not None
        and terminal_share > max_terminal_value_share
    ):
        warnings.append(
            f"Terminal değerin işletme değeri içindeki payı yüksek: "
            f"{terminal_share:.1%} (eşik {max_terminal_value_share:.0%})."
        )

    def _dcf_core(w, g_t):
        pv = 0.0
        prev = fcf
        for yr, gr in enumerate(rates, start=1):
            prev *= (1 + gr)
            pv += prev / ((1 + w) ** yr)
        tv = (prev * (1 + g_t)) / (w - g_t)
        tp = tv / ((1 + w) ** len(rates))
        return (pv + tp + equity_adjustment) / shares

    sensitivity = {}
    try:
        sensitivity["wacc_minus_1pct"] = round(
            _dcf_core(wacc - 0.01, terminal_g), 4
        )
        sensitivity["wacc_plus_1pct"] = round(
            _dcf_core(wacc + 0.01, terminal_g), 4
        )
        sensitivity["terminal_g_minus_05pct"] = round(
            _dcf_core(wacc, terminal_g - 0.005), 4
        )
        sensitivity["terminal_g_plus_05pct"] = round(
            _dcf_core(wacc, terminal_g + 0.005), 4
        )
    except (ValueError, ZeroDivisionError):
        sensitivity = None

    return {
        "model": "DCF",
        "valid": True,
        "current_price": round(price, 4),
        "valuation_currency": valuation_currency,
        "valuation_scope": valuation_scope,
        "projected_fcf": [round(x, 2) for x in projected_fcf],
        "pv_fcf": round(pv_fcf, 2),
        "terminal_value": round(terminal_value, 2),
        "terminal_pv": round(terminal_pv, 2),
        "terminal_value_share_of_ev": (
            round(terminal_share, 4) if terminal_share is not None else None
        ),
        "enterprise_value": round(enterprise_value, 2),
        "equity_value": round(equity_value, 2),
        "equity_adjustment": round(equity_adjustment, 2),
        "net_debt_used": (
            round(net_debt_val, 2) if net_debt is not None else None
        ),
        "cash_used": cash_used,
        "debt_used": debt_used,
        "fair_value": round(fair_value, 4),
        "upside_pct": round((fair_value / price - 1) * 100, 2),
        "sensitivity": sensitivity,
        "fcf_quality": fcf_quality or None,
        "capex_da_ratio": (
            round(capex_da_ratio, 4) if capex_da_ratio is not None else None
        ),
        "warnings": warnings,
        "note": (
            "current_price yalnızca upside_pct için kullanılır; "
            "değerlemenin doğruluğunu belirlemez. Tüm parasal girdiler "
            "aynı para biriminde ve aynı değerleme kapsamında olmalıdır."
        ),
    }


# --- 5. Revizyon: combine_fair_values ----------------------------------------
def combine_fair_values(models):
    """
    Geçerli model sonuçlarını ağırlıklı birleştirir.

    Beklenen giriş şeması (SÖZLEŞME):
        models: [
            {
                "result": <model sonucu sözlüğü; içinde "model", "valid",
                           "fair_value" olmalı>,
                "weight": <sayı > 0>,
                "weight_rationale": <opsiyonel string>,
            },
            ...
        ]

    NOT: Bu fonksiyon "name" anahtarını KULLANMAZ; model adı
    result["model"] alanından okunur. Üst katman "name" gönderiyorsa
    bunu result içine taşımalıdır.

    Revizyonlar (madde 5):
      - Yinelenen model adları tespit edilir ve hata fırlatılır; böylece
        normalized_weights sözlüğünde üzerine yazma önlenir.
      - Her modele opsiyonel "weight_rationale" alanı eklenebilir; sonuçta
        raporlanır.
    """
    usable = []
    seen_models = set()

    for item in models:
        result = item.get("result")
        weight_raw = item.get("weight")
        if weight_raw is None:
            continue
        try:
            weight = validate_number(
                weight_raw, "weight", minimum=0
            )
        except ValueError:
            continue

        if not (
            result
            and result.get("valid") is True
            and result.get("fair_value") is not None
            and weight > 0
        ):
            continue

        model_name = result.get("model")
        if model_name in seen_models:
            raise ValueError(
                f"Yinelenen model adı: {model_name}. "
                "Her model yalnızca bir kez birleştirilebilir."
            )
        seen_models.add(model_name)

        value = validate_number(
            result["fair_value"], "fair_value",
            strictly_positive=True,
        )
        rationale = item.get("weight_rationale")
        usable.append((value, weight, model_name, rationale))

    if not usable:
        return {
            "valid": False,
            "fair_value": None,
            "reason": "Birleştirilecek geçerli model yok.",
        }

    total_weight = sum(weight for _, weight, _, _ in usable)
    fair_value = sum(
        value * weight for value, weight, _, _ in usable
    ) / total_weight

    return {
        "valid": True,
        "engine_version": ENGINE_VERSION,
        "fair_value": round(fair_value, 4),
        "models_used": [name for _, _, name, _ in usable],
        "normalized_weights": {
            name: round(weight / total_weight, 4)
            for _, weight, name, _ in usable
        },
        "weight_rationales": {
            name: rationale
            for _, _, name, rationale in usable
            if rationale is not None
        },
    }


# --- 6. Revizyon: calculate_upside -------------------------------------------
def calculate_upside(
    current_price,
    fair_value,
    upper_threshold_pct=DEFAULT_UPSIDE_UPPER_PCT,
    lower_threshold_pct=DEFAULT_UPSIDE_LOWER_PCT,
):
    """
    Mevcut fiyata göre değerleme farkını hesaplar.

    Revizyonlar (madde 6):
      - %15/-%15 eşikleri parametreleştirildi (proje tercihi, evrensel kural değil).
      - Sonuç yatırım tavsiyesi değildir notu eklendi.
    """
    price = validate_number(
        current_price, "current_price", strictly_positive=True
    )
    value = validate_number(
        fair_value, "fair_value", strictly_positive=True
    )
    upper = validate_number(
        upper_threshold_pct, "upper_threshold_pct"
    )
    lower = validate_number(
        lower_threshold_pct, "lower_threshold_pct"
    )
    if lower >= upper:
        raise ValueError(
            "lower_threshold_pct, upper_threshold_pct'ten küçük olmalı."
        )

    upside = (value / price - 1) * 100

    if upside >= upper:
        status = "POTANSIYEL_UCUZ"
    elif upside <= lower:
        status = "POTANSIYEL_PAHALI"
    else:
        status = "ADIL_DEGERE_YAKIN"

    return {
        "current_price": round(price, 4),
        "fair_value": round(value, 4),
        "upside_pct": round(upside, 2),
        "status": status,
        "thresholds": {"upper_pct": upper, "lower_pct": lower},
        "disclaimer": (
            "Bu sonuç yalnızca potansiyel fiyat farkını gösterir; "
            "yatırım tavsiyesi değildir."
        ),
    }


# --- 7. Revizyon: calculate_valuation_scenarios ------------------------------
def calculate_valuation_scenarios(
    current_price,
    scenarios,
    require_weights_sum_one=False,
    **_deprecated_kwargs,
):
    """
    Senaryo bazlı değerleme.

    Örnek scenarios:
    {
        "bear": {
            "eps": 9, "pe": 22, "weight": 0.25,
            "eps_source": {"type": "management_guidance", "as_of": "2026-09-30",
                           "reference": "FY26 alt bant"},
            "pe_source": {"type": "sector_median", "as_of": "2026-10-01",
                          "reference": "5y medyan, büyüme düzeltmeli"},
        },
        "base": {...},
        "bull": {...},
    }

    Revizyonlar (madde 7 tamamlayıcı):
      - forward_eps tamamen kaldırıldı. Geriye dönük uyumluluk için
        **_deprecated_kwargs ile yakalanır ve uyarı üretilir (sessizce yutulmaz).
      - Her senaryoda EPS ve F/K varsayımlarının kaynağı AYRI AYRI saklanır:
          * eps_source: {"type", "as_of", "reference"}
          * pe_source:  {"type", "as_of", "reference"}
        Eksikse None döner ve uyarı listesine eklenir.
      - Ağırlık kuralları: her ağırlık [0,1], toplam > 0;
        require_weights_sum_one=True ise toplam == 1.
    """
    if _deprecated_kwargs:
        deprecated = ", ".join(_deprecated_kwargs.keys())
        raise TypeError(
            f"calculate_valuation_scenarios artık şu parametreleri kabul etmiyor: "
            f"{deprecated}. forward_eps kaldırıldı; EPS senaryo içinde verilmeli."
        )

    price = validate_number(
        current_price, "current_price", strictly_positive=True
    )

    if not isinstance(scenarios, dict) or not scenarios:
        raise ValueError("Senaryo sözlüğü boş olamaz.")

    def _validate_source(src, field):
        if src is None:
            return None
        if not isinstance(src, dict):
            raise ValueError(f"{field}: sözlük olmalı veya None.")
        return {
            "type": src.get("type"),
            "as_of": src.get("as_of"),
            "reference": src.get("reference"),
        }

    results = {}
    total_weight = 0.0
    weighted_value = 0.0
    warnings = []

    for name, scenario in scenarios.items():
        if not isinstance(scenario, dict):
            raise ValueError(f"{name}: senaryo sözlük olmalı.")

        eps = validate_number(scenario.get("eps"), f"{name}.eps")
        pe = validate_number(
            scenario.get("pe"), f"{name}.pe", minimum=0.01
        )
        weight = validate_number(
            scenario.get("weight"), f"{name}.weight",
            minimum=0, maximum=1,
        )

        if eps <= 0:
            raise ValueError(
                f"{name}: EPS pozitif olmalı; bu senaryo için "
                "başka bir değerleme yöntemi kullan."
            )

        eps_source = _validate_source(
            scenario.get("eps_source"), f"{name}.eps_source"
        )
        pe_source = _validate_source(
            scenario.get("pe_source"), f"{name}.pe_source"
        )
        if eps_source is None:
            warnings.append(f"{name}: eps_source belirtilmemiş.")
        if pe_source is None:
            warnings.append(f"{name}: pe_source belirtilmemiş.")

        fair_value = eps * pe
        results[name] = {
            "eps": eps,
            "pe": pe,
            "eps_source": eps_source,
            "pe_source": pe_source,
            "fair_value": round(fair_value, 4),
            "upside_pct": round((fair_value / price - 1) * 100, 2),
            "weight": weight,
        }
        total_weight += weight
        weighted_value += fair_value * weight

    if total_weight <= 0:
        raise ValueError("Senaryo ağırlıkları toplamı sıfır olamaz.")

    if require_weights_sum_one and abs(total_weight - 1.0) > 1e-6:
        raise ValueError(
            f"Senaryo ağırlıkları toplamı 1 olmalı; mevcut: {total_weight}."
        )

    return {
        "valid": True,
        "current_price": round(price, 4),
        "scenarios": results,
        "weighted_fair_value": round(weighted_value / total_weight, 4),
        "low_estimate": min(x["fair_value"] for x in results.values()),
        "high_estimate": max(x["fair_value"] for x in results.values()),
        "weights_sum_one_enforced": require_weights_sum_one,
        "warnings": warnings,
        "engine_version": ENGINE_VERSION,
    }


# --- 8. Revizyon: __main__ ---------------------------------------------------
if __name__ == "__main__":
    # DİKKAT: Bu blok yalnızca ÖRNEK KULLANIM/demo amaçlıdır.
    # Buradaki değerler (fiyat, EPS, F/K, senaryolar) gerçek piyasa verisi
    # değildir. Gerçek veri toplama ve analiz akışı bu sabitleri kullanmaz;
    # üretimde bu blok çalıştırılmaz (yalnızca doğrudan çalıştırıldığında).
    demo_price = 375.0
    demo_eps = 12.0
    demo_pe = 30.0

    print("=== DEMO (gerçek veri değil) ===")

    pe_result = calculate_pe_fair_value(
        current_price=demo_price,
        forward_eps=demo_eps,
        fair_pe=demo_pe,
        pe_estimate={
            "source": "demo",
            "as_of": "2026-10-17",
            "rationale": "örnek",
            "value": demo_pe,
        },
    )

    dcf_result = calculate_dcf_fair_value(
        current_price=demo_price,
        current_fcf=2_000_000,
        growth_rates=[0.12, 0.10, 0.08, 0.06, 0.04],
        discount_rate=0.10,
        terminal_growth_rate=0.03,
        cash=5_000_000,
        debt=2_000_000,
        diluted_shares=1_000_000,
    )

    combined = combine_fair_values([
        {"result": pe_result, "weight": 0.4,
         "weight_rationale": "demo: konsensüs F/K"},
        {"result": dcf_result, "weight": 0.6,
         "weight_rationale": "demo: FCFF modeli"},
    ])

    scenarios = calculate_valuation_scenarios(
        current_price=demo_price,
        scenarios={
            "bear": {"eps": 9, "pe": 22, "weight": 0.25,
                     "assumption_source": "demo"},
            "base": {"eps": 12, "pe": 30, "weight": 0.50,
                     "assumption_source": "demo"},
            "bull": {"eps": 15, "pe": 35, "weight": 0.25,
                     "assumption_source": "demo"},
        },
        require_weights_sum_one=True,
    )

    upside = calculate_upside(demo_price, pe_result["fair_value"])

    print("P/E sonucu:", pe_result)
    print("DCF sonucu:", dcf_result)
    print("Birleşik:", combined)
    print("Senaryolar:", scenarios)
    print("Upside:", upside)
