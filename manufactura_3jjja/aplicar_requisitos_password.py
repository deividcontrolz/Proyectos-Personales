#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
aplicar_requisitos_password.py
------------------------------
Aplica automaticamente los cambios para forzar los requisitos COMPLETOS
de contraseña en todo el sistema 3-JJJ-A:

    - Minimo 8 caracteres, maximo 12
    - Al menos una letra
    - Al menos un numero
    - Al menos un caracter especial
    - No puede ser 100% numerica

Archivos modificados:
    1. core/forms.py      -> agrega helper + arregla CambiarPasswordTemporalForm
    2. core/views.py      -> importa helper + arregla bloque cambiar_password
    3. static/js/app.js   -> arregla funcion validarPassword
    4. templates/admin/admin_usuarios.html -> inputs 8-12 + nota visual

USO:
    1. Colocar este archivo en la misma carpeta que manage.py
    2. Ejecutar:  python aplicar_requisitos_password.py

Hace backups automaticos en _backup_requisitos_FECHA_HORA/
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ------------------------------------------------------------
# CONFIGURACION
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
BACKUP_DIR = BASE_DIR / f"_backup_requisitos_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

OK = "[OK]"
ERR = "[ERROR]"
WARN = "[AVISO]"
SKIP = "[SALTADO]"


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


def ya_aplicado(texto, marcador):
    """Devuelve True si el marcador ya esta en el archivo."""
    return marcador in texto


# ------------------------------------------------------------
# TEXTO DEL HELPER A INSERTAR EN forms.py
# ------------------------------------------------------------
HELPER_PASSWORD = '''

# ============================================================
# HELPER: Validacion reutilizable de contrasenas seguras
# ============================================================
def validar_password_completa(password):
    """Valida que una contrasena cumpla TODOS los requisitos.

    Devuelve None si es valida, o un mensaje de error (str) si no lo es.
    Requisitos:
        - Entre 8 y 12 caracteres
        - Al menos una letra
        - Al menos un numero
        - Al menos un caracter especial
        - No puede ser completamente numerica
    """
    if not password:
        return 'La contrasena es obligatoria.'
    if len(password) < 8:
        return 'La contrasena debe tener al menos 8 caracteres.'
    if len(password) > 12:
        return 'La contrasena no puede exceder 12 caracteres.'
    if password.isdigit():
        return 'La contrasena no puede ser completamente numerica.'
    if not re.search(r'[a-zA-Z]', password):
        return 'La contrasena debe contener al menos una letra.'
    if not re.search(r'[0-9]', password):
        return 'La contrasena debe contener al menos un numero.'
    if not re.search(r'[!@#$%^&*(),.?":{}|<>\\[\\]\\-_=+`~]', password):
        return 'La contrasena debe contener al menos un caracter especial.'
    return None


'''

# ------------------------------------------------------------
# TEXTO DE LA NUEVA CambiarPasswordTemporalForm
# ------------------------------------------------------------
NUEVA_CAMBIAR_FORM = '''class CambiarPasswordTemporalForm(forms.Form):
    password1 = forms.CharField(
        label='Nueva Contrasena',
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
            'min_length': 'La contrasena debe tener al menos 8 caracteres.',
            'max_length': 'La contrasena no puede exceder 12 caracteres.',
        },
    )
    password2 = forms.CharField(
        label='Confirmar Contrasena',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-dark',
            'placeholder': 'Repita la contrasena (8 a 12 caracteres)',
            'id': 'id_password2',
            'minlength': '8',
            'maxlength': '12',
            'autocomplete': 'new-password',
        }),
        min_length=8,
        max_length=12,
        error_messages={
            'min_length': 'La confirmacion debe tener al menos 8 caracteres.',
            'max_length': 'La confirmacion no puede exceder 12 caracteres.',
        },
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')

        # Validacion completa (letra, numero, especial, no 100% numerica)
        error = validar_password_completa(p1)
        if error:
            raise forms.ValidationError(error)

        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contrasenas no coinciden.')

        return cleaned
'''

