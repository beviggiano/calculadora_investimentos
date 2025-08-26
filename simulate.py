# simulate.py
from __future__ import annotations
from typing import List, Dict
from finance.products import ProductConfig, aplicar_ir_liquido

def simular_produto(cfg: ProductConfig, n_meses: int, vp: float, pmt: float = 0.0, aporte_no_comeco=False) -> Dict:
    """
    Evolução com:
    - taxa bruta mensal cfg.i_am
    - custos mensais equivalentes (admin/custódia)
    - IR no resgate conforme prazo
    """
    saldo = vp
    evolucao_bruta = [saldo]
    fee_am = cfg.fee_am_total()
    for _ in range(1, n_meses + 1):
        if aporte_no_comeco:
            saldo += pmt
            saldo *= (1.0 + cfg.i_am)
        else:
            saldo *= (1.0 + cfg.i_am)
            saldo += pmt
        # aplica custo mensal sobre patrimônio
        if fee_am > 0.0:
            saldo *= (1.0 - fee_am)
        evolucao_bruta.append(saldo)

    total_investido = vp + pmt * n_meses
    vf_bruto = saldo
    ir_out = aplicar_ir_liquido(vf_bruto, total_investido, cfg.prazo_meses or n_meses, cfg.ir_isento)
    return {
        "nome": cfg.nome,
        "evolucao": evolucao_bruta,
        "vf_bruto": vf_bruto,
        "vf_liquido": ir_out["vf_liquido"],
        "ir_pago": ir_out["ir_pago"],
        "total_investido": total_investido,
        "prazo_meses": n_meses,
        "custos_am": fee_am,
    }

def comparar_series(configs: List[ProductConfig], n_meses: int, vp: float, pmt: float, aporte_no_comeco: bool) -> List[Dict]:
    out = []
    for cfg in configs:
        cfg.prazo_meses = n_meses
        out.append(simular_produto(cfg, n_meses, vp, pmt, aporte_no_comeco))
    return out
