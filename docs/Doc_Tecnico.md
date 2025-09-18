Documento Tecnico \- Modulos del Sistema

**Nota:** Este documento se enfoca en una selección representativa de módulos importantes del sistema. Se incluyen los componentes principales para entender la arquitectura principal, omitiendo deliberadamente módulos redundantes o de menor relevancia (por ejemplo, configuraciones de logging/SSL u otras utilidades menores). 

Modulo Core: Configuración Centralizada

El módulo app/core/config.py implementa una configuración centralizada usando dataclasses para gestionar parámetros del sistema, incluyendo APIs y umbrales.

@dataclass  
class Config:  
    """Configuracion centralizada para Portfolio Replicator"""

    \# Mercado  
    market: str \= "argentina"

    \# APIs y credenciales (se cargan dinámicamente)  
    finnhub\_api\_key: str \= ""

    \# IOL (se cargan dinámicamente)  
    iol\_username: str \= ""  
    iol\_password: str \= ""

    \# Fuentes CCL (orden de prioridad)  
    ccl\_sources: List\[str\] \= field(default\_factory=lambda: \["dolarapi", "iol\_al30"\])  
    preferred\_ccl\_source: str \= "dolarapi\_ccl"

    \# Umbrales y configuraciones  
    arbitrage\_threshold: float \= 0.005  \# 0.5%  
    cache\_ttl\_seconds: int \= 180

    \# Configuraciones de red  
    request\_timeout: int \= 30  
    retry\_attempts: int \= 3

**Aspectos tecnicos:** Utiliza dataclass. El método from\_env() carga variables de entorno dinámicamente, soportando archivos .env con manejo de errores para dependencias opcionales.

Módulo Services: Detección de Arbitraje

El módulo app/services/arbitrage\_detector.py contiene la lógica principal para detectar oportunidades de arbitraje entre CEDEARs y activos subyacentes.

class ArbitrageOpportunity:  
    """Representa una oportunidad de arbitraje detectada"""

    def \_\_init\_\_(self, symbol: str, cedear\_price\_usd: float, underlying\_price\_usd: float,   
                 difference\_usd: float, difference\_percentage: float, ccl\_rate: float,  
                 cedear\_price\_ars: float \= None, iol\_session\_active: bool \= False):  
        self.symbol \= symbol  
        self.cedear\_price\_usd \= cedear\_price\_usd  
        self.underlying\_price\_usd \= underlying\_price\_usd  
        self.difference\_usd \= difference\_usd  
        self.difference\_percentage \= difference\_percentage  
        self.ccl\_rate \= ccl\_rate  
        self.cedear\_price\_ars \= cedear\_price\_ars  
        self.iol\_session\_active \= iol\_session\_active  
        self.timestamp \= datetime.now().isoformat()

        \# Determinar recomendación basada en diferencia  
        if difference\_usd \> 0:  \# CEDEAR más barato  
            self.recommendation \= "Comprar CEDEAR, vender subyacente"  
            self.action \= "BUY\_CEDEAR"  
        else:  \# Subyacente más barato  
            self.recommendation \= "Comprar subyacente, vender CEDEAR"  
            self.action \= "BUY\_UNDERLYING"

**Aspectos tecnicos:** Implementa comparación de precios con conversión CCL. Usa datetime para timestamps y lógica condicional para recomendaciones. El método to\_dict() facilita estructurar.JSON.

Módulo Services: Obtención Unificada de Precios

El módulo app/services/price\_fetcher.py unifica la obtención de precios desde múltiples fuentes con fallbacks.

