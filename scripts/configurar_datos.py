import sqlite3
import random

def actualizar_estructura():
    conn = sqlite3.connect('armario.db')
    cursor = conn.cursor()
    # Añadimos la columna 'estilo' para que la IA sea más lista
    try:
        cursor.execute("ALTER TABLE prendas ADD COLUMN estilo TEXT DEFAULT 'Casual'")
    except: pass 
    
    # Creamos la tabla donde la IA aprenderá a combinar
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conjuntos_maestros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            color_top TEXT,
            color_bottom TEXT,
            estilo TEXT
        )
    ''')
    conn.commit()
    conn.close()

def cargar_datos_aprendizaje():
    conn = sqlite3.connect('armario.db')
    cursor = conn.cursor()
    
    # ... (aquí va todo el código de los bucles que generan las 500 prendas) ...
    # (incluyendo los tipos, colores y estilos que definimos antes)
    
    conn.commit()
    conn.close()
    print("¡Base de datos alimentada con éxito!")

# --- ESTO ES LO QUE HACE QUE SE EJECUTE ---
if __name__ == "__main__":
    actualizar_estructura()
    cargar_datos_aprendizaje()