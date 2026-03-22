from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO
from PIL import Image
import uvicorn
import os
import collections
import sqlite3
import random

app = FastAPI()

# --- CONFIGURACIÓN DE DIRECTORIOS Y LOGS ---
# Esto elimina los códigos de colores [32m de la terminal
log_config = uvicorn.config.LOGGING_CONFIG
log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"

modelo = YOLO("yolov8n.pt") 
CARPETA_RAIZ_ARMARIOS = "armarios_usuarios"

if not os.path.exists(CARPETA_RAIZ_ARMARIOS):
    os.makedirs(CARPETA_RAIZ_ARMARIOS)

# Servimos la carpeta de armarios para que las imágenes sean accesibles
app.mount("/imagenes", StaticFiles(directory=CARPETA_RAIZ_ARMARIOS), name="imagenes")

def conectar_db():
    return sqlite3.connect('armario.db')

# --- FUNCIONES DE APOYO ---

def detectar_color(ruta_imagen):
    img = Image.open(ruta_imagen).convert('RGB')
    img = img.resize((100, 100))
    ancho, alto = img.size
    cuadro_central = img.crop((ancho//4, alto//4, 3*ancho//4, 3*alto//4))
    datos = list(cuadro_central.getdata())
    r, g, b = collections.Counter(datos).most_common(1)[0][0]
    
    if r > 200 and g > 200 and b > 200: return "Blanco"
    if r < 75 and g < 75 and b < 75: return "Negro"
    if b > r and b > g: return "Azul"
    if r > g and r > b: return "Rojo"
    if abs(r - g) < 20 and r > 150: return "Beige/Amarillo"
    return "Gris/Variado"

def guardar_en_db(archivo, tipo, color, estilo, capa, usuario_id):
    conn = conectar_db()
    cursor = conn.cursor()
    query = """
        INSERT INTO prendas (nombre_archivo, tipo, color, estilo, capa, usuario_id, me_gusta) 
        VALUES (?, ?, ?, ?, ?, ?, 0)
    """
    cursor.execute(query, (archivo, tipo, color, estilo, capa, usuario_id))
    conn.commit()
    conn.close()

# --- ENDPOINTS DE USUARIOS (Login / Registro) ---

@app.post("/registro")
async def registro(usuario: str = Form(...), password: str = Form(...)):
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO usuarios (nombre, password) VALUES (?, ?)", (usuario, password))
        conn.commit()
        # Crear carpeta física para el usuario
        os.makedirs(os.path.join(CARPETA_RAIZ_ARMARIOS, usuario), exist_ok=True)
        print(f"INFO: Nuevo usuario registrado: {usuario}")
        return {"status": "ok"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    finally:
        conn.close()

@app.post("/login")
async def login(usuario: str = Form(...), password: str = Form(...)):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre FROM usuarios WHERE nombre = ? AND password = ?", (usuario, password))
    user = cursor.fetchone()
    conn.close()
    if user:
        print(f"INFO: Sesión iniciada: {usuario}")
        return {"id": user[0], "nombre": user[1]}
    raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

# --- RUTAS DE PRENDAS ---

@app.get("/")
def estado():
    return FileResponse("index.html")

@app.post("/analizar-prenda")
async def analizar_prenda(file: UploadFile = File(...), username: str = Form(...)):
    contenido = await file.read()
    nombre_orig = file.filename
    nombre_base = os.path.splitext(nombre_orig)[0]
    nombre_temp = f"temp_{nombre_base}.jpg" 
    
    # Guardamos en la carpeta específica del usuario
    ruta_usuario = os.path.join(CARPETA_RAIZ_ARMARIOS, username)
    os.makedirs(ruta_usuario, exist_ok=True)
    ruta_temp = os.path.join(ruta_usuario, nombre_temp)
    
    with open(ruta_temp, "wb") as f:
        f.write(contenido)

    resultados = modelo(ruta_temp, conf=0.15)
    prendas_ia = [modelo.names[int(c)] for r in resultados for c in r.boxes.cls]
    
    traduccion = {
        "shirt": "Camiseta", "pants": "Pantalón", "jeans": "Vaquero", 
        "jacket": "Chaqueta", "sweatshirt": "Sudadera", "skirt": "Falda",
        "shoes": "Calzado", "sneakers": "Calzado"
    }
    
    tipo_ia = prendas_ia[0] if prendas_ia else "shirt"
    tipo_detectado = traduccion.get(tipo_ia, "Sudadera")
    color_detectado = detectar_color(ruta_temp)

    return JSONResponse(content={
        "archivo_temp": nombre_temp,
        "tipo_ia": tipo_detectado,
        "color_ia": color_detectado
    })

@app.post("/confirmar-guardado")
async def confirmar_guardado(datos: dict):
    archivo_temp = datos.get('archivo')
    tipo_usuario = datos.get('tipo')
    color_usuario = datos.get('color')
    estilo_usuario = datos.get('estilo')
    user_id = datos.get('user_id')
    username = datos.get('username')

    ruta_usuario = os.path.join(CARPETA_RAIZ_ARMARIOS, username)
    ruta_temp = os.path.join(ruta_usuario, archivo_temp)
    
    # IA de respaldo si el usuario no eligió nada
    if not tipo_usuario or not color_usuario:
        resultados = modelo(ruta_temp, conf=0.15)
        prendas_ia = [modelo.names[int(c)] for r in resultados for c in r.boxes.cls]
        if not tipo_usuario:
            traduccion = {"shirt": "Camiseta", "pants": "Pantalón", "jeans": "Vaquero"}
            tipo_usuario = traduccion.get(prendas_ia[0] if prendas_ia else "shirt", "Camiseta")
        if not color_usuario:
            color_usuario = detectar_color(ruta_temp)

    estilo_final = estilo_usuario if estilo_usuario else "Casual"
    nombre_final = archivo_temp.replace("temp_", "")
    ruta_final = os.path.join(ruta_usuario, nombre_final)
    
    if os.path.exists(ruta_temp):
        if os.path.exists(ruta_final): os.remove(ruta_final)
        os.rename(ruta_temp, ruta_final)

    capa = 1
    if tipo_usuario in ['Chaqueta', 'Abrigo', 'Sudadera']: capa = 3
    elif tipo_usuario in ['Pantalón', 'Vaquero', 'Falda']: capa = 2
    
    guardar_en_db(nombre_final, tipo_usuario, color_usuario, estilo_final, capa, user_id)
    print(f"INFO: Prenda guardada para {username}: {tipo_usuario}")
    
    return {"status": "ok"}

@app.get("/ver-armario/{user_id}")
def ver_armario(user_id: int):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre_archivo, tipo, color FROM prendas WHERE usuario_id = ?", (user_id,))
    filas = cursor.fetchall()
    conn.close()
    return {"armario": [{"id": f[0], "archivo": f[1], "tipo": f[2], "color": f[3]} for f in filas]}

if __name__ == "__main__":
    # Ejecutamos con log_config personalizado para limpiar la consola
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log_config)