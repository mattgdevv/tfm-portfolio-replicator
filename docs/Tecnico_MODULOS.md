# Documento Tecnico - Modulos del Sistema

## Modulo Core: Configuracion Centralizada

El módulo `app/core/config.py` implementa una configuración centralizada usando dataclasses para gestionar parámetros del sistema, incluyendo APIs y umbrales.

```python
@dataclass
class Config:
    """Configuracion centralizada para Portfolio Replicator"""
    
    # Mercado
    market: str = "argentina"
    
    # APIs y credenciales (se cargan dinámicamente)
    finnhub_api_key: str = ""
    
    # IOL (se cargan dinámicamente)
    iol_username: str = ""
    iol_password: str = ""
    
    # Fuentes CCL (orden de prioridad)
    ccl_sources: List[str] = field(default_factory=lambda: ["dolarapi", "iol_al30"])
    preferred_ccl_source: str = "dolarapi_ccl"
    
    # Umbrales y configuraciones
    arbitrage_threshold: float = 0.005  # 0.5%
    cache_ttl_seconds: int = 180
    
    # Configuraciones de red
    request_timeout: int = 30
    retry_attempts: int = 3
```

**Aspectos tecnicos:** Utiliza `dataclass` para inmutabilidad y validación automática. El método `from_env()` carga variables de entorno dinámicamente, soportando archivos `.env` con manejo de errores para dependencias opcionales.

## Módulo Services: Detección de Arbitraje

El módulo `app/services/arbitrage_detector.py` contiene la lógica principal para detectar oportunidades de arbitraje entre CEDEARs y activos subyacentes.

```python
class ArbitrageOpportunity:
    """Representa una oportunidad de arbitraje detectada"""
    
    def __init__(self, symbol: str, cedear_price_usd: float, underlying_price_usd: float, 
                 difference_usd: float, difference_percentage: float, ccl_rate: float,
                 cedear_price_ars: float = None, iol_session_active: bool = False):
        self.symbol = symbol
        self.cedear_price_usd = cedear_price_usd
        self.underlying_price_usd = underlying_price_usd
        self.difference_usd = difference_usd
        self.difference_percentage = difference_percentage
        self.ccl_rate = ccl_rate
        self.cedear_price_ars = cedear_price_ars
        self.iol_session_active = iol_session_active
        self.timestamp = datetime.now().isoformat()
        
        # Determinar recomendación basada en diferencia
        if difference_usd > 0:  # CEDEAR más barato
            self.recommendation = "Comprar CEDEAR, vender subyacente"
            self.action = "BUY_CEDEAR"
        else:  # Subyacente más barato
            self.recommendation = "Comprar subyacente, vender CEDEAR"
            self.action = "BUY_UNDERLYING"
```

**Aspectos tecnicos:** Implementa comparación de precios con conversión CCL. Usa `datetime` para timestamps y lógica condicional para recomendaciones. El método `to_dict()` facilita serialización JSON.

## Módulo Services: Obtención Unificada de Precios

El módulo `app/services/price_fetcher.py` unifica la obtención de precios desde multiples fuentes con fallbacks.

```python
class PriceFetcher:
    """
    Servicio unificado para obtención de precios de CEDEARs.
    Elimina duplicación proporcionando interfaz común.
    """

    def __init__(self, cedear_processor: CEDEARProcessor, iol_session=None, byma_integration=None, dollar_service=None, config=None):
        """
        Constructor con dependencias inyectadas.
        """
        self.cedear_processor = cedear_processor
        self.iol_session = iol_session
        self.byma_integration = byma_integration
        self.dollar_service = dollar_service
        self.config = config
        self.timeout = getattr(config, 'request_timeout', 10) if config else 10
        self.mode = "full" if iol_session else "limited"

    def set_iol_session(self, session):
        """Establece sesión IOL para modo completo"""
        self.iol_session = session
        self.mode = "full" if session else "limited"
```

**Aspectos técnicos:** Usa inyeccion de dependencias para flexibilidad. El atributo `mode` cambia dinámicamente basado en disponibilidad de sesión IOL. Maneja timeouts configurables y logging reducido para optimización.

## Módulo Integrations: Integración BYMA

El módulo `app/integrations/byma_integration.py` maneja datos históricos de BYMA, incluyendo CCL y precios de CEDEARs.

```python
class BYMAIntegration:
    """Servicio para obtener datos históricos de BYMA"""
    
    def __init__(self, config=None):
        self.base_url = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free"
        self.timeout = getattr(config, 'request_timeout', 15) if config else 15
        self.session = requests.Session()
        
        # Headers comunes
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Portfolio-Replicator/1.0"
        }
        
        # Cache simple para evitar requests repetidos
        self._cache = {}
        self._cache_timeout = 300  # 5 minutos

    @staticmethod
    def get_last_business_day(reference: Optional[datetime] = None) -> datetime:
        """Devuelve el último día hábil (evita fines de semana y feriados AR si disponible)."""
        return get_last_business_day_by_market("AR", reference)
```

