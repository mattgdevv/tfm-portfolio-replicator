# Portfolio Replicator TFM

**Sistema ETL de detección de arbitraje multi-fuente para CEDEARs vs activos subyacentes**



---

## ⚡ Quick Start

```bash
# 1. Clonar e instalar
git clone https://github.com/mattgdevv/tfm-portfolio-replicator.git
cd tfm-portfolio-replicator
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Demo básico (usando archivo ejemplo)
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket

# 3. Portfolio desde IOL (requiere credenciales)
python scripts/etl_cli.py --source iol

# 4. Modo interactivo completo
python main.py

# 5. Health check de servicios
python scripts/etl_cli.py --health-check
```

### **🔑 Para usar IOL API**
```bash
# 1. Configurar credenciales (opcional - también se piden interactivamente)
cp .env.example .env
# Editar IOL_USERNAME e IOL_PASSWORD en .env

# 2. Ejecutar análisis IOL con umbral personalizado
python scripts/etl_cli.py --source iol --threshold 0.01 --verbose
```

## 🎯 Características Principales

### **🚨 Detección Automática de Arbitraje**
- Compara precios CEDEAR vs activo subyacente en tiempo real
- Alertas automáticas cuando diferencia supera umbral configurable
- Recomendaciones de acción específicas

### **📊 Pipeline ETL Multi-fuente**
- **IOL API**: Portfolio real con autenticación OAuth2
- **Excel/CSV**: Bull Market, Cocos Capital, formatos personalizados
- **BYMA**: Ratios oficiales y cotización CCL
- **Finnhub**: Precios internacionales USD

### **💾 Persistencia Estructurada**
- Base de datos SQLite con 4 tablas relacionales
- Tracking histórico de portfolios y oportunidades
- Métricas de pipeline ETL para análisis

### **⏰ Automatización Completa**
- Scheduling configurable: 2min/30min/hourly/daily
- Fallbacks automáticos para disponibilidad 24/7
- Health checks y monitoreo continuo

## � Formatos de Archivo Soportados

### **📋 Brokers Argentinos Soportados**

| Broker | Formato | Columnas Requeridas | Parámetro CLI |
|--------|---------|-------------------|---------------|
| **Bull Market** | Excel/CSV | `Producto`, `Cantidad` | `--broker bullmarket` |
| **Cocos Capital** | Excel/CSV | `instrumento`, `cantidad` | `--broker cocos` |
| **Genérico** | Excel/CSV | `symbol`, `quantity` | `--broker generic` |

### **📝 Formato Bull Market**
```csv/xlsx (Copiar y pegar portfolio - carece de funcionalidad para exportar)
Producto,Cantidad,Ultimo Precio,PPC,Total
"AAPL
CEDEAR APPLE INC","20,00","USD 11,40","USD 4,52","USD 227,91"
"MSFT
CEDEAR MICROSOFT CORP","15,00","USD 8,25","USD 7,10","USD 123,75"
```
- **Producto**: Ticker en primera línea (ej: "AAPL\nCEDEAR APPLE INC")
- **Cantidad**: Formato argentino con comas decimales

### **📝 Formato Cocos Capital**
```csv exportado
instrumento,cantidad,precio,moneda,total
AAPL,20,11.40,USD,228.00
MSFT,15,8.25,USD,123.75
```
- **instrumento**: Ticker directo
- **cantidad**: Número entero o decimal

### **📝 Formato Genérico (Standard)**
```csv
symbol,quantity
AAPL,20,11.40
MSFT,15,8.25
GOOGL,5,45.20
```
- **symbol**: Ticker del CEDEAR
- **quantity**: Cantidad numérica
- **price**: Opcional (se obtiene de APIs)

### **🔧 Detección Automática**
El sistema detecta automáticamente:
- ✅ **Extensiones**: `.xlsx`, `.xls`, `.csv`
- ✅ **Delimitadores CSV**: `,` `;` `\t` (automático)
- ✅ **Formatos numéricos**: Argentino (`1.234,56`) y USA (`1,234.56`)
- ✅ **Tickers multi-línea**: Bull Market format
- ✅ **Encoding**: UTF-8, Latin1 (automático)

### **📊 Ejemplos Completos**

```bash
# Bull Market (requiere especificar broker)
python scripts/etl_cli.py --source excel --file portfolio_bullmarket.xlsx --broker bullmarket

# Cocos Capital
python scripts/etl_cli.py --source excel --file portfolio_cocos.csv --broker cocos

# Formato genérico (cualquier broker)
python scripts/etl_cli.py --source excel --file portfolio_custom.csv --broker generic
```

