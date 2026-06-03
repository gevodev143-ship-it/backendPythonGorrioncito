import numpy as np
import pandas as pd
import joblib
import json
import logging
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay
import matplotlib.pyplot as plt
from config.supabase import supabase
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
log = logging.getLogger(__name__)

# ─── 1. Carga y análisis exploratorio con Pandas ─────────────────────────────
log.info("Cargando datos de Supabase...")
res = supabase.table("mensaje_cliente") \
    .select("mensajecliente, intencion(intencionnombre)") \
    .eq("aprobado_entrenamiento", True) \
    .not_.is_("intencionid", "null") \
    .execute()

df = pd.DataFrame([
    {"texto": d["mensajecliente"], "intencion": d["intencion"]["intencionnombre"]}
    for d in res.data if d.get("mensajecliente")
])

log.info(f"Total muestras: {len(df)}")
log.info(f"Distribución de clases:\n{df['intencion'].value_counts()}")

# Alerta de desbalanceo
min_clase = df['intencion'].value_counts().min()
if min_clase < 10:
    log.warning(f"Clase minoritaria con solo {min_clase} muestras — riesgo de sobreajuste")

X, y = df["texto"].values, df["intencion"].values

# ─── 2. Split estratificado ──────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ─── 3. Definir y comparar múltiples modelos ─────────────────────────────────
modelos = {
    "Naive Bayes":     MultinomialNB(alpha=0.5),
    "Random Forest":   RandomForestClassifier(n_estimators=100, random_state=42),
    "KNN":             KNeighborsClassifier(n_neighbors=5),
    "Árbol (ID3)":     DecisionTreeClassifier(criterion="entropy", random_state=42),
}

resultados = {}
for nombre, clf in modelos.items():
    pipe = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1,2), min_df=2,
                                               strip_accents="unicode", lowercase=True,
                                               max_features=5000, sublinear_tf=True)),
                     ("modelo", clf)])
    cv_scores = cross_val_score(pipe, X_train, y_train, cv=5, scoring="f1_weighted")
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    resultados[nombre] = {
        "pipeline": pipe,
        "cv_f1_mean": cv_scores.mean(),
        "cv_f1_std":  cv_scores.std(),
        "report":     classification_report(y_test, y_pred, output_dict=True),
    }
    log.info(f"{nombre}: CV F1 = {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

# ─── 4. Seleccionar mejor modelo y guardar con metadata ──────────────────────
mejor_nombre = max(resultados, key=lambda k: resultados[k]["cv_f1_mean"])
mejor_pipeline = resultados[mejor_nombre]["pipeline"]
mejor_f1 = resultados[mejor_nombre]["cv_f1_mean"]

log.info(f"Mejor modelo: {mejor_nombre} (F1={mejor_f1:.3f})")

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "modelo.joblib")
joblib.dump(mejor_pipeline, OUTPUT_PATH)

metadata = {
    "modelo": mejor_nombre,
    "f1_score_cv": round(mejor_f1, 4),
    "clases": list(mejor_pipeline.classes_),
    "n_train": len(X_train),
    "n_test":  len(X_test),
    "fecha":   datetime.now().isoformat(),
    "comparativa": {k: round(v["cv_f1_mean"], 4) for k, v in resultados.items()}
}
with open(OUTPUT_PATH.replace(".joblib", "_metadata.json"), "w") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

# ─── 4b. Exportar CSV con datos de entrenamiento ─────────────────────────────
log.info("Exportando datos de entrenamiento a CSV...")

# Predicciones y confianzas sobre el set de test
y_pred_test = mejor_pipeline.predict(X_test)
probs_test   = mejor_pipeline.predict_proba(X_test)
confianzas_test = np.round(probs_test.max(axis=1) * 100, 2)

df_test = pd.DataFrame({
    "texto":             X_test,
    "intencion_real":    y_test,
    "intencion_pred":    y_pred_test,
    "confianza_%":       confianzas_test,
    "correcto":          y_test == y_pred_test,
    "split":             "test",
})

# Predicciones sobre el set de train
y_pred_train = mejor_pipeline.predict(X_train)
probs_train  = mejor_pipeline.predict_proba(X_train)
confianzas_train = np.round(probs_train.max(axis=1) * 100, 2)

df_train = pd.DataFrame({
    "texto":             X_train,
    "intencion_real":    y_train,
    "intencion_pred":    y_pred_train,
    "confianza_%":       confianzas_train,
    "correcto":          y_train == y_pred_train,
    "split":             "train",
})

df_export = pd.concat([df_train, df_test], ignore_index=True)

CSV_PATH = OUTPUT_PATH.replace(".joblib", "_entrenamiento.csv")
df_export.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
log.info(f"CSV exportado: {CSV_PATH} ({len(df_export)} filas)")
# ─── 5. Métricas y visualizaciones ───────────────────────────────────────────
print(classification_report(y_test, mejor_pipeline.predict(X_test)))

# Matriz de confusión
fig, ax = plt.subplots(figsize=(8, 6))
ConfusionMatrixDisplay.from_estimator(mejor_pipeline, X_test, y_test, ax=ax,
                                       xticks_rotation=45, colorbar=False)
ax.set_title(f"Matriz de confusión — {mejor_nombre}")
plt.tight_layout()
plt.savefig("confusion_matrix.png", dpi=150)

# Batch update a Supabase (eficiente)
todos = supabase.table("mensaje_cliente").select("mensaje_cliente_id, mensajecliente").execute().data
textos_todos = [r["mensajecliente"] for r in todos]
probs_todas  = mejor_pipeline.predict_proba(textos_todos)  # batch, no loop
confianzas   = np.round(probs_todas.max(axis=1) * 100, 2)

for registro, confianza in zip(todos, confianzas):
    supabase.table("mensaje_cliente") \
        .update({"porcentaje_confianza": float(confianza)}) \
        .eq("mensaje_cliente_id", registro["mensaje_cliente_id"]) \
        .execute()