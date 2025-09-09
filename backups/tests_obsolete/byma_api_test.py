#!/usr/bin/env python3
"""
Test script para la API de BYMA - CEDEARs
"""

import requests
import json
import urllib3
from typing import Dict, List

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_byma_api():
    """Test BYMA API for CEDEARs data"""
    
    print("🔍 Testing BYMA API for CEDEARs...")
    
    # BYMA API endpoint
    url = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free/cedears"
    
    # Request payload
    payload = {
        "excludeZeroPxAndQty": True,
        "T1": True,
        "T0": False,
        "Content-Type": "application/json, text/plain"
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print("📡 Making request to BYMA API...")
        response = requests.post(url, json=payload, headers=headers, verify=False)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Success! Received {len(data)} CEDEARs")
        
        # Show first few CEDEARs
        print("\n📊 Sample CEDEARs data:")
        print("=" * 80)
        
        for i, cedear in enumerate(data[:10]):  # Show first 10
            print(f"\n{i+1}. {cedear.get('symbol', 'N/A')}")
            print(f"   Descripción: {cedear.get('securityDesc', 'N/A')}")
            print(f"   Tipo: {cedear.get('securityType', 'N/A')}")
            print(f"   Mercado: {cedear.get('market', 'N/A')}")
            print(f"   Precio: ${cedear.get('trade', 'N/A')}")
            print(f"   Moneda: {cedear.get('denominationCcy', 'N/A')}")
            print(f"   Volumen: {cedear.get('volume', 'N/A')}")
            print(f"   Bid: ${cedear.get('bidPrice', 'N/A')} | Ask: ${cedear.get('offerPrice', 'N/A')}")
        
        # Search for specific CEDEARs from your portfolio
        print("\n🔍 Searching for CEDEARs from your portfolio:")
        print("=" * 80)
        
        portfolio_cedeares = ["AAPL", "AMD", "BRKB", "TSLA", "PBR"]
        
        for symbol in portfolio_cedeares:
            found = False
            for cedear in data:
                if cedear.get('symbol') == symbol:
                    print(f"\n✅ Found {symbol}:")
                    print(f"   Precio: ${cedear.get('trade', 'N/A')} {cedear.get('denominationCcy', 'N/A')}")
                    print(f"   Bid: ${cedear.get('bidPrice', 'N/A')} | Ask: ${cedear.get('offerPrice', 'N/A')}")
                    print(f"   Volumen: {cedear.get('volume', 'N/A')}")
                    found = True
                    break
            
            if not found:
                print(f"❌ {symbol} not found in BYMA data")
        
        # Count CEDEARs by currency
        print("\n📈 Statistics:")
        print("=" * 80)
        
        pesos_count = 0
        usd_count = 0
        
        for cedear in data:
            currency = cedear.get('denominationCcy', '')
            if currency == 'ARS':
                pesos_count += 1
            elif currency == 'USD':
                usd_count += 1
        
        print(f"Total CEDEARs: {len(data)}")
        print(f"CEDEARs en pesos: {pesos_count}")
        print(f"CEDEARs en dólares: {usd_count}")
        
        # Save full data to file
        with open('byma_cedeares.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Full data saved to 'byma_cedeares.json'")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error making request: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_byma_api() 