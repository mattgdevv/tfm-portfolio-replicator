# Arquitectura - Portfolio Replicator 

---

## Resumen 

Portfolio Replicator implementa una arquitectura con inyección de dependencias, con la intención de seguir principios SOLID y aspirar a un pipeline ETL, escalable y mantenible.

##  Arquitectura General

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
🔧  Services Layer        │ Lógica de Negocio (15 servicios)
                          │ ├─ ArbitrageDetector, DatabaseService
                          │ ├─ PriceFetcher, DollarRateService
                          │ ├─ CEDEARProcessor, PortfolioProcessor  
                          │ └─ ... (9 servicios adicionales)
─────────────────────────┼─────────────────────────────────────
🔌  Integration Layer     │ APIs Externas
                          │ ├─ IOLIntegration (Broker argentino)
                          │ ├─ BYMAIntegration (Mercado oficial)
                          │ └─ Finnhub/DolarAPI (Internacional)
─────────────────────────┼─────────────────────────────────────
💾  Data Layer           │ Almacenamiento y Modelos
                          │ ├─ SQLite Database (4 tablas)
                          │ ├─ JSON Output  
                          │ ├─ Pydantic Models (Position, Portfolio)
                          │ └─ Validación automática de datos
```

## 🧩 Componentes Principales

### **1. Core Layer - Dependency Injection/Inyección de Dependencias**

```python
@dataclass
class Services:
    """Container de servicios construidos con DI"""
    arbitrage_detector: ArbitrageDetector
    dollar_service: DollarRateService
    international_service: InternationalPriceService
    byma_integration: BYMAIntegration
    iol_integration: IOLIntegration
    variation_analyzer: VariationAnalyzer  # Implementado completo, sin uso en workflows
    # ... 15 servicios total (14 activos + 1 implementado sin uso)
```

** Factory + DI Container:**
- **Construcción centralizada** vía `build_services()`
- **Validación de dependencias** al inicio
- **Zero estado global** - elimina singletons problemáticos
- **Inyección estricta** - todos los servicios vía constructor

### **2. Services Layer - Servicios**

#### **Detección de Arbitraje**
```python
class ArbitrageDetector:
    def __init__(self, international_service, dollar_service, 
                 byma_integration, cedear_processor, price_fetcher):
        # Validación estricta de dependencias
        if international_service is None:
            raise ValueError("Usar build_services() para DI")
```

#### **Almacenamiento de Datos**
```python
class DatabaseService:
    """Servicio para guardar datos del pipeline en SQLite"""
    def save_portfolio_data(self, portfolio, arbitrage_opportunities):
        # Guarda en 4 tablas relacionales estructuradas
```

#### **Obtención de Precios Multi-fuente**
```python
class PriceFetcher:
    """Servicio unificado con fallbacks automáticos"""
    async def get_price(self, symbol):
        # Finnhub → IOL → Cache → Estimación teórica
```

### **3. Integration Layer - APIs Externas**

#### **IOL Integration (Broker Argentino)**
```python
class IOLIntegration:
    def __init__(self, dollar_service, cedear_processor):
        # Autenticación OAuth2 + sesión persistente
        # Portfolio real en tiempo real
```

#### **BYMA Integration (Mercado Oficial)**
```python
class BYMAIntegration:
    def __init__(self, config):
        # Datos oficiales de ratios CEDEARs
        # CCL histórico y validación de días hábiles
```

### **4. Data Models Layer - Estructuras de Datos (Pydantic)**

#### **Portfolio Models con Validación Automática**
```python
class Position(BaseModel):
    """Posición individual con validación Pydantic"""
    symbol: str                    # Ticker normalizado
    quantity: float               # Cantidad de títulos
    price: Optional[float]        # Precio unitario (ARS/USD)
    currency: str                 # Moneda base
    
    # Campos específicos para CEDEARs
    is_cedear: bool = False
    underlying_symbol: Optional[str]     # AAPL, TSLA, etc.
    underlying_quantity: Optional[float] # Cantidad convertida
    conversion_ratio: Optional[float]    # Ratio de conversión
    
    # Campos para FCIs y cotizaciones
    is_fci_usd: bool = False
    dollar_rate: Optional[float]         # CCL utilizado
    total_value_ars: Optional[float]     # Valor en pesos
```

```python
class Portfolio(BaseModel):
    """Container principal de posiciones"""
    positions: List[Position]     # Lista de posiciones
    broker: Optional[str]         # Origen ("iol", "bullmarket")
    timestamp: datetime           # Timestamp del análisis
    
class ConvertedPortfolio(BaseModel):
    """Portfolio con CEDEARs convertidos a subyacentes"""
    original_positions: List[Position]
    converted_positions: List[Position]
    conversion_summary: dict      # Métricas de conversión
