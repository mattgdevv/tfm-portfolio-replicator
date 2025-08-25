#!/usr/bin/env python3
"""
Scheduler ETL simplificado para Portfolio Replicator
Ejecuta análisis one-shot con output estructurado y exit codes determinísticos
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Configurar logging estructurado (JSON Lines)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def log_event(level: str, msg: str, **kwargs):
    """Log estructurado en formato JSON Lines"""
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "msg": msg,
        **kwargs
    }
    print(json.dumps(event))

def write_status(status: Dict[str, Any], output_dir: Path):
    """Escribe status.json con schema fijo"""
    status_file = output_dir / "status.json"
    status_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(status_file, 'w') as f:
        json.dump(status, f, indent=2)

def parse_args():
    """Parse argumentos CLI"""
    parser = argparse.ArgumentParser(
        description="Portfolio Replicator ETL - Ejecución única",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Excel con MOCK
  python scheduler.py --run-once --source excel --file data/sample.xlsx
  
  # IOL con MOCK (sin credenciales)
  MOCK_IOL=1 python scheduler.py --run-once --source iol
  
  # IOL real (con credenciales)
  IOL_USER=user IOL_PASS=pass python scheduler.py --run-once --source iol
        """
    )
    
    parser.add_argument(
        "--run-once", 
        action="store_true", 
        required=True,
        help="Ejecutar ETL una sola vez y salir"
    )
    
    parser.add_argument(
        "--source", 
        choices=["excel", "iol"], 
        required=True,
        help="Fuente de datos del portfolio"
    )
    
    parser.add_argument(
        "--file", 
        type=str,
        help="Archivo Excel/CSV (requerido si --source excel)"
    )
    
    parser.add_argument(
        "--arbitrage-threshold", 
        type=float, 
        default=0.015,
        help="Umbral de arbitraje (default: 0.015 = 1.5%%)"
    )
    
    parser.add_argument(
        "--output-dir", 
        type=Path, 
        default=Path("output"),
        help="Directorio de salida (default: output/)"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        help="Seed para MOCK_IOL (reproducibilidad en tests)"
    )
    
    return parser.parse_args()

def validate_args(args):
    """Valida argumentos y configuración"""
    if args.source == "excel" and not args.file:
        log_event("ERROR", "validation_failed", reason="--file required for --source excel")
        return False
        
    if args.source == "excel" and not Path(args.file).exists():
        log_event("ERROR", "validation_failed", reason=f"File not found: {args.file}")
        return False
    
    return True

async def run_etl(args) -> Dict[str, Any]:
    """
    Ejecuta ETL completo y retorna status
    """
    start_time = time.time()
    
    try:
        # Importar módulos necesarios
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        from app.processors.file_processor import PortfolioProcessor
        from app.services.unified_analysis import UnifiedAnalysisService
        from app.services.arbitrage_detector import ArbitrageDetector
        from app.services.dollar_rate import DollarRateService
        
        log_event("INFO", "etl_started", source=args.source, threshold=args.arbitrage_threshold)
        
        # 1. Configurar procesadores
        portfolio_processor = PortfolioProcessor()
        unified_analysis = UnifiedAnalysisService()
        dollar_service = DollarRateService()
        
        # 2. Obtener portfolio según fuente
        if args.source == "excel":
            log_event("INFO", "loading_portfolio", source="excel", file=args.file)
            portfolio = await portfolio_processor.process_file(args.file, broker="ETL")
            
        elif args.source == "iol":
            if os.getenv("MOCK_IOL") == "1":
                log_event("INFO", "loading_portfolio", source="iol_mock")
                portfolio = await load_mock_iol_portfolio(args)
            else:
                log_event("INFO", "loading_portfolio", source="iol_real")
                portfolio = await load_real_iol_portfolio(args)
        
        if not portfolio or not portfolio.positions:
            raise ValueError("Portfolio vacío o inválido")
        
        log_event("INFO", "portfolio_loaded", 
                 positions=len(portfolio.positions),
                 cedeares=len([p for p in portfolio.positions if p.is_cedear]))
        
        # 3. Ejecutar análisis de arbitraje
        log_event("INFO", "arbitrage_analysis_started", threshold=args.arbitrage_threshold)
        
        analysis_result = await unified_analysis.analyze_portfolio(
            portfolio, 
            threshold=args.arbitrage_threshold
        )
        
        opportunities = analysis_result.get("arbitrage_opportunities", [])
        
        log_event("INFO", "arbitrage_analysis_completed",
                 opportunities_found=len(opportunities),
                 threshold=args.arbitrage_threshold)
        
        # 4. Guardar resultados
        await save_etl_results(args.output_dir, portfolio, analysis_result, args)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        log_event("INFO", "etl_finished", 
                 source=args.source,
                 duration_ms=duration_ms,
                 opportunities=len(opportunities))
        
        return {
            "last_run_ok": True,
            "last_error": None,
            "last_run_at": datetime.now(timezone.utc).isoformat(),
            "source": args.source,
            "duration_ms": duration_ms,
            "opportunities_found": len(opportunities),
            "positions_analyzed": len(portfolio.positions)
        }
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        
        log_event("ERROR", "etl_failed", 
                 source=args.source,
                 error=error_msg,
                 duration_ms=duration_ms)
        
        return {
            "last_run_ok": False,
            "last_error": error_msg,
            "last_run_at": datetime.now(timezone.utc).isoformat(),
            "source": args.source,
            "duration_ms": duration_ms
        }

