#!/usr/bin/env python3
"""
❌ DEPRECATED: Test roto por migración a DI estricto

Script de prueba para VariationAnalyzer
Prueba el análisis de variaciones de CEDEARs vs subyacentes

TODO: Migrar usando build_services() para DI estricto
"""

# ❌ ROTO POR MIGRACION DI: Este test usa imports legacy incompatibles
# 💡 Para migrar: usar build_services() en lugar de variation_analyzer global
# 📍 Referencia histórica: muestra análisis de variaciones antes de DI estricto

import asyncio
import sys
import os

def main():
    """Test marcado como deprecated - requiere migración a DI"""
    raise RuntimeError("Test roto por migración DI - usar build_services() en lugar de variation_analyzer global")

if __name__ == "__main__":
    main()

# ❌ CODIGO LEGACY COMENTADO:
# # Agregar el directorio raíz al path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# 
# from app.services.variation_analyzer import variation_analyzer, VariationAnalyzer  # ❌ YA NO EXISTE
# from app.integrations.iol import IOLIntegration

async def test_variation_analyzer():
    """Prueba el analizador de variaciones"""
    print("🧪 Probando VariationAnalyzer")
    print("=" * 50)
    
    # Símbolos de prueba
    test_symbols = ["TSLA", "AAPL"]  # Comenzar con pocos para probar
    
    # 1. Probar modo limitado (sin IOL)
    print("1️⃣ Probando modo LIMITADO (precios teóricos)...")
    analyzer_limited = VariationAnalyzer()  # Sin sesión IOL
    
    try:
        analysis = await analyzer_limited.analyze_single_variation("TSLA")
        
        if analysis:
            print("✅ Análisis de variación completado:")
            print(analyzer_limited.format_detailed_analysis(analysis))
        else:
            print("❌ No se pudo completar el análisis de variación")
            
    except Exception as e:
        print(f"❌ Error en modo limitado: {e}")
    
    # 2. Probar múltiples símbolos
    print("\n2️⃣ Probando múltiples símbolos (modo limitado)...")
    try:
        analyses = await analyzer_limited.analyze_portfolio_variations(test_symbols)
        
        if analyses:
            print("✅ Análisis múltiple completado:")
            print(analyzer_limited.format_variation_report(analyses))
        else:
            print("❌ No se pudieron completar los análisis")
            
    except Exception as e:
        print(f"❌ Error con múltiples símbolos: {e}")
    
    # 3. Probar modo completo (con IOL) - opcional
    print("\n3️⃣ Probando modo COMPLETO (con IOL)...")
    
    test_iol = input("¿Probar con autenticación IOL? (s/n): ").strip().lower()
    
    if test_iol == 's':
        try:
            # Solicitar credenciales
            username = input("Usuario IOL: ").strip()
            password = input("Contraseña IOL: ").strip()
            
            if username and password:
                # Autenticar
                iol_integration = IOLIntegration()
                await iol_integration.authenticate(username, password)
                
                # Crear analizador con sesión IOL
                analyzer_full = VariationAnalyzer(iol_integration.session)
                
                print("🔐 Autenticado con IOL - probando modo completo...")
                
                analysis = await analyzer_full.analyze_single_variation("TSLA")
                
                if analysis:
                    print("✅ Análisis con IOL completado:")
                    print(analyzer_full.format_detailed_analysis(analysis))
                else:
                    print("❌ No se pudo completar el análisis con IOL")
            else:
                print("⚠️  Credenciales no proporcionadas - saltando prueba IOL")
                
        except Exception as e:
            print(f"❌ Error con modo IOL: {e}")
    else:
        print("⚠️  Saltando prueba con IOL")
    
    print("\n" + "=" * 50)
    print("🎯 Prueba de VariationAnalyzer completada")
    print("💡 El analizador está listo para integrarse en el PortfolioProcessor")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_variation_analyzer())