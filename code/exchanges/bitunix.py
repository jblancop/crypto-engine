from code.exchanges.abstract_exchange import Exchange

import pandas as pd


class Bitunix(Exchange):
    '''
    Implementación de "Exchange" para la plataforma Bitunix.
    '''
    @staticmethod
    def parse_candles(api_json, api_fields, df_fields):
        '''
        Implementación de "parse_candles" para Bitunix.
        '''
        data = api_json['data']

        df = pd.DataFrame(data=data)

        if any(col not in df.columns for col in api_fields):
            return None
        
        df = df.astype(api_fields)

        df['timestamp'] = pd.to_datetime(df['ts'], utc=True).dt.tz_convert('Europe/Madrid') #Se normalizan las marcas temporales
        df = df.sort_values('timestamp').set_index('timestamp') #y se establecen como índice del DF.
        df = df[df_fields]

        return df        
    
    @staticmethod
    def parse_pairs(api_json):
        '''
        Implementación de "parse_pairs" para Bitunix.
        '''
        data = api_json.get('data')
        pairs = set()

        for item in data:
            
            is_usdt = item.get('quote') == 'USDT' #Sólo se trabaja contra Tether
            is_active = item.get('isOpen') == 1 #y sólo interesan los pares activos.

            pair = item.get('symbol')

            if is_usdt and is_active: pairs.add(pair.upper())

        return pairs
    
    @staticmethod
    def set_params(pair, timeframe, _):
        '''
        Implementación de "set_params" para Bitunix.
        '''
        return {
            'symbol': pair,
            'interval': timeframe
        } #Bitunix sólo requiere "api_batch" si se ataca el punto final histórico, si no siempre devuelve 201 velas.