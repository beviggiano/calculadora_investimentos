# main.py
from __future__ import annotations
import os
from datetime import datetime

# --- Simuladores de produtos e relatórios ---
from services.bcb_api import fetch_market_rates
from finance.tvm import pmt_para_meta, aa_to_am
from finance.products import (
    ProductConfig, taxa_cdb_am, taxa_tesouro_selic_am, taxa_poupanca_am,
    taxa_prefixado_am, taxa_ipca_am
)
from simulate import comparar_series
from report.report import salvar_csv, grafico_png, html_relatorio, pdf_relatorio

# --- MPT (Teoria Moderna do Portfólio) ---
import numpy as np
import pandas as pd
from portfolio.data import load_prices_csv, to_monthly_last, simple_returns, validate_prices
from portfolio.mpt import MPTInput, max_sharpe, min_variance, efficient_frontier, annualize
from report.portfolio_report import plot_frontier_png, plot_growth_png, save_portfolio_html


# =========================
# Helpers de entrada
# =========================
def _input_float(msg: str, default: float) -> float:
    raw = input(f"{msg} [{default}]: ").strip()
    return float(raw.replace(",", ".") or default)

def _input_int(msg: str, default: int) -> int:
    raw = input(f"{msg} [{default}]: ").strip()
    return int(raw or default)

def _input_bool(msg: str, default: bool=False) -> bool:
    raw = input(f"{msg} [{'s' if default else 'n'}]: ").strip().lower()
    if raw == "": 
        return default
    return raw.startswith("s")


# =========================
# Menu
# =========================
def menu():
    print("\n=== Calculadora de Investimentos (API SGS/BCB + IR/Custos + PDF + MPT) ===")
    print("1) Comparar CDB x Tesouro Selic x Poupança x Prefixado x IPCA")
    print("2) Descobrir PMT para meta (usando taxa real)")
    print("3) Relatório completo (HTML + CSV + PNG + PDF)")
    print("4) Portfólio (MPT): carregar CSV de preços e otimizar")
    print("0) Sair")


# =========================
# Montagem de configurações de produtos
# =========================
def montar_configs(market: dict, percentual_cdi: float,
                   fee_cdb_aa: float, fee_tes_selic_aa: float, fee_poup_aa: float,
                   fee_prefixado_aa: float, fee_ipca_aa: float,
                   taxa_prefixada_aa: float, taxa_real_ipca_aa: float) -> list[ProductConfig]:
    # taxas mensais brutas
    i_cdb_am = taxa_cdb_am(percentual_cdi, market["cdi_aa"])
    i_tes_selic_am = taxa_tesouro_selic_am(market["selic_aa"])
    i_poup_am = taxa_poupanca_am(market["selic_aa"], market["tr_am"])
    i_prefixado_am = taxa_prefixado_am(taxa_prefixada_aa)
    i_ipca_am = taxa_ipca_am(taxa_real_ipca_aa, market.get("ipca_aa", 0.0))

    # configs (custódia/admin podem ser ajustadas; por padrão 0)
    cfgs = [
        ProductConfig("CDB (% CDI)", i_cdb_am, fee_admin_aa=fee_cdb_aa),
        ProductConfig("Tesouro Selic", i_tes_selic_am, fee_admin_aa=fee_tes_selic_aa),
        ProductConfig("Poupança", i_poup_am, fee_admin_aa=fee_poup_aa, ir_isento=True),
        ProductConfig("Tesouro Prefixado", i_prefixado_am, fee_admin_aa=fee_prefixado_aa),
        ProductConfig("Tesouro IPCA+", i_ipca_am, fee_admin_aa=fee_ipca_aa),
    ]
    return cfgs


