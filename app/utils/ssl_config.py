"""
Configuración centralizada de SSL warnings para toda la aplicación
"""
import urllib3

def disable_ssl_warnings():
    """Suprime SSL warnings de urllib3 de forma centralizada"""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
