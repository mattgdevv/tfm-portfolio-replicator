"""
Tests básicos para DollarRateService usando unittest estándar
"""

import unittest
import asyncio
from unittest.mock import Mock
from app.services.dollar_rate import DollarRateService
from app.core.config import Config


class TestDollarRateService(unittest.TestCase):
    """Tests para el servicio de tasas de dólar"""

    def test_init_with_config(self):
        """Test inicialización con configuración"""
        config = Config()
        config.request_timeout = 45
        config.cache_ttl_seconds = 600

        service = DollarRateService(config)

        self.assertEqual(service.timeout, 45)
        self.assertEqual(service._cache_ttl_seconds, 600)
        self.assertEqual(service.preferred_ccl_source, "dolarapi_ccl")

    def test_init_without_config(self):
        """Test inicialización sin configuración (valores por defecto)"""
        service = DollarRateService()

        self.assertEqual(service.timeout, 30)  # Valor mejorado
        self.assertEqual(service._cache_ttl_seconds, 300)  # Valor mejorado
        self.assertEqual(service.preferred_ccl_source, "dolarapi_ccl")

    def test_sources_status_initialization(self):
        """Test que las fuentes se inicializan correctamente"""
        service = DollarRateService()

        expected_sources = {
            "dolarapi_ccl": True,
            "ccl_al30": False,  # Requiere autenticación
            "dolarapi_mep": True,
        }

        self.assertEqual(service.sources_status, expected_sources)

    def test_set_iol_session(self):
        """Test configuración de sesión IOL"""
        service = DollarRateService()

        # Inicialmente CCL AL30 debería estar deshabilitado
        self.assertFalse(service.sources_status["ccl_al30"])

        # Configurar sesión
        mock_session = Mock()
        service.set_iol_session(mock_session)

        # Ahora debería estar habilitado
        self.assertTrue(service.sources_status["ccl_al30"])

    def test_set_iol_session_none(self):
        """Test eliminación de sesión IOL"""
        service = DollarRateService()

        # Configurar sesión primero
        mock_session = Mock()
        service.set_iol_session(mock_session)
        self.assertTrue(service.sources_status["ccl_al30"])

        # Luego quitarla
        service.set_iol_session(None)
        self.assertFalse(service.sources_status["ccl_al30"])

    def test_cache_operations(self):
        """Test operaciones básicas de cache"""
        service = DollarRateService()

        # Cache debería estar vacío inicialmente
        self.assertEqual(len(service._cache), 0)

        # Agregar entrada al cache
        test_data = {"rate": 950.0, "source": "test"}
        service._cache["test_key"] = test_data

        # Verificar que se guardó
        self.assertEqual(len(service._cache), 1)
        self.assertEqual(service._cache["test_key"], test_data)


if __name__ == "__main__":
    # Ejecutar tests
    unittest.main()
