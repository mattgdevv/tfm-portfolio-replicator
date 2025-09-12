"""
Test suite para Portfolio Replicator
Ejecutar con: python -m pytest tests/ o python tests/run_tests.py
"""

import unittest
import sys
import os

# Agregar el directorio padre al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_all_tests():
    """Ejecuta todos los tests de la suite"""
    # Descubrir y ejecutar tests
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir, pattern='test_*.py')

    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Resumen
    print("\n" + "="*60)
    print("RESUMEN DE TESTS")
    print("="*60)
    print(f"Tests ejecutados: {result.testsRun}")
    print(f"Errores: {len(result.errors)}")
    print(f"Fallos: {len(result.failures)}")
    print(f"Éxitos: {result.testsRun - len(result.errors) - len(result.failures)}")

    if result.errors:
        print("\nERRORES:")
        for test, error in result.errors:
            print(f"  - {test}: {error}")

    if result.failures:
        print("\nFALLOS:")
        for test, failure in result.failures:
            print(f"  - {test}: {failure}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
