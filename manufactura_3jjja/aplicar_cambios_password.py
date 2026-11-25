#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
aplicar_cambios_password.py
---------------------------
Aplica automaticamente TODOS los cambios para limitar las contraseñas
a MIN=8 y MAX=12 caracteres en el sistema 3-JJJ-A.

USO:
    1. Colocar este archivo en la misma carpeta que manage.py
    2. Ejecutar:  python aplicar_cambios_password.py

Hace backups automaticos en _backup_password_FECHA_HORA/
por si necesitas revertir.
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ------------------------------------------------------------
# CONFIGURACION
# ------------------------------------------------------------
MIN_LENGTH = 8
MAX_LENGTH = 12

BASE_DIR = Path(__file__).resolve().parent
BACKUP_DIR = BASE_DIR / f"_backup_password_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

OK = "[OK]"
ERR = "[ERROR]"
WARN = "[AVISO]"


# ------------------------------------------------------------
# UTILIDADES
# ------------------------------------------------------------
def log(msg):
    print(msg)


def buscar_archivo(rutas_relativas):
    """Devuelve la primera ruta existente de la lista, o None."""
    for rel in rutas_relativas:
        p = BASE_DIR / rel
        if p.exists():
            return p
    return None


def hacer_backup(path):
    """Copia el archivo a la carpeta de backups."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        rel = path.relative_to(BASE_DIR)
    except ValueError:
        rel = Path(path.name)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    log(f"    {OK} Backup: {rel}")


def leer(path):
    return path.read_text(encoding='utf-8')


def escribir(path, contenido):
    path.write_text(contenido, encoding='utf-8')


def reemplazar_exacto(texto, viejo, nuevo, descripcion):
    """Reemplaza texto exacto. Devuelve (nuevo_texto, exito)."""
    if viejo not in texto:
        log(f"    {WARN} No se encontro el bloque: {descripcion}")
        return texto, False
    if texto.count(viejo) > 1:
        log(f"    {WARN} El bloque aparece mas de una vez: {descripcion}")
    return texto.replace(viejo, nuevo, 1), True


def asegurar_parent(path):
    path.parent.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# CONTENIDO DE LOS ARCHIVOS NUEVOS
# ------------------------------------------------------------
CONTENIDO_PASSWORD_LIMITS_JS = r"""/* ============================================================
   password-limits.js
   Impone MIN=8 y MAX=12 caracteres en TODOS los campos de
   contraseña del sistema (login, registro, admin, cambio de
   contraseña temporal, etc.) de forma defensiva.
   - No modifica ninguna lógica existente.
   - Se aplica también a campos creados dinámicamente (modales).
   ============================================================ */
