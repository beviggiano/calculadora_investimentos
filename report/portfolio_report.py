# report/portfolio_report.py
from __future__ import annotations
import os
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .report import pdf_relatorio  # reutilizaremos o gerador PDF “genérico” se quiser anexar páginas extras

def plot_frontier_png(path_png: str, df_frontier: pd.DataFrame, pt_maxsharpe: dict, pt_minvar: dict) -> None:
    """
    Plota a fronteira eficiente (vol x retorno) e destaca pontos de máx. Sharpe e mín. variância.
    Regra: 1 gráfico por figura, sem definir cores.
    """
    plt.figure()
    if not df_frontier.empty:
        plt.plot(df_frontier["vol_m"], df_frontier["ret_m"], linestyle="-", marker="")
    # pontos
    plt.scatter([pt_maxsharpe["vol_m"]], [pt_maxsharpe["ret_m"]], label="Máx. Sharpe")
    plt.scatter([pt_minvar["vol_m"]], [pt_minvar["ret_m"]], label="Mín. Variância")
    plt.xlabel("Volatilidade mensal")
    plt.ylabel("Retorno mensal")
    plt.title("Fronteira Eficiente (Mensal)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path_png, dpi=150)
    plt.close()

def plot_growth_png(path_png: str, returns_df: pd.DataFrame, weights: np.ndarray, label: str) -> None:
    """
    Plot do crescimento de R$1 para uma carteira (backtest simples sem rebalanceamento intra-período).
    """
    plt.figure()
    w = np.array(weights).reshape(-1, 1)
    # carteira: retorno período = soma(w_i * r_i,t)
    port_r = returns_df.fillna(0.0).values @ w  # (T x N) @ (N x 1) = (T x 1)
    port_r = pd.Series(port_r.ravel(), index=returns_df.index)
    growth = (1.0 + port_r).cumprod()
    plt.plot(growth.index, growth.values, label=label)
    plt.xlabel("Tempo")
    plt.ylabel("Crescimento de R$1")
    plt.title(f"Crescimento – {label}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path_png, dpi=150)
    plt.close()

def save_portfolio_html(path_html: str, summary: dict, images: dict) -> None:
    """
    HTML simples com métricas e links para as imagens.
    """
    def fmt(x): 
        return f"{x:,.4f}" if isinstance(x, (int, float)) else str(x)
    def pct(x): 
        return f"{x*100:.2f}%"
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    lines = []
    for k,v in summary.items():
        lines.append(f"<tr><td>{k}</td><td style='text-align:right'>{fmt(v)}</td></tr>")
    html = f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8">
<title>Relatório – Portfólio (MPT)</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;margin:2rem}}
table{{border-collapse:collapse;width:100%;margin:1rem 0}}
th,td{{border:1px solid #ddd;padding:8px}}
th{{background:#f2f2f2}} td:nth-child(2){{text-align:right}}
</style></head><body>
<h1>Relatório – Portfólio (MPT)</h1>
<small>Gerado em {now}</small>
<h2>Resumo</h2>
<table>
<tr><th>Métrica</th><th>Valor</th></tr>
{''.join(lines)}
</table>
<h2>Imagens</h2>
<ul>
<li><a href="{os.path.basename(images['frontier'])}">Fronteira Eficiente (PNG)</a></li>
<li><a href="{os.path.basename(images['growth_maxsharpe'])}">Crescimento – Máx. Sharpe (PNG)</a></li>
<li><a href="{os.path.basename(images['growth_minvar'])}">Crescimento – Mín. Variância (PNG)</a></li>
</ul>
</body></html>"""
    with open(path_html, "w", encoding="utf-8") as f:
        f.write(html)