class PriceFetcher:  
    """  
    Servicio unificado para obtención de precios de CEDEARs.  
    Elimina duplicación proporcionando interfaz común.  
    """

    def \_\_init\_\_(self, cedear\_processor: CEDEARProcessor, iol\_session=None, byma\_integration=None, dollar\_service=None, config=None):  
        """  
        Constructor con dependencias inyectadas.  
        """  
        self.cedear\_processor \= cedear\_processor  
        self.iol\_session \= iol\_session  
        self.byma\_integration \= byma\_integration  
        self.dollar\_service \= dollar\_service  
        self.config \= config  
        self.timeout \= getattr(config, 'request\_timeout', 10\) if config else 10  
        self.mode \= "full" if iol\_session else "limited"

    def set\_iol\_session(self, session):  
        """Establece sesión IOL para modo completo"""  
        self.iol\_session \= session  
        self.mode \= "full" if session else "limited"

**Aspectos técnicos:** Usa inyección de dependencias para flexibilidad. El atributo mode cambia dinámicamente basado en disponibilidad de sesión IOL. Maneja timeouts configurables y logging reducido para optimización.

Módulo Services: Servicio de Precios Internacionales

El módulo app/services/international\_prices.py proporciona un servicio para obtener cotizaciones de acciones internacionales a través de la API de Finnhub, con mecanismos de caché y control de llamadas.

class InternationalPriceService:  
    """Servicio para obtener precios de acciones internacionales usando Finnhub"""

    def \_\_init\_\_(self, config=None):  
        \# Configuración mediante config opcional (backward compatible)  
        self.timeout \= config.request\_timeout if config else 10  
        \# Leer API key desde Config o fallback a .env  
        if config and hasattr(config, 'finnhub\_api\_key'):  
            self.finnhub\_api\_key \= config.finnhub\_api\_key  
        else:  
            self.finnhub\_api\_key \= os.getenv("FINNHUB\_API\_KEY")  
        self.finnhub\_base\_url \= "https://finnhub.io/api/v1"

        \# Estado de fuentes  
        self.sources\_status \= {  
            "finnhub": bool(self.finnhub\_api\_key)  
        }

        \# Rate limiting para Finnhub (60 calls/min \= 1 call/segundo)  
        self.last\_finnhub\_call \= 0  
        self.finnhub\_min\_interval \= 1.0  \# segundos

        \# Cache para precios (TTL de 72 horas para cubrir fines de semana)  
        self.\_price\_cache: Dict\[str, Dict\[str, Any\]\] \= {}  
        self.\_cache\_ttl\_hours \= 72  \# 72 horas \= 3 días

    def \_get\_from\_cache(self, symbol: str) \-\> Optional\[Dict\[str, Any\]\]:  
        """Obtiene precio desde caché si está disponible y válido"""  
        if symbol not in self.\_price\_cache:  
            return None

        cached\_data \= self.\_price\_cache\[symbol\]  
        cache\_time \= cached\_data.get('cached\_at')

        if not cache\_time:  
            return None

        \# Verificar si el caché expiró  
        cache\_age \= datetime.now() \- cache\_time  
        if cache\_age \> timedelta(hours=self.\_cache\_ttl\_hours):  
            \# Caché expirado, eliminarlo  
            del self.\_price\_cache\[symbol\]  
            return None

        logger.debug(f"\[CACHE\] Cache hit para {symbol}: ${cached\_data\['price'\]:.2f} USD (age: {cache\_age})")  
        return cached\_data.copy()

**Aspectos técnicos:** Toma la API key de Finnhub de la configuración (o variables de entorno) de forma flexible. Implementa caché interno de precios por **72 horas**, evitando llamadas repetidas a la API durante fines de semana. Controla el *rate limit* de Finnhub asegurando un mínimo de 1 segundo entre consultas. Utiliza un diccionario sources\_status para indicar disponibilidad de fuentes (en este caso Finnhub) y solo habilita consultas si hay API key configurada.

Módulo Services: Analizador de Variaciones

El módulo app/services/variation\_analyzer.py contiene lógica de variación CEDEAR–Subyacente–CCL. Actualmente está implementado pero no integrado al pipeline ETL ni al modo interactivo, por lo que su uso es experimental.

