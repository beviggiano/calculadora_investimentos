# portfolio/data.py
from __future__ import annotations
import pandas as pd
from typing import Iterable, Optional

def load_prices_csv(path: str, date_col: str = "date", usecols: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """
    Lê um CSV com colunas: date,<ativo1>,<ativo2>,...
    - date: YYYY-MM-DD (ou reconhecível pelo pandas)
    - Preços de fechamento (ou cotações representativas)
    Retorna DataFrame com DateTimeIndex e colunas = ativos, ordenado por data.
    """
    df = pd.read_csv(path, usecols=usecols)
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()
    # remove colunas totalmente vazias e linhas sem nenhum preço
    df = df.dropna(axis=1, how="all").dropna(how="all")
    return df

def to_monthly_last(df_prices: pd.DataFrame) -> pd.DataFrame:
    """
    Reamostra para frequência mensal (último valor do mês).
    Útil quando os preços são diários.
    """
    return df_prices.resample("M").last().dropna(how="all")

def simple_returns(df_prices: pd.DataFrame) -> pd.DataFrame:
    """
    Retornos simples percentuais: r_t = P_t / P_{t-1} - 1
    """
    return df_prices.pct_change().dropna(how="all")

def validate_prices(df_prices: pd.DataFrame) -> None:
    if df_prices.shape[1] < 2:
        raise ValueError("Forneça preços de pelo menos 2 ativos para MPT.")
    if df_prices.isna().any().any():
        # Aceitamos NaN esparsos, mas o ideal é limpar/alinhar previamente
        pass
