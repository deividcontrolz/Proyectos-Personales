#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
actualizar_login_iconos.py
--------------------------
Script de un solo uso que aplica al Sistema 3-JJJ-A:

  1. Copia de seguridad (.bak_YYYYMMDD_HHMMSS) de:
        - templates/registration/login.html
        - static/css/login.css
        - static/js/login.js

  2. Reemplaza los iconos <i class="bi bi-eye / bi-eye-slash"> por SVGs
     inline (integrados en el propio HTML), eliminando la dependencia de
     Bootstrap Icons SOLO para el boton de ver/ocultar contraseña.

  3. Ajusta el CSS del campo de contraseña para que el boton del ojo
     quede correctamente alineado y NO tape el placeholder
     ("Ingrese su contrasena").

  4. Actualiza login.js para alternar entre los SVGs (ojo abierto / cerrado).

NO modifica modelos, vistas, urls, formularios ni ningun otro archivo del
sistema. NO toca los iconos bi-* del resto de la plantilla.
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


# ============================================================
# LOCALIZACION DE ARCHIVOS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
CORE_DIR = BASE_DIR / 'core'


def primer_existente(rutas):
    for p in rutas:
        if p.exists():
            return p
    return None


LOGIN_HTML = primer_existente([
    CORE_DIR / 'templates' / 'registration' / 'login.html',
    BASE_DIR / 'templates' / 'registration' / 'login.html',
])

LOGIN_CSS = primer_existente([
    CORE_DIR / 'static' / 'css' / 'login.css',
    BASE_DIR / 'static' / 'css' / 'login.css',
])

LOGIN_JS = primer_existente([
    CORE_DIR / 'static' / 'js' / 'login.js',
    BASE_DIR / 'static' / 'js' / 'login.js',
])


# ============================================================
# UTILIDADES
# ============================================================
def backup(path):
    if not path or not path.exists():
        return None
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino = path.with_name(path.name + f'.bak_{ts}')
    shutil.copy2(path, destino)
    return destino


def abrir(p):
    return p.read_text(encoding='utf-8')


def escribir(p, c):
    p.write_text(c, encoding='utf-8')


# ============================================================
# PASO 1: HTML -> SVGs inline en lugar de <i class="bi bi-eye">
# ============================================================
SVGS_INLINE = (
    '<svg class="eye-icon eye-open" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>'
    '<circle cx="12" cy="12" r="3"/>'
    '</svg>\n'
    '                                '
    '<svg class="eye-icon eye-closed" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 '
    '18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 '
    '18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>'
    '<line x1="1" y1="1" x2="23" y2="23"/>'
    '</svg>'
)

# Posibles variantes del icono viejo (con/sin espacios, en linea o multilinea)
PATRONES_VIEJO = [
    r'<i\s+class="bi\s+bi-eye"\s*></i>',
    r'<i\s+class="bi\s+bi-eye"\s*/>',
]


def actualizar_html():
    html = abrir(LOGIN_HTML)
    reemplazado = False

    for pat in PATRONES_VIEJO:
        nuevo_html, n = re.subn(pat, SVGS_INLINE, html)
        if n > 0:
            html = nuevo_html
            reemplazado = True
            break

    if not reemplazado:
        # Puede que ya se haya actualizado antes
        if 'eye-icon eye-open' in html:
            print('  [!] login.html ya contiene los SVGs inline. Nada que hacer.')
            return
        raise RuntimeError(
            'No se encontro el icono <i class="bi bi-eye"></i> en login.html. '
            'Revisa el archivo manualmente.'
        )

    escribir(LOGIN_HTML, html)
    print('  [+] login.html: boton del ojo convertido a SVG inline.')


# ============================================================
# PASO 2: CSS -> corregir posicionamiento y estilos del ojo
# ============================================================
CSS_VIEJO = '''.password-input-wrapper input {
            padding-right: 42px;
        }
        .toggle-password-btn {
            position: absolute;
            right: 12px;
            background: transparent;
            border: none;
            color: #94a3b8;
            cursor: pointer;
            font-size: 1.1rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 4px;
            transition: color 0.2s ease;
            z-index: 2;
        }
        .toggle-password-btn:hover {
            color: #10b981;
        }'''

