#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
aplicar_solo_titulo_verde.py
----------------------------
Deja UNICAMENTE el titulo "Registro de Usuario" en verde.
Todo lo demas del formulario vuelve a su estado original.

Hace dos cosas:
    1. Elimina el bloque <style> grande de override verde (si existe).
    2. Inyecta un <style> minimo que SOLO pinta el h1 del header.

USO:
    1. Colocar este archivo junto a manage.py
    2. Ejecutar:  python aplicar_solo_titulo_verde.py
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BACKUP_DIR = BASE_DIR / f"_backup_titulo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

OK = "[OK]"
ERR = "[ERROR]"
WARN = "[AVISO]"
SKIP = "[SALTADO]"

# Marcadores de bloques previos a eliminar
MARKERS_ANTIGUOS = [
    "/* === OVERRIDE VERDE REGISTRO (inline) === */",
    "/* === OVERRIDE VERDE REGISTRO v1 === */",
]

# Nuevo bloque minimo: solo el titulo
NUEVO_STYLE = """<style>
/* === SOLO TITULO VERDE === */
.registro-container .registro-header h1 {
    color: #34d399 !important;
}
.registro-container .registro-header h1 i {
    color: #10b981 !important;
}
/* === FIN SOLO TITULO VERDE === */
</style>
"""

MARKER_NUEVO = "/* === SOLO TITULO VERDE === */"


def log(msg):
    print(msg)


def hacer_backup(path):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        rel = path.relative_to(BASE_DIR)
    except ValueError:
        rel = Path(path.name)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    log(f"    {OK} Backup: {rel}")


def buscar_archivo(rutas):
    for rel in rutas:
        p = BASE_DIR / rel
        if p.exists():
            return p
    return None


def quitar_bloque_style(texto, marcador_inicio, marcador_fin):
    """Elimina el bloque <style>...</style> que contiene el marcador."""
    # Busca <style> ... marcador_inicio ... </style>
    patron = re.compile(
        r"<style>\s*" + re.escape(marcador_inicio) + r".*?</style>\s*",
        re.DOTALL,
    )
    nuevo, n = patron.subn("", texto)
    return nuevo, n


def quitar_override_app_css():
    """Elimina el bloque que se anexo al final de app.css (si existe)."""
    log("\n=== Limpiando app.css (override anterior) ===")
    path = buscar_archivo([
        'static/css/app.css',
        'core/static/css/app.css',
    ])
    if not path:
        log(f"    {WARN} No se encontro app.css")
        return

    texto = path.read_text(encoding='utf-8')
    marker = "/* === OVERRIDE VERDE REGISTRO v1 === */"
    marker_fin = "/* === FIN OVERRIDE VERDE REGISTRO v1 === */"

    if marker not in texto:
        log(f"    {SKIP} app.css no tenia el override anterior")
        return

    # Elimina desde el marcador de inicio hasta el marcador de fin (inclusive)
    patron = re.compile(
        re.escape(marker) + r".*?" + re.escape(marker_fin) + r"\s*",
        re.DOTALL,
    )
    texto_limpio, n = patron.subn("", texto)
    if n == 0:
        log(f"    {WARN} No se pudo eliminar el bloque de app.css")
        return

    hacer_backup(path)
    path.write_text(texto_limpio.rstrip() + "\n", encoding='utf-8')
    log(f"    {OK} Override anterior eliminado de app.css")


def modificar_registro_html():
    log("\n=== Ajustando registro.html ===")
    path = buscar_archivo([
        'templates/registration/registro.html',
        'core/templates/registration/registro.html',
    ])
    if not path:
        log(f"    {ERR} No se encontro registro.html")
        return False

    hacer_backup(path)
    texto = path.read_text(encoding='utf-8')
    cambios = 0

    # 1. Eliminar bloques de override anteriores (por marcador de inicio)
    for marker in MARKERS_ANTIGUOS:
        texto, n = quitar_bloque_style(texto, marker, "</style>")
        if n > 0:
            log(f"    {OK} Bloque de override eliminado ({n} bloque(s))")
            cambios += n

    # 2. Si ya esta el bloque nuevo, no duplicar
    if MARKER_NUEVO in texto:
        log(f"    {SKIP} El bloque 'solo titulo verde' ya estaba aplicado")
    else:
        # Insertar justo despues de {% block content %}
        patron_block = re.compile(r"(\{%\s*block\s+content\s*%\})")
        m = patron_block.search(texto)
        if not m:
            log(f"    {ERR} No se encontro {{% block content %}}")
            return False
        fin = m.end()
        texto = texto[:fin] + "\n" + NUEVO_STYLE + texto[fin:]
        log(f"    {OK} Bloque 'solo titulo verde' inyectado")
        cambios += 1

    if cambios > 0:
        path.write_text(texto, encoding='utf-8')
        log(f"    {OK} registro.html guardado ({cambios} cambio(s))")
    return cambios > 0


def resumen(ok):
    log("\n" + "=" * 60)
    log("RESUMEN")
    log("=" * 60)
    if ok:
        log(f"  {OK} Configuracion aplicada")
        log("")
        log("Ahora SOLO el titulo 'Registro de Usuario' esta en verde.")
        log("Todo lo demas vuelve a como estaba antes.")
        log("")
        log("Proximos pasos:")
        log("  1. Reinicia el servidor:  python manage.py runserver")
        log("  2. Recarga el registro con Ctrl + F5 (forzar recarga)")
    else:
        log(f"  {WARN} No hubo cambios que aplicar.")
    log("")
    log(f"Backups en: {BACKUP_DIR.name}/")
    log("=" * 60)


def main():
    log("=" * 60)
    log("SOLO TITULO VERDE - REGISTRO DE USUARIO")
    log("Sistema 3-JJJ-A")
    log("=" * 60)
    log(f"Directorio base: {BASE_DIR}")

    if not (BASE_DIR / 'manage.py').exists():
        log("")
        log(f"{WARN} No se detecto manage.py en esta carpeta.")
        r = input("\n¿Continuar de todas formas? (s/N): ").strip().lower()
        if r != 's':
            log("Cancelado.")
            sys.exit(1)

    quitar_override_app_css()
    ok = modificar_registro_html()
    resumen(ok)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        log("\n\nCancelado por el usuario.")
        sys.exit(1)
    except Exception as e:
        log(f"\n{ERR} Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)