(function () {
    'use strict';

    var MIN_PASS = 8;
    var MAX_PASS = 12;

    function aplicarLimite(input) {
        if (!input || input.dataset.passLimitBound === '1') return;

        input.setAttribute('maxlength', MAX_PASS);
        if (!input.hasAttribute('minlength')) {
            input.setAttribute('minlength', MIN_PASS);
        }

        input.addEventListener('input', function () {
            if (this.value.length > MAX_PASS) {
                this.value = this.value.slice(0, MAX_PASS);
            }
        });

        input.addEventListener('paste', function (e) {
            var clipboard = (e.clipboardData || window.clipboardData);
            if (!clipboard) return;
            var pegado = clipboard.getData('text') || '';
            var actual = this.value;
            var ini = this.selectionStart || 0;
            var fin = this.selectionEnd || 0;
            var resultado = actual.slice(0, ini) + pegado + actual.slice(fin);
            if (resultado.length > MAX_PASS) {
                e.preventDefault();
                this.value = resultado.slice(0, MAX_PASS);
            }
        });

        input.dataset.passLimitBound = '1';
    }

    function aplicarATodos() {
        var selector = 'input[type="password"], ' +
                       'input[name*="password" i], ' +
                       'input[id*="password" i], ' +
                       'input[name*="contrasenia" i], ' +
                       'input[id*="contrasenia" i]';
        var inputs = document.querySelectorAll(selector);
        for (var i = 0; i < inputs.length; i++) {
            aplicarLimite(inputs[i]);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', aplicarATodos);
    } else {
        aplicarATodos();
    }

    if (window.MutationObserver) {
        document.addEventListener('DOMContentLoaded', function () {
            var observer = new MutationObserver(function () {
                aplicarATodos();
            });
            observer.observe(document.body, { childList: true, subtree: true });
        });
    }
})();
"""

CONTENIDO_CAMBIAR_CSS = r"""/* cambiar_password_temporal.css */
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body {
    height: 100%;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    overflow: hidden;
}
.page-wrapper {
    display: flex; align-items: center; justify-content: center;
    width: 100%; height: 100vh;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    position: relative;
}
.page-wrapper::before {
    content: ''; position: absolute; top: 50%; left: 0;
    width: 100%; height: 50%;
    background: linear-gradient(180deg,
        rgba(16,185,129,0.0) 0%,
        rgba(16,185,129,0.05) 15%,
        rgba(5,150,105,0.12) 40%,
        rgba(4,120,87,0.20) 65%,
        rgba(6,78,59,0.28) 100%);
    pointer-events: none;
}
.login-card {
    position: relative; width: 100%; max-width: 420px;
    background: rgba(30, 41, 59, 0.95);
    border: 1px solid rgba(16, 185, 129, 0.15);
    border-radius: 24px; padding: 40px 36px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.3), 0 4px 12px rgba(0,0,0,0.15);
    backdrop-filter: blur(10px); z-index: 1;
}
.login-header { text-align: center; margin-bottom: 24px; }
.login-logo {
    width: 60px; height: 60px; margin: 0 auto 16px;
    background: linear-gradient(135deg, #f59e0b, #d97706);
    border-radius: 16px;
    display: flex; align-items: center; justify-content: center;
    font-size: 26px; color: white;
    box-shadow: 0 4px 15px rgba(245, 158, 11, 0.35);
}
.login-header h1 { color: #f1f5f9; font-size: 1.2rem; margin: 0 0 6px 0; font-weight: 700; }
.login-header p  { color: #94a3b8; font-size: 0.82rem; margin: 0; }
.info-box {
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.3);
    color: #fbbf24; padding: 12px 14px; border-radius: 12px;
    font-size: 0.82rem; display: flex; align-items: flex-start;
    gap: 10px; margin-bottom: 20px; line-height: 1.4;
}
.info-box i { font-size: 1.1rem; flex-shrink: 0; margin-top: 2px; }
.form-group { margin-bottom: 18px; }
.form-group label {
    display: block; color: #cbd5e1; font-size: 0.78rem; font-weight: 600;
    margin-bottom: 7px; text-transform: uppercase; letter-spacing: 0.5px;
}
.form-control-dark {
    width: 100%; padding: 12px 44px 12px 16px;
    background: rgba(15, 23, 42, 0.8);
    border: 1.5px solid rgba(100, 116, 139, 0.3);
    border-radius: 12px; color: #f1f5f9; font-size: 0.9rem;
    transition: all 0.25s ease;
}
.form-control-dark:focus {
    outline: none; border-color: #10b981;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
    background: rgba(15, 23, 42, 0.95);
}
.form-control-dark::placeholder { color: #64748b; }

.password-input-wrapper {
    position: relative; display: flex; align-items: center; width: 100%;
}
.toggle-password-btn {
    position: absolute; right: 12px;
    background: transparent; border: none; color: #94a3b8;
    cursor: pointer; font-size: 1.1rem;
    display: inline-flex; align-items: center; justify-content: center;
    padding: 4px; transition: color 0.2s ease; z-index: 2;
}
.toggle-password-btn:hover { color: #10b981; }

.btn-login {
    width: 100%; padding: 13px;
    background: linear-gradient(135deg, #10b981, #059669);
    border: none; border-radius: 12px; color: white;
    font-size: 0.95rem; font-weight: 600; cursor: pointer;
    transition: all 0.3s ease;
    display: flex; align-items: center; justify-content: center;
    gap: 8px; margin-top: 8px; letter-spacing: 0.5px;
}
.btn-login:hover {
    background: linear-gradient(135deg, #059669, #047857);
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(16, 185, 129, 0.3);
}
.messages-container { margin-bottom: 18px; }
.alert {
    padding: 10px 14px; border-radius: 10px; font-size: 0.85rem;
    display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
}
.alert-success {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399;
}
.alert-error, .alert-info {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171;
}
.alert-warning {
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.3); color: #fbbf24;
}
.fade-in { animation: fadeIn 0.4s ease; }
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-8px); }
    to   { opacity: 1; transform: translateY(0); }
}
"""

CONTENIDO_CAMBIAR_JS = r"""/* cambiar_password_temporal.js
   Alterna la visibilidad de los campos de contraseña en la
   pantalla de cambio obligatorio de contraseña.
*/
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.toggle-password-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            var targetId = this.getAttribute('data-target');
            var input = targetId ? document.getElementById(targetId) : null;
            var icon = this.querySelector('i');
            if (!input) return;

            if (input.type === 'password') {
                input.type = 'text';
                if (icon) icon.className = 'bi bi-eye';
            } else {
                input.type = 'password';
                if (icon) icon.className = 'bi bi-eye-slash';
            }
        });
    });
});
"""

CONTENIDO_TEMPLATE_CAMBIAR = r"""{% load static %}
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cambiar Contraseña - 3-JJJ-A</title>
    <link rel="stylesheet" href="{% static 'css/3jjja-icons-mask.css' %}">
    <link rel="stylesheet" href="{% static 'css/cambiar_password_temporal.css' %}">
