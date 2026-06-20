from code.exchanges.abstract_exchange import Exchange

import pandas as pd


class OKX(Exchange):
    '''
    Implementación de "Exchange" para la plataforma OKX.
    '''
    @staticmethod
    def parse_candles(api_json, api_fields, df_fields):
        '''
        Implementación de "parse_candles" para OKX.
        '''
        data = api_json.get('data')

        df = pd.DataFrame(data=data, columns=api_fields.keys()) #La API de OKX envía las columnas sin encabezado.
        df = df.astype(api_fields)
        
        df['timestamp'] = pd.to_datetime(df['ts'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Europe/Madrid') #Se normalizan las marcas temporales
        df = df.sort_values('timestamp').set_index('timestamp') #y se establecen como índice del DF.
        df = df[df_fields]

        return df       
    
    @staticmethod
    def parse_pairs(api_json):
        '''
        Implementación de "parse_pairs" para OKX.
        '''
        data = api_json.get('data')
        pairs = set()

        for item in data:

            is_eur = item.get('quoteCcy') == 'EUR' #Sólo se trabaja contra el euro
            is_active = item.get('state') == 'live' #y sólo interesan los pares activos.

            pair = item.get('instId')

            if is_eur and is_active: pairs.add(pair)

        return pairs
    
    @staticmethod
    def set_params(pair, timeframe, api_batch):
        '''
        Implementación de "set_params" para OKX.
        '''
        return {
            'instId': pair,
            'bar': timeframe,
            'limit': api_batch
        }