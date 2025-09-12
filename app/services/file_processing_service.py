"""
Servicio para procesamiento de archivos Excel/CSV
"""
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from typing import Optional, Tuple

from app.models.portfolio import Portfolio


class FileProcessingService:
    """Servicio para manejo de archivos Excel/CSV y selección de archivos"""
    
    def __init__(self, portfolio_processor):
        self.portfolio_processor = portfolio_processor
    
    async def handle_excel_portfolio(self) -> Optional[Portfolio]:
        """Maneja la carga de portfolio desde archivo Excel o CSV"""
        print("\n📁 Cargando portfolio desde archivo Excel/CSV...")
        
        try:
            # Obtener archivo usando interfaz gráfica o modo manual
            file_path = await self._get_file_path()
            
            if not file_path:
                print("❌ No se seleccionó archivo")
                return None
            
            # Verificar que el archivo existe
            if not Path(file_path).exists():
                print(f"❌ El archivo no existe: {file_path}")
                return None
            
            print(f"📁 Archivo seleccionado: {Path(file_path).name}")
            
            # Preguntar el tipo de broker
            broker_type = self._get_broker_type()
            if not broker_type:
                return None
            
            # Procesar el archivo
            print("📊 Procesando archivo...")
            portfolio = await self.portfolio_processor.process_file(file_path, broker_type)
            
            return portfolio
            
        except Exception as e:
            print(f"❌ Error procesando archivo: {e}")
            return None
    
    async def _get_file_path(self) -> Optional[str]:
        """Obtiene la ruta del archivo usando interfaz gráfica o modo manual"""
        file_path = None
        
        # Intentar usar tkinter para selección de archivo
        try:
            file_path = self._show_file_dialog()
        except Exception as e:
            print(f"⚠️  Error con interfaz gráfica: {e}")
            print("🔄 Cambiando a modo manual...")
        
        # Si no se obtuvo archivo con tkinter, usar modo manual
        if not file_path:
            file_path = self._get_file_manual()
        
        return file_path
    
    def _show_file_dialog(self) -> Optional[str]:
        """Muestra el diálogo de selección de archivo usando tkinter"""
        # Crear ventana principal
        root = tk.Tk()
        root.title("Adjuntar archivo de portfolio")
        root.geometry("400x200")
        
        # Centrar la ventana
        root.eval('tk::PlaceWindow . center')
        
        # Variable para almacenar el archivo seleccionado
        file_path = None
        
        # Función que se ejecuta al presionar el botón
        def adjuntar_archivo():
            nonlocal file_path
            archivo = filedialog.askopenfilename(
                title="Seleccionar archivo de portfolio",
                filetypes=[
                    ("Archivos Excel", "*.xlsx *.xls"),
                    ("Archivos CSV", "*.csv"),
                    ("Todos los archivos", "*.*")
                ]
            )
            if archivo:
                file_path = archivo
                print(f"✅ Archivo seleccionado: {archivo}")
                root.quit()  # Cerrar la ventana
            else:
                print("❌ No se seleccionó ningún archivo")
                root.quit()
        
        # Crear el botón y agregarlo a la ventana
        boton = tk.Button(root, text="📎 Adjuntar archivo", command=adjuntar_archivo, 
                        font=("Arial", 14), bg="#4CAF50", fg="white", 
                        relief="raised", bd=3)
        boton.pack(pady=50)
        
        # Texto explicativo
        label = tk.Label(root, text="Selecciona tu archivo de portfolio\n(Excel o CSV)", 
                       font=("Arial", 12))
        label.pack(pady=20)
        
        print("🔍 Abriendo ventana para adjuntar archivo...")
        
        # Iniciar el bucle principal
        root.mainloop()
        
        return file_path
    
    def _get_file_manual(self) -> Optional[str]:
        """Obtiene la ruta del archivo en modo manual"""
        print("\n📝 Cambiando a modo manual...")
        print("Nota: Puedes arrastrar el archivo desde Finder/Explorer a esta terminal")
        print("   O escribir la ruta completa del archivo")
        
        file_path = input("📎 Archivo (arrastra o escribe ruta): ").strip()
        
        if not file_path:
            return None
        
        # Limpiar la ruta si el usuario arrastró el archivo
        if file_path.startswith("'") and file_path.endswith("'"):
            file_path = file_path[1:-1]
        elif file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]
        
        return file_path
    
    def _get_broker_type(self) -> Optional[str]:
        """Pregunta al usuario el tipo de broker"""
        print("\n🏦 ¿De qué broker es tu archivo?")
        print("1. Cocos Capital")
        print("2. Bull Market")
        print("3. Otro broker (formato estándar)")
        
        choice = input("Elige opción (1-3): ").strip()
        
        if choice == "1":
            print("✅ Cocos Capital seleccionado")
            return "cocos"
        elif choice == "2":
            print("✅ Bull Market seleccionado")
            return "bull_market"
        elif choice == "3":
            print("✅ Formato estándar seleccionado")
            return "standard"
        else:
            print("❌ Opción inválida")
            return None
