# Portfolio Replicator

**Sistema ETL para detección automática de arbitraje entre CEDEARs argentinos y activos subyacentes internacionales**

*Trabajo Final de Máster - Perfil Data Engineering*

---

## Instalación Rápida

```bash
# Clonar repositorio e instalar dependencias
git clone https://github.com/mattgdevv/tfm-portfolio-replicator.git
cd tfm-portfolio-replicator
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configurar API necesaria
cp .env.example .env
# Editar FINNHUB_API_KEY en .env (obtener gratis en https://finnhub.io/)

# Demo inmediato con datos de ejemplo (portfolio.csv sample para --broker cocos)
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket
```

## Funcionalidades Principales

- **🎯 Deteccion automática de arbitraje** entre CEDEARs y activos subyacentes
- **📊 Pipeline ETL multi-fuente** (IOL, Excel/CSV, BYMA, Finnhub)
- **⏰ Ejecucion programada** (2min/30min/hourly/daily)
- **💾 Almacenamiento** en SQLite + JSON
- **🔄 Sistema de fallbacks** para operación 24/7
- **🏥 Health checks automáticos** y monitoreo

## Modos de Ejecución

### Modo Automático (CLI)
**Optimizado para automatizacion y pipelines CI/CD**

```bash
# Análisis desde IOL (requiere credenciales)
python scripts/etl_cli.py --source iol --threshold 0.01 --verbose

# Análisis desde archivo - (cargar archivo a directorio o usar data.csv)
python scripts/etl_cli.py --source excel --file portfolio.xlsx --broker bullmarket

# Ejecución programada cada 30 minutos
python scripts/etl_cli.py --source iol --schedule 30min

# Health check del sistema
python scripts/etl_cli.py --health-check --verbose
```

### Modo Interactivo
**Para analisis exploratorio con menu paso a paso**

```bash
python main.py
```

Opciones del menú interactivo:
1. **📥 IOL → Analisis → Guardado** (con confirmaciones)
2. **📄 Archivo → Analisis → Guardado** (con validaciones)  
3. **🔄 Actualizar ratios CEDEARs** (desde PDF BYMA)
4. **🏥 Diagnostico completo** (estado de servicios)
5. **🚪 Salir**

## 📊 Formatos de Portfolio Soportados

| Broker | Comando | Ejemplo |
|--------|---------|---------|
| **Bull Market** | `--broker bullmarket` | `python scripts/etl_cli.py --source excel --file portfolio.xlsx --broker bullmarket` |
| **Cocos Capital** | `--broker cocos` | `python scripts/etl_cli.py --source excel --file portfolio.csv --broker cocos` |
| **Formato Genérico** | `--broker generic` | `python scripts/etl_cli.py --source excel --file portfolio.csv --broker generic` |
| **IOL API** | `--source iol` | `python scripts/etl_cli.py --source iol --threshold 0.005` |

### Detección Automática
- **Extensiones**: `.xlsx`, `.xls`, `.csv`
- **Delimitadores**: `,`, `;`, `\t` (detección inteligente)
- **Encoding**: UTF-8
- **Columnas requeridas**: Solo ticker y cantidad

## ⚙️ Configuración

### APIs Requeridas

```bash
# 1. Finnhub API (OBLIGATORIO)
# Registro gratuito en: https://finnhub.io/
# Editar en .env: FINNHUB_API_KEY=tu_key

# 2. IOL API (OPCIONAL - solo para --source iol)
# Editar en .env: IOL_USERNAME=usuario, IOL_PASSWORD=password
```

### Fuentes de Datos

| Fuente | Propósito | Autenticación |
|--------|-----------|---------------|
| **Finnhub** | Precios internacionales USD | API Key (gratis) |
| **IOL API** | Portfolio real, precios locales | OAuth2 (credenciales) |
| **BYMA** | Ratios CEDEARs, CCL oficial | Pública |
| **DolarAPI** | Cotización CCL backup | Libre |

## 📈 Ejemplo de Resultados (Al momento, recomedanciones superficiales)

