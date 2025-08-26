import os
import pytest
from services.bcb_api import fetch_market_rates, get_ipca_12m

pytestmark = pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1",
                                reason="Defina RUN_INTEGRATION=1 para rodar testes de integração")

def test_fetch_market_rates_ok():
    m = fetch_market_rates(prefer_meta_selic=False, include_ipca=True)
    assert 0 < m["cdi_aa"] < 1
    assert 0 < m["selic_aa"] < 1
    assert isinstance(m["cdi_data"], str)
    assert isinstance(m["selic_data"], str)
    assert "ipca_aa" in m and -0.05 < m["ipca_aa"] < 1.0  # ampla margem

def test_ipca_12m_ok():
    ipca_aa, data = get_ipca_12m()
    assert -0.05 < ipca_aa < 1.0
    assert isinstance(data, str)
