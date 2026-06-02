from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import pandas as pd
import io
import math

from app.config.supabase import supabase

router = APIRouter(prefix="/excel", tags=["Excel"])

# ─────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────
CHUNK_SIZE = 500          # filas por batch insert a Supabase
LOG_SEP    = "═" * 60


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _fetch_all_pages(table: str, select: str, page_size: int = 1000) -> list[dict]:
    """
    Descarga TODAS las filas de una tabla usando paginación.
    Supabase limita por defecto a 1 000 filas por request.
    """
    rows, offset = [], 0
    while True:
        res = (
            supabase.table(table)
            .select(select)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows


def _bulk_upsert_names(
    table: str,
    name_col: str,         # columna del nombre  (ej. "marcanombre")
    id_col: str,           # columna del id      (ej. "marcaid")
    names_needed: set[str],
) -> dict[str, int]:
    """
    1. Descarga el catálogo existente en 1 sola request (paginada).
    2. Determina cuáles nombres son nuevos.
    3. Inserta los nuevos en un solo batch.
    4. Devuelve dict  nombre → id  con toda la tabla.
    """
    # -- prefetch completo ------------------------------------------------
    existing_rows = _fetch_all_pages(table, f"{id_col},{name_col}")
    name_to_id: dict[str, int] = {
        r[name_col]: r[id_col] for r in existing_rows
    }

    # -- calcular nuevos --------------------------------------------------
    # Sanear el set entrante: descartar NaN/None/cadenas vacías/no-string
    names_needed = {
        n for n in names_needed
        if isinstance(n, str) and n.strip() not in ("", "nan", "none", "NaN")
    }
    new_names = names_needed - name_to_id.keys()

    if new_names:
        payload = [{name_col: n} for n in sorted(new_names, key=str)]

        # batch insert en chunks de CHUNK_SIZE
        for i in range(0, len(payload), CHUNK_SIZE):
            chunk = payload[i : i + CHUNK_SIZE]
            ins = supabase.table(table).insert(chunk).execute()
            for r in ins.data or []:
                name_to_id[r[name_col]] = r[id_col]

        print(f"   ➕ {len(new_names)} nuevos registros insertados en '{table}'")

    print(f"   📖 Catálogo '{table}' listo → {len(name_to_id)} entradas")
    return name_to_id


def _chunked_insert_products(
    records: list[dict],
) -> tuple[int, list[dict]]:
    """
    Inserta productos en batches.
    Devuelve (insertados, errores).
    """
    insertados = 0
    errores: list[dict] = []

    for i in range(0, len(records), CHUNK_SIZE):
        chunk = records[i : i + CHUNK_SIZE]
        try:
            res = supabase.table("producto").insert(chunk).execute()
            insertados += len(res.data or [])
        except Exception as exc:
            # Si falla el batch completo, registrar cada fila como error
            print(f"   ⚠️  Error en batch productos [{i}:{i+len(chunk)}]: {exc}")
            for row in chunk:
                errores.append({**row, "_motivo": f"error batch: {exc}"})

    return insertados, errores


# ─────────────────────────────────────────────────────────────
# ENDPOINT
# ─────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_excel(file: UploadFile = File(...)):

    print(f"\n{LOG_SEP}")
    print(f"📂  Archivo recibido: {file.filename}")
    print(LOG_SEP)

    # ── 1. LEER ARCHIVO ──────────────────────────────────────
    contenido = await file.read()

    try:
        df = pd.read_excel(io.BytesIO(contenido), skiprows=1)
    except Exception:
        try:
            df = pd.read_csv(io.BytesIO(contenido))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    print(f"\n📊  Total de filas leídas  : {len(df)}")
    print(f"📋  Columnas encontradas   : {list(df.columns)}\n")

    # ── 2. NORMALIZAR COLUMNAS ────────────────────────────────
    df.columns = [str(c).strip().upper() for c in df.columns]

    required = {"DESCRIPCION", "CATEGORIA", "MARCA"}
    if not required.issubset(df.columns):
        raise HTTPException(
            status_code=422,
            detail=f"Faltan columnas: {required - set(df.columns)}",
        )

    df = df[["DESCRIPCION", "CATEGORIA", "MARCA"]].copy()

    # ── 3. LIMPIEZA VECTORIZADA ───────────────────────────────
    filas_antes = len(df)

    # Primero dropna real antes de convertir a str (evita float NaN en .unique())
    df = df.dropna(subset=["DESCRIPCION", "CATEGORIA", "MARCA"])

    for col in ["DESCRIPCION", "CATEGORIA", "MARCA"]:
        df[col] = df[col].astype(str).str.strip()

    # eliminar filas con campos vacíos o que quedaron como "nan"/"none" tras astype
    _BAD = {"", "nan", "none", "NaN", "None"}
    mask_validas = (
        ~df["DESCRIPCION"].isin(_BAD) &
        ~df["CATEGORIA"].isin(_BAD)   &
        ~df["MARCA"].isin(_BAD)
    )
    df = df[mask_validas].reset_index(drop=True)

    filas_descartadas_limpieza = filas_antes - len(df)
    print(f"🧹  Filas descartadas en limpieza: {filas_descartadas_limpieza}")
    print(f"✅  Filas válidas a procesar     : {len(df)}\n")

    # ── 4. FASE 1 & 2: MARCAS Y CATEGORÍAS (bulk) ────────────
    print("🏷️   FASE 1: MARCAS")
    nombres_marcas = set(df["MARCA"].unique())
    marca_map = _bulk_upsert_names("marca", "marcanombre", "marcaid", nombres_marcas)

    print("\n📂  FASE 2: CATEGORÍAS")
    nombres_cats = set(df["CATEGORIA"].unique())
    cat_map = _bulk_upsert_names("categoria", "ctgranombre", "ctgraid", nombres_cats)

    # ── 5. MAPEAR IDs EN EL DATAFRAME (vectorizado) ───────────
    df["marca_id"] = df["MARCA"].map(marca_map)
    df["cat_id"]   = df["CATEGORIA"].map(cat_map)

    # Filas sin mapeo (insert de marca/categoria falló)
    sin_ids = df[df["marca_id"].isna() | df["cat_id"].isna()].copy()
    df      = df[df["marca_id"].notna() & df["cat_id"].notna()].copy()

    errores_mapeo = []
    for _, row in sin_ids.iterrows():
        motivo = []
        if pd.isna(row["marca_id"]):    motivo.append("error marca")
        if pd.isna(row["cat_id"]):      motivo.append("error categoria")
        errores_mapeo.append({
            "DESCRIPCION": row["DESCRIPCION"],
            "CATEGORIA":   row["CATEGORIA"],
            "MARCA":       row["MARCA"],
            "_motivo":     ", ".join(motivo),
        })

    # ── 6. FASE 3: PRODUCTOS (dedup + bulk insert) ────────────
    print("\n📦  FASE 3: PRODUCTOS")

    # Prefetch nombres de productos existentes (paginado)
    print("   🔍 Descargando productos existentes…")
    existing_products = _fetch_all_pages("producto", "prdcnombre")
    existing_names_lower: set[str] = {
        r["prdcnombre"].strip().lower() for r in existing_products
    }
    print(f"   📖 {len(existing_names_lower)} productos ya en BD")

    # Detectar duplicados dentro del propio Excel
    df["_nombre_lower"] = df["DESCRIPCION"].str.lower()
    duplicados_excel = df.duplicated(subset="_nombre_lower", keep="first")

    errores_dup: list[dict] = []

    for _, row in df[duplicados_excel].iterrows():
        errores_dup.append({
            "DESCRIPCION": row["DESCRIPCION"],
            "CATEGORIA":   row["CATEGORIA"],
            "MARCA":       row["MARCA"],
            "_motivo":     "duplicado en excel",
        })

    df = df[~duplicados_excel].copy()

    # Detectar duplicados contra BD
    mask_dup_bd = df["_nombre_lower"].isin(existing_names_lower)
    for _, row in df[mask_dup_bd].iterrows():
        errores_dup.append({
            "DESCRIPCION": row["DESCRIPCION"],
            "CATEGORIA":   row["CATEGORIA"],
            "MARCA":       row["MARCA"],
            "_motivo":     "duplicado en BD",
        })

    df_nuevos = df[~mask_dup_bd].copy()

    duplicados_total = len(errores_dup)
    print(f"   🔁 Duplicados detectados: {duplicados_total}")
    print(f"   🆕 Productos nuevos a insertar: {len(df_nuevos)}")

    # Construir payload y bulk insert
    records = [
        {
            "prdcnombre": row["DESCRIPCION"],
            "ctgraid":    int(row["cat_id"]),
            "marcaid":    int(row["marca_id"]),
        }
        for _, row in df_nuevos.iterrows()
    ]

    insertados, errores_insert = _chunked_insert_products(records)

    # ── 7. RESUMEN ────────────────────────────────────────────
    filas_descartadas = errores_mapeo + errores_dup + errores_insert

    print(f"\n{LOG_SEP}")
    print("📊  RESUMEN FINAL")
    print(LOG_SEP)
    print(f"   ✅ Insertados            : {insertados}")
    print(f"   🔁 Duplicados           : {duplicados_total}")
    print(f"   🧹 Descartados limpieza : {filas_descartadas_limpieza}")
    print(f"   ❌ Otros errores        : {len(errores_mapeo) + len(errores_insert)}")
    print(LOG_SEP + "\n")

    # ── 8. DEVOLVER DESCARTADOS ───────────────────────────────
    if filas_descartadas:
        df_desc = pd.DataFrame(filas_descartadas)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_desc.to_excel(writer, index=False, sheet_name="descartados")
        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="descartados.xlsx"',
                "X-Insertados": str(insertados),
                "X-Duplicados": str(duplicados_total),
            },      
        )

    return {
        "ok":          True,
        "insertados":  insertados,
        "duplicados":  duplicados_total,
        "descartados": 0,
    }