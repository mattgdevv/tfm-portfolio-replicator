#!/usr/bin/env python3
"""
Script de prueba para ArbitrageDetector
Prueba la detección de arbitraje entre CEDEARs y subyacentes
"""

import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.arbitrage_detector import arbitrage_detector, ArbitrageDetector
from app.integrations.iol import IOLIntegration

async def test_arbitrage_detector():
    """Prueba el detector de arbitraje"""
    print("🧪 Probando ArbitrageDetector")
    print("=" * 50)
    
    # Símbolos de prueba
    test_symbols = ["TSLA", "PLTR", "AMD"]
    
    # 1. Probar modo limitado (sin IOL)
    print("1️⃣ Probando modo LIMITADO (precios teóricos)...")
    detector_limited = ArbitrageDetector()  # Sin sesión IOL
    
    try:
        opportunity = await detector_limited.detect_single_arbitrage("TSLA", threshold_percentage=0.01)  # 1% threshold para testing
        
        if opportunity:
            print("✅ Oportunidad detectada en modo limitado:")
            print(detector_limited.format_alert(opportunity))
        else:
            print("ℹ️  No se detectó oportunidad significativa para TSLA")
            
    except Exception as e:
        print(f"❌ Error en modo limitado: {e}")
    
    # 2. Probar múltiples símbolos en modo limitado
    print("\n2️⃣ Probando múltiples símbolos (modo limitado)...")
    try:
        opportunities = await detector_limited.detect_portfolio_arbitrages(test_symbols, threshold_percentage=0.01)
        
        if opportunities:
            print(f"✅ {len(opportunities)} oportunidades detectadas:")
            for opp in opportunities:
                print(f"   📊 {opp.symbol}: {opp.difference_percentage:.1%} ({opp.difference_usd:+.2f} USD)")
        else:
            print("ℹ️  No se detectaron oportunidades significativas")
            
    except Exception as e:
        print(f"❌ Error con múltiples símbolos: {e}")
    
    # 3. Probar modo completo (con IOL) - opcional
    print("\n3️⃣ Probando modo COMPLETO (con IOL)...")
    
    # Preguntar si quiere probar con IOL
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
                
                # Crear detector con sesión IOL
                detector_full = ArbitrageDetector(iol_integration.session)
                
                print("🔐 Autenticado con IOL - probando modo completo...")
                
                opportunity = await detector_full.detect_single_arbitrage("TSLA", threshold_percentage=0.01)
                
                if opportunity:
                    print("✅ Oportunidad detectada en modo completo:")
                    print(detector_full.format_alert(opportunity))
                    print("\n📊 Comparación de modos:")
                    print(f"   🟡 Teórico: ${opportunity.cedear_price_usd:.2f} USD")
                    print(f"   🔴 Real IOL: Disponible en modo completo")
                else:
                    print("ℹ️  No se detectó oportunidad significativa con IOL")
            else:
                print("⚠️  Credenciales no proporcionadas - saltando prueba IOL")
                
        except Exception as e:
            print(f"❌ Error con modo IOL: {e}")
    else:
        print("⚠️  Saltando prueba con IOL")
    
    # 4. Mostrar ejemplo de alerta formateada
    print("\n4️⃣ Ejemplo de alerta formateada:")
    
    # Crear oportunidad de ejemplo para demostrar formato
    from app.services.arbitrage_detector import ArbitrageOpportunity
    
    example_opp = ArbitrageOpportunity(
        symbol="TSLA",
        cedear_price_usd=280.50,
        underlying_price_usd=309.83,
        difference_usd=29.33,
        difference_percentage=0.095,  # 9.5%
        ccl_rate=1362.14,
        cedear_price_ars=382000,
        iol_session_active=False
    )
    
    print(detector_limited.format_alert(example_opp))
    
    print("\n" + "=" * 50)
    print("🎯 Prueba de ArbitrageDetector completada")
    print("💡 El detector está listo para integrarse en el PortfolioProcessor")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_arbitrage_detector())