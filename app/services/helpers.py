import re

SUPABASE_URL    = "https://iohltonvumgllknokthn.supabase.co"
BUCKET_PRODUCTO = "imagenes/producto"

STOPWORDS = {
    "tiene", "tienen", "hay", "busco", "quiero", "necesito",
    "me", "un", "una", "unos", "unas", "el", "la", "los", "las",
    "de", "del", "para", "por", "con", "si", "que", "es", "en",
    "algún", "alguna", "algunos", "ver", "mostrar", "dame", "tienes",
}

def url_imagen(bucket: str, nombre: str) -> str:
    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{nombre}"

def normalizar_query(texto: str) -> str:
    texto = re.sub(r"[^\w\s]", "", texto.lower()).strip()
    texto = re.sub(r"es\b", "", texto)
    texto = re.sub(r"s\b",  "", texto)
    return texto.strip()

def extraer_palabras_clave(mensaje: str) -> list[str]:
    limpio = re.sub(r"[^\w\s]", "", mensaje.lower()).strip()
    return [p for p in limpio.split() if p not in STOPWORDS and len(p) > 2]

def respuesta_texto(contenido: str) -> dict:
    return {"tipo": "texto", "contenido": contenido}

def formatear_productos(productos: list[dict]) -> list[dict]:
    return [
        {
            "id":     p["prdcid"],
            "nombre": p["prdcnombre"],
            "imagen": url_imagen(BUCKET_PRODUCTO, p["prdcimgnombrebucket"])
                      if p.get("prdcimgnombrebucket") else "",
        }
        for p in productos
    ]