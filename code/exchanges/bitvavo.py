from code.exchanges.abstract_exchange import Exchange
import pandas as pd


class Bitvavo(Exchange):
    '''
    Implementación de "Exchange" para la plataforma Bitvavo.
    '''
    @staticmethod
    def parse_candles(api_json, api_fields, df_fields):
        '''
        Implementación de "parse_candles" para Bitvavo.
        '''    
        df = pd.DataFrame(data=api_json, columns=api_fields.keys()) #La API de Bitvavo envía las columnas sin encabezado. 
        df = df.astype(api_fields)

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Europe/Madrid') #Se normalizan las marcas temporales
        df = df.sort_values('timestamp').set_index('timestamp') #y se establecen como índice del DF.
        df = df.iloc[:-1] #Se elimina la vela en formación.
        df = df[df_fields]

        return df
    
    @staticmethod
    def parse_pairs(api_json):
        '''
        Implementación de "parse_pairs" para Bitvavo.
        '''
        pairs = set()

        for item in api_json:

            is_eur = item.get('quote') == 'EUR' #Sólo se trabaja contra el euro
            is_active = item.get('status') == 'trading' #y sólo interesan los pares activos.

            pair = item.get('market')

            if is_eur and is_active: pairs.add(pair)

        return pairs
    
    @staticmethod
    def set_params(pair, timeframe, api_batch):
        '''
        Implementación de "set_params" para Bitvavo.
        '''
        return {
            'interval': timeframe,
            'limit': api_batch
        } #Bitvavo no pasa el par por parámetros sino en la propia URL.