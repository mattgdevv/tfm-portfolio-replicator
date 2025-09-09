#!/usr/bin/env python3
"""
ETL CLI para Portfolio Replicator con DI estricta
Ejecuta análisis parametrizados desde línea de comandos con output estructurado
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

# Agregar directorio padre al path para importar app
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configurar logging estructurado (JSON Lines)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def log_event(level: str, msg: str, **kwargs):
    """Log estructurado en formato JSON Lines para monitoreo/debugging"""
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "msg": msg,
        **kwargs
    }
    print(json.dumps(event, ensure_ascii=False))

def write_results(results: Dict[str, Any], output_dir: Path):
    """Escribe resultados estructurados en archivos JSON"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Status principal
    status_file = output_dir / "status.json"
    with open(status_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Timestamp para tracking
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Portfolio data si existe
    if "portfolio_data" in results:
        portfolio_file = output_dir / f"portfolio_{timestamp}.json"
        with open(portfolio_file, 'w', encoding='utf-8') as f:
            json.dump(results["portfolio_data"], f, indent=2, ensure_ascii=False)
    
    # Analysis results si existe
    if "analysis_data" in results:
        analysis_file = output_dir / f"analysis_{timestamp}.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(results["analysis_data"], f, indent=2, ensure_ascii=False)

def parse_args():
    """Parse argumentos CLI con todas las opciones necesarias"""
    parser = argparse.ArgumentParser(
        description="Portfolio Replicator ETL CLI - Ejecución parametrizada",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Análisis de archivo Excel/CSV
  python etl_cli.py --source excel --file data/portfolio.csv
  
  # Análisis especificando broker para mejor precisión
  python etl_cli.py --source excel --file data.csv --broker bullmarket
  
  # Análisis con threshold personalizado
  python etl_cli.py --source excel --file data.csv --threshold 0.01
  
  # Output a directorio específico
  python etl_cli.py --source excel --file data.csv --output results/
  
  # Solo análisis sin guardar archivos
  python etl_cli.py --source excel --file data.csv --no-save
        """
    )
    
    parser.add_argument("--source", choices=["excel"], required=True,
                       help="Fuente de datos del portfolio")
    parser.add_argument("--file", required=True,
                       help="Archivo Excel/CSV del portfolio")
    parser.add_argument("--broker", choices=["cocos", "bullmarket", "generic"], default="generic",
                       help="Broker del archivo (default: generic - mejor especificar para más precisión)")
    parser.add_argument("--threshold", type=float, default=None,
                       help="Umbral de arbitraje (default: usa config.arbitrage_threshold)")
    parser.add_argument("--timeout", type=int, default=None,
                       help="Timeout para requests en segundos (default: usa config.request_timeout)")
    parser.add_argument("--cache-ttl", type=int, default=None,
                       help="TTL del cache en segundos (default: usa config.cache_ttl_seconds)")
    parser.add_argument("--output", default="output",
                       help="Directorio de salida (default: output/)")
    parser.add_argument("--no-save", action="store_true",
                       help="No guardar archivos, solo mostrar resultados")
    parser.add_argument("--verbose", action="store_true",
                       help="Mostrar logs detallados")
    
    return parser.parse_args()

async def run_etl_analysis(args) -> Dict[str, Any]:
    """
    Ejecuta análisis completo usando DI estricta
    
    Returns:
        Dict con resultados estructurados y exit code
    """
    start_time = datetime.now()
    
    try:
        # Importar y construir servicios con DI estricta
        from app.core.config import Config
        from app.core.services import build_services
        from app.models.portfolio import Portfolio
        
        log_event("INFO", "etl_started", 
                 source=args.source, file=args.file, threshold=args.threshold)
        
        # 1. Construir servicios DI con configuración personalizada
        config = Config.from_env()
        
        # 2. Aplicar parámetros CLI si se especifican (sobrescriben config)
        config_overrides = []
        if args.threshold is not None:
            config.arbitrage_threshold = args.threshold
            config_overrides.append(f"threshold={args.threshold}")
        if args.timeout is not None:
            config.request_timeout = args.timeout
            config_overrides.append(f"timeout={args.timeout}s")
        if hasattr(args, 'cache_ttl') and args.cache_ttl is not None:
            config.cache_ttl_seconds = args.cache_ttl
            config_overrides.append(f"cache_ttl={args.cache_ttl}s")
        
        services = build_services(config)
        
        # 3. Mostrar configuración efectiva
        print(f"📊 Configuración ETL:")
        print(f"   • Threshold: {config.arbitrage_threshold} ({config.arbitrage_threshold*100:.1f}%)")
        print(f"   • Timeout: {config.request_timeout}s")
        print(f"   • Cache TTL: {config.cache_ttl_seconds}s")
        if config_overrides:
            print(f"   ↳ Sobrescrito por CLI: {', '.join(config_overrides)}")
        else:
            print(f"   ↳ Usando configuración por defecto")
        
        # 2. Procesar archivo
        log_event("INFO", "processing_file", file=args.file)
        
        file_path = Path(args.file)
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {args.file}")
        
        # Mapear nombres de broker CLI a los nombres internos
        broker_mapping = {
            "cocos": "Cocos Capital",
            "bullmarket": "Bull Market", 
            "generic": "CLI"
        }
        broker_name = broker_mapping[args.broker]
        
        portfolio = await services.portfolio_processor.process_file(str(file_path), broker_name)
        
        log_event("INFO", "portfolio_loaded", 
                 positions=len(portfolio.positions),
                 cedeares=sum(1 for p in portfolio.positions if p.is_cedear))
        
        # 4. Análisis de arbitraje
        log_event("INFO", "analyzing_arbitrage", threshold=config.arbitrage_threshold)
        
        analysis_result = await services.unified_analysis.analyze_portfolio(
            portfolio, threshold=config.arbitrage_threshold
        )
        
        opportunities = analysis_result.get("arbitrage_opportunities", [])
        
        log_event("INFO", "analysis_completed",
                 opportunities_found=len(opportunities),
                 symbols_analyzed=len(analysis_result.get("price_data", {})))
        
        # 4. Preparar resultados estructurados
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        results = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "duration_ms": duration_ms,
            "input": {
                "source": args.source,
                "file": args.file,
                "threshold": args.threshold
            },
            "summary": {
                "total_positions": len(portfolio.positions),
                "cedear_positions": sum(1 for p in portfolio.positions if p.is_cedear),
                "opportunities_found": len(opportunities),
                "symbols_analyzed": len(analysis_result.get("price_data", {}))
            },
            "opportunities": [opp.to_dict() for opp in opportunities],
            "portfolio_data": {
                "positions": [
                    {
                        "symbol": p.symbol,
                        "quantity": p.quantity,
                        "total_value": p.total_value,
                        "is_cedear": p.is_cedear,
                        "underlying_symbol": p.underlying_symbol,
                        "underlying_quantity": p.underlying_quantity
                    } for p in portfolio.positions
                ]
            },
            "analysis_data": analysis_result
        }
        
        # 5. Guardar archivos si se solicita
        if not args.no_save:
            output_dir = Path(args.output)
            write_results(results, output_dir)
            log_event("INFO", "results_saved", output_dir=str(output_dir))
        
        # 6. Mostrar resumen
        print("\n" + "="*60)
        print(f"📊 ETL COMPLETADO - {len(opportunities)} oportunidades encontradas")
        print("="*60)
        
        for opp in opportunities:
            print(f"🚨 {opp.symbol}: {opp.difference_percentage:.1%} - {opp.recommendation}")
        
        if not opportunities:
            print("✅ No se detectaron oportunidades de arbitraje")
        
        print(f"\n⏱️  Duración: {duration_ms}ms")
        if not args.no_save:
            print(f"💾 Resultados guardados en: {args.output}/")
        print("="*60)
        
        log_event("INFO", "etl_success", duration_ms=duration_ms, exit_code=0)
        return {"exit_code": 0, "results": results}
        
    except FileNotFoundError as e:
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        log_event("ERROR", "file_not_found", error=str(e), duration_ms=duration_ms)
        return {"exit_code": 1, "error": str(e)}
        
    except Exception as e:
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        log_event("ERROR", "etl_failed", error=str(e), duration_ms=duration_ms)
        return {"exit_code": 3, "error": str(e)}

def main():
    """Función principal con exit codes determinísticos"""
    args = parse_args()
    
    # Configurar verbosidad
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Ejecutar análisis
        result = asyncio.run(run_etl_analysis(args))
        
        exit_code = result["exit_code"]
        
        if exit_code != 0:
            print(f"\n❌ ERROR: {result.get('error', 'Unknown error')}")
            print("💡 Use --verbose para más detalles")
        
        log_event("INFO", "cli_exit", exit_code=exit_code)
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        log_event("INFO", "cli_interrupted")
        print("\n⏸️  Ejecución interrumpida por usuario")
        sys.exit(1)
    except Exception as e:
        log_event("ERROR", "cli_error", error=str(e))
        print(f"\n💥 Error inesperado: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()
