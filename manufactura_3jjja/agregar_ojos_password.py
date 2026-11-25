#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agregar_ojos_password.py
------------------------
Agrega el boton de mostrar/ocultar contraseña (con SVG inline, sin
librerias externas) a los campos de contraseña que aun NO lo tienen:

    - templates/registration/registro.html       (password1, password2)
    - templates/admin/admin_usuarios.html        (modal: nueva_password,
                                                  confirmar_password)

Ademas corrige un pequeño bug en static/js/app.js: el bloque de
inicializacion de iconos quedo anidado por error dentro del handler del
click, lo cual hacia que los iconos solo se inicializaran al primer click.
Se mueve al nivel correcto.

Reglas visuales (ya aplicadas al resto del sistema):
    Contraseña OCULTA  ->  ojo CON RAYA (tachado)
    Contraseña VISIBLE ->  ojo ABIERTO  (sin raya)

Hace copia de seguridad (.bak_YYYYMMDD_HHMMSS) de cada archivo antes
de modificarlo. NO toca vistas, modelos, urls, formularios ni ningun
otro archivo del sistema.
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CORE_DIR = BASE_DIR / 'core'


# ============================================================
# UTILIDADES
# ============================================================
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


def encontrar(nombre):
    """Busca un archivo por nombre dentro de core/ o la raiz."""
    for base in (CORE_DIR, BASE_DIR):
        if base.exists():
            for f in base.rglob(nombre):
                if f.is_file() and '.bak_' not in f.name:
                    return f
    return None


# ============================================================
# SVG INLINE (ojo con raya — estado inicial por estar OCULTO)
# ============================================================
SVG_EYE_CLOSED = (
    '<svg class="eye-icon eye-closed" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 '
    '18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 '
    '18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>'
    '<line x1="1" y1="1" x2="23" y2="23"/>'
    '</svg>'
)


def boton_ojo(indent):
    """Devuelve el bloque completo del boton con el SVG inline."""
    return (
        f'{indent}<button type="button" class="toggle-password-btn" '
        f'aria-label="Mostrar u ocultar contraseña">\n'
        f'{indent}    {SVG_EYE_CLOSED}\n'
        f'{indent}</button>'
    )


# ============================================================
# 1) REGISTRO.HTML  ->  envolver password1 y password2
# ============================================================
def actualizar_registro(html_path):
    html = leer(html_path)
    cambios = 0

    for campo in ('password1', 'password2'):
        marcador = '{{ form.' + campo + ' }}'

        # Evita duplicar si ya fue envuelto antes
        if f'password-wrapper' in html and f'form.{campo} }}' in html:
            # Comprobacion rapida: buscar si el bloque de este campo ya
            # esta dentro de un .password-wrapper
            patron_ya = re.compile(
                r'<div class="password-wrapper">[^<]*'
                r'\{\{\s*form\.' + campo + r'\s*\}\}',
                re.DOTALL
            )
            if patron_ya.search(html):
                print(f'  [!] registro.html: {campo} ya estaba envuelto.')
                continue

        if marcador not in html:
            print(f'  [!] registro.html: no se encontro "{marcador}".')
            continue

        reemplazo = (
            '<div class="password-wrapper">\n'
            '                        ' + marcador + '\n'
            '                        ' + boton_ojo('                        ') + '\n'
            '                    </div>'
        )

        html = html.replace(marcador, reemplazo, 1)
        cambios += 1
        print(f'  [+] registro.html: {campo} envuelto con boton del ojo.')

    if cambios:
        escribir(html_path, html)
    else:
        print('  [!] registro.html: nada que cambiar.')