</head>
<body>
    <div class="page-wrapper">
        <div class="login-card">
            <div class="login-header">
                <div class="login-logo">
                    <i class="bi bi-shield-lock"></i>
                </div>
                <h1>Cambio de Contraseña Obligatorio</h1>
                <p>Establezca una contraseña personal para continuar</p>
            </div>

            {% if messages %}
            <div class="messages-container">
                {% for message in messages %}
                <div class="alert alert-{{ message.tags }} fade-in">
                    <i class="bi bi-{% if message.tags == 'success' %}check-circle{% elif message.tags == 'error' %}x-circle{% elif message.tags == 'warning' %}exclamation-triangle{% else %}info-circle{% endif %}"></i>
                    {{ message }}
                </div>
                {% endfor %}
            </div>
            {% endif %}

            <div class="info-box">
                <i class="bi bi-info-circle-fill"></i>
                <div>
                    Hola <strong>{{ usuario.nombre_completo }}</strong>, su contraseña actual
                    fue asignada por el administrador como <em>temporal</em>.
                    Por seguridad debe cambiarla antes de continuar.
                    <br><small>La nueva contraseña debe tener entre <strong>8 y 12 caracteres</strong>.</small>
                </div>
            </div>

            <form method="post" novalidate>
                {% csrf_token %}

                <div class="form-group">
                    <label for="id_password1">Nueva Contraseña</label>
                    <div class="password-input-wrapper">
                        {{ form.password1 }}
                        <button type="button" class="toggle-password-btn"
                                data-target="id_password1" aria-label="Ver contraseña">
                            <i class="bi bi-eye-slash"></i>
                        </button>
                    </div>
                </div>

                <div class="form-group">
                    <label for="id_password2">Confirmar Contraseña</label>
                    <div class="password-input-wrapper">
                        {{ form.password2 }}
                        <button type="button" class="toggle-password-btn"
                                data-target="id_password2" aria-label="Ver contraseña">
                            <i class="bi bi-eye-slash"></i>
                        </button>
                    </div>
                </div>

                <button type="submit" class="btn-login">
                    <i class="bi bi-check-circle"></i> Cambiar Contraseña
                </button>
            </form>
        </div>
    </div>

    <script src="{% static 'js/password-limits.js' %}" defer></script>
    <script src="{% static 'js/cambiar_password_temporal.js' %}" defer></script>
