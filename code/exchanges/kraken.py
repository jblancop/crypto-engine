from code.exchanges.abstract_exchange import Exchange

import pandas as pd


class Kraken(Exchange):
    '''
    Implementación de "Exchange" para la plataforma Kraken.
    '''
    @staticmethod
    def parse_candles(api_json, api_fields, df_fields):
        '''
        Implementación de "parse_candles" para Kraken.
        '''
        result = api_json.get('result')
        data = next(v for k, v in result.items() if k != 'last')

        df = pd.DataFrame(data=data, columns=api_fields.keys()) #La API de Kraken envía las columnas sin encabezado.
        df = df.astype(api_fields)

        df['timestamp'] = pd.to_datetime(df['time'], unit='s').dt.tz_localize('UTC').dt.tz_convert('Europe/Madrid') #Se normalizan las marcas temporales
        df = df.sort_values('timestamp').set_index('timestamp') #y se establecen como índice del DF.
        df = df[df_fields]

        return df        
    
    @staticmethod
    def parse_pairs(api_json):
        '''
        Implementación de "parse_pairs" para Kraken.
        '''
        data = api_json.get('result')
        pairs = set()

        for _, v in data.items():
            
            ir_eur = v.get('quote') == 'ZEUR' #Sólo se trabaja contra el euro
            is_active = v.get('status') == 'online' #y sólo interesan los pares activos.

            pair = v.get('altname')

            if ir_eur and is_active: pairs.add(pair)

        return pairs
    
    @staticmethod
    def set_params(pair, timeframe, _):
        '''
        Implementación de "set_params" para Kraken.
        '''
        return {
            'pair': pair,
            'interval': timeframe
        } #Kraken no requiere "api_batch", siempre devuelve 721 velas.