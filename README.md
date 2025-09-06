# Portfolio Replicator MVP

Sistema completo para análisis de portfolios y detección de arbitraje entre CEDEARs y activos subyacentes con múltiples fuentes de datos y fallbacks robustos.

## 🚀 Features

- **📊 Multi-source Portfolio Import**: IOL API + Excel/CSV con procesamiento AI (Gemini)
- **🔄 CEDEAR → Underlying Conversion**: Conversión automática con ratios BYMA reales
- **⚡ Arbitrage Detection**: Detección de oportunidades con precios en tiempo real
- **🛡️ Robust Fallbacks**: Múltiples fuentes con fallback automático (Finnhub, DolarAPI, IOL)
- **📈 Real-time CCL**: Cotización CCL desde múltiples fuentes con cache inteligente
- **🤖 Headless ETL**: Scheduler ETL con JSON structured logging y exit codes determinísticos
- **🧪 Mock Mode**: MOCK_IOL=1 para testing sin credenciales
- **📊 JSON Lines Logging**: Logs estructurados parseables para CI/CD

## 🛠️ Quick Start

### 1. Setup
```bash
git clone <repository-url>
cd portfolio-replicator
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Opcional: crear .env para APIs
cp .env.example .env
# Configurar: IOL_USERNAME, IOL_PASSWORD, FINNHUB_API_KEY, GEMINI_API_KEY
```

### 3. Uso

#### 🖥️ Modo Interactivo
```bash
python main.py
```

#### 📁 ETL Headless (Excel)
```bash
python scripts/scheduler.py --run-once --source excel --file data/sample.csv
```

#### 🤖 ETL Mock (Sin credenciales)
```bash
MOCK_IOL=1 python scripts/scheduler.py --run-once --source iol --seed 42
```

#### ⏰ ETL Periodico (Cron)
```bash
# Cada 15 minutos
*/15 * * * * TZ=America/Argentina/Buenos_Aires /ruta/venv/bin/python /ruta/scripts/scheduler.py --run-once --source excel --file /ruta/data/sample.csv >> /ruta/logs/etl.log 2>&1
```

## 📋 Menu Interactivo

1. **Obtener portfolio desde IOL** - Autenticación y descarga en tiempo real
2. **Cargar portfolio desde Excel/CSV** - Procesamiento AI con Gemini 
3. **Ver lista de CEDEARs disponibles** - Catálogo BYMA actualizado
4. **Configurar fuente de cotización CCL** - DolarAPI vs IOL AL30
5. **Salir**
6. **Actualizar/chequear registro de CEDEARs (BYMA)** - Refresh catálogo
7. **Probar análisis de variaciones de CEDEARs** - Testing individual  
8. **Refrescar CCL (ignorar cache)** - Force refresh CCL rate

## 🤖 ETL Scheduler

### Comandos Disponibles
```bash
# Ayuda
python scripts/scheduler.py --help

# Excel ETL
python scripts/scheduler.py --run-once --source excel --file /path/to/portfolio.csv

# IOL Real (con credenciales)
IOL_USER=usuario IOL_PASS=password python scripts/scheduler.py --run-once --source iol

# IOL Mock (sin credenciales)
MOCK_IOL=1 python scripts/scheduler.py --run-once --source iol --seed 42

# Custom threshold
python scripts/scheduler.py --run-once --source excel --file data/sample.csv --arbitrage-threshold 0.01
```

### Output Files
- `output/status.json` - Estado del último run
- `output/portfolio_YYYYMMDD_HHMMSS.json` - Datos del portfolio
- `output/analysis_YYYYMMDD_HHMMSS.json` - Resultados de arbitraje

### Exit Codes
- `0` = Success
- `1` = Configuration error  
- `2` = Authentication error
- `3` = Data processing error

## 🗂️ Data Sources & Fallbacks

### Fuentes de Datos
- **📊 Portfolio Data**: IOL API + Excel/CSV (Gemini AI processing)
- **💰 CEDEAR Prices (ARS)**: BYMA API (tiempo real)  
- **📈 Underlying Prices (USD)**: Finnhub API
- **💱 CCL Rate**: DolarAPI → IOL AL30 (estrategia robusta)
- **🏦 CEDEAR Catalog**: BYMA API actualizado

### Fallback Logic
- **Finnhub**: Principal para precios internacionales
- **BYMA → Finnhub+CCL**: Fallback para CEDEARs no listados en BYMA
- **DolarAPI → IOL**: Fallback automático para CCL
- **MOCK_IOL**: Fixtures locales para testing sin credenciales

## 🛡️ Estrategia Robusta CCL (Contado con Liquidación)

### ¿Por qué es importante el CCL?

