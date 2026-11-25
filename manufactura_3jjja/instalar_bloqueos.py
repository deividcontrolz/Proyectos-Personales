# -*- coding: utf-8 -*-
"""
instalar_bloqueos.py
====================
Script de instalación del sistema de bloqueo por intentos fallidos de login.
- Crea una copia de seguridad de los archivos originales.
- Aplica modificaciones quirúrgicas sin romper funcionalidad existente.

Ejecutar desde la raíz del proyecto (junto a manage.py):
    python instalar_bloqueos.py
"""

import os
import re
import shutil
import sys
from datetime import datetime

# ============================================================
# DETECCIÓN AUTOMÁTICA DE ARCHIVOS
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def find_app_dir():
    """Encuentra la app que contiene views.py + urls.py."""
    candidates = []
    for name in os.listdir(BASE_DIR):
        path = os.path.join(BASE_DIR, name)
        if not os.path.isdir(path):
            continue
        if name.startswith('.') or name in ('media', 'static', 'templates', 'venv', 'env', '__pycache__'):
            continue
        if os.path.exists(os.path.join(path, 'views.py')) and \
           os.path.exists(os.path.join(path, 'urls.py')):
            candidates.append(path)
    if not candidates:
        return None
    for c in candidates:
        if os.path.basename(c) == 'core':
            return c
    return candidates[0]


