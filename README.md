# Portfolio Replicator

**Multi-source arbitrage detection system for CEDEARs vs underlying assets with intelligent fallback estimation**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Async](https://img.shields.io/badge/Async-asyncio-green.svg)](https://docs.python.org/3/library/asyncio.html)
[![Architecture](https://img.shields.io/badge/Architecture-DI-orange.svg)](https://en.wikipedia.org/wiki/Dependency_injection)

## ⚡ Quick Start

```bash
# Setup
git clone <repository-url> && cd portfolio-replicator
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Interactive mode
python main.py

# ETL Pipeline
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket
```

## 🎯 Features

- **Real-time Arbitrage Detection** - Multi-source price comparison with configurable thresholds
- **Intelligent Fallback Estimation** - Automatic theoretical pricing when markets are closed or unavailable
- **Multi-broker Support** - IOL API, Excel/CSV (Bull Market, Cocos Capital)
- **Robust Data Pipeline** - Automatic fallbacks, caching, and error handling
- **Configurable ETL** - CLI with flexible parameters and output formats
- **24/7 Analysis** - Works on weekends using international prices + CCL estimation

## ⚙️ Configuration

### Basic Setup
```json
// .prefs.json
{
  "arbitrage_threshold": 0.005,
  "request_timeout": 30,
  "cache_ttl_seconds": 180
}
```

### Environment Variables (CI/CD)
```bash
export ARBITRAGE_THRESHOLD=0.01
export REQUEST_TIMEOUT=25
export CACHE_TTL_SECONDS=300
python main.py
```

### ETL CLI Parameters
```bash
# Default configuration
python scripts/etl_cli.py --source excel --file data.csv

# Custom threshold and broker
python scripts/etl_cli.py --source excel --file data.csv --threshold 0.015 --broker bullmarket

# All parameters
python scripts/etl_cli.py \
  --source excel \
  --file data.csv \
  --broker cocos \
  --threshold 0.01 \
  --timeout 45 \
  --cache-ttl 300 \
  --output results/
```

## 🗂️ Data Sources

| Source | Type | Support |
|--------|------|---------|
| **IOL API** | Live | ✅ Real-time portfolio & prices |
| **Bull Market** | Excel/CSV | ✅ Custom format parsing |
| **Cocos Capital** | Excel/CSV | ✅ Custom format parsing |
| **Generic** | Excel/CSV | ✅ Standard format |
| **BYMA** | API | ✅ CEDEAR ratios & data |
| **Finnhub** | API | ✅ International prices |
| **DolarAPI** | API | ✅ CCL rates |

## 📊 Output Examples

### Console Output
```
📊 Configuración ETL:
   • Threshold: 0.015 (1.5%)
   • Timeout: 45s
   • Cache TTL: 180s
   ↳ Sobrescrito por CLI: threshold=0.015, timeout=45s

🚨 OPORTUNIDAD DETECTADA: SPY - 0.5%
🚨 Arbitraje detectado en SPY: 0.5%
```

### JSON Output
```json
{
  "symbol": "SPY",
  "arbitrage_percentage": 0.005,
  "recommendation": "Comprar subyacente, vender CEDEAR",
  "cedear_price_usd": 461.25,
  "underlying_price_usd": 463.89
}
```

## 🏗️ Architecture

### Dependency Injection
- **15 specialized services** with automatic injection
- **Zero global state** - pure dependency injection  
- **Runtime validation** - startup dependency checks

### Data Pipeline
```
Portfolio Input → Format Detection → CEDEAR Processing → Price Fetching → Arbitrage Analysis → Output
```

### Error Handling
- **Graceful degradation** - continues with available data
- **Multiple fallbacks** - DolarAPI → IOL → Cache → Theoretical estimation
- **Weekend/Holiday support** - automatic theoretical pricing when markets closed
- **Detailed logging** - structured error reporting

### Intelligent Estimation
When real-time data is unavailable (weekends, holidays, API failures):
1. **International prices** fetched from Finnhub (real-time)
2. **CCL rate** obtained from DolarAPI (available 24/7)
3. **Theoretical CEDEAR price** calculated using conversion ratios
4. **Arbitrage detection** continues seamlessly with estimated prices

## 📚 API Reference

### ETL CLI Options
```bash
--source {excel}              # Data source type
--file FILE                   # Portfolio file path  
--broker {cocos,bullmarket,generic}  # Broker format
--threshold FLOAT             # Arbitrage threshold (default: config)
--timeout INT                 # Request timeout in seconds
--cache-ttl INT              # Cache TTL in seconds  
--output DIR                 # Output directory
--no-save                    # Don't save files
--verbose                    # Detailed logging
```

### Configuration Priority
1. **CLI parameters** (highest)
2. **Environment variables** 
3. **`.prefs.json`**
4. **Code defaults** (lowest)

## 🛠️ Development

### Project Structure
```
app/
├── core/           # DI Container & Config
├── services/       # Business Logic (15 services)
├── integrations/   # External APIs (IOL, BYMA)
├── processors/     # Data Processing
├── models/         # Data Models
├── utils/          # Utilities
└── ui/             # User Interface
```

### Adding New Services
```python
# 1. Create service
class NewService:
    def __init__(self, dependency_service, config=None):
        self.dependency = dependency_service
        self.config = config

# 2. Register in build_services()
new_service = NewService(existing_service, config=config)
```

## 🧪 Testing

Tests prepared for DI-compatible implementation:
```python
import pytest
from app.core.services import build_services

def test_arbitrage_detector():
    services = build_services()
    detector = services.arbitrage_detector
    # Test logic here...
```

## 🚨 Known Issues

- **IOL session expiry**: Re-authentication required
- **BYMA PDF dependency**: Manual updates for new CEDEARs
- **Test suite**: Needs migration to pytest with DI support

---

*Portfolio Replicator - Multi-source arbitrage detection system for financial markets*