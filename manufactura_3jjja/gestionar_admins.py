#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gestionar_admins.py v2 - Gestor de administradores en DOS FASES

1ª EJECUCIÓN:
    - Menú para eliminar admins dejando solo uno.

2ª EJECUCIÓN (y posteriores):
    - OCULTA a los administradores en la lista de usuarios (interfaz).
    - OCULTA el botón eliminar en el template.
    - BLOQUEA eliminar admins desde la vista.
    - NO altera ninguna otra función del sistema.
"""

import os
import sys
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

# ============================================================
# 1. LOCALIZAR PROYECTO Y CONFIGURAR DJANGO
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
MANAGE_PY = BASE_DIR / 'manage.py'


def _err(msg):
    print(f"\n[ERROR] {msg}\n")
    sys.exit(1)


def _ok(msg):
    print(f"  [OK] {msg}")


def _info(msg):
    print(f"  [i]  {msg}")


def _warn(msg):
    print(f"  [!]  {msg}")


if not MANAGE_PY.exists():
    _err(f"No se encontró manage.py en:\n  {BASE_DIR}\n"
         f"Coloca este script en la raíz del proyecto Django.")

try:
    contenido_manage = MANAGE_PY.read_text(encoding='utf-8')
except Exception as e:
    _err(f"No se pudo leer manage.py: {e}")

m = re.search(r"DJANGO_SETTINGS_MODULE['\"]?\s*[,=]\s*['\"]([^'\"]+)['\"]", contenido_manage)
if not m:
    m = re.search(r"setdefault\(\s*['\"]DJANGO_SETTINGS_MODULE['\"]\s*,\s*['\"]([^'\"]+)['\"]", contenido_manage)
if not m:
    _err("No se pudo detectar DJANGO_SETTINGS_MODULE en manage.py")

os.environ['DJANGO_SETTINGS_MODULE'] = m.group(1)
sys.path.insert(0, str(BASE_DIR))

try:
    import django
    django.setup()
except Exception as e:
    _err(f"Error al inicializar Django: {e}")

Usuario = None
try:
    from core.models import Usuario
except Exception:
    try:
        from django.contrib.auth import get_user_model
        Usuario = get_user_model()
    except Exception as e:
        _err(f"No se pudo importar el modelo Usuario: {e}")


# ============================================================
# 2. RUTAS Y ESTADO
# ============================================================
RUTA_ESTADO = BASE_DIR / 'media' / 'sistema' / 'admin_script_state.json'

_posibles_tpl = [
    BASE_DIR / 'core' / 'templates' / 'admin' / 'admin_usuarios.html',
    BASE_DIR / 'templates' / 'admin' / 'admin_usuarios.html',
    BASE_DIR / 'admin' / 'templates' / 'admin' / 'admin_usuarios.html',
    BASE_DIR / 'app' / 'templates' / 'admin' / 'admin_usuarios.html',
]
RUTA_TEMPLATE = next((p for p in _posibles_tpl if p.exists()), None)

_posibles_views = [
    BASE_DIR / 'core' / 'views.py',
    BASE_DIR / 'app' / 'views.py',
    BASE_DIR / 'views.py',
]
RUTA_VIEWS = next((p for p in _posibles_views if p.exists()), None)


def cargar_estado():
    if RUTA_ESTADO.exists():
        try:
            return json.loads(RUTA_ESTADO.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {'fase': 'inicial', 'historial': []}


def guardar_estado(estado):
    RUTA_ESTADO.parent.mkdir(parents=True, exist_ok=True)
    RUTA_ESTADO.write_text(
        json.dumps(estado, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )


def _backup(ruta):
    try:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        destino = ruta.with_suffix(ruta.suffix + f'.bak_{ts}')
        shutil.copy2(ruta, destino)
        return destino
    except Exception as e:
        _warn(f"No se pudo crear backup de {ruta.name}: {e}")
        return None


# ============================================================
# 3. FASE 1 — ELIMINAR ADMINS (dejando solo uno)
# ============================================================
def fase_1_eliminar_admins():
    print("\n" + "=" * 62)
    print("  FASE 1 · ELIMINACIÓN DE ADMINISTRADORES")
    print("=" * 62)

    admins = list(Usuario.objects.filter(is_staff=True).order_by('id_usuario'))

    if not admins:
        _warn("No hay administradores en el sistema.")
        return []

    if len(admins) == 1:
        _info(f"Solo hay un administrador ({admins[0].id_usuario}). Nada que eliminar.")
        return []

    print(f"\n  Se encontraron {len(admins)} administradores:\n")
    print("  " + "-" * 58)
    for i, a in enumerate(admins, 1):
        estado_txt = "ACTIVO" if a.is_active else "INACTIVO"
        nombre = getattr(a, 'nombre_completo', '') or ''
        print(f"  [{i:>2}]  {a.id_usuario:<28} {nombre:<28} {estado_txt}")
    print("  " + "-" * 58)

    print("\n  Selecciona el administrador que deseas CONSERVAR.")
    conservar = None
    while conservar is None:
        try:
            entrada = input(f"\n  >> Opción a conservar (1-{len(admins)}): ").strip()
            if not entrada:
                continue
            idx = int(entrada) - 1
            if 0 <= idx < len(admins):
                conservar = admins[idx]
            else:
                _warn("Número fuera de rango.")
        except ValueError:
            _warn("Ingresa un número válido.")
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Operación cancelada por el usuario.")
            return []

    a_eliminar = [a for a in admins if a.id_usuario != conservar.id_usuario]

    print("\n" + "=" * 62)
    print("  RESUMEN DE LA OPERACIÓN")
    print("=" * 62)
    print(f"\n  CONSERVAR:  {conservar.id_usuario}  ({getattr(conservar, 'nombre_completo', '')})")
    print(f"\n  ELIMINAR:")
    for a in a_eliminar:
        print(f"     -  {a.id_usuario:<28} ({getattr(a, 'nombre_completo', '')})")

    print("\n  " + "!" * 58)
    print("  ESTA ACCIÓN NO SE PUEDE DESHACER")
    print("  " + "!" * 58)

    try:
        confirm = input("\n  Escribe 'CONFIRMAR' para proceder: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Operación cancelada.")
        return []

    if confirm != 'CONFIRMAR':
        _info("Confirmación incorrecta. Operación cancelada.")
        return []

    eliminados = []
    print()
    for admin in a_eliminar:
        uid = admin.id_usuario
        try:
            admin.delete()
            eliminados.append(uid)
            _ok(f"Eliminado: {uid}")
        except Exception as e:
            _warn(f"No se pudo eliminar {uid}: {e}")

    return eliminados


# ============================================================
# 4. FASE 2 — OCULTAR ADMINS Y BLOQUEAR ELIMINACIÓN
# ============================================================
MARCA_VIEW_OCULTAR = "# === OCULTAR_ADMINS_ACTIVO ==="
MARCA_VIEW_GUARDA = "# === BLOQUEO_ELIMINAR_ADMIN_ACTIVO ==="


def _view_ya_oculta_admins(texto):
    return MARCA_VIEW_OCULTAR in texto


def _view_ya_bloquea(texto):
    return MARCA_VIEW_GUARDA in texto


def _aplicar_ocultar_admins_en_view(texto):
    """
    Añade `.exclude(is_staff=True)` al queryset de usuarios en admin_usuarios_view.
    Busca el patrón:
        usuarios_qs = Usuario.objects.all().order_by('-fecha_registro')
    """
    patron = re.compile(
        r"(usuarios_qs\s*=\s*Usuario\.objects\.all\(\)(?:\.order_by\([^)]*\))?)"
    )

    def repl(match):
        original = match.group(1)
        # Si ya tiene exclude, no duplicar
        if 'exclude' in original:
            return original
        return (
            f"{MARCA_VIEW_OCULTAR}\n"
            f"    {original}.exclude(is_staff=True)"
        )

    nuevo, n = patron.subn(repl, texto, count=1)
    return nuevo, n


def _aplicar_guarda_eliminar(texto):
    """
    Añade una guarda al inicio del bloque 'if accion == "eliminar"'.
    """
    patron = re.compile(
        r"(\bif\s+accion\s*==\s*['\"]eliminar['\"]\s+and\s+usuario_id\s*:)"
    )
    guarda = (
        r"\1\n"
        f"            {MARCA_VIEW_GUARDA}\n"
        "            _target = Usuario.objects.filter(id_usuario=usuario_id).first()\n"
        "            if _target and _target.is_staff:\n"
        "                messages.error(request, 'No puede eliminar un administrador.')\n"
        "                return redirect('core:admin_usuarios')\n"
    )
    nuevo, n = patron.subn(guarda, texto, count=1)
    return nuevo, n


def _template_ya_protegido(texto):
    patron = re.compile(
        r"\{%\s*if\s+not\s+u\.is_staff\s*%\}.*?abrirModalEliminar.*?\{%\s*endif\s*%\}",
        re.DOTALL
    )
    return bool(patron.search(texto))


def fase_2_bloquear_y_ocultar():
    print("\n" + "=" * 62)
    print("  FASE 2 · OCULTAR ADMINS Y BLOQUEAR ELIMINACIÓN")
    print("=" * 62)

    cambios = []

    # -------- 4.1 VIEWS.PY --------
    print("\n  [1/2] Modificando views.py ...")
    if RUTA_VIEWS is None:
        _warn("No se encontró views.py. Saltando.")
    else:
        _info(f"Ruta: {RUTA_VIEWS.relative_to(BASE_DIR)}")
        try:
            texto_view = RUTA_VIEWS.read_text(encoding='utf-8')
        except Exception as e:
            _warn(f"No se pudo leer views.py: {e}")
            texto_view = None

        if texto_view is None:
            pass
        else:
            backup = _backup(RUTA_VIEWS)
            if backup:
                _info(f"Backup: {backup.name}")

            modificado = False

            # --- Ocultar admins del listado ---
            if _view_ya_oculta_admins(texto_view):
                _ok("La vista YA oculta admins del listado.")
            else:
                nuevo_view, n = _aplicar_ocultar_admins_en_view(texto_view)
                if n > 0:
                    texto_view = nuevo_view
                    _ok("Aplicado: .exclude(is_staff=True) en usuarios_qs")
                    modificado = True
                else:
                    _warn("No se encontró el patrón 'usuarios_qs = Usuario.objects.all()...'")
                    _info("Aplica manualmente: añade .exclude(is_staff=True) al queryset")

            # --- Guarda de seguridad al eliminar ---
            if _view_ya_bloquea(texto_view):
                _ok("La vista YA bloquea eliminar admins.")
            else:
                nuevo_view, n = _aplicar_guarda_eliminar(texto_view)
                if n > 0:
                    texto_view = nuevo_view
                    _ok("Aplicada: guarda de seguridad al eliminar.")
                    modificado = True
                else:
                    _warn("No se localizó el patrón 'accion == eliminar'. Revisa manualmente.")

            if modificado:
                try:
                    RUTA_VIEWS.write_text(texto_view, encoding='utf-8')
                    cambios.append('views')
                except Exception as e:
                    _warn(f"No se pudo escribir views.py: {e}")

    # -------- 4.2 TEMPLATE --------
    print("\n  [2/2] Modificando admin_usuarios.html ...")
    if RUTA_TEMPLATE is None:
        _warn("No se encontró el template admin_usuarios.html. Saltando.")
    else:
        _info(f"Ruta: {RUTA_TEMPLATE.relative_to(BASE_DIR)}")
        try:
            texto = RUTA_TEMPLATE.read_text(encoding='utf-8')
        except Exception as e:
            _warn(f"No se pudo leer el template: {e}")
            texto = None

        if texto is None:
            pass
        elif _template_ya_protegido(texto):
            _ok("El template YA protege el botón eliminar.")
        else:
            backup = _backup(RUTA_TEMPLATE)
            if backup:
                _info(f"Backup: {backup.name}")

            patron_boton = re.compile(
                r'(<button\b[^>]*?\baction-del\b[^>]*?onclick="abrirModalEliminar\([^)]*\)"[^>]*>'
                r'\s*<i\s+class="bi bi-x-octagon"></i>\s*</button>)',
                re.DOTALL
            )

            def _wrap(match):
                return "{% if not u.is_staff %}\n" + match.group(1) + "\n{% endif %}"

            nuevo, n = patron_boton.subn(_wrap, texto)
            if n > 0:
                try:
                    RUTA_TEMPLATE.write_text(nuevo, encoding='utf-8')
                    _ok(f"Template actualizado ({n} coincidencia(s)).")
                    cambios.append('template')
                except Exception as e:
                    _warn(f"No se pudo escribir el template: {e}")
            else:
                _warn("No se pudo ubicar automáticamente el botón eliminar.")

    print("\n" + "=" * 62)
    if cambios:
        print(f"  Cambios aplicados: {', '.join(cambios)}")
    else:
        print("  El sistema YA estaba correctamente configurado (sin cambios).")
    print("=" * 62)
    print("\n  ✓ Los administradores ya NO aparecen en la lista de usuarios.")
    print("  ✓ La opción de eliminar administradores está bloqueada.")
    print("  (Reinicia el servidor Django si estaba en ejecución.)")


# ============================================================
# 5. MENÚ PRINCIPAL
# ============================================================
def main():
    print("\n" + "#" * 62)
    print("#   GESTOR DE ADMINISTRADORES · 3-JJJ-A  (v2)")
    print("#" * 62)

    estado = cargar_estado()
    fase = estado.get('fase', 'inicial')

    print(f"\n  Estado actual: {fase}")

    # ---------- PRIMERA EJECUCIÓN ----------
    if fase == 'inicial':
        print("\n  >>> PRIMERA EJECUCIÓN <<<")
        print("  Podrás ELIMINAR administradores (dejando solo uno).")
        print("  Después, una SEGUNDA ejecución hará que:")
        print("    - Los admins NO aparezcan en la lista de usuarios.")
        print("    - NO se puedan eliminar admins desde el sistema.")
        print("\n  NOTA: Si no eliminas nada, puedes salir con Ctrl+C.")

        try:
            input("\n  Presiona ENTER para continuar...")
        except (KeyboardInterrupt, EOFError):
            print("\n  Cancelado.")
            sys.exit(0)

        eliminados = fase_1_eliminar_admins()

        if eliminados:
            estado['fase'] = 'eliminacion_realizada'
            estado['historial'].append({
                'fecha': datetime.now().isoformat(),
                'admins_eliminados': eliminados,
            })
            guardar_estado(estado)
            print(f"\n  [OK] Se eliminaron {len(eliminados)} administrador(es).")
            print("       Vuelve a ejecutar el script para activar el ocultamiento.")
        else:
            print("\n  No se realizaron eliminaciones.")
            try:
                r = input("  ¿Deseas continuar y aplicar el ocultamiento igualmente? (s/N): ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                r = 'n'
            if r == 's':
                estado['fase'] = 'eliminacion_realizada'
                estado['historial'].append({
                    'fecha': datetime.now().isoformat(),
                    'admins_eliminados': [],
                })
                guardar_estado(estado)
                print("\n  Estado guardado. Vuelve a ejecutar el script.")
            else:
                print("\n  Saliendo sin cambios. Puedes reintentar cuando quieras.")
        return

    # ---------- SEGUNDA EJECUCIÓN ----------
    if fase == 'eliminacion_realizada':
        print("\n  >>> SEGUNDA EJECUCIÓN <<<")
        print("  Se OCULTARÁN los admins y se BLOQUEARÁ su eliminación.")
        try:
            input("\n  Presiona ENTER para continuar...")
        except (KeyboardInterrupt, EOFError):
            print("\n  Cancelado.")
            sys.exit(0)

        fase_2_bloquear_y_ocultar()

        estado['fase'] = 'bloqueado'
        estado['historial'].append({
            'fecha': datetime.now().isoformat(),
            'accion': 'ocultamiento_y_proteccion_activados',
        })
        guardar_estado(estado)
        return

    # ---------- EJECUCIONES POSTERIORES ----------
    print("\n  >>> EJECUCIÓN POSTERIOR <<<")
    print("  El sistema ya está configurado. Verificando estado...\n")
    fase_2_bloquear_y_ocultar()
    print("\n  [i] El script ya cumplió sus dos fases.")
    print(f"      Para reiniciar el ciclo, elimina:\n      {RUTA_ESTADO}")


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Operación cancelada por el usuario.\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR INESPERADO] {e}\n")
        sys.exit(1)