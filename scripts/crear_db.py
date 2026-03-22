import sqlite3
import os

def inicializar_db():
    # Opcional: Si quieres empezar de cero y evitar errores de columnas faltantes
    # puedes descomentar la siguiente línea para borrar la DB vieja automáticamente:
    # if os.path.exists('armario.db'): os.remove('armario.db')

    conn = sqlite3.connect('armario.db')
    cursor = conn.cursor()
    
    # 1. Creamos la tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            password TEXT
        )
    ''')
    
    # 2. Creamos la tabla de prendas con todas las columnas necesarias
    # Añadimos 'estilo', 'capa' y la relación 'usuario_id'
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_archivo TEXT,
            tipo TEXT,
            color TEXT,
            estilo TEXT,
            capa INTEGER,
            usuario_id INTEGER,
            me_gusta INTEGER DEFAULT 0,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Base de datos 'armario.db' actualizada correctamente.")
    print("✨ Tablas creadas: 'usuarios' y 'prendas' (con soporte para multiusuario).")

if __name__ == "__main__":
    inicializar_db()