# ------------------------------------------------------------
# BLOQUE NUEVO PARA views.py (cambiar_password)
# ------------------------------------------------------------
NUEVO_BLOQUE_VIEWS = """        elif accion == 'cambiar_password' and usuario_id:
            nueva_password = request.POST.get('nueva_password', '').strip()
            confirmar_password = request.POST.get('confirmar_password', '').strip()

            # Validacion completa (longitud, letra, numero, especial, no 100% numerica)
            error = validar_password_completa(nueva_password)
            if error:
                messages.error(request, error)
            elif nueva_password != confirmar_password:
                messages.error(request, 'Las contrasenas no coinciden. Por favor verifique.')
            else:
                try:
                    user = Usuario.objects.get(id_usuario=usuario_id)
                    user.set_password(nueva_password)
                    user.save()
                    marcar_password_temporal(usuario_id)
                    messages.success(
                        request,
                        f'Contrasena temporal asignada a {usuario_id}. '
                        f'El usuario debera cambiarla al iniciar sesion.'
                    )
                except Usuario.DoesNotExist:
                    messages.error(request, 'Usuario no encontrado.')
            return redirect('core:admin_usuarios')"""

# ------------------------------------------------------------
# NUEVA FUNCION validarPassword PARA app.js
# ------------------------------------------------------------
NUEVA_FUNCION_JS = """window.validarPassword = function(e) {
    if (!nuevaPass || !confirmarPass || !errorMsg || !errorText) return true;
    var p1 = nuevaPass.value.trim();
    var p2 = confirmarPass.value.trim();

    function mostrarError(msg, campo) {
        errorText.textContent = msg;
        errorMsg.classList.add('visible');
        if (campo) campo.focus();
        if (e && e.preventDefault) e.preventDefault();
        return false;
    }

    if (p1.length < 8) {
        return mostrarError('La contraseña debe tener al menos 8 caracteres.', nuevaPass);
    }
    if (p1.length > 12) {
        return mostrarError('La contraseña no puede exceder 12 caracteres.', nuevaPass);
    }
    if (/^\\d+$/.test(p1)) {
        return mostrarError('La contraseña no puede ser completamente numérica.', nuevaPass);
    }
    if (!/[a-zA-Z]/.test(p1)) {
        return mostrarError('La contraseña debe contener al menos una letra.', nuevaPass);
    }
    if (!/[0-9]/.test(p1)) {
        return mostrarError('La contraseña debe contener al menos un número.', nuevaPass);
    }
    if (!/[!@#$%^&*(),.?":{}|<>\\[\\]\\-_=+`~]/.test(p1)) {
        return mostrarError('La contraseña debe contener al menos un carácter especial.', nuevaPass);
    }
    if (p1 !== p2) {
        return mostrarError('Las contraseñas no coinciden. Por favor verifique.', confirmarPass);
    }

    errorMsg.classList.remove('visible');
    return true;
};"""


# ============================================================
# 1. MODIFICAR core/forms.py
# ============================================================
def modificar_forms():
    log("\n=== [1/4] Modificando core/forms.py ===")
    path = buscar_archivo(['core/forms.py', 'forms.py'])
    if not path:
        log(f"    {ERR} No se encontro forms.py")
        return False

    hacer_backup(path)
    texto = leer(path)
    cambios = 0

    # --- 1.1 Insertar helper despues de la ultima linea de import ---
    if ya_aplicado(texto, 'def validar_password_completa(password):'):
        log(f"    {SKIP} Helper validar_password_completa ya estaba presente")
    else:
        # Buscamos el final del bloque de imports (despues de "    SEVERIDAD_CHOICES\n)")
        patron_import_fin = re.compile(
            r"(from \.models import \([^)]*?SEVERIDAD_CHOICES\s*\n\))",
            re.DOTALL,
        )
        match = patron_import_fin.search(texto)
        if match:
            pos = match.end()
            texto = texto[:pos] + HELPER_PASSWORD + texto[pos:]
            log(f"    {OK} Helper validar_password_completa insertado")
            cambios += 1
        else:
            log(f"    {WARN} No se encontro el fin del bloque de imports")
            log(f"    {WARN} Agrega manualmente la funcion validar_password_completa")

    # --- 1.2 Reemplazar clase CambiarPasswordTemporalForm completa ---
    patron_cambiar = re.compile(
        r"class CambiarPasswordTemporalForm\(forms\.Form\):.*?(?=\Z)",
        re.DOTALL,
    )
    if patron_cambiar.search(texto):
        # Solo reemplazar si el bloque actual NO tiene la llamada al helper
        bloque_actual = patron_cambiar.search(texto).group(0)
        if 'validar_password_completa(p1)' in bloque_actual:
            log(f"    {SKIP} CambiarPasswordTemporalForm ya usa el helper")
        else:
            # Conservar todo lo que venga DESPUES de la clase (si lo hubiera)
            texto = patron_cambiar.sub(NUEVA_CAMBIAR_FORM + '\n', texto)
            log(f"    {OK} CambiarPasswordTemporalForm reemplazada")
            cambios += 1
    else:
        log(f"    {WARN} No se encontro class CambiarPasswordTemporalForm")

    escribir(path, texto)
    log(f"    {OK} forms.py guardado ({cambios} cambios aplicados)")
    return cambios > 0


