#!/usr/bin/env python3
"""
Test script para investigar información de FCIs desde IOL API
"""

import requests
from datetime import datetime, timedelta
import json

class IOLAuth:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.bearer_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.base_url = "https://api.invertironline.com"

    def get_bearer_token(self) -> str:
        """Get a valid bearer token, refreshing if necessary."""
        if (not self.bearer_token or 
            not self.token_expiry or 
            datetime.now() >= self.token_expiry):
            self._refresh_tokens()
        return self.bearer_token

    def _refresh_tokens(self):
        """Refresh the bearer token using the refresh token."""
        try:
            if not self.refresh_token:
                response = requests.post(
                    f"{self.base_url}/token",
                    data={
                        "username": self.username,
                        "password": self.password,
                        "grant_type": "password"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
            else:
                response = requests.post(
                    f"{self.base_url}/token",
                    data={
                        "refresh_token": self.refresh_token,
                        "grant_type": "refresh_token"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
            
            response.raise_for_status()
            data = response.json()
            
            self.bearer_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            self.token_expiry = datetime.now() + timedelta(minutes=14)
            
            print("✅ Tokens refreshed successfully")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error refreshing tokens: {str(e)}")
            raise

def test_fci_info():
    """Test FCI information from IOL API"""
    
    # Get credentials
    username = input("Usuario IOL: ").strip()
    password = input("Contraseña IOL: ").strip()
    
    # Initialize auth
    auth = IOLAuth(username, password)
    
    try:
        # Get bearer token
        bearer_token = auth.get_bearer_token()
        print("\n✅ Successfully authenticated with IOL API!")
        
        # Set up session with auth
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        })
        
        print("\n🔍 Testing FCI information...")
        
        # Test 1: Get portfolio to see IOLDOLD details
        print("\n1️⃣ Portfolio positions (looking for IOLDOLD):")
        try:
            response = session.get(f"{auth.base_url}/api/v2/portafolio")
            response.raise_for_status()
            data = response.json()
            
            for position in data.get("activos", []):
                titulo = position["titulo"]
                if "IOLDOLD" in titulo["simbolo"]:
                    print(f"\n🎯 Found IOLDOLD:")
                    print(f"   Símbolo: {titulo['simbolo']}")
                    print(f"   Descripción: {titulo['descripcion']}")
                    print(f"   Tipo: {titulo['tipo']}")
                    print(f"   País: {titulo.get('pais', 'N/A')}")
                    print(f"   Mercado: {titulo.get('mercado', 'N/A')}")
                    print(f"   Moneda: {titulo.get('moneda', 'N/A')}")
                    print(f"   Cantidad: {position['cantidad']}")
                    print(f"   Precio: {position['ultimoPrecio']}")
                    print(f"   Valorizado: {position['valorizado']}")
                    print(f"   PPC: {position['ppc']}")
                    
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 2: Get FCI information
        print("\n2️⃣ Testing FCI endpoints:")
        try:
            response = session.get(f"{auth.base_url}/api/v2/Titulos/FCI")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 3: Get specific FCI info
        print("\n3️⃣ Testing specific FCI info for IOLDOLD:")
        try:
            response = session.get(f"{auth.base_url}/api/v2/Titulos/FCI/IOLDOLD")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 4: Get FCI administrators
        print("\n4️⃣ Testing FCI administrators:")
        try:
            response = session.get(f"{auth.base_url}/api/v2/Titulos/FCI/Administradoras")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n✅ All FCI tests completed!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    test_fci_info() 