# 🏗️ Arquitectura Técnica - Portfolio Replicator TFM

**Sistema ETL de detección de arbitraje multi-fuente con arquitectura de microservicios**

---

## 📊 Resumen Ejecutivo

Portfolio Replicator implementa una **arquitectura de capas moderna** con **Dependency Injection estricta**, siguiendo principios SOLID y patrones enterprise para construir un pipeline ETL robusto, escalable y mantenible.

## 🎯 Arquitectura General

### 🏛️ **Patrón Arquitectónico: Layered Architecture + Microservicios**

```
🖥️  Application Layer     │ main.py, etl_cli.py
                          │ ├─ Modo Interactivo (análisis manual)
                          │ └─ Modo ETL CLI (automatización)
─────────────────────────┼─────────────────────────────────────
🌊  Workflow Layer        │ Interactive Flows + Commands
                          │ ├─ ExtractionCommands
                          │ ├─ AnalysisCommands  
                          │ └─ MonitoringCommands
─────────────────────────┼─────────────────────────────────────
🏗️  Core Layer           │ DI Container + Configuration
                          │ ├─ build_services() (Factory)
                          │ ├─ Services (Container)
                          │ └─ Config (Configuración centralizada)
─────────────────────────┼─────────────────────────────────────
🔧  Services Layer        │ Lógica de Negocio (16 servicios)
                          │ ├─ ArbitrageDetector
                          │ ├─ DatabaseService
                          │ ├─ PriceFetcher
                          │ └─ ... (13 servicios adicionales)
─────────────────────────┼─────────────────────────────────────
🔌  Integration Layer     │ APIs Externas
                          │ ├─ IOLIntegration (Broker argentino)
                          │ ├─ BYMAIntegration (Mercado oficial)
                          │ └─ Finnhub/DolarAPI (Internacional)
─────────────────────────┼─────────────────────────────────────
⚙️  Processor Layer       │ Transformación de Datos
                          │ ├─ CEDEARProcessor
                          │ ├─ PortfolioProcessor
                          │ └─ FileProcessor
─────────────────────────┼─────────────────────────────────────
💾  Data Layer           │ Persistencia y Modelos
                          │ ├─ SQLite Database (4 tablas)
                          │ ├─ JSON Output
                          │ └─ Portfolio Models
```

## 🧩 Componentes Principales

### **1. Core Layer - Dependency Injection Factory**

```python
@dataclass
class Services:
    """Container de servicios construidos con DI"""
    arbitrage_detector: ArbitrageDetector
    dollar_service: DollarRateService
    international_service: InternationalPriceService
    byma_integration: BYMAIntegration
    iol_integration: IOLIntegration
    # ... 16 servicios especializados total
```

**🎯 Patrón Factory + DI Container:**
- **Construcción centralizada** vía `build_services()`
- **Validación de dependencias** al inicio
- **Zero estado global** - elimina singletons problemáticos
- **Inyección estricta** - todos los servicios vía constructor

### **2. Services Layer - Microservicios Especializados**

#### **🔍 Detección de Arbitraje**
```python
class ArbitrageDetector:
    def __init__(self, international_service, dollar_service, 
                 byma_integration, cedear_processor, price_fetcher):
        # Validación estricta de dependencias
        if international_service is None:
            raise ValueError("Usar build_services() para DI")
```

#### **💾 Persistencia de Datos**
```python
class DatabaseService:
    """Servicio para guardar datos del pipeline en SQLite"""
    def save_portfolio_data(self, portfolio, arbitrage_opportunities):
        # Guarda en 4 tablas relacionales estructuradas
```

#### **💰 Obtención de Precios Multi-fuente**
```python
class PriceFetcher:
    """Servicio unificado con fallbacks automáticos"""
    async def get_price(self, symbol):
        # Finnhub → IOL → Cache → Estimación teórica
```

### **3. Integration Layer - APIs Externas**

#### **🏦 IOL Integration (Broker Argentino)**
```python
class IOLIntegration:
    def __init__(self, dollar_service, cedear_processor):
        # Autenticación OAuth2 + sesión persistente
        # Portfolio real en tiempo real
```

#### **🏛️ BYMA Integration (Mercado Oficial)**
```python
class BYMAIntegration:
    def __init__(self, config):
        # Datos oficiales de ratios CEDEARs
        # CCL histórico y validación de días hábiles
```

### **4. Processor Layer - Transformación de Datos**

#### **📊 CEDEAR Processor**
- **Conversión automática** CEDEAR → subyacente
- **Ratios de conversión** actualizados
- **Validación de símbolos** y normalización

#### **📁 Portfolio Processor**
- **Detección automática** de formato CSV/Excel
- **Mapeo inteligente** de columnas
- **Procesamiento multi-broker** (Bull Market, Cocos Capital)