def find_file(filename, start_dir):
    """Busca un archivo recursivamente desde start_dir."""
    for root, dirs, files in os.walk(start_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None


APP_DIR = find_app_dir()
if not APP_DIR:
    print("[ERROR] No se encontró la app (carpeta con views.py y urls.py).")
    sys.exit(1)

VIEWS_PATH = os.path.join(APP_DIR, 'views.py')
URLS_PATH = os.path.join(APP_DIR, 'urls.py')

# Buscar admin_usuarios.html en la app y en templates globales
ADMIN_HTML_PATH = find_file('admin_usuarios.html', APP_DIR)
if not ADMIN_HTML_PATH:
    ADMIN_HTML_PATH = find_file('admin_usuarios.html', BASE_DIR)

print("=" * 60)
print("  INSTALADOR - SISTEMA DE BLOQUEO POR INTENTOS")
print("=" * 60)
print(f"  App detectada:    {APP_DIR}")
print(f"  views.py:         {VIEWS_PATH}")
print(f"  urls.py:          {URLS_PATH}")
print(f"  admin_usuarios:   {ADMIN_HTML_PATH}")
print("=" * 60)

if not ADMIN_HTML_PATH:
    print("[ADVERTENCIA] No se encontró admin_usuarios.html, se omitirá esa modificación.")

# ============================================================
# CREAR BACKUP
# ============================================================
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
BACKUP_DIR = os.path.join(BASE_DIR, f'backup_{timestamp}')
os.makedirs(BACKUP_DIR, exist_ok=True)

files_to_backup = [('views.py', VIEWS_PATH), ('urls.py', URLS_PATH)]
if ADMIN_HTML_PATH:
    files_to_backup.append(('admin_usuarios.html', ADMIN_HTML_PATH))

print("\n[1/4] Creando copia de seguridad...")
for name, path in files_to_backup:
    if path and os.path.exists(path):
        shutil.copy2(path, os.path.join(BACKUP_DIR, name))
        print(f"   [OK] {name} -> {BACKUP_DIR}")
print(f"   Copia guardada en: {BACKUP_DIR}")

# ============================================================
# BLOQUES DE CÓDIGO NUEVO
# ============================================================

NUEVAS_FUNCIONES = '''
# ============================================================
# SISTEMA DE INTENTOS FALLIDOS DE LOGIN (archivo JSON - sin BD)
# ============================================================
MAX_INTENTOS_ADMIN = 3
MAX_INTENTOS_USUARIO = 5
MINUTOS_SUSPENSION = 15


def _ruta_archivo_intentos():
    base = Path(getattr(settings, 'MEDIA_ROOT', settings.BASE_DIR))
    carpeta = base / 'sistema'
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta / 'intentos_login.json'


def _cargar_intentos():
    ruta = _ruta_archivo_intentos()
    if not ruta.exists():
        return {}
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _guardar_intentos(data):
    ruta = _ruta_archivo_intentos()
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _parsear_fecha(iso_str):
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt)
        return dt
    except (ValueError, TypeError):
        return None


def esta_bloqueado(usuario_id):
    """Devuelve (bloqueado, motivo, minutos_restantes)."""
    data = _cargar_intentos()
    info = data.get(str(usuario_id))
    if not info:
        return False, '', 0
    if info.get('bloqueado_permanente'):
        return True, 'permanente', 0
    dt = _parsear_fecha(info.get('bloqueado_hasta'))
    if dt and dt > timezone.now():
        minutos = int((dt - timezone.now()).total_seconds() / 60) + 1
        return True, 'temporal', minutos
    return False, '', 0


def registrar_intento_fallido(usuario_id, es_admin=False):
    """Registra un intento fallido y aplica la política de bloqueo."""
    data = _cargar_intentos()
    uid = str(usuario_id)
    info = data.get(uid, {'intentos': 0, 'bloqueado_hasta': None, 'bloqueado_permanente': False})
    info['intentos'] = int(info.get('intentos', 0)) + 1

    if es_admin:
        # Admin: suspensión cada 3 intentos, nunca bloqueo permanente
        if info['intentos'] >= MAX_INTENTOS_ADMIN:
            info['bloqueado_hasta'] = (timezone.now() + timedelta(minutes=MINUTOS_SUSPENSION)).isoformat()
            info['intentos'] = 0
            info['bloqueado_permanente'] = False
    else:
        # Usuario normal: suspensión al 3er intento, bloqueo al 5to
        if info['intentos'] >= MAX_INTENTOS_USUARIO:
            info['bloqueado_permanente'] = True
            info['bloqueado_hasta'] = None
        elif info['intentos'] == 3:
            info['bloqueado_hasta'] = (timezone.now() + timedelta(minutes=MINUTOS_SUSPENSION)).isoformat()

    data[uid] = info
    _guardar_intentos(data)
    return info


def limpiar_intentos(usuario_id):
    """Borra los intentos al iniciar sesión exitosamente."""
    data = _cargar_intentos()
    uid = str(usuario_id)
    if uid in data:
        del data[uid]
        _guardar_intentos(data)


def desbloquear_usuario(usuario_id):
    """Elimina el bloqueo/suspensión de un usuario."""
    data = _cargar_intentos()
    uid = str(usuario_id)
    if uid in data:
        del data[uid]
        _guardar_intentos(data)
        return True
    return False


def get_info_intentos(usuario_id):
    """Devuelve la info de intentos de un usuario."""
    data = _cargar_intentos()
    return data.get(str(usuario_id), {'intentos': 0, 'bloqueado_hasta': None, 'bloqueado_permanente': False})

'''

NUEVO_LOGIN_VIEW = '''def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # 1. Verificar si está bloqueado o suspendido
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

            try:
                user = Usuario.objects.get(id_usuario=username)
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
                else:
                    # Registrar intento fallido
                    info = registrar_intento_fallido(username, es_admin=user.is_staff)
                    if user.is_staff:
                        if info.get('bloqueado_hasta'):
                            messages.error(
                                request,
                                f'Credenciales incorrectas. Por seguridad, la cuenta '
                                f'de administrador ha sido suspendida {MINUTOS_SUSPENSION} minutos.'
                            )
                        else:
                            restantes = max(MAX_INTENTOS_ADMIN - info.get('intentos', 0), 0)
                            messages.error(
                                request,
                                f'Credenciales incorrectas. '
                                f'Le quedan {restantes} intento(s) antes de la suspensión temporal.'
                            )
                    else:
                        if info.get('bloqueado_permanente'):
                            messages.error(
                                request,
                                'Credenciales incorrectas. Su cuenta ha sido BLOQUEADA por '
                                'superar los 5 intentos fallidos. Contacte al administrador.'
                            )
                        elif info.get('bloqueado_hasta'):
                            messages.warning(
                                request,
                                f'Credenciales incorrectas. Cuenta suspendida por '
                                f'{MINUTOS_SUSPENSION} minutos por superar el límite de intentos.'
                            )
                        else:
                            restantes = max(MAX_INTENTOS_USUARIO - info.get('intentos', 0), 0)
                            messages.error(
                                request,
                                f'Credenciales incorrectas. '
                                f'Le quedan {restantes} intento(s) antes del bloqueo.'
                            )
            except Usuario.DoesNotExist:
                messages.error(request, 'Usuario o contrasena incorrectos.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form})

'''

NUEVA_VISTA_DESBLOQUEO = '''# ============================================================
# VISTA: DESBLOQUEAR USUARIO (Admin)
# ============================================================
def admin_desbloquear_usuario_view(request, usuario_id):
    usuario = get_usuario_sesion(request)
    if not usuario:
        messages.error(request, 'Debe iniciar sesion para acceder.')
        return redirect('core:login')
    if not usuario.is_staff:
        return render(request, 'errors/403.html', status=403)
    if tiene_password_temporal(usuario.id_usuario):
        return redirect('core:cambiar_password_temporal')

    if desbloquear_usuario(usuario_id):
        messages.success(request, f'Usuario "{usuario_id}" desbloqueado correctamente.')
    else:
        messages.info(request, f'El usuario "{usuario_id}" no tenia bloqueos activos.')
    return redirect('core:admin_usuarios')


'''

# ============================================================
# PARCHEAR views.py
# ============================================================
print("\n[2/4] Parcheando views.py...")

with open(VIEWS_PATH, 'r', encoding='utf-8') as f:
    views_content = f.read()

if 'MAX_INTENTOS_ADMIN' in views_content:
    print("   [SKIP] views.py ya contiene el sistema de bloqueos.")
else:
    original = views_content

    # 1) Import datetime
    anchor_import = "from django.conf import settings\n"
    if "from datetime import datetime, timedelta" not in views_content:
        views_content = views_content.replace(
            anchor_import,
            anchor_import + "from datetime import datetime, timedelta\n",
            1
        )
        print("   [OK] Import datetime agregado")

    # 2) Insertar nuevas funciones después de tiene_password_temporal
    anchor_fn = "    return str(id_usuario) in _cargar_temporales()\n"
    if anchor_fn in views_content:
        views_content = views_content.replace(
            anchor_fn,
            anchor_fn + "\n" + NUEVAS_FUNCIONES + "\n",
            1
        )
        print("   [OK] Funciones de bloqueo insertadas")
    else:
        print("   [WARN] No se encontró el ancla de tiene_password_temporal")

    # 3) Reemplazar login_view
    login_pattern = re.compile(
        r'def login_view\(request\):.*?(?=\n\ndef logout_view)',
        re.DOTALL
    )
    if login_pattern.search(views_content):
        views_content = login_pattern.sub(NUEVO_LOGIN_VIEW.rstrip(), views_content, count=1)
        print("   [OK] login_view reemplazado")
    else:
        print("   [WARN] No se pudo localizar login_view")

    # 4) Insertar vista de desbloqueo antes de la sección 10
    anchor_v10 = (
        "# ============================================================\n"
        "# 10. VISTA: REGISTRO DE NUEVO USUARIO\n"
        "# ============================================================"
    )
    if anchor_v10 in views_content:
        views_content = views_content.replace(
            anchor_v10,
            NUEVA_VISTA_DESBLOQUEO + anchor_v10,
            1
        )
        print("   [OK] Vista admin_desbloquear_usuario_view agregada")
    else:
        print("   [WARN] No se encontró el ancla de la sección 10")

    # 5) Modificar admin_usuarios_view (contexto)
    old_ctx = '''    rol_filtro = request.GET.get('rol', '')
    estado_filtro = request.GET.get('estado', '')
    usuarios = Usuario.objects.all().order_by('-fecha_registro')
    if rol_filtro:
        usuarios = usuarios.filter(rol=rol_filtro)
    if estado_filtro == 'activo':
        usuarios = usuarios.filter(is_active=True)
    elif estado_filtro == 'inactivo':
        usuarios = usuarios.filter(is_active=False)
    contexto = {
        'usuario': request.usuario_actual,
        'usuarios': usuarios,
        'roles': ROLES_CHOICES,
        'rol_filtro': rol_filtro,
        'estado_filtro': estado_filtro,
        'total_usuarios': usuarios.count(),
    }'''

    new_ctx = '''    rol_filtro = request.GET.get('rol', '')
    estado_filtro = request.GET.get('estado', '')
    usuarios_qs = Usuario.objects.all().order_by('-fecha_registro')
    if rol_filtro:
        usuarios_qs = usuarios_qs.filter(rol=rol_filtro)
    if estado_filtro == 'activo':
        usuarios_qs = usuarios_qs.filter(is_active=True)
    elif estado_filtro == 'inactivo':
        usuarios_qs = usuarios_qs.filter(is_active=False)

    # Enriquecer con info de bloqueo por intentos fallidos
    usuarios = list(usuarios_qs)
    for u in usuarios:
        bl, mo, mi = esta_bloqueado(u.id_usuario)
        u.bloqueado = bl
        u.motivo_bloqueo = mo
        u.minutos_restantes = mi
        u.info_intentos = get_info_intentos(u.id_usuario)

    contexto = {
        'usuario': request.usuario_actual,
        'usuarios': usuarios,
        'roles': ROLES_CHOICES,
        'rol_filtro': rol_filtro,
        'estado_filtro': estado_filtro,
        'total_usuarios': len(usuarios),
    }'''

    if old_ctx in views_content:
        views_content = views_content.replace(old_ctx, new_ctx, 1)
        print("   [OK] admin_usuarios_view modificado para incluir bloqueos")
    else:
        print("   [WARN] No se pudo modificar admin_usuarios_view (contexto)")

    if views_content != original:
        with open(VIEWS_PATH, 'w', encoding='utf-8') as f:
            f.write(views_content)
        print("   [OK] views.py guardado")
    else:
        print("   [WARN] views.py no se modificó (sin cambios aplicados)")

# ============================================================
# PARCHEAR urls.py
# ============================================================
print("\n[3/4] Parcheando urls.py...")

with open(URLS_PATH, 'r', encoding='utf-8') as f:
    urls_content = f.read()

if 'admin_desbloquear_usuario' in urls_content:
    print("   [SKIP] urls.py ya contiene la ruta de desbloqueo.")
else:
    anchor_url = (
        "    path('panel-admin/usuarios/', views.admin_usuarios_view, name='admin_usuarios'),\n"
    )
    new_url = (
        anchor_url +
        "    path('panel-admin/usuarios/desbloquear/<str:usuario_id>/', "
        "views.admin_desbloquear_usuario_view, name='admin_desbloquear_usuario'),\n"
    )
    if anchor_url in urls_content:
        urls_content = urls_content.replace(anchor_url, new_url, 1)
        with open(URLS_PATH, 'w', encoding='utf-8') as f:
            f.write(urls_content)
        print("   [OK] Ruta de desbloqueo agregada")
    else:
        print("   [WARN] No se encontró el ancla en urls.py")

# ============================================================
# PARCHEAR admin_usuarios.html
# ============================================================
if ADMIN_HTML_PATH:
    print("\n[4/4] Parcheando admin_usuarios.html...")

    with open(ADMIN_HTML_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    if 'admin_desbloquear_usuario' in html:
        print("   [SKIP] admin_usuarios.html ya contiene el botón de desbloqueo.")
    else:
        # 1) Badge de bloqueado en la columna de Estado
        old_badge = '''                            {% if u.is_staff %}
                                <span class="status-badge badge-admin">Admin</span>
                            {% endif %}'''
        new_badge = '''                            {% if u.is_staff %}
                                <span class="status-badge badge-admin">Admin</span>
                            {% endif %}
                            {% if u.bloqueado %}
                                <span class="status-badge" style="background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.5); margin-left: 4px;" title="{{ u.motivo_bloqueo|default:'Bloqueado' }}{% if u.minutos_restantes %} ({{ u.minutos_restantes }} min){% endif %}">
                                    <i class="bi bi-lock-fill"></i> Bloqueado
                                </span>
                            {% endif %}'''

        if old_badge in html:
            html = html.replace(old_badge, new_badge, 1)
            print("   [OK] Badge de bloqueado agregado")
        else:
            print("   [WARN] No se encontró el ancla para el badge")

        # 2) Botón de desbloqueo en las acciones
        old_actions = '''                                <button type="button" class="action-btn action-pwd" title="Cambiar contraseña"
                                    onclick="abrirModalPassword('{{ u.id_usuario }}', '{{ u.nombre_completo }}')">
                                    <i class="bi bi-key"></i>
                                </button>
                            </div>'''
        new_actions = '''                                <button type="button" class="action-btn action-pwd" title="Cambiar contraseña"
                                    onclick="abrirModalPassword('{{ u.id_usuario }}', '{{ u.nombre_completo }}')">
                                    <i class="bi bi-key"></i>
                                </button>
                                {% if u.bloqueado %}
                                <form method="post" action="{% url 'core:admin_desbloquear_usuario' u.id_usuario %}" style="display:inline;">
                                    {% csrf_token %}
                                    <button type="submit" class="action-btn" title="Desbloquear usuario"
                                        style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3);">
                                        <i class="bi bi-unlock-fill"></i>
                                    </button>
                                </form>
                                {% endif %}
                            </div>'''

        if old_actions in html:
            html = html.replace(old_actions, new_actions, 1)
            print("   [OK] Botón de desbloqueo agregado")
        else:
            print("   [WARN] No se encontró el ancla para el botón")

        with open(ADMIN_HTML_PATH, 'w', encoding='utf-8') as f:
            f.write(html)
        print("   [OK] admin_usuarios.html guardado")

# ============================================================
# RESUMEN FINAL
# ============================================================
print("\n" + "=" * 60)
print("  INSTALACIÓN COMPLETADA")
print("=" * 60)
print(f"  Backup:  {BACKUP_DIR}")
print("")
print("  Próximos pasos:")
print("  1. Reinicia el servidor de Django.")
print("  2. Prueba el login 3 veces con contraseña incorrecta.")
print("  3. Ve al panel admin y verifica el botón de desbloqueo.")
print("")
print("  Si algo falla, restaura desde el backup:")
print(f"    copy {BACKUP_DIR}\\*.* {APP_DIR}\\")
print("=" * 60)