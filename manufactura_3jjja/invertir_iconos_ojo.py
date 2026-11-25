#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
invertir_iconos_ojo.py
----------------------
Invierte la logica visual de los iconos de mostrar/ocultar contraseña
en TODO el sistema 3-JJJ-A:

    * Contraseña OCULTA  ->  icono OJO CON RAYA (tachado)
    * Contraseña VISIBLE ->  icono OJO ABIERTO (sin raya)

Archivos afectados:
    - core/static/js/login.js
    - core/static/css/login.css
    - core/static/js/app.js
    - core/templates/registration/cambiar_password_temporal.html

Hace copia de seguridad (.bak_YYYYMMDD_HHMMSS) de cada archivo ANTES de
modificarlo. No toca vistas, modelos, urls ni ningun otro archivo.
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CORE_DIR = BASE_DIR / 'core'


def primer_existente(rutas):
    for p in rutas:
        if p.exists():
            return p
    return None


def backup(path):
    if not path or not path.exists():
        return None
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = path.with_name(path.name + f'.bak_{ts}')
    shutil.copy2(path, dst)
    return dst


def leer(p):
    return p.read_text(encoding='utf-8')


def escribir(p, c):
    p.write_text(c, encoding='utf-8')


# -------- Localizar archivos --------
LOGIN_JS = primer_existente([
    CORE_DIR / 'static' / 'js' / 'login.js',
    BASE_DIR / 'static' / 'js' / 'login.js',
])
LOGIN_CSS = primer_existente([
    CORE_DIR / 'static' / 'css' / 'login.css',
    BASE_DIR / 'static' / 'css' / 'login.css',
])
APP_JS = primer_existente([
    CORE_DIR / 'static' / 'js' / 'app.js',
    BASE_DIR / 'static' / 'js' / 'app.js',
])
CAMBIAR_HTML = primer_existente([
    CORE_DIR / 'templates' / 'registration' / 'cambiar_password_temporal.html',
    BASE_DIR / 'templates' / 'registration' / 'cambiar_password_temporal.html',
])


# ============================================================
# 1) login.js  ->  invertir toggle
# ============================================================
NUEVO_LOGIN_JS = '''/* login.js
   Alterna la visibilidad de la contraseña y el icono del ojo.
   Regla visual:
       Contraseña OCULTA  ->  ojo CON RAYA (tachado)
       Contraseña VISIBLE ->  ojo ABIERTO (sin raya)
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
                // pasa de OCULTA a VISIBLE -> mostrar OJO ABIERTO
                input.type = 'text';
                if (eyeOpen)   { eyeOpen.style.display = 'block'; }
                if (eyeClosed) { eyeClosed.style.display = 'none'; }
            } else {
                // pasa de VISIBLE a OCULTA -> mostrar OJO CON RAYA
                input.type = 'password';
                if (eyeOpen)   { eyeOpen.style.display = 'none'; }
                if (eyeClosed) { eyeClosed.style.display = 'block'; }
            }
        });
    });
});
'''


def actualizar_login_js():
    escribir(LOGIN_JS, NUEVO_LOGIN_JS)
    print('  [+] login.js: logica del ojo invertida.')


# ============================================================
# 2) login.css  ->  por defecto mostrar OJO CON RAYA
# ============================================================
def actualizar_login_css():
    css = leer(LOGIN_CSS)

    # Busqueda flexible por regex: bloque ".toggle-password-btn .eye-closed { display:none }"
    patron_viejo = re.compile(
        r'\.toggle-password-btn\s+\.eye-closed\s*\{\s*display\s*:\s*none\s*;?\s*\}',
        re.DOTALL
    )
    patron_nuevo_ya = re.compile(
        r'\.toggle-password-btn\s+\.eye-open\s*\{\s*display\s*:\s*none\s*;?\s*\}',
        re.DOTALL
    )

    if patron_viejo.search(css):
        css = patron_viejo.sub(
            '.toggle-password-btn .eye-open {\n            display: none;\n        }',
            css, count=1
        )
        escribir(LOGIN_CSS, css)
        print('  [+] login.css: por defecto ahora se muestra el OJO CON RAYA.')
        return

    if patron_nuevo_ya.search(css):
        print('  [!] login.css ya estaba invertido.')
        return

    raise RuntimeError(
        'No se encontro el bloque ".toggle-password-btn .eye-closed" en login.css.'
    )


