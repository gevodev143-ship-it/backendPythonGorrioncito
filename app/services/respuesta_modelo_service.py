from app.services.helpers import respuesta_texto

from app.intenciones.saludo.saludo                                                             import responder_saludo
from app.intenciones.despedida.despedida                                                       import responder_despedida
from app.intenciones.buscar_producto.buscar_producto                                           import buscar_producto
from app.intenciones.buscar_productos_por_categoria.buscar_productos_por_categoria             import buscar_productos_por_categoria
from app.intenciones.ver_catalogo.ver_catalogo                                                 import responder_ver_catalogo
from app.intenciones.buscar_producto_por_precio.buscar_producto_por_precio                     import buscar_producto_por_precio

def generar_respuesta(intencion: str, mensaje: str) -> dict:

    if intencion == "saludo":
        return responder_saludo()

    if intencion == "despedida":
        return responder_despedida()

    if intencion == "buscar_producto":
        return buscar_producto(mensaje)

    if intencion == "buscar_productos_por_categoria":
        return buscar_productos_por_categoria(mensaje)

    if intencion == "ver_catalogo":
        return responder_ver_catalogo()

    if intencion == "buscar_producto_por_precio":
        return buscar_producto_por_precio(mensaje)

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