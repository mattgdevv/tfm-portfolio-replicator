# Portfolio Replicator TFM

**Sistema ETL de detección de arbitraje multi-fuente para CEDEARs vs activos subyacentes con estimación inteligente**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Async](https://img.shields.io/badge/Async-asyncio-green.svg)](https://docs.python.org/3/library/asyncio.html)
[![Architecture](https://img.shields.io/badge/Architecture-DI-orange.svg)](https://en.wikipedia.org/wiki/Dependenc### 📋 Casos de Uso Testing
```bash
# 1. Portfolio real IOL (requiere credenciales)
python main.py → opción 1

# 2. Portfolio archivo ejemplo
python main.py → opción 2 → data.csv

# 3. Pipeline ETL completo
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket

# 4. Testing periodicidad (ejecución cada 2 minutos)
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket --schedule 2min
# Dejar correr unos minutos, luego Ctrl+C para detener
# Verificar múltiples registros en BD: sqlite3 output/portfolio_data.db "SELECT datetime(timestamp, 'localtime'), id FROM portfolios ORDER BY timestamp DESC LIMIT 5;"

# 5. Verificación servicios
python main.py → opción 9
```![TFM](https://img.shields.io/badge/TFM-Data%20Engineer-purple.svg)](#)

## ⚡ Quick Start

```bash
# 1. Clonar repositorio
git clone https://github.com/mattgdevv/tfm-portfolio-replicator.git
cd tfm-portfolio-replicator

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. (OPCIONAL) Configurar credenciales IOL
cp .env.example .env  # Editar con IOL_USERNAME e IOL_PASSWORD si tienes cuenta

# 5a. Modo INTERACTIVO (con menú) - USA .prefs.json existente
python main.py

# 5b. Modo ETL AUTOMÁTICO (para CI/CD) - USA .prefs.json existente  
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket

# 5c. Diagnóstico de servicios únicamente
python scripts/etl_cli.py --health-check
```

> **💡 Configuración**: El sistema usa `.prefs.json` (incluido) para configuración principal. Variables de entorno en `.env` son opcionales y sobrescriben `.prefs.json`.

## 🎯 Dos Modos de Ejecución

### 🖥️ **Modo Interactivo** (`main.py`)
- **Propósito**: Exploración manual y análisis paso a paso
- **Interfaz**: Menú con 9 opciones
- **Usuario objetivo**: Analistas, desarrollo, testing
- **Entrada**: Input usuario (credenciales, archivos, configuración)

### 🤖 **Modo ETL Automático** (`scripts/etl_cli.py`)
- **Propósito**: Pipelines automáticos y CI/CD
- **Interfaz**: CLI parametrizable
- **Usuario objetivo**: Sistemas automáticos, batch processing
- **Entrada**: Solo parámetros de línea de comandos

## 🎯 Features

- **Real-time Arbitrage Detection** - Multi-source price comparison with configurable thresholds
- **Intelligent Fallback Estimation** - Automatic theoretical pricing when markets are closed or unavailable
- **Multi-broker Support** - IOL API, Excel/CSV (Bull Market, Cocos Capital)
- **SQLite Database Integration** - Persistent storage for portfolios, positions, arbitrage opportunities, and pipeline metrics
- **Robust Data Pipeline** - Automatic fallbacks, caching, and error handling
- **Configurable ETL** - CLI with flexible parameters and output formats
- **⏰ Periodic Execution** - Built-in scheduler for automated ETL runs (2min/30min/hourly/daily)
- **24/7 Analysis** - Works on weekends using international prices + CCL estimation
- **Historical Data Storage** - Track arbitrage opportunities and portfolio changes over time

## ⚙️ Configuration

### 🎚️ Jerarquía de Configuración (prioridad descendente)

1. **🥇 Variables de entorno** (`.env` + export) - Mayor prioridad
2. **🥈 Archivo `.prefs.json`** - Configuración principal 
3. **🥉 Defaults en código** - Valores por defecto

### 📁 Archivos de Configuración

#### `.prefs.json` (Configuración Principal)
```json
{
  "arbitrage_threshold": 0.002,
  "request_timeout": 30, 
  "cache_ttl_seconds": 180,
  "PREFERRED_CCL_SOURCE": "dolarapi_ccl"
}
```

#### `.env` (Credenciales y Overrides - Opcional)
```bash
# Credenciales IOL (solo si tienes cuenta)
IOL_USERNAME=tu_usuario
IOL_PASSWORD=tu_password

# API Keys opcionales (funcionalidades avanzadas)
FINNHUB_API_KEY=tu_finnhub_key
GEMINI_API_KEY=tu_gemini_key

# Override configuración (sobrescribe .prefs.json)
ARBITRAGE_THRESHOLD=0.01
REQUEST_TIMEOUT=25
CACHE_TTL_SECONDS=300
```

### 🖥️ Modo Interactivo (main.py)
```bash
python main.py
# Menú con 9 opciones:
# 1. Portfolio desde IOL (requiere credenciales)
# 2. Portfolio desde Excel/CSV 
# 3. Ver CEDEARs disponibles
# 4-9. Configuración y diagnósticos
```

### 🤖 Modo ETL Automático (scripts/etl_cli.py)
```bash
# Configuración básica (usa defaults)
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket

# Configuración personalizada
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket --threshold 0.015 --timeout 45

# Todos los parámetros + output personalizado
python scripts/etl_cli.py \
  --source excel \
  --file data.csv \
  --broker cocos \
  --threshold 0.01 \
  --timeout 45 \
  --cache-ttl 300 \
  --output results/ \
  --verbose

# Solo análisis sin guardar archivos JSON (BD siempre se guarda)
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket --no-save

# Modo verbose (output técnico completo para debugging)
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket --verbose

# Health check de servicios
python scripts/etl_cli.py --health-check

# Health check con logs técnicos detallados
python scripts/etl_cli.py --health-check --verbose
```

#### 🖥️ **Control de Output**
```bash
# Modo NORMAL (por defecto) - Output limpio y profesional
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket
# Salida: Solo información esencial y resultados para el usuario

# Modo VERBOSE - Output técnico completo
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket --verbose  
# Salida: DEBUG logs, detalles HTTP, cache hits, rate limiting, etc.
```

#### 🕒 **Ejecución Periódica (Scheduling)**
```bash
# Ejecutar cada 30 minutos (recomendado para producción)
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket --schedule 30min

# Ejecutar cada hora
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket --schedule 1hour

# Ejecutar diariamente 
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket --schedule daily

# Para testing: ejecutar cada 2 minutos (solo para pruebas)
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket --schedule 2min
```

**Opciones de scheduling disponibles:**
- `2min` - Cada 2 minutos (solo para testing/demos)
- `30min` - Cada 30 minutos (recomendado para desarrollo)
- `1hour` / `hourly` - Cada hora (recomendado para producción)
- `daily` - Una vez por día

**Características del scheduler:**
- ✅ **Ejecución automática** - Se ejecuta indefinidamente hasta Ctrl+C
- ✅ **Logging completo** - Timestamps y contadores de ejecución
- ✅ **Persistencia en BD** - Cada ejecución genera nuevo registro en SQLite
- ✅ **Gestión de errores** - Continúa ejecutándose aunque falle una iteración
- ✅ **Evidencia verificable** - Registros en BD y archivos con timestamps únicos

## 📊 Ejemplos de Uso

### 🚀 **Caso 1: Usuario nuevo - Quick Start**
```bash
# 1. Clonar repo y setup
git clone https://github.com/mattgdevv/tfm-portfolio-replicator.git && cd tfm-portfolio-replicator
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# 2. Probar con datos ejemplo (incluidos) - guarda JSON + SQLite
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket

# Resultado esperado: Detección de 4 oportunidades de arbitraje ✅
```

### 🏦 **Caso 2: Usuario con cuenta IOL**
```bash
# 1. Configurar credenciales
cp .env.example .env
# Editar .env con IOL_USERNAME e IOL_PASSWORD

# 2. Modo interactivo
python main.py
# Opción 1: "Obtener portfolio desde IOL"

# 3. Verificar conexión
python main.py  
# Opción 9: "Diagnóstico de servicios"
```

### 📈 **Caso 3: Análisis de archivo personalizado**
```csv
# mi_portfolio.csv
Símbolo,Cantidad,Precio,Broker
AAPL,10,150.0,bullmarket
MSFT,5,300.0,bullmarket
GOOGL,8,120.0,bullmarket
```
```bash
python scripts/etl_cli.py --source excel --file mi_portfolio.csv --broker bullmarket --threshold 0.01
```

### 🕒 **Caso 4: ETL Periódico Automático**
```bash
# Testing/Demo: Ejecutar cada 2 minutos para ver múltiples ejecuciones rápido
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket --schedule 2min

# Producción: Monitoreo continuo cada 30 minutos
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket --schedule 30min

# Análisis diario automático
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket --schedule daily

# Verificar ejecuciones en BD
sqlite3 output/portfolio_data.db "SELECT datetime(timestamp, 'localtime'), total_positions FROM portfolios ORDER BY timestamp DESC LIMIT 5;"
```

### 🏥 **Caso 5: Diagnóstico y Health Check**
```bash
# Verificación rápida de todos los servicios
python scripts/etl_cli.py --health-check

# Diagnóstico detallado con logs técnicos
python scripts/etl_cli.py --health-check --verbose

# En scripts automatizados - verificar antes de ETL
if python scripts/etl_cli.py --health-check; then
    echo "✅ Servicios operativos, ejecutando ETL..."
    python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket
else
    echo "❌ Error en servicios, cancelando ETL"
    exit 1
fi

# Health check desde aplicación interactiva
python main.py  # → Opción 9: Diagnóstico de servicios
```

## 🗂️ Data Sources

| Source | Type | Support |
|--------|------|---------|
| **IOL API** | Live | ✅ Real-time portfolio & prices |
| **Bull Market** | Excel/CSV | ✅ Custom format parsing |
| **Cocos Capital** | Excel/CSV | ✅ Custom format parsing |
| **Generic** | Excel/CSV | ✅ Standard format |
| **BYMA** | API | ✅ CEDEAR ratios & data |
| **Finnhub** | API | ✅ International prices |
| **DolarAPI** | API | ✅ CCL rates |

## 📊 Output Examples

### Console Output

#### Modo Normal (Profesional)
```
📊 Configuración ETL:
   • Threshold: 0.2% (0.002)
   • Timeout: 30s
   • Cache TTL: 180s

📊 Procesando 6 CEDEARs: UNH, SNOW, HMY, FXI, AMGN, BA
🚨 OPORTUNIDAD DETECTADA: UNH - 0.2%

============================================================
📊 ETL COMPLETADO - 1 oportunidades encontradas
============================================================
🚨 UNH: 0.2% - Comprar CEDEAR, vender subyacente

⏱️  Duración: 35098ms
============================================================
```

#### Modo Verbose (Debugging)
```
DEBUG:asyncio:Using selector: KqueueSelector
{"ts": "2025-09-11T21:04:39.289652+00:00", "level": "INFO", "msg": "etl_started", "source": "excel"}
INFO:app.core.services:🏗️  Construyendo servicios con dependency injection...
DEBUG:urllib3.connectionpool:Starting new HTTPS connection (1): finnhub.io:443
DEBUG:urllib3.connectionpool:https://finnhub.io:443 "GET /api/v1/quote?symbol=UNH HTTP/1.1" 200 None
DEBUG:app.services.international_prices:✅ Precio de UNH obtenido desde finnhub: $353.61
INFO:app.services.arbitrage_detector:🚨 OPORTUNIDAD DETECTADA: UNH - 0.2%
```
   • Cache TTL: 180s
   ↳ Sobrescrito por CLI: threshold=0.015, timeout=45s

🚨 OPORTUNIDAD DETECTADA: SPY - 0.5%
🚨 Arbitraje detectado en SPY: 0.5%
```

### JSON Output
```json
{
  "symbol": "SPY",
  "arbitrage_percentage": 0.005,
  "recommendation": "Comprar subyacente, vender CEDEAR",
  "cedear_price_usd": 461.25,
  "underlying_price_usd": 463.89
}
```

## 💾 Database Storage

### 📊 SQLite Database Schema
El sistema guarda todos los datos en una base de datos SQLite (`output/portfolio_data.db`) con 4 tablas principales:

#### `portfolios` - Información del portfolio
- `id`, `timestamp`, `source`, `broker`, `total_positions`
- `total_value_ars`, `total_value_usd`, `ccl_rate`, `execution_time_ms`

#### `positions` - Posiciones individuales
- `portfolio_id`, `symbol`, `quantity`, `conversion_ratio`
- `price_ars`, `price_usd`, `is_cedear`, `underlying_symbol`

#### `arbitrage_opportunities` - Oportunidades detectadas
- `portfolio_id`, `symbol`, `cedear_price_ars`, `underlying_price_usd`
- `arbitrage_percentage`, `recommendation`, `ccl_rate`, `confidence_score`

#### `pipeline_metrics` - Métricas del ETL
- `timestamp`, `execution_time_ms`, `records_processed`
- `opportunities_found`, `sources_status`, `data_quality_score`

### 🔍 Query Examples
```sql
-- Ver últimos portfolios procesados
SELECT id, broker, total_positions, timestamp 
FROM portfolios 
ORDER BY timestamp DESC LIMIT 5;

-- Mejores oportunidades de arbitraje
SELECT symbol, arbitrage_percentage, recommendation 
FROM arbitrage_opportunities 
WHERE arbitrage_percentage > 0.005 
ORDER BY arbitrage_percentage DESC;
```

## 🏗️ Arquitectura del Sistema

### 📦 Estructura del Proyecto
```
📁 proyecto_2/
├── 📁 app/                    # Core biblioteca reutilizable
│   ├── 📁 core/              # DI Container & Config  
│   ├── 📁 services/          # Lógica de negocio (16 servicios)
│   │   ├── arbitrage_detector.py    # Detección de oportunidades
│   │   ├── database_service.py      # 💾 Persistencia SQLite  
│   │   ├── price_fetcher.py         # Obtención de precios
│   │   ├── dollar_rate.py           # Cotización CCL
│   │   └── ...                      # 12 servicios adicionales
│   ├── 📁 integrations/      # APIs externas (IOL, BYMA)
│   ├── 📁 processors/        # Procesamiento de datos
│   ├── 📁 models/            # Modelos de datos
│   ├── 📁 utils/             # Utilidades
│   └── 📁 workflows/         # Flujos interactivos y comandos
│       ├── interactive_flows.py    # Coordinador de flujos interactivos
│       └── 📁 commands/            # Building blocks reutilizables
│           ├── extraction_commands.py
│           ├── analysis_commands.py  
│           └── monitoring_commands.py
│
├── 📁 scripts/               # Herramientas ejecutables independientes
│   ├── etl_cli.py           # Pipeline ETL automático principal
│   ├── download_byma_pdf.py # Descarga datos BYMA
│   └── update_byma_cedeares.py
│
├── 📁 docs/                 # Documentación técnica
├── 📁 output/               # Resultados de análisis y base de datos
│   ├── portfolio_YYYYMMDD_HHMMSS.json  # Portfolio procesado
│   ├── analysis_YYYYMMDD_HHMMSS.json   # Análisis de arbitraje  
│   ├── portfolio_data.db               # 💾 Base de datos SQLite
│   └── status.json                     # Estado última ejecución
├── 📁 backups/              # Versiones anteriores
├── main.py                  # 🖥️ Aplicación interactiva
├── data.csv                 # 📊 Portfolio de ejemplo
└── requirements.txt         # 📦 Dependencias
```

### 🔄 Pipeline de Datos
```
📊 Input Portfolio → 🔍 Detección Formato → 🏦 Procesamiento CEDEARs → 
💰 Obtención Precios → 📈 Análisis Arbitraje → � Guardado BD → �📋 Output JSON
```

### 🧩 Dependency Injection
- **15 servicios especializados** con inyección automática
- **Zero estado global** - inyección de dependencias pura  
- **Validación runtime** - verificación de dependencias al inicio

### 🔧 Gestión de Errores
- **Degradación elegante** - continúa con datos disponibles
- **Múltiples fallbacks** - DolarAPI → IOL → Cache → Estimación teórica
- **Soporte 24/7** - precios teóricos automáticos cuando mercados cerrados
- **Logging estructurado** - reporte detallado de errores

### 🧠 Estimación Inteligente
Cuando datos en tiempo real no disponibles (fines de semana, feriados, fallos API):
1. **Precios internacionales** desde Finnhub (tiempo real)
2. **Tasa CCL** desde DolarAPI (disponible 24/7)
3. **Precio teórico CEDEAR** calculado usando ratios de conversión
4. **Detección arbitraje** continúa seamlessly con precios estimados

## 📚 API Reference

### ETL CLI Options
```bash
--source {excel}              # Data source type
--file FILE                   # Portfolio file path  
--broker {cocos,bullmarket,generic}  # Broker format
--threshold FLOAT             # Arbitrage threshold (default: config)
--timeout INT                 # Request timeout in seconds
--cache-ttl INT              # Cache TTL in seconds  
--output DIR                 # Output directory
--no-save                    # Don't save files
--verbose                    # Modo verbose: logs técnicos completos para debugging
--schedule {2min,30min,1hour,hourly,daily}  # Periodic execution
--health-check               # Solo diagnóstico de servicios (sin ETL)
```

### Schedule Options
- `2min` - Every 2 minutes (testing/demo only)
- `30min` - Every 30 minutes (recommended for development)
- `1hour` / `hourly` - Every hour (recommended for production)
- `daily` - Once per day (daily analysis)

### Configuration Priority
1. **CLI parameters** (highest)
2. **Environment variables** 
3. **`.prefs.json`**
4. **Code defaults** (lowest)

## 🛠️ Desarrollo

### 🔧 Agregar Nuevos Servicios
```python
# 1. Crear servicio en app/services/
class NewService:
    def __init__(self, dependency_service, config=None):
        self.dependency = dependency_service
        self.config = config

# 2. Registrar en app/core/services.py
def build_services(config):
    # ... otros servicios
    new_service = NewService(existing_service, config=config)
    return Services(new_service=new_service, ...)
```

### 🔄 Flujos de Trabajo
- **Interactive flows** (`app/workflows/`) - Para interacción usuario
- **ETL Pipeline** (`scripts/etl_cli.py`) - Para automatización
- **Commands** (`app/workflows/commands/`) - Building blocks reutilizables

### 📊 Formato Portfolio CSV/Excel
```csv
Símbolo,Cantidad,Precio,Broker
AAPL,10,150.0,bullmarket
MSFT,5,300.0,bullmarket
```

## 🧪 Testing y Debugging

### 🔍 Verificar Sistema
```bash
# Health check completo de todos los servicios
python scripts/etl_cli.py --health-check

# Health check con logs técnicos detallados
python scripts/etl_cli.py --health-check --verbose

# Test completo del menú interactivo
python main.py
# Seleccionar opción 9: "Diagnóstico de servicios"

# Test pipeline ETL con datos ejemplo (modo normal)
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket

# Test pipeline ETL con output técnico completo (debugging)
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket --verbose

# Test conexión IOL (requiere credenciales)
python main.py
# Seleccionar opción 1: "Obtener portfolio desde IOL"
```

### 🐛 Debugging Common Issues
```bash
# Error IOL authentication
# ✅ Verificar credenciales en .env
# ✅ Usar opción 9 para diagnosticar conexión

# Error archivo CSV
# ✅ Verificar formato en data.csv ejemplo
# ✅ Especificar --broker correcto

# Error APIs externas
# ✅ Verificar conexión internet
# ✅ Sistema usa fallbacks automáticos
```

## 🧪 Testing

### ✅ Sistema de Testing DI-Compatible
```python
import pytest
from app.core.services import build_services
from app.core.config import Config

def test_arbitrage_detector():
    config = Config.from_env()
    services = build_services(config)
    detector = services.arbitrage_detector
    # Test logic here...

def test_portfolio_processing():
    services = build_services(Config.from_env())
    processor = services.portfolio_processor
    # Test processing logic...
```

### � Casos de Uso Testing
```bash
# 1. Portfolio real IOL (requiere credenciales)
python main.py → opción 1

# 2. Portfolio archivo ejemplo
python main.py → opción 2 → data.csv

# 3. Pipeline ETL completo
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket

# 4. Health check rápido de servicios
python scripts/etl_cli.py --health-check

# 5. Verificación servicios interactiva
python main.py → opción 9
```

## �🚨 Known Issues & Roadmap

### ⚠️ Limitaciones Actuales
- **IOL session expiry**: Re-autenticación requerida periódicamente
- **BYMA PDF dependency**: Actualizaciones manuales para nuevos CEDEARs
- **Test suite**: Migración a pytest con soporte DI en progreso

### 🔮 Roadmap TFM
- [ ] **Testing automatizado** completo con pytest
- [ ] **CI/CD pipeline** con GitHub Actions  
- [ ] **Docker containerization** para deployment
- [ ] **Monitoring y alertas** para producción
- [ ] **API REST** para integración externa

## 📚 Referencias TFM

### 🎓 Contexto Académico
Este proyecto es el **Trabajo Final de Máster (TFM)** para el perfil **Data Engineer**, implementando:

- **Pipeline ETL robusto** con arquitectura de microservicios
- **Gestión avanzada de datos** multi-fuente con fallbacks inteligentes  
- **Procesamiento en tiempo real** y batch con Python asyncio
- **Base de datos SQLite** para persistencia y análisis histórico
- **Dependency Injection** para modularidad y testing
- **Estimación inteligente** cuando datos en tiempo real no disponibles

### 💾 Gestión de Datos
- **Persistencia dual**: JSON (compatibilidad) + SQLite (análisis)
- **Datos históricos**: Track de portfolios y oportunidades en el tiempo
- **Integridad referencial**: Foreign keys entre portfolios, posiciones y arbitrajes
- **Métricas de calidad**: Seguimiento de performance del pipeline ETL
- **Queries analíticos**: Fácil acceso para reportes y modelos ML

### 📊 Métricas del Sistema
- **16 servicios especializados** con inyección de dependencias (incluye DatabaseService)
- **4 fuentes de datos** con fallbacks automáticos
- **2 modos de ejecución** (interactivo + automático)
- **Soporte 24/7** incluso con mercados cerrados
- **Gestión de errores** multi-nivel con degradación elegante
- **4 tablas SQLite** para análisis y reporting completo

---

*Portfolio Replicator TFM - Sistema ETL de detección de arbitraje multi-fuente para mercados financieros*