from app.config.supabase import supabase
from app.services.helpers import (
    extraer_palabras_clave,
    normalizar_query,
    respuesta_texto,
    formatear_productos,
)

def buscar_producto(mensaje: str) -> dict:
    palabras_clave = extraer_palabras_clave(mensaje)

    if not palabras_clave:
        return respuesta_texto("No entendí qué producto buscas. ¿Puedes describirlo mejor?")

    palabras_norm = [normalizar_query(p) for p in palabras_clave]

    query = supabase.table("producto").select("prdcid, prdcnombre, prdcimgnombrebucket")
    for palabra in palabras_norm:
        query = query.ilike("prdcnombre", f"%{palabra}%")

    productos = query.execute().data or []

    if not productos and len(palabras_norm) > 1:
        vistos: set[int] = set()
        for palabra in palabras_norm:
            res = (
                supabase.table("producto")
                .select("prdcid, prdcnombre, prdcimgnombrebucket")
                .ilike("prdcnombre", f"%{palabra}%")
                .execute()
            )
            for p in (res.data or []):
                if p["prdcid"] not in vistos:
                    vistos.add(p["prdcid"])
                    productos.append(p)

    if not productos:
        return respuesta_texto("No encontramos productos relacionados a tu búsqueda.")

    termino = palabras_clave[0].capitalize()

    return {
        "tipo":      "productos",
        "mensaje":   f"Sí 👍 tenemos {termino} disponibles. Te muestro las opciones que tenemos para ti:",
        "contenido": formatear_productos(productos),
    }