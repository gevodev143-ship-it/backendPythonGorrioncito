import random

SALUDOS = [
    "Hola 😊 ¿En qué puedo ayudarte hoy?",
    "¡Bienvenido! ¿Qué estás buscando?",
    "Hola, dime cómo puedo ayudarte 👋",
    "¡Hola! Estoy listo para ayudarte con productos o consultas.",
    "Bienvenido 😊 ¿Buscas algún producto en especial?",
    "Hola 👋 ¿Qué necesitas hoy?",
    "Hola, cuéntame qué estás buscando 🔎",
    "¡Bienvenido! Estoy aquí para ayudarte a encontrar productos.",
    "Hola 😊 ¿Deseas ver productos, categorías o precios?",
]

def responder_saludo() -> dict:
    return {"tipo": "texto", "contenido": random.choice(SALUDOS)}