</body>
</html>
"""


# ------------------------------------------------------------
# 1. MODIFICAR core/forms.py
# ------------------------------------------------------------
def modificar_forms():
    log("\n=== [1/6] Modificando core/forms.py ===")
    path = buscar_archivo(['core/forms.py', 'forms.py'])
    if not path:
        log(f"    {ERR} No se encontro forms.py en core/ ni en la raiz.")
        return False

    hacer_backup(path)
    texto = leer(path)
    cambios = 0

    # --- 1.1 password1 de RegistroUsuarioForm ---
    viejo_p1 = """    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Contraseña',
            'autocomplete': 'new-password',
            'maxlength': '20',
        }),
        label='Contraseña',
        validators=[
            MinLengthValidator(4, 'La contraseña debe tener al menos 4 caracteres.'),
            MaxLengthValidator(20, 'La contraseña no puede exceder 20 caracteres.'),
        ]
    )"""
    nuevo_p1 = """    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Contraseña (8 a 12 caracteres)',
            'autocomplete': 'new-password',
            'maxlength': '12',
            'minlength': '8',
        }),
        label='Contraseña',
        validators=[
            MinLengthValidator(8, 'La contraseña debe tener al menos 8 caracteres.'),
            MaxLengthValidator(12, 'La contraseña no puede exceder 12 caracteres.'),
        ]
    )"""
    texto, ok = reemplazar_exacto(texto, viejo_p1, nuevo_p1, "password1 RegistroUsuarioForm")
    cambios += 1 if ok else 0

    # --- 1.2 password2 de RegistroUsuarioForm ---
    viejo_p2 = """    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Confirmar contraseña',
            'autocomplete': 'new-password',
            'maxlength': '20',
        }),
        label='Confirmar Contraseña',
        validators=[
            MinLengthValidator(4, 'La confirmación debe tener al menos 4 caracteres.'),
            MaxLengthValidator(20, 'La confirmación no puede exceder 20 caracteres.'),
        ]
    )"""
    nuevo_p2 = """    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Confirmar contraseña (8 a 12 caracteres)',
            'autocomplete': 'new-password',
            'maxlength': '12',
            'minlength': '8',
        }),
        label='Confirmar Contraseña',
        validators=[
            MinLengthValidator(8, 'La confirmación debe tener al menos 8 caracteres.'),
            MaxLengthValidator(12, 'La confirmación no puede exceder 12 caracteres.'),
        ]
    )"""
    texto, ok = reemplazar_exacto(texto, viejo_p2, nuevo_p2, "password2 RegistroUsuarioForm")
    cambios += 1 if ok else 0

    # --- 1.3 clean_password2 de RegistroUsuarioForm ---
    viejo_clean = """    def clean_password2(self):
        p1 = self.cleaned_data.get('password1', '')
        p2 = self.cleaned_data.get('password2', '')
        if p1 != p2:
            raise ValidationError('Las contraseñas no coinciden.')
        if not re.search(r'[a-zA-Z]', p1):
            raise ValidationError('La contraseña debe contener al menos una letra.')
        if not re.search(r'[0-9]', p1):
            raise ValidationError('La contraseña debe contener al menos un número.')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>\\[\\]\\-_=+`~]', p1):
            raise ValidationError('La contraseña debe contener al menos un caracter especial.')
        return p2"""
    nuevo_clean = """    def clean_password2(self):
        p1 = self.cleaned_data.get('password1', '')
        p2 = self.cleaned_data.get('password2', '')
        if len(p1) < 8:
            raise ValidationError('La contraseña debe tener al menos 8 caracteres.')
        if len(p1) > 12:
            raise ValidationError('La contraseña no puede exceder 12 caracteres.')
        if p1 != p2:
            raise ValidationError('Las contraseñas no coinciden.')
        if not re.search(r'[a-zA-Z]', p1):
            raise ValidationError('La contraseña debe contener al menos una letra.')
        if not re.search(r'[0-9]', p1):
            raise ValidationError('La contraseña debe contener al menos un número.')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>\\[\\]\\-_=+`~]', p1):
            raise ValidationError('La contraseña debe contener al menos un caracter especial.')
        return p2"""
    texto, ok = reemplazar_exacto(texto, viejo_clean, nuevo_clean, "clean_password2 RegistroUsuarioForm")
    cambios += 1 if ok else 0

    # --- 1.4 LoginForm password widget (maxlength 100 -> 12) ---
    viejo_login = """            'placeholder': 'Contraseña',
            'autocomplete': 'current-password',
            'maxlength': '100',
            'id': 'id_password',"""
    nuevo_login = """            'placeholder': 'Contraseña',
            'autocomplete': 'current-password',
            'maxlength': '12',
            'id': 'id_password',"""
    texto, ok = reemplazar_exacto(texto, viejo_login, nuevo_login, "LoginForm password widget")
    cambios += 1 if ok else 0

    # --- 1.5 CambiarPasswordTemporalForm (clase completa) ---
    patron_cambiar = re.compile(
        r"class CambiarPasswordTemporalForm\(forms\.Form\):.*?(?=\nclass |\Z)",
        re.DOTALL,
    )
    nuevo_cambiar = '''class CambiarPasswordTemporalForm(forms.Form):
    password1 = forms.CharField(
        label='Nueva Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Entre 8 y 12 caracteres',
            'id': 'id_password1',
            'minlength': '8',
            'maxlength': '12',
            'autocomplete': 'new-password',
        }),
        min_length=8,
        max_length=12,
        error_messages={
            'min_length': 'La contraseña debe tener al menos 8 caracteres.',
            'max_length': 'La contraseña no puede exceder 12 caracteres.',
        },
    )
    password2 = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Repita la contraseña (8 a 12 caracteres)',
            'id': 'id_password2',
            'minlength': '8',
            'maxlength': '12',
            'autocomplete': 'new-password',
        }),
        min_length=8,
        max_length=12,
        error_messages={
            'min_length': 'La confirmación debe tener al menos 8 caracteres.',
            'max_length': 'La confirmación no puede exceder 12 caracteres.',
        },
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and len(p1) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
        if p1 and len(p1) > 12:
            raise forms.ValidationError('La contraseña no puede exceder 12 caracteres.')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        if p1 and p1.isdigit():
            raise forms.ValidationError('La contraseña no puede ser completamente numérica.')
        return cleaned
'''
    if patron_cambiar.search(texto):
        texto = patron_cambiar.sub(nuevo_cambiar, texto, count=1)
        log(f"    {OK} CambiarPasswordTemporalForm reemplazada")
        cambios += 1
    else:
        log(f"    {WARN} No se encontro class CambiarPasswordTemporalForm")

    escribir(path, texto)
    log(f"    {OK} forms.py guardado ({cambios} cambios aplicados)")
    return True


# ------------------------------------------------------------
# 2. MODIFICAR core/views.py
# ------------------------------------------------------------
def modificar_views():
    log("\n=== [2/6] Modificando core/views.py ===")
    path = buscar_archivo(['core/views.py', 'views.py'])
    if not path:
        log(f"    {ERR} No se encontro views.py")
        return False

    hacer_backup(path)
    texto = leer(path)

    # Bloque dentro de admin_usuarios_view
    patron = re.compile(
        r"        elif accion == 'cambiar_password' and usuario_id:.*?"
        r"(?=\n        return redirect\('core:admin_usuarios'\))",
        re.DOTALL,
    )
    nuevo_bloque = """        elif accion == 'cambiar_password' and usuario_id:
            nueva_password = request.POST.get('nueva_password', '').strip()
            confirmar_password = request.POST.get('confirmar_password', '').strip()
            if not nueva_password:
                messages.error(request, 'Debe ingresar una nueva contraseña.')
            elif len(nueva_password) < 8:
                messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
            elif len(nueva_password) > 12:
                messages.error(request, 'La contraseña no puede exceder 12 caracteres.')
            elif nueva_password != confirmar_password:
                messages.error(request, 'Las contraseñas no coinciden. Por favor verifique.')
            else:
                try:
                    user = Usuario.objects.get(id_usuario=usuario_id)
                    user.set_password(nueva_password)
                    user.save()
                    marcar_password_temporal(usuario_id)
                    messages.success(
                        request,
                        f'Contraseña temporal asignada a {usuario_id}. '
                        f'El usuario deberá cambiarla al iniciar sesión.'
                    )
                except Usuario.DoesNotExist:
                    messages.error(request, 'Usuario no encontrado.')
            return redirect('core:admin_usuarios')"""

    if patron.search(texto):
        texto = patron.sub(nuevo_bloque, texto, count=1)
        log(f"    {OK} Bloque cambiar_password actualizado")
    else:
        log(f"    {WARN} No se encontro el bloque 'cambiar_password' en admin_usuarios_view")
        log(f"    {WARN} views.py se deja sin cambios")
        return False

    escribir(path, texto)
    log(f"    {OK} views.py guardado")
    return True


# ------------------------------------------------------------
# 3. MODIFICAR templates/base.html
# ------------------------------------------------------------
def modificar_base_html():
    log("\n=== [3/6] Modificando templates/base.html ===")
    path = buscar_archivo([
        'templates/base.html',
        'core/templates/base.html',
    ])
    if not path:
        log(f"    {WARN} No se encontro base.html. Añade manualmente la linea:")
        log(f"        <script src=\"{{% static 'js/password-limits.js' %}}\" defer></script>")
        return False

    hacer_backup(path)
    texto = leer(path)

    # Si ya esta enlazado, no duplicar
    if 'password-limits.js' in texto:
        log(f"    {OK} password-limits.js ya estaba enlazado en base.html")
        return True

    # Insertar despues de app.js
    patron_appjs = re.compile(
        r'(<script[^>]*src=["\'][^"\']*app\.js[^"\']*["\'][^>]*>\s*</script>)',
        re.IGNORECASE,
    )
    match = patron_appjs.search(texto)

    if match:
        insercion = (
            match.group(1)
            + '\n    <script src="{% static \'js/password-limits.js\' %}" defer></script>'
        )
        texto = texto[:match.start()] + insercion + texto[match.end():]
        log(f"    {OK} Script insertado despues de app.js")
    else:
        # Fallback: insertar antes de </body>
        if '</body>' in texto:
            insercion = (
                '    <script src="{% static \'js/password-limits.js\' %}" defer></script>\n'
                '</body>'
            )
            texto = texto.replace('</body>', insercion, 1)
            log(f"    {OK} Script insertado antes de </body>")
        else:
            log(f"    {WARN} No se pudo encontrar un punto de insercion en base.html")
            log(f"    {WARN} Añade manualmente:")
            log(f"        <script src=\"{{% static 'js/password-limits.js' %}}\" defer></script>")
            return False

    escribir(path, texto)
    log(f"    {OK} base.html guardado")
    return True


# ------------------------------------------------------------
# 4. REEMPLAZAR templates/registration/cambiar_password_temporal.html
# ------------------------------------------------------------
def reemplazar_template_cambiar():
    log("\n=== [4/6] Reemplazando cambiar_password_temporal.html ===")
    path = buscar_archivo([
        'templates/registration/cambiar_password_temporal.html',
        'core/templates/registration/cambiar_password_temporal.html',
    ])
    if not path:
        log(f"    {ERR} No se encontro cambiar_password_temporal.html")
        return False

    hacer_backup(path)
    escribir(path, CONTENIDO_TEMPLATE_CAMBIAR)
    log(f"    {OK} Template reemplazado completamente")
    return True


# ------------------------------------------------------------
# 5. CREAR ARCHIVOS ESTATICOS
# ------------------------------------------------------------
def crear_estaticos():
    log("\n=== [5/6] Creando archivos estaticos ===")

    # Detectar carpeta static
    static_root = None
    for candidato in [
        BASE_DIR / 'static',
        BASE_DIR / 'core' / 'static',
        BASE_DIR / 'mi_proyecto' / 'static',
    ]:
        if candidato.exists():
            static_root = candidato
            break

    if static_root is None:
        # Crear en la raiz si no existe
        static_root = BASE_DIR / 'static'
        static_root.mkdir(parents=True, exist_ok=True)
        log(f"    {WARN} No existia carpeta static. Creada en: static/")

    log(f"    Carpeta static detectada: {static_root.relative_to(BASE_DIR)}")

    # --- password-limits.js ---
    p = static_root / 'js' / 'password-limits.js'
    asegurar_parent(p)
    if p.exists():
        hacer_backup(p)
    escribir(p, CONTENIDO_PASSWORD_LIMITS_JS)
    log(f"    {OK} Creado: {p.relative_to(BASE_DIR)}")

    # --- cambiar_password_temporal.css ---
    p = static_root / 'css' / 'cambiar_password_temporal.css'
    asegurar_parent(p)
    if p.exists():
        hacer_backup(p)
    escribir(p, CONTENIDO_CAMBIAR_CSS)
    log(f"    {OK} Creado: {p.relative_to(BASE_DIR)}")

    # --- cambiar_password_temporal.js ---
    p = static_root / 'js' / 'cambiar_password_temporal.js'
    asegurar_parent(p)
    if p.exists():
        hacer_backup(p)
    escribir(p, CONTENIDO_CAMBIAR_JS)
    log(f"    {OK} Creado: {p.relative_to(BASE_DIR)}")

    return True


# ------------------------------------------------------------
# 6. RESUMEN
# ------------------------------------------------------------
def resumen(resultados):
    log("\n" + "=" * 60)
    log("RESUMEN")
    log("=" * 60)
    nombres = [
        "1. core/forms.py",
        "2. core/views.py",
        "3. templates/base.html",
        "4. template cambiar_password_temporal.html",
        "5. archivos estaticos (JS + CSS)",
    ]
    todo_ok = True
    for nombre, ok in zip(nombres, resultados):
        estado = f"{OK}" if ok else f"{WARN}"
        log(f"  {estado} {nombre}")
        if not ok:
            todo_ok = False

    log("\n" + "-" * 60)
    if todo_ok:
        log(f"{OK} TODOS los cambios aplicados correctamente.")
        log("")
        log("Proximos pasos:")
        log("  1. Reinicia el servidor:  python manage.py runserver")
        log("  2. Recarga el navegador con Ctrl + F5")
        log("  3. Prueba:")
        log("     - Login: no deja teclear mas de 12 caracteres")
        log("     - Registro: pide minimo 8, maximo 12")
        log("     - Panel admin > Usuarios > cambiar contraseña: 8-12")
        log("     - Cambio de contraseña temporal: 8-12")
    else:
        log(f"{WARN} Algunos cambios requirieron atencion manual.")
        log("  Revisa los mensajes [AVISO] arriba.")

    log("")
    log(f"Backups guardados en: {BACKUP_DIR.name}/")
    log("Si algo sale mal, copia los archivos de ahi sobre los originales.")
    log("=" * 60)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    log("=" * 60)
    log("APLICADOR AUTOMATICO DE CAMBIOS - PASSWORD 8-12")
    log("Sistema 3-JJJ-A")
    log("=" * 60)
    log(f"Directorio base: {BASE_DIR}")

    if not (BASE_DIR / 'manage.py').exists():
        log("")
        log(f"{WARN} No se detecto manage.py en esta carpeta.")
        log(f"{WARN} Asegurate de ejecutar este script en la raiz del proyecto Django.")
        respuesta = input("\n¿Continuar de todas formas? (s/N): ").strip().lower()
        if respuesta != 's':
            log("Cancelado por el usuario.")
            sys.exit(1)

    resultados = []
    resultados.append(modificar_forms())
    resultados.append(modificar_views())
    resultados.append(modificar_base_html())
    resultados.append(reemplazar_template_cambiar())
    resultados.append(crear_estaticos())

    resumen(resultados)


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