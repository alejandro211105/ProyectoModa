import sqlite3

def añadir_capas():
    conn = sqlite3.connect('armario.db')
    cursor = conn.cursor()
    
    # Añadimos la columna capa si no existe
    try:
        cursor.execute("ALTER TABLE prendas ADD COLUMN capa INTEGER DEFAULT 1")
    except: pass

    # Asignamos capas lógicas según el tipo de prenda
    # Capa 1: Torso base
    cursor.execute("UPDATE prendas SET capa = 1 WHERE tipo IN ('Camiseta', 'Camisa', 'Top')")
    # Capa 2: Parte inferior
    cursor.execute("UPDATE prendas SET capa = 2 WHERE tipo IN ('Pantalón', 'Vaquero', 'Falda')")
    # Capa 3: Exterior
    cursor.execute("UPDATE prendas SET capa = 3 WHERE tipo IN ('Chaqueta', 'Abrigo', 'Sudadera')")
    
    conn.commit()
    conn.close()
    print("Capas de profundidad configuradas con éxito.")

if __name__ == "__main__":
    añadir_capas()