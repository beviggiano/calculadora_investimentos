from finance.taxes import aliquota_ir_por_dias, annual_to_monthly_fee

def test_aliquota_ir_regressiva():
    assert aliquota_ir_por_dias(90) == 0.225
    assert aliquota_ir_por_dias(200) == 0.20
    assert aliquota_ir_por_dias(500) == 0.175
    assert aliquota_ir_por_dias(1000) == 0.15

def test_fee_aa_para_am():
    am = annual_to_monthly_fee(0.12)  # ~0.9489% a.m.
    assert 0.009 < am < 0.010