# ============================================================
# 2. MODIFICAR core/views.py
# ============================================================
def modificar_views():
    log("\n=== [2/4] Modificando core/views.py ===")
    path = buscar_archivo(['core/views.py', 'views.py'])
    if not path:
        log(f"    {ERR} No se encontro views.py")
        return False

    hacer_backup(path)
    texto = leer(path)
    cambios = 0

    # --- 2.1 Importar el helper ---
    if 'validar_password_completa,' in texto and 'from .forms import' in texto:
        log(f"    {SKIP} Import de validar_password_completa ya presente")
    else:
        viejo_import = """from .forms import (
    IncidenteForm, ActualizarIncidenteForm,
    ModeloCalzadoForm, BusquedaModeloForm, RegistroUsuarioForm,
    LoginForm, MaquinariaForm,
    CambiarPasswordTemporalForm,
)"""
        nuevo_import = """from .forms import (
    IncidenteForm, ActualizarIncidenteForm,
    ModeloCalzadoForm, BusquedaModeloForm, RegistroUsuarioForm,
    LoginForm, MaquinariaForm,
    CambiarPasswordTemporalForm,
    validar_password_completa,
)"""
        texto, ok = reemplazar_exacto(texto, viejo_import, nuevo_import, "import de forms")
        if ok:
            log(f"    {OK} Import de validar_password_completa agregado")
            cambios += 1

    # --- 2.2 Reemplazar bloque cambiar_password ---
    patron = re.compile(
        r"        elif accion == 'cambiar_password' and usuario_id:.*?"
        r"(?=\n        return redirect\('core:admin_usuarios'\))",
        re.DOTALL,
    )
    match = patron.search(texto)
    if match:
        bloque = match.group(0)
        if 'validar_password_completa(nueva_password)' in bloque:
            log(f"    {SKIP} Bloque cambiar_password ya usa el helper")
        else:
            texto = texto[:match.start()] + NUEVO_BLOQUE_VIEWS + texto[match.end():]
            log(f"    {OK} Bloque cambiar_password actualizado")
            cambios += 1
    else:
        log(f"    {WARN} No se encontro el bloque 'cambiar_password' en admin_usuarios_view")

    escribir(path, texto)
    log(f"    {OK} views.py guardado ({cambios} cambios aplicados)")
    return cambios > 0


# ============================================================
# 3. MODIFICAR static/js/app.js
# ============================================================
def modificar_app_js():
    log("\n=== [3/4] Modificando static/js/app.js ===")

    # Buscar el archivo en las ubicaciones tipicas
    path = buscar_archivo([
        'static/js/app.js',
        'core/static/js/app.js',
    ])
    if not path:
        log(f"    {ERR} No se encontro app.js")
        return False

    hacer_backup(path)
    texto = leer(path)

    # Reemplazar SOLO la funcion window.validarPassword
    # Buscamos desde "window.validarPassword = function(e) {" hasta el "};" que la cierra.
    patron = re.compile(
        r"window\.validarPassword\s*=\s*function\s*\(e\)\s*\{.*?\n\};",
        re.DOTALL,
    )
    match = patron.search(texto)
    if not match:
        log(f"    {WARN} No se encontro la funcion validarPassword en app.js")
        log(f"    {WARN} app.js se deja sin cambios")
        return False

    bloque_actual = match.group(0)
    if 'completamente numérica' in bloque_actual and 'carácter especial' in bloque_actual:
        log(f"    {SKIP} validarPassword ya tiene los requisitos completos")
        return True

    texto = texto[:match.start()] + NUEVA_FUNCION_JS + texto[match.end():]
    escribir(path, texto)
    log(f"    {OK} validarPassword reemplazada con requisitos completos")
    log(f"    {OK} app.js guardado")
    return True


# ============================================================
# 4. MODIFICAR templates/admin/admin_usuarios.html
# ============================================================
NOTA_REQUISITOS_HTML = """            <div style="background: rgba(59,130,246,0.08); border: 1px solid rgba(59,130,246,0.25);
                        color: #93c5fd; padding: 10px 12px; border-radius: 8px;
                        font-size: 0.78rem; line-height: 1.4; margin-bottom: 14px;">
                <i class="bi bi-shield-check"></i>
                <strong>Requisitos:</strong> 8&ndash;12 caracteres, al menos 1 letra,
                1 n&uacute;mero y 1 car&aacute;cter especial (<code>!@#$%...</code>).
            </div>
"""