**Aspectos técnicos:** Utiliza `requests.Session()` para conexiones persistentes y optimización. Implementa cache interno con TTL para reducir llamadas API. Maneja días hábiles con lógica de mercado argentino.

## Módulo Processors: Procesamiento de CEDEARs

El módulo `app/processors/cedeares.py` gestiona conversión y ratios de CEDEARs desde datos BYMA.

```python
class CEDEARProcessor:
    def __init__(self):
        self.cedeares_data = self._load_cedeares_data()
        self.cedeares_map = self._build_cedeares_map()
    
    def _load_cedeares_data(self) -> list:
        """Carga los datos de CEDEARs desde el archivo con ratios del PDF de BYMA."""
        data_path = Path(__file__).parent.parent.parent / "byma_cedeares_pdf.json"
        
        if not data_path.exists():
            print("[ERROR] No se encontraron datos de CEDEARs")
            print("🔄 Descargando datos de CEDEARs desde BYMA por primera vez...")
            if self._download_cedeares_data():
                # Reintentar carga después de descarga
                data_path = Path(__file__).parent.parent.parent / "byma_cedeares_pdf.json"
                if not data_path.exists():
                    print("[ERROR] Error: No se pudo descargar los datos de CEDEARs")
                    return []
            else:
                print("[ERROR] Error descargando datos de CEDEARs")
                return []
        
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
```

**Aspectos técnicos:** Usa `Path` para rutas relativas robustas. Implementa descarga automática con `subprocess` y manejo de errores. Carga JSON con encoding UTF-8 para compatibilidad internacional.

## Módulo Models: Modelos de Datos

El módulo `app/models/portfolio.py` define estructuras de datos con validación Pydantic.

```python
class Position(BaseModel):
    symbol: str
    quantity: float
    price: Optional[float] = None
    currency: str
    total_value: Optional[float] = None
    # Campos para conversiones de CEDEARs
    is_cedear: bool = False
    underlying_symbol: Optional[str] = None
    underlying_quantity: Optional[float] = None
    conversion_ratio: Optional[float] = None
    # Campos para FCIs
    is_fci_usd: bool = False
    is_fci_ars: bool = False
    # Campos para cotización del dólar
    dollar_rate: Optional[float] = None
    dollar_source: Optional[str] = None
    total_value_ars: Optional[float] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.total_value is None and self.price is not None:
            self.total_value = self.quantity * self.price
```

**Aspectos técnicos:** Extiende `BaseModel` de Pydantic para validación automática de tipos. Campos opcionales permiten flexibilidad para diferentes tipos de activos. El `__init__` calcula `total_value` automáticamente si no se proporciona.

## Módulo Integrations: Integración IOL

El módulo `app/integrations/iol.py` maneja autenticación OAuth2 y obtención de datos de portfolio desde IOL.

```python
class IOLAuth:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.bearer_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.base_url = "https://api.invertironline.com"

    def get_bearer_token(self) -> str:
        """Get a valid bearer token, refreshing if necessary."""
        if (not self.bearer_token or 
            not self.token_expiry or 
            datetime.now() >= self.token_expiry):
            self._refresh_tokens()
        return self.bearer_token

    def _refresh_tokens(self):
        """Refresh the bearer token using the refresh token."""
        try:
            if not self.refresh_token:
                # Initial token request
                response = requests.post(
                    f"{self.base_url}/token",
                    data={
                        "username": self.username,
                        "password": self.password,
                        "grant_type": "password"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
            else:
                # Refresh existing token
                response = requests.post(
                    f"{self.base_url}/token",
                    data={
                        "refresh_token": self.refresh_token,
                        "grant_type": "refresh_token"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
            
            response.raise_for_status()
            data = response.json()
```

**Aspectos técnicos:** Implementa OAuth2 con manejo de refresh tokens. Usa `requests` para HTTP con validación de expiración automática. Maneja errores con `raise_for_status()` para robustez.

## Módulo Processors: Procesamiento de Archivos

El módulo `app/processors/file_processor.py` procesa archivos Excel/CSV con detección automática de formatos.

