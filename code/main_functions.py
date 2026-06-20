from code.exchanges.bitunix import Bitunix
from code.exchanges.kraken import Kraken
from code.exchanges.okx import OKX
from code.aux_functions import execute_api_request
from code.divergence_functions import (
    add_slope_information, add_volume_information, check_divergence, check_low_pivots, 
    compute_rsi, find_bullish_divergence_by_low_pivots, find_low_pivots, format_timestamps, 
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
    candles_url = f"{cfg['this']['api_url']}/{cfg['this']['endpoint']['candles']}"
    df_fields = cfg['all']['df_fields']['candles']
    # Tubería:
    candles_params = exchange.set_params(pair, timeframe, api_batch)
    candles_json = execute_api_request(candles_url, candles_params)
    candles_df = exchange.parse_candles(candles_json, api_fields, df_fields)

    return candles_df


def get_divergence(candles_df: pd.DataFrame, std_timeframe: str, cfg: dict[str, dict[str, Any]]) -> dict[str, Any]:
    '''
    Envoltorio que devuelve la información sobre la divergencia para un elemento de mercado par/intervalo.

    Parámetros:
    + candles_df: El DF con la información de mercado.
    + std_timeframe: El marco temporal normalizado en el que se está operando.
    + cfg: El diccionario de configuración.

    Retorno:
    + Un diccionario con información sobre la divergencia.
    '''
    #Variables:
    narrow_candle_range = cfg['this']['api_batch'] - cfg['all']['narrow_candles']
    wide_candle_range = cfg['this']['api_batch'] - cfg['all']['wide_candles']
    min_strength = cfg['all']['min_strength']
    pivot_window = cfg['all']['pivot_window']
    rsi_period = cfg['all']['rsi_period']
    slope_batch = pivot_window * 2
    #Tubería:
    candles_df['rsi'] = compute_rsi(candles_df['close'], rsi_period)
    pivots = find_low_pivots(candles_df['low'], pivot_window, std_timeframe)
    result = check_low_pivots(pivots, std_timeframe, narrow_candle_range, wide_candle_range)
    
    if not result: return None

    divergence_df, vol_series = get_aux_data_structures(candles_df, pivots)
    divergence = find_bullish_divergence_by_low_pivots(divergence_df)

    if divergence:

        divergence = add_slope_information(divergence, candles_df, slope_batch)
        divergence = add_volume_information(divergence, vol_series)
        divergence = format_timestamps(divergence)
        result = check_divergence(divergence, min_strength, std_timeframe)

        if result: return divergence
    
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