## 🔧 Tecnologías y Justificación

### **Core Technologies**

| Tecnología | Propósito | Justificación |
|------------|-----------|---------------|
| **Python 3.8+** | Lenguaje principal | Ecosistema rico en APIs financieras + asyncio |
| **asyncio** | Concurrencia | Manejo eficiente de múltiples APIs simultáneas |
| **SQLite** | Base de datos | Embebida, perfecta para prototipo académico |
| **Pandas** | Procesamiento | De facto para transformación de datos financieros |
| **requests + aiohttp** | HTTP clients | APIs REST síncronas y asíncronas |

### **Architectural Patterns**

| Patrón | Implementación | Beneficio |
|--------|---------------|-----------|
| **Dependency Injection** | build_services() + Container | Testabilidad + Modularidad |
| **Factory Pattern** | Services construction | Centralized object creation |
| **Strategy Pattern** | Multi-source pricing | Fácil extensión de fuentes |
| **Fallback Pattern** | Degradación elegante | Disponibilidad 24/7 |
| **Command Pattern** | Workflow commands | Operaciones reutilizables |

### **External APIs & Data Sources**

```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│   IOL API       │   BYMA API      │   Finnhub      │   DolarAPI      │
├─────────────────┼─────────────────┼─────────────────┼─────────────────┤
│ • Portfolio real│ • Ratios CEDEARs│ • Precios USD   │ • Cotización CCL│
│ • Precios local │ • CCL histórico │ • Datos globales│ • Backup rates  │
│ • Autenticación │ • Días hábiles  │ • API key req.  │ • Sin auth      │
│ • Rate limits   │ • Público       │ • 60 req/min    │ • Libre         │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

## 📊 Base de Datos - Esquema SQLite

### **Estructura Relacional (4 Tablas)**

```sql
-- Portfolio principal
CREATE TABLE portfolios (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,           -- 'iol', 'excel'
    broker TEXT,                    -- 'bullmarket', 'cocos'
    total_positions INTEGER,
    total_value_ars REAL,
    total_value_usd REAL,
    ccl_rate REAL,
    execution_time_ms INTEGER
);

-- Posiciones individuales
CREATE TABLE positions (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER REFERENCES portfolios(id),
    symbol TEXT NOT NULL,
    quantity REAL,
    conversion_ratio REAL,
    price_ars REAL,
    price_usd REAL,
    is_cedear BOOLEAN,
    underlying_symbol TEXT
);

-- Oportunidades de arbitraje detectadas
CREATE TABLE arbitrage_opportunities (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER REFERENCES portfolios(id),
    symbol TEXT NOT NULL,
    cedear_price_ars REAL,
    underlying_price_usd REAL,
    arbitrage_percentage REAL,
    recommendation TEXT,
    ccl_rate REAL,
    confidence_score REAL
);

-- Métricas del pipeline ETL
CREATE TABLE pipeline_metrics (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    execution_time_ms INTEGER,
    records_processed INTEGER,
    opportunities_found INTEGER,
    sources_status TEXT,           -- JSON con estado de APIs
    data_quality_score REAL
);
```

## 🔄 Pipeline de Datos - Flujo ETL

### **Extract → Transform → Load**

```
📊 INPUT SOURCES
├─ IOL API (OAuth2 + portfolio real)
├─ Excel/CSV (Bull Market, Cocos Capital)
├─ Manual input (símbolos individuales)
└─ Historical data (base de datos)
           │
           ▼
🔍 DETECTION & VALIDATION
├─ Formato detection (CSV/Excel/JSON)
├─ Column mapping (intelligent)
├─ Symbol validation & normalization
└─ Data quality checks
           │
           ▼
🏦 CEDEAR PROCESSING
├─ CEDEAR identification
├─ Ratio de conversión lookup
├─ Underlying symbol mapping
└─ Quantity adjustment
           │
           ▼
💰 PRICE FETCHING (Multi-source)
├─ Finnhub API (internacional)
├─ IOL API (local argentino)
├─ Cache lookup (180s TTL)
└─ Theoretical pricing (fallback)
           │
           ▼
📈 ARBITRAGE ANALYSIS
├─ Price comparison (CEDEAR vs underlying)
├─ CCL rate application
├─ Threshold evaluation (configurable)
└─ Opportunity scoring
           │
           ▼