CSS_NUEVO = '''.password-input-wrapper input {
            padding-right: 52px;
        }
        .toggle-password-btn {
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            background: transparent;
            border: none;
            color: #94a3b8;
            cursor: pointer;
            width: 32px;
            height: 32px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0;
            margin: 0;
            line-height: 0;
            transition: color 0.2s ease;
            z-index: 3;
        }
        .toggle-password-btn:hover {
            color: #10b981;
        }
        .toggle-password-btn:focus {
            outline: none;
        }
        .toggle-password-btn .eye-icon {
            width: 20px;
            height: 20px;
            display: block;
            pointer-events: none;
            flex-shrink: 0;
        }
        .toggle-password-btn .eye-closed {
            display: none;
        }'''


def actualizar_css():
    css = abrir(LOGIN_CSS)

    if CSS_VIEJO not in css:
        if '.toggle-password-btn .eye-icon' in css:
            print('  [!] login.css ya tiene los estilos nuevos. Nada que hacer.')
            return
        raise RuntimeError(
            'No se encontro el bloque CSS esperado para el boton del ojo. '
            'Asegurate de que login.css conserva el formato original.'
        )

    css = css.replace(CSS_VIEJO, CSS_NUEVO)
    escribir(LOGIN_CSS, css)
    print('  [+] login.css: boton del ojo re-alineado y sin solapar el placeholder.')


# ============================================================
# PASO 3: JS -> alternar SVGs en lugar de clases bi-*
# ============================================================
JS_NUEVO = '''/* login.js
   Alterna la visibilidad de la contraseña y el icono del ojo.
   Los iconos son SVG inline (no dependen de librerias externas).
*/
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.toggle-password-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();

            var wrapper = this.closest('.password-input-wrapper');
            var input = wrapper ? wrapper.querySelector('input') : null;
            if (!input) { return; }

            var eyeOpen = this.querySelector('.eye-open');
            var eyeClosed = this.querySelector('.eye-closed');

            if (input.type === 'password') {
                input.type = 'text';
                if (eyeOpen)   { eyeOpen.style.display = 'none'; }
                if (eyeClosed) { eyeClosed.style.display = 'block'; }
            } else {
                input.type = 'password';
                if (eyeOpen)   { eyeOpen.style.display = 'block'; }
                if (eyeClosed) { eyeClosed.style.display = 'none'; }
            }
        });
    });
});
'''


def actualizar_js():
    escribir(LOGIN_JS, JS_NUEVO)
    print('  [+] login.js: logica actualizada para alternar SVGs inline.')


# ============================================================
# MAIN
# ============================================================
def main():
    print('=' * 60)
    print(' ACTUALIZACION ICONOS DEL LOGIN - Sistema 3-JJJ-A')
    print('=' * 60)

    faltantes = []
    if not LOGIN_HTML: faltantes.append('templates/registration/login.html')
    if not LOGIN_CSS:  faltantes.append('static/css/login.css')
    if not LOGIN_JS:   faltantes.append('static/js/login.js')

    if faltantes:
        print('ERROR: No se encontraron los siguientes archivos:')
        for f in faltantes:
            print('   -', f)
        print('\nEjecuta el script desde la RAIZ del proyecto (donde esta manage.py).')
        sys.exit(1)

    print(f'\nProyecto detectado en: {BASE_DIR}')
    print(f'HTML : {LOGIN_HTML.relative_to(BASE_DIR)}')
    print(f'CSS  : {LOGIN_CSS.relative_to(BASE_DIR)}')
    print(f'JS   : {LOGIN_JS.relative_to(BASE_DIR)}')

    # Backup
    print('\n[1/4] Creando copias de seguridad...')
    for ruta in (LOGIN_HTML, LOGIN_CSS, LOGIN_JS):
        bak = backup(ruta)
        if bak:
            print(f'  [+] {ruta.name}  ->  {bak.name}')

    # Cambios
    print('\n[2/4] Actualizando HTML (SVG inline)...')
    actualizar_html()

    print('\n[3/4] Ajustando CSS (sin solapamiento)...')
    actualizar_css()

    print('\n[4/4] Reescribiendo JS...')
    actualizar_js()

    print('\n' + '=' * 60)
    print(' LISTO. Cambios aplicados correctamente.')
    print('=' * 60)
    print('\nResumen:')
    print('  * El boton del ojo ya no depende de Bootstrap Icons.')
    print('  * Los iconos (ojo abierto / cerrado) son SVG inline en el HTML.')
    print('  * El padding del input y el boton han sido re-ajustados para')
    print('    que el icono NO tape el placeholder "Ingrese su contrasena".')
    print('  * El resto de iconos bi-* del sistema siguen intactos.')
    print('\nReinicia el servidor Django y recarga con Ctrl+F5 (cache).')
    print('=' * 60)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'\n[ERROR] {e}')
        sys.exit(1)