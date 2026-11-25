#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_iconos_v2.py
================
Versión BLINDADA contra backups/logs/copias.

- Filtra agresivamente archivos .bak, .log, copia, backup, etc.
- Muestra TODOS los candidatos con ruta completa antes de tocar nada.
- Pide confirmación explícita (o usa --si para no interactivo).
- Modifica TAMBIÉN staticfiles/ si existe, para que Django sirva el cambio.

USO:
    cd /ruta/al/proyecto      (donde está manage.py)
    python fix_iconos_v2.py              # interactivo
    python fix_iconos_v2.py --si         # sin preguntar
    python fix_iconos_v2.py --dry-run    # solo mostrar, no tocar
"""

import os
import re
import sys
import shutil
import argparse
from datetime import datetime
from urllib.parse import quote

# ============================================================
# FILTROS ESTRICTOS
# ============================================================
STAMP = datetime.now().strftime('%Y%m%d_%H%M%S')

# Patrones que DESCARTAN un archivo automáticamente (case-insensitive)
PATRONES_BASURA = re.compile(
    r'('
    r'\.bak($|[._\-])'            # .bak, .bak_, .bak- , .bak. 
    r'|\.backup'
    r'|\.old($|[._\-])'
    r'|\.orig($|[._\-])'
    r'|\.save($|[._\-])'
    r'|\.log($|[._\-])'
    r'|_log($|[._\-])'
    r'|-log($|[._\-])'
    r'|\.txt$'
    r'|\.md$'
    r'|~$'
    r'|\.swp$'
    r'|\.swo$'
    r'|copia'                     # "copia de ..."
    r'|backup'                    # "backup_..."
    r'|_bkp'
    r'|-bkp'
    r'|_bk\b'
    r'|-bk\b'
    r'|_copy'
    r'|-copy'
    r'|_old$'
    r'|-old$'
    r'|_v\d+$'                    # archivo_v1, archivo_v2...
    r'|\s+\(\d+\)'                # "archivo (1)"
    r')',
    re.IGNORECASE
)

# Carpetas que NO se recorren
SKIP_DIRS = {
    '.git', '.hg', '.svn',
    'node_modules', '__pycache__',
    '.venv', 'venv', 'env', '.env',
    '.idea', '.vscode',
    'media', 'migrations',
}

# Nombres EXACTOS que buscamos
NOMBRES = {
    'template_admin':   'admin_usuarios.html',
    'template_pwd':     'cambiar_password_temporal.html',
    'css_iconos':       '3jjja-icons-mask.css',
}

# ============================================================
# CONTENIDO A ESCRIBIR (resumido: solo lo esencial)
# ============================================================

# Bloque anti-conflicto + 4 iconos faltantes para el CSS de iconos
CSS_ICONOS_EXTRA = '''

/* ============================================================ */
/* ANTI-CONFLICTO: neutraliza el ::before de bootstrap-icons     */
/* (agregado por fix_iconos_v2.py)                               */
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

/* ============================================================ */
/* Iconos faltantes (agregados por fix_iconos_v2.py)             */
/* ============================================================ */
.bi-lock-fill {
  -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M8%201a2%202%200%200%201%202%202v4H6V3a2%202%200%200%201%202-2m3%206V3a3%203%200%200%200-6%200v4a2%202%200%200%200-2%202v5a2%202%200%200%200%202%202h6a2%202%200%200%200%202-2V9a2%202%200%200%200-2-2%22%2F%3E%3C%2Fsvg%3E");
  mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M8%201a2%202%200%200%201%202%202v4H6V3a2%202%200%200%201%202-2m3%206V3a3%203%200%200%200-6%200v4a2%202%200%200%200-2%202v5a2%202%200%200%200%202%202h6a2%202%200%200%200%202-2V9a2%202%200%200%200-2-2%22%2F%3E%3C%2Fsvg%3E");
}
.bi-unlock-fill {
  -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M11%201a2%202%200%200%200-2%202v4a2%202%200%200%201%202%202v5a2%202%200%200%201-2%202H3a2%202%200%200%201-2-2V9a2%202%200%200%201%202-2h5V3a3%203%200%200%201%206%200v4a.5.5%200%200%201-1%200V3a2%202%200%200%200-2-2%22%2F%3E%3C%2Fsvg%3E");
  mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M11%201a2%202%200%200%200-2%202v4a2%202%200%200%201%202%202v5a2%202%200%200%201-2%202H3a2%202%200%200%201-2-2V9a2%202%200%200%201%202-2h5V3a3%203%200%200%201%206%200v4a.5.5%200%200%201-1%200V3a2%202%200%200%200-2-2%22%2F%3E%3C%2Fsvg%3E");
}
.bi-info-circle-fill {
  -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M8%2016A8%208%200%201%200%208%200a8%208%200%200%200%200%2016m.93-9.412-1%204.705c-.07.34.029.533.304.533.194%200%20.487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703%200-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381%202.29-.287zM8%205.5a1%201%200%201%201%200-2%201%201%200%200%201%200%202%22%2F%3E%3C%2Fsvg%3E");
  mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M8%2016A8%208%200%201%200%208%200a8%208%200%200%200%200%2016m.93-9.412-1%204.705c-.07.34.029.533.304.533.194%200%20.487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703%200-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381%202.29-.287zM8%205.5a1%201%200%201%201%200-2%201%201%200%200%201%200%202%22%2F%3E%3C%2Fsvg%3E");
}
.bi-eye-slash {
  -webkit-mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M13.359%2011.238C15.06%209.72%2016%208%2016%208s-3-5.5-8-5.5a7%207%200%200%200-2.79.588l.77.771A6%206%200%200%201%208%203.5c2.12%200%203.879%201.168%205.168%202.457A13%2013%200%200%201%2014.828%208q-.086.13-.195.288c-.335.48-.83%201.12-1.465%201.755q-.27.275-.57.535zM11.297%209.176a3.5%203.5%200%200%200-4.474-4.474l.823.823a2.5%202.5%200%200%201%202.829%202.829zm-2.943%201.299.822.822a3.5%203.5%200%200%201-4.474-4.474l.823.823a2.5%202.5%200%200%200%202.829%202.829%22%2F%3E%3Cpath%20d%3D%22M3.35%205.47q-.27.24-.518.487A13%2013%200%200%200%201.172%208l.195.288c.335.48.83%201.12%201.465%201.755C4.121%2011.332%205.881%2012.5%208%2012.5c.716%200%201.39-.133%202.02-.36l.77.772A7%207%200%200%201%208%2013.5C3%2013.5%200%208%200%208s.939-1.721%202.641-3.238l.708.709zm10.296%208.884-12-12%20.708-.708%2012%2012z%22%2F%3E%3C%2Fsvg%3E");
  mask-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22currentColor%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M13.359%2011.238C15.06%209.72%2016%208%2016%208s-3-5.5-8-5.5a7%207%200%200%200-2.79.588l.77.771A6%206%200%200%201%208%203.5c2.12%200%203.879%201.168%205.168%202.457A13%2013%200%200%201%2014.828%208q-.086.13-.195.288c-.335.48-.83%201.12-1.465%201.755q-.27.275-.57.535zM11.297%209.176a3.5%203.5%200%200%200-4.474-4.474l.823.823a2.5%202.5%200%200%201%202.829%202.829zm-2.943%201.299.822.822a3.5%203.5%200%200%201-4.474-4.474l.823.823a2.5%202.5%200%200%200%202.829%202.829%22%2F%3E%3Cpath%20d%3D%22M3.35%205.47q-.27.24-.518.487A13%2013%200%200%200%201.172%208l.195.288c.335.48.83%201.12%201.465%201.755C4.121%2011.332%205.881%2012.5%208%2012.5c.716%200%201.39-.133%202.02-.36l.77.772A7%207%200%200%201%208%2013.5C3%2013.5%200%208%200%208s.939-1.721%202.641-3.238l.708.709zm10.296%208.884-12-12%20.708-.708%2012%2012z%22%2F%3E%3C%2Fsvg%3E");
}
'''


# ============================================================
# UTILIDADES
# ============================================================
def es_basura(nombre_archivo):
    """True si el nombre del archivo parece backup/log/copia."""
    return bool(PATRONES_BASURA.search(nombre_archivo))


def buscar_exacto(nombre_archivo, raiz, incluir_staticfiles=True):
    """
    Busca archivos con nombre EXACTO. Excluye basura, .git, etc.
    Devuelve lista de rutas absolutas encontradas.
    """
    encontrados = []
    for dp, dn, fn in os.walk(raiz):
        # Ignorar dirs
        skip = set(SKIP_DIRS)
        if not incluir_staticfiles:
            skip.add('staticfiles')
        dn[:] = [d for d in dn if d not in skip]

        if nombre_archivo in fn:
            full = os.path.join(dp, nombre_archivo)
            # Filtro final: solo si el nombre exacto NO es basura
            if not es_basura(nombre_archivo):
                encontrados.append(full)
    return encontrados


def tamanio_legible(path):
    try:
        n = os.path.getsize(path)
        for u in ('B', 'KB', 'MB'):
            if n < 1024:
                return f"{n:.0f} {u}"
            n /= 1024
        return f"{n:.1f} GB"
    except OSError:
        return "?"


def fecha_mod(path):
    try:
        ts = os.path.getmtime(path)
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
    except OSError:
        return "?"


def backup(path):
    bak = f"{path}.bak_{STAMP}"
    try:
        shutil.copy2(path, bak)
        return bak
    except Exception as e:
        print(f"      ⚠ No se pudo crear backup: {e}")
        return None


def escribir(path, contenido, dry=False):
    if dry:
        print(f"      [DRY-RUN] escribiría {path}")
        return True

    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    if os.path.isfile(path):
        bak = backup(path)
        if bak:
            print(f"      ✓ Backup: {os.path.basename(bak)}")

    try:
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(contenido)
        return True
    except Exception as e:
        print(f"      ✗ ERROR escribiendo: {e}")
        return False


# ============================================================
# DIAGNÓSTICO
# ============================================================
def diagnostico(raiz):
    """Muestra qué archivos hay para cada nombre buscado."""
    print("=" * 70)
    print(" DIAGNÓSTICO")
    print("=" * 70)
    print(f"Raíz: {raiz}\n")

    resultados = {}
    for clave, nombre in NOMBRES.items():
        print(f"→ Buscando '{nombre}'...")
        encontrados = buscar_exacto(nombre, raiz, incluir_staticfiles=True)

        # También listar los que fueron descartados (para transparencia)
        descartados = []
        for dp, dn, fn in os.walk(raiz):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            for f in fn:
                if nombre.lower() in f.lower() and f != nombre:
                    descartados.append(os.path.join(dp, f))

        if not encontrados:
            print(f"   ✗ No encontré ningún '{nombre}' válido.")
        else:
            print(f"   ✓ {len(encontrados)} archivo(s) válido(s):")
            for i, p in enumerate(encontrados, 1):
                rel = os.path.relpath(p, raiz)
                print(f"      {i}. {rel}")
                print(f"         tamaño={tamanio_legible(p)}  mod={fecha_mod(p)}")

        if descartados:
            print(f"   ⓘ {len(descartados)} archivo(s) descartado(s) por parecer copia/log:")
            for p in descartados[:10]:
                print(f"      - {os.path.relpath(p, raiz)}")
            if len(descartados) > 10:
                print(f"      ... y {len(descartados) - 10} más")

        resultados[clave] = encontrados
        print()

    # Detección de conflicto static/ vs staticfiles/
    print("→ Verificando conflicto static/ vs staticfiles/...")
    css_static = [p for p in resultados.get('css_iconos', [])
                  if os.sep + 'static' + os.sep in p
                  and os.sep + 'staticfiles' + os.sep not in p]
    css_staticfiles = [p for p in resultados.get('css_iconos', [])
                       if os.sep + 'staticfiles' + os.sep in p]

    if css_static and css_staticfiles:
        print(f"   ⚠ HAY CONFLICTO:")
        print(f"      - static/:      {len(css_static)} copia(s)")
        print(f"      - staticfiles/: {len(css_staticfiles)} copia(s)")
        print(f"      Django sirve desde staticfiles/. El script debe actualizar AMBOS.")
    elif css_static and not css_staticfiles:
        print(f"   ⓘ Solo hay en static/. Ejecutá collectstatic después.")
    elif css_staticfiles and not css_static:
        print(f"   ⚠ Solo hay en staticfiles/. ¡Falta el original en static/!")
    else:
        print(f"   ✗ No se encontró el CSS de iconos en ningún lado.")

    print()
    return resultados


# ============================================================
# APLICAR
# ============================================================
def aplicar_css_iconos(paths, dry=False):
    """Añade bloque anti-conflicto + iconos faltantes al CSS."""
    print(f"\n[CSS DE ICONOS]  {len(paths)} archivo(s)")
    ok = 0
    for p in paths:
        print(f"  → {os.path.relpath(p)}")

        if dry:
            print(f"      [DRY-RUN] añadiría bloque extra")
            ok += 1
            continue

        try:
            with open(p, 'r', encoding='utf-8') as f:
                txt = f.read()
        except Exception as e:
            print(f"      ✗ No se pudo leer: {e}")
            continue

        # Si ya tiene el bloque, no lo duplicamos
        if 'fix_iconos_v2.py' in txt and 'ANTI-CONFLICTO' in txt:
            print(f"      ⓘ Ya tiene el bloque aplicado. Sin cambios.")
            ok += 1
            continue

        if not txt.endswith('\n'):
            txt += '\n'
        txt += CSS_ICONOS_EXTRA

        if escribir(p, txt, dry=dry):
            print(f"      ✓ Actualizado")
            ok += 1
    return ok


def aplicar_template(paths, contenido, etiqueta, dry=False):
    """Reemplaza un template con el contenido nuevo."""
    print(f"\n[{etiqueta}]  {len(paths)} archivo(s)")
    ok = 0
    for p in paths:
        print(f"  → {os.path.relpath(p)}")
        # Detectar si ya tiene SVG inline (por si ya se aplicó antes)
        try:
            with open(p, 'r', encoding='utf-8') as f:
                txt = f.read()
            if '<svg' in txt and 'aria-hidden="true"' in txt and 'bi bi-' not in txt:
                print(f"      ⓘ Ya parece tener SVG inline. Sin cambios.")
                ok += 1
                continue
        except Exception:
            pass

        if escribir(p, contenido, dry=dry):
            print(f"      ✓ Actualizado")
            ok += 1
    return ok


# ============================================================
# PLANTILLAS DE TEMPLATES (importadas de un módulo aparte)
# ============================================================
def cargar_contenidos():
    """
    Importa los contenidos de template desde el módulo
    'contenidos_fix_iconos' si existe en el directorio actual.
    Si no, devuelve None y avisa.
    """
    try:
        sys.path.insert(0, os.getcwd())
        import contenidos_fix_iconos as C
        return C
    except ImportError:
        return None


# ============================================================
# MAIN
# ============================================================
def main():
    ap = argparse.ArgumentParser(description='Fix de iconos blindado.')
    ap.add_argument('--si', action='store_true',
                    help='No pedir confirmación (auto-aplicar).')
    ap.add_argument('--dry-run', action='store_true',
                    help='Solo mostrar, no tocar nada.')
    ap.add_argument('--solo-diag', action='store_true',
                    help='Solo diagnóstico, no aplicar.')
    ap.add_argument('--solo-static', action='store_true',
                    help='Solo actualizar static/css/3jjja-icons-mask.css.')
    args = ap.parse_args()

    raiz = os.getcwd()
    print()
    if not os.path.isfile(os.path.join(raiz, 'manage.py')):
        print("⚠  No encuentro 'manage.py' aquí. ¿Estás en la raíz del proyecto?")
        if not args.si:
            r = input("   ¿Continuar igual? [s/N]: ").strip().lower()
            if r != 's':
                return 1

    # ---- DIAGNÓSTICO ----
    encontrados = diagnostico(raiz)

    if args.solo_diag:
        return 0

    # ---- CARGAR CONTENIDOS DE TEMPLATES ----
    C = cargar_contenidos()
    if not C:
        print("✗ Falta el archivo 'contenidos_fix_iconos.py' en el directorio actual.")
        print("  Copialo y volvé a ejecutar.")
        return 2

    # ---- RESUMEN DE LO QUE SE HARÁ ----
    print("=" * 70)
    print(" PLAN DE ACCIÓN")
    print("=" * 70)
    css_paths = encontrados.get('css_iconos', [])
    tpl_admin = encontrados.get('template_admin', [])
    tpl_pwd   = encontrados.get('template_pwd', [])

    print(f"  CSS de iconos:                {len(css_paths)} archivo(s)")
    for p in css_paths:
        print(f"     - {os.path.relpath(p, raiz)}")
    print(f"  Template admin_usuarios:      {len(tpl_admin)} archivo(s)")
    for p in tpl_admin:
        print(f"     - {os.path.relpath(p, raiz)}")
    print(f"  Template cambiar_password:    {len(tpl_pwd)} archivo(s)")
    for p in tpl_pwd:
        print(f"     - {os.path.relpath(p, raiz)}")
    print()

    if args.solo_static:
        aplicar_css_iconos(css_paths, dry=args.dry_run)
        return 0

    # ---- CONFIRMACIÓN ----
    if not args.si and not args.dry_run:
        print("¿Aplicar los cambios a estos archivos?")
        print("  (Se hará backup de cada uno antes de tocarlo)")
        r = input("  Escribí 'SI' (mayúsculas) para confirmar: ").strip()
        if r != 'SI':
            print("Cancelado.")
            return 0

    # ---- APLICAR ----
    print()
    print("=" * 70)
    print(" APLICANDO")
    print("=" * 70)

    total = 0
    total += aplicar_css_iconos(css_paths, dry=args.dry_run)
    total += aplicar_template(tpl_admin, C.TEMPLATE_ADMIN_USUARIOS,
                              'TEMPLATE admin_usuarios.html', dry=args.dry_run)
    total += aplicar_template(tpl_pwd, C.TEMPLATE_CAMBIAR_PWD,
                              'TEMPLATE cambiar_password_temporal.html', dry=args.dry_run)

    # ---- REPORTE ----
    print()
    print("=" * 70)
    print(f" ✔ LISTO. {total} archivo(s) procesado(s).")
    print(f" Backups con sufijo: .bak_{STAMP}")
    print()
    print(" IMPORTANTE — Para que Django sirva los cambios:")
    print("   1) python manage.py collectstatic --noinput")
    print("   2) Si tenés 'staticfiles/' en el proyecto, borralo ANTES de collectstatic:")
    print("      rm -rf staticfiles/")
    print("   3) En el navegador: Ctrl + Shift + R  (recarga forzada, limpia caché)")
    print("   4) Abrí DevTools (F12) → Network → recargá → buscá '3jjja-icons-mask.css'")
    print("      y confirmá que tiene el bloque nuevo al final.")
    print("=" * 70)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nCancelado.")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)