class VariationAnalyzer:  
    """Analizador de variaciones de CEDEARs"""

    def \_\_init\_\_(self, cedear\_processor, international\_service, dollar\_service, byma\_integration, price\_fetcher, iol\_session=None):  
        """  
        Constructor con Dependency Injection estricta

        Args:  
            cedear\_processor: Procesador de CEDEARs (REQUERIDO)  
            international\_service: Servicio de precios internacionales (REQUERIDO)  
            dollar\_service: Servicio de cotización dólar (REQUERIDO)  
            byma\_integration: Servicio BYMA histórico (REQUERIDO)  
            price\_fetcher: Servicio unificado de obtención de precios (REQUERIDO)  
            iol\_session: Sesión IOL para modo completo (opcional)  
        """  
        if cedear\_processor is None:  
            raise ValueError("cedear\_processor es requerido \- use build\_services() para crear instancias")  
        if international\_service is None:  
            raise ValueError("international\_service es requerido \- use build\_services() para crear instancias")  
        if dollar\_service is None:  
            raise ValueError("dollar\_service es requerido \- use build\_services() para crear instancias")  
        if byma\_integration is None:  
            raise ValueError("byma\_integration es requerido \- use build\_services() para crear instancias")  
        if price\_fetcher is None:  
            raise ValueError("price\_fetcher es requerido \- use build\_services() para crear instancias")

        self.iol\_session \= iol\_session  
        self.cedear\_processor \= cedear\_processor  
        self.international\_service \= international\_service  
        self.dollar\_service \= dollar\_service  
        self.byma\_integration \= byma\_integration  
        self.price\_fetcher \= price\_fetcher  
        self.mode \= "full" if iol\_session else "limited"

    def set\_iol\_session(self, session):  
        """Establece la sesión de IOL para modo completo"""  
        self.iol\_session \= session  
        self.mode \= "full" if session else "limited"  
        self.price\_fetcher.set\_iol\_session(session)  \# Sincronizar con PriceFetcher

**Aspectos técnicos:** Emplea inyección de dependencias, requiriendo que se provean todos los servicios necesarios (procesador de CEDEARs, servicio internacional, servicio del dólar, integración BYMA, PriceFetcher) para su inicialización. Mantiene un estado mode similar a PriceFetcher (cambiando a "full" o "limited" según haya sesión IOL activa) y expone set\_iol\_session() para actualizar la sesión. Notablemente, sincroniza la sesión IOL con el PriceFetcher interno (self.price\_fetcher.set\_iol\_session(session)), asegurando que ambos componentes operen en modo consistente. Además, el módulo define un dataclass interno para estructurar los resultados del análisis de variación (e.g. diferencias porcentuales), facilitando la interpretación de los hallazgos. 

Módulo Integrations: Integración BYMA

El módulo app/integrations/byma\_integration.py maneja datos de mercado de BYMA, incluyendo CCL historico y precios de CEDEARs.

class BYMAIntegration:  
    """Servicio para obtener datos históricos de BYMA"""

    def \_\_init\_\_(self, config=None):  
        self.base\_url \= "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free"  
        self.timeout \= getattr(config, 'request\_timeout', 15\) if config else 15  
        self.session \= requests.Session()

        \# Headers comunes  
        self.headers \= {  
            "Content-Type": "application/json",  
            "User-Agent": "Portfolio-Replicator/1.0"  
        }

        \# Cache simple para evitar requests repetidos  
        self.\_cache \= {}  
        self.\_cache\_timeout \= 300  \# 5 minutos

    @staticmethod  
    def get\_last\_business\_day(reference: Optional\[datetime\] \= None) \-\> datetime:  
        """Devuelve el último día hábil (evita fines de semana y feriados AR si disponible)."""  
        return get\_last\_business\_day\_by\_market("AR", reference)

**Aspectos técnicos:** Utiliza requests.Session() para conexiones persistentes y optimización. Implementa caché interno con TTL para reducir llamadas repetidas a la API. Maneja cálculos de días hábiles específicos del mercado argentino mediante utilidades (evitando fines de semana y feriados locales).

Módulo Processors: Procesamiento de CEDEARs