El **CCL (Contado con Liquidación)** es fundamental para el análisis de variaciones de CEDEARs porque:

1. **Separar efectos**: Distinguir si el movimiento de un CEDEAR se debe al tipo de cambio o al activo subyacente
2. **Análisis preciso**: Si CCL sube 2% y un CEDEAR sube 5%, el activo realmente subió ~3%
3. **Detección de arbitrajes**: Identificar discrepancias entre el movimiento esperado vs. real

### Estrategia de Fallback Robusta

**Tiempo Real:**
1. **🥇 DolarAPI** (primario) - Más confiable y rápido
2. **🥈 IOL AL30/AL30D** (secundario) - Requiere autenticación pero muy preciso

**Histórico:**
- **BYMA únicamente** - Datos históricos confiables con web scraping

### Fuentes Detalladas

#### 1. DolarAPI (Primario)
- **URL**: `https://dolarapi.com/v1/dolares/contadoconliqui`
- **Ventajas**: Rápido, confiable, no requiere autenticación
- **Desventajas**: Dependiente de servicio externo

#### 2. IOL AL30/AL30D (Secundario)
- **Cálculo**: `CCL = AL30 (ARS) / AL30D (USD)`
- **Ventajas**: Muy preciso, calculado en tiempo real
- **Desventajas**: Requiere autenticación IOL

#### 3. Yahoo CCL Implícito (Terciario)
- **Cálculo**: `CCL = (Precio_CEDEAR_ARS × Ratio) / Precio_US_USD`
- **Símbolos**: AAPL, MSFT, TSLA, SPY (mediana para robustez)
- **Ventajas**: Siempre disponible, robusto contra outliers
- **Desventajas**: Puede ser bloqueado por rate limits

#### 4. BYMA Histórico
- **Web scraping** de datos históricos BYMA
- **Función**: `get_last_business_day()` para días hábiles
- **Fallback**: Busca 1-2 días hábiles anteriores si fecha exacta no disponible

### Configuración

En `.env` o `.prefs.json`:
```json
{
  "PREFERRED_CCL_SOURCE": "dolarapi_ccl"  // o "ccl_al30"
}
```

### Cache y Performance

- **TTL**: 3 minutos por fuente
- **Estrategia**: Cache por fuente individual
- **Refresh manual**: Opción 8 del menú principal

### Manejo de Errores

- **Silencioso**: Solo muestra error final si todas las fuentes fallan
- **Informativo**: Indica qué fuente se usó cuando hay fallback
- **Resiliente**: Yahoo con reintentos y rate limiting inteligente

### Ejemplo de Uso

```python
from app.services.dollar_rate import dollar_service

# Automático con fallback
ccl_result = await dollar_service.get_ccl_rate()
print(f"CCL: ${ccl_result['rate']:.2f}")
print(f"Fuente: {ccl_result['source_name']}")
print(f"Fallback usado: {ccl_result['fallback_used']}")
```

### Análisis de Variación

El sistema calcula automáticamente:
```
Variación_CCL = (CCL_actual - CCL_ayer) / CCL_ayer
```

**Clasificación del Impacto:**
- 🟢 **< 0.5%**: MÍNIMA - Movimientos CEDEAR son del activo
- 🟡 **0.5% - 1.5%**: MODERADA - Puede afectar algunos CEDEARs  
- 🔴 **> 1.5%**: SIGNIFICATIVA - Explica gran parte de movimientos CEDEAR

## ETL headless (SQLite/Parquet/metrics)

Ejecutar una corrida única de ETL (lee Excel/CSV, re‑precia con BYMA→Yahoo y exporta a `output/`):

```bash
PYTHONPATH=. python scripts/run_etl_once.py --source excel --file /ruta/portfolio.xlsx
```

## Scheduler & Alertas

Scheduler (APScheduler) para ejecutar ETL y/o evaluación de alertas periódicamente.

Instalación (una vez):
```bash
python -m pip install -r requirements.txt
```

Run-once (smoke):
```bash
PYTHONPATH=. python scripts/scheduler.py --source excel --file "/ruta/portfolio.xlsx" --run-once
```

Programar ETL cada 30 minutos:
```bash
PYTHONPATH=. python scripts/scheduler.py --source excel --file "/ruta/portfolio.xlsx" --interval-minutes 30
```

Activar job de alertas (Excel) cada 30 min con umbral 0.5%:
```bash
PYTHONPATH=. python scripts/scheduler.py --source excel \
  --file "/ruta/portfolio.xlsx" \
  --interval-minutes 60 \
  --alerts-enabled \
  --alerts-interval-minutes 30 \
  --arbitrage-threshold 0.005
```

