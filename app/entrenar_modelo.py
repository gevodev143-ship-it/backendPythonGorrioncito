from config.supabase import supabase
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import pickle
import os

# ─── 1. Obtener datos de entrenamiento (solo aprobados) ───────────────────────
print("📦 Obteniendo datos de Supabase...")

res = supabase.table("mensaje_cliente") \
    .select("mensajecliente, intencionid, intencion(intencionnombre)") \
    .not_.is_("intencionid", "null") \
    .eq("aprobado_entrenamiento", True) \
    .execute()

datos = res.data

if not datos:
    print("❌ No hay datos de entrenamiento aprobados en la BD.")
    exit()

# ─── 2. Preparar X e y ────────────────────────────────────────────────────────
textos      = [d["mensajecliente"] for d in datos]
intenciones = [d["intencion"]["intencionnombre"] for d in datos]

print(f"✅ {len(textos)} mensajes aprobados cargados.")
print(f"📌 Intenciones únicas: {set(intenciones)}\n")

# ─── 3. Construir y entrenar el pipeline ──────────────────────────────────────
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        strip_accents="unicode",
        lowercase=True,
    )),
    ("modelo", MultinomialNB(alpha=0.5)),
])

pipeline.fit(textos, intenciones)
print("🧠 Modelo entrenado correctamente.")

# ─── 4. Guardar como modelo.pkl ───────────────────────────────────────────────
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "modelo.pkl")
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

with open(OUTPUT_PATH, "wb") as f:
    pickle.dump(pipeline, f)

print(f"💾 Modelo guardado en: {OUTPUT_PATH}")

# ─── 5. Probar el modelo en TODOS los mensajes y actualizar porcentaje_confianza
print("\n🔄 Actualizando porcentaje_confianza en todos los mensajes...")

todos_res = supabase.table("mensaje_cliente") \
    .select("mensaje_cliente_id, mensajecliente") \
    .execute()

todos = todos_res.data

if not todos:
    print("⚠️  No hay mensajes para evaluar.")
else:
    actualizados = 0
    errores      = 0

    for registro in todos:
        mensaje_id = registro["mensaje_cliente_id"]
        texto      = registro["mensajecliente"]

        try:
            probs      = pipeline.predict_proba([texto])[0]
            idx        = probs.argmax()
            porcentaje = round(float(probs[idx]) * 100, 2)

            result = supabase.table("mensaje_cliente") \
                .update({"porcentaje_confianza": porcentaje}) \
                .eq("mensaje_cliente_id", mensaje_id) \
                .execute()

            actualizados += 1

        except Exception as e:
            print(f"  ⚠️  Error en mensaje {mensaje_id}: {e}")
            errores += 1

    print(f"✅ {actualizados} mensajes actualizados.")
    if errores:
        print(f"❌ {errores} mensajes con error.")

# ─── 6. Prueba rápida con los primeros 3 mensajes aprobados ───────────────────
print("\n🔍 Prueba rápida (mensajes aprobados):")
for ej in textos[:3]:
    probs  = pipeline.predict_proba([ej])[0]
    clases = pipeline.classes_
    idx    = probs.argmax()
    print(f"  Mensaje  : {ej}")
    print(f"  Intención: {clases[idx]} ({round(probs[idx] * 100, 2)}%)\n")