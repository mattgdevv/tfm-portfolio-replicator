"""
Servicio para manejo de archivos y exportación de portfolios
"""
import pandas as pd
from datetime import datetime
from typing import Optional
from pathlib import Path

from app.models.portfolio import Portfolio, ConvertedPortfolio


class FileService:
    """Servicio para operaciones de archivos y exportación"""
    
    async def save_results(self, original: Portfolio, converted: ConvertedPortfolio = None):
        """Guarda los resultados en archivos"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Guardar portfolio original
            original_data = []
            for pos in original.positions:
                original_data.append({
                    'symbol': pos.symbol,
                    'quantity': pos.quantity,
                    'price': pos.price,
                    'currency': pos.currency,
                    'total_value': pos.total_value,
                    'is_cedear': pos.is_cedear,
                    'underlying_symbol': pos.underlying_symbol,
                    'underlying_quantity': pos.underlying_quantity
                })
            
            original_df = pd.DataFrame(original_data)
            original_file = f"portfolio_original_{timestamp}.xlsx"
            original_df.to_excel(original_file, index=False)
            print(f"✅ Portfolio original guardado: {original_file}")
            
            # Guardar portfolio convertido si existe
            if converted:
                converted_data = []
                for pos in converted.converted_positions:
                    converted_data.append({
                        'symbol': pos.symbol,
                        'quantity': pos.quantity,
                        'price': pos.price,
                        'currency': pos.currency,
                        'total_value': pos.total_value
                    })
                
                converted_df = pd.DataFrame(converted_data)
                converted_file = f"portfolio_converted_{timestamp}.xlsx"
                converted_df.to_excel(converted_file, index=False)
                print(f"✅ Portfolio convertido guardado: {converted_file}")
                
        except Exception as e:
            print(f"❌ Error guardando archivos: {e}")