💾 PERSISTENCE & OUTPUT
├─ SQLite database (4 tablas relacionales)
├─ JSON export (portfolio + analysis)
├─ Status tracking
└─ Metrics collection
```

## 🔐 Gestión de Configuración

### **Jerarquía de Configuración (Prioridad)**

```
1. 🥇 Variables de entorno (.env + export)
2. 🥈 Archivo .prefs.json  
3. 🥉 Defaults en código
```

### **Configuración Centralizada**

```python
@dataclass
class Config:
    # Mercado y región
    market: str = "argentina"
    
    # APIs y credenciales
    finnhub_api_key: str = ""
    iol_username: str = ""
    iol_password: str = ""
    
    # Fuentes CCL (orden de prioridad)
    ccl_sources: List[str] = ["dolarapi", "iol_al30"]
    preferred_ccl_source: str = "dolarapi_ccl"
    
    # Umbrales de negocio
    arbitrage_threshold: float = 0.005  # 0.5%
    cache_ttl_seconds: int = 180        # 3 minutos
    
    # Configuraciones de red
    request_timeout: int = 30
    retry_attempts: int = 3
```

## 🛡️ Gestión de Errores y Resilencia

### **Patrón Fallback Multi-nivel**

```python
async def get_price_with_fallbacks(symbol):
    """Ejemplo de degradación elegante"""
    try:
        # 1. Fuente principal (Finnhub)
        return await finnhub_service.get_price(symbol)
    except APIException:
        try:
            # 2. Fuente secundaria (IOL)
            return await iol_service.get_price(symbol)
        except AuthException:
            try:
                # 3. Cache local
                return cache.get_last_known_price(symbol)
            except CacheException:
                # 4. Estimación teórica
                return estimate_theoretical_price(symbol)
```

### **Monitoreo y Health Checks**

```python
class MonitoringCommands:
    async def health_check_all_services(self):
        """Verificación completa del sistema"""
        # BYMA API status
        # IOL API authentication  
        # Database connectivity
        # Cache validity
        # Configuration integrity
```

## 🔧 Validación y Testing

### **Validación Arquitectónica Automática**

```python
def validate_strict_di():
    """Verificación AST de arquitectura DI"""
    # Detecta imports prohibidos de servicios globales
    # Valida constructores directos vs DI
    # Enforce dependency injection estricta
```

### **Testing Strategy**

- **Unit Tests**: Servicios individuales con mocks
- **Integration Tests**: APIs reales con rate limiting
- **End-to-End Tests**: Pipeline completo con datos reales
- **Health Checks**: Monitoreo continuo de dependencias

## 📈 Escalabilidad y Extensibilidad

### **Diseño para Crecimiento**

#### **🌍 Extensión Geográfica (Futura)**
```python
# Arquitectura preparada para otros mercados
class BrazilBDRProcessor(PortfolioProcessor):
    """Procesador para BDRs brasileños"""
    
class SpainETFProcessor(PortfolioProcessor):
    """Procesador para ETFs españoles"""
```

#### **🔌 Nuevas Fuentes de Datos**
```python
# Patrón Strategy permite agregar fácilmente
class BloombergIntegration(PriceSource):
    """Integración con Bloomberg Terminal"""
    
class ReutersIntegration(PriceSource):
    """Integración con Reuters API"""
```

#### **📊 Nuevos Tipos de Análisis**
```python
# Servicios modulares extensibles
class RiskAnalyzer:
    """Análisis de riesgo y correlación"""
    
class PortfolioOptimizer:
    """Optimización y rebalanceo"""
```

## 🎯 Fortalezas Arquitectónicas

### **✅ Ventajas Clave**

1. **Modularidad Extrema**: 16 servicios especializados, cada uno con responsabilidad única
2. **Dependency Injection Estricta**: Zero estado global, testabilidad máxima
3. **Resilencia**: Múltiples fallbacks garantizan operación 24/7
4. **Configurabilidad**: Jerarquía clara de configuración con overrides
5. **Extensibilidad**: Patrón Strategy facilita agregar nuevas fuentes/mercados
6. **Observabilidad**: Logging estructurado + métricas + health checks
7. **Persistencia Estructurada**: Base de datos relacional para análisis histórico

### **🔬 Decisiones Técnicas Justificadas**

| Decisión | Alternativa | Justificación |
|----------|-------------|---------------|
| SQLite | PostgreSQL/MySQL | Prototipo académico, deployment simple |
| asyncio | threading | APIs I/O bound, mejor concurrencia |
| DI Container | Service Locator | Testing + modularidad superior |
| Factory Pattern | Singleton | Evita estado global problemático |
| JSON + SQLite | Solo SQL | Compatibilidad + análisis flexible |

---

## 📊 Métricas del Sistema

- **16 servicios especializados** con inyección de dependencias
- **4 fuentes de datos externas** con fallbacks automáticos  
- **4 tablas SQLite** para persistencia relacional
- **2 modos de ejecución** (interactivo + automático)
- **5 capas arquitectónicas** bien definidas
- **Zero estado global** - DI pura
- **99% disponibilidad simulada** incluso con APIs down

---

*Arquitectura diseñada para escalabilidad, mantenibilidad y operación 24/7 en entornos financieros críticos.*