```python
class PortfolioProcessor:
    def __init__(self, cedear_processor, dollar_service=None, config=None, verbose=False, debug=False):
        """
        Constructor con Dependency Injection estricta
        
        Args:
            cedear_processor: Procesador de CEDEARs (REQUERIDO)
            dollar_service: Servicio de cotización dólar (OPCIONAL)
            config: Configuración del sistema (OPCIONAL - usa settings por defecto)
            verbose: Logging verbose para mapeo de columnas
            debug: Logging debug detallado
        """
        if cedear_processor is None:
            raise ValueError("cedear_processor es requerido - use build_services() para crear instancias")
            
        # Configuración adicional si es necesaria
        
        self.cedear_processor = cedear_processor
        self.dollar_service = dollar_service
        self.config = config
        self.verbose = verbose
        self.debug = debug
        
    
    async def process_file(self, file_path: str, broker: str = "Unknown") -> Portfolio:
        """Procesa un archivo Excel/CSV y devuelve un Portfolio"""
        print("[INFO] Leyendo archivo")
        
        # Detectar tipo de archivo por extensión
        file_extension = file_path.lower().split('.')[-1]
        
        try:
            if file_extension in ['xlsx', 'xls']:
                # Leer archivo Excel
                print("[DATA] Detectado archivo Excel - leyendo...")
                file = pd.read_excel(file_path)
                print(f"[SUCCESS] Excel leído correctamente. Filas: {len(file)}, Columnas: {len(file.columns)}")
            else:
                # Leer archivo CSV con delimitador principal (cambio: , en lugar de ;)
                file = pd.read_csv(file_path, delimiter=',')
                print(f"[SUCCESS] CSV leído correctamente. Filas: {len(file)}, Columnas: {len(file.columns)}")
```

**Aspectos técnicos:** Usa `pandas` para lectura de archivos con detección automática de extensiones. Implementa validación estricta de dependencias en constructor. Soporta logging verbose/debug para diagnóstico.

## Módulo Services: Servicio de Base de Datos

El módulo `app/services/database_service.py` gestiona persistencia en SQLite con esquema relacional.

```python
class DatabaseService:
    """Servicio para guardar datos del pipeline en base de datos SQLite"""
    
    def __init__(self, db_path: str = "output/portfolio_data.db"):
        """
        Inicializa el servicio de base de datos
        
        Args:
            db_path: Ruta al archivo de base de datos SQLite
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Crea las tablas necesarias si no existen"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabla de portfolios (información general)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    broker TEXT,
                    total_positions INTEGER,
                    total_value_ars REAL,
                    total_value_usd REAL,
                    ccl_rate REAL,
                    execution_time_ms INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
```

**Aspectos técnicos:** Usa `sqlite3` con context managers para conexiones seguras. Implementa `AUTOINCREMENT` y `IF NOT EXISTS` para robustez. Maneja rutas con `Path` y creación automática de directorios.

## Módulo Utils: Días Hábil

El módulo `app/utils/business_days.py` calcula días hábiles considerando feriados por mercado.

```python
def is_business_day_by_market(dt: datetime, market: Market) -> bool:
    if dt.weekday() >= 5:  # 5=Saturday, 6=Sunday
        return False
    return dt.date() not in _get_holidays_for_market(market)

def get_last_business_day_by_market(
    market: Market,
    reference_dt: Optional[datetime] = None,
    days_back: int = 0,
) -> datetime:
    """
    Returns the last business day for a given market, optionally going back N business days.
    """
    current = (reference_dt or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)

    # First, step back 'days_back' business days
    steps_remaining = days_back
    while steps_remaining > 0:
        current -= timedelta(days=1)
```

**Aspectos técnicos:** Usa librería `holidays` para feriados específicos por mercado. Implementa lógica recursiva para retroceder días hábiles. Soporta mercados "AR" y "US" con validación de entrada.

## Módulo Workflows: Flujos Interactivos

El módulo `app/workflows/interactive_flows.py` coordina flujos interactivos con comandos especializados.

```python
class InteractiveFlows:
    """
    Coordinador de flujos interactivos para análisis de portfolios
    
    IMPORTANTE: Este NO es un pipeline ETL automático. Es un coordinador
    de comandos para flujos interactivos que requieren input del usuario.
    
    Para pipelines ETL automáticos usar: scripts/etl_cli.py
    
    Flujos disponibles:
    - Extracción IOL con análisis interactivo
    - Extracción archivo con análisis interactivo  
    - Comandos individuales de monitoreo
    - Comandos individuales de análisis
    """
    
    def __init__(self, services: Services, iol_integration, portfolio_processor):
        """
        Constructor del coordinador de flujos interactivos
        
        Args:
            services: Container de servicios DI completo
            iol_integration: Integración IOL configurada
            portfolio_processor: Procesador de portfolios
        """
        self.services = services
        self.iol_integration = iol_integration
        self.portfolio_processor = portfolio_processor
        
        # Inicializar comandos especializados
        self.extraction = ExtractionCommands(services, iol_integration, portfolio_processor)
        self.analysis = AnalysisCommands(services, iol_integration) 
        self.monitoring = MonitoringCommands(services, iol_integration)
```

**Aspectos técnicos:** Usa inyección de dependencias con container `Services`. Separa responsabilidades en comandos especializados (extraction, analysis, monitoring). Incluye documentación clara sobre su propósito no automático.
