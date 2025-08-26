# finance/products.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict
from .tvm import aa_to_am
from .taxes import annual_to_monthly_fee, aliquota_ir_por_dias

@dataclass
class ProductConfig:
    nome: str
    i_am: float                 # taxa bruta efetiva mensal
    fee_admin_aa: float = 0.0   # % a.a. (por ex.: 0.01 = 1% a.a.)
    fee_custodia_aa: float = 0.0
    ir_isento: bool = False     # Poupança: True para PF
    prazo_meses: int = 0        # para cálculo de IR regressivo (base: meses*30 ~ dias)

    def fee_am_total(self) -> float:
        return annual_to_monthly_fee(self.fee_admin_aa) + annual_to_monthly_fee(self.fee_custodia_aa)

def taxa_poupanca_am(selic_aa: float, tr_am: float = 0.0) -> float:
    # regra didática
    if selic_aa > 0.085:
        return 0.005 + tr_am
    return (0.70 * selic_aa) / 12.0 + tr_am

def taxa_cdb_am(percentual_cdi: float, cdi_aa: float) -> float:
    i_cdi_am = aa_to_am(cdi_aa)
    return i_cdi_am * (percentual_cdi / 100.0)

def taxa_tesouro_selic_am(selic_aa: float) -> float:
    return aa_to_am(selic_aa)

def taxa_prefixado_am(taxa_prefixada_aa: float) -> float:
    return aa_to_am(taxa_prefixada_aa)

def taxa_ipca_am(taxa_real_aa: float, ipca_aa: float) -> float:
    """
    Composição aproximada: (1+real)*(1+IPCA) - 1 anual -> converte p/ mensal
    """
    nominal_aa = (1.0 + taxa_real_aa) * (1.0 + ipca_aa) - 1.0
    return aa_to_am(nominal_aa)

def aplicar_ir_liquido(vf_apos_custos: float, total_investido: float, prazo_meses: int, isento: bool) -> Dict[str, float]:
    """
    IR sobre rendimento (ganho = vf - total investido), cobrado no resgate.
    Retorna dict com vf_liquido e ir_pago.
    """
    if isento:
        return {"vf_liquido": vf_apos_custos, "ir_pago": 0.0}
    ganho = max(vf_apos_custos - total_investido, 0.0)
    dias = max(1, prazo_meses * 30)  # aproximação
    aliq = aliquota_ir_por_dias(dias)
    ir_pago = ganho * aliq
    vf_liquido = vf_apos_custos - ir_pago
    return {"vf_liquido": vf_liquido, "ir_pago": ir_pago}