El módulo app/processors/cedeares.py gestiona conversión y ratios de CEDEARs desde datos de BYMA.

class CEDEARProcessor:  
    def \_\_init\_\_(self):  
        self.cedeares\_data \= self.\_load\_cedeares\_data()  
        self.cedeares\_map \= self.\_build\_cedeares\_map()

    def \_load\_cedeares\_data(self) \-\> list:  
        """Carga los datos de CEDEARs desde el archivo con ratios del PDF de BYMA."""  
        data\_path \= Path(\_\_file\_\_).parent.parent.parent / "byma\_cedeares\_pdf.json"

        if not data\_path.exists():  
            print("\[ERROR\] No se encontraron datos de CEDEARs")  
            print("🔄 Descargando datos de CEDEARs desde BYMA por primera vez...")  
            if self.\_download\_cedeares\_data():  
                \# Reintentar carga después de descarga  
                data\_path \= Path(\_\_file\_\_).parent.parent.parent / "byma\_cedeares\_pdf.json"  
                if not data\_path.exists():  
                    print("\[ERROR\] Error: No se pudo descargar los datos de CEDEARs")  
                    return \[\]  
            else:  
                print("\[ERROR\] Error descargando datos de CEDEARs")  
                return \[\]

        with open(data\_path, 'r', encoding='utf-8') as f:  
            return json.load(f)

**Aspectos técnicos:** Usa Path para manejo robusto de rutas relativas. Implementa descarga automática del dataset de CEDEARs utilizando *subprocess* en caso de ausencia local, con manejo de errores en cascada. Carga el archivo JSON con encoding UTF-8 para compatibilidad.

Módulo Models: Modelos de Datos

El módulo app/models/portfolio.py define estructuras de datos con validación Pydantic.

class Position(BaseModel):  
    symbol: str  
    quantity: float  
    price: Optional\[float\] \= None  
    currency: str  
    total\_value: Optional\[float\] \= None  
    \# Campos para conversiones de CEDEARs  
    is\_cedear: bool \= False  
    underlying\_symbol: Optional\[str\] \= None  
    underlying\_quantity: Optional\[float\] \= None  
    conversion\_ratio: Optional\[float\] \= None  
    \# Campos para FCIs  
    is\_fci\_usd: bool \= False  
    is\_fci\_ars: bool \= False  
    \# Campos para cotización del dólar  
    dollar\_rate: Optional\[float\] \= None  
    dollar\_source: Optional\[str\] \= None  
    total\_value\_ars: Optional\[float\] \= None

    def \_\_init\_\_(self, \*\*data):  
        super().\_\_init\_\_(\*\*data)  
        if self.total\_value is None and self.price is not None:  
            self.total\_value \= self.quantity \* self.price

**Aspectos técnicos:** Extiende BaseModel de Pydantic para validación automática de tipos. Los campos opcionales permiten flexibilidad para diferentes tipos de activos (CEDEARs, fondos, etc.). El \_\_init\_\_ calcula total\_value automáticamente si no se proporciona explícitamente, multiplicando cantidad por precio unitario.

Módulo Models: Portfolio Consolidado

En el mismo módulo app/models/portfolio.py, se define la clase Portfolio para representar un portafolio completo compuesto por múltiples posiciones.

class Portfolio(BaseModel):  
    positions: List\[Position\]  
    broker: Optional\[str\] \= None  
    timestamp: datetime \= Field(default\_factory=datetime.now)

**Aspectos técnicos:** Esta clase Pydantic agrupa un conjunto de Position en una sola estructura. El campo timestamp utiliza Field(default\_factory=datetime.now) para establecer automáticamente la fecha y hora de creación del portafolio. De este modo, cada instancia queda sellada temporalmente al momento de su generación. Además, en su configuración interna (class Config), define un ejemplo de esquema (json\_schema\_extra\["example"\]) que ilustra el formato de un portfolio completo.

Módulo Integrations: Integración IOL

