#!/usr/bin/env python3
"""
ETL CLI para Portfolio Replicator con DI estricta
Ejecuta análisis parametrizado desde línea de comandos con output estructurado
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Agregar directorio padre al path para importar app
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports de servicios (movidos del nivel de función para evitar redundancia)
from app.core.config import Config
from app.core.services import build_services

# Configurar logging estructurado (JSON Lines)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Variable global para controlar verbosidad
_verbose_mode = False

def set_verbose_mode(verbose: bool):
    """Configura el modo verbose globalmente"""
    global _verbose_mode
    _verbose_mode = verbose

def log_event(level: str, msg: str, **kwargs):
    """Log estructurado en formato JSON Lines para monitoreo del sistema (solo en verbose)"""
    if _verbose_mode:
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "msg": msg,
            **kwargs
        }
        print(json.dumps(event, ensure_ascii=False))

def print_progress(message: str):
    """Print para mostrar progreso (siempre visible)"""
    print(message)

def print_verbose(message: str):
    """Print solo en modo verbose"""
    if _verbose_mode:
        print(message)

def parse_schedule_interval(schedule_str: str) -> int:
    """Convierte string de schedule a segundos"""
    schedule_map = {
        "2min": 2 * 60,      # 2 minutos (para pruebas)
        "30min": 30 * 60,    # 30 minutos
        "1hour": 60 * 60,    # 1 hora 
        "hourly": 60 * 60,   # 1 hora (alias)
        "daily": 24 * 60 * 60  # 1 día
    }
    
    if schedule_str not in schedule_map:
        raise ValueError(f"Schedule inválido: {schedule_str}. Opciones: {list(schedule_map.keys())}")
    
    return schedule_map[schedule_str]

def run_scheduled_etl(args):
    """Ejecuta ETL de forma periódica según el schedule especificado"""
    try:
        interval_seconds = parse_schedule_interval(args.schedule)
        interval_minutes = interval_seconds // 60
        
        print_progress(f"🕒 MODO PERIÓDICO ACTIVADO")
        print_progress(f"📅 Ejecutando cada {args.schedule} ({interval_minutes} minutos)")
        if _verbose_mode:
            if args.source == "excel":
                print(f"📁 Archivo: {args.file}")
                print(f"🏦 Broker: {args.broker}")
            elif args.source == "iol":
                print(f"🔗 Fuente: IOL API")
        print_progress(f"⏹️  Presiona Ctrl+C para detener")
        print_progress("=" * 50)
        
        log_event("INFO", "scheduler_started", 
                 schedule=args.schedule, 
                 interval_seconds=interval_seconds)
        
        execution_count = 0
        
        while True:
            execution_count += 1
            start_time = datetime.now()
            
            print_progress(f"\n🚀 Ejecución #{execution_count} - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            try:
                # Ejecutar ETL
                result = asyncio.run(run_etl_analysis(args))
                
                if result["exit_code"] == 0:
                    opportunities = len(result.get("results", {}).get("opportunities", []))
                    print_progress(f"✅ Completado - {opportunities} oportunidades encontradas")
                else:
                    print(f"❌ Error en ejecución: {result.get('error', 'Unknown')}")
                
                log_event("INFO", "scheduled_execution_completed",
                         execution_count=execution_count,
                         exit_code=result["exit_code"],
                         opportunities_found=len(result.get("results", {}).get("opportunities", [])))
                
            except Exception as e:
                print(f"💥 Error en ejecución #{execution_count}: {e}")
                log_event("ERROR", "scheduled_execution_failed",
                         execution_count=execution_count,
                         error=str(e))
            
            # Mostrar próxima ejecución
            next_run = datetime.now().timestamp() + interval_seconds
            next_run_str = datetime.fromtimestamp(next_run).strftime('%H:%M:%S')
            print_progress(f"⏰ Próxima ejecución: {next_run_str}")
            
            # Esperar hasta la próxima ejecución
            if _verbose_mode:
                print_verbose(f"😴 Esperando {interval_minutes} minutos...")
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        print_progress(f"\n⏹️  Scheduler detenido después de {execution_count} ejecuciones")
        log_event("INFO", "scheduler_stopped", total_executions=execution_count)
    except ValueError as e:
        print(f"❌ Error en configuración de schedule: {e}")
        log_event("ERROR", "scheduler_config_error", error=str(e))
        sys.exit(1)

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
  
  # Análisis de portfolio desde IOL API
  python etl_cli.py --source iol
  
  # Análisis IOL con threshold personalizado
  python etl_cli.py --source iol --threshold 0.01
  
  # Diagnóstico de servicios únicamente
  python etl_cli.py --health-check
        """
    )
    
    # Argumentos principales
    parser.add_argument("--health-check", action="store_true",
                       help="Ejecutar solo diagnóstico de servicios (sin procesamiento ETL)")
    
    # Argumentos ETL (requeridos solo si no es health-check)
    parser.add_argument("--source", choices=["excel", "iol"],
                       help="Fuente de datos del portfolio")
    parser.add_argument("--file",
                       help="Archivo Excel/CSV del portfolio (requerido solo para --source excel)")
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
    parser.add_argument("--schedule", type=str, default=None,
                       help="Ejecutar periódicamente: '2min', '30min', '1hour', 'daily' o 'hourly'")
    
    return parser.parse_args()