# =========================
# Ações do menu
# =========================
def acao_comparar():
    print("\n-- Parâmetros --")
    n_meses = _input_int("Horizonte (meses)", 60)
    vp = _input_float("Valor inicial (VP)", 10000.0)
    pmt = _input_float("Aporte mensal (PMT)", 0.0)
    aporte_no_comeco = _input_bool("Aportar no começo do mês?", False)
    percentual_cdi = _input_float("CDB: % do CDI", 110.0)
    usar_selic_meta = _input_bool("Usar Selic meta (432) em vez de Selic over (4189)?", False)

    # custos anuais (% a.a.) – ajuste conforme sua corretora/plataforma
    fee_cdb_aa = _input_float("Custo anual CDB (admin/corretagem) a.a.", 0.0)
    fee_tes_selic_aa = _input_float("Custo anual Tesouro Selic (custódia/admin) a.a.", 0.0)
    fee_poup_aa = _input_float("Custo anual Poupança a.a.", 0.0)
    fee_prefixado_aa = _input_float("Custo anual Tesouro Prefixado a.a.", 0.0)
    fee_ipca_aa = _input_float("Custo anual Tesouro IPCA+ a.a.", 0.0)

    # taxas de referência para Prefixado e IPCA+
    taxa_prefixada_aa = _input_float("Tesouro Prefixado: taxa anual de referência (ex.: 0.12 = 12%)", 0.12)
    taxa_real_ipca_aa = _input_float("Tesouro IPCA+: taxa real anual (ex.: 0.06 = 6%)", 0.06)

    market = fetch_market_rates(prefer_meta_selic=usar_selic_meta, include_ipca=True)
    cfgs = montar_configs(market, percentual_cdi, fee_cdb_aa, fee_tes_selic_aa, fee_poup_aa,
                          fee_prefixado_aa, fee_ipca_aa, taxa_prefixada_aa, taxa_real_ipca_aa)

    series = comparar_series(cfgs, n_meses, vp, pmt, aporte_no_comeco)
    print("\nResultados (VF Líquido):")
    for s in sorted(series, key=lambda x: x["vf_liquido"], reverse=True):
        print(f"- {s['nome']}: Investido=R$ {s['total_investido']:,.2f} | IR=R$ {s['ir_pago']:,.2f} | VF Líquido=R$ {s['vf_liquido']:,.2f}")


def acao_meta():
    print("\n-- Meta (PMT necessário) --")
    n_meses = _input_int("Horizonte (meses)", 60)
    vp = _input_float("Valor inicial (VP)", 0.0)
    vf_desejado = _input_float("Valor futuro desejado", 50000.0)
    aporte_no_comeco = _input_bool("Aportar no começo do mês?", False)

    usar_selic_meta = _input_bool("Basear na Selic meta (432)? (senão usa CDB % CDI)", True)
    if usar_selic_meta:
        i_am = aa_to_am(fetch_market_rates(prefer_meta_selic=True, include_ipca=False)["selic_aa"])
    else:
        percentual_cdi = _input_float("Se usar CDI: % do CDI (ex.: 110)", 110.0)
        market = fetch_market_rates(prefer_meta_selic=False, include_ipca=False)
        i_am = taxa_cdb_am(percentual_cdi, market["cdi_aa"])

    pmt = pmt_para_meta(vp, i_am, n_meses, vf_desejado, aporte_no_comeco)
    print(f"\nTaxa de referência: {i_am*100:.4f}% a.m.")
    print(f"PMT necessário ≈ R$ {pmt:,.2f}/mês para atingir R$ {vf_desejado:,.2f} em {n_meses} meses.")