```
OPORTUNIDADES DE ARBITRAJE DETECTADAS:

UNH (UnitedHealth)
├─ CEDEAR: $3,847 ARS  
├─ Subyacente: $353.61 USD ($3,607 ARS equivalente)
├─ Arbitraje: 6.65%
└─ Recomendación: Vender CEDEAR, comprar subyacente

AAPL (Apple)
├─ CEDEAR: $1,530 ARS
├─ Subyacente: $150.12 USD ($1,531 ARS equivalente)  
├─ Arbitraje: -0.07%
└─ Precio equilibrado (dentro del umbral)
```

## 🔧 Parámetros CLI Completos

### Parámetros Principales
```bash
--source [iol|excel]        # Fuente de datos (requerido)
--file ARCHIVO             # Archivo para source excel (requerido si excel)
--broker [tipo]            # bullmarket|cocos|generic (default: generic)
--health-check             # Solo verificación de estado del sistema
```

### Parametros de Configuracion
```bash
--threshold 0.01           # Umbral arbitraje (default: 0.5%)
--timeout 10               # Timeout requests en segundos (default: 5s)
--cache-ttl 600           # TTL cache en segundos (default: 300s)
--output DIR              # Directorio salida (default: output/)
--schedule [freq]         # Periodicidad: 2min|30min|hourly|daily
--verbose                 # Logging JSON detallado
--no-save                # Solo análisis, sin guardar archivos
```

### Ejemplos Completos
```bash
# Análisis completo con todas las opciones
python scripts/etl_cli.py --source excel --file portfolio.xlsx \
  --broker bullmarket --threshold 0.01 --verbose --output results/

# Monitoreo programado cada 30 minutos
python scripts/etl_cli.py --source iol --schedule 30min \
  --threshold 0.005 --verbose

# Testing rápido sin guardar
python scripts/etl_cli.py --source excel --file portfolio.csv \
  --broker cocos --no-save --verbose

# Health check completo
python scripts/etl_cli.py --health-check --verbose
```

## 🏗️ Arquitectura

### Capas del Sistema
```
🖥️  Application    → main.py + etl_cli.py
🌊  Workflow       → Commands + Interactive Flows  
🏗️  Core           → DI Container + Configuration
🔧  Services       → 15 servicios (14 activos + análisis de variaciones*)
🔌  Integration    → APIs externas (IOL, BYMA, Finnhub)
💾  Data           → SQLite + JSON + Models
```

**Tecnologías**: Python 3.8+, asyncio, SQLite, Pandas, DI

## 💾 Base de Datos y Output

### Estructura SQLite (4 tablas)
- **portfolios**: Información general del análisis
- **positions**: Posiciones individuales del portfolio
- **arbitrage_opportunities**: Oportunidades detectadas
- **pipeline_metrics**: Métricas de ejecución

### Output Generado
```bash
output/
├── portfolio_data.db          # Base de datos SQLite
├── status.json               # Estado última ejecución
├── portfolio_YYYYMMDD_HHMMSS.json  # Datos del portfolio
└── analysis_YYYYMMDD_HHMMSS.json   # Resultados de análisis
```

### Consultas SQL Útiles
```sql
-- Ver oportunidades de arbitraje
SELECT symbol, arbitrage_percentage, recommendation 
FROM arbitrage_opportunities 
WHERE arbitrage_percentage > 0.01 
ORDER BY arbitrage_percentage DESC;
```

## 🔍 Troubleshooting

### Problemas Comunes

**Error: "Finnhub API key required"**
```bash
# Solución: Configurar API key obligatoria
echo "FINNHUB_API_KEY=tu_key_aqui" >> .env
```

**Error: "IOL authentication failed"**
```bash
# Solución: Verificar credenciales IOL
python scripts/etl_cli.py --health-check --verbose
```

**Warning: "No opportunities found"**
```bash
# Normal - reducir threshold para más sensibilidad
python scripts/etl_cli.py --source excel --file portfolio.csv --threshold 0.001
```

## 📚 Documentación Adicional

- **[Arquitectura Técnica](docs/TFM_ARQUITECTURA.md)** - Diseño completo del sistema

### Notas Técnicas
(*) El servicio de análisis de variaciones está implementado pero preparado para desarrollo futuro