def validate_args(args):
    """Valida argumentos según el modo de ejecución"""
    if not args.health_check:
        # Para ETL normal, source es requerido
        if not args.source:
            print("❌ ERROR: --source es requerido para procesamiento ETL")
            print("💡 Use --health-check para diagnóstico únicamente")
            sys.exit(2)
        
        # Para source excel, file es requerido
        if args.source == "excel" and not args.file:
            print("❌ ERROR: --file es requerido para --source excel")
            print("💡 Use --source iol para obtener portfolio desde IOL API")
            sys.exit(2)

async def run_etl_analysis(args) -> Dict[str, Any]:
    """
    Ejecuta análisis completo usando DI estricta
    
    Returns:
        Dict con resultados estructurados y exit code
    """
    start_time = datetime.now()
    
    try:
        # Construir servicios con DI estricta
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
        if _verbose_mode:
            print(f"📊 Configuración ETL:")
            print(f"   • Threshold: {config.arbitrage_threshold} ({config.arbitrage_threshold*100:.1f}%)")
            print(f"   • Timeout: {config.request_timeout}s")
            print(f"   • Cache TTL: {config.cache_ttl_seconds}s")
            if config_overrides:
                print(f"   ↳ Sobrescrito por CLI: {', '.join(config_overrides)}")
            else:
                print(f"   ↳ Usando configuración por defecto")
        else:
            print_progress("📊 Iniciando análisis ETL...")
        
        # 2. Obtener portfolio según fuente
        if args.source == "excel":
            log_event("INFO", "processing_file", file=args.file)
            
            file_path = Path(args.file)
            if not file_path.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {args.file}")
            
            # Mapear nombres de broker CLI a los nombres internos
            broker_mapping = {
                "cocos": "Cocos Capital",
                "bullmarket": "Bull Market", 
                "generic": "Generic"
            }
            broker_name = broker_mapping[args.broker]
            
            portfolio = await services.portfolio_processor.process_file(str(file_path), broker_name)
            
        elif args.source == "iol":
            log_event("INFO", "fetching_iol_portfolio")
            
            # Verificar que las credenciales IOL estén configuradas
            if not config.iol_username or not config.iol_password:
                raise ValueError("Credenciales IOL no configuradas. Configure IOL_USERNAME e IOL_PASSWORD en .env")
            
            # Autenticar con IOL
            await services.iol_integration.authenticate(config.iol_username, config.iol_password)
            
            # Obtener portfolio desde IOL API
            portfolio = await services.iol_integration.get_portfolio()
            broker_name = "IOL"
            
        else:
            raise ValueError(f"Fuente no soportada: {args.source}")
        
        log_event("INFO", "portfolio_loaded", 
                 positions=len(portfolio.positions),
                 cedeares=sum(1 for p in portfolio.positions if p.is_cedear),
                 source=args.source,
                 broker=broker_name)
        
        # 4. Análisis de arbitraje
        log_event("INFO", "analyzing_arbitrage", threshold=config.arbitrage_threshold)
        
        analysis_result = await services.arbitrage_detector.analyze_portfolio(
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
                "broker": broker_name,
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
            "analysis_data": {
                "arbitrage_opportunities": [opp.to_dict() for opp in analysis_result.get("arbitrage_opportunities", [])],
                "price_data": analysis_result.get("price_data", {}),
                "summary": analysis_result.get("summary", {})
            }
        }
        
        # 5. Guardar archivos si se solicita
        if not args.no_save:
            output_dir = Path(args.output)
            
            # ✅ MANTENER: Archivos JSON (compatibilidad)
            write_results(results, output_dir)
            
            # ➕ AGREGAR: Base de datos (criterio TFM)
            try:
                services.database_service.save_all(results)
                log_event("INFO", "database_saved", db_path=str(services.database_service.db_path))
            except Exception as e:
                log_event("ERROR", "database_save_failed", error=str(e))
                print(f"⚠️  Error guardando en BD: {e}")
            
            log_event("INFO", "results_saved", output_dir=str(output_dir))
        
        # 6. Mostrar resumen
        if _verbose_mode:
            print("\n" + "="*60)
            print(f"📊 ETL COMPLETADO - {len(opportunities)} oportunidades encontradas")
            print("="*60)
        else:
            print(f"\n📊 {len(opportunities)} oportunidades de arbitraje encontradas")
        
        for opp in opportunities:
            print(f"🚨 {opp.symbol}: {opp.difference_percentage:.1%} - {opp.recommendation}")
        
        if not opportunities:
            print("✅ No se detectaron oportunidades de arbitraje")
        
        if _verbose_mode:
            print(f"\n⏱️  Duración: {duration_ms}ms")
            if not args.no_save:
                print(f"💾 Resultados guardados en: {args.output}/")
            print("="*60)
        elif not args.no_save:
            print(f"💾 Resultados guardados en: {args.output}/")
        
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