def acao_relatorio():
    print("\n-- Relatório completo --")
    n_meses = _input_int("Horizonte (meses)", 60)
    vp = _input_float("Valor inicial (VP)", 10000.0)
    pmt = _input_float("Aporte mensal (PMT)", 0.0)
    aporte_no_comeco = _input_bool("Aportar no começo do mês?", False)
    percentual_cdi = _input_float("CDB: % do CDI", 110.0)
    usar_selic_meta = _input_bool("Usar Selic meta (432) em vez de Selic over (4189)?", False)

    fee_cdb_aa = _input_float("Custo anual CDB (admin/corretagem) a.a.", 0.0)
    fee_tes_selic_aa = _input_float("Custo anual Tesouro Selic (custódia/admin) a.a.", 0.0)
    fee_poup_aa = _input_float("Custo anual Poupança a.a.", 0.0)
    fee_prefixado_aa = _input_float("Custo anual Tesouro Prefixado a.a.", 0.0)
    fee_ipca_aa = _input_float("Custo anual Tesouro IPCA+ a.a.", 0.0)

    taxa_prefixada_aa = _input_float("Tesouro Prefixado: taxa anual de referência (ex.: 0.12 = 12%)", 0.12)
    taxa_real_ipca_aa = _input_float("Tesouro IPCA+: taxa real anual (ex.: 0.06 = 6%)", 0.06)

    market = fetch_market_rates(prefer_meta_selic=usar_selic_meta, include_ipca=True)
    cfgs = montar_configs(market, percentual_cdi, fee_cdb_aa, fee_tes_selic_aa, fee_poup_aa,
                          fee_prefixado_aa, fee_ipca_aa, taxa_prefixada_aa, taxa_real_ipca_aa)
    series = comparar_series(cfgs, n_meses, vp, pmt, aporte_no_comeco)

    outdir = "saida_relatorio"
    os.makedirs(outdir, exist_ok=True)
    base = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(outdir, f"evolucao_{base}.csv")
    png_path = os.path.join(outdir, f"grafico_{base}.png")
    html_path = os.path.join(outdir, f"relatorio_{base}.html")
    pdf_path = os.path.join(outdir, f"relatorio_{base}.pdf")

    salvar_csv(csv_path, series)
    grafico_png(png_path, series)
    params = dict(n_meses=n_meses, vp=vp, pmt=pmt, aporte_no_comeco=aporte_no_comeco)
    html_relatorio(html_path, params, series, png_path, csv_path, market)
    pdf_relatorio(pdf_path, params, series, png_path, market)

    print("\nArquivos gerados:")
    print(f"• CSV:  {csv_path}")
    print(f"• PNG:  {png_path}")
    print(f"• HTML: {html_path}")
    print(f"• PDF:  {pdf_path}")


