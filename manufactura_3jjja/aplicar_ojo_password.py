#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aplicar_ojo_password.py
=======================
Ejecutar desde la MISMA carpeta donde esta manage.py:

    cd ruta/al/proyecto/   (donde esta manage.py)
    python aplicar_ojo_password.py

El script:
  1) Verifica que exista manage.py en la carpeta actual.
  2) Busca automaticamente admin_usuarios.html en todo el proyecto.
  3) Hace copia de seguridad con fecha y hora.
  4) Inserta el boton del ojo (bi-eye-slash <-> bi-eye) en los campos
     de contrasena del modal "Cambiar Contrasena".
  5) No modifica ningun otro archivo ni funcion.
  6) Es idempotente (si ya esta aplicado, no duplica).
"""

import os
import re
import shutil
import sys
from datetime import datetime

# ============================================================
# 1) COMPROBAR QUE ESTAMOS EN LA RAIZ (donde esta manage.py)
# ============================================================
def verificar_raiz():
    if not os.path.isfile("manage.py"):
        print("\n\033[91m[ERROR]\033[0m No se encontro 'manage.py' en la carpeta actual.")
        print("Carpeta actual:", os.getcwd())
        print("\nDebes ejecutar este script DESDE la carpeta que contiene manage.py.")
        print("Ejemplo:")
        print("    cd C:\\ruta\\a\\tu\\proyecto")
        print("    python aplicar_ojo_password.py")
        sys.exit(1)
    print("\033[92m[OK]\033[0m Encontrado manage.py en:", os.getcwd())


# ============================================================
# 2) BUSCAR admin_usuarios.html EN TODO EL PROYECTO
# ============================================================
def buscar_archivo(nombre):
    """Busca recursivamente un archivo por nombre. Devuelve la ruta o None."""
    for raiz, dirs, archivos in os.walk("."):
        # Ignorar carpetas tipicas que no nos interesan
        dirs[:] = [d for d in dirs if d not in
                   (".git", "__pycache__", "venv", ".venv", "env",
                    "node_modules", "backup", ".idea", ".vscode")]
        if nombre in archivos:
            return os.path.join(raiz, nombre)
    return None


# ============================================================
# 3) BACKUP
# ============================================================
def hacer_backup(ruta):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    carpeta = "backup_ojo_password_" + stamp
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, os.path.basename(ruta))
    shutil.copy2(ruta, destino)
    print("\033[92m[OK]\033[0m Backup creado:", destino)
    return carpeta


# ============================================================
# 4) BLOQUE CSS + JS QUE SE INSERTA EN admin_usuarios.html
# ============================================================
MARCADOR = "toggle-password-eye"

BLOQUE = """
<!-- ===== OJO MOSTRAR/OCULTAR CONTRASENA (inyectado automaticamente) ===== -->
<style>
    .toggle-password-eye {
        position: absolute;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
        background: transparent;
        border: none;
        color: #94a3b8;
        cursor: pointer;
        padding: 4px 8px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        z-index: 5;
        transition: color 0.2s ease;
    }
    .toggle-password-eye:hover { color: #10b981; }
    .toggle-password-eye:focus { outline: none; }

    /* Sobrescribe la regla '.input-icon-wrap i' que posicionaba el icono a la izquierda */
    .input-icon-wrap .toggle-password-eye i {
        position: static !important;
        left: auto !important;
        top: auto !important;
        transform: none !important;
        color: inherit !important;
        font-size: 1.05rem !important;
    }
    .input-icon-wrap .form-control-dark {
        padding-right: 42px !important;
    }
</style>

<script>
    // Alterna visibilidad del campo y cambia el icono:
    //  oculta   ->  bi-eye-slash  (ojo con raya)
    //  visible  ->  bi-eye        (ojo abierto)
    function togglePasswordEye(inputId, btn) {
        var input = document.getElementById(inputId);
        if (!input) return;
        var icon = btn.querySelector('i');
        if (input.type === 'password') {
            input.type = 'text';
            if (icon) icon.className = 'bi bi-eye';
        } else {
            input.type = 'password';
            if (icon) icon.className = 'bi bi-eye-slash';
        }
    }

    // Al cerrar el modal se resetea todo (oculto + icono con raya).
    document.addEventListener('DOMContentLoaded', function () {
        if (typeof window.cerrarModalPassword === 'function') {
            var _orig = window.cerrarModalPassword;
            window.cerrarModalPassword = function () {
                try { _orig(); } catch (e) {}
                ['nueva_password', 'confirmar_password'].forEach(function (id) {
                    var inp = document.getElementById(id);
                    if (inp) inp.type = 'password';
                });
                var iconos = document.querySelectorAll('.toggle-password-eye i');
                for (var i = 0; i < iconos.length; i++) {
                    iconos[i].className = 'bi bi-eye-slash';
                }
            };
        }
    });
</script>
"""


# ============================================================
# 5) APLICAR CAMBIOS EN admin_usuarios.html
# ============================================================
# Detecta los <input type="password" ... id="nueva_password" ...>
#                           <input ... id="confirmar_password" ...>
PATRON_INPUT = re.compile(
    r'(<input\b[^>]*?\bid="(nueva_password|confirmar_password)"[^>]*?>)',
    re.MULTILINE
)


def aplicar_cambios(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()

    if MARCADOR in contenido:
        print("\033[93m[!]\033[0m Ya estaba aplicado el ojo en ese archivo. Se omite.")
        return False

    # --- Insertar boton del ojo despues de cada input ---
    def reemplazo(m):
        tag = m.group(1)
        input_id = m.group(2)
        boton = (
            '\n                        '
            f'<button type="button" class="toggle-password-eye" '
            f'onclick="togglePasswordEye(\'{input_id}\', this)" '
            f'title="Mostrar / ocultar contrase\u00f1a" '
            f'aria-label="Mostrar u ocultar contrase\u00f1a">'
            f'\n                            <i class="bi bi-eye-slash"></i>'
            f'\n                        </button>'
        )
        return tag + boton

    nuevo, n = PATRON_INPUT.subn(reemplazo, contenido)
    if n == 0:
        print("\033[91m[ERROR]\033[0m No se encontraron los campos 'nueva_password' /")
        print("        'confirmar_password' en admin_usuarios.html.")
        print("        Es posible que la plantilla haya cambiado.")
        return False
    print("\033[92m[OK]\033[0m Boton de ojo insertado en {} campo(s).".format(n))

    # --- Insertar CSS+JS antes del ULTIMO {% endblock %} ---
    if "{% endblock %}" not in nuevo:
        print("\033[91m[ERROR]\033[0m No se encontro '{% endblock %}' en la plantilla.")
        return False
    idx = nuevo.rfind("{% endblock %}")
    nuevo = nuevo[:idx] + BLOQUE + "\n" + nuevo[idx:]

    with open(ruta, "w", encoding="utf-8") as f:
        f.write(nuevo)

    print("\033[92m[OK]\033[0m CSS + JS inyectados correctamente.")
    print("\033[92m[OK]\033[0m Archivo guardado:", ruta)
    return True


# ============================================================
# 6) MAIN
# ============================================================
def main():
    print("=" * 62)
    print("  Aplicando OJO mostrar/ocultar contrasena")
    print("=" * 62)

    verificar_raiz()

    print("\n[1/3] Buscando 'admin_usuarios.html' en el proyecto...")
    ruta = buscar_archivo("admin_usuarios.html")
    if not ruta:
        print("\033[91m[ERROR]\033[0m No se encontro 'admin_usuarios.html' en el proyecto.")
        sys.exit(1)
    print("\033[92m[OK]\033[0m Encontrado en:", ruta)

    print("\n[2/3] Creando copia de seguridad...")
    hacer_backup(ruta)

    print("\n[3/3] Aplicando cambios...")
    aplicado = aplicar_cambios(ruta)

    print("\n" + "=" * 62)
    if aplicado:
        print("  LISTO. Reinicia el servidor y prueba el modal.")
    else:
        print("  No se aplicaron cambios (ya estaba hecho o hubo un aviso).")
    print("=" * 62)


if __name__ == "__main__":
    main()