async def load_mock_iol_portfolio(args):
    """Carga portfolio desde fixtures MOCK_IOL"""
    import random
    
    log_event("INFO", "mock_iol_loading", seed=args.seed)
    
    # Configurar seed para reproducibilidad
    if args.seed:
        random.seed(args.seed)
    
    # Simular latencia si está configurada
    mock_latency_ms = int(os.getenv("MOCK_LATENCY_MS", "100"))
    if mock_latency_ms > 0:
        await asyncio.sleep(mock_latency_ms / 1000)
        log_event("INFO", "mock_latency_simulated", latency_ms=mock_latency_ms)
    
    # Simular errores si está configurado
    mock_fail_rate = float(os.getenv("MOCK_FAIL_RATE", "0.0"))
    if mock_fail_rate > 0 and random.random() < mock_fail_rate:
        raise Exception(f"MOCK_IOL: Simulated failure (rate: {mock_fail_rate})")
    
    # Cargar portfolio desde fixtures
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "iol"
    portfolio_file = fixtures_dir / "portfolio_sample.json"
    
    if not portfolio_file.exists():
        raise FileNotFoundError(f"Fixture no encontrado: {portfolio_file}")
    
    with open(portfolio_file, 'r') as f:
        portfolio_data = json.load(f)
    
    log_event("INFO", "mock_portfolio_loaded", 
             positions=len(portfolio_data["positions"]),
             fixture_file=str(portfolio_file))
    
    # Convertir datos fixture a objetos Portfolio/Position
    from app.models.portfolio import Portfolio, Position
    from app.processors.cedeares import cedeares_processor
    
    positions = []
    for pos_data in portfolio_data["positions"]:
        # Calcular underlying_quantity usando el ratio real de CEDEARs
        cedear_info = cedeares_processor.get_cedear_info(pos_data["symbol"])
        if cedear_info:
            ratio = cedear_info.get("ratio", "1:1")
            conversion_ratio = cedeares_processor.parse_ratio(ratio)
            underlying_quantity = pos_data["quantity"] / conversion_ratio
        else:
            underlying_quantity = pos_data.get("underlying_quantity", 1.0)
        
        position = Position(
            symbol=pos_data["symbol"],
            quantity=pos_data["quantity"],
            price=None,  # Precios se obtienen en tiempo real
            currency="ARS",  # MOCK usa ARS como default
            is_cedear=pos_data["is_cedear"],
            underlying_symbol=pos_data["underlying_symbol"],
            underlying_quantity=underlying_quantity
        )
        positions.append(position)
    
    return Portfolio(positions=positions, broker="MOCK_IOL")

async def load_real_iol_portfolio(args):
    """Carga portfolio desde IOL real con autenticación"""
    from app.integrations.iol import IOLIntegration
    
    # Validar credenciales
    username = os.getenv("IOL_USER")
    password = os.getenv("IOL_PASS")
    
    if not username or not password:
        raise ValueError("IOL_USER y IOL_PASS son requeridos para IOL real")
    
    log_event("INFO", "iol_auth_started", username=username)
    
    iol = IOLIntegration()
    
    # TODO: Implementar token caching en .cache/iol_token.json
    await iol.authenticate(username, password)
    
    log_event("INFO", "iol_auth_success")
    
    portfolio = await iol.get_portfolio()
    
    if not portfolio:
        raise ValueError("No se pudo obtener portfolio desde IOL")
    
    return portfolio

async def save_etl_results(output_dir: Path, portfolio, analysis_result: Dict, args):
    """Guarda resultados del ETL en archivos estructurados"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Portfolio data
    portfolio_file = output_dir / f"portfolio_{timestamp}.json"
    with open(portfolio_file, 'w') as f:
        json.dump({
            "source": args.source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "positions": len(portfolio.positions),
            "cedeares": len([p for p in portfolio.positions if p.is_cedear]),
            "broker": portfolio.broker
        }, f, indent=2)
    
    # Analysis results
    analysis_file = output_dir / f"analysis_{timestamp}.json"
    with open(analysis_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "threshold": args.arbitrage_threshold,
            "opportunities": len(analysis_result.get("arbitrage_opportunities", [])),
            "results": analysis_result
        }, f, indent=2)
    
    log_event("INFO", "results_saved", 
             portfolio_file=str(portfolio_file),
             analysis_file=str(analysis_file))

def main():
    """Función principal"""
    args = parse_args()
    
    # Validar argumentos
    if not validate_args(args):
        sys.exit(1)  # Config error
    
    # Configurar seed para reproducibilidad
    if args.seed:
        import random
        random.seed(args.seed)
    
    try:
        # Ejecutar ETL
        status = asyncio.run(run_etl(args))
        
        # Escribir status.json
        write_status(status, args.output_dir)
        
        # Exit code según resultado
        exit_code = 0 if status["last_run_ok"] else 3  # 3 = data error
        
        log_event("INFO", "scheduler_exit", exit_code=exit_code, status=status["last_run_ok"])
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        log_event("WARNING", "scheduler_interrupted")
        sys.exit(130)  # Standard interrupt exit code
        
    except Exception as e:
        log_event("ERROR", "scheduler_fatal", error=str(e))
        
        # Escribir status de error
        status = {
            "last_run_ok": False,
            "last_error": f"Fatal error: {str(e)}",
            "last_run_at": datetime.now(timezone.utc).isoformat(),
            "source": args.source,
            "duration_ms": 0
        }
        write_status(status, args.output_dir)
        
        sys.exit(2)  # Auth/system error

if __name__ == "__main__":
    main()