# ============================================================
# 3) app.js  ->  invertir toggle + inicializar icono
# ============================================================
def actualizar_app_js():
    contenido = leer(APP_JS)

    # --- a) Invertir la logica del toggle ---
    viejo = 'this.innerHTML = isPassword ? eyeOffSVG : eyeSVG;'
    nuevo = 'this.innerHTML = isPassword ? eyeSVG : eyeOffSVG;'
    if viejo in contenido:
        contenido = contenido.replace(viejo, nuevo, 1)
        print('  [+] app.js: logica del toggle invertida.')
    elif nuevo in contenido:
        print('  [!] app.js: el toggle ya estaba invertido.')
    else:
        raise RuntimeError('No se encontro la linea del toggle en app.js.')

    # --- b) Agregar inicializacion: password oculta -> ojo con raya ---
    if 'toggleButtons.forEach' in contenido and 'eyeOffSVG;\n        }\n    });' not in contenido:
        # Buscar el cierre del bloque toggleButtons.forEach dentro de DOMContentLoaded
        patron_cierre = re.compile(
            r'(\n\s*\}\);\s*\n\s*\}\);\s*\n\s*\}\);\s*\n)',
            re.DOTALL
        )
        # Localizar el primer cierre que viene despues de "toggleButtons.forEach"
        pos = contenido.find('toggleButtons.forEach')
        if pos == -1:
            print('  [!] app.js: no se encontro toggleButtons.forEach para inicializar.')
            escribir(APP_JS, contenido)
            return

        m = patron_cierre.search(contenido, pos)
        if not m:
            print('  [!] app.js: no se pudo localizar el cierre del bloque.')
            escribir(APP_JS, contenido)
            return

        cierre = m.group(1)
        bloque_inicializacion = (
            '\n    // Inicializacion: los campos de contraseña arrancan OCULTOS,\n'
            '    // por lo tanto mostramos el OJO CON RAYA desde el inicio.\n'
            '    toggleButtons.forEach(function (btn) {\n'
            '        var wrapper = btn.closest(\'.password-wrapper\');\n'
            '        if (!wrapper) return;\n'
            '        var input = wrapper.querySelector(\'input\');\n'
            '        if (input && input.getAttribute(\'type\') === \'password\') {\n'
            '            btn.innerHTML = eyeOffSVG;\n'
            '        }\n'
            '    });\n' + cierre
        )

        contenido = contenido[:m.start(1)] + bloque_inicializacion + contenido[m.end(1):]
        print('  [+] app.js: inicializacion de icono (ojo con raya por defecto) agregada.')

    escribir(APP_JS, contenido)


