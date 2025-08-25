import requests
from datetime import datetime, timedelta
from loguru import logger
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
            self.token_expiry = datetime.now() + timedelta(minutes=14)  # 14 minutes to be safe
            
            logger.info("Successfully refreshed IOL API tokens")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error refreshing IOL API tokens: {str(e)}")
            raise

def format_currency(amount: float, currency: str = "ARS") -> str:
    """Format a number as currency."""
    return f"${amount:,.2f} {currency}"

def format_percentage(value: float) -> str:
    """Format a number as percentage."""
    return f"{value:+.2f}%" if value != 0 else "0.00%"

def main():
    # Get credentials
    username = input("Enter your IOL username: ")
    password = input("Enter your IOL password: ")
    
    # Initialize auth
    auth = IOLAuth(username, password)
    
    try:
        # Get bearer token
        bearer_token = auth.get_bearer_token()
        print("\nSuccessfully authenticated with IOL API!")
        
        # Set up session with auth
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        })
        
        # Get cash balances and positions from /api/v2/estadocuenta
        print("\nFetching your account summary...")
        response_estado = session.get(f"{auth.base_url}/api/v2/estadocuenta")
        response_estado.raise_for_status()
        estado_data = response_estado.json()
        ars_account = None
        usd_account = None
        for cuenta in estado_data.get("cuentas", []):
            moneda = cuenta.get("moneda", "").lower()
            if "peso" in moneda:
                ars_account = cuenta
            elif "dolar" in moneda:
                usd_account = cuenta
        
        # Print ARS summary
        print("\n" + "="*80)
        print("PORTFOLIO SUMMARY (ARS)".center(80))
        print("="*80)
        if ars_account:
            print(f"\nActivos valorizados en ARS: {format_currency(ars_account.get('titulosValorizados', 0.0), 'ARS')}")
            print(f"Saldo disponible en ARS:    {format_currency(ars_account.get('disponible', 0.0), 'ARS')}")
            print(f"Saldo total valorizado:     {format_currency(ars_account.get('total', 0.0), 'ARS')}")
        else:
            print("No ARS account found.")
        
        # Print USD summary if available
        print("\n" + "="*80)
        print("PORTFOLIO SUMMARY (USD)".center(80))
        print("="*80)
        if usd_account:
            print(f"\nSaldo disponible en USD:    {format_currency(usd_account.get('disponible', 0.0), 'USD')}")
            print(f"Saldo total valorizado:     {format_currency(usd_account.get('total', 0.0), 'USD')}")
        else:
            print("No USD account found.")
        
        # Get portfolio positions (for ARS)
        print("\nFetching your portfolio positions...")
        response = session.get(f"{auth.base_url}/api/v2/portafolio")
        response.raise_for_status()
        data = response.json()
        
        print("\n" + "="*80)
        print("POSITIONS (ARS)".center(80))
        print("="*80)
        for position in data.get("activos", []):
            titulo = position["titulo"]
            print(f"\n{titulo['descripcion']} ({titulo['simbolo']})")
            print("-" * 80)
            print(f"Type: {titulo['tipo']}")
            print(f"Quantity: {position['cantidad']:,.0f}")
            print(f"Current Price: {format_currency(position['ultimoPrecio'], 'ARS')}")
            print(f"Total Value: {format_currency(position['valorizado'], 'ARS')}")
            print(f"Average Cost: {format_currency(position['ppc'], 'ARS')}")
            print(f"Daily Change: {format_percentage(position['variacionDiaria'])}")
            print(f"Total P/L: {format_currency(position['gananciaDinero'], 'ARS')} ({format_percentage(position['gananciaPorcentaje'])})")
        
    except requests.exceptions.RequestException as e:
        print(f"\nError: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")

if __name__ == "__main__":
    main() 