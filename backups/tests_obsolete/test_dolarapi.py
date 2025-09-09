#!/usr/bin/env python3
"""
Script de prueba para probar endpoints de dolarapi.com
"""

import requests
from datetime import datetime
import json

def test_dolarapi_endpoints():
    """Test different dolarapi.com endpoints"""
    
    base_url = "https://dolarapi.com/v1/dolares"
    
    endpoints = {
        "CCL": f"{base_url}/contadoconliqui",  # Endpoint correcto
        "MEP (Bolsa)": f"{base_url}/bolsa", 
        "Oficial": f"{base_url}/oficial",
        "Blue": f"{base_url}/blue"
    }
    
    print("🔍 Probando endpoints de dolarapi.com...")
    print("=" * 50)
    
    results = {}
    
    for name, url in endpoints.items():
        print(f"\n📊 Probando {name}: {url}")
        try:
            response = requests.get(url, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Respuesta exitosa:")
                print(f"   Compra: ${data.get('compra', 'N/A')}")
                print(f"   Venta: ${data.get('venta', 'N/A')}")
                print(f"   Casa: {data.get('casa', 'N/A')}")
                print(f"   Nombre: {data.get('nombre', 'N/A')}")
                print(f"   Fecha: {data.get('fechaActualizacion', 'N/A')}")
                
                results[name] = {
                    "success": True,
                    "data": data
                }
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                results[name] = {
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error de conexión: {str(e)}")
            results[name] = {
                "success": False,
                "error": str(e)
            }
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {str(e)}")
            results[name] = {
                "success": False,
                "error": f"JSON error: {str(e)}"
            }
    
    print("\n" + "=" * 50)
    print("📋 RESUMEN DE RESULTADOS:")
    print("=" * 50)
    
    successful = []
    failed = []
    
    for name, result in results.items():
        if result["success"]:
            successful.append(name)
            data = result["data"]
            print(f"✅ {name}: Compra=${data.get('compra')} | Venta=${data.get('venta')}")
        else:
            failed.append(name)
            print(f"❌ {name}: {result['error']}")
    
    print(f"\n🎯 Exitosos: {len(successful)}/{len(endpoints)}")
    if successful:
        print(f"   {', '.join(successful)}")
    
    if failed:
        print(f"❌ Fallidos: {len(failed)}/{len(endpoints)}")
        print(f"   {', '.join(failed)}")
    
    # Recomendación para uso
    if "CCL" in successful:
        ccl_data = results["CCL"]["data"]
        print(f"\n💡 RECOMENDACIÓN:")
        print(f"   Para CEDEARs usar CCL: ${ccl_data.get('venta')} (venta)")
        print(f"   Endpoint: {endpoints['CCL']}")
    
    return results

if __name__ == "__main__":
    test_dolarapi_endpoints()