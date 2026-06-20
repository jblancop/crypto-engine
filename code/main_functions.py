from code.exchanges.bitunix import Bitunix
from code.exchanges.bitvavo import Bitvavo
from code.exchanges.kraken import Kraken
from code.exchanges.okx import Okx
from code.aux_functions import build_candles_url, execute_api_request
from code.divergence_functions import (
    add_slope_information, add_volume_information, check_divergence, check_low_pivots, 
    compute_rsi, find_bullish_divergence, find_low_pivots, format_timestamps, 
    get_aux_data_structures
)
from typing import Any
import pandas as pd


def get_candles(pair: str, timeframe: str, cfg: dict[str, dict[str, Any]]) -> pd.DataFrame:
    '''
    Envoltorio que devuelve la información de mercado para una plataforma.

    Parámetros:
    + pair: El par del que se quiere obtener información.
    + timeframe: El marco temporal en el que se quiere operar.
    + cfg: El diccionario de configuración.

    Retorno:
    + Un DF con la información de mercado.
    '''
    # Plataforma:
    exchange = globals().get(cfg['this']['class_name'])
    # Variables:
    api_batch = cfg['this']['api_batch']
    api_fields = cfg['this']['api_fields']['candles']
    candles_url = build_candles_url(pair, cfg)
    df_fields = cfg['all']['df_fields']['candles']
    # Tubería:
    candles_params = exchange.set_params(pair, timeframe, api_batch)
    candles_json = execute_api_request(candles_url, candles_params)
    candles_df = exchange.parse_candles(candles_json, api_fields, df_fields)

    return candles_df


def get_divergence(candles_df: pd.DataFrame, cfg: dict[str, dict[str, Any]]) -> dict[str, Any]:
    '''
    Envoltorio que devuelve la información sobre la divergencia para un elemento de mercado par/intervalo.

    Parámetros:
    + candles_df: El DF con la información de mercado.
    + cfg: El diccionario de configuración.

    Retorno:
    + Un diccionario con información sobre la divergencia.
    '''
    #Variables:
    api_batch = min(len(candles_df), cfg['this']['api_batch']) #A veces la API no devuelve tantas velas como se supone.
    pivot_limit = api_batch - cfg['all']['candle_range']
    min_strength = cfg['all']['min_strength']
    pivot_window = cfg['all']['pivot_window']
    rsi_period = cfg['all']['rsi_period']
    #Tubería:
    candles_df['rsi'] = compute_rsi(candles_df['close'], rsi_period)
    low_pivots_idx = find_low_pivots(candles_df['low'], pivot_window)
    bool_check = check_low_pivots(low_pivots_idx, pivot_limit)

    if not bool_check: return None

    divergence_df, vol_series = get_aux_data_structures(candles_df, low_pivots_idx)
    divergence = find_bullish_divergence(divergence_df)

    if divergence:

        divergence = add_slope_information(divergence, candles_df, pivot_window)
        divergence = add_volume_information(divergence, vol_series)
        divergence = format_timestamps(divergence)
        bool_check = check_divergence(divergence, min_strength)

        if bool_check: return divergence
    
    return None


def get_pairs(cfg: dict[str, dict[str, Any]]) -> set[str]:
    '''
    Envoltorio que devuelve los pares de mercado para una plataforma.

    Parámetro:
    + cfg: El diccionario de configuración.

    Retorno:
    + Un conjunto con los pares.
    '''
    # Plataforma:
    exchange = globals().get(cfg['this']['class_name'])
    # Variables:
    pairs_url = f"{cfg['this']['api_url']}/{cfg['this']['endpoint']['pairs']}"
    pairs_params = cfg['this'].get('pairs_params') #Este parámetro sólo es necesario en OKX.
    # Tubería:
    pairs_json = execute_api_request(pairs_url, pairs_params)
    pairs_set = exchange.parse_pairs(pairs_json)

    return pairs_set