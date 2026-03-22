import requests

# La dirección local de tu propio ordenador
url = "http://127.0.0.1:8000/subir-ropa"

# Ruta de una imagen que tengas en tu PC (cambia 'foto_prueba.jpg' por una real)
ruta_imagen = "foto_prueba.jpg" 

try:
    with open(ruta_imagen, "rb") as f:
        # Enviamos la foto como si fuéramos el móvil
        archivos = {"file": f}
        respuesta = requests.post(url, files=archivos)
        
    print("Estado:", respuesta.status_code)
    print("Respuesta del servidor:", respuesta.json())
except FileNotFoundError:
    print(f"Error: No encontré el archivo {ruta_imagen}. Pon una foto en la carpeta.")