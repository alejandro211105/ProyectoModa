from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from PIL import Image, UnidentifiedImageError
import uvicorn
import os
import collections
import sqlite3
import hashlib

app = FastAPI()

# ── CORS ──────────────────────────────────────────────────────────────────────
# Permite peticiones desde cualquier origen en la red local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── LOGS ──────────────────────────────────────────────────────────────────────
log_config = uvicorn.config.LOGGING_CONFIG
log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"

# ── RUTAS BASE ────────────────────────────────────────────────────────────────
DIR_SCRIPTS  = os.path.dirname(os.path.abspath(__file__))
DIR_RAIZ     = os.path.dirname(DIR_SCRIPTS)
DIR_HTML     = os.path.join(DIR_RAIZ, "html")
DIR_DB       = os.path.join(DIR_RAIZ, "bases_datos")
DIR_ARMARIOS = os.path.join(DIR_RAIZ, "armarios_usuarios")
RUTA_DB      = os.path.join(DIR_DB,   "armario.db")
RUTA_MODELO  = os.path.join(DIR_RAIZ, "yolov8n.pt")

# Límite de tamaño de imagen: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024

for carpeta in [DIR_ARMARIOS, DIR_DB]:
    os.makedirs(carpeta, exist_ok=True)

# ── MODELO Y ESTÁTICOS ────────────────────────────────────────────────────────
modelo = YOLO(RUTA_MODELO)
app.mount("/imagenes", StaticFiles(directory=DIR_ARMARIOS), name="imagenes")
app.mount("/html",     StaticFiles(directory=DIR_HTML),     name="html")

# ── BASE DE DATOS ─────────────────────────────────────────────────────────────
def conectar_db():
    conn = sqlite3.connect(RUTA_DB)
    conn.row_factory = sqlite3.Row
    return conn

# ── SEGURIDAD ─────────────────────────────────────────────────────────────────
def hashear_password(password: str) -> str:
    """SHA-256 del password. En producción usar bcrypt."""
    return hashlib.sha256(password.encode()).hexdigest()

def nombre_seguro(nombre: str) -> str:
    """Elimina separadores de ruta para prevenir path traversal."""
    return os.path.basename(nombre)