El módulo app/integrations/iol.py maneja autenticación OAuth2 y obtención de datos de portfolio desde IOL.

class IOLAuth:  
    def \_\_init\_\_(self, username: str, password: str):  
        self.username \= username  
        self.password \= password  
        self.bearer\_token \= None  
        self.refresh\_token \= None  
        self.token\_expiry \= None  
        self.base\_url \= "https://api.invertironline.com"

    def get\_bearer\_token(self) \-\> str:  
        """Get a valid bearer token, refreshing if necessary."""  
        if (not self.bearer\_token or   
            not self.token\_expiry or   
            datetime.now() \>= self.token\_expiry):  
            self.\_refresh\_tokens()  
        return self.bearer\_token

    def \_refresh\_tokens(self):  
        """Refresh the bearer token using the refresh token."""  
        try:  
            if not self.refresh\_token:  
                \# Initial token request  
                response \= requests.post(  
                    f"{self.base\_url}/token",  
                    data={  
                        "username": self.username,  
                        "password": self.password,  
                        "grant\_type": "password"  
                    },  
                    headers={"Content-Type": "application/x-www-form-urlencoded"}  
                )  
            else:  
                \# Refresh existing token  
                response \= requests.post(  
                    f"{self.base\_url}/token",  
                    data={  
                        "refresh\_token": self.refresh\_token,  
                        "grant\_type": "refresh\_token"  
                    },  
                    headers={"Content-Type": "application/x-www-form-urlencoded"}  
                )

            response.raise\_for\_status()  
            data \= response.json()

**Aspectos técnicos:** Implementa OAuth2 con manejo de *refresh tokens*. Usa requests para llamadas HTTP y verifica expiración de tokens en cada solicitud mediante datetime para refrescarlos cuando sea necesario. Maneja errores con raise\_for\_status().

Módulo Integrations: IOL (Clase IOLIntegration)

Además del flujo de autenticación, el módulo IOL define la clase IOLIntegration, que coordina el inicio de sesión y la extracción de datos de la API de InvertirOnline (IOL) integrandolos al sistema.

class IOLIntegration:  
    def \_\_init\_\_(self, dollar\_service, cedear\_processor, services\_container=None):  
        """  
        Constructor con Dependency Injection estricta

        Args:  
            dollar\_service: Servicio de cotización dólar (REQUERIDO)  
            cedear\_processor: Procesador de CEDEARs (REQUERIDO)  
            services\_container: Container de servicios para notificación automática  
        """  
        if dollar\_service is None:  
            raise ValueError("dollar\_service es requerido \- use build\_services() para crear instancias")  
        if cedear\_processor is None:  
            raise ValueError("cedear\_processor es requerido \- use build\_services() para crear instancias")

        self.auth \= None  
        self.session \= None  
        self.dollar\_service \= dollar\_service  
        self.cedear\_processor \= cedear\_processor  
        self.\_services\_container \= services\_container

    async def authenticate(self, username: str, password: str):  
        """Authenticate with IOL API and notify dependent services."""  
        self.auth \= IOLAuth(username, password)  
        bearer\_token \= self.auth.get\_bearer\_token()

        self.session \= requests.Session()  
        self.session.headers.update({  
            "Authorization": f"Bearer {bearer\_token}",  
            "Content-Type": "application/json"  
        })

        \# Establecer la sesión en el servicio de dólar para CCL AL30  
        self.dollar\_service.set\_iol\_session(self.session)

        \# Notificar automáticamente a servicios dependientes si hay container disponible  
        self.\_notify\_session\_established()

    def \_notify\_session\_established(self):  
        """Notifica a todos los servicios que necesitan la sesión IOL"""  
        if not self.\_services\_container:  
            return

        \# Lista de servicios que necesitan la sesión IOL  
        services\_needing\_session \= \['price\_fetcher', 'arbitrage\_detector', 'variation\_analyzer'\]

        for service\_name in services\_needing\_session:  
            service \= getattr(self.\_services\_container, service\_name, None)  
            if service and hasattr(service, 'set\_iol\_session'):  
                service.set\_iol\_session(self.session)

