"""
ARFEZ AI v3.0 - Tahmin Hata Analizi (Tek Doğru Kaynak)
======================================================
data_collector.py ve app_mssql.py buradan import eder.
"""


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


# Eski isimle geriye dönük uyumluluk
determine_error_code = analyze_prediction_error
