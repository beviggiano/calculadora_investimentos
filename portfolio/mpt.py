# portfolio/mpt.py
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Tuple, Dict
from dataclasses import dataclass
from scipy.optimize import minimize

@dataclass
class MPTInput:
    mu_m: np.ndarray        # vetor de retornos esperados mensais (média simples)
    Sigma_m: np.ndarray     # matriz de covariâncias mensais
    names: list[str]        # nomes dos ativos
    rf_m: float             # taxa livre de risco mensal (Selic convertida p/ mês)
    bounds: Tuple[Tuple[float,float], ...]  # limites por ativo (ex.: (0,1) p/ sem short)

def _ensure_psd(S: np.ndarray, eps: float = 1e-10) -> np.ndarray:
    """Garante PSD por 'clip' nos autovalores negativos residuais."""
    vals, vecs = np.linalg.eigh(S)
    vals_clipped = np.clip(vals, eps, None)
    return (vecs @ np.diag(vals_clipped) @ vecs.T)

def portfolio_stats(w: np.ndarray, mu_m: np.ndarray, Sigma_m: np.ndarray, rf_m: float) -> Tuple[float, float, float]:
    """
    Retorno esperado mensal, vol mensal, Sharpe mensal (excesso/risk).
    """
    ret = float(w @ mu_m)
    vol = float(np.sqrt(w @ Sigma_m @ w))
    sharpe = (ret - rf_m) / vol if vol > 0 else -np.inf
    return ret, vol, sharpe

def max_sharpe(inp: MPTInput) -> Dict:
    n = len(inp.names)
    w0 = np.ones(n) / n
    cons = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    def obj(w):  # maximizar Sharpe -> minimizar negativo
        _, _, sh = portfolio_stats(w, inp.mu_m, inp.Sigma_m, inp.rf_m)
        return -sh
    res = minimize(obj, w0, method="SLSQP", bounds=inp.bounds, constraints=cons, options={"maxiter": 500})
    w = res.x
    ret, vol, sh = portfolio_stats(w, inp.mu_m, inp.Sigma_m, inp.rf_m)
    return {"w": w, "ret_m": ret, "vol_m": vol, "sharpe_m": sh, "success": res.success, "message": res.message}

def min_variance(inp: MPTInput) -> Dict:
    n = len(inp.names)
    w0 = np.ones(n) / n
    cons = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    def obj(w):
        return float(np.sqrt(w @ inp.Sigma_m @ w))
    res = minimize(obj, w0, method="SLSQP", bounds=inp.bounds, constraints=cons, options={"maxiter": 500})
    w = res.x
    ret, vol, sh = portfolio_stats(w, inp.mu_m, inp.Sigma_m, inp.rf_m)
    return {"w": w, "ret_m": ret, "vol_m": vol, "sharpe_m": sh, "success": res.success, "message": res.message}

def efficient_frontier(inp: MPTInput, n_pts: int = 40) -> pd.DataFrame:
    """
    Gera a fronteira resolvendo, para alvos de retorno, a mínima variância.
    """
    mu = inp.mu_m
    Sigma = inp.Sigma_m
    n = len(mu)
    w0 = np.ones(n) / n
    cons_base = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    rets = np.linspace(float(mu.min()), float(mu.max()*1.3), n_pts)  # varrer um pouco além
    rows = []
    for r_target in rets:
        cons = cons_base + [{"type": "eq", "fun": lambda w, targ=r_target: w @ mu - targ}]
        def obj(w): return float(w @ Sigma @ w)  # minimiza variância
        res = minimize(obj, w0, method="SLSQP", bounds=inp.bounds, constraints=cons, options={"maxiter": 500})
        if res.success:
            w = res.x
            ret, vol, sh = portfolio_stats(w, mu, Sigma, inp.rf_m)
            rows.append({"ret_m": ret, "vol_m": vol, "sharpe_m": sh})
    return pd.DataFrame(rows)

def annualize(ret_m: float, vol_m: float) -> Tuple[float, float]:
    """
    Annualiza retorno (geométrico) e volatilidade (sqrt(12)).
    """
    ret_a = (1.0 + ret_m) ** 12 - 1.0
    vol_a = vol_m * np.sqrt(12.0)
    return ret_a, vol_a
