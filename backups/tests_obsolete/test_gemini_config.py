#!/usr/bin/env python3
"""
Script de prueba para verificar la configuración de Gemini
"""

from app.config import settings

def test_gemini_config():
    print("🔍 Verificando configuración de Gemini...")
    
    if settings.GEMINI_API_KEY:
        print("✅ API key de Gemini encontrada")
        print(f"   Longitud: {len(settings.GEMINI_API_KEY)} caracteres")
        print(f"   Inicio: {settings.GEMINI_API_KEY[:10]}...")
    else:
        print("❌ API key de Gemini NO encontrada")
        print("   Verifica que el archivo .env existe y contiene GEMINI_API_KEY=tu_key")
        return False
    
    return True

if __name__ == "__main__":
    test_gemini_config() 