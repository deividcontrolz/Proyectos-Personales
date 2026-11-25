#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
aplicar_titulo_verde_limpio.py
------------------------------
Deja SOLO el titulo "Registro de Usuario" en verde, con el CSS
en un archivo independiente. NO toca app.css ni custom.css.

Pasos:
    1. Limpia cualquier override de app.css (si existe).
    2. Limpia cualquier override de custom.css (si existe).
    3. Crea static/css/registro-titulo.css con el estilo del titulo.
    4. Quita el <style> inline de registro.html (si existe).
    5. Enlaza el CSS externo dentro de {% block content %}.

USO:
    1. Colocar este archivo junto a manage.py
    2. Ejecutar:  python aplicar_titulo_verde_limpio.py
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

# Marcadores que hay que eliminar de app.css/custom.css
MARKERS_CSS = [
    "/* === OVERRIDE VERDE REGISTRO v1 === */",
]
MARKERS_CSS_FIN = [
    "/* === FIN OVERRIDE VERDE REGISTRO v1 === */",
]

# Marcadores que hay que eliminar del <style> inline en registro.html
MARKERS_INLINE = [
    "/* === SOLO TITULO VERDE === */",
    "/* === OVERRIDE VERDE REGISTRO (inline) === */",
    "/* === OVERRIDE VERDE REGISTRO === */",
]

NOMBRE_CSS = "registro-titulo.css"
LINK_TAG = '<link rel="stylesheet" href="{% static \'css/' + NOMBRE_CSS + '\' %}">'

CONTENIDO_CSS = """/* ============================================================
   registro-titulo.css
   Solo el estilo del titulo "Registro de Usuario".
   Se carga dentro de {% block content %} para ganar en cascada
   sobre app.css (que se carga desde el <head> del base.html).
   ============================================================ */

.registro-container .registro-header h1 {
    color: #34d399 !important;
}

.registro-container .registro-header h1 i {
    color: #10b981 !important;
}
"""


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


def localizar_static():
    for rel in ['static', 'core/static']:
        p = BASE_DIR / rel
        if p.exists() and p.is_dir():
            return p
    p = BASE_DIR / 'static'
    p.mkdir(parents=True, exist_ok=True)
    return p


# ============================================================
# 1. Limpiar override de app.css
# ============================================================
def limpiar_override_en_css(nombre_archivo):
    log(f"\n=== Limpiando {nombre_archivo} ===")
    path = buscar_archivo([
        f'static/css/{nombre_archivo}',
        f'core/static/css/{nombre_archivo}',
    ])
    if not path:
        log(f"    {WARN} No se encontro {nombre_archivo}")
        return

    texto = path.read_text(encoding='utf-8')
    hubo_cambio = False

    for marker_ini, marker_fin in zip(MARKERS_CSS, MARKERS_CSS_FIN):
        if marker_ini not in texto:
            continue
        patron = re.compile(
            re.escape(marker_ini) + r".*?" + re.escape(marker_fin) + r"\s*",
            re.DOTALL,
        )
        texto_nuevo, n = patron.subn("", texto)
        if n > 0:
            if not hubo_cambio:
                hacer_backup(path)
                hubo_cambio = True
            texto = texto_nuevo
            log(f"    {OK} Bloque eliminado ({n} bloque(s))")

    if hubo_cambio:
        path.write_text(texto.rstrip() + "\n", encoding='utf-8')
        log(f"    {OK} {nombre_archivo} guardado limpio")
    else:
        log(f"    {SKIP} {nombre_archivo} no contenia el override")


# ============================================================
# 2. Crear archivo CSS externo
# ============================================================
def crear_css_externo():
    log(f"\n=== Creando static/css/{NOMBRE_CSS} ===")
    static_dir = localizar_static()
    css_dir = static_dir / 'css'
    css_dir.mkdir(parents=True, exist_ok=True)

    ruta = css_dir / NOMBRE_CSS
    if ruta.exists():
        hacer_backup(ruta)
    ruta.write_text(CONTENIDO_CSS, encoding='utf-8')
    log(f"    {OK} Creado: {ruta.relative_to(BASE_DIR)}")