# ── FUNCIONES DE APOYO ────────────────────────────────────────────────────────
def detectar_color(ruta_imagen: str) -> str:
    try:
        img = Image.open(ruta_imagen).convert('RGB')
        img = img.resize((100, 100))
        ancho, alto = img.size
        cuadro = img.crop((ancho//4, alto//4, 3*ancho//4, 3*alto//4))
        datos  = list(cuadro.getdata())
        r, g, b = collections.Counter(datos).most_common(1)[0][0]

        if r > 200 and g > 200 and b > 200: return "Blanco"
        if r < 75  and g < 75  and b < 75:  return "Negro"
        if b > r   and b > g:               return "Azul"
        if r > g   and r > b:               return "Rojo"
        if abs(r - g) < 20 and r > 150:     return "Beige/Amarillo"
        return "Gris/Variado"
    except (UnidentifiedImageError, Exception) as e:
        print(f"WARN: No se pudo detectar color en {ruta_imagen}: {e}")
        return "Gris/Variado"

def guardar_en_db(archivo, tipo, color, estilo, capa, usuario_id):
    try:
        with conectar_db() as conn:
            conn.execute(
                "INSERT INTO prendas (nombre_archivo, tipo, color, estilo, capa, usuario_id, me_gusta) "
                "VALUES (?, ?, ?, ?, ?, ?, 0)",
                (archivo, tipo, color, estilo, capa, usuario_id)
            )
    except sqlite3.Error as e:
        print(f"ERROR al guardar en BD: {e}")
        raise HTTPException(status_code=500, detail="Error al guardar en la base de datos")

def asignar_capa(tipo: str) -> int:
    """
    Capa 1 = parte superior (camiseta, sudadera, chaqueta…)
    Capa 2 = parte inferior (pantalón, vaquero, falda)
    Capa 3 = calzado
    Coincide con la lógica del frontend.
    """
    if tipo in ['Pantalón', 'Vaquero', 'Falda']:
        return 2
    if tipo in ['Calzado']:
        return 3
    return 1  # Camiseta, Sudadera, Chaqueta, Abrigo, etc.

# ── ENDPOINTS DE USUARIOS ─────────────────────────────────────────────────────
@app.post("/registro")
async def registro(usuario: str = Form(...), password: str = Form(...)):
    usuario  = usuario.strip()
    password = password.strip()

    if not usuario or not password:
        raise HTTPException(status_code=400, detail="Usuario y contraseña no pueden estar vacíos")
    if len(usuario) < 3:
        raise HTTPException(status_code=400, detail="El usuario debe tener al menos 3 caracteres")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    if nombre_seguro(usuario) != usuario:
        raise HTTPException(status_code=400, detail="El nombre de usuario contiene caracteres no permitidos")

    try:
        with conectar_db() as conn:
            conn.execute(
                "INSERT INTO usuarios (nombre, password) VALUES (?, ?)",
                (usuario, hashear_password(password))
            )
        os.makedirs(os.path.join(DIR_ARMARIOS, usuario), exist_ok=True)
        print(f"INFO: Nuevo usuario registrado: {usuario}")
        return {"status": "ok"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="El usuario ya existe")

@app.post("/login")
async def login(usuario: str = Form(...), password: str = Form(...)):
    usuario  = usuario.strip()
    password = password.strip()

    if not usuario or not password:
        raise HTTPException(status_code=400, detail="Rellena todos los campos")

    try:
        with conectar_db() as conn:
            row = conn.execute(
                "SELECT id, nombre FROM usuarios WHERE nombre = ? AND password = ?",
                (usuario, hashear_password(password))
            ).fetchone()
    except sqlite3.Error as e:
        print(f"ERROR en login: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    if row:
        print(f"INFO: Sesión iniciada: {usuario}")
        return {"id": row["id"], "nombre": row["nombre"]}
    raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

# ── RUTAS HTML ────────────────────────────────────────────────────────────────
@app.get("/")
def raiz():
    return FileResponse(os.path.join(DIR_HTML, "index.html"))

@app.get("/app")
def app_principal():
    return FileResponse(os.path.join(DIR_HTML, "stylemate.html"))

# ── ENDPOINTS DE PRENDAS ──────────────────────────────────────────────────────
@app.post("/analizar-prenda")
async def analizar_prenda(file: UploadFile = File(...), username: str = Form(...)):
    # Validaciones
    username = nombre_seguro(username.strip())
    if not username:
        raise HTTPException(status_code=400, detail="Nombre de usuario inválido")

    contenido = await file.read()
    if len(contenido) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="La imagen supera el tamaño máximo de 10 MB")
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    nombre_base = nombre_seguro(os.path.splitext(file.filename)[0])
    nombre_temp = f"temp_{nombre_base}.jpg"

    ruta_usuario = os.path.join(DIR_ARMARIOS, username)
    os.makedirs(ruta_usuario, exist_ok=True)
    ruta_temp = os.path.join(ruta_usuario, nombre_temp)

    with open(ruta_temp, "wb") as f:
        f.write(contenido)

    try:
        resultados = modelo(ruta_temp, conf=0.15)
        prendas_ia = [modelo.names[int(c)] for r in resultados for c in r.boxes.cls]
    except Exception as e:
        print(f"WARN: Error en modelo YOLO: {e}")
        prendas_ia = []

    traduccion = {
        "shirt": "Camiseta", "pants": "Pantalón", "jeans": "Vaquero",
        "jacket": "Chaqueta", "sweatshirt": "Sudadera", "skirt": "Falda",
        "shoes": "Calzado",   "sneakers": "Calzado"
    }

    tipo_ia        = prendas_ia[0] if prendas_ia else "shirt"
    tipo_detectado = traduccion.get(tipo_ia, "Camiseta")
    color_detectado = detectar_color(ruta_temp)

    return JSONResponse(content={
        "archivo_temp": nombre_temp,
        "tipo_ia":      tipo_detectado,
        "color_ia":     color_detectado
    })

@app.post("/confirmar-guardado")
async def confirmar_guardado(datos: dict):
    # Validar campos obligatorios
    archivo_temp   = datos.get('archivo')
    tipo_usuario   = datos.get('tipo')
    color_usuario  = datos.get('color')
    estilo_usuario = datos.get('estilo')
    user_id        = datos.get('user_id')
    username       = datos.get('username')

    if not all([archivo_temp, username, user_id is not None]):
        raise HTTPException(status_code=400, detail="Faltan campos obligatorios (archivo, username, user_id)")

    # Sanitizar para prevenir path traversal
    username     = nombre_seguro(str(username).strip())
    archivo_temp = nombre_seguro(str(archivo_temp).strip())

    if not username or not archivo_temp:
        raise HTTPException(status_code=400, detail="Nombre de archivo o usuario inválido")

    ruta_usuario = os.path.join(DIR_ARMARIOS, username)
    ruta_temp    = os.path.join(ruta_usuario, archivo_temp)

    if not os.path.exists(ruta_temp):
        raise HTTPException(status_code=404, detail="Archivo temporal no encontrado. Sube la imagen de nuevo.")

    # IA de respaldo si el usuario no eligió nada
    if not tipo_usuario or not color_usuario:
        try:
            resultados = modelo(ruta_temp, conf=0.15)
            prendas_ia = [modelo.names[int(c)] for r in resultados for c in r.boxes.cls]
        except Exception:
            prendas_ia = []

        if not tipo_usuario:
            traduccion = {"shirt": "Camiseta", "pants": "Pantalón", "jeans": "Vaquero"}
            tipo_usuario = traduccion.get(prendas_ia[0] if prendas_ia else "shirt", "Camiseta")
        if not color_usuario:
            color_usuario = detectar_color(ruta_temp)

    estilo_final = estilo_usuario if estilo_usuario else "Casual"

    # Quitar el prefijo "temp_" de forma segura (siempre son los primeros 5 caracteres)
    nombre_final = archivo_temp[5:] if archivo_temp.startswith("temp_") else archivo_temp
    ruta_final   = os.path.join(ruta_usuario, nombre_final)

    if os.path.exists(ruta_final):
        os.remove(ruta_final)
    os.rename(ruta_temp, ruta_final)

    capa = asignar_capa(tipo_usuario)
    guardar_en_db(nombre_final, tipo_usuario, color_usuario, estilo_final, capa, user_id)
    print(f"INFO: Prenda guardada para {username}: {tipo_usuario} ({color_usuario}), capa {capa}")

    return {"status": "ok"}

@app.get("/ver-armario/{user_id}")
def ver_armario(user_id: int):
    try:
        with conectar_db() as conn:
            filas = conn.execute(
                "SELECT id, nombre_archivo, tipo, color, capa FROM prendas WHERE usuario_id = ? ORDER BY capa, id",
                (user_id,)
            ).fetchall()
        return {"armario": [dict(f) for f in filas]}
    except sqlite3.Error as e:
        print(f"ERROR al leer armario: {e}")
        raise HTTPException(status_code=500, detail="Error al leer el armario")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log_config)
