from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # API Keys
    IOL_USERNAME: Optional[str] = None
    IOL_PASSWORD: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    FINNHUB_API_KEY: Optional[str] = None  # para fallback de precios internacionales
    
    # IOL API configuration
    IOL_BASE_URL: str = "https://api.invertironline.com"
    
    # Dollar rate configuration
    PREFERRED_CCL_SOURCE: str = "dolarapi_ccl"  # "dolarapi_ccl" o "ccl_al30"
    
    # pydantic-settings v2 config
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",  # ignorar claves extra en .env (no romper si hay más variables)
    )

settings = Settings()