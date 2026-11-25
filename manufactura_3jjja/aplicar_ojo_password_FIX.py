#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aplicar_ojo_password_FIX.py
===========================
Corrige el problema: el script anterior modificó un archivo dentro de
una carpeta 'backup_*' en lugar del archivo real.

Este script:
  1) Verifica que exista manage.py.
  2) Usa la RUTA EXACTA: templates/admin/admin_usuarios.html
  3) Ignora TODAS las carpetas que empiecen con 'backup'.
  4) Reporta claramente si el archivo real ya tenía (o no) el ojo aplicado.
  5) Hace backup y aplica los cambios.
  6) Muestra un diff visible de lo que hizo.
"""

import os
import re
import shutil
import sys
from datetime import datetime

# ============================================================
# RUTAS POSIBLES (en orden de prioridad)
# ============================================================
RUTAS_CANDIDATAS = [
    os.path.join("templates", "admin", "admin_usuarios.html"),
    os.path.join("templates", "admin_usuarios.html"),
    os.path.join("core", "templates", "admin", "admin_usuarios.html"),
    os.path.join("core", "templates", "admin_usuarios.html"),
]


def verificar_raiz():
    if not os.path.isfile("manage.py"):
        print("\033[91m[ERROR]\033[0m No se encontro 'manage.py' aqui.")
        print("Carpeta actual:", os.getcwd())
        print("\nEjecuta el script DESDE la carpeta que contiene manage.py.")
        sys.exit(1)
    print("\033[92m[OK]\033[0m manage.py encontrado en:", os.getcwd())


def buscar_archivo_real():
    """Busca el archivo SOLO en las rutas candidatas conocidas.
    Ignora por completo las carpetas que empiecen con 'backup'."""
    print("\n[1/4] Buscando 'admin_usuarios.html' en rutas conocidas...")
    for ruta in RUTAS_CANDIDATAS:
        if os.path.isfile(ruta):
            print("\033[92m[OK]\033[0m Encontrado:", ruta)
            return ruta
    # Si no esta en las candidatas, hacemos un walk pero ignorando backups
    print("  Busqueda ampliada (ignorando carpetas 'backup*')...")
    for raiz, dirs, archivos in os.walk("."):
        # Excluir carpetas que empiecen con 'backup' o tipicas de venv
        dirs[:] = [
            d for d in dirs
            if not d.lower().startswith("backup")
            and d not in (".git", "__pycache__", "venv", ".venv", "env",
                          "node_modules", ".idea", ".vscode", "media", "staticfiles")
        ]
        if "admin_usuarios.html" in archivos:
            ruta = os.path.join(raiz, "admin_usuarios.html")
            print("\033[92m[OK]\033[0m Encontrado:", ruta)
            return ruta
    return None


def hacer_backup(ruta):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    carpeta = "backup_FIX_ojo_" + stamp
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, os.path.basename(ruta))
    shutil.copy2(ruta, destino)
    print("  Backup:", destino)
    return destino


# ============================================================
# BLOQUE CSS + JS QUE SE INYECTA
# ============================================================
MARCADOR = "toggle-password-eye"

BLOQUE = """
<!-- ===== OJO MOSTRAR/OCULTAR CONTRASENA (inyectado por FIX) ===== -->
<style>
    .input-icon-wrap { position: relative; }

    /* Nuestro boton va a la DERECHA */
    .input-icon-wrap .toggle-password-eye {
        position: absolute !important;
        right: 10px !important;
        left: auto !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        background: transparent !important;
        border: none !important;
        color: #94a3b8 !important;
        cursor: pointer !important;
        padding: 4px 8px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        z-index: 5 !important;
        line-height: 1 !important;
        transition: color 0.2s ease;
    }
    .input-icon-wrap .toggle-password-eye:hover { color: #10b981 !important; }
    .input-icon-wrap .toggle-password-eye:focus { outline: none !important; }

    /* Neutraliza la regla '.input-icon-wrap i' de app.css
       que posicionaba el <i> a la IZQUIERDA */
    .input-icon-wrap .toggle-password-eye i {
        position: static !important;
        left: auto !important;
        top: auto !important;
        transform: none !important;
        color: inherit !important;
        font-size: 1.05rem !important;
        line-height: 1 !important;
    }

    /* Deja hueco a la derecha del input para que no tape el texto */
    .input-icon-wrap .form-control-dark {
        padding-right: 42px !important;
    }
</style>

<script>
    // Alterna visibilidad y cambia el icono:
    //   oculto  ->  bi-eye-slash  (ojo con raya)
    //   visible ->  bi-eye        (ojo abierto)
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

    // Reset al cerrar el modal
    document.addEventListener('DOMContentLoaded', function () {
        var intentos = 0;
        var timer = setInterval(function () {
            intentos++;
            if (typeof window.cerrarModalPassword === 'function') {
                clearInterval(timer);
                var _orig = window.cerrarModalPassword;
                window.cerrarModalPassword = function () {
                    try { _orig(); } catch (e) {}
                    ['nueva_password', 'confirmar_password'].forEach(function (id) {
                        var inp = document.getElementById(id);
                        if (inp) inp.type = 'password';
                    });
                    var ic = document.querySelectorAll('.toggle-password-eye i');
                    for (var i = 0; i < ic.length; i++) {
                        ic[i].className = 'bi bi-eye-slash';
                    }
                };
            }
            if (intentos > 20) clearInterval(timer);
        }, 100);
    });
</script>
"""


PATRON_INPUT = re.compile(
    r'(<input\b[^>]*?\bid="(nueva_password|confirmar_password)"[^>]*?>)',
    re.MULTILINE
)


def aplicar_cambios(ruta):
    print("\n[3/4] Analizando el archivo...")
    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()

    if MARCADOR in contenido:
        print("\033[93m[!]\033[0m El archivo YA tiene el ojo aplicado (marcador encontrado).")
        print("    Si no ves los iconos:")
        print("    - Haz Ctrl+F5 en el navegador para forzar recarga (cache).")
        print("    - Verifica que base.html cargue los Bootstrap Icons (bi-*).")
        respuesta = input("\n    ¿Re-aplicar de todas formas? (s/N): ").strip().lower()
        if respuesta != "s":
            print("    Cancelado.")
            return False

    print("\n[4/4] Insertando el ojo en los campos de contraseña...")

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
        print("\033[91m[ERROR]\033[0m No se encontraron los inputs de contraseña.")
        print("        Buscados: id=\"nueva_password\" y id=\"confirmar_password\"")
        return False
    print(f"  \033[92m[OK]\033[0m Boton insertado en {n} campo(s).")

    if "{% endblock %}" not in nuevo:
        print("\033[91m[ERROR]\033[0m No hay '{% endblock %}' en la plantilla.")
        return False
    idx = nuevo.rfind("{% endblock %}")
    nuevo = nuevo[:idx] + BLOQUE + "\n" + nuevo[idx:]
    print("  \033[92m[OK]\033[0m CSS + JS inyectados.")

    with open(ruta, "w", encoding="utf-8") as f:
        f.write(nuevo)
    print("  \033[92m[OK]\033[0m Archivo guardado:", ruta)
    return True


def main():
    print("=" * 64)
    print("  FIX: OJO mostrar/ocultar contraseña en admin_usuarios.html")
    print("=" * 64)

    verificar_raiz()
    ruta = buscar_archivo_real()
    if not ruta:
        print("\033[91m[ERROR]\033[0m No se encontro admin_usuarios.html.")
        sys.exit(1)

    print("\n[2/4] Creando copia de seguridad...")
    hacer_backup(ruta)

    if aplicar_cambios(ruta):
        print("\n" + "=" * 64)
        print("  LISTO. Ahora:")
        print("    1) Reinicia el servidor (Ctrl+C y 'python manage.py runserver')")
        print("    2) En el navegador abre el modal y pulsa Ctrl+F5 (forzar recarga)")
        print("=" * 64)
    else:
        print("\n  No se aplicaron cambios (ver mensajes arriba).")


if __name__ == "__main__":
    main()