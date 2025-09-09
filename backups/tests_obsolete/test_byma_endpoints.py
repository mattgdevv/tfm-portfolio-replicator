#!/usr/bin/env python3
"""
Test de endpoints BYMA para encontrar datos históricos
"""

import requests
import json
import urllib3
from datetime import datetime, timedelta

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_byma_endpoints():
    """Prueba diferentes endpoints de BYMA para encontrar datos históricos"""
    
    print("🔍 Explorando endpoints BYMA para datos históricos")
    print("=" * 60)
    
    base_urls = [
        "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free",
        "https://api-mgr.byma.com.ar/eod",  # EndOfDay según el wrapper
        "https://api-mgr.byma.com.ar/delayed",  # Delayed según el wrapper
    ]
    
    endpoints_to_test = [
        "/cedears",
        "/indices",
        "/index", 
        "/indicators",
        "/equity",
        "/historical",
        "/history",
        "/eod",
        "/ccl",
        "/dolar",
        "/turnover"
    ]
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Portfolio-Replicator/1.0"
    }
    
    # Payload para CEDEARs que sabemos que funciona
    cedear_payload = {
        "excludeZeroPxAndQty": True,
        "T1": True,
        "T0": False
    }
    
    working_endpoints = []
    
    for base_url in base_urls:
        print(f"\n🌐 Probando base URL: {base_url}")
        print("-" * 40)
        
        for endpoint in endpoints_to_test:
            url = f"{base_url}{endpoint}"
            
            try:
                print(f"  📡 GET {endpoint}...", end=" ")
                
                # Probar GET primero
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=10,
                    verify=False
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, list) and len(data) > 0:
                            print(f"✅ {len(data)} items")
                            working_endpoints.append({
                                "url": url,
                                "method": "GET",
                                "items": len(data),
                                "sample": data[0] if data else None
                            })
                            continue
                        elif isinstance(data, dict) and data:
                            print(f"✅ Dict con {len(data)} keys")
                            working_endpoints.append({
                                "url": url,
                                "method": "GET",
                                "type": "dict",
                                "keys": list(data.keys())[:5],
                                "sample": data
                            })
                            continue
                    except json.JSONDecodeError:
                        pass
                
                # Si GET no funciona, probar POST con payload
                if endpoint == "/cedears":  # Solo para CEDEARs que sabemos que funciona con POST
                    print("❌ -> 📡 POST...", end=" ")
                    response = requests.post(
                        url,
                        json=cedear_payload,
                        headers=headers,
                        timeout=10,
                        verify=False
                    )
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if isinstance(data, list) and len(data) > 0:
                                print(f"✅ {len(data)} items")
                                working_endpoints.append({
                                    "url": url,
                                    "method": "POST",
                                    "payload": cedear_payload,
                                    "items": len(data),
                                    "sample": data[0] if data else None
                                })
                                continue
                        except json.JSONDecodeError:
                            pass
                
                print(f"❌ {response.status_code}")
                
            except requests.exceptions.RequestException as e:
                print(f"❌ {type(e).__name__}")
    
    # Mostrar resumen
    print(f"\n🎯 ENDPOINTS QUE FUNCIONAN ({len(working_endpoints)}):")
    print("=" * 60)
    
    for i, ep in enumerate(working_endpoints, 1):
        print(f"\n{i}. {ep['method']} {ep['url']}")
        
        if 'items' in ep:
            print(f"   📊 {ep['items']} elementos")
            if ep.get('sample'):
                sample = ep['sample']
                print(f"   📋 Sample keys: {list(sample.keys())[:8]}")
                if 'symbol' in sample:
                    print(f"   🏷️  Sample symbol: {sample.get('symbol')}")
                if 'trade' in sample:
                    print(f"   💰 Sample price: {sample.get('trade')}")
        
        elif 'keys' in ep:
            print(f"   🔑 Keys: {ep['keys']}")
    
    # Probar endpoints específicos para CCL/Indices
    print(f"\n🔍 PROBANDO ENDPOINTS ESPECÍFICOS PARA CCL:")
    print("=" * 60)
    
    ccl_endpoints = [
        "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free/indices",
        "https://api.byma.com.ar/indices",
        "https://api.byma.com.ar/ccl",
        "https://bymadata.com.ar/api/indices",
    ]
    
    for url in ccl_endpoints:
        try:
            print(f"📡 {url}...", end=" ")
            response = requests.get(url, headers=headers, timeout=5, verify=False)
            print(f"{response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ Datos obtenidos: {type(data)} con {len(data) if isinstance(data, (list, dict)) else 'N/A'} elementos")
                    if isinstance(data, list) and len(data) > 0:
                        print(f"   📋 Sample: {data[0]}")
                    elif isinstance(data, dict):
                        print(f"   🔑 Keys: {list(data.keys())[:5]}")
                except json.JSONDecodeError:
                    print(f"   ⚠️  No es JSON válido")
        except Exception as e:
            print(f"❌ {type(e).__name__}")

if __name__ == "__main__":
    test_byma_endpoints()