# ============================================================
# 4) cambiar_password_temporal.html  ->  invertir togglePass()
# ============================================================
def actualizar_cambiar_password():
    html = leer(CAMBIAR_HTML)

    # --- a) Invertir la funcion togglePass (flexible a formato) ---
    patron_js = re.compile(
        r"if\s*\(\s*input\.type\s*===\s*'password'\s*\)\s*\{\s*"
        r"input\.type\s*=\s*'text'\s*;\s*"
        r"icon\.className\s*=\s*'bi\s+bi-eye-slash'\s*;\s*"
        r"\}\s*else\s*\{\s*"
        r"input\.type\s*=\s*'password'\s*;\s*"
        r"icon\.className\s*=\s*'bi\s+bi-eye'\s*;\s*"
        r"\}",
        re.DOTALL
    )

    reemplazo_js = (
        "if (input.type === 'password') {\n"
        "                // pasa de OCULTA a VISIBLE -> OJO ABIERTO\n"
        "                input.type = 'text';\n"
        "                icon.className = 'bi bi-eye';\n"
        "            } else {\n"
        "                // pasa de VISIBLE a OCULTA -> OJO CON RAYA\n"
        "                input.type = 'password';\n"
        "                icon.className = 'bi bi-eye-slash';\n"
        "            }"
    )

    if patron_js.search(html):
        html = patron_js.sub(reemplazo_js, html, count=1)
        print('  [+] cambiar_password_temporal.html: logica de togglePass invertida.')
    else:
        # Ya podria estar invertida
        patron_ya = re.compile(
            r"if\s*\(\s*input\.type\s*===\s*'password'\s*\)\s*\{\s*"
            r"input\.type\s*=\s*'text'\s*;\s*"
            r"icon\.className\s*=\s*'bi\s+bi-eye'\s*;\s*"
            r"\}\s*else\s*\{\s*"
            r"input\.type\s*=\s*'password'\s*;\s*"
            r"icon\.className\s*=\s*'bi\s+bi-eye-slash'\s*;\s*"
            r"\}",
            re.DOTALL
        )
        if patron_ya.search(html):
            print('  [!] cambiar_password_temporal.html: togglePass ya estaba invertido.')
        else:
            raise RuntimeError(
                'No se encontro la funcion togglePass en cambiar_password_temporal.html.'
            )

    # --- b) Icono inicial: como el campo arranca OCULTO, mostrar bi-eye-slash ---
    #     Solo reemplazamos los <i class="bi bi-eye"></i> DENTRO de los
    #     botones .toggle-password-btn para no tocar otros iconos.
    patron_icono_btn = re.compile(
        r'(<button[^>]*class="toggle-password-btn"[^>]*>\s*)'
        r'<i\s+class="bi\s+bi-eye"\s*></i>',
        re.DOTALL
    )
    html, n = patron_icono_btn.subn(
        r'\1<i class="bi bi-eye-slash"></i>',
        html
    )
    if n:
        print(f'  [+] cambiar_password_temporal.html: {n} icono(s) iniciales -> ojo con raya.')

    escribir(CAMBIAR_HTML, html)


# ============================================================
# MAIN
# ============================================================
def main():
    print('=' * 60)
    print(' INVERTIR ICONO DEL OJO - Sistema 3-JJJ-A')
    print('=' * 60)

    faltantes = []
    if not LOGIN_JS:     faltantes.append('static/js/login.js')
    if not LOGIN_CSS:    faltantes.append('static/css/login.css')
    if not APP_JS:       faltantes.append('static/js/app.js')
    if not CAMBIAR_HTML: faltantes.append('templates/registration/cambiar_password_temporal.html')

    if faltantes:
        print('ERROR: No se encontraron los siguientes archivos:')
        for f in faltantes:
            print('   -', f)
        print('\nEjecuta este script desde la RAIZ del proyecto (donde esta manage.py).')
        sys.exit(1)

    print(f'\nProyecto: {BASE_DIR}')

    # ---- Backups ----
    print('\n[1/5] Creando copias de seguridad...')
    for nombre, ruta in (
        ('login.js',                        LOGIN_JS),
        ('login.css',                       LOGIN_CSS),
        ('app.js',                          APP_JS),
        ('cambiar_password_temporal.html',  CAMBIAR_HTML),
    ):
        bak = backup(ruta)
        if bak:
            print(f'  [+] {nombre}  ->  {bak.name}')

    # ---- Cambios ----
    print('\n[2/5] Actualizando login.js...')
    actualizar_login_js()

    print('\n[3/5] Actualizando login.css...')
    actualizar_login_css()

    print('\n[4/5] Actualizando app.js...')
    actualizar_app_js()

    print('\n[5/5] Actualizando cambiar_password_temporal.html...')
    actualizar_cambiar_password()

    print('\n' + '=' * 60)
    print(' LISTO. Iconos del ojo invertidos en TODO el sistema.')
    print('=' * 60)
    print('\nComportamiento nuevo (en TODOS los campos de contraseña):')
    print('  * Contraseña OCULTA  ->  OJO CON RAYA  (tachado)')
    print('  * Contraseña VISIBLE ->  OJO ABIERTO   (sin raya)')
    print('\nAplicado en:')
    print('  * Login                       (login.js / login.css)')
    print('  * Registro de usuario         (app.js)')
    print('  * Cambio de contraseña temp.  (cambiar_password_temporal.html)')
    print('\nReinicia Django y recarga con Ctrl+F5 (cache del navegador).')
    print('=' * 60)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'\n[ERROR] {e}')
        sys.exit(1)