def acao_portfolio_mpt():
    print("\n-- Portfólio (MPT) --")
    csv_path = input("Caminho do CSV de preços (date, ativo1, ativo2, ...): ").strip()
    if not csv_path:
        print("Informe um caminho de arquivo CSV.")
        return

    usar_diario = _input_bool("As séries estão diárias (converter para mensal)?", True)
    permitir_short = _input_bool("Permitir venda a descoberto (short)?", False)
    bound_low = -1.0 if permitir_short else 0.0
    bound_high = 1.0
    print("A taxa livre de risco virá da Selic (SGS).")
    usar_selic_meta = _input_bool("Usar Selic meta (432) em vez da Selic over (4189)?", False)

    # Carregar preços
    try:
        prices = load_prices_csv(csv_path)
        validate_prices(prices)
        if usar_diario:
            prices = to_monthly_last(prices)
    except Exception as e:
        print(f"Erro ao carregar preços: {e}")
        return

    # Retornos mensais
    rets = simple_returns(prices).dropna()
    names = list(rets.columns)
    if len(names) < 2:
        print("Forneça pelo menos 2 ativos para otimizar um portfólio.")
        return

    mu_m = rets.mean().values.astype(float)             # média mensal (simples)
    Sigma_m = np.cov(rets.values.T)                     # covariância mensal
    if np.min(np.linalg.eigvals(Sigma_m)) < 0:
        Sigma_m = Sigma_m + 1e-10 * np.eye(Sigma_m.shape[0])  # robustez numérica

    # Taxa livre de risco mensal (Selic)
    market = fetch_market_rates(prefer_meta_selic=usar_selic_meta, include_ipca=False)
    rf_m = aa_to_am(market["selic_aa"])

    bounds = tuple((bound_low, bound_high) for _ in names)
    inp = MPTInput(mu_m=mu_m, Sigma_m=Sigma_m, names=names, rf_m=rf_m, bounds=bounds)

    # Soluções
    sol_max = max_sharpe(inp)
    sol_min = min_variance(inp)
    df_frontier = efficient_frontier(inp, n_pts=40)

    # Annualização para exibir
    ret_a_max, vol_a_max = annualize(sol_max["ret_m"], sol_max["vol_m"])
    ret_a_min, vol_a_min = annualize(sol_min["ret_m"], sol_min["vol_m"])

    # Saídas
    outdir = "saida_portfolio"
    os.makedirs(outdir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    png_frontier = os.path.join(outdir, f"frontier_{ts}.png")
    png_gmax = os.path.join(outdir, f"growth_maxsharpe_{ts}.png")
    png_gmin = os.path.join(outdir, f"growth_minvar_{ts}.png")
    html_path = os.path.join(outdir, f"portfolio_{ts}.html")

    # Gráficos (sem estilos/cores específicas; 1 gráfico por figura)
    plot_frontier_png(png_frontier, df_frontier, sol_max, sol_min)
    plot_growth_png(png_gmax, rets, sol_max["w"], "Máx. Sharpe")
    plot_growth_png(png_gmin, rets, sol_min["w"], "Mín. Variância")

    # HTML simples com resumo
    summary = {
        "Ativos": ", ".join(names),
        "rf (Selic) mensal": rf_m,
        "Máx. Sharpe (m)": sol_max["sharpe_m"],
        "Máx. Sharpe – Ret (a.a.)": ret_a_max,
        "Máx. Sharpe – Vol (a.a.)": vol_a_max,
        "Mín. Variância – Ret (a.a.)": ret_a_min,
        "Mín. Variância – Vol (a.a.)": vol_a_min,
        "Pesos Máx. Sharpe": ", ".join([f"{n}={w:.3f}" for n, w in zip(names, sol_max["w"])]),
        "Pesos Mín. Variância": ", ".join([f"{n}={w:.3f}" for n, w in zip(names, sol_min["w"])]),
    }
    save_portfolio_html(html_path, summary, {
        "frontier": png_frontier,
        "growth_maxsharpe": png_gmax,
        "growth_minvar": png_gmin
    })

    print("\nPortfólio (MPT) – resultados:")
    print(f"- rf mensal (Selic): {rf_m*100:.4f}%")
    print(f"- Máx. Sharpe: retorno(a.a.)={ret_a_max*100:.2f}% | vol(a.a.)={vol_a_max*100:.2f}%")
    print("  Pesos:", ", ".join([f"{n}={w:.3f}" for n, w in zip(names, sol_max["w"])]))
    print(f"- Mín. Variância: retorno(a.a.)={ret_a_min*100:.2f}% | vol(a.a.)={vol_a_min*100:.2f}%")
    print("  Pesos:", ", ".join([f"{n}={w:.3f}" for n, w in zip(names, sol_min["w"])]))

    print("\nArquivos gerados:")
    print("• Fronteira:", png_frontier)
    print("• Crescimento (Máx. Sharpe):", png_gmax)
    print("• Crescimento (Mín. Variância):", png_gmin)
    print("• HTML:", html_path)


# =========================
# Loop principal
# =========================
def main():
    while True:
        menu()
        op = input("Escolha: ").strip()
        if op == "1":
            acao_comparar()
        elif op == "2":
            acao_meta()
        elif op == "3":
            acao_relatorio()
        elif op == "4":
            acao_portfolio_mpt()
        elif op == "0":
            print("Até mais!")
            break
        else:
            print("Opção inválida.")


if __name__ == "__main__":
    main()
