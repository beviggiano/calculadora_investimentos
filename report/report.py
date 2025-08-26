# report/report.py
from __future__ import annotations
import csv, os
from datetime import datetime
from typing import List, Dict
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader

def salvar_csv(csv_path: str, series: List[Dict]) -> None:
    max_len = max(len(s["evolucao"]) for s in series)
    header = ["Mes"] + [f"{s['nome']} (bruto)" for s in series] + [f"{s['nome']} (líquido)" for s in series]
    rows = []
    for mes in range(max_len):
        row = [mes]
        for s in series:
            row.append(round(s["evolucao"][mes], 2) if mes < len(s["evolucao"]) else "")
        for s in series:
            # não temos série mensal líquida; repetimos bruto por mês para referência
            row.append(round(s["evolucao"][mes], 2) if mes < len(s["evolucao"]) else "")
        rows.append(row)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(header); w.writerows(rows)

def grafico_png(png_path: str, series: List[Dict]) -> None:
    plt.figure()
    for s in series:
        plt.plot(s["evolucao"], label=f"{s['nome']} (bruto)")
    plt.title("Evolução (mês a mês) – valores brutos antes do IR")
    plt.xlabel("Meses"); plt.ylabel("Saldo (R$)")
    plt.legend(); plt.tight_layout(); plt.savefig(png_path, dpi=150); plt.close()

def html_relatorio(html_path: str, params: Dict, series: List[Dict], png_path: str, csv_path: str, market: Dict) -> None:
    finais = sorted(series, key=lambda x: x["vf_liquido"], reverse=True)
    def pct(x): return f"{x*100:.4f}%"
    linhas = "".join([
        f"<tr><td>{s['nome']}</td><td>{s['total_investido']:,.2f}</td>"
        f"<td>{s['vf_bruto']:,.2f}</td><td>{s['ir_pago']:,.2f}</td><td><b>{s['vf_liquido']:,.2f}</b></td></tr>"
        for s in finais
    ])
    html = f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8">
