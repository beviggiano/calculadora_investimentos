from finance.products import taxa_poupanca_am, taxa_cdb_am, taxa_ipca_am
from finance.tvm import aa_to_am

def test_poupanca_regra():
    # Selic alta -> 0,5% a.m. + TR
    assert abs(taxa_poupanca_am(0.1, 0.0) - 0.005) < 1e-12
    # Selic baixa -> ~ 70% Selic/12
    t = taxa_poupanca_am(0.06, 0.0)
    assert abs(t - (0.70 * 0.06)/12) < 1e-12

def test_cdb_percentual_cdi():
    cdi_aa = 0.12
    i_am = taxa_cdb_am(110, cdi_aa)
    assert abs(i_am - aa_to_am(0.12)*1.10) < 1e-12

def test_taxa_ipca_composicao():
    taxa_real_aa = 0.06
    ipca_aa = 0.04
    i_am = taxa_ipca_am(taxa_real_aa, ipca_aa)
    # nominal anual esperado
    nominal_aa = (1+0.06)*(1+0.04) - 1
    from math import isclose
    # checa conversão para mensal
    assert isclose(i_am, (1+nominal_aa)**(1/12)-1, rel_tol=1e-12)
