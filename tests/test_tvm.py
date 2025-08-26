import math
from finance.tvm import aa_to_am, am_to_aa, vf_simples, vf_compostos, vp_compostos, vf_serie_pmt, pmt_para_meta

def test_conversoes_taxa_roundtrip():
    aa = 0.12
    am = aa_to_am(aa)
    back = am_to_aa(am)
    assert abs(back - aa) < 1e-10

def test_vf_simples():
    assert vf_simples(1000, 0.02, 12) == 1000 * (1 + 0.02*12)

def test_vf_compostos():
    assert vf_compostos(1000, 0.02, 12) == 1000 * ((1+0.02)**12)

def test_vp_compostos():
    vf = 1210
    vp = vp_compostos(vf, 0.1, 2)
    assert abs(vp * (1.1**2) - vf) < 1e-9

def test_vf_serie_pmt_postecipada():
    vf = vf_serie_pmt(0.01, 12, 100, aporte_no_comeco=False)
    assert abs(vf - 100 * (((1.01)**12 - 1)/0.01)) < 1e-9

def test_vf_serie_pmt_antecipada():
    vf = vf_serie_pmt(0.01, 12, 100, aporte_no_comeco=True)
    assert abs(vf - 100 * (((1.01)**12 - 1)/0.01) * 1.01) < 1e-9

def test_pmt_para_meta():
    vp, i, n, vf_d = 10000, 0.01, 12, 30000
    pmt = pmt_para_meta(vp, i, n, vf_d, aporte_no_comeco=False)
    vf_total = vf_compostos(vp, i, n) + vf_serie_pmt(i, n, pmt, False)
    assert abs(vf_total - vf_d) < 1e-6
