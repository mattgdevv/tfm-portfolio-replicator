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
from ..services.byma_historical import BYMAHistoricalService
from ..services.unified_analysis import UnifiedAnalysisService
from ..services.variation_analyzer import VariationAnalyzer
from ..processors.cedeares import CEDEARProcessor
from ..processors.file_processor import PortfolioProcessor

logger = logging.getLogger(__name__)


@dataclass
class Services:
    """Container de servicios construidos"""
    arbitrage_detector: ArbitrageDetector
    dollar_service: DollarRateService
    international_service: InternationalPriceService
    byma_service: BYMAHistoricalService
    unified_analysis: UnifiedAnalysisService
    variation_analyzer: VariationAnalyzer
    portfolio_processor: PortfolioProcessor
    cedear_processor: CEDEARProcessor
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
    international_service = InternationalPriceService()
    dollar_service = DollarRateService()
    byma_service = BYMAHistoricalService()
    
    # Servicios con dependencias
    arbitrage_detector = ArbitrageDetector(
        international_service=international_service,
        dollar_service_dep=dollar_service,
        byma_service=byma_service,
        cedear_processor=cedear_processor,
        iol_session=None  # Se configura después cuando sea necesario
    )
    
    unified_analysis = UnifiedAnalysisService(
        arbitrage_detector=arbitrage_detector,
        cedear_processor=cedear_processor,
        international_service=international_service
    )
    
    variation_analyzer = VariationAnalyzer(
        cedear_processor=cedear_processor,
        international_service=international_service,
        dollar_service=dollar_service,
        byma_service=byma_service,
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
    
    logger.info(f"✅ Servicios construidos para mercado: {config.market}")
    
    return Services(
        arbitrage_detector=arbitrage_detector,
        dollar_service=dollar_service,
        international_service=international_service,
        byma_service=byma_service,
        unified_analysis=unified_analysis,
        variation_analyzer=variation_analyzer,
        portfolio_processor=portfolio_processor,
        cedear_processor=cedear_processor,
        config=config
    )


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
            cache_ttl_seconds=60,
            mock_iol=True
        )
    
    logger.info("🧪 Construyendo servicios para testing...")
    return build_services(mock_config)