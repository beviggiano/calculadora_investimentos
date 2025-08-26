# finance/taxes.py
from __future__ import annotations

def aliquota_ir_por_dias(dias: int) -> float:
    """
    Tabela regressiva (Lei 11.033/2004, art. 1º; IN RFB 1.585/2015): 
    - até 180 dias: 22,5%
    - 181 a 360:    20,0%
    - 361 a 720:    17,5%
    - acima de 720: 15,0%
    Retorna fração (ex.: 0.225).
    """
    if dias <= 180:
        return 0.225
    if dias <= 360:
        return 0.20
    if dias <= 720:
        return 0.175
    return 0.15

def annual_to_monthly_fee(fee_aa: float) -> float:
    """
    Converte taxa anual de custo (admin/custódia) em equivalente mensal.
    Aplicada como redução do patrimônio: saldo *= (1 - fee_am)
    """
    return (1.0 + fee_aa) ** (1.0 / 12.0) - 1.0
