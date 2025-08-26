# app.py
from __future__ import annotations
import io, os, tempfile
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# Módulos do projeto
from services.bcb_api import fetch_market_rates
from finance.tvm import pmt_para_meta, aa_to_am
from finance.products import (
    ProductConfig, taxa_cdb_am, taxa_tesouro_selic_am, taxa_poupanca_am,
    taxa_prefixado_am, taxa_ipca_am
)
from simulate import comparar_series
from report.report import salvar_csv, grafico_png, html_relatorio, pdf_relatorio

# MPT
from portfolio.data import load_prices_csv, to_monthly_last, simple_returns, validate_prices
from portfolio.mpt import MPTInput, max_sharpe, min_variance, efficient_frontier, annualize

st.set_page_config(page_title="Calculadora de Investimentos", layout="wide")

# ===================== helpers =====================
def montar_configs(market: dict, percentual_cdi: float,
                   fee_cdb_aa: float, fee_tes_selic_aa: float, fee_poup_aa: float,
                   fee_prefixado_aa: float, fee_ipca_aa: float,
                   taxa_prefixada_aa: float, taxa_real_ipca_aa: float) -> list[ProductConfig]:
    i_cdb_am = taxa_cdb_am(percentual_cdi, market["cdi_aa"])
    i_tes_selic_am = taxa_tesouro_selic_am(market["selic_aa"])
    i_poup_am = taxa_poupanca_am(market["selic_aa"], market["tr_am"])
    i_prefixado_am = taxa_prefixado_am(taxa_prefixada_aa)
    i_ipca_am = taxa_ipca_am(taxa_real_ipca_aa, market.get("ipca_aa", 0.0))
    return [
        ProductConfig("CDB (% CDI)", i_cdb_am, fee_admin_aa=fee_cdb_aa),
        ProductConfig("Tesouro Selic", i_tes_selic_am, fee_admin_aa=fee_tes_selic_aa),
        ProductConfig("Poupança", i_poup_am, fee_admin_aa=fee_poup_aa, ir_isento=True),
        ProductConfig("Tesouro Prefixado", i_prefixado_am, fee_admin_aa=fee_prefixado_aa),
        ProductConfig("Tesouro IPCA+", i_ipca_am, fee_admin_aa=fee_ipca_aa),
    ]

def df_resultados(series: list[dict]) -> pd.DataFrame:
    rows = []
    for s in series:
        rows.append({
            "Aplicação": s["nome"],
            "Total investido (R$)": s["total_investido"],
            "VF bruto (R$)": s["vf_bruto"],
            "IR pago (R$)": s["ir_pago"],
            "VF líquido (R$)": s["vf_liquido"],
        })
    df = pd.DataFrame(rows).sort_values("VF líquido (R$)", ascending=False)
    return df

def fig_evolucao(series: list[dict]):
    plt.figure()
    for s in series:
        plt.plot(s["evolucao"], label=f"{s['nome']} (bruto)")
    plt.title("Evolução (mês a mês) – valores brutos antes do IR")
    plt.xlabel("Meses"); plt.ylabel("Saldo (R$)")
    plt.legend(); plt.tight_layout()
    return plt.gcf()

# ===================== layout geral =====================
st.title("🧮 Calculadora de Investimentos")
st.caption("Com API SGS/BCB, IR regressivo, custos, relatórios em HTML/CSV/PNG/PDF e MPT (Teoria Moderna do Portfólio).")

with st.sidebar:
    st.header("⚙️ Preferências")
    usar_selic_meta = st.toggle("Usar Selic meta (432) em vez de Selic over (4189)", value=False)
    st.caption("Afeta taxa livre de risco e Tesouro Selic. CDI e TR sempre via SGS.")
    st.divider()
    st.markdown("**Fontes de Mercado (ao vivo):**")
    if st.button("🔄 Atualizar taxas do SGS"):
        st.session_state["_refresh_rates"] = True

# fetch taxas (cache simples por sessão)
if "_market" not in st.session_state or st.session_state.get("_refresh_rates"):
    st.session_state["_market"] = fetch_market_rates(prefer_meta_selic=usar_selic_meta, include_ipca=True)
    st.session_state["_refresh_rates"] = False

