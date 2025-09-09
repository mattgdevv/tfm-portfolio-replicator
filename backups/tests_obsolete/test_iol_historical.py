#!/usr/bin/env python3
"""
Test de endpoints históricos de IOL
Investiga qué datos históricos podemos obtener
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import json

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.integrations.iol import IOLIntegration

async def test_iol_historical():
    """Prueba endpoints históricos de IOL"""
    print("🔍 Investigando endpoints históricos de IOL")
    print("=" * 60)
    
    # Solicitar credenciales
    username = input("Usuario IOL: ").strip()
    password = input("Contraseña IOL: ").strip()
    
    if not username or not password:
        print("❌ Credenciales requeridas")
        return
    
    try:
        # Autenticar
        iol = IOLIntegration()
        print("🔐 Autenticando con IOL...")
        await iol.authenticate(username, password)
        print("✅ Autenticado correctamente")
        
        # Test 1: Revisar respuesta de cotización actual para ver qué campos históricos tiene
        print("\n1️⃣ Investigando campos en cotización actual...")
        test_symbol = "TSLA"
        
        url = f"https://api.invertironline.com/api/v2/bcba/Titulos/{test_symbol}/Cotizacion"
        response = iol.session.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"📊 Campos disponibles en cotización de {test_symbol}:")
        for key, value in data.items():
            print(f"   {key}: {value}")
        
        # Test 2: Probar endpoints de históricos
        print(f"\n2️⃣ Probando endpoints históricos...")
        
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        historical_endpoints = [
            f"/api/v2/bcba/Titulos/{test_symbol}/Historico",
            f"/api/v2/bcba/Titulos/{test_symbol}/Historia",
            f"/api/v2/bcba/Titulos/{test_symbol}/Cotizaciones",
            f"/api/v2/bcba/Titulos/{test_symbol}/Precios",
            f"/api/v2/bcba/Titulos/{test_symbol}/SerieHistorica",
            f"/api/v2/Historicos/{test_symbol}",
            f"/api/v2/Historico/{test_symbol}",
            f"/api/v2/bcba/Titulos/{test_symbol}/Cotizacion?fecha={yesterday}",
            f"/api/v2/bcba/Titulos/{test_symbol}/Cotizacion?desde={week_ago}&hasta={yesterday}",
        ]
        
        base_url = "https://api.invertironline.com"
        
        working_endpoints = []
        
        for endpoint in historical_endpoints:
            try:
                print(f"   📡 {endpoint}...", end=" ")
                
                url = f"{base_url}{endpoint}"
                response = iol.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            print(f"✅ Lista con {len(data)} elementos")
                            if len(data) > 0:
                                print(f"      📋 Sample: {data[0]}")
                        elif isinstance(data, dict):
                            print(f"✅ Dict con {len(data)} keys")
                            print(f"      🔑 Keys: {list(data.keys())}")
                        else:
                            print(f"✅ Tipo: {type(data)}")
                        
                        working_endpoints.append({
                            "endpoint": endpoint,
                            "data": data,
                            "type": type(data).__name__
                        })
                    except json.JSONDecodeError:
                        print(f"✅ {response.status_code} (No JSON)")
                else:
                    print(f"❌ {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {type(e).__name__}")
        
        # Test 3: Probar otros símbolos para ver consistencia
        print(f"\n3️⃣ Probando otros CEDEARs...")
        
        other_symbols = ["AAPL", "AMD", "GOOGL"]
        
        for symbol in other_symbols:
            try:
                url = f"https://api.invertironline.com/api/v2/bcba/Titulos/{symbol}/Cotizacion"
                response = iol.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    precio_actual = data.get("ultimoPrecio", "N/A")
                    cierre_anterior = data.get("cierreAnterior", "N/A")
                    apertura = data.get("apertura", "N/A")
                    
                    print(f"   {symbol}: Actual=${precio_actual}, CierreAnt=${cierre_anterior}, Apertura=${apertura}")
                else:
                    print(f"   {symbol}: ❌ {response.status_code}")
                    
            except Exception as e:
                print(f"   {symbol}: ❌ {type(e).__name__}")
        
        # Test 4: Probar endpoints de bonos para CCL histórico
        print(f"\n4️⃣ Probando bonos para CCL histórico...")
        
        bond_symbols = ["AL30", "AL30D"]
        
        for bond in bond_symbols:
            try:
                # Precio actual
                url = f"https://api.invertironline.com/api/v2/bCBA/Titulos/{bond}/Cotizacion"
                response = iol.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   {bond} actual: {json.dumps(data, indent=2)}")
                    
                    # Intentar histórico
                    hist_url = f"https://api.invertironline.com/api/v2/bCBA/Titulos/{bond}/Historico"
                    hist_response = iol.session.get(hist_url, timeout=10)
                    
                    if hist_response.status_code == 200:
                        hist_data = hist_response.json()
                        print(f"   {bond} histórico: Tipo {type(hist_data)}, Len: {len(hist_data) if isinstance(hist_data, (list, dict)) else 'N/A'}")
                    else:
                        print(f"   {bond} histórico: ❌ {hist_response.status_code}")
                else:
                    print(f"   {bond}: ❌ {response.status_code}")
                    
            except Exception as e:
                print(f"   {bond}: ❌ {type(e).__name__}")
        
        # Resumen
        print(f"\n🎯 RESUMEN:")
        print("=" * 60)
        
        if working_endpoints:
            print(f"✅ {len(working_endpoints)} endpoints históricos funcionan:")
            for ep in working_endpoints:
                print(f"   • {ep['endpoint']} ({ep['type']})")
        else:
            print("❌ No se encontraron endpoints históricos funcionales")
        
        print(f"\n💡 ESTRATEGIA RECOMENDADA:")
        print("- Usar 'cierreAnterior' del endpoint actual para precio de ayer")
        print("- Si no está disponible, usar Yahoo Finance para subyacente + CCL teórico")
        print("- Para CCL histórico, usar AL30/AL30D si están disponibles")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import getpass
    
    # Monkey patch para getpass en async
    import builtins
    original_input = builtins.input
    
    def getpass_input(prompt):
        import getpass
        return getpass.getpass(prompt)
    
    # Reemplazar input con getpass para contraseña
    password_input = input("Contraseña IOL: ")
    
    asyncio.run(test_iol_historical())