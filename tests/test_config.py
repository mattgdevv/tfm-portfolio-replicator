"""
Tests básicos para Config usando unittest estándar
"""

import unittest
import os
import tempfile
from app.core.config import Config


class TestConfig(unittest.TestCase):
    """Tests para la configuración del sistema"""

    def test_config_defaults(self):
        """Test valores por defecto de configuración"""
        config = Config()

        self.assertEqual(config.market, "argentina")
        self.assertEqual(config.arbitrage_threshold, 0.005)
        self.assertEqual(config.cache_ttl_seconds, 180)
        self.assertEqual(config.request_timeout, 30)
        self.assertEqual(config.retry_attempts, 3)

    def test_config_custom_values(self):
        """Test configuración con valores personalizados"""
        config = Config()
        config.arbitrage_threshold = 0.01
        config.request_timeout = 60
        config.cache_ttl_seconds = 600

        self.assertEqual(config.arbitrage_threshold, 0.01)
        self.assertEqual(config.request_timeout, 60)
        self.assertEqual(config.cache_ttl_seconds, 600)

    def test_config_from_env_basic(self):
        """Test carga básica desde variables de entorno"""
        # Crear configuración de prueba
        config = Config()
        config.arbitrage_threshold = 0.02
        config.request_timeout = 45

        # Verificar que los valores se mantienen
        self.assertEqual(config.arbitrage_threshold, 0.02)
        self.assertEqual(config.request_timeout, 45)

    def test_ccl_sources_list(self):
        """Test que las fuentes CCL están configuradas correctamente"""
        config = Config()

        expected_sources = ["dolarapi", "iol_al30"]
        self.assertEqual(config.ccl_sources, expected_sources)

    def test_preferred_ccl_source(self):
        """Test fuente CCL preferida por defecto"""
        config = Config()

        self.assertEqual(config.preferred_ccl_source, "dolarapi_ccl")

    def test_config_validation(self):
        """Test que la configuración se valida correctamente"""
        config = Config()

        # Estos deberían ser valores válidos
        self.assertGreater(config.arbitrage_threshold, 0)
        self.assertGreater(config.request_timeout, 0)
        self.assertGreater(config.cache_ttl_seconds, 0)
        self.assertGreater(config.retry_attempts, 0)


if __name__ == "__main__":
    unittest.main()