async def run_health_check() -> Dict[str, Any]:
    """
    Ejecuta solo diagnóstico de servicios usando DI estricta
    
    Returns:
        Dict con resultados del health check y exit code
    """
    start_time = datetime.now()
    
    try:
        log_event("INFO", "health_check_started")
        
        # 1. Inicializar servicios
        from app.workflows.commands.monitoring_commands import MonitoringCommands
        
        config = Config.from_env()
        services = build_services(config)
        
        # 2. Ejecutar health check
        monitoring = MonitoringCommands(services, None)
        await monitoring.run_health_diagnostics()
        
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        log_event("INFO", "health_check_success", duration_ms=duration_ms, exit_code=0)
        
        return {
            "success": True,
            "duration_ms": duration_ms,
            "exit_code": 0
        }
        
    except Exception as e:
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        log_event("ERROR", "health_check_error", error=str(e), duration_ms=duration_ms, exit_code=1)
        
        return {
            "success": False,
            "error": str(e),
            "duration_ms": duration_ms,
            "exit_code": 1
        }


def main():
    """Función principal con exit codes determinísticos"""
    args = parse_args()
    
    # Validar argumentos según modo
    validate_args(args)
    
    # Configurar verbosidad globalmente
    set_verbose_mode(args.verbose)
    
    # Configurar logging según verbosidad
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        from app.utils.logging_config import setup_debug_logging
        setup_debug_logging()
    else:
        from app.utils.logging_config import setup_quiet_logging
        setup_quiet_logging()
    
    try:
        # Si es health check, ejecutar solo diagnóstico
        if args.health_check:
            result = asyncio.run(run_health_check())
            
            exit_code = result["exit_code"]
            
            if exit_code != 0:
                print(f"\n❌ ERROR en health check: {result.get('error', 'Unknown error')}")
                print("💡 Use --verbose para más detalles")
            
            log_event("INFO", "cli_exit", exit_code=exit_code)
            sys.exit(exit_code)
        
        # Si hay schedule, ejecutar periódicamente
        elif args.schedule:
            run_scheduled_etl(args)
        else:
            # Ejecutar una sola vez (comportamiento original)
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