## �🗂️ Fuentes de Datos Integradas

| Fuente | Propósito | Estado |
|--------|-----------|--------|
| **IOL API** | Portfolio real, precios locales | ✅ OAuth2 |
| **BYMA** | Ratios CEDEARs, CCL oficial | ✅ Público |
| **Finnhub** | Precios internacionales | ✅ API Key |
| **DolarAPI** | Cotización CCL backup | ✅ Libre |

## 📊 Ejemplo de Output

```bash
🚨 OPORTUNIDADES DE ARBITRAJE DETECTADAS:

UNH (UnitedHealth)
├─ CEDEAR: $3,847 ARS  
├─ Subyacente: $353.61 USD ($3,607 ARS equivalente)
├─ Arbitraje: 6.65%
└─ 💡 Recomendación: Vender CEDEAR, comprar subyacente

AAPL (Apple)
├─ CEDEAR: $1,530 ARS
├─ Subyacente: $150.12 USD ($1,531 ARS equivalente)  
├─ Arbitraje: -0.07%
└─ ✅ Precio justo (dentro del umbral)
```

## 🏗️ Arquitectura

### **Capas del Sistema**
```
🖥️  Application Layer    → main.py (interactivo) + etl_cli.py (automático)
🌊  Workflow Layer       → Commands + Interactive Flows  
🏗️  Core Layer          → DI Container + Configuration
🔧  Services Layer       → 15 servicios especializados
🔌  Integration Layer    → APIs externas (IOL, BYMA, Finnhub)
💾  Data Layer          → SQLite + JSON + Portfolio Models
```

### **Tecnologías Clave**
- **Python 3.8+ + asyncio**: Concurrencia eficiente para APIs
- **SQLite**: Persistencia embebida para prototipo académico  
- **Dependency Injection**: 15 servicios modulares con DI estricta
- **Pandas**: Procesamiento de datos financieros
- **requests**: APIs REST síncronas

## 🎯 Dos Modos de Ejecución

### **🖥️ Modo Interactivo** (`main.py`)
- Menú con 5 opciones para exploración manual
- Ideal para análisis, configuración, y demostraciones
- Input interactivo para credenciales y parámetros

### **🤖 Modo ETL Automático** (`scripts/etl_cli.py`)
- CLI parametrizable para pipelines automatizados
- Perfecto para CI/CD, scheduling, y batch processing
- Output estructurado (JSON + SQLite)

## 📊 Casos de Uso

### **📈 Inversor Individual con IOL**
```bash
# Portfolio desde IOL (automático - pide credenciales)
python scripts/etl_cli.py --source iol

# Con umbral personalizado y logs detallados
python scripts/etl_cli.py --source iol --threshold 0.005 --verbose

# Con scheduling automático cada 30 minutos
python scripts/etl_cli.py --source iol --schedule 30min
```

### **📋 Portfolio desde Excel/CSV**
```bash
# Bull Market (especificar broker es importante para parsing correcto)
python scripts/etl_cli.py --source excel --file portfolio_bullmarket.xlsx --broker bullmarket

# Cocos Capital  
python scripts/etl_cli.py --source excel --file portfolio_cocos.csv --broker cocos

# Formato genérico (otros brokers)
python scripts/etl_cli.py --source excel --file portfolio_custom.csv --broker generic

# Con ejecución periódica
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket --schedule hourly
```

### **🔍 Análisis y Monitoreo**
```bash
# Health check completo
python scripts/etl_cli.py --health-check --verbose

# Diagnóstico interactivo
python main.py  # → Opción 4: Diagnóstico servicios
```

## 💾 Base de Datos SQLite

```sql
-- Consultas útiles
SELECT symbol, arbitrage_percentage, recommendation 
FROM arbitrage_opportunities 
WHERE arbitrage_percentage > 0.015 
ORDER BY arbitrage_percentage DESC;

SELECT datetime(timestamp, 'localtime'), total_value_usd 
FROM portfolios 
ORDER BY timestamp DESC LIMIT 5;
```

## ⚙️ Configuración

### **🔑 Credenciales IOL (Opcional)**
```bash
# Opción 1: Variables de entorno
cp .env.example .env
# Editar IOL_USERNAME e IOL_PASSWORD en .env

# Opción 2: Input interactivo (recomendado)
# Al ejecutar con --source iol, pedirá credenciales si no están en .env
python scripts/etl_cli.py --source iol
```