# ============================================================
# 2) ADMIN_USUARIOS.HTML  ->  envolver campos del modal
# ============================================================
def actualizar_admin_usuarios(html_path):
    html = leer(html_path)
    cambios = 0

    # --- Reemplazo de nueva_password ---
    viejo_p1 = (
        '<div class="input-icon-wrap">\n'
        '                    <input type="password" name="nueva_password" id="nueva_password"\n'
        '                        class="form-control-dark" placeholder="Min. 4 caracteres"\n'
        '                        minlength="4" maxlength="50" required\n'
        '                        oninput="checkStrength(); checkMatch();">\n'
        '                </div>'
    )
    nuevo_p1 = (
        '<div class="password-wrapper">\n'
        '                    <input type="password" name="nueva_password" id="nueva_password"\n'
        '                        class="form-control-dark" placeholder="Min. 4 caracteres"\n'
        '                        minlength="4" maxlength="50" required\n'
        '                        oninput="checkStrength(); checkMatch();">\n'
        '                    ' + boton_ojo('                    ') + '\n'
        '                </div>'
    )

    if viejo_p1 in html:
        html = html.replace(viejo_p1, nuevo_p1, 1)
        cambios += 1
        print('  [+] admin_usuarios.html: campo "nueva_password" envuelto.')
    elif 'name="nueva_password"' in html and 'password-wrapper' not in html.split('name="nueva_password"')[1][:200]:
        # Fallback mas flexible con regex
        patron = re.compile(
            r'<div class="input-icon-wrap">\s*'
            r'(<input type="password" name="nueva_password".*?>)'
            r'\s*</div>',
            re.DOTALL
        )
        m = patron.search(html)
        if m:
            bloque_nuevo = (
                '<div class="password-wrapper">\n'
                '                    ' + m.group(1) + '\n'
                '                    ' + boton_ojo('                    ') + '\n'
                '                </div>'
            )
            html = html[:m.start()] + bloque_nuevo + html[m.end():]
            cambios += 1
            print('  [+] admin_usuarios.html: campo "nueva_password" envuelto (fallback).')
    else:
        print('  [!] admin_usuarios.html: no se encontro bloque de "nueva_password".')

    # --- Reemplazo de confirmar_password ---
    viejo_p2 = (
        '<div class="input-icon-wrap">\n'
        '                    <input type="password" name="confirmar_password" id="confirmar_password"\n'
        '                        class="form-control-dark" placeholder="Repite la contraseña"\n'
        '                        minlength="4" maxlength="50" required\n'
        '                        oninput="checkMatch();">\n'
        '                </div>'
    )
    nuevo_p2 = (
        '<div class="password-wrapper">\n'
        '                    <input type="password" name="confirmar_password" id="confirmar_password"\n'
        '                        class="form-control-dark" placeholder="Repite la contraseña"\n'
        '                        minlength="4" maxlength="50" required\n'
        '                        oninput="checkMatch();">\n'
        '                    ' + boton_ojo('                    ') + '\n'
        '                </div>'
    )

    if viejo_p2 in html:
        html = html.replace(viejo_p2, nuevo_p2, 1)
        cambios += 1
        print('  [+] admin_usuarios.html: campo "confirmar_password" envuelto.')
    elif 'name="confirmar_password"' in html:
        patron = re.compile(
            r'<div class="input-icon-wrap">\s*'
            r'(<input type="password" name="confirmar_password".*?>)'
            r'\s*</div>',
            re.DOTALL
        )
        m = patron.search(html)
        if m:
            bloque_nuevo = (
                '<div class="password-wrapper">\n'
                '                    ' + m.group(1) + '\n'
                '                    ' + boton_ojo('                    ') + '\n'
                '                </div>'
            )
            html = html[:m.start()] + bloque_nuevo + html[m.end():]
            cambios += 1
            print('  [+] admin_usuarios.html: campo "confirmar_password" envuelto (fallback).')
    else:
        print('  [!] admin_usuarios.html: no se encontro bloque de "confirmar_password".')

    if cambios:
        escribir(html_path, html)
    else:
        print('  [!] admin_usuarios.html: nada que cambiar.')


