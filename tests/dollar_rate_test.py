#!/usr/bin/env python3
"""
Test script para obtener la cotización del dólar desde IOL API
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
                # Initial token request
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
                # Refresh existing token
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

def test_dollar_endpoints():
    """Test different endpoints to get dollar rate"""
    
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
        
        print("\n🔍 Testing different dollar rate endpoints...")
        
        # Test 1: POST /api/v2/Cotizaciones/MEP
        print("\n1️⃣ Testing POST /api/v2/Cotizaciones/MEP")
        try:
            response = session.post(
                f"{auth.base_url}/api/v2/Cotizaciones/MEP",
                json={
                    "idPlazoOperatoriaVenta": 0,
                    "simbolo": "GGAL"
                }
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 2: GET /api/v2/Cotizaciones/MEP/GGAL
        print("\n2️⃣ Testing GET /api/v2/Cotizaciones/MEP/GGAL")
        try:
            response = session.get(f"{auth.base_url}/api/v2/Cotizaciones/MEP/GGAL")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 3: GET /api/v2/bCBA/Titulos/GGAL/Cotizacion
        print("\n3️⃣ Testing GET /api/v2/bCBA/Titulos/GGAL/Cotizacion")
        try:
            response = session.get(f"{auth.base_url}/api/v2/bCBA/Titulos/GGAL/Cotizacion")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 4: GET /api/v2/estados_Unidos/Titulos/Cotizacion/Instrumentos
        print("\n4️⃣ Testing GET /api/v2/estados_Unidos/Titulos/Cotizacion/Instrumentos")
        try:
            response = session.get(f"{auth.base_url}/api/v2/estados_Unidos/Titulos/Cotizacion/Instrumentos")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 5: GET /api/v2/Cotizaciones/MEP/estados_Unidos/Todos
        print("\n5️⃣ Testing GET /api/v2/Cotizaciones/MEP/estados_Unidos/Todos")
        try:
            response = session.get(f"{auth.base_url}/api/v2/Cotizaciones/MEP/estados_Unidos/Todos")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 6: GET /api/v2/Cotizaciones/CCL (nuevo test)
        print("\n6️⃣ Testing GET /api/v2/Cotizaciones/CCL")
        try:
            response = session.get(f"{auth.base_url}/api/v2/Cotizaciones/CCL")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 7: POST /api/v2/Cotizaciones/CCL (nuevo test)
        print("\n7️⃣ Testing POST /api/v2/Cotizaciones/CCL")
        try:
            response = session.post(
                f"{auth.base_url}/api/v2/Cotizaciones/CCL",
                json={
                    "idPlazoOperatoriaVenta": 0,
                    "simbolo": "GGAL"
                }
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    test_dollar_endpoints() 