```

**🔧 Ventajas del Diseño:**
- **Validación automática** de tipos y valores vía Pydantic
- **Serialización JSON** nativa para APIs y persistencia
- **Flexibilidad** con campos opcionales para diferentes tipos de activos
- **Extensibilidad** para FCIs, bonos, futuros, etc.
- **Consistency** de datos con validación en tiempo de construcción

### **5. Services Layer - Transformación de Datos (Processors)**

#### **CEDEARProcessor (Servicio)**
- **Conversión automática** CEDEAR → subyacente
- **Ratios de conversión** actualizados desde BYMA
- **Validación de símbolos** y normalización

#### **PortfolioProcessor (Processor)**
- **Procesamiento de archivos**: Excel/CSV con múltiples formatos
- **Detección automática** de formato y delimitadores
- **Mapeo inteligente** de columnas por broker
- **Extracción de CEDEARs**: Escaneado directo sin dependencia de headers
- **Conversión automática**: CEDEAR → activo subyacente
- **Responsabilidad única**: Solo transformación de datos (ETL-Transform)


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

## Pipeline de Datos - Flujo ETL

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
├─ Cache lookup (72h TTL) → cuando Finnhub falla
├─ IOL API (local argentino)
└─ Theoretical pricing (último recurso)
           │
           ▼
📈 ARBITRAGE ANALYSIS
├─ Price comparison (CEDEAR vs underlying)
├─ CCL rate application
├─ Threshold evaluation (configurable)
└─ Opportunity scoring
           │
           ▼
💾 STORAGE & OUTPUT
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
    """Ejemplo de degradación elegante para precios internacionales"""
    try:
        # 1. Fuente principal (Finnhub)
        return await finnhub_service.get_price(symbol)
    except APIException:
        try:
            # 2. Cache local (72h TTL)
            return cache.get_last_known_price(symbol)
        except CacheException:
            # 3. Estimación teórica basada en ratios
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

**Estado Actual del Testing:**
- **Health Checks**: Sistema de monitoreo implementado para validar conectividad de APIs
- **Manual Testing**: Validación manual de flujos completos durante desarrollo
- **Error Handling**: Logging estructurado y manejo de excepciones en todos los servicios

**Testing Framework Preparado:**
- **Arquitectura DI**: Facilita testing futuro con mocks/stubs
- **Servicios Desacoplados**: Cada componente se puede testear independientemente
- **Configuración Flexible**: Permite entornos de testing separados

## 📈 Escalabilidad y Mantenibilidad

### **Características que Facilitan Crecimiento**

#### **🔧 Modularidad Real**
La arquitectura DI actual facilita:
- **Agregar nuevas fuentes de datos**: Sistema de fallback permite incorporar APIs adicionales
- **Testing independiente**: Cada servicio se puede mockear individualmente  
- **Configuración flexible**: Nuevos parámetros vía Config centralizada
- **Logging estructurado**: Observabilidad para debugging en producción

#### **🌍 Limitaciones de Extensión Geográfica**
```python
# ACTUAL: Específico para Argentina
class PortfolioProcessor:
    def _map_bullmarket_format()  # Bull Market Argentina
    def _map_cocos_format()       # Cocos Capital Argentina
    
# REQUERIRÍA: Refactoring significativo para otros mercados
# - Abstracción de brokers
# - Múltiples procesadores de instrumentos (CEDEARs, BDRs, ETFs)
# - Configuración por país/mercado
```

#### **🔌 Fuentes de Datos Extensibles**
```python
# ACTUAL: Sistema de fallback simple pero efectivo
async def get_ccl_rate(self, preferred_source):
    sources = ["dolarapi_ccl", "ccl_al30"]  # Fácil agregar más
    
# FACILITA: Agregar nuevas fuentes sin romper código existente
# REQUIERE: Implementar misma interfaz de retorno
```

### ** Fortalezas para Mantenimiento**

1. **DI Estricta**: Cambios en servicios no afectan dependientes
2. **Configuración Centralizada**: Un solo lugar para ajustes
3. **Fallbacks Automáticos**: Sistema resiliente ante fallas de APIs
4. **Separación de Responsabilidades**: 15 servicios especializados
5. **Validación Automática**: AST checks previenen regresiones arquitectónicas

### ** Limitaciones Actuales**

- **Single-threaded**: asyncio pero no paralelización real
- **SQLite**: Adecuado para prototipo, limitado para otros casos de uso
- **Argentina-específico**: Posibilidad de ampliar cobertura
- **Cache simple**: En memoria, se pierde al reiniciar
- **Sin API REST**: Solo CLI e interactivo

---

## Métricas del Sistema

- **15 servicios especializados** con inyección de dependencias
- **4 fuentes de datos externas** con fallbacks automáticos  
- **4 tablas SQLite** para estructura relacional
- **2 modos de ejecución** (interactivo + automático)
- **6 capas arquitectónicas** bien definidas
- **Zero estado global** - DI pura
- **Sistema de fallbacks** para operación resiliente

---