**Aspectos técnicos:** Aplica inyección de dependencias requiriendo los servicios críticos (cotización del dólar y procesador de CEDEARs) desde su construcción. El método authenticate hace el *login* vía OAuth2 (utilizando IOLAuth internamente) y crea una sesión (requests.Session) con el token obtenido. Esta sesión autenticada se propaga al resto del sistema: se asigna al servicio del dólar (dollar\_service.set\_iol\_session(...) para habilitar la fuente CCL vía AL30) y, mediante \_notify\_session\_established, informa a otros servicios dependientes (PriceFetcher, ArbitrageDetector, VariationAnalyzer) estableciendo la sesión IOL en cada uno (llamando a sus métodos set\_iol\_session si existen). De este modo, tras autenticarse, todos los componentes relevantes operan en *modo completo* con datos en tiempo real de IOL. 

Módulo Processors: Procesamiento de Archivos

El módulo app/processors/file\_processor.py procesa archivos Excel/CSV con detección de formatos.

class PortfolioProcessor:  
    def \_\_init\_\_(self, cedear\_processor, dollar\_service=None, config=None, verbose=False, debug=False):  
        """  
        Constructor con Dependency Injection estricta

        Args:  
            cedear\_processor: Procesador de CEDEARs (REQUERIDO)  
            dollar\_service: Servicio de cotización dólar (OPCIONAL)  
            config: Configuración del sistema (OPCIONAL \- usa settings por defecto)  
            verbose: Logging verbose para mapeo de columnas  
            debug: Logging debug detallado  
        """  
        if cedear\_processor is None:  
            raise ValueError("cedear\_processor es requerido \- use build\_services() para crear instancias")

        \# Configuración adicional si es necesaria

        self.cedear\_processor \= cedear\_processor  
        self.dollar\_service \= dollar\_service  
        self.config \= config  
        self.verbose \= verbose  
        self.debug \= debug

    async def process\_file(self, file\_path: str, broker: str \= "Unknown") \-\> Portfolio:  
        """Procesa un archivo Excel/CSV y devuelve un Portfolio"""  
        print("\[INFO\] Leyendo archivo")

        \# Detectar tipo de archivo por extensión  
        file\_extension \= file\_path.lower().split('.')\[-1\]

        try:  
            if file\_extension in \['xlsx', 'xls'\]:  
                \# Leer archivo Excel  
                print("\[DATA\] Detectado archivo Excel \- leyendo...")  
                file \= pd.read\_excel(file\_path)  
                print(f"\[SUCCESS\] Excel leído correctamente. Filas: {len(file)}, Columnas: {len(file.columns)}")  
            else:  
                \# Leer archivo CSV con delimitador principal (cambio: , en lugar de ;)  
                file \= pd.read\_csv(file\_path, delimiter=',')  
                print(f"\[SUCCESS\] CSV leído correctamente. Filas: {len(file)}, Columnas: {len(file.columns)}")

**Aspectos técnicos:** Usa pandas para lectura de archivos con detección automática de extensiones. Implementa validación estricta de dependencias en el constructor (no permite instancias sin un cedear\_processor). Soporta flags de logging verbose/debug para diagnóstico detallado durante el mapeo de columnas. El método asíncrono process\_file identifica el formato por extensión y aplica el lector adecuado

Módulo Services: Servicio de Base de Datos

El módulo app/services/database\_service.py gestiona almacenamiento en SQLite con esquema relacional.