Variables de entorno alternativas (sin flags):
- También podés definir defaults en `.prefs.json` (la app los lee como fallback) con las claves:
  `SCHEDULER_SOURCE`, `SCHEDULER_FILE`, `SCHEDULER_INTERVAL_MINUTES`, `SCHEDULER_TIMEZONE`, `SCHEDULER_JITTER_SECONDS`,
  `ALERTS_ENABLED`, `ALERTS_INTERVAL_MINUTES`, `ARBITRAGE_THRESHOLD`.

One‑off de alertas desde menú principal:
- En `main.py`, opción “Evaluar alertas ahora (Excel)” para una evaluación inmediata con umbral configurable.

Monitoreo del scheduler:
- PID de proceso en `.scheduler.pid` (para iniciar/detener desde el menú)
- Logs en `output/scheduler.log`
- Estado rápido desde la consola:
  ```bash
  [ -f .scheduler.pid ] && ps -p "$(cat .scheduler.pid)" >/dev/null && echo RUNNING || echo STOPPED
  ```
  Alternativa sin usar el PID file:
  ```bash
  pgrep -f "scripts/scheduler.py" >/dev/null && echo RUNNING || echo STOPPED
  ```

### `.prefs.json` (defaults locales)

La app puede leer defaults desde `.prefs.json` (fallback si no pasás flags). Claves soportadas:

- `PREFERRED_CCL_SOURCE`:
  - Fuente CCL por defecto. Valores posibles: `dolarapi_ccl`, `ccl_al30`.
- `SCHEDULER_SOURCE`:
  - Fuente del portfolio para la ETL. Valores: `excel` (actualmente soportado) o `iol` (futuro).
- `SCHEDULER_FILE`:
  - Ruta absoluta del Excel/CSV del portfolio.
- `SCHEDULER_INTERVAL_MINUTES`:
  - Cada cuántos minutos corre la ETL. Default: 60.
- `SCHEDULER_TIMEZONE`:
  - Zona horaria del scheduler. Default: `UTC`.
- `SCHEDULER_JITTER_SECONDS`:
  - Desincronización aleatoria máxima (en segundos) aplicada al intervalo para evitar colisiones si corrés múltiples instancias. Si no sabés, dejalo en 0.
- `ALERTS_ENABLED`:
  - Habilita el job de alertas periódico (basado en Excel). `true`/`false`.
- `ALERTS_INTERVAL_MINUTES`:
  - Cada cuántos minutos corre el job de alertas. Default: 30.
- `ARBITRAGE_THRESHOLD`:
  - Umbral de porcentaje para alertas de arbitraje (e.g., 0.005 = 0.5%).
- `CEDEAR_CACHE_TTL_SECONDS`:
  - TTL de cache in‑memory para precios CEDEAR (segundos). Default recomendado: 180.

Ejemplo:

```json
{
  "PREFERRED_CCL_SOURCE": "dolarapi_ccl",
  "SCHEDULER_SOURCE": "excel",
  "SCHEDULER_FILE": "/Users/you/portfolio.xlsx",
  "SCHEDULER_INTERVAL_MINUTES": 60,
  "SCHEDULER_TIMEZONE": "UTC",
  "SCHEDULER_JITTER_SECONDS": 0,
  "ALERTS_ENABLED": false,
  "ALERTS_INTERVAL_MINUTES": 30,
  "ARBITRAGE_THRESHOLD": 0.005
}
```

## Scripts útiles (utils/)

- `utils/update_byma_cedeares.py`: descarga el listado de CEDEARs desde BYMA y guarda `byma_cedeares.json`.

  Uso:
  ```bash
  PYTHONPATH=. python utils/update_byma_cedeares.py
  ```

- `utils/byma_api_test.py`: testea el endpoint CEDEARs de BYMA, imprime muestra, estadísticas y guarda `byma_cedeares.json`.

  Uso:
  ```bash
  PYTHONPATH=. python utils/byma_api_test.py
  ```

## Notes

- Fines de semana/feriados: se usan cierres más recientes; utilitario `get_last_business_day()` listo para futuros históricos.
- Caché CCL: 3 minutos por fuente; opción 8 permite refrescar manualmente.

## Logging

Logs are written to `logs/portfolio.log` with daily rotation and 7-day retention.

## Project Structure

```
.
├── configs/
│   └── portfolio_config.json
├── pipeline/
│   ├── broker_api.py
│   ├── config_manager.py
│   ├── loader.py
│   ├── logger.py
│   ├── market_data.py
│   ├── notifier.py
│   ├── portfolio_pipeline.py
│   ├── scheduler.py
│   └── transformer.py
├── scripts/
│   └── make_portfolio_config.py
├── main.py
├── requirements.txt
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 