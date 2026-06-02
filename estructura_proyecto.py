import os
from datetime import datetime

def generar_estructura(ruta_inicio="."):
    estructura = []

    estructura.append("ESTRUCTURA DEL PROYECTO")
    estructura.append("=" * 60)
    estructura.append(f"Ruta base: {os.path.abspath(ruta_inicio)}")
    estructura.append(f"Fecha: {datetime.now()}")
    estructura.append("=" * 60 + "\n")

    for root, dirs, files in os.walk(ruta_inicio):
        nivel = root.replace(ruta_inicio, "").count(os.sep)
        indent = "    " * nivel

        estructura.append(f"{indent}📁 {os.path.basename(root)}/")

        subindent = "    " * (nivel + 1)

        # Carpetas
        for d in dirs:
            estructura.append(f"{subindent}📂 {d}/")

        # Archivos
        for f in files:
            estructura.append(f"{subindent}📄 {f}")

    return "\n".join(estructura)


def guardar_estructura(contenido, nombre_archivo="estructura_proyecto.txt"):
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"\n✅ Estructura guardada en: {nombre_archivo}")


if __name__ == "__main__":
    print("🔍 Generando estructura del proyecto...\n")

    resultado = generar_estructura(".")
    guardar_estructura(resultado)