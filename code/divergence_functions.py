from typing import Any
import numpy as np
import pandas as pd


def add_slope_information(divergence: dict[str, Any], candles_df: pd.DataFrame, slope_batch: int) -> dict[str, Any]:
    '''
    Estima la fuerza de la divergencia mediante la comparación de la pendiente del precio y del RSI, que han de ser opuestas.

    Parámetros:
    + divergence: El diccionario con información de la divergencia.
    + candles_df: El DF con la información de mercado.
    + slope_batch: Número de velas utilizadas en cada iteración.

    Retorno:
    + La divergencia (con información adicional).
    '''
    candles_df = candles_df.sort_index(ascending=False) #El DF se pasa invertido para empezar el análisis por los registros más recientes.

    condition = True
    start = 0 #Inicio del lote
    end = slope_batch #y fin.
    slope_candles = 0 #Cuántas velas consecutivas muestran divergencia de pendientes entre el precio y el RSI.
    x = np.arange(slope_batch) #Eje X: Serie numérica con tantos valores como velas se analizan en cada iteración.

    while condition:

        y_price = candles_df['low'].iloc[start:end] #Eje Y: Serie de valores del precio para cada iteración.
        price_slope = np.polyfit(x, y_price, 1)[0] #Cálculo de la pendiente por regresión lineal.

        y_rsi = candles_df['rsi'].iloc[start:end] #Lo mismo pero para el RSI.
        rsi_slope = np.polyfit(x, y_rsi, 1)[0]

        condition = price_slope > 0 and rsi_slope < 0 #Dada la inversión del DF, una pendiente del precio positiva indica que disminuye.

        if condition: 
            divergence['strength'] += 1
            slope_candles += slope_batch

        start += slope_batch #Si el bucle continúa, en la siguiente iteración se analizará el siguiente lote de velas.
        end += slope_batch
    
    if slope_candles > 0:
        divergence['slope_candles'] = slope_candles
    
    return divergence


def add_volume_information(divergence: dict[str, Any], vol_series: pd.Series) -> dict[str, Any]:
    '''
    Añade información sobre el volumen a la divergencia.

    Parámetros:
    + divergence: La divergencia sin información de volumen.
    + vol_series: Una serie con el volumen de activo de todos los mínimos detectados.

    Retorno:
    + La divergencia enriquecida.
    '''
    timestamps = divergence['pivot_timestamps']

    vol_ratios = calculate_volume_ratios(vol_series, timestamps)
    latest_ratio = vol_ratios[-1]

    if latest_ratio > 2: #Si el último mínimo tiene un volumen 2 veces superior a la media,
        divergence['strength'] += 1
        divergence['latest_vol_ratio'] = latest_ratio #se añade la información a la divergencia.

    max_ratio = 0

    for ratio in vol_ratios: #Además, se determina si para la sucesión de mínimos de la divergencia
        if ratio > max_ratio: #el volumen es creciente;
            max_ratio = ratio
        else: break

    if latest_ratio == max_ratio: #si el último volúmen es el máximo tras superar el bucle, significa que sí.
        divergence['strength'] += 1
        divergence['rising_vol'] = True

    return divergence


def calculate_volume_ratios(vol_series: pd.Series, timestamps: list[pd.Timestamp]) -> list[float]:
    '''
    Calcula la relación entre el volumen de un mínimo y el volumen medio de todos ellos.

    Parámetros:
    + vol_series: Una serie de Pandas con el volumen de activo de todos los mínimos detectados.
    + timestamps: Las marcas de tiempo de los mínimos de la divergencia detectada.

    Retorno:
    + Una lista con los ratios (su número depende de la fuerza de la divergencia).
    '''
    avg_vol = vol_series.mean()

    vol_df = vol_series.loc[timestamps].to_frame() #Crea un DF a partir de la serie sólo con las marcas temporales de la divergencia.
    vol_df['avg_vol'] = avg_vol
    vol_df['vol_ratio'] = round(vol_df['volume']/vol_df['avg_vol'], 2)  

    vol_ratios = vol_df['vol_ratio'].tolist()

    return vol_ratios  


