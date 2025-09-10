# ETL vs Interactive - Guía de Arquitectura

## 🎯 DIFERENCIAS CLAVE

### 📊 ETL Pipeline Automático
**Archivo:** `scripts/etl_cli.py`  
**Propósito:** Pipeline verdadero para automatización

```bash
# Ejecución automática sin interrupciones
python scripts/etl_cli.py --source excel --file data.csv --broker bullmarket
```

**Características:**
- ✅ 100% automatizado
- ✅ Parametrizable desde CLI
- ✅ Output estructurado (JSON)
- ✅ Para CI/CD y automatización
- ✅ Sin input del usuario
- ✅ Verdadero pipeline ETL

### 🎪 Aplicación Interactiva
**Archivo:** `main.py` + `app/etl/interactive_flows.py`  
**Propósito:** UI interactiva para exploración manual

```bash
# Aplicación con menú interactivo
python main.py
```

**Características:**
- 🎯 Requiere input del usuario en cada paso
- 🎯 Menú de opciones
- 🎯 Flujos paso a paso
- 🎯 Para análisis exploratorio
- 🎯 UI amigable
- 🎯 NO es un pipeline automático

## 📁 ESTRUCTURA ORGANIZADA

```
proyecto_2/
├── 🎪 main.py                     # Aplicación interactiva
├── 📊 scripts/etl_cli.py          # Pipeline ETL real
├── 📁 app/
│   ├── etl/
│   │   ├── interactive_flows.py   # Coordinador interactivo
│   │   └── commands/              # Comandos especializados
│   ├── core/                      # DI Container
│   ├── services/                  # Business logic
│   └── ...
├── 📁 docs/                       # Documentación
├── 📁 output/                     # Resultados ETL
└── 📁 backups/                    # Respaldos seguros
```

## 🎓 PARA TU TFM

### Documentar como:
1. **Pipeline ETL Real:** `etl_cli.py` - Automatización Data Engineer
2. **Aplicación Interactiva:** `main.py` - UI para exploración

### En el video explicar:
- ETL CLI = Pipeline automático 
- Main.py = Aplicación interactiva
- Ambos usan los mismos servicios DI

## ✅ NOMBRES CORREGIDOS

- ❌ ~~`pipeline.py`~~ (confuso)
- ✅ `interactive_flows.py` (claro)
- ✅ `etl_cli.py` (el verdadero pipeline)
