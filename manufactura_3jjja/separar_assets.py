#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
separar_assets.py
Separa CSS/JS inline de un template Django. Versión con diagnóstico.
"""

from __future__ import print_function

import argparse
import io
import re
import sys
import traceback
from pathlib import Path

# ---------- Forzar salida UTF-8 (importante en Windows) ----------
if sys.version_info >= (3, 7):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
elif sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


STYLE_RE  = re.compile(r"<style\b[^>]*>(.*?)</style>",   re.DOTALL | re.IGNORECASE)
SCRIPT_RE = re.compile(r"<script\b(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
                       re.DOTALL | re.IGNORECASE)

ROOT = Path(__file__).resolve().parent


def log(*a):
    print(*a)
    sys.stdout.flush()


# --------------------------------------------------------------------------- #
# Resolución de rutas
# --------------------------------------------------------------------------- #

def resolver_template(raw):
    """Devuelve un Path al template, buscando de varias formas."""
    # 1) Absoluta
    p = Path(raw)
    if p.is_absolute() and p.exists():
        return p

    # 2) Relativa al script (donde está manage.py)
    p2 = (ROOT / raw).resolve()
    if p2.exists():
        return p2

    # 3) Relativa al cwd
    p3 = Path(raw).resolve()
    if p3.exists():
        return p3

    # 4) Buscar por nombre en el proyecto
    name = Path(raw).name
    encontrados = [f for f in ROOT.rglob(name) if f.is_file()]
    if len(encontrados) == 1:
        log("[!] No encontré '{}' tal cual, pero sí este: {}".format(raw, encontrados[0]))
        return encontrados[0]
    if len(encontrados) > 1:
        log("[ERROR] Varios archivos llamados '{}':".format(name))
        for f in encontrados:
            log("   - {}".format(f))
        sys.exit(2)

    log("[ERROR] No encontré el template.")
    log("   Argumento        : {}".format(raw))
    log("   Probé en         : {}".format(p3))
    log("   ROOT (script)    : {}".format(ROOT))
    log("   Archivos .html en el proyecto:")
    for f in sorted(ROOT.rglob("*.html"))[:20]:
        log("     - {}".format(f.relative_to(ROOT)))
    sys.exit(2)


def resolver_static(app, subdir):
    """Devuelve (ruta_física, prefijo_para_static_tag)."""
    subdir = (subdir or "").strip("/\\")

    if app:
        candidatos = []
        for p in ROOT.rglob(app):
            if not p.is_dir():
                continue
            if not (p / "__init__.py").exists():
                continue
            sp = str(p).lower()
            if "site-packages" in sp or "\\venv\\" in sp or "/venv/" in sp \
               or "\\env\\" in sp or "/env/" in sp or "/.venv/" in sp:
                continue
            candidatos.append(p)

        if not candidatos:
            log("[ERROR] No encontré la app '{}' (carpeta con __init__.py).".format(app))
            log("   ¿Pusiste --app correctamente? Ej: --app core")
            sys.exit(2)
        candidatos.sort(key=lambda x: len(x.parts))
        app_path = candidatos[0]
        log("   App encontrada   : {}".format(app_path))

        static_root = app_path / "static" / app
        prefix = app + "/"
        if subdir:
            static_root = static_root / subdir
            prefix += subdir + "/"
        static_root.mkdir(parents=True, exist_ok=True)
        return static_root, prefix

    static_root = ROOT / "static"
    if subdir:
        static_root = static_root / subdir
    static_root.mkdir(parents=True, exist_ok=True)
    prefix = (subdir + "/") if subdir else ""
    return static_root, prefix


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(
        description="Separa CSS/JS inline de un template Django."
    )
    parser.add_argument("template", help="Ruta al template .html")
    parser.add_argument("--app",    default=None, help="App destino (ej: core).")
    parser.add_argument("--subdir", default="",   help="Subcarpeta dentro de css/ y js/.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force",   action="store_true")
    parser.add_argument("--debug",   action="store_true",
                        help="Muestra el contenido extraído.")
    args = parser.parse_args()

    log("=" * 60)
    log(" separar_assets.py")
    log("=" * 60)
    log(" ROOT (script)  : {}".format(ROOT))
    log(" Template arg   : {}".format(args.template))

    template_path = resolver_template(args.template)
    log(" Template real  : {}".format(template_path))

    static_root, static_prefix = resolver_static(args.app, args.subdir)
    log(" Static root    : {}".format(static_root))
    log(" Static prefix  : '{}'".format(static_prefix))

    css_rel = "css/{}.css".format(template_path.stem)
    js_rel  = "js/{}.js".format(template_path.stem)
    css_path = static_root / css_rel
    js_path  = static_root / js_rel
    log(" CSS destino    : {}".format(css_path))
    log(" JS  destino    : {}".format(js_path))
    log("-" * 60)

    html = template_path.read_text(encoding="utf-8")
    log(" Tamaño template: {} caracteres".format(len(html)))

    styles  = STYLE_RE.findall(html)
    scripts = SCRIPT_RE.findall(html)

    log(" Bloques <style>  encontrados : {}".format(len(styles)))
    log(" Bloques <script> encontrados : {}".format(len(scripts)))

    if not styles and not scripts:
        log("")
        log("[!] No hay <style> ni <script> inline. Nada que hacer.")
        log("    ¿Estás seguro de que este es el archivo correcto?")
        log("    Primeros 400 caracteres del template:")
        log("    " + html[:400].replace("\n", "\n    "))
        return 0

    if args.debug:
        for i, s in enumerate(styles):
            log("\n--- <style> #{} (primeros 200 chars) ---".format(i + 1))
            log(s[:200])
        for i, s in enumerate(scripts):
            log("\n--- <script> #{} (primeros 200 chars) ---".format(i + 1))
            log(s[:200])

    if args.dry_run:
        log("")
        log("[dry-run] No se escribió nada.")
        return 0

    for p in (css_path, js_path):
        if p.exists() and not args.force:
            log("   [!] Ya existe {} (usa --force para sobrescribir).".format(p))

    # ---- Escribir archivos ----
    css_content = "\n\n".join(s.strip() for s in styles  if s.strip()) + "\n"
    js_content  = "\n\n".join(s.strip() for s in scripts if s.strip()) + "\n"

    css_path.write_text(css_content, encoding="utf-8")
    log("   ✔ CSS escrito  : {}  ({} bytes)".format(css_path, len(css_content)))

    js_path.write_text(js_content, encoding="utf-8")
    log("   ✔ JS escrito   : {}  ({} bytes)".format(js_path, len(js_content)))

    # ---- Reemplazar en el HTML ----
    static_css = "{{% static '{}{}' %}}".format(static_prefix, css_rel)
    static_js  = "{{% static '{}{}' %}}".format(static_prefix, js_rel)

    st_n = [0]
    def _r_style(_m):
        st_n[0] += 1
        if st_n[0] == 1:
            return '<link rel="stylesheet" href="{}">'.format(static_css)
        return ""

    sc_n = [0]
    def _r_script(_m):
        sc_n[0] += 1
        if sc_n[0] == 1:
            return '<script src="{}"></script>'.format(static_js)
        return ""

    new_html = STYLE_RE.sub(_r_style, html)
    new_html = SCRIPT_RE.sub(_r_script, new_html)

    if new_html == html:
        log("   [!] El HTML no cambió (¿los bloques ya estaban reemplazados?).")
    else:
        template_path.write_text(new_html, encoding="utf-8")
        log("   ✔ HTML actualizado: {}".format(template_path))

    log("")
    log("✔ Listo.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        print("\n[EXCEPCIÓN NO CONTROLADA]", file=sys.stderr)
        traceback.print_exc()
        # Evita que la ventana se cierre si se ejecuta con doble clic
        if sys.platform.startswith("win"):
            input("\nPresiona ENTER para salir...")
        sys.exit(1)