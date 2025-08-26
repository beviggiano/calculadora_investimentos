# finance/tvm.py
from __future__ import annotations
import math

def aa_to_am(i_aa: float) -> float:
    """Converte taxa efetiva ao ano para efetiva ao mês: (1+i)^1/12 - 1"""
    return (1.0 + i_aa) ** (1.0 / 12.0) - 1.0

def am_to_aa(i_am: float) -> float:
    """Converte taxa efetiva ao mês para efetiva ao ano: (1+i)^12 - 1"""
    return (1.0 + i_am) ** 12.0 - 1.0

def vf_simples(vp: float, i: float, n: int) -> float:
    """VF juros simples: VP*(1 + i*n)"""
    return vp * (1.0 + i * n)

def vf_compostos(vp: float, i: float, n: int) -> float:
    """VF juros compostos: VP*(1+i)^n"""
    return vp * ((1.0 + i) ** n)

def vp_compostos(vf: float, i: float, n: int) -> float:
    """VP em compostos: VF/(1+i)^n"""
    return vf / ((1.0 + i) ** n)

def vf_serie_pmt(i: float, n: int, pmt: float, aporte_no_comeco=False) -> float:
    """
    VF de anuidade (aportes uniformes).
    Postecipada: PMT*(((1+i)^n - 1)/i)
    Antecipada: acima * (1+i)
    """
    if i == 0:
        vf = pmt * n
    else:
        vf = pmt * (((1.0 + i) ** n - 1.0) / i)
    if aporte_no_comeco and i != 0:
        vf *= (1.0 + i)
    return vf

def pmt_para_meta(vp: float, i: float, n: int, vf_desejado: float, aporte_no_comeco=False) -> float:
    """
    Resolve PMT para atingir VF desejado, dado VP e taxa i.
    """
    vf_do_vp = vf_compostos(vp, i, n)
    alvo = max(vf_desejado - vf_do_vp, 0.0)
    if i == 0:
        return (alvo / n) if n > 0 else 0.0
    fator = (((1.0 + i) ** n - 1.0) / i)
    if aporte_no_comeco:
        fator *= (1.0 + i)
    return alvo / fator if fator != 0 else 0.0