# ============================================================
# 3) APP.JS  ->  mover la inicializacion de iconos fuera del click
# ============================================================
def actualizar_app_js(js_path):
    contenido = leer(js_path)

    # Bloque mal anidado (dentro del handler del click)
    bloque_mal = (
        "            // Alternar el icono\n"
        "            this.innerHTML = isPassword ? eyeSVG : eyeOffSVG;\n"
        "    // Inicializacion: los campos de contraseña arrancan OCULTOS,\n"
        "    // por lo tanto mostramos el OJO CON RAYA desde el inicio.\n"
        "    toggleButtons.forEach(function (btn) {\n"
        "        var wrapper = btn.closest('.password-wrapper');\n"
        "        if (!wrapper) return;\n"
        "        var input = wrapper.querySelector('input');\n"
        "        if (input && input.getAttribute('type') === 'password') {\n"
        "            btn.innerHTML = eyeOffSVG;\n"
        "        }\n"
        "    });\n"
        "\n"
        "        });\n"
        "    });\n"
        "});"
    )

    # Version corregida: la inicializacion va FUERA del click handler
    bloque_bien = (
        "            // Alternar el icono\n"
        "            this.innerHTML = isPassword ? eyeSVG : eyeOffSVG;\n"
        "        });\n"
        "    });\n"
        "\n"
        "    // Inicializacion: los campos de contraseña arrancan OCULTOS,\n"
        "    // por lo tanto mostramos el OJO CON RAYA desde el inicio.\n"
        "    toggleButtons.forEach(function (btn) {\n"
        "        var wrapper = btn.closest('.password-wrapper');\n"
        "        if (!wrapper) return;\n"
        "        var input = wrapper.querySelector('input');\n"
        "        if (input && input.getAttribute('type') === 'password') {\n"
        "            btn.innerHTML = eyeOffSVG;\n"
        "        }\n"
        "    });\n"
        "});"
    )

    if bloque_mal in contenido:
        contenido = contenido.replace(bloque_mal, bloque_bien, 1)
        escribir(js_path, contenido)
        print('  [+] app.js: bloque de inicializacion movido fuera del click handler.')
        return

    # Alternativa: intento con regex por si el whitespace cambio
    patron = re.compile(
        r"(\s*//\s*Alternar el icono\s*\n"
        r"\s*this\.innerHTML\s*=\s*isPassword\s*\?\s*eyeSVG\s*:\s*eyeOffSVG\s*;\s*\n)"
        r"(\s*//\s*Inicializacion.*?\n"
        r"\s*toggleButtons\.forEach\(function\s*\(btn\)\s*\{.*?\}\);\s*\n)"
        r"(\s*\}\);\s*\n\s*\}\);\s*\n\}\);)",
        re.DOTALL
    )
    m = patron.search(contenido)
    if m:
        cierre_handler = m.group(1) + '        });\n    });\n'
        inicializacion = '\n    ' + m.group(2).strip().replace('\n', '\n    ') + '\n'
        contenido = contenido[:m.start()] + cierre_handler + inicializacion + '});' + contenido[m.end():]
        escribir(js_path, contenido)
        print('  [+] app.js: bloque de inicializacion reubicado (regex).')
        return

    print('  [!] app.js: no se encontro el bloque a corregir (quizas ya esta bien).')


# ============================================================
# MAIN
# ============================================================
def main():
    print('=' * 60)
    print(' AGREGAR OJOS EN CAMPOS DE CONTRASEÑA - 3-JJJ-A')
    print('=' * 60)

    registro_html       = encontrar('registro.html')
    admin_usuarios_html = encontrar('admin_usuarios.html')
    app_js              = encontrar('app.js')

    faltantes = []
    if not registro_html:       faltantes.append('registro.html')
    if not admin_usuarios_html: faltantes.append('admin_usuarios.html')
    if not app_js:              faltantes.append('app.js')

    if faltantes:
        print('ERROR: No se encontraron los siguientes archivos:')
        for f in faltantes:
            print('   -', f)
        print('\nEjecuta este script desde la RAIZ del proyecto (donde esta manage.py).')
        sys.exit(1)

    print(f'\nProyecto: {BASE_DIR}')
    print(f'registro.html        : {registro_html.relative_to(BASE_DIR)}')
    print(f'admin_usuarios.html  : {admin_usuarios_html.relative_to(BASE_DIR)}')
    print(f'app.js               : {app_js.relative_to(BASE_DIR)}')

    # Backups
    print('\n[1/4] Creando copias de seguridad...')
    for etiqueta, ruta in (
        ('registro.html',       registro_html),
        ('admin_usuarios.html', admin_usuarios_html),
        ('app.js',              app_js),
    ):
        bak = backup(ruta)
        if bak:
            print(f'  [+] {etiqueta}  ->  {bak.name}')

    # Cambios
    print('\n[2/4] Actualizando registro.html...')
    actualizar_registro(registro_html)

    print('\n[3/4] Actualizando admin_usuarios.html...')
    actualizar_admin_usuarios(admin_usuarios_html)

    print('\n[4/4] Corrigiendo app.js...')
    actualizar_app_js(app_js)

    print('\n' + '=' * 60)
    print(' LISTO. Campos de contraseña con boton del ojo agregados.')
    print('=' * 60)
    print('\nReglas visuales aplicadas:')
    print('  * Contraseña OCULTA  ->  OJO CON RAYA  (tachado)')
    print('  * Contraseña VISIBLE ->  OJO ABIERTO   (sin raya)')
    print('\nAplicado en:')
    print('  * registro.html       ->  password1 y password2')
    print('  * admin_usuarios.html ->  modal: nueva_password y confirmar_password')
    print('\nLos iconos son SVG inline (sin librerias externas).')
    print('Reinicia Django y recarga con Ctrl+F5 (cache).')
    print('=' * 60)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'\n[ERROR] {e}')
        sys.exit(1)