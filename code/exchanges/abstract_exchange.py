from abc import ABC, abstractmethod
from typing import Any
import pandas as pd


class Exchange(ABC):
    '''
    Interfaz para la definición de una clase que represente una plataforma de compraventa de criptomonedas.
    '''
    @abstractmethod
    def parse_candles(api_json: dict[str, Any], api_fields: dict[str, str], df_fields: list[str]) -> pd.DataFrame:
        '''
        Transforma la información de mercado recibida de la API de la plataforma en un DF.

        Parámetros:
        + api_json: La respuesta de la API.
        + api_fields: Los campos/tipos de que consta la respuesta.
        + df_fields: Los campos definitivos del DF.

        Retorno:
        + Un DF con la información de mercado normalizada.
        '''
        pass
    
    @abstractmethod
    def parse_pairs(api_json: dict[str, Any]) -> set[str]:
        '''
        Recaba todos los pares activos cripto/cotizada de la plataforma a partir de su API.

        Parámetro:
        + api_json: La respuesta de la API.

        Retorno:
        + Un conjunto con todos los pares.
        '''
        pass

    @abstractmethod
    def set_params(pair: str, timeframe: str|int, api_batch: int) -> dict[str, Any]:
        '''
        Genera el diccionario de parámetros necesario para atacar el punto final "candles" de la API.

        Parámetros:
        + pair: El par del que se quiere obtener información.
        + timeframe: El marco temporal en el que se quiere operar.
        + api_batch: Número de velas solicitadas.

        Retorno:
        + El diccionario con los parámetros.
        '''
        pass        