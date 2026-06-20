from functools import wraps
from omegaconf import OmegaConf as oc
from pathlib import Path
from time import perf_counter
from typing import Any, Callable
import argparse as ap
import pandas as pd
import requests as rq


def parse_arguments() -> str:
    '''
    Permite el paso de argumentos en el comando de ejecución de main.py.

    Retorno:
    + La plataforma de la que se quiere obtener la información de mercado.
    '''
    parser = ap.ArgumentParser() #Gestor de argumentos.

    parser.add_argument( #El único argumento que se le pasa es la plataforma.
        '--exchange',
        required=True,
        choices=['bitunix', 'kraken', 'okx']
    )

    args = parser.parse_args()

    return args.exchange


def execute_api_request(url: str, params: dict[str, Any]) -> dict[str, Any]:
    '''
    Hace una petición a una API.

    Parámetros:
    + url: La URL completa, incluyendo el punto final a atacar.
    + params: Los parámetros necesarios para hacer la petición.

    Retorno:
    + Un JSON con toda la información enviada por la API.
    '''
    with rq.Session() as session:
        response = session.get(url=url, params=params)
        response.raise_for_status()
        return response.json()


def load_config(exchange: str) -> dict[str, dict[str, Any]]:
    '''
    Devuelve el diccionario de configuración.

    Parámetro:
    + exchange: El nombre de la plataforma de la que se quiere obtener la información.

    Retorno:
    + Un diccionario con la información de configuración común y para la plataforma
    '''
    yml_path = Path('config')/'config.yml'
    cfg = oc.load(yml_path)

    return {
        'all': cfg['all'],
        'this': cfg[exchange]
    }


def measure_execution_time(main: Callable) -> Callable:
    '''
    Decorador para medir el tiempo de ejecución de la función principal.

    Parámetro:
    + main: La función principal, a decorar.

    Retorno:
    + La función envoltorio, que decora.
    '''
    @wraps(main) #Preserva el nombre y la documentación original de la función decorada.
    def wrapper(*args, **kwargs):
        
        start = perf_counter() 
        i, divergences_dict = main(*args, **kwargs)
        elapsed = perf_counter() - start
        
        final_mssg = f'Se han analizado {i} elementos de mercado y se han detectado {len(divergences_dict)} divergencias alcistas en {round(elapsed/60, 2)} minutos'
        print(final_mssg)
    
    return wrapper


def order_candles_dict(candles_dict: dict[tuple[str, str], pd.DataFrame], timeframes: list[str]) -> dict[tuple[str, str], pd.DataFrame]:
    '''
    Ordena los elementos del diccionario de mercado.

    Parámetros:
    + candles_dict: Un diccionario con pares (intervalo, par)/DF de mercado.
    + timeframes: Los intervalos temporales en los que se quiere operar.

    Retorno:
    + El diccionario de mercado ordenado por intervalo y par.
    '''
    timeframe_dict = {timeframe: i for i, timeframe in enumerate(timeframes)} #Diccionario con pares intervalo/orden.
    order_tuple = lambda item: (timeframe_dict[item[0][0]], item[0][1]) #Siendo "item" cada par de "candles_dict", devuelve una tupla (orden, par).

    ordered_dict = dict(
        sorted(
            candles_dict.items(),
            key=order_tuple #Se ordenan los pares de "candles_dict" según las "order_tuple"
        )
    )

    return ordered_dict


def write_report(divergences_dict: dict[tuple, dict], exchange: str, report_folder: str) -> None:
    '''
    Crea el informe de divergencias.

    Parámetros:
    + divergences_dict: Las divergencias de relevancia.
    + exchange: El nombre de la plataforma de la que se ha obtenido la información.
    + report_folder: Ruta donde se almacenan los informes

    Retorno:
    + Nada, crea el informe.
    '''
    report_folder = Path(report_folder)

    if not report_folder.exists(): report_folder.mkdir(parents=True)

    with open(report_folder/f'{exchange}_divergences_{pd.Timestamp.today().date()}.txt', 'a', encoding='utf-8') as file:
        for (timeframe, pair), divergence in divergences_dict.items():
            file.write(f'{timeframe}/{pair}:\n{divergence}\n')