market = st.session_state["_market"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("CDI (a.a.)", f"{market['cdi_aa']*100:.2f}%", market["cdi_data"])
col2.metric(f"Selic ({market['selic_source']}) (a.a.)", f"{market['selic_aa']*100:.2f}%", market["selic_data"])
col3.metric("TR (a.m.)", f"{market['tr_am']*100:.3f}%", market["tr_data"])
col4.metric("IPCA 12m (a.a.)", f"{market.get('ipca_aa',0.0)*100:.2f}%", market.get("ipca_data",""))

tabs = st.tabs(["💰 Produtos", "🎯 Meta (PMT)", "📑 Relatórios", "📊 Portfólio (MPT)"])

# ===================== Tab 1: Produtos =====================
with tabs[0]:
    st.subheader("Comparar Produtos")
    with st.form("prod_form"):
        c1, c2, c3, c4 = st.columns(4)
        n_meses = c1.number_input("Horizonte (meses)", min_value=1, value=60, step=1)
        vp = c2.number_input("Valor inicial (VP)", min_value=0.0, value=10000.0, step=100.0)
        pmt = c3.number_input("Aporte mensal (PMT)", min_value=0.0, value=0.0, step=50.0)
        aporte_no_comeco = c4.toggle("Aporte no começo do mês?", value=False)

        c5, c6 = st.columns(2)
        percentual_cdi = c5.number_input("CDB: % do CDI", min_value=0.0, value=110.0, step=5.0)
        # custos anuais
        st.markdown("**Custos anuais (% a.a.)**")
        d1, d2, d3, d4, d5 = st.columns(5)
        fee_cdb_aa = d1.number_input("CDB", min_value=0.0, value=0.0, step=0.001, format="%.3f")
        fee_tes_selic_aa = d2.number_input("Tesouro Selic", min_value=0.0, value=0.0, step=0.001, format="%.3f")
        fee_poup_aa = d3.number_input("Poupança", min_value=0.0, value=0.0, step=0.001, format="%.3f")
        fee_prefixado_aa = d4.number_input("Tesouro Prefixado", min_value=0.0, value=0.0, step=0.001, format="%.3f")
        fee_ipca_aa = d5.number_input("Tesouro IPCA+", min_value=0.0, value=0.0, step=0.001, format="%.3f")

        st.markdown("**Taxas de referência adicionais**")
        e1, e2 = st.columns(2)
        taxa_prefixada_aa = e1.number_input("Tesouro Prefixado (a.a.)", min_value=0.0, value=0.12, step=0.005, format="%.3f")
        taxa_real_ipca_aa = e2.number_input("Tesouro IPCA+ (taxa real a.a.)", min_value=0.0, value=0.06, step=0.005, format="%.3f")

        submitted = st.form_submit_button("Simular comparação")
    if submitted:
        cfgs = montar_configs(market, percentual_cdi, fee_cdb_aa, fee_tes_selic_aa, fee_poup_aa,
                              fee_prefixado_aa, fee_ipca_aa, taxa_prefixada_aa, taxa_real_ipca_aa)
        series = comparar_series(cfgs, n_meses, vp, pmt, aporte_no_comeco)

        st.success("Simulação concluída.")
        st.dataframe(df_resultados(series), use_container_width=True)

        fig = fig_evolucao(series)
        st.pyplot(fig)

# ===================== Tab 2: Meta (PMT) =====================
with tabs[1]:
    st.subheader("Cálculo de PMT para atingir meta")
    with st.form("meta_form"):
        c1, c2, c3 = st.columns(3)
        n_meses_m = c1.number_input("Horizonte (meses)", min_value=1, value=120, step=1)
        vp_m = c2.number_input("Valor inicial (VP)", min_value=0.0, value=20000.0, step=100.0)
        vf_desejado = c3.number_input("Valor futuro desejado", min_value=1.0, value=200000.0, step=500.0)
        aporte_no_comeco_m = st.toggle("Aporte no começo do mês?", value=True)

        base = st.radio("Basear taxa em:", ["Selic (SGS)", "CDB (% do CDI)"], horizontal=True)
        if base == "CDB (% do CDI)":
            percentual_cdi_m = st.number_input("CDB: % do CDI", min_value=0.0, value=110.0, step=5.0)
        submitted_m = st.form_submit_button("Calcular PMT")
    if submitted_m:
        if base == "Selic (SGS)":
            i_am = aa_to_am(market["selic_aa"])
        else:
            i_am = taxa_cdb_am(percentual_cdi_m, market["cdi_aa"])
        pmt = pmt_para_meta(vp_m, i_am, n_meses_m, vf_desejado, aporte_no_comeco_m)
        st.info(f"Taxa de referência: **{i_am*100:.4f}% a.m.**")
        st.success(f"PMT necessário ≈ **R$ {pmt:,.2f}/mês**")

# ===================== Tab 3: Relatórios =====================
with tabs[2]:
    st.subheader("Gerar Relatório (HTML + CSV + PNG + PDF)")
    with st.form("rel_form"):
        c1, c2, c3, c4 = st.columns(4)
        n_meses_r = c1.number_input("Horizonte (meses)", min_value=1, value=60, step=1)
        vp_r = c2.number_input("Valor inicial (VP)", min_value=0.0, value=10000.0, step=100.0)
        pmt_r = c3.number_input("Aporte mensal (PMT)", min_value=0.0, value=0.0, step=50.0)
        aporte_no_comeco_r = c4.toggle("Aporte no começo do mês?", value=False)

        c5, c6 = st.columns(2)
        percentual_cdi_r = c5.number_input("CDB: % do CDI", min_value=0.0, value=110.0, step=5.0)

        st.markdown("**Custos anuais (% a.a.)**")
        d1, d2, d3, d4, d5 = st.columns(5)
        fee_cdb_r = d1.number_input("CDB", min_value=0.0, value=0.0, step=0.001, format="%.3f")
        fee_selic_r = d2.number_input("Tesouro Selic", min_value=0.0, value=0.0, step=0.001, format="%.3f")
        fee_poup_r = d3.number_input("Poupança", min_value=0.0, value=0.0, step=0.001, format="%.3f")
        fee_pref_r = d4.number_input("Tesouro Prefixado", min_value=0.0, value=0.0, step=0.001, format="%.3f")
        fee_ipca_r = d5.number_input("Tesouro IPCA+", min_value=0.0, value=0.0, step=0.001, format="%.3f")

        st.markdown("**Taxas de referência**")
        e1, e2 = st.columns(2)
        taxa_pref_r = e1.number_input("Prefixado (a.a.)", min_value=0.0, value=0.12, step=0.005, format="%.3f")
        taxa_real_ipca_r = e2.number_input("IPCA+ (real a.a.)", min_value=0.0, value=0.06, step=0.005, format="%.3f")

        submitted_r = st.form_submit_button("Gerar e baixar arquivos")
    if submitted_r:
        cfgs = montar_configs(market, percentual_cdi_r, fee_cdb_r, fee_selic_r, fee_poup_r,
                              fee_pref_r, fee_ipca_r, taxa_pref_r, taxa_real_ipca_r)
        series = comparar_series(cfgs, n_meses_r, vp_r, pmt_r, aporte_no_comeco_r)

        # gerar arquivos em pasta temporária e oferecer downloads
        with tempfile.TemporaryDirectory() as tmp:
            base = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = os.path.join(tmp, f"evolucao_{base}.csv")
            png_path = os.path.join(tmp, f"grafico_{base}.png")
            html_path = os.path.join(tmp, f"relatorio_{base}.html")
            pdf_path = os.path.join(tmp, f"relatorio_{base}.pdf")

            salvar_csv(csv_path, series)
            grafico_png(png_path, series)
            params = dict(n_meses=n_meses_r, vp=vp_r, pmt=pmt_r, aporte_no_comeco=aporte_no_comeco_r)
            html_relatorio(html_path, params, series, png_path, csv_path, market)
            pdf_relatorio(pdf_path, params, series, png_path, market)

            # ler bytes
            csv_bytes = open(csv_path, "rb").read()
            png_bytes = open(png_path, "rb").read()
            html_bytes = open(html_path, "rb").read()
            pdf_bytes = open(pdf_path, "rb").read()

        st.success("Relatórios gerados!")
        cdl1, cdl2, cdl3, cdl4 = st.columns(4)
        cdl1.download_button("⬇️ CSV", data=csv_bytes, file_name=f"evolucao_{base}.csv", mime="text/csv")
        cdl2.download_button("⬇️ PNG", data=png_bytes, file_name=f"grafico_{base}.png", mime="image/png")
        cdl3.download_button("⬇️ HTML", data=html_bytes, file_name=f"relatorio_{base}.html", mime="text/html")
        cdl4.download_button("⬇️ PDF", data=pdf_bytes, file_name=f"relatorio_{base}.pdf", mime="application/pdf")

        st.dataframe(df_resultados(series), use_container_width=True)
        st.pyplot(fig_evolucao(series))

# ===================== Tab 4: MPT =====================
with tabs[3]:
    st.subheader("Teoria Moderna do Portfólio (MPT)")
    up = st.file_uploader("Envie um CSV de preços (colunas: date, ATIVO1, ATIVO2, ...)", type=["csv"])
    if up:
        try:
            prices = pd.read_csv(up)
            prices["date"] = pd.to_datetime(prices["date"])
            prices = prices.set_index("date").sort_index()
            st.write("Prévia dos dados:", prices.head())
        except Exception as e:
            st.error(f"Erro ao ler CSV: {e}")
            prices = None
    else:
        prices = None

    if prices is not None:
        usar_diario_p = st.toggle("Séries diárias? (converter para último de cada mês)", value=True)
        permitir_short = st.toggle("Permitir short (pesos negativos)?", value=False)
        bounds = (-1.0, 1.0) if permitir_short else (0.0, 1.0)

        if usar_diario_p:
            prices = to_monthly_last(prices)

        rets = simple_returns(prices).dropna()
        if rets.shape[1] < 2:
            st.warning("Envie preços de pelo menos 2 ativos.")
        else:
            names = list(rets.columns)
            mu_m = rets.mean().values.astype(float)
            Sigma_m = np.cov(rets.values.T)
            if np.min(np.linalg.eigvals(Sigma_m)) < 0:
                Sigma_m = Sigma_m + 1e-10*np.eye(Sigma_m.shape[0])

            rf_m = aa_to_am(market["selic_aa"])
            inp = MPTInput(mu_m=mu_m, Sigma_m=Sigma_m, names=names,
                           rf_m=rf_m, bounds=tuple(bounds for _ in names))

            with st.spinner("Otimizando carteiras..."):
                sol_max = max_sharpe(inp)
                sol_min = min_variance(inp)
                df_front = efficient_frontier(inp, n_pts=40)

            ra_max, va_max = annualize(sol_max["ret_m"], sol_max["vol_m"])
            ra_min, va_min = annualize(sol_min["ret_m"], sol_min["vol_m"])

            # gráficos
            # fronteira
            plt.figure()
            if not df_front.empty:
                plt.plot(df_front["vol_m"], df_front["ret_m"], linestyle="-", marker="")
            plt.scatter([sol_max["vol_m"]], [sol_max["ret_m"]], label="Máx. Sharpe")
            plt.scatter([sol_min["vol_m"]], [sol_min["ret_m"]], label="Mín. Variância")
            plt.xlabel("Vol mensal"); plt.ylabel("Ret mensal")
            plt.title("Fronteira Eficiente (Mensal)")
            plt.legend(); plt.tight_layout()
            st.pyplot(plt.gcf())

            # crescimento de R$1 para as duas carteiras
            def plot_growth(weights, label):
                plt.figure()
                w = np.array(weights).reshape(-1, 1)
                port_r = rets.fillna(0.0).values @ w
                port_r = pd.Series(port_r.ravel(), index=rets.index)
                growth = (1.0 + port_r).cumprod()
                plt.plot(growth.index, growth.values, label=label)
                plt.xlabel("Tempo"); plt.ylabel("Crescimento de R$1")
                plt.title(f"Crescimento – {label}")
                plt.legend(); plt.tight_layout()
                st.pyplot(plt.gcf())

            plot_growth(sol_max["w"], "Máx. Sharpe")
            plot_growth(sol_min["w"], "Mín. Variância")

            st.markdown("### Pesos e métricas")
            cA, cB = st.columns(2)
            cA.write("**Máx. Sharpe**")
            cA.write(pd.DataFrame({"Ativo": names, "Peso": sol_max["w"]}))
            cA.info(f"Ret (a.a.): {ra_max*100:.2f}% | Vol (a.a.): {va_max*100:.2f}% | Sharpe (m): {sol_max['sharpe_m']:.3f}")

            cB.write("**Mín. Variância**")
            cB.write(pd.DataFrame({"Ativo": names, "Peso": sol_min["w"]}))
            cB.info(f"Ret (a.a.): {ra_min*100:.2f}% | Vol (a.a.): {va_min*100:.2f}% | Sharpe (m): {sol_min['sharpe_m']:.3f}")

            # downloads simples dos resultados
            res = {
                "Ativos": ", ".join(names),
                "rf (Selic) mensal": rf_m,
                "Máx. Sharpe (m)": sol_max["sharpe_m"],
                "Máx. Sharpe – Ret (a.a.)": ra_max,
                "Máx. Sharpe – Vol (a.a.)": va_max,
                "Mín. Variância – Ret (a.a.)": ra_min,
                "Mín. Variância – Vol (a.a.)": va_min,
                "Pesos Máx. Sharpe": ", ".join([f"{n}={w:.3f}" for n,w in zip(names, sol_max["w"])]),
                "Pesos Mín. Variância": ", ".join([f"{n}={w:.3f}" for n,w in zip(names, sol_min["w"])]),
            }
            csv_buf = io.StringIO()
            pd.DataFrame([res]).to_csv(csv_buf, index=False)
            st.download_button("⬇️ Baixar resumo (CSV)", data=csv_buf.getvalue(), file_name="portfolio_summary.csv", mime="text/csv")