<title>Relatório – Calculadora de Investimentos</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;margin:2rem}}
h1,h2{{margin:.3rem 0}} small{{color:#555}}
table{{border-collapse:collapse;width:100%;margin:1rem 0}}
th,td{{border:1px solid #ddd;padding:8px;text-align:right}}
th{{background:#f2f2f2}} td:first-child,th:first-child{{text-align:left}}
blockquote{{background:#fafafa;border-left:4px solid #ccc;padding:.5rem 1rem}}
</style></head><body>
<h1>Relatório – Calculadora de Investimentos</h1>
<small>Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</small>

<h2>Parâmetros</h2>
<table>
<tr><th>Horizonte</th><td>{params['n_meses']} meses</td></tr>
<tr><th>VP</th><td>R$ {params['vp']:.2f}</td></tr>
<tr><th>PMT</th><td>R$ {params['pmt']:.2f}</td></tr>
<tr><th>Aporte no começo?</th><td>{'Sim' if params['aporte_no_comeco'] else 'Não'}</td></tr>
</table>

<h2>Taxas de Mercado (SGS/BCB)</h2>
<table>
<tr><th>CDI (a.a.)</th><td>{pct(market['cdi_aa'])} (ref. {market['cdi_data']})</td></tr>
<tr><th>Selic ({market['selic_source']}) (a.a.)</th><td>{pct(market['selic_aa'])} (ref. {market['selic_data']})</td></tr>
<tr><th>TR (a.m.)</th><td>{pct(market['tr_am'])} (ref. {market['tr_data']})</td></tr>
{"<tr><th>IPCA 12m (a.a.)</th><td>"+pct(market['ipca_aa'])+f" (ref. {market['ipca_data']})</td></tr>" if 'ipca_aa' in market else ""}
<tr><th>Coleta</th><td>{market['fetch_time']}</td></tr>
</table>

<h2>Resultados (com custos + IR no resgate)</h2>
<table>
<tr><th>Aplicação</th><th>Total Investido (R$)</th><th>VF Bruto (R$)</th><th>IR Pago (R$)</th><th>VF Líquido (R$)</th></tr>
{linhas}
</table>

<h2>Gráfico (bruto)</h2>
<img src="{os.path.basename(png_path)}" alt="Gráfico" style="max-width:100%;height:auto"/>

<h2>CSV</h2>
<p><a href="{os.path.basename(csv_path)}">{os.path.basename(csv_path)}</a></p>

<blockquote><b>Notas:</b><br>
1) Custos anuais (admin/custódia) aplicados mês a mês no patrimônio.<br>
2) IR regressivo aplicado sobre rendimentos no resgate, conforme prazo simulado.<br>
3) IPCA 12m é aproximado (produto dos últimos 12 meses). Tesouro IPCA usa taxa real + IPCA 12m para compor taxa nominal anual.</blockquote>
</body></html>"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

def pdf_relatorio(pdf_path: str, params: Dict, series: List[Dict], png_path: str, market: Dict) -> None:
    """
    Gera PDF simples com sumário e o gráfico.
    """
    c = canvas.Canvas(pdf_path, pagesize=A4)
    w, h = A4
    x, y = 2*cm, h - 2*cm

    def draw_line(txt: str, dy=0.6*cm, bold=False):
        nonlocal y
        y -= dy
        if bold:
            c.setFont("Helvetica-Bold", 11)
        else:
            c.setFont("Helvetica", 10)
        c.drawString(x, y, txt)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, "Relatório – Calculadora de Investimentos")
    c.setFont("Helvetica", 9)
    c.drawRightString(w-2*cm, y, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    draw_line(f"Horizonte: {params['n_meses']} meses", dy=1.0*cm)
    draw_line(f"VP: R$ {params['vp']:.2f} | PMT: R$ {params['pmt']:.2f} | Aporte no começo? {'Sim' if params['aporte_no_comeco'] else 'Não'}")

    # Taxas
    draw_line("Taxas de Mercado (SGS/BCB):", bold=True)
    draw_line(f"CDI (a.a.): {market['cdi_aa']*100:.4f}%  (ref. {market['cdi_data']})")
    draw_line(f"Selic ({market['selic_source']}): {market['selic_aa']*100:.4f}%  (ref. {market['selic_data']})")
    draw_line(f"TR (a.m.): {market['tr_am']*100:.4f}%  (ref. {market['tr_data']})")
    if 'ipca_aa' in market:
        draw_line(f"IPCA 12m (a.a.): {market['ipca_aa']*100:.4f}%  (ref. {market['ipca_data']})")

    # Tabela resumida
    draw_line("Resultados (com custos + IR):", dy=0.8*cm, bold=True)
    c.setFont("Helvetica-Bold", 9)
    y -= 0.5*cm
    c.drawString(x, y, "Aplicação")
    c.drawRightString(x+9*cm, y, "Investido")
    c.drawRightString(x+13.5*cm, y, "VF Bruto")
    c.drawRightString(w-2*cm, y, "VF Líquido")

    c.setFont("Helvetica", 9)
    for s in sorted(series, key=lambda k: k["vf_liquido"], reverse=True):
        y -= 0.5*cm
        if y < 6*cm:
            c.showPage()
            y = h - 2*cm
        c.drawString(x, y, s["nome"])
        c.drawRightString(x+9*cm, y, f"R$ {s['total_investido']:,.2f}")
        c.drawRightString(x+13.5*cm, y, f"R$ {s['vf_bruto']:,.2f}")
        c.drawRightString(w-2*cm, y, f"R$ {s['vf_liquido']:,.2f}")

    # Gráfico
    if os.path.exists(png_path):
        c.showPage()
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2*cm, h - 2*cm, "Gráfico – Evolução (bruto)")
        img = ImageReader(png_path)
        # largura útil ~17cm
        img_w = 17*cm
        c.drawImage(img, 2*cm, h - 2*cm - 12*cm, width=img_w, height=12*cm, preserveAspectRatio=True, anchor='n')

    c.save()