class DatabaseService:  
    """Servicio para guardar datos del pipeline en base de datos SQLite"""

    def \_\_init\_\_(self, db\_path: str \= "output/portfolio\_data.db"):  
        """  
        Inicializa el servicio de base de datos

        Args:  
            db\_path: Ruta al archivo de base de datos SQLite  
        """  
        self.db\_path \= Path(db\_path)  
        self.db\_path.parent.mkdir(parents=True, exist\_ok=True)  
        self.\_init\_database()

    def \_init\_database(self):  
        """Crea las tablas necesarias si no existen"""  
        with sqlite3.connect(self.db\_path) as conn:  
            cursor \= conn.cursor()

            \# Tabla de portfolios (información general)  
            cursor.execute("""  
                CREATE TABLE IF NOT EXISTS portfolios (  
                    id INTEGER PRIMARY KEY AUTOINCREMENT,  
                    timestamp TEXT NOT NULL,  
                    source TEXT NOT NULL,  
                    broker TEXT,  
                    total\_positions INTEGER,  
                    total\_value\_ars REAL,  
                    total\_value\_usd REAL,  
                    ccl\_rate REAL,  
                    execution\_time\_ms INTEGER,  
                    created\_at TEXT DEFAULT CURRENT\_TIMESTAMP  
                )  
            """)

**Aspectos técnicos:** Usa sqlite3 con context managers para asegurar cierre correcto de la conexión. Crea el directorio de la base de datos automáticamente con Path.mkdir si no existe. En la inicialización, construye las tablas necesarias utilizando SQL con IF NOT EXISTS. Los campos almacenan información agregada del portafolio (valores totales, tasa CCL utilizada, tiempo de ejecución, etc.), aprovechando AUTOINCREMENT para la clave primaria y timestamp.

Módulo Utils: Días Hábil

El módulo app/utils/business\_days.py calcula días hábiles considerando feriados por mercado.

def is\_business\_day\_by\_market(dt: datetime, market: Market) \-\> bool:  
    if dt.weekday() \>= 5:  \# 5=Saturday, 6=Sunday  
        return False  
    return dt.date() not in \_get\_holidays\_for\_market(market)

def get\_last\_business\_day\_by\_market(  
    market: Market,  
    reference\_dt: Optional\[datetime\] \= None,  
    days\_back: int \= 0,  
) \-\> datetime:  
    """  
    Returns the last business day for a given market, optionally going back N business days.  
    """  
    current \= (reference\_dt or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)

    \# First, step back 'days\_back' business days  
    steps\_remaining \= days\_back  
    while steps\_remaining \> 0:  
        current \-= timedelta(days=1)  
        if is\_business\_day\_by\_market(current, market):  
            steps\_remaining \-= 1

**Aspectos técnicos:** Usa la librería holidays para consultar feriados específicos según el mercado. Implementa lógica de retroceso recursivo: la función get\_last\_business\_day\_by\_market permite obtener el último día hábil a partir de una fecha de referencia, retrocediendo tantos días hábiles como se indique.

Módulo Workflows: Flujos Interactivos

El módulo app/workflows/interactive\_flows.py coordina flujos interactivos con comandos especializados.

class InteractiveFlows:  
    """  
    Coordinador de flujos interactivos para análisis de portfolios

    IMPORTANTE: Este NO es un pipeline ETL automático. Es un coordinador  
    de comandos para flujos interactivos que requieren input del usuario.

    Para pipelines ETL automáticos usar: scripts/etl\_cli.py

    Flujos disponibles:  
    \- Extracción IOL con análisis interactivo  
    \- Extracción archivo con análisis interactivo    
    \- Comandos individuales de monitoreo  
    \- Comandos individuales de análisis  
    """

    def \_\_init\_\_(self, services: Services, iol\_integration, portfolio\_processor):  
        """  
        Constructor del coordinador de flujos interactivos

        Args:  
            services: Container de servicios DI completo  
            iol\_integration: Integración IOL configurada  
            portfolio\_processor: Procesador de portfolios  
        """  
        self.services \= services  
        self.iol\_integration \= iol\_integration  
        self.portfolio\_processor \= portfolio\_processor

        \# Inicializar comandos especializados  
        self.extraction \= ExtractionCommands(services, iol\_integration, portfolio\_processor)  
        self.analysis \= AnalysisCommands(services, iol\_integration)   
        self.monitoring \= MonitoringCommands(services, iol\_integration)

