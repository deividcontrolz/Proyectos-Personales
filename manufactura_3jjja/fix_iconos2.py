#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_iconos2.py
==============
Corrige los iconos cuadrados en TODO el proyecto 3-JJJ-A.

Hace 3 cosas:
  1) Agrega bloque ANTI-CONFLICTO al final de 3jjja-icons-mask.css
     (neutraliza el ::before de bootstrap-icons que dibuja cuadrados).
  2) Verifica que los iconos del modal de cambiar contraseña estén
     todos definidos y agrega los que falten.
  3) Detecta si algún template carga bootstrap-icons.css y lo reporta
     para que lo quites manualmente (no lo borra para no romper nada).

Hace BACKUP de cada archivo antes de modificarlo.
Ignora archivos de LOG.
"""
import os, re, sys, shutil
from datetime import datetime
from urllib.parse import quote

# ------------------------------------------------------------
TARGET_CSS = '3jjja-icons-mask.css'
LOG_MARKERS = ('.log', '_log', '-log', '.access', '.error', 'debug.log')
SKIP_DIRS = {'.git', '.hg', '.svn', 'node_modules', '__pycache__',
             '.venv', 'venv', 'env', '.env', '.idea', '.vscode',
             'media', 'migrations', 'staticfiles'}

# Iconos del modal "Cambiar Contraseña" (admin_usuarios.html)
ICONOS_MODAL = {
    'bi-shield-lock':       None,   # ya definido
    'bi-info-circle':       None,
    'bi-exclamation-circle':None,
    'bi-check-circle':      None,
    'bi-x-circle':          None,
    'bi-check-lg':          None,
    'bi-x-lg':              None,
    'bi-key':               None,
    'bi-lock-fill':         'M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2m3 6V3a3 3 0 0 0-6 0v4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2',
    'bi-unlock-fill':       'M11 1a2 2 0 0 0-2 2v4a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h5V3a3 3 0 0 1 6 0v4a.5.5 0 0 1-1 0V3a2 2 0 0 0-2-2',
    'bi-info-circle-fill':  'M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16m.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07 .686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2',
    'bi-eye-slash':          'M13.359 11.238C15.06 9.72 16 8 16 8s-3-5.5-8-5.5a7 7 0 0 0-2.79.588l.77.771A6 6 0 0 1 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755q-.27.275-.57.535zM11.297 9.176a3.5 3.5 0 0 0-4.474-4.474l.823.823a2.5 2.5 0 0 1 2.829 2.829zm-2.943 1.299.822.822a3.5 3.5 0 0 1-4.474-4.474l.823.823a2.5 2.5 0 0 0 2.829 2.829|M3.35 5.47q-.27.24-.518.487A13 13 0 0 0 1.172 8l.195.288c.335.48.83 1.12 1.465 1.755C4.121 11.332 5.881 12.5 8 12.5c.716 0 1.39-.133 2.02-.36l.77.772A7 7 0 0 1 8 13.5C3 13.5 0 8 0 8s.939-1.721 2.641-3.238l.708.709zm10.296 8.884-12-12 .708-.708 12 12z',
}

BLOQUE_ANTI_CONFLICTO = '''

/* ============================================================ */
/* ANTI-CONFLICTO: neutraliza el sistema de fuente de Bootstrap  */
/* Icons. Nuestro sistema usa mask-image en .bi, así que        */
/* cualquier ::before/::after con font-family de Bootstrap      */
/* sobra y produce cuadrados.                                    */
/* ============================================================ */
.bi::before,
.bi::after,
[class^="bi-"]::before,
[class*=" bi-"]::before,
[class^="bi-"]::after,
[class*=" bi-"]::after {
  content: none !important;
  display: none !important;
  font-family: inherit !important;
}

.bi {
  font-family: inherit !important;
  font-style: normal !important;
  font-weight: normal !important;
}
'''

# ------------------------------------------------------------
def es_log(p):
    p = str(p).lower()
    return any(k in p for k in LOG_MARKERS)

def svg_uri(nombre, d):
    if '|' in d:
        inner = ''.join(f'<path d="{x}"/>' for x in d.split('|'))
    else:
        inner = f'<path d="{d}"/>'
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
           f'fill="currentColor" class="bi bi-{nombre[3:]}" viewBox="0 0 16 16">'
           f'{inner}</svg>')
    return 'url("data:image/svg+xml,' + quote(svg, safe='') + '")'

def buscar(nombre, raiz, ext=None):
    out = []
    for dp, dn, fn in os.walk(raiz):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if ext and not f.endswith(ext): continue
            if f == nombre or (ext and nombre.endswith(ext) and f == nombre):
                full = os.path.join(dp, f)
                if not es_log(full):
                    out.append(full)
    return out

def backup(path):
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = f'{path}.bak_{stamp}'
    shutil.copy2(path, bak)
    return bak

def tiene_anti_conlicto(txt):
    return 'ANTI-CONFLICTO' in txt

def icono_definido(txt, nombre):
    return re.search(rf'\.{re.escape(nombre)}\s*\{{', txt) is not None

# ------------------------------------------------------------
def procesar_css(path):
    print(f"\n→ CSS: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        txt = f.read()

    cambios = []

    # A) Agregar bloque anti-conflicto si no está
    if not tiene_anti_conlicto(txt):
        cambios.append(('ANTI-CONFLICTO', BLOQUE_ANTI_CONFLICTO))
        print("  ✗ Falta bloque ANTI-CONFLICTO  → se agregará")
    else:
        print("  ✓ Bloque ANTI-CONFLICTO ya presente")

    # B) Agregar iconos faltantes
    faltan = []
    for nombre, d in ICONOS_MODAL.items():
        if d is None:  # ya definido o lo damos por hecho
            continue
        if not icono_definido(txt, nombre):
            faltan.append(nombre)

    if faltan:
        print(f"  ✗ Faltan iconos: {', '.join(faltan)}")
        bloque_iconos = "\n\n/* --- Iconos agregados por fix_iconos2 --- */\n"
        for n in faltan:
            u = svg_uri(n, ICONOS_MODAL[n])
            bloque_iconos += f"\n.{n} {{\n  -webkit-mask-image: {u};\n  mask-image: {u};\n}}\n"
        cambios.append(('ICONOS', bloque_iconos))
    else:
        print("  ✓ Todos los iconos del modal ya están definidos")

    if not cambios:
        print("  → Sin cambios")
        return False

    bak = backup(path)
    print(f"  ↳ Backup: {os.path.basename(bak)}")

    if not txt.endswith('\n'):
        txt += '\n'
    for _, bloque in cambios:
        txt += bloque

    with open(path, 'w', encoding='utf-8') as f:
        f.write(txt)
    print(f"  ✓ Guardado")
    return True

def detectar_bootstrap_icons(raiz):
    """Busca referencias a bootstrap-icons.css en templates."""
    hallazgos = []
    for dp, dn, fn in os.walk(raiz):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if not f.endswith('.html'): continue
            full = os.path.join(dp, f)
            if es_log(full): continue
            try:
                with open(full, 'r', encoding='utf-8', errors='ignore') as fh:
                    txt = fh.read()
            except Exception:
                continue
            for i, line in enumerate(txt.splitlines(), 1):
                if 'bootstrap-icons' in line.lower() and '<link' in line.lower():
                    hallazgos.append((full, i, line.strip()))
    return hallazgos

# ------------------------------------------------------------
def main():
    raiz = os.getcwd()
    print("=" * 64)
    print(" fix_iconos2.py — corrige cuadrados en TODOS los iconos")
    print("=" * 64)
    print(f"Raíz: {raiz}\n")

    # PASO 1: CSS
    print("[1] Procesando 3jjja-icons-mask.css ...")
    css_files = buscar(TARGET_CSS, raiz)
    if not css_files:
        print("  ✗ No encontré 3jjja-icons-mask.css")
        return 1
    for p in css_files:
        print(f"    • {p}")
    print()
    modificados = 0
    for p in css_files:
        if procesar_css(p):
            modificados += 1

    # PASO 2: detectar bootstrap-icons en HTML
    print("\n[2] Buscando referencias a bootstrap-icons.css en templates ...")
    conflictos = detectar_bootstrap_icons(raiz)
    if conflictos:
        print(f"  ⚠ Encontré {len(conflictos)} referencia(s) que PUEDEN causar cuadrados:\n")
        for path, lineno, linea in conflictos:
            rel = os.path.relpath(path, raiz)
            print(f"    • {rel}:{lineno}")
            print(f"        {linea}")
        print()
        print("  → ABRÍ esos templates y BORRÁ esas líneas <link ...>.")
        print("    Solo debe quedar:  <link rel=\"stylesheet\" href=\"{% static 'css/3jjja-icons-mask.css' %}\">")
    else:
        print("  ✓ No encontré conflictos con bootstrap-icons.css")

    # PASO 3: reporte
    print("\n" + "=" * 64)
    if modificados:
        print(f"✔ {modificados} archivo(s) CSS actualizado(s).")
    else:
        print("✔ El CSS ya estaba correcto.")
    print()
    print("PRÓXIMOS PASOS:")
    print("  1) Si detecté conflictos, quitalos de los templates.")
    print("  2) python manage.py collectstatic --noinput")
    print("  3) En el navegador:  Ctrl + F5")
    print("  4) Abrí el modal 'Cambiar Contraseña' → los iconos deben verse.")
    print("=" * 64)
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(130)