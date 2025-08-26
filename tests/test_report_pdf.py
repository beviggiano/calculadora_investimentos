import os, tempfile
from report.report import grafico_png, html_relatorio, pdf_relatorio
from datetime import datetime

def _fake_series():
    return [
        {"nome": "A", "evolucao":[100,110,121], "vf_bruto":121, "vf_liquido":118, "ir_pago":3, "total_investido":100, "prazo_meses":2, "custos_am":0.0},
        {"nome": "B", "evolucao":[100,109,118], "vf_bruto":118, "vf_liquido":116, "ir_pago":2, "total_investido":100, "prazo_meses":2, "custos_am":0.0}
    ]

def test_relatorios_arquivos():
    with tempfile.TemporaryDirectory() as d:
        png = os.path.join(d, "g.png")
        html = os.path.join(d, "r.html")
        pdf  = os.path.join(d, "r.pdf")
        series = _fake_series()
        grafico_png(png, series)
        params = {"n_meses": 2, "vp": 100.0, "pmt": 0.0, "aporte_no_comeco": False}
        market = {"cdi_aa":0.12, "cdi_data":"01/01/2025", "selic_aa":0.12, "selic_data":"01/01/2025",
                  "selic_source":"overnight", "tr_am":0.0, "tr_data":"01/01/2025", "fetch_time": datetime.now().isoformat()}
        html_relatorio(html, params, series, png, os.path.join(d, "x.csv"), market)
        pdf_relatorio(pdf, params, series, png, market)
        assert os.path.exists(png) and os.path.getsize(png) > 0
        assert os.path.exists(html) and os.path.getsize(html) > 0
        assert os.path.exists(pdf) and os.path.getsize(pdf) > 0
