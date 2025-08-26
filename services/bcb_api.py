# services/bcb_api.py
from __future__ import annotations
import requests
from typing import Tuple, List
from datetime import datetime

SGS_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"

# Códigos SGS
SGS_TR_MENSAL = 226          # TR mensal (% a.m.)
SGS_SELIC_OVERNIGHT = 4189   # Selic Over (% a.a.)
SGS_CDI_OVERNIGHT = 4392     # CDI Over (% a.a.)
SGS_SELIC_META = 432         # Meta Selic (% a.a.)
SGS_IPCA_MENSAL = 433        # IPCA var. mensal (% ao mês)

def _get_sgs_last_value(code: int, n: int = 1) -> Tuple[float, str]:
    url = f"{SGS_BASE.format(code=code)}/ultimos/{n}?formato=json"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise RuntimeError(f"Série {code} sem dados.")
    ultimo = data[-1]
    valor = float(str(ultimo["valor"]).replace(",", "."))
    data_str = ultimo["data"]  # dd/mm/aaaa
    return valor, data_str

def _get_sgs_last_n_values(code: int, n: int) -> List[Tuple[str, float]]:
    url = f"{SGS_BASE.format(code=code)}/ultimos/{n}?formato=json"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    arr = []
    for item in r.json():
        valor = float(str(item["valor"]).replace(",", "."))
        arr.append((item["data"], valor))
    return arr

def get_tr_mensal() -> Tuple[float, str]:
    return _get_sgs_last_value(SGS_TR_MENSAL, 1)  # % a.m.

def get_selic_overnight_aa() -> Tuple[float, str]:
    return _get_sgs_last_value(SGS_SELIC_OVERNIGHT, 1)  # % a.a.

def get_cdi_overnight_aa() -> Tuple[float, str]:
    return _get_sgs_last_value(SGS_CDI_OVERNIGHT, 1)  # % a.a.

def get_selic_meta_aa() -> Tuple[float, str]:
    return _get_sgs_last_value(SGS_SELIC_META, 1)  # % a.a.

def get_ipca_12m() -> Tuple[float, str]:
    """
    IPCA acumulado 12 meses (aprox.): produto dos últimos 12 meses (1+ipca_m/100)-1
    Retorna (ipca_aa_decimal, 'mm/aaaa do último ponto')
    """
    ult_12 = _get_sgs_last_n_values(SGS_IPCA_MENSAL, 12)
    fator = 1.0
    for _, v_m in ult_12:
        fator *= (1.0 + v_m / 100.0)
    ipca_aa = fator - 1.0
    data_ultimo = ult_12[-1][0] if ult_12 else ""
    return ipca_aa, data_ultimo

def fetch_market_rates(prefer_meta_selic: bool = False, include_ipca=True) -> dict:
    cdi_val, cdi_data = get_cdi_overnight_aa()
    if prefer_meta_selic:
        selic_val, selic_data = get_selic_meta_aa()
        selic_src = "meta"
    else:
        selic_val, selic_data = get_selic_overnight_aa()
        selic_src = "overnight"
    tr_val, tr_data = get_tr_mensal()

    out = {
        "cdi_aa": cdi_val / 100.0,
        "cdi_data": cdi_data,
        "selic_aa": selic_val / 100.0,
        "selic_data": selic_data,
        "selic_source": selic_src,
        "tr_am": tr_val / 100.0,
        "tr_data": tr_data,
        "fetch_time": datetime.now().isoformat(timespec="seconds"),
    }
    if include_ipca:
        ipca_aa, ipca_data = get_ipca_12m()
        out.update({"ipca_aa": ipca_aa, "ipca_data": ipca_data})
    return out
