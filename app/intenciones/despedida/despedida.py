import random

DESPEDIDAS = [
    "Gracias por visitarnos 😊",
    "Hasta luego, que tengas un excelente día.",
    "Fue un placer ayudarte 👋",
    "Hasta pronto 😊",
    "Vuelve cuando necesites algo.",
]

def responder_despedida() -> dict:
    return {"tipo": "texto", "contenido": random.choice(DESPEDIDAS)}