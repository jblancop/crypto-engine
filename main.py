'''
Ejecutar desde la raíz del repositorio:
    uv run main.py --exchange <bitunix|kraken|okx>
''' 
from code.aux_functions import load_config, measure_execution_time, parse_arguments, order_candles_dict, write_report
from code.main_functions import get_candles, get_divergence, get_pairs

from concurrent.futures import ThreadPoolExecutor, as_completed


@measure_execution_time
def main(exchange: str) -> tuple[int, dict[tuple, dict]]:
    '''
    Procesa objetos de mercado de forma concurrente para determinar divergencias.

    Parámetro:
    + exchange: La plataforma de la que se quiere obtener información.

    Retorno:
    + Una tupla con el número de objetos analizado y las divergencias encontradas.
    '''
    cfg = load_config(exchange)
    pairs = get_pairs(cfg)

    max_workers = cfg['all']['max_workers']
    timeframes = cfg['this']['timeframes']
    report_folder = cfg['all']['report_folder']

    candles_dict = dict()
    divergences_dict = dict()

    with ThreadPoolExecutor(max_workers=max_workers) as executor: #Procesado concurrente de los elementos (par/intervalo) de mercado.
        
        futures = { #El ejecutor devuelve por cada elemento un objeto "futuro", que representa la ejecución pendiente de la función.
            executor.submit(get_candles, pair, exch_timeframe, cfg): (pair, timeframes[exch_timeframe])
            for pair in pairs
            for exch_timeframe in timeframes.keys()
        } #"futures" es un diccionario con pares "future"/("pair", "std_timeframe").

        for i, future in enumerate(as_completed(futures)): #as_completed() devuelve los futuros en orden de finalización y no de envío.

            pair, std_timeframe = futures[future]

            try:

                candles_df = future.result()

                if candles_df is not None: #Hasta este momento no se comprueba si el procesado fue exitoso o no. 
                    candles_dict[(std_timeframe, pair)] = candles_df 
            
            except Exception as e:
                print(f'Error al procesar el elemento {pair}/{std_timeframe}: {e}')

    candles_dict = order_candles_dict(candles_dict, timeframes.values())

    for (std_timeframe, pair), candles_df in candles_dict.items():

        divergence = get_divergence(candles_df, std_timeframe, cfg)

        if divergence: divergences_dict[(std_timeframe, pair)] = divergence

    if divergences_dict: write_report(divergences_dict, exchange, report_folder)

    return i, divergences_dict


if __name__ == '__main__':

    exchange = parse_arguments()

    main(exchange)