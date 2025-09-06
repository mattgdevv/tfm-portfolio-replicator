# ❌ ROTO POR MIGRACION DI: Este test usa imports legacy incompatibles
# 💡 Para migrar: usar build_services() en lugar de dollar_service global
# 📍 Referencia histórica: muestra como funcionaba el fallback CCL antes de DI estricto

import asyncio


def test_ccl_fallback_implicit_yahoo():
    """
    ❌ DEPRECATED: Test roto por migración a DI estricto
    
    Smoke Test – CCL Fallback Chain
    Objetivo: demostrar que, si IOL (AL30) y DolarAPI no están disponibles,
    el sistema obtiene un CCL válido usando el fallback implícito basado en Yahoo Finance.
    
    TODO: Migrar a DI usando build_services() si se requiere en el futuro
    """
    raise RuntimeError("Test roto por migración DI - usar build_services() en lugar de dollar_service global")
    # from app.services.dollar_rate import dollar_service  # ❌ YA NO EXISTE

    async def run():
        print("\n[SMOKE] CCL fallback: IOL/DolarAPI deshabilitados → Implicito (Yahoo)")
        # Forzar deshabilitar fuentes primarias
        dollar_service.sources_status["dolarapi_ccl"] = False
        dollar_service.sources_status["ccl_al30"] = False
        # Limpiar cache para asegurar refetch
        for key in ["ccl:dolarapi_ccl", "ccl:ccl_al30", "ccl_implicit_yahoo"]:
            dollar_service._cache.pop(key, None)
        result = await dollar_service.get_ccl_rate("dolarapi_ccl")
        assert isinstance(result, dict), "La respuesta debe ser un dict con metadatos"
        rate = result.get("rate")
        source = result.get("source")
        print(f"[SMOKE] CCL obtenido: ${rate} | fuente: {source} | preferida: {result.get('preferred_source')} | intentadas: {result.get('attempted_sources')}")
        assert rate and rate > 0, "CCL debe ser > 0"
        assert source in {"ccl_implicit_yahoo", "dolarapi_ccl", "ccl_al30"}, "Fuente desconocida"

    asyncio.run(run())


def test_cedear_price_fallback_yahoo():
    """
    Smoke Test – Precio CEDEAR con BYMA→Yahoo
    Objetivo: demostrar que en modo sin IOL podemos obtener precio ARS y USD de un CEDEAR
    mediante la cadena de fuentes (BYMA real, y si no, Yahoo .BA como fallback).
    """
    from app.services.arbitrage_detector import arbitrage_detector

    async def run():
        print("\n[SMOKE] Precio CEDEAR (modo limitado) con BYMA→Yahoo fallback")
        # Asegurar modo limitado (sin IOL)
        arbitrage_detector.set_iol_session(None)
        # Elegir un símbolo representativo
        symbol = "PLTR"
        price_ars, price_usd = await arbitrage_detector._get_cedear_price_usd(symbol)
        print(f"[SMOKE] {symbol}: precio CEDEAR ARS={price_ars} | acción vía CEDEAR USD={price_usd}")
        assert price_ars is not None and price_ars > 0, "Precio ARS debe ser > 0"
        assert price_usd is not None and price_usd > 0, "Precio USD debe ser > 0"

    asyncio.run(run())