**Aspectos técnicos:** Utiliza inyección de dependencias con el contenedor de servicios Services. Separa responsabilidades en comandos especializados (extracción, análisis, monitoreo) instanciando clases dedicadas para cada grupo de operaciones. Incluye documentación clara en el docstring de la clase enfatizando que se trata de flujos manuales, no un pipeline automático, sugiriendo usar scripts ETL separados para automatización. Esto asegura que las responsabilidades queden bien delimitadas entre procesos interactivos y procesos ETL.

Módulo Services: Servicio de Cotización del Dólar

El módulo app/services/dollar\_rate.py ofrece un servicio para obtener la cotización del dólar (principalmente el dólar CCL) utilizando múltiples fuentes con prioridad y mecanismos de fallback.

class DollarRateService:  
    """Servicio para obtener cotizaciones del dólar con múltiples fuentes"""

    def \_\_init\_\_(self, config=None):  
        \# Configuración mediante config opcional (backward compatible)  
        if config:  
            self.timeout \= getattr(config, 'request\_timeout', 30\)  \# Usar 30s por defecto en lugar de 10  
            self.\_cache\_ttl\_seconds \= getattr(config, 'cache\_ttl\_seconds', 300\)  \# 5 minutos por defecto  
            self.preferred\_ccl\_source \= getattr(config, 'preferred\_ccl\_source', 'dolarapi\_ccl')  
        else:  
            \# Valores por defecto mejorados para mantener compatibilidad  
            self.timeout \= 30  \# Aumentado de 10 a 30 segundos  
            self.\_cache\_ttl\_seconds \= 300  \# Aumentado de 180 a 300 segundos (5 minutos)  
            self.preferred\_ccl\_source \= 'dolarapi\_ccl'

        self.sources\_status \= {  
            "dolarapi\_ccl": True,  
            "ccl\_al30": False,  \# Requiere autenticación IOL  
            "dolarapi\_mep": True,  
            \# CCL implícito Yahoo eliminado para simplicidad  
        }  
        self.last\_health\_check \= {}  
        self.iol\_session \= None  \# Sesión de IOL para CCL AL30  
        \# Cache en memoria (TTL corto)  
        self.\_cache: Dict\[str, Dict\[str, Any\]\] \= {}

    def set\_iol\_session(self, session):  
        """Establece la sesión de IOL para poder usar CCL AL30"""  
        self.iol\_session \= session  
        self.sources\_status\["ccl\_al30"\] \= session is not None  
        if session:  
            logger.info("🔐 Sesión IOL establecida \- CCL AL30 disponible")  
        else:  
            logger.info("🔓 Sesión IOL no disponible \- CCL AL30 deshabilitado")

**Aspectos técnicos:** Carga parámetros de configuración (timeout, TTL de caché, fuente preferida) con valores por defecto seguros si no se proporciona config. Mantiene un diccionario sources\_status para indicar qué fuentes de cotización están habilitadas: por defecto activa fuentes públicas (dolarapi\_ccl para CCL dólar MEP/CCL vía *dolarapi* y dolarapi\_mep), mientras deshabilita ccl\_al30 hasta tener una sesión IOL disponible (ya que requiere autenticación para obtener CCL vía bono AL30). Dispone de un caché en memoria de corto plazo (5 minutos) para evitar consultas frecuentes. El método set\_iol\_session() activa o desactiva dinámicamente la fuente ccl\_al30 según se establezca una sesión autenticada, registrando en logs si la fuente de AL30 quedó habilitada (🔐) o deshabilitada (🔓). Un método no mostrado (get\_ccl\_rate) implementa la estrategia de *fallback*: intenta la fuente preferida configurada y, en caso de falla o indisponibilidad, recurre a fuentes alternativas (por ejemplo, si dolarapi\_ccl falla pero ccl\_al30 está disponible con sesión, la emplea). Esto garantiza resiliencia en la obtención de la cotización del dólar crucial para los cálculos del sistema.

---

