# -*- coding: utf-8 -*-
"""
reparar_middleware.py
Repara el error: module 'core.middleware' has no attribute 'CurrentUserMiddleware'
"""
from pathlib import Path

BASE = Path(__file__).resolve().parent
APP = None
for c in BASE.iterdir():
    if c.is_dir() and (c / 'models.py').exists():
        txt = (c / 'models.py').read_text(encoding='utf-8', errors='ignore')
        if 'class Usuario' in txt and 'class Incidente' in txt:
            APP = c
            break

if APP is None:
    print("[X] No se encontró la app.")
    raise SystemExit(1)

MW = APP / 'middleware.py'

CLASE = '''

# ============================================================
# Middleware de auditoría (auto-añadido)
# ============================================================
try:
    from .auditoria import set_current_user, clear_current_user
except ImportError:
    set_current_user = lambda u: None
    clear_current_user = lambda: None


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = None
        try:
            uid = request.session.get('usuario_id')
            if uid:
                from .models import Usuario
                try:
                    user = Usuario.objects.get(id_usuario=uid)
                except Usuario.DoesNotExist:
                    user = None
        except Exception:
            user = None

        set_current_user(user)
        try:
            response = self.get_response(request)
        finally:
            clear_current_user()
        return response
'''

if MW.exists():
    txt = MW.read_text(encoding='utf-8')
    if 'CurrentUserMiddleware' in txt:
        print("[OK] Ya estaba definida la clase. Nada que hacer.")
    else:
        MW.write_text(txt.rstrip() + '\n' + CLASE, encoding='utf-8')
        print(f"[OK] Clase añadida a: {MW}")
else:
    # Crear el archivo con la clase
    MW.write_text(
        '# -*- coding: utf-8 -*-\n'
        '"""Middleware de auditoría."""\n' + CLASE,
        encoding='utf-8'
    )
    print(f"[OK] Archivo creado: {MW}")

print()
print("Ahora ejecuta:")
print("  python manage.py runserver")