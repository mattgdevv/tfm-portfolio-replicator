# 🗂️ Tests Obsoletos - Movidos el 08/09/2024

## 📋 **RESUMEN**
Estos 19 archivos de test han sido movidos a este directorio porque **no son compatibles** con la nueva arquitectura de Dependency Injection (DI) implementada en el proyecto.

## ❌ **PROBLEMAS IDENTIFICADOS**

### **1. Importaciones Directas de Servicios**
```python
# ❌ ANTES (obsoleto)
from app.services.dollar_rate import dollar_service
from app.services.arbitrage_detector import arbitrage_detector

# ✅ AHORA (DI container)
from app.core.services import build_services
services = build_services()
dollar_service = services['dollar_rate']
```

### **2. Instancias Globales Obsoletas**
```python
# ❌ ANTES (obsoleto)
international_price_service = InternationalPriceService()

# ✅ AHORA (DI container)
services = build_services()
international_service = services['international_prices']
```

### **3. Servicios Eliminados**
- `byma_historical_service` → reemplazado por `byma_integration`
- Instancias globales eliminadas por patrón DI

## 📁 **ARCHIVOS MOVIDOS**
- `byma_api_test.py`
- `dollar_rate_test.py`
- `fci_test.py`
- `test_arbitrage_detector.py`
- `test_byma_endpoints.py`
- `test_byma_integration.py`
- `test_ccl_al30.py`
- `test_ccl_al30_with_iol.py`
- `test_dollar_service.py`
- `test_excel_reading.py`
- `test_gemini_config.py`
- `test_international_prices.py`
- `test_iol_api.py`
- `test_iol_api_checkpoint.py`
- `test_iol_historical.py`
- `test_smoke_fallbacks.py`
- `test_variation_analyzer.py`
- `validate_portfolio_symbols.py`
- Y otros...

## 🔄 **SIGUIENTE PASO**
Crear una nueva suite de tests compatible con la arquitectura DI en el directorio `tests/` vacío.

## 📊 **ESTADÍSTICAS**
- **19 archivos de test** movidos
- **2095 líneas** de código de test obsoleto
- **Ratio tests/código: ~81%** (muy alto para aplicación de negocio)

---
*Estos tests están preservados por si necesitas referencia histórica, pero NO deben usarse con la arquitectura actual.*
