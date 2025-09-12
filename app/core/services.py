"""
Factory para construcción de servicios con dependency injection
"""

from dataclasses import dataclass
from typing import Optional
import logging

from .config import Config
from ..services.arbitrage_detector import ArbitrageDetector
from ..services.dollar_rate import DollarRateService
from ..services.international_prices import InternationalPriceService
from ..integrations.byma_integration import BYMAIntegration
from ..integrations.iol import IOLIntegration
from ..services.unified_analysis import UnifiedAnalysisService
from ..services.variation_analyzer import VariationAnalyzer
from ..services.price_fetcher import PriceFetcher
from ..services.file_service import FileService
from ..services.config_service import ConfigService
from ..services.portfolio_display_service import PortfolioDisplayService
from ..services.file_processing_service import FileProcessingService
from ..services.database_service import DatabaseService
from ..processors.cedeares import CEDEARProcessor
from ..processors.file_processor import PortfolioProcessor

logger = logging.getLogger(__name__)


@dataclass
class Services:
    """Container de servicios construidos"""
    arbitrage_detector: ArbitrageDetector
    dollar_service: DollarRateService
    international_service: InternationalPriceService
    byma_integration: BYMAIntegration
    iol_integration: IOLIntegration
    unified_analysis: UnifiedAnalysisService
    variation_analyzer: VariationAnalyzer
    price_fetcher: PriceFetcher
    portfolio_processor: PortfolioProcessor
    cedear_processor: CEDEARProcessor
    file_service: FileService
    config_service: ConfigService
    portfolio_display_service: PortfolioDisplayService
    file_processing_service: FileProcessingService
    database_service: DatabaseService
    config: Config


def build_services(config: Optional[Config] = None) -> Services:
    """
    Construye todos los servicios con dependency injection
    
    Args:
        config: Configuración del sistema (usa Config.from_env() si no se pasa)
        
    Returns:
        Services: Container con todos los servicios configurados
    """
    if config is None:
        config = Config.from_env()
    
    config.validate()
    
    logger.info("🏗️  Construyendo servicios con dependency injection...")
    
    # Servicios base (sin dependencias)
    cedear_processor = CEDEARProcessor()
    international_service = InternationalPriceService(config=config)
    dollar_service = DollarRateService(config=config)
    byma_integration = BYMAIntegration(config=config)

    price_fetcher = PriceFetcher(
        cedear_processor=cedear_processor,
        iol_session=None,  # Se configura después cuando sea necesario
        byma_integration=byma_integration,
        dollar_service=dollar_service,
        config=config
    )

    # Servicios con dependencias
    arbitrage_detector = ArbitrageDetector(
        international_service=international_service,
        dollar_service_dep=dollar_service,
        byma_integration=byma_integration,
        cedear_processor=cedear_processor,
        price_fetcher=price_fetcher,
        iol_session=None,  # Se configura después cuando sea necesario
        config=config
    )
    
    unified_analysis = UnifiedAnalysisService(
        arbitrage_detector=arbitrage_detector,
        cedear_processor=cedear_processor,
        international_service=international_service,
        config=config
    )
    
    variation_analyzer = VariationAnalyzer(
        cedear_processor=cedear_processor,
        international_service=international_service,
        dollar_service=dollar_service,
        byma_integration=byma_integration,
        price_fetcher=price_fetcher,
        iol_session=None  # Se configura después cuando sea necesario
    )

    portfolio_processor = PortfolioProcessor(
        cedear_processor=cedear_processor,
        dollar_service=dollar_service,
        arbitrage_detector=arbitrage_detector,
        variation_analyzer=variation_analyzer,
        config=config,
        verbose=False,  # Configurable en futuro
        debug=False     # Configurable en futuro
    )
    
    # Crear servicios auxiliares
    file_service = FileService()
    file_processing_service = FileProcessingService(portfolio_processor)
    database_service = DatabaseService()  # Base de datos para resultados ETL
    
    # Crear servicios que necesitan el container completo (se pasa después)
    services_container = Services(
        arbitrage_detector=arbitrage_detector,
        dollar_service=dollar_service,
        international_service=international_service,
        byma_integration=byma_integration,
        iol_integration=None,  # Se crea después
        unified_analysis=unified_analysis,
        variation_analyzer=variation_analyzer,
        price_fetcher=price_fetcher,
        portfolio_processor=portfolio_processor,
        cedear_processor=cedear_processor,
        file_service=file_service,
        config_service=None,  # Se crea después
        portfolio_display_service=None,  # Se crea después
        file_processing_service=file_processing_service,
        database_service=database_service,
        config=config
    )
    
    # Crear servicios que necesitan acceso al container completo
    config_service = ConfigService(services_container, config=config)
    
    # Para portfolio_display_service necesitamos importar IOL integration
    from ..integrations.iol import IOLIntegration
    iol_integration = IOLIntegration(
        dollar_service=dollar_service,
        cedear_processor=cedear_processor
    )
    portfolio_display_service = PortfolioDisplayService(services_container, iol_integration, cedear_processor)
    
    # Actualizar el container con los servicios completos
    services_container.config_service = config_service
    services_container.portfolio_display_service = portfolio_display_service
    services_container.iol_integration = iol_integration
    
    logger.info(f"✅ Servicios construidos para mercado: {config.market}")
    
    return services_container


def build_test_services(mock_config: Optional[Config] = None) -> Services:
    """
    Construye servicios para testing con mocks/configuración específica
    
    Args:
        mock_config: Configuración específica para tests
        
    Returns:
        Services: Container con servicios para testing
    """
    if mock_config is None:
        mock_config = Config(
            market="test",
            arbitrage_threshold=0.01,  # 1% para tests
            cache_ttl_seconds=60
        )
    
    logger.info("🧪 Construyendo servicios para testing...")
    return build_services(mock_config)