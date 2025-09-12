# 🧪 Tests para Portfolio Replicator

Suite de tests unitarios para validar la funcionalidad del sistema ETL de arbitraje de CEDEARs.

## 📊 Cobertura Actual

- ✅ **DollarRateService**: 6 tests (configuración, cache, sesiones IOL)
- ✅ **Config**: 6 tests (valores por defecto, personalización, validación)
- **Total**: 12 tests ejecutándose correctamente

## 🚀 Cómo Ejecutar

### Opción 1: Ejecutar todos los tests
```bash
python tests/run_tests.py
```

### Opción 2: Ejecutar tests individuales
```bash
python -m unittest tests.test_dollar_rate_service
python -m unittest tests.test_config
```

### Opción 3: Ejecutar con verbose
```bash
python -m unittest -v tests/
```

## 📁 Estructura de Tests

```
tests/
├── __init__.py                 # Paquete de tests
├── run_tests.py               # Ejecutor principal de tests
├── test_dollar_rate_service.py # Tests para servicio de dólar
└── test_config.py             # Tests para configuración
```

## 🎯 Tipos de Tests Incluidos

### Unit Tests
- ✅ Inicialización de servicios con/sin configuración
- ✅ Valores por defecto y personalización
- ✅ Operaciones de cache básicas
- ✅ Gestión de sesiones IOL
- ✅ Validación de configuración

### Próximas Expansiones
- 🔄 Tests de integración para pipeline ETL
- 🔄 Tests de servicios de base de datos
- 🔄 Tests de APIs externas (con mocks)
- 🔄 Tests de performance

## 📈 Métricas

- **Tests actuales**: 12
- **Cobertura aproximada**: ~40% de servicios críticos
- **Tiempo de ejecución**: < 0.01s
- **Estado**: ✅ Todos pasan

## 🛠️ Dependencias

- **unittest** (incluido en Python estándar)
- **Módulos del proyecto** (app.core.config, app.services.dollar_rate)

## 📝 Notas para TFM

Esta suite de tests demuestra:
- ✅ Capacidad de testing del código
- ✅ Validación de configuraciones críticas
- ✅ Verificación de lógica de negocio
- ✅ Mantenibilidad y extensibilidad del código

Para producción, se recomienda expandir con:
- Tests de integración end-to-end
- Mocks para APIs externas
- Tests de carga y performance
- Cobertura > 80%
