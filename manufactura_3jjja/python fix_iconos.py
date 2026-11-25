#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_iconos.py
=============
Corrige los iconos que aparecen como cuadrados (▯) en el sistema 3-JJJ-A.

CAUSA:
    El archivo '3jjja-icons-mask.css' no define algunos iconos que las
    plantillas HTML usan: bi-lock-fill, bi-unlock-fill,
    bi-info-circle-fill y bi-eye-slash.

SOLUCION:
    Agrega esos 4 iconos al final del CSS mask, sin tocar ninguna otra
    regla ni archivo. Hace copia de seguridad antes de modificar.

USO:
    cd /ruta/a/la/raiz/del/proyecto      (donde está manage.py)
    python fix_iconos.py
"""

import os
import re
import sys
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

# ============================================================
# CONFIGURACION
# ============================================================
NOMBRE_CSS = '3jjja-icons-mask.css'
SUFIJO_BACKUP = '.bak_icons_' + datetime.now().strftime('%Y%m%d_%H%M%S')

# Palabras clave que delatan un archivo de LOG (no tocar nunca)
LOG_KEYWORDS = ('.log', 'log.', '-log', '_log', '.access', '.error', 'debug.log')

# Directorios que se ignoran al recorrer el proyecto
DIRS_IGNORADOS = {
    '.git', '.hg', '.svn',
    'node_modules', '__pycache__',
    '.venv', 'venv', 'env', '.env',
    'staticfiles', 'media', 'migrations',
    '.idea', '.vscode', 'dist', 'build',
}

# ============================================================
# DEFINICION DE LOS ICONOS FALTANTES
# (paths SVG oficiales de Bootstrap Icons v1.11)
# ============================================================
ICONOS_FALTANTES = {
    'bi-lock-fill':
        '<path d="M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2m3 6V3a3 3 0 0 0-6 0v4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2"/>',

    'bi-unlock-fill':
        '<path d="M11 1a2 2 0 0 0-2 2v4a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h5V3a3 3 0 0 1 6 0v4a.5.5 0 0 1-1 0V3a2 2 0 0 0-2-2"/>',

    'bi-info-circle-fill':
        '<path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16m.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2"/>',

    'bi-eye-slash':
        '<path d="M13.359 11.238C15.06 9.72 16 8 16 8s-3-5.5-8-5.5a7 7 0 0 0-2.79.588l.77.771A6 6 0 0 1 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755q-.27.275-.57.535zM11.297 9.176a3.5 3.5 0 0 0-4.474-4.474l.823.823a2.5 2.5 0 0 1 2.829 2.829zm-2.943 1.299.822.822a3.5 3.5 0 0 1-4.474-4.474l.823.823a2.5 2.5 0 0 0 2.829 2.829"/><path d="M3.35 5.47q-.27.24-.518.487A13 13 0 0 0 1.172 8l.195.288c.335.48.83 1.12 1.465 1.755C4.121 11.332 5.881 12.5 8 12.5c.716 0 1.39-.133 2.02-.36l.77.772A7 7 0 0 1 8 13.5C3 13.5 0 8 0 8s.939-1.721 2.641-3.238l.708.709zm10.296 8.884-12-12 .708-.708 12 12z"/>',
}


# ============================================================
# UTILIDADES
# ============================================================
def es_archivo_log(ruta):
    """True si el nombre de archivo delata un LOG (no tocar)."""
    p = str(ruta).lower()
    return any(k in p for k in LOG_KEYWORDS)


def svg_a_data_uri(svg_inner, icon_name):
    """
    Construye el data:image/svg+xml URL-encoded EXACTAMENTE con el
    mismo formato que ya usa 3jjja-icons-mask.css.
    """
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
        f'fill="currentColor" class="bi bi-{icon_name}" viewBox="0 0 16 16">'
        f'   {svg_inner} </svg>'
    )
    return 'url("data:image/svg+xml,' + quote(svg, safe='') + '")'


def buscar_css_iconos(raiz):
    """Busca archivos '3jjja-icons-mask.css' en el proyecto, sin logs."""
    encontrados = []
    for dirpath, dirnames, filenames in os.walk(raiz):
        # Podar directorios ignorados (modifica la lista in-place)
        dirnames[:] = [d for d in dirnames if d not in DIRS_IGNORADOS]
        for fname in filenames:
            if fname != NOMBRE_CSS:
                continue
            full = os.path.join(dirpath, fname)
            if es_archivo_log(full):
                print(f"  [IGNORADO] {full}  (parece log)")
                continue
            encontrados.append(full)
    return encontrados


def iconos_definidos(css_path):
    """Devuelve el set de nombres 'bi-xxx' ya definidos en el CSS."""
    try:
        with open(css_path, 'r', encoding='utf-8', errors='ignore') as f:
            txt = f.read()
    except Exception as e:
        print(f"  [ERROR] No se pudo leer: {e}")
        return set()
    return set(re.findall(r'\.(bi-[a-zA-Z0-9\-]+)\s*\{', txt))


def escanear_plantillas(raiz):
    """Devuelve el set de iconos 'bi-xxx' usados en los .html del proyecto."""
    usados = set()
    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if d not in DIRS_IGNORADOS]
        for fname in filenames:
            if not fname.endswith('.html'):
                continue
            full = os.path.join(dirpath, fname)
            if es_archivo_log(full):
                continue
            try:
                with open(full, 'r', encoding='utf-8', errors='ignore') as f:
                    txt = f.read()
            except Exception:
                continue
            # Coincide con class="bi bi-xxx" o class="bi bi-xxx ..."
            for m in re.finditer(r'\bbi\s+bi-([a-z0-9\-]+)', txt):
                usados.add('bi-' + m.group(1))
    return usados


# ============================================================
# PROCESO PRINCIPAL
# ============================================================
def procesar_css(css_path, iconos_necesarios):
    """
    Agrega al CSS los iconos faltantes.
    Devuelve True si modificó el archivo, False si no hubo cambios.
    """
    definidos = iconos_definidos(css_path)
    faltan = [ic for ic in iconos_necesarios
              if ic in ICONOS_FALTANTES and ic not in definidos]

    if not faltan:
        print(f"  [OK] No falta ningún icono en este CSS.")
        return False

    print(f"  [INFO] Faltan {len(faltan)} icono(s): {', '.join(faltan)}")

    # 1) Backup
    backup = css_path + SUFIJO_BACKUP
    try:
        shutil.copy2(css_path, backup)
        print(f"  [BACKUP] {backup}")
    except Exception as e:
        print(f"  [ERROR] No se pudo crear backup: {e}")
        return False

    # 2) Construir bloques nuevos
    bloques = []
    for ic in faltan:
        uri = svg_a_data_uri(ICONOS_FALTANTES[ic], ic)
        bloques.append(
            f"\n/* --- {ic} (agregado por fix_iconos.py) --- */\n"
            f".{ic} {{\n"
            f"  -webkit-mask-image: {uri};\n"
            f"  mask-image: {uri};\n"
            f"}}\n"
        )

    # 3) Leer, asegurar salto de línea final, y anexar
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            original = f.read()
        if not original.endswith('\n'):
            original += '\n'
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(original + ''.join(bloques))
    except Exception as e:
        print(f"  [ERROR] No se pudo escribir el CSS: {e}")
        # Intentar restaurar desde el backup
        try:
            shutil.copy2(backup, css_path)
            print(f"  [ROLLBACK] Se restauró el original desde el backup.")
        except Exception:
            pass
        return False

    print(f"  [OK] {len(faltan)} icono(s) agregado(s) con éxito.")
    return True


def main():
    raiz = Path.cwd()
    print("=" * 62)
    print(" fix_iconos.py  -  Corrector de iconos cuadrados (▯)")
    print("=" * 62)
    print(f"Directorio raíz : {raiz}")
    print()

    # --- PASO 1: localizar el CSS de iconos -----------------------
    print("[1] Buscando archivos '3jjja-icons-mask.css'...")
    css_files = buscar_css_iconos(str(raiz))

    if not css_files:
        print()
        print("  ✗ No se encontró '3jjja-icons-mask.css'.")
        print("    Asegurate de ejecutar este script desde la RAÍZ del proyecto")
        print("    (donde está manage.py).")
        sys.exit(1)

    for f in css_files:
        print(f"  → {f}")
    print()

    # --- PASO 2: escanear iconos usados en plantillas ------------
    print("[2] Escaneando iconos 'bi bi-*' usados en plantillas HTML...")
    usados = escanear_plantillas(str(raiz))
    print(f"  → {len(usados)} iconos distintos detectados en total.")
    faltantes_globales = usados - set().union(
        *[iconos_definidos(f) for f in css_files]
    ) if css_files else usados
    if faltantes_globales:
        print(f"  → Iconos sin definir en CSS: {', '.join(sorted(faltantes_globales))}")
    else:
        print(f"  → Todos los iconos usados ya están definidos.")
    print()

    # --- PASO 3: agregar los 4 iconos faltantes ------------------
    print("[3] Procesando cada archivo CSS...")
    modificados = 0
    for css in css_files:
        print(f"\n  → {css}")
        # Asegurar que los 4 iconos conocidos queden presentes
        if procesar_css(css, set(ICONOS_FALTANTES.keys())):
            modificados += 1
    print()

    # --- REPORTE FINAL ------------------------------------------
    print("=" * 62)
    if modificados:
        print(f" ✔ LISTO: {modificados} archivo(s) CSS actualizado(s).")
        print(f"   Los originales quedaron como:  *.css{SUFIJO_BACKUP}")
        print()
        print("   Próximos pasos:")
        print("     1) Si usás Django en producción, corré:  python manage.py collectstatic")
        print("     2) Recargá el navegador con  Ctrl + F5  (borra caché).")
        print("     3) Verificá que los iconos ya se ven (candado, ojo, info, etc).")
    else:
        print(" ✔ LISTO: no hubo cambios (los iconos ya estaban definidos).")
    print("=" * 62)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[ABORTADO] Cancelado por el usuario.")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR INESPERADO] {e}")
        sys.exit(1)