def check_divergence(divergence: dict[str, Any], min_strength: int, std_timeframe: str) -> bool:
    '''
    Comprueba si la divergencia cumple los criterios de calidad.

    Parámetros:
    + divergence: El diccionario con información de la divergencia.
    + min_strength: La intensidad mínima que se espera de un divergencia en marcos temporales superiores a 1h.
    + std_timeframe: El marco temporal normalizado en el que se está operando.

    Retorno:
    + Un valor lógico en función de si se cumplen o no las condiciones.
    '''
    filter_1 = len(divergence['pivot_timestamps']) >= 3 #Se consideran buenas divergencias aquellas con fuerza 2 por mínimos
    filter_2 = divergence['strength'] >= min_strength #o con fuerza "min_strength" en general.
    
    if std_timeframe in ('15min', '1h'): 
        return True
    else:
        if filter_1 or filter_2: return True

    return False


def check_low_pivots(pivots: list[int], std_timeframe: str, narrow_candle_range: int, wide_candle_range: int) -> bool:
    '''
    Comprueba si los mínimos cumplen las condiciones de divergencia.

    Parámetros:
    + pivots: Una lista con los índices de los mínimos locales.
    + std_timeframe: El marco temporal normalizado en el que se está operando.
    + narrow_candle_range: El rango de velas para marcos temporales bajos.
    + wide_candle_range: El rango de velas para marcos temporales altos.

    Retorno:
    + Un valor lógico en función de si se cumplen o no las condiciones.
    '''
    if not pivots: return False

    lte_1h_cond = pivots[-1] < narrow_candle_range
    gt_1h_cond = pivots[-1] < wide_candle_range

    if std_timeframe in ('15min', '1h'): 
        if lte_1h_cond: return False
    else:
        if gt_1h_cond: return False

    return True


def compute_rsi(series: pd.Series, rsi_period: int) -> pd.Series:
    '''
    Calcula el índice de fuerza relativa (RSI), que identifica condiciones de sobrecompra (>70) y sobreventa (<30).

    Parámetro:
    + series: La columna del DF sobre la que se hace el cálculo (generalmente, el precio de cierre).
    + rsi_period: Número de velas utilizadas para el cálculo (generalmente, 14). 

    Retorno:
    + Una serie con los valores del RSI (entre 0 y 100).    
    '''
    delta = series.diff() #Cambio de precio entre velas consecutivas.

    gain = delta.clip(lower=0) #Subidas de precio (el resto de valores se sustituye por cero): presión compradora.
    loss = -delta.clip(upper=0) #Bajadas de precio (en valor absoluto): presión vendedora.

    wilder_avg_gain = gain.ewm(alpha=1/rsi_period, adjust=False).mean() #Cálculo de medias suavizadas (método de Wilder) para la presión compradora
    wilder_avg_loss = loss.ewm(alpha=1/rsi_period, adjust=False).mean() #y la vendedora.

    rs = wilder_avg_gain/wilder_avg_loss #Relación entre la fuerza de las subidas y de las bajadas.
    rsi = 100 - (100/(1 + rs)) #Transforma la relación en un oscilador acotado entre 0 y 100.

    return rsi


