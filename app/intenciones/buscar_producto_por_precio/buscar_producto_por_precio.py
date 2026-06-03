from app.config.supabase import supabase
from app.services.helpers import (
    extraer_palabras_clave,
    normalizar_query,
    respuesta_texto,
    formatear_productos,
)

def buscar_producto_por_precio(mensaje: str) -> dict:
    palabras_clave = extraer_palabras_clave(mensaje)

    if not palabras_clave:
        return respuesta_texto("No entendí qué producto buscas. ¿Puedes describirlo mejor?")

    palabras_norm = [normalizar_query(p) for p in palabras_clave]

    query = supabase.table("producto").select("prdcid, prdcnombre, prdcimgnombrebucket, prdcprecio")
    for palabra in palabras_norm:
        query = query.ilike("prdcnombre", f"%{palabra}%")

    productos = query.execute().data or []

    if not productos and len(palabras_norm) > 1:
        vistos: set[int] = set()
        for palabra in palabras_norm:
            res = (
                supabase.table("producto")
                .select("prdcid, prdcnombre, prdcimgnombrebucket, prdcprecio")
                .ilike("prdcnombre", f"%{palabra}%")
                .execute()
            )
            for p in (res.data or []):
                if p["prdcid"] not in vistos:
                    vistos.add(p["prdcid"])
                    productos.append(p)

    if not productos:
        return respuesta_texto("No encontramos productos relacionados a tu búsqueda.")

    # ── Mensaje según cantidad de resultados ─────────────────
    if len(productos) == 1:
        p = productos[0]
        precio = p.get("prdcprecio")
        nombre = p["prdcnombre"]
        if precio is not None:
            mensaje_resp = (
                f"Aquí tienes el precio del producto {nombre} "
                f"con un precio de S/{precio:.2f} 😊"
            )
        else:
            mensaje_resp = (
                f"Encontré el producto {nombre}, "
                f"pero aún no tiene precio registrado. ¡Consúltanos directamente!"
            )
    else:
        termino = palabras_clave[0].capitalize()
        mensaje_resp = (
            f"Aquí tengo los precios de los productos😊 "
            f"¡Elige el que más te convenga!"
        )

    return {
        "tipo":      "productos",
        "mensaje":   mensaje_resp,
        "contenido": formatear_productos(productos),
    }