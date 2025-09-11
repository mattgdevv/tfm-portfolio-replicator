"""
Configuración centralizada de logging para toda la aplicación
"""
import logging
import warnings

def setup_quiet_logging():
    """Configura logging silencioso para librerías externas ruidosas"""
    
    # Silenciar loggers ruidosos de librerías externas
    noisy_loggers = [
        'urllib3.connectionpool',
        'urllib3.util.retry', 
        'requests.packages.urllib3.connectionpool',
        'requests.packages.urllib3',
        'urllib3',
        'httpx',
        'httpcore',
        'peewee',
        'requests',
        'asyncio',
        'chardet.charsetprober'
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        logging.getLogger(logger_name).disabled = True
    
    # Silenciar warnings de pandas/pyarrow y otros
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="pandas")
    warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")
    warnings.filterwarnings("ignore", message=".*Pyarrow will become.*")
    warnings.filterwarnings("ignore", message=".*NumExpr defaulting.*")
    warnings.filterwarnings("ignore", message=".*Using selector.*")
    
    # Configurar formato limpio para la aplicación
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        force=True
    )

def setup_debug_logging():
    """Configura logging detallado para debugging"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s:%(name)s:%(message)s',
        force=True
    )