# ============================================================
# 3. Modificar registro.html
# ============================================================
def quitar_style_inline(texto):
    total = 0
    for marker in MARKERS_INLINE:
        patron = re.compile(
            r"[ \t]*<style>\s*" + re.escape(marker) + r".*?</style>\s*\n?",
            re.DOTALL,
        )
        texto, n = patron.subn("", texto)
        if n > 0:
            log(f"    {OK} <style> inline eliminado ({marker})")
            total += n
    if total == 0:
        log(f"    {SKIP} No habia <style> inline")
    return texto


def inyectar_link(texto):
    if NOMBRE_CSS in texto:
        log(f"    {SKIP} El <link> a {NOMBRE_CSS} ya estaba")
        return texto, 0

    patron_block = re.compile(r"(\{%\s*block\s+content\s*%\})")
    m = patron_block.search(texto)
    if not m:
        log(f"    {ERR} No se encontro {{% block content %}}")
        return texto, 0

    texto = texto[:m.end()] + "\n" + LINK_TAG + texto[m.end():]
    log(f"    {OK} <link> inyectado en {{% block content %}}")
    return texto, 1


def modificar_registro_html():
    log("\n=== Modificando registro.html ===")
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

    texto = quitar_style_inline(texto)
    texto, n = inyectar_link(texto)
    cambios += n

    path.write_text(texto, encoding='utf-8')
    log(f"    {OK} registro.html guardado")
    return True


# ============================================================
# RESUMEN
# ============================================================
def verificar():
    log("\n=== Verificacion final ===")
    # 1. app.css limpio
    app_css = buscar_archivo(['static/css/app.css', 'core/static/css/app.css'])
    if app_css:
        t = app_css.read_text(encoding='utf-8')
        if any(m in t for m in MARKERS_CSS):
            log(f"    {WARN} app.css aun contiene el override")
        else:
            log(f"    {OK} app.css limpio (sin override)")
    # 2. custom.css limpio
    cus_css = buscar_archivo(['static/css/custom.css', 'core/static/css/custom.css'])
    if cus_css:
        t = cus_css.read_text(encoding='utf-8')
        if any(m in t for m in MARKERS_CSS):
            log(f"    {WARN} custom.css aun contiene el override")
        else:
            log(f"    {OK} custom.css limpio (sin override)")
    # 3. archivo externo existe
    static_dir = localizar_static()
    ruta_css = static_dir / 'css' / NOMBRE_CSS
    if ruta_css.exists():
        log(f"    {OK} Existe static/css/{NOMBRE_CSS}")
    else:
        log(f"    {WARN} NO existe static/css/{NOMBRE_CSS}")
    # 4. registro.html enlaza el CSS
    reg = buscar_archivo([
        'templates/registration/registro.html',
        'core/templates/registration/registro.html',
    ])
    if reg:
        t = reg.read_text(encoding='utf-8')
        if NOMBRE_CSS in t:
            log(f"    {OK} registro.html enlaza {NOMBRE_CSS}")
        else:
            log(f"    {WARN} registro.html NO enlaza {NOMBRE_CSS}")
        if any(m in t for m in MARKERS_INLINE):
            log(f"    {WARN} registro.html aun tiene <style> inline")
        else:
            log(f"    {OK} registro.html sin <style> inline")


def resumen():
    log("\n" + "=" * 60)
    log("RESUMEN")
    log("=" * 60)
    log(f"  {OK} app.css y custom.css SIN override")
    log(f"  {OK} CSS externo en static/css/{NOMBRE_CSS}")
    log(f"  {OK} registro.html enlaza el CSS externo")
    log("")
    log("Proximos pasos:")
    log("  1. Reinicia el servidor:  python manage.py runserver")
    log("  2. Recarga con Ctrl + F5")
    log("")
    log(f"Backups en: {BACKUP_DIR.name}/")
    log("=" * 60)


def main():
    log("=" * 60)
    log("TITULO VERDE LIMPIO - CSS EN ARCHIVO EXTERNO")
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

    limpiar_override_en_css('app.css')
    limpiar_override_en_css('custom.css')
    crear_css_externo()
    modificar_registro_html()
    verificar()
    resumen()


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