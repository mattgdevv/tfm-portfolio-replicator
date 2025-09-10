import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from ..models.portfolio import Portfolio, Position
# ❌ ELIMINADO: import de instancia global - usar DI
# from ..processors.cedeares import CEDEARProcessor

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
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error refreshing IOL API tokens: {str(e)}")

class IOLIntegration:
    def __init__(self, dollar_service, cedear_processor):
        """
        Constructor con Dependency Injection estricta
        
        Args:
            dollar_service: Servicio de cotización dólar (REQUERIDO)
            cedear_processor: Procesador de CEDEARs (REQUERIDO)
        """
        if dollar_service is None:
            raise ValueError("dollar_service es requerido - use build_services() para crear instancias")
        if cedear_processor is None:
            raise ValueError("cedear_processor es requerido - use build_services() para crear instancias")
            
        self.auth = None
        self.session = None
        self.dollar_service = dollar_service
        self.cedear_processor = cedear_processor

    async def authenticate(self, username: str, password: str):
        """Authenticate with IOL API."""
        self.auth = IOLAuth(username, password)
        bearer_token = self.auth.get_bearer_token()
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        })
        
        # Establecer la sesión en el servicio de dólar para CCL AL30
        self.dollar_service.set_iol_session(self.session)

    async def get_portfolio(self) -> Portfolio:
        """Get portfolio from IOL API."""
        if not self.session:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        # Get portfolio positions
        response = self.session.get(f"{self.auth.base_url}/api/v2/portafolio")
        response.raise_for_status()
        data = response.json()
        
        # Convert to our Portfolio model
        positions = []
        for position_data in data.get("activos", []):
            titulo = position_data["titulo"]
            symbol = titulo["simbolo"]
            
            # Check if this is a CEDEAR
            is_cedear = self.cedear_processor.is_cedear(symbol)
            underlying_info = None
            underlying_quantity = None
            conversion_ratio = None
            
            # Determine asset type and currency
            moneda = titulo.get("moneda", "").lower()
            tipo = titulo.get("tipo", "")
            
            is_fci_usd = titulo.get("tipo") == "FondoComundeInversion" and "dolar" in moneda
            is_fci_ars = titulo.get("tipo") == "FondoComundeInversion" and "peso" in moneda
            
            if is_cedear:
                underlying_info = self.cedear_processor.get_underlying_asset(symbol)
                if underlying_info:
                    conversion_ratio = self.cedear_processor.parse_ratio(underlying_info["ratio"])
                    underlying_quantity = position_data["cantidad"] / conversion_ratio
            
            position = Position(
                symbol=symbol,
                quantity=position_data["cantidad"],
                price=position_data["ultimoPrecio"],
                total_value=position_data["valorizado"],  # Usar el valor real calculado por IOL
                currency="USD" if is_fci_usd else "ARS",  # USD for dollar FCIs, ARS for others
                is_cedear=is_cedear,
                underlying_symbol=underlying_info["symbol"] if underlying_info else None,
                underlying_quantity=underlying_quantity,
                conversion_ratio=conversion_ratio,
                is_fci_usd=is_fci_usd,
                is_fci_ars=is_fci_ars
            )
            positions.append(position)
        
        return Portfolio(
            positions=positions,
            broker="iol"
        )

    async def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary (cash balances, etc.)."""
        if not self.session:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        response = self.session.get(f"{self.auth.base_url}/api/v2/estadocuenta")
        response.raise_for_status()
        return response.json()

    async def get_dollar_rate(self) -> float:
        """Get current USD/ARS exchange rate using MEP."""
        if not self.session:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            # Get MEP rate using GGAL as proxy
            response = self.session.get(f"{self.auth.base_url}/api/v2/Cotizaciones/MEP/GGAL")
            response.raise_for_status()
            data = response.text.strip()
            
            # The response is just the rate as a string
            dollar_rate = float(data)
            print(f"💱 Dólar MEP (GGAL): ${dollar_rate:,.2f} ARS")
            return dollar_rate
            
        except Exception as e:
            print(f"Warning: Could not get dollar rate from API: {e}")
            return 1000.0  # Default fallback 