def modificar_admin_usuarios():
    log("\n=== [4/4] Modificando templates/admin/admin_usuarios.html ===")
    path = buscar_archivo([
        'templates/admin/admin_usuarios.html',
        'core/templates/admin/admin_usuarios.html',
    ])
    if not path:
        log(f"    {WARN} No se encontro admin_usuarios.html")
        return False

    hacer_backup(path)
    texto = leer(path)
    cambios = 0

    # --- 4.1 Input nueva_password ---
    viejo_p1 = '''<input type="password" name="nueva_password" id="nueva_password"
                        class="form-control-dark" placeholder="Min. 8 caracteres"
                        minlength="4" maxlength="50" required
                        oninput="checkStrength(); checkMatch();">'''
    nuevo_p1 = '''<input type="password" name="nueva_password" id="nueva_password"
                        class="form-control-dark" placeholder="8 a 12 caracteres"
                        minlength="8" maxlength="12" required
                        oninput="checkStrength(); checkMatch();">'''
    texto, ok = reemplazar_exacto(texto, viejo_p1, nuevo_p1, "input nueva_password")
    if ok:
        log(f"    {OK} Input nueva_password actualizado (8-12)")
        cambios += 1

    # --- 4.2 Input confirmar_password ---
    viejo_p2 = '''<input type="password" name="confirmar_password" id="confirmar_password"
                        class="form-control-dark" placeholder="Repite la contraseña"
                        minlength="4" maxlength="50" required
                        oninput="checkMatch();">'''
    nuevo_p2 = '''<input type="password" name="confirmar_password" id="confirmar_password"
                        class="form-control-dark" placeholder="Repite la contraseña (8 a 12)"
                        minlength="8" maxlength="12" required
                        oninput="checkMatch();">'''
    texto, ok = reemplazar_exacto(texto, viejo_p2, nuevo_p2, "input confirmar_password")
    if ok:
        log(f"    {OK} Input confirmar_password actualizado (8-12)")
        cambios += 1

    # --- 4.3 Insertar nota de requisitos despues del match-indicator ---
    if 'Requisitos:' in texto and 'car&aacute;cter especial' in texto:
        log(f"    {SKIP} Nota de requisitos ya estaba presente")
    else:
        ancla = '''<div class="match-indicator" id="matchIndicator">
                    <i class="bi bi-info-circle"></i>
                    <span>Las contraseñas deben coincidir</span>
                </div>'''
        if ancla in texto:
            reemplazo = ancla + '\n' + NOTA_REQUISITOS_HTML
            texto = texto.replace(ancla, reemplazo, 1)
            log(f"    {OK} Nota de requisitos insertada en el modal")
            cambios += 1
        else:
            log(f"    {WARN} No se encontro el match-indicator; nota no insertada")

    escribir(path, texto)
    log(f"    {OK} admin_usuarios.html guardado ({cambios} cambios aplicados)")
    return cambios > 0


# ============================================================
# RESUMEN
# ============================================================
def resumen(resultados):
    log("\n" + "=" * 60)
    log("RESUMEN")
    log("=" * 60)
    nombres = [
        "1. core/forms.py (helper + CambiarPasswordTemporalForm)",
        "2. core/views.py (import + bloque cambiar_password)",
        "3. static/js/app.js (validarPassword)",
        "4. templates/admin/admin_usuarios.html (inputs + nota)",
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
        log("  3. Prueba estas contraseñas:")
        log("       - '12345678'  -> DEBE FALLAR (100% numerica)")
        log("       - 'abcdefgh'  -> DEBE FALLAR (sin numero ni especial)")
        log("       - 'abcd1234'  -> DEBE FALLAR (sin especial)")
        log("       - 'Abc123!@'  -> DEBE PASAR (8 caracteres, todo OK)")
        log("       - 'Abcdef123!'-> DEBE PASAR (11 caracteres)")
    else:
        log(f"{WARN} Algunos cambios requirieron atencion manual.")
        log("  Revisa los mensajes [AVISO] arriba.")

    log("")
    log(f"Backups guardados en: {BACKUP_DIR.name}/")
    log("Si algo sale mal, copia los archivos de ahi sobre los originales.")
    log("=" * 60)


# ============================================================
# MAIN
# ============================================================
def main():
    log("=" * 60)
    log("APLICADOR DE REQUISITOS COMPLETOS DE CONTRASENA")
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
    resultados.append(modificar_app_js())
    resultados.append(modificar_admin_usuarios())

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