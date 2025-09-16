"""
Validación estricta para arquitectura DI
Detecta y previene uso de servicios globales deprecated
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple, Set
import logging

logger = logging.getLogger(__name__)

# Servicios globales eliminados que NO deben importarse
FORBIDDEN_GLOBAL_IMPORTS = {
    "app.services.dollar_rate.dollar_service",
    "app.services.arbitrage_detector.arbitrage_detector", 
    "app.services.international_prices.international_price_service",
    "app.services.byma_historical.byma_historical_service",
    "app.services.variation_analyzer.variation_analyzer",
    "app.processors.cedeares.cedeares_processor",
}

class GlobalServiceImportVisitor(ast.NodeVisitor):
    """AST visitor que detecta imports de servicios globales prohibidos y constructores directos"""
    
    def __init__(self):
        self.violations: List[Tuple[int, str]] = []
        # Constructores directos que deberían usar DI
        self.forbidden_constructors = {
            "CEDEARProcessor", "PortfolioProcessor", "VariationAnalyzer", 
            "ArbitrageDetector", "DollarRateService", "InternationalPriceService",
            "BYMAHistoricalService"
        }
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            for alias in node.names:
                import_path = f"{node.module}.{alias.name}"
                if import_path in FORBIDDEN_GLOBAL_IMPORTS:
                    self.violations.append((
                        node.lineno, 
                        f"Import prohibido: {import_path} - usar build_services() para DI"
                    ))
        self.generic_visit(node)
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name in FORBIDDEN_GLOBAL_IMPORTS:
                self.violations.append((
                    node.lineno,
                    f"Import prohibido: {alias.name} - usar build_services() para DI"
                ))
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        """Detecta constructores directos de servicios"""
        if isinstance(node.func, ast.Name):
            if node.func.id in self.forbidden_constructors:
                self.violations.append((
                    node.lineno,
                    f"Constructor directo prohibido: {node.func.id}() - usar build_services() para DI"
                ))
        self.generic_visit(node)


def validate_file_strict_di(file_path: Path) -> List[Tuple[int, str]]:
    """
    Valida que un archivo no importe servicios globales prohibidos
    
    Returns:
        Lista de violaciones (línea, mensaje)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(file_path))
        visitor = GlobalServiceImportVisitor()
        visitor.visit(tree)
        
        return visitor.violations
        
    except Exception as e:
        logger.error(f"Error validando {file_path}: {e}")
        return [(0, f"Error de parsing: {e}")]


def validate_project_strict_di(project_root: Path, 
                              excluded_patterns: Set[str] = None) -> bool:
    """
    Valida todo el proyecto para DI estricto
    
    Args:
        project_root: Directorio raíz del proyecto
        excluded_patterns: Patrones de archivos a excluir (ej: {"*_backup.py"})
    
    Returns:
        True si no hay violaciones, False si las hay
    """
    if excluded_patterns is None:
        excluded_patterns = {
            "*_backup.py",   # Archivos legacy (ya eliminados)
            "scripts/scheduler.py",  # Script legacy específico (por ahora)
            "app/core/services.py",  # Factory DI - debe crear instancias
            "app/core/validation.py", # Este archivo - no aplica a sí mismo
        }
    
    violations_found = False
    total_files = 0
    
    # Buscar todos los archivos Python
    for py_file in project_root.rglob("*.py"):
        # Saltar archivos excluidos
        relative_path = py_file.relative_to(project_root)
        if any(relative_path.match(pattern) for pattern in excluded_patterns):
            continue
            
        total_files += 1
        violations = validate_file_strict_di(py_file)
        
        if violations:
            violations_found = True
            print(f"\n[ERROR] VIOLACIONES DI en {relative_path}:")
            for line_no, message in violations:
                print(f"   Línea {line_no}: {message}")
    
    if not violations_found:
        print(f"[SUCCESS] VALIDACIÓN DI EXITOSA: {total_files} archivos verificados")
        print("Arquitectura DI estricta confirmada")
    else:
        print(f"\n[WARNING]  RESUMEN: Violaciones encontradas en {total_files} archivos")
        print("Corrija los imports para usar build_services() exclusivamente")
    
    return not violations_found


def check_runtime_di_strict():
    """
    Verificación en tiempo de ejecución de que servicios globales están deshabilitados
    """
    forbidden_globals = [
        "app.services.dollar_rate.dollar_service",
        "app.services.arbitrage_detector.arbitrage_detector",
        "app.services.international_prices.international_price_service",
        "app.services.byma_historical.byma_historical_service",
        "app.services.variation_analyzer.variation_analyzer",
        "app.processors.cedeares.cedeares_processor",
    ]
    
    violations = []
    
    for module_path in forbidden_globals:
        try:
            # Intentar importar - debería fallar o estar comentado
            parts = module_path.split('.')
            module_name = '.'.join(parts[:-1])
            attr_name = parts[-1]
            
            module = __import__(module_name, fromlist=[attr_name])
            if hasattr(module, attr_name):
                attr = getattr(module, attr_name)
                # Si el atributo existe y no es None/comentado, es violación
                if attr is not None:
                    violations.append(f"Servicio global activo: {module_path}")
                    
        except (ImportError, AttributeError):
            # Si no se puede importar, está bien (eliminado)
            pass
    
    if violations:
        raise RuntimeError(
            f"[ERROR] SERVICIOS GLOBALES DETECTADOS:\n" + 
            "\n".join(f"  - {v}" for v in violations) +
            "\nTodos los servicios deben obtenerse vía build_services()"
        )
    
    logger.info("[SUCCESS] Verificación runtime DI: OK")


if __name__ == "__main__":
    # Script de validación standalone
    project_root = Path(__file__).parent.parent.parent
    
    print("[SEARCH] Validando arquitectura DI estricta...")
    
    # Validación estática
    is_valid = validate_project_strict_di(project_root)
    
    # Validación runtime
    try:
        check_runtime_di_strict()
        runtime_ok = True
    except RuntimeError as e:
        print(f"\n{e}")
        runtime_ok = False
    
    # Resultado final
    if is_valid and runtime_ok:
        print("\n🎉 ARQUITECTURA DI ESTRICTA VALIDADA CORRECTAMENTE")
        sys.exit(0)
    else:
        print("\n[ERROR] FALLOS EN VALIDACIÓN DI - CORREGIR ANTES DE CONTINUAR")
        sys.exit(1)
