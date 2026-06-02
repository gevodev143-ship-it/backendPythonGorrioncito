from app.config.supabase import supabase
from app.services.helpers import (
    extraer_palabras_clave,
    normalizar_query,
    respuesta_texto,
    formatear_productos,
)

def buscar_productos_por_categoria(mensaje: str) -> dict:
    palabras_clave = extraer_palabras_clave(mensaje)

    if not palabras_clave:
        return respuesta_texto("No entendí qué categoría buscas. ¿Puedes describirla mejor?")

    categorias = supabase.table("categoria").select("ctgraid, ctgranombre").execute().data or []

    if not categorias:
        return respuesta_texto("No hay categorías registradas.")

    def puntaje_categoria(nombre: str) -> int:
        n      = nombre.lower()
        n_norm = normalizar_query(n)
        score  = 0
        for palabra in palabras_clave:
            p_norm = normalizar_query(palabra)
            p_orig = palabra.lower()
            if n_norm == p_norm:                                    score += 100
            elif n_norm.startswith(p_norm) or n.startswith(p_orig): score += 85
            elif p_norm in n_norm:                                   score += 70
            elif p_orig in n:                                        score += 60
            elif n_norm in p_norm and len(n_norm) >= 4:              score += 40
            elif len(p_norm) >= 4 and len(n_norm) >= 4:
                for i in range(min(len(p_norm), len(n_norm)), 3, -1):
                    if p_norm[:i] == n_norm[:i]:
                        score += i * 5
                        break
        return score

    categoria_encontrada, mejor_puntaje = max(
        ((cat, puntaje_categoria(cat["ctgranombre"])) for cat in categorias),
        key=lambda x: x[1],
    )

    if mejor_puntaje < 40:
        return respuesta_texto(
            "No encontramos una categoría relacionada. "
            "Prueba con términos como 'herramientas', 'pinturas', 'acabados'."
        )

    productos = (
        supabase.table("producto")
        .select("prdcid, prdcnombre, prdcimgnombrebucket")
        .eq("ctgraid", categoria_encontrada["ctgraid"])
        .execute()
        .data or []
    )

    if not productos:
        return respuesta_texto(
            f"No hay productos registrados en la categoría {categoria_encontrada['ctgranombre']}."
        )

    return {
        "tipo":      "productos",
        "mensaje":   f"Sí 👍 tenemos {categoria_encontrada['ctgranombre']} disponibles. Te muestro las opciones que tenemos para ti:",
        "contenido": formatear_productos(productos),
    }