
# fair_value_engine

from datetime import date, datetime
from math import isfinite


ENGINE_VERSION = "1.0.0"


def validate_number(value, field_name, minimum=None):
    """Sayısal girdiyi doğrular."""
    if value is None or isinstance(value, bool):
        raise ValueError(f"{field_name}: veri eksik.")

    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name}: sayısal değer gerekli.")

    if not isfinite(value):
        raise ValueError(f"{field_name}: geçersiz sayı.")

    if minimum is not None and value < minimum:
        raise ValueError(f"{field_name}: minimum değer {minimum}.")

    return value


def validate_data_quality(
    price,
    financial_date,
    price_date=None,
    max_financial_age_days=550,
    max_price_age_days=7,
):
    """
    Finansal verinin ve fiyatın tarihini kontrol eder.
    financial_date ve price_date: date, datetime veya YYYY-MM-DD.
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

    price = validate_number(price, "price", minimum=0.000001)
    fin_date = parse_date(financial_date, "financial_date")
    today = date.today()

    if fin_date > today:
        raise ValueError("Finansal veri tarihi gelecekte olamaz.")

    fin_age = (today - fin_date).days

    if fin_age > max_financial_age_days:
        raise ValueError(
            f"Finansal veri eski: {fin_age} gün."
        )

    result = {
        "valid": True,
        "price": price,
        "financial_date": fin_date.isoformat(),
        "financial_age_days": fin_age,
        "price_age_days": None,
        "engine_version": ENGINE_VERSION,
    }

    if price_date is not None:
        p_date = parse_date(price_date, "price_date")
        if p_date > today:
            raise ValueError("Fiyat tarihi gelecekte olamaz.")

        price_age = (today - p_date).days

        if price_age > max_price_age_days:
            raise ValueError(f"Hisse fiyatı eski: {price_age} gün.")

        result["price_date"] = p_date.isoformat()
        result["price_age_days"] = price_age

    return result


def calculate_pe_fair_value(
    current_price,
    forward_eps,
    fair_pe,
):
    """
    İleriye dönük EPS x gerekçelendirilmiş F/K.

    fair_pe dışarıdan sağlanmalıdır.
    Bu fonksiyon kendiliğinden uygun F/K tahmin etmez.
    """

    price = validate_number(
        current_price, "current_price", minimum=0.000001
    )
    eps = validate_number(forward_eps, "forward_eps")
    pe = validate_number(fair_pe, "fair_pe", minimum=0.01)

    if eps <= 0:
        return {
            "model": "FORWARD_PE",
            "valid": False,
            "reason": "EPS pozitif değil; standart F/K modeli uygun değil.",
            "fair_value": None,
        }

    fair_value = eps * pe

    return {
        "model": "FORWARD_PE",
        "valid": True,
        "current_price": round(price, 4),
        "forward_eps": eps,
        "fair_pe": pe,
        "fair_value": round(fair_value, 4),
        "upside_pct": round(
            (fair_value / price - 1) * 100, 2
        ),
    }


def calculate_dcf_fair_value(
    current_price,
    current_fcf,
    growth_rates,
    discount_rate,
    terminal_growth_rate,
    cash,
    debt,
    diluted_shares,
):
    """
    Basitleştirilmiş FCFF DCF modeli.

    current_fcf: son 12 aylık normalize edilmiş FCFF.
    growth_rates: her projeksiyon yılı için büyüme oranı.
                   Örnek: [0.12, 0.10, 0.08, 0.06, 0.04]
    discount_rate: WACC.
    terminal_growth_rate: uzun vadeli büyüme.
    cash, debt: aynı para biriminde net nakit/borç kalemleri.
    diluted_shares: seyreltilmiş hisse sayısı.

    Tüm finansal girdiler aynı para biriminde olmalı.
    """

    price = validate_number(
        current_price, "current_price", minimum=0.000001
    )
    fcf = validate_number(current_fcf, "current_fcf")
    wacc = validate_number(discount_rate, "discount_rate")
    terminal_g = validate_number(
        terminal_growth_rate, "terminal_growth_rate"
    )
    cash = validate_number(cash, "cash", minimum=0)
    debt = validate_number(debt, "debt", minimum=0)
    shares = validate_number(
        diluted_shares, "diluted_shares", minimum=0.000001
    )

    if fcf <= 0:
        raise ValueError(
            "FCF pozitif değil; bu DCF sürümü uygun olmayabilir."
        )

    if not isinstance(growth_rates, (list, tuple)) or not growth_rates:
        raise ValueError("growth_rates dolu bir liste olmalı.")

    rates = [
        validate_number(g, "growth_rate")
        for g in growth_rates
    ]

    if any(g <= -1 for g in rates):
        raise ValueError("Yıllık büyüme oranı -100%'den büyük olmalı.")

    if wacc <= terminal_g:
        raise ValueError(
            "WACC, terminal büyüme oranından büyük olmalı."
        )

    if wacc <= -1:
        raise ValueError("WACC geçersiz.")

    projected_fcf = []
    pv_fcf = 0.0
    previous_fcf = fcf

    for year, growth in enumerate(rates, start=1):
        previous_fcf *= (1 + growth)
        projected_fcf.append(previous_fcf)
        pv_fcf += previous_fcf / ((1 + wacc) ** year)

    terminal_fcf = projected_fcf[-1] * (1 + terminal_g)
    terminal_value = terminal_fcf / (wacc - terminal_g)

    terminal_pv = terminal_value / (
        (1 + wacc) ** len(rates)
    )

    enterprise_value = pv_fcf + terminal_pv
    equity_value = enterprise_value + cash - debt
    fair_value = equity_value / shares

    if fair_value <= 0:
        return {
            "model": "DCF",
            "valid": False,
            "reason": "Hesaplanan özkaynak değeri pozitif değil.",
            "fair_value": None,
        }

    return {
        "model": "DCF",
        "valid": True,
        "current_price": round(price, 4),
        "projected_fcf": [
            round(x, 2) for x in projected_fcf
        ],
        "pv_fcf": round(pv_fcf, 2),
        "terminal_value": round(terminal_value, 2),
        "terminal_pv": round(terminal_pv, 2),
        "enterprise_value": round(enterprise_value, 2),
        "equity_value": round(equity_value, 2),
        "fair_value": round(fair_value, 4),
        "upside_pct": round(
            (fair_value / price - 1) * 100, 2
        ),
    }


def combine_fair_values(models):
    """
    Geçerli model sonuçlarını ağırlıklı birleştirir.

    models örneği:
    [
        {"result": pe_result, "weight": 0.4},
        {"result": dcf_result, "weight": 0.6},
    ]

    Geçersiz modeller dışarıda bırakılır.
    Kalan ağırlıklar yeniden normalize edilir.
    """

    usable = []

    for item in models:
        result = item.get("result")
        weight = validate_number(
            item.get("weight"), "weight", minimum=0
        )

        if (
            result
            and result.get("valid") is True
            and result.get("fair_value") is not None
            and weight > 0
        ):
            value = validate_number(
                result["fair_value"], "fair_value",
                minimum=0.000001
            )
            usable.append((value, weight, result["model"]))

    if not usable:
        return {
            "valid": False,
            "fair_value": None,
            "reason": "Birleştirilecek geçerli model yok.",
        }

    total_weight = sum(weight for _, weight, _ in usable)

    fair_value = sum(
        value * weight for value, weight, _ in usable
    ) / total_weight

    return {
        "valid": True,
        "engine_version": ENGINE_VERSION,
        "fair_value": round(fair_value, 4),
        "models_used": [name for _, _, name in usable],
        "normalized_weights": {
            name: round(weight / total_weight, 4)
            for _, weight, name in usable
        },
    }


def calculate_upside(current_price, fair_value):
    """Mevcut fiyata göre değerleme farkını hesaplar."""

    price = validate_number(
        current_price, "current_price", minimum=0.000001
    )
    value = validate_number(
        fair_value, "fair_value", minimum=0.000001
    )

    upside = (value / price - 1) * 100

    if upside >= 15:
        status = "POTANSIYEL_UCUZ"
    elif upside <= -15:
        status = "POTANSIYEL_PAHALI"
    else:
        status = "ADIL_DEGERE_YAKIN"

    return {
        "current_price": round(price, 4),
        "fair_value": round(value, 4),
        "upside_pct": round(upside, 2),
        "status": status,
    }
    

def calculate_valuation_scenarios(
    current_price,
    forward_eps,
    scenarios,
):
    """
    Örnek scenarios:
    {
        "bear": {"eps": 9,  "pe": 22, "weight": 0.25},
        "base": {"eps": 12, "pe": 30, "weight": 0.50},
        "bull": {"eps": 15, "pe": 35, "weight": 0.25},
    }
    """

    price = validate_number(
        current_price, "current_price", minimum=0.000001
    )

    if not isinstance(scenarios, dict) or not scenarios:
        raise ValueError("Senaryo sözlüğü boş olamaz.")

    results = {}
    total_weight = 0.0
    weighted_value = 0.0

    for name, scenario in scenarios.items():
        eps = validate_number(
            scenario.get("eps"), f"{name}.eps"
        )
        pe = validate_number(
            scenario.get("pe"), f"{name}.pe",
            minimum=0.01
        )
        weight = validate_number(
            scenario.get("weight"), f"{name}.weight",
            minimum=0
        )

        if eps <= 0:
            raise ValueError(
                f"{name}: EPS pozitif olmalı; bu senaryo için "
                "başka bir değerleme yöntemi kullan."
            )

        fair_value = eps * pe

        results[name] = {
            "eps": eps,
            "pe": pe,
            "fair_value": round(fair_value, 4),
            "upside_pct": round(
                (fair_value / price - 1) * 100, 2
            ),
            "weight": weight,
        }

        total_weight += weight
        weighted_value += fair_value * weight

    if total_weight <= 0:
        raise ValueError("Senaryo ağırlıkları toplamı sıfır olamaz.")

    return {
        "valid": True,
        "current_price": round(price, 4),
        "scenarios": results,
        "weighted_fair_value": round(
            weighted_value / total_weight, 4
        ),
        "low_estimate": min(
            x["fair_value"] for x in results.values()
        ),
        "high_estimate": max(
            x["fair_value"] for x in results.values()
        ),
    }
    
    
if __name__ == "__main__":
    price = 375.0

    pe_result = calculate_pe_fair_value(
        current_price=price,
        forward_eps=12.0,
        fair_pe=30.0,
    )

    scenarios = calculate_valuation_scenarios(
        current_price=price,
        forward_eps=12.0,
        scenarios={
            "bear": {"eps": 9, "pe": 22, "weight": 0.25},
            "base": {"eps": 12, "pe": 30, "weight": 0.50},
            "bull": {"eps": 15, "pe": 35, "weight": 0.25},
        },
    )

    print("P/E sonucu:", pe_result)
    print("Senaryolar:", scenarios)