def find_bullish_divergence_by_low_pivots(divergence_df: pd.DataFrame) -> dict[str, Any]:
    '''
    Detecta divergencias alcistas entre el precio y el RSI mediante el análisis de mínimos locales.

    Parámetro:
    + divergence_df: El DF con los mínimos locales de precio.

    Retorno:
    + Un diccionario con las marcas temporales en las que ocurre la divergencia y su intensidad.
    '''
    timestamps = set()

    i = 0
    strength = 0 #La divergencia puede ser única o múltiple (varias sucesivas).

    while i < (len(divergence_df)) - 1: #El DF se ha de pasar en orden inverso: el mínimo más reciente en primera posición.

        current_price_low = divergence_df['low'].iloc[i] #El RSI se calcula con el precio de cierre pero la divergencia con el mínimo.
        previous_price_low = divergence_df['low'].iloc[i + 1] #El -1 del bucle evita que i + 1 pueda salirse de rango.

        current_rsi_low = divergence_df['rsi'].iloc[i]
        previous_rsi_low = divergence_df['rsi'].iloc[i + 1]

        decreasing_price = current_price_low < previous_price_low * 0.995 #Se exige que el precio disminuya al menos un 0,5 %
        increasing_rsi = current_rsi_low > previous_rsi_low + 1 #y que el RSI aumente en un punto.

        if decreasing_price and increasing_rsi: 

            timestamps.update([divergence_df.index[i], divergence_df.index[i + 1]])
            
            i += 1
            strength += 1

        else: break

    if strength == 0: return None

    return {
        'strength': strength,
        'pivot_timestamps': sorted(timestamps) #Transforma el conjunto en una lista ordenada.
    }


def find_low_pivots(series: pd.Series, pivot_window: int, std_timeframe: str) -> list[int]:
    '''
    Detecta mínimos locales en una serie (columna) de un DF.

    Parámetros:
    + series: La serie donde se van a buscar los valores mínimos (generalmente, el precio mínimo).
    + pivot_window: Número de velas de amplitud para determinar el mínimo.
    + std_timeframe: El marco temporal normalizado en el que se está operando.

    Retorno:
    + Una lista con los índices de los mínimos locales.
    '''
    pivots = list()

    for i in range(pivot_window, len(series) - pivot_window): #Se evalúan sólos los puntos con suficiente contexto a su alrededor.

        start = i - pivot_window #Se define la ventana de búsqueda.
        end = i + pivot_window + 1 #El 1 es debido a cómo funciona el rebanado en Python.

        if series.iloc[i] == min(series.iloc[start:end]): #Calcula el mínimo dentro de la ventana y lo compara con el valor en iteración;
            pivots.append(i) #si coinciden, se trata de un mínimo local, por lo que añade su índice al conjunto.
    
    if std_timeframe in ('15min', '1h'): #Para marcos temporales bajos,
        last_i = len(series) - pivot_window + series.iloc[-pivot_window:].argmin() #busca el mínimo del final de la serie, sin preocuparse de la amplitud de la ventana hacia la derecha,
        if last_i not in pivots: pivots.append(last_i) #y lo añade.

    return pivots


def format_timestamps(divergence: dict[str, Any]) -> dict[str, Any]:
    '''
    Simplifica las marcas temporales para facilitar su lectura.

    Parámetro:
    + divergence: El diccionario con las marcas temporales.

    Retorno:
    + El diccionario con las marcas en formato cadena.
    '''
    timestamps = divergence.pop('pivot_timestamps') #Las marcas se extraen del diccionario,

    timestrings = list()

    for timestamp in timestamps: #se formatean una a una
        timestring = timestamp.strftime('%Y-%m-%d %H:%M')
        timestrings.append(timestring)

    new_item = ('pivot_timestamps', timestrings)

    items = list(divergence.items())
    items.insert(1, new_item) #y se vuelven a insertar en la misma posición.

    divergence = dict(items)

    return divergence


def get_aux_data_structures(candles_df: pd.DataFrame, pivots: list[int]) -> tuple[pd.DataFrame, pd.Series]:
    '''
    Crea las estructuras de datos auxiliares para calcular divergencias.

    Parámetros:
    + candles_df: El DF con la información de mercado.
    + pivots: Una lista con los índices de los mínimos locales.

    Retorno:
    + Una tupla con ambas estructuras de datos.
    '''
    divergence_df = candles_df.iloc[pivots].loc[:, ['low', 'rsi']].sort_index(ascending=False) #Para la determinación de la divergencia (por mínimos, el método principal).
    vol_series = candles_df.iloc[pivots].loc[:, 'volume'] #Para el cálculo del volumen en los mínimos de la divergencia.

    return divergence_df, vol_series