### **⚙️ Parámetros Configurables**
```bash
# Umbral de arbitraje personalizado (default: 0.5%)
--threshold 0.01  # 1%

# Timeout de requests (default: 5s)
--timeout 10

# TTL de cache (default: 300s)
--cache-ttl 600

# Broker específico para archivos (importante para parsing correcto)
--broker bullmarket  # Bull Market
--broker cocos       # Cocos Capital  
--broker generic     # Formato estándar

# Output verbose con logs JSON
--verbose

# Sin guardar archivos, solo mostrar en consola
--no-save
```

### **📅 Scheduling Automático**
```bash
# Opciones disponibles:
--schedule 2min     # Cada 2 minutos
--schedule 30min    # Cada 30 minutos  
--schedule hourly   # Cada hora
--schedule daily    # Diario
```

### **🎛️ Jerarquía de Configuración (prioridad descendente)**
1. **Parámetros CLI** (--threshold, --timeout, etc.)
2. **Variables de entorno** (`.env`)  
3. **Archivo `.prefs.json`** (incluido)
4. **Defaults en código**

## 📚 Documentación TFM

### **📖 Documentación Específica del TFM**
- **[🏗️ Arquitectura Técnica](docs/TFM_ARQUITECTURA.md)** - Componentes, tecnologías, justificaciones
- **[💼 Caso de Negocio](docs/TFM_CASO_NEGOCIO.md)** - Problema, alternativas, valor diferencial  
- **[🚀 Implementación](docs/TFM_IMPLEMENTACION.md)** - Logros vs propuesta, decisiones técnicas
- **[🎥 Guía de Demostración](docs/TFM_DEMOSTRACION.md)** - Script para video de 5 minutos

### **🎓 Contexto Académico**
Este proyecto es el **Trabajo Final de Máster (TFM)** para el perfil **Data Engineer**, implementando:

- **Pipeline ETL** con arquitectura de microservicios
- **Periodicidad configurable** (2min/30min/hourly/daily)  
- **Monitorización completa** con health checks automáticos
- **Base de datos estructurada** lista para modelos ML
- **Gestión de errores** multi-nivel con fallbacks automáticos

## 🛠️ Desarrollo

### **🔧 Agregar Nuevos Servicios**
```python
# 1. Crear en app/services/
class NewService:
    def __init__(self, dependency_service, config=None):
        self.dependency = dependency_service

# 2. Registrar en app/core/services.py  
def build_services(config):
    # ... agregar al container
    return Services(new_service=new_service, ...)
```

### **🧪 Testing y Validación**
```bash
# Verificación DI estricta
python -c "from app.core.validation import validate_project_strict_di; validate_project_strict_di('.')"

# Health check completo
python scripts/etl_cli.py --health-check --verbose
```

## 🎯 Diferenciadores vs Competencia

| Característica | Bloomberg/Reuters | Apps Locales | **Portfolio Replicator** |
|----------------|-------------------|--------------|--------------------------|
| **Detección arbitraje** | ❌ No especializado | ❌ No existe | ✅ **Automática** |
| **Multi-fuente argentino** | ❌ Sin integración local | ❌ Una fuente | ✅ **4 fuentes integradas** |
| **Disponibilidad 24/7** | ✅ Sí | ❌ Horario mercado | ✅ **Fallbacks automáticos** |
| **Costo** | $22,000+ USD/año | Gratuito básico | ✅ **Open source** |

## 🚨 Limitaciones y Roadmap

### **⚠️ Limitaciones Actuales**
- **Alcance geográfico**: Solo Argentina (arquitectura preparada para expansión)
- **Precios delayed**: 15-30 min delay (APIs gratuitas/públicas)
- **IOL tokens**: Gestión automática con refresh según necesidad

### **🔮 Roadmap Futuro**
- [ ] **Extensión Brasil**: BDRs + fuentes locales
- [ ] **Extensión España**: ETFs + BME integration  
- [ ] **API REST**: Exposición como microservicio
- [ ] **Dashboard Web**: UI para monitoreo continuo
- [ ] **ML Models**: Predicción de oportunidades

## 📊 Métricas del Sistema

- **15 servicios especializados** con dependency injection
- **4 fuentes de datos** con fallbacks automáticos
- **4 tablas SQLite** para análisis histórico  
- **2 modos de ejecución** (interactivo + automático)
- **99% disponibilidad** simulada incluso con APIs down
- **2-5 oportunidades** detectadas por semana (promedio)

## 📞 Contacto

**Proyecto TFM**: Portfolio Replicator  
**Autor**: Matteo Giusiano  
**Universidad**: Máster en Data Engineering  
**Año**: 2025

---

*Sistema ETL para detección automática de arbitraje en mercado financiero argentino - Trabajo Final de Máster*
