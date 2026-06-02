from app.services.helpers import respuesta_texto

from app.intenciones.saludo.saludo                                                 import responder_saludo
from app.intenciones.despedida.despedida                                           import responder_despedida
from app.intenciones.buscar_producto.buscar_producto                               import buscar_producto
from app.intenciones.buscar_productos_por_categoria.buscar_productos_por_categoria import buscar_productos_por_categoria

def generar_respuesta(intencion: str, mensaje: str) -> dict:

    if intencion == "saludo":
        return responder_saludo()

    if intencion == "despedida":
        return responder_despedida()

    if intencion == "buscar_producto":
        return buscar_producto(mensaje)

    if intencion == "bucar_productos_por_categoria":
        return buscar_productos_por_categoria(mensaje)

    # Fallback
    resultado_cat = buscar_productos_por_categoria(mensaje)
    if resultado_cat.get("tipo") == "productos":
        return resultado_cat

    resultado_prod = buscar_producto(mensaje)
    if resultado_prod.get("tipo") == "productos":
        return resultado_prod

    return respuesta_texto(
        "No encontré productos ni categorías relacionadas. "
        "Intenta con otro término, por ejemplo: 'martillo', 'pinturas', 'herramientas'."
    )