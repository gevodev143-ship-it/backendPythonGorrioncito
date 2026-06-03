"""
actualizar_precios_cero.py
────────────────────────────────────────────────────────────
Busca en la tabla `producto` todos los registros donde
prdcprecio = 0 y los actualiza con un precio aleatorio
entre 10 y 50.
"""

import sys
import os
import random
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from app.config.supabase import supabase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s"
)
log = logging.getLogger(__name__)

# ── 1. Obtener productos con prdcprecio = 0 ──────────────────
log.info("Buscando productos con prdcprecio = 0...")
res = supabase.table("producto") \
    .select("prdcid, prdcnombre, prdcprecio") \
    .eq("prdcprecio", 0) \
    .execute()

if not res.data:
    log.info("No hay productos con precio en 0. Nada que actualizar.")
    sys.exit(0)

log.info(f"Productos encontrados con precio 0: {len(res.data)}")

# ── 2. Actualizar cada uno con precio aleatorio ───────────────
actualizados = 0

for producto in res.data:
    nuevo_precio = round(random.uniform(10, 50), 2)

    supabase.table("producto") \
        .update({"prdcprecio": nuevo_precio}) \
        .eq("prdcid", producto["prdcid"]) \
        .execute()

    log.info(f"  ✓ '{producto['prdcnombre']}' → prdcprecio = {nuevo_precio}")
    actualizados += 1

# ── 3. Resumen ────────────────────────────────────────────────
log.info("─" * 50)
log.info(f"Total actualizados: {actualizados}")
