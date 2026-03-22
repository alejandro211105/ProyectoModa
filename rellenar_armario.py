import sqlite3
import random

def rellenar():
    conn = sqlite3.connect('armario.db')
    cursor = conn.cursor()
    
    # Datos para inventar ropa
    tipos = ["Camiseta", "Pantalón", "Sudadera", "Chaqueta", "Vaquero", "Falda"]
    colores = ["Azul", "Negro", "Blanco", "Rojo", "Gris", "Beige/Amarillo"]
    estilos = ["Casual", "Formal", "Deportivo"]

    print("Cargando 500 prendas nuevas...")
    
    for i in range(500):
        t = random.choice(tipos)
        c = random.choice(colores)
        e = random.choice(estilos)
        archivo = f"deepfashion_{i}.jpg"
        
        # Insertamos los datos de prueba
        cursor.execute("INSERT INTO prendas (nombre_archivo, tipo, color, estilo) VALUES (?, ?, ?, ?)", 
                       (archivo, t, c, e))
    
    conn.commit() # ¡ESTO ES LO MÁS IMPORTANTE PARA QUE SE GUARDE!
    conn.close()
    print("¡Listo! 500 prendas añadidas correctamente.")

if __name__ == "__main__":
    rellenar()