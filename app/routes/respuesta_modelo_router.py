import os
import pickle

from fastapi import APIRouter
from pydantic import BaseModel

from app.config.supabase import supabase
from app.services.respuesta_modelo_service import generar_respuesta

router = APIRouter()

# ─── Cargar modelo ────────────────────────────────────────────────────────────

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "modelo.pkl")

modelo     = None
vectorizer = None

try:
    with open(MODEL_PATH, "rb") as f:
        data = pickle.load(f)
        if isinstance(data, dict):
            modelo     = data.get("modelo")
            vectorizer = data.get("vectorizer")
        else:
            modelo = data
except FileNotFoundError:
    print("⚠️  modelo.pkl no encontrado")

# ─── Schema ───────────────────────────────────────────────────────────────────

class MensajeRequest(BaseModel):
    historial_chat_id: int
    mensajecliente:    str

# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/modelo/detectar")
async def detectar_intencion(req: MensajeRequest):
    try:
        texto = req.mensajecliente.strip()

        # Guardar mensaje cliente
        insert_res = (
            supabase.table("mensaje_cliente")
            .insert({
                "historial_chat_id":   req.historial_chat_id,
                "mensajecliente":      texto,
                "respuesta_chatbot":   False,
                "porcentaje_confianza": None,
            })
            .execute()
        )

        if not insert_res.data:
            return {"respuesta": {"tipo": "texto", "contenido": "Error al guardar el mensaje."}}

        mensaje_cliente_id = insert_res.data[0]["mensaje_cliente_id"]

        if modelo is None:
            return {"respuesta": {"tipo": "texto", "contenido": "Chat en mantenimiento, por favor espere..."}}

        # Predicción
        X          = vectorizer.transform([texto]) if vectorizer else [texto]
        probs      = modelo.predict_proba(X)[0]
        idx_max    = probs.argmax()
        intencion  = str(modelo.classes_[idx_max])
        porcentaje = round(float(probs[idx_max]) * 100, 2)

        # Obtener intencionid
        intencion_res = (
            supabase.table("intencion")
            .select("intencionid")
            .eq("intencionnombre", intencion)
            .single()
            .execute()
        )
        intencion_id = intencion_res.data["intencionid"] if intencion_res.data else None

        # ── Generar respuesta → va a service → va a intenciones/ ──
        respuesta_chatbot = generar_respuesta(intencion=intencion, mensaje=texto)

        # Actualizar mensaje con resultado
        (
            supabase.table("mensaje_cliente")
            .update({
                "respuesta_chatbot":   True,
                "porcentaje_confianza": porcentaje,
                "intencionid":         intencion_id,
            })
            .eq("mensaje_cliente_id", mensaje_cliente_id)
            .execute()
        )

        return {
            "intencion":           intencion,
            "porcentaje_confianza": porcentaje,
            "respuesta":           respuesta_chatbot,  # ← esto llega al frontend
        }

    except Exception as e:
        return {"respuesta": {"tipo": "texto", "contenido": f"Error: {str(e)}"}}