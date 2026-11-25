#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
actualizar_login.py
-------------------
Script de un solo uso que aplica los siguientes cambios al Sistema 3-JJJ-A:

  1. Crea copia de seguridad (.bak_YYYYMMDD_HHMMSS) de:
        - core/views.py
        - core/forms.py
        - <templates>/registration/login.html

  2. Extrae el CSS y JS embebidos en login.html y los guarda como archivos
     estáticos independientes:
        - static/css/login.css
        - static/js/login.js
     Luego reemplaza los bloques inline del HTML por referencias {% static %}.

  3. Simplifica la clase LoginForm en forms.py para que NO valide complejidad
     de contraseña (letras, números, caracteres especiales). De este modo,
     cualquier credencial incorrecta llega hasta la vista de login y se
     contabiliza como intento fallido.

  4. Reescribe login_view en views.py para que:
        - Cualquier contraseña incorrecta cuente como intento fallido.
        - Los mensajes mostrados sean únicamente:
              * "USUARIO INEXISTENTE."
              * "CONTRASEÑA INCORRECTA."
        - Se muestren avisos adicionales solo cuando la cuenta queda
          suspendida o bloqueada.

NO modifica ninguna otra función, modelo, URL ni plantilla del sistema.
"""

import os
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

STATIC_DIR = primer_existente([
    CORE_DIR / 'static',
    BASE_DIR / 'static',
])

VIEWS_PY = CORE_DIR / 'views.py'
FORMS_PY = CORE_DIR / 'forms.py'


# ============================================================
# UTILIDADES
# ============================================================
def backup(path):
    """Crea copia de seguridad con timestamp."""
    if not path or not path.exists():
        return None
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino = path.with_name(path.name + f'.bak_{ts}')
    shutil.copy2(path, destino)
    return destino


def abrir(path):
    return path.read_text(encoding='utf-8')


def escribir(path, contenido):
    path.write_text(contenido, encoding='utf-8')


# ============================================================
# PASO 1: EXTRAER CSS Y JS DE login.html
# ============================================================
def procesar_login_html():
    if not LOGIN_HTML:
        raise RuntimeError('No se encontro login.html en ninguna ruta conocida.')
    if not STATIC_DIR:
        raise RuntimeError('No se encontro carpeta static/ en el proyecto.')

    css_path = STATIC_DIR / 'css' / 'login.css'
    js_path = STATIC_DIR / 'js' / 'login.js'

    html = abrir(LOGIN_HTML)

    # --- CSS ---
    css_match = re.search(r'<style>(.*?)</style>', html, re.DOTALL)
    if css_match:
        css_content = css_match.group(1).strip()
        css_path.parent.mkdir(parents=True, exist_ok=True)
        escribir(css_path, css_content + '\n')
        html = re.sub(
            r'<style>.*?</style>',
            '<link rel="stylesheet" href="{% static \'css/login.css\' %}">',
            html, count=1, flags=re.DOTALL
        )
        print(f'  [+] CSS extraido  -> {css_path.relative_to(BASE_DIR)}')
    else:
        print(f'  [!] No se encontro <style> en login.html (ya externalizado?)')

    # --- JS inline (excluye los que tienen src=) ---
    script_pattern = re.compile(
        r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>',
        re.DOTALL
    )
    scripts = script_pattern.findall(html)
    if scripts:
        js_content = max(scripts, key=len).strip()
        js_path.parent.mkdir(parents=True, exist_ok=True)
        escribir(js_path, js_content + '\n')
        html = script_pattern.sub(
            '<script src="{% static \'js/login.js\' %}"></script>',
            html, count=1
        )
        print(f'  [+] JS  extraido  -> {js_path.relative_to(BASE_DIR)}')
    else:
        print(f'  [!] No se encontro <script> inline en login.html')

    escribir(LOGIN_HTML, html)
    print(f'  [+] login.html actualizado (usa archivos externos).')


# ============================================================
# PASO 2: SIMPLIFICAR LoginForm EN forms.py
# ============================================================
NUEVO_LOGIN_FORM = '''class LoginForm(forms.Form):
    """Formulario de inicio de sesion simplificado.

    Las validaciones de complejidad de contraseña se realizan al crear o
    actualizar un usuario. En el login NO se valida la complejidad: cualquier
    credencial incorrecta debe llegar a la vista para registrarse como
    intento fallido y aplicar la politica de bloqueo.
    """

    username = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Nombre de usuario',
            'autocomplete': 'username',
            'maxlength': '50',
            'id': 'id_username',
        }),
        label='Usuario',
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Contraseña',
            'autocomplete': 'current-password',
            'maxlength': '100',
            'id': 'id_password',
        }),
        label='Contraseña',
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip().lower()
        if not username:
            raise ValidationError('El nombre de usuario es obligatorio.')
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if not password:
            raise ValidationError('La contraseña es obligatoria.')
        # IMPORTANTE: sin validacion de complejidad aqui a proposito.
        # Si la credencial es incorrecta, la vista de login se encarga de
        # registrar el intento fallido y aplicar la politica de bloqueo.
        return password


'''


def procesar_forms():
    contenido = abrir(FORMS_PY)
    inicio = contenido.find('class LoginForm(forms.Form):')
    fin_marca = ('# ============================================================\n'
                 '# 6. FORMULARIO: REGISTRO DE MAQUINARIA')
    fin = contenido.find(fin_marca, inicio)

    if inicio == -1 or fin == -1:
        raise RuntimeError('No se pudo localizar el bloque LoginForm en forms.py.')

    nuevo = contenido[:inicio] + NUEVO_LOGIN_FORM + contenido[fin:]
    escribir(FORMS_PY, nuevo)
    print('  [+] LoginForm simplificado en forms.py')


# ============================================================
# PASO 3: REESCRIBIR login_view EN views.py
# ============================================================
NUEVO_LOGIN_VIEW = '''def login_view(request):
    """Vista de login.

    Reglas aplicadas:
      * Cualquier contraseña incorrecta (sin importar su formato o
        complejidad) cuenta como intento fallido y aplica la politica
        de suspension / bloqueo.
      * Los unicos mensajes de credenciales son:
            "USUARIO INEXISTENTE."
            "CONTRASEÑA INCORRECTA."
      * Solo se añaden avisos extra cuando la cuenta queda suspendida
        o bloqueada, para que el usuario sepa que debe esperar o
        contactar al administrador.
    """
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # 1. Verificar si esta bloqueado o suspendido
            bloqueado, motivo, minutos = esta_bloqueado(username)
            if bloqueado:
                if motivo == 'permanente':
                    messages.error(
                        request,
                        'Su cuenta ha sido BLOQUEADA por demasiados intentos fallidos. '
                        'Contacte al administrador del sistema.'
                    )
                else:
                    messages.error(
                        request,
                        f'Cuenta suspendida temporalmente. '
                        f'Intente nuevamente en {minutos} minuto(s).'
                    )
                return render(request, 'registration/login.html', {'form': form})

            # 2. Verificar existencia del usuario
            try:
                user = Usuario.objects.get(id_usuario=username)
            except Usuario.DoesNotExist:
                messages.error(request, 'USUARIO INEXISTENTE.')
                return render(request, 'registration/login.html', {'form': form})

            # 3. Verificar contrasena
            if user.check_password(password) and user.is_active:
                limpiar_intentos(username)
                request.session[SESSION_KEY] = user.id_usuario
                request.session.set_expiry(0)
                request.session.modified = True

                if tiene_password_temporal(user.id_usuario):
                    messages.warning(
                        request,
                        'Su contraseña es temporal. Debe cambiarla antes de continuar.'
                    )
                    return redirect('core:cambiar_password_temporal')

                messages.success(request, f'Bienvenido, {user.nombre_completo}.')
                return redirect('core:redirect_por_rol')

            # 4. Contrasena incorrecta (o usuario inactivo) -> intento fallido
            info = registrar_intento_fallido(username, es_admin=user.is_staff)
            messages.error(request, 'CONTRASEÑA INCORRECTA.')

            # Avisos adicionales: solo cuando aplican suspension o bloqueo.
            if user.is_staff:
                if info.get('bloqueado_hasta'):
                    messages.warning(
                        request,
                        f'La cuenta de administrador ha sido suspendida '
                        f'{MINUTOS_SUSPENSION} minutos por seguridad.'
                    )
            else:
                if info.get('bloqueado_permanente'):
                    messages.error(
                        request,
                        'Su cuenta ha sido BLOQUEADA por superar el limite de '
                        'intentos fallidos. Contacte al administrador.'
                    )
                elif info.get('bloqueado_hasta'):
                    messages.warning(
                        request,
                        f'Cuenta suspendida {MINUTOS_SUSPENSION} minutos '
                        f'por superar el limite de intentos.'
                    )
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form})


'''


def procesar_views():
    contenido = abrir(VIEWS_PY)
    inicio = contenido.find('def login_view(request):')
    fin = contenido.find('def logout_view(request):', inicio)

    if inicio == -1 or fin == -1:
        raise RuntimeError('No se pudo localizar login_view en views.py.')

    nuevo = contenido[:inicio] + NUEVO_LOGIN_VIEW + contenido[fin:]
    escribir(VIEWS_PY, nuevo)
    print('  [+] login_view actualizado en views.py')


# ============================================================
# MAIN
# ============================================================
def main():
    print('=' * 60)
    print(' ACTUALIZACION DEL LOGIN - Sistema 3-JJJ-A')
    print('=' * 60)

    # 0. Validar rutas
    faltantes = [str(p.relative_to(BASE_DIR))
                 for p in (VIEWS_PY, FORMS_PY) if not p.exists()]
    if not LOGIN_HTML:
        faltantes.append('templates/registration/login.html')
    if not STATIC_DIR:
        faltantes.append('static/')
    if faltantes:
        print('ERROR: No se encontraron los siguientes archivos/carpetas:')
        for f in faltantes:
            print('   -', f)
        print('\nEjecuta este script desde la RAIZ del proyecto (donde esta manage.py).')
        sys.exit(1)

    print(f'\nProyecto detectado en: {BASE_DIR}')
    print(f'Template login.html : {LOGIN_HTML.relative_to(BASE_DIR)}')
    print(f'Carpeta static      : {STATIC_DIR.relative_to(BASE_DIR)}')

    # 1. Backup
    print('\n[1/4] Creando copias de seguridad...')
    for etiqueta, ruta in (
        ('views.py',  VIEWS_PY),
        ('forms.py',  FORMS_PY),
        ('login.html', LOGIN_HTML),
    ):
        bak = backup(ruta)
        if bak:
            print(f'  [+] {etiqueta}  ->  {bak.name}')

    # 2. Extraer CSS/JS
    print('\n[2/4] Extrayendo CSS y JS del login...')
    procesar_login_html()

    # 3. Simplificar LoginForm
    print('\n[3/4] Simplificando LoginForm...')
    procesar_forms()

    # 4. Reescribir login_view
    print('\n[4/4] Reescribiendo login_view...')
    procesar_views()

    print('\n' + '=' * 60)
    print(' LISTO. Cambios aplicados correctamente.')
    print('=' * 60)
    print('\nResumen de comportamiento nuevo del login:')
    print('  * Credenciales incorrectas  -> "CONTRASEÑA INCORRECTA."')
    print('  * Usuario no registrado     -> "USUARIO INEXISTENTE."')
    print('  * Sin mensajes de "caracter especial", "letra" o "numero".')
    print('  * Cualquier clave incorrecta cuenta como intento fallido.')
    print('  * Se mantiene la politica de suspension / bloqueo.')
    print('\nReinicia el servidor Django para aplicar los cambios.')
    print('=' * 60)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'\n[ERROR] {e}')
        sys.exit(1)