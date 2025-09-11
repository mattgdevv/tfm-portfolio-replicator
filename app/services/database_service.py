"""
Servicio para manejo de base de datos SQLite
Guarda resultados del pipeline ETL en formato estructurado para modelización
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


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
            
            # Tabla de posiciones individuales
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_id INTEGER,
                    symbol TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price_ars REAL,
                    price_usd REAL,
                    total_value_ars REAL,
                    total_value_usd REAL,
                    is_cedear BOOLEAN DEFAULT TRUE,
                    conversion_ratio REAL,
                    underlying_symbol TEXT,
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios (id)
                )
            """)
            
            # Tabla de oportunidades de arbitraje
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_id INTEGER,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    cedear_price_ars REAL,
                    cedear_price_usd REAL,
                    underlying_price_usd REAL,
                    arbitrage_percentage REAL NOT NULL,
                    arbitrage_absolute REAL,
                    recommendation TEXT,
                    ccl_rate REAL,
                    confidence_score REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios (id)
                )
            """)
            
            # Tabla de métricas del pipeline
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    execution_time_ms INTEGER,
                    records_processed INTEGER,
                    opportunities_found INTEGER,
                    symbols_analyzed INTEGER,
                    sources_status TEXT,  -- JSON con status de APIs
                    errors_count INTEGER DEFAULT 0,
                    data_quality_score REAL,
                    cache_hits INTEGER DEFAULT 0,
                    cache_misses INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info(f"✅ Base de datos inicializada: {self.db_path}")
    
    def save_portfolio_data(self, results: Dict[str, Any]) -> int:
        """
        Guarda datos del portfolio en la base de datos
        
        Args:
            results: Diccionario con los resultados del ETL
            
        Returns:
            int: ID del portfolio insertado
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Extraer información del portfolio
            portfolio_data = results.get("portfolio_data", {})
            input_data = results.get("input", {})
            summary = results.get("summary", {})
            
            # Insertar portfolio principal
            cursor.execute("""
                INSERT INTO portfolios (
                    timestamp, source, broker, total_positions, 
                    total_value_ars, total_value_usd, ccl_rate, execution_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                input_data.get("source", "unknown"),
                input_data.get("broker", "unknown"),
                summary.get("total_positions", len(portfolio_data.get("positions", []))),
                0.0,  # Por ahora 0, se puede calcular después
                0.0,  # Por ahora 0, se puede calcular después
                0.0,  # CCL rate se obtiene de las oportunidades
                results.get("duration_ms", 0)
            ))
            
            portfolio_id = cursor.lastrowid
            
            # Insertar posiciones
            positions = portfolio_data.get("positions", [])
            for position in positions:
                cursor.execute("""
                    INSERT INTO positions (
                        portfolio_id, symbol, quantity, price_ars, price_usd,
                        total_value_ars, total_value_usd, is_cedear, 
                        conversion_ratio, underlying_symbol
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    portfolio_id,
                    position.get("symbol"),
                    position.get("quantity", 0),
                    0.0,  # price_ars no está en esta estructura
                    0.0,  # price_usd no está en esta estructura  
                    position.get("total_value") or 0.0,
                    0.0,  # total_value_usd calculado después
                    position.get("is_cedear", True),
                    position.get("underlying_quantity", 1.0),
                    position.get("underlying_symbol")
                ))
            
            conn.commit()
            logger.info(f"💾 Portfolio guardado en BD: {portfolio_id} ({len(positions)} posiciones)")
            return portfolio_id
    
    def save_arbitrage_data(self, results: Dict[str, Any], portfolio_id: int):
        """
        Guarda oportunidades de arbitraje en la base de datos
        
        Args:
            results: Diccionario con los resultados del ETL
            portfolio_id: ID del portfolio relacionado
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Buscar oportunidades en diferentes ubicaciones del dict
            opportunities = []
            if "opportunities" in results:
                opportunities = results["opportunities"]
            elif "analysis_data" in results and "opportunities" in results["analysis_data"]:
                opportunities = results["analysis_data"]["opportunities"]
            
            metrics = results.get("metrics", {})
            
            for opp in opportunities:
                cursor.execute("""
                    INSERT INTO arbitrage_opportunities (
                        portfolio_id, timestamp, symbol, cedear_price_ars,
                        cedear_price_usd, underlying_price_usd, arbitrage_percentage,
                        arbitrage_absolute, recommendation, ccl_rate, confidence_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    portfolio_id,
                    opp.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    opp.get("symbol"),
                    opp.get("cedear_price_ars", 0),
                    opp.get("cedear_price_usd", 0),
                    opp.get("underlying_price_usd", 0),
                    opp.get("difference_percentage", 0),
                    opp.get("difference_usd", 0),
                    opp.get("recommendation", ""),
                    opp.get("ccl_rate", metrics.get("ccl_rate", 0)),
                    opp.get("confidence_score", 1.0)
                ))
            
            conn.commit()
            logger.info(f"🎯 Arbitraje guardado en BD: {len(opportunities)} oportunidades")
    
    def save_pipeline_metrics(self, results: Dict[str, Any]):
        """
        Guarda métricas del pipeline en la base de datos
        
        Args:
            results: Diccionario con los resultados del ETL
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            metrics = results.get("metrics", {})
            summary = results.get("summary", {})
            
            # Contar oportunidades
            opportunities_count = 0
            if "opportunities" in results:
                opportunities_count = len(results["opportunities"])
            elif "analysis_data" in results and "opportunities" in results["analysis_data"]:
                opportunities_count = len(results["analysis_data"]["opportunities"])
            
            cursor.execute("""
                INSERT INTO pipeline_metrics (
                    timestamp, execution_time_ms, records_processed,
                    opportunities_found, symbols_analyzed, sources_status,
                    errors_count, data_quality_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                results.get("duration_ms", metrics.get("execution_time_ms", 0)),
                summary.get("total_positions", len(results.get("portfolio_data", {}).get("positions", []))),
                opportunities_count,
                summary.get("symbols_analyzed", 0),
                json.dumps(metrics.get("sources_status", {})),
                metrics.get("errors_count", 0),
                metrics.get("data_quality_score", 1.0)
            ))
            
            conn.commit()
            logger.info("📊 Métricas del pipeline guardadas en BD")
    
    def save_all(self, results: Dict[str, Any]):
        """
        Guarda todos los datos del ETL en la base de datos
        
        Args:
            results: Diccionario completo con los resultados del ETL
        """
        try:
            # Guardar portfolio y obtener ID
            portfolio_id = self.save_portfolio_data(results)
            
            # Guardar análisis de arbitraje
            self.save_arbitrage_data(results, portfolio_id)
            
            # Guardar métricas
            self.save_pipeline_metrics(results)
            
            logger.info(f"✅ Todos los datos guardados en BD: portfolio_id={portfolio_id}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando en BD: {e}")
            raise
    
    def get_portfolio_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Obtiene resumen de portfolios de los últimos N días
        
        Args:
            days: Número de días hacia atrás
            
        Returns:
            Dict con estadísticas del portfolio
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Estadísticas básicas
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_runs,
                    AVG(total_positions) as avg_positions,
                    AVG(execution_time_ms) as avg_execution_time,
                    MAX(timestamp) as last_run
                FROM portfolios 
                WHERE datetime(timestamp) > datetime('now', '-{} days')
            """.format(days))
            
            stats = cursor.fetchone()
            
            return {
                "total_runs": stats[0] if stats[0] else 0,
                "avg_positions": round(stats[1], 1) if stats[1] else 0,
                "avg_execution_time_ms": round(stats[2], 1) if stats[2] else 0,
                "last_run": stats[3]
            }
    
    def get_arbitrage_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Obtiene resumen de oportunidades de arbitraje
        
        Args:
            days: Número de días hacia atrás
            
        Returns:
            Dict con estadísticas de arbitraje
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Top oportunidades
            cursor.execute("""
                SELECT 
                    symbol,
                    AVG(arbitrage_percentage) as avg_arbitrage,
                    COUNT(*) as frequency,
                    MAX(arbitrage_percentage) as max_arbitrage
                FROM arbitrage_opportunities 
                WHERE datetime(timestamp) > datetime('now', '-{} days')
                GROUP BY symbol
                ORDER BY avg_arbitrage DESC
                LIMIT 5
            """.format(days))
            
            top_opportunities = [
                {
                    "symbol": row[0],
                    "avg_arbitrage": round(row[1], 4) if row[1] else 0,
                    "frequency": row[2],
                    "max_arbitrage": round(row[3], 4) if row[3] else 0
                }
                for row in cursor.fetchall()
            ]
            
            return {
                "top_opportunities": top_opportunities,
                "total_opportunities": len(top_opportunities)
            }

    # ===============================================
    # MÉTODOS PARA HEALTH CHECKS
    # ===============================================

    async def count_tables(self) -> int:
        """Cuenta el número de tablas en la base de datos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                return cursor.fetchone()[0]
        except Exception:
            return 0

    async def count_total_records(self) -> int:
        """Cuenta el total de registros en todas las tablas principales"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Contar registros en tablas principales
                tables = ['portfolios', 'positions', 'arbitrage_opportunities', 'pipeline_metrics']
                total = 0
                
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    total += cursor.fetchone()[0]
                
                return total
        except Exception:
            return 0

    async def get_last_execution_time(self) -> Optional[str]:
        """Obtiene la fecha de la última ejecución del ETL"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp 
                    FROM portfolios 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                result = cursor.fetchone()
                
                if result:
                    # Formatear timestamp para mejor legibilidad
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(result[0].replace('Z', '+00:00'))
                        # Calcular hace cuánto tiempo fue
                        now = datetime.now(dt.tzinfo)
                        diff = now - dt
                        
                        if diff.total_seconds() < 3600:  # menos de 1 hora
                            minutes_ago = int(diff.total_seconds() / 60)
                            return f"Hace {minutes_ago} minutos ({dt.strftime('%H:%M:%S')})"
                        elif diff.days == 0:  # hoy
                            return f"Hoy a las {dt.strftime('%H:%M:%S')}"
                        elif diff.days == 1:  # ayer
                            return f"Ayer a las {dt.strftime('%H:%M:%S')}"
                        else:  # más días
                            return f"{diff.days} días atrás ({dt.strftime('%Y-%m-%d %H:%M')})"
                    except:
                        return result[0]
                
                return None
        except Exception:
            return None

    async def _count_table_records(self, table_name: str) -> int:
        """Cuenta registros en una tabla específica"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                return cursor.fetchone()[0]
        except Exception:
            return 0
