#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
============================================================
INSTALADOR TODO-EN-UNO: AUDITORÍA + REPORTE PDF
Sistema de Gestión de Producción - Manufacturera 3-JJJ-A
============================================================

Ejecutar desde la RAÍZ del proyecto (junto a manage.py):
    python instalar_auditoria.py

Realiza TODO automáticamente:
  1) Backup único con timestamp (NUNCA sobrescribe backups previos).
  2) Crea <app>/auditoria.py         (mixin + señales).
  3) Crea <app>/middleware.py        (usuario actual thread-local).
  4) Modifica <app>/models.py        (aplica el mixin a los 10 modelos).
  5) Modifica settings.py            (registra el middleware).
  6) Crea <app>/reportes_auditoria_pdf.py
  7) Modifica <app>/views.py         (añade vista 'reporte_auditoria_pdf').
  8) Modifica <app>/urls.py          (añade ruta 'reportes/auditoria/').
  9) Modifica la plantilla panel_reportes.html
     (añade card de auditoría + arregla el bug JS del card de usuarios).

Es IDEMPOTENTE: puedes ejecutarlo varias veces sin duplicar nada.
"""

import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path


# ============================================================
# Log de consola
# ============================================================
def log(msg, level='info'):
    iconos = {'info': '   ', 'ok': '[OK] ', 'warn': '[!] ', 'err': '[X] ',
              'step': '>> ', 'skip': '[--] '}
    print(f"{iconos.get(level, '   ')}{msg}")


# ============================================================
# 1. Detectar rutas del proyecto
# ============================================================
BASE_DIR = Path(__file__).resolve().parent

if not (BASE_DIR / 'manage.py').exists():
    log("No se encontró manage.py. Ejecuta el script desde la raíz del proyecto.", 'err')
    sys.exit(1)

# --- Detectar app principal ---
APP_DIR = None
for candidate in BASE_DIR.iterdir():
    if not candidate.is_dir() or candidate.name.startswith(('_', '.')):
        continue
    models_file = candidate / 'models.py'
    if not models_file.exists():
        continue
    try:
        txt = models_file.read_text(encoding='utf-8')
    except Exception:
        continue
    if 'class Usuario' in txt and 'class Incidente' in txt:
        APP_DIR = candidate
        break

if APP_DIR is None:
    log("No se encontró la app con 'Usuario' e 'Incidente' en models.py.", 'err')
    sys.exit(1)

APP_NAME = APP_DIR.name

# --- Detectar settings.py ---
SETTINGS_FILE = None
for p in BASE_DIR.rglob('settings.py'):
    if any(x in str(p) for x in ('site-packages', 'venv', '.venv', 'env')):
        continue
    SETTINGS_FILE = p
    break

if SETTINGS_FILE is None:
    log("No se encontró settings.py", 'err')
    sys.exit(1)

# --- Detectar panel_reportes.html ---
PANEL_HTML = None
for p in BASE_DIR.rglob('panel_reportes.html'):
    if any(x in str(p) for x in ('site-packages', 'venv', '.venv', 'env')):
        continue
    PANEL_HTML = p
    break

# --- Rutas de archivos de la app ---
MODELS_FILE   = APP_DIR / 'models.py'
VIEWS_FILE    = APP_DIR / 'views.py'
URLS_FILE     = APP_DIR / 'urls.py'
AUDITORIA_PY  = APP_DIR / 'auditoria.py'
MIDDLEWARE_PY = APP_DIR / 'middleware.py'
REPORTES_AUD  = APP_DIR / 'reportes_auditoria_pdf.py'

print("=" * 62)
log(f"Proyecto:        {BASE_DIR}", 'ok')
log(f"App:             {APP_DIR}", 'ok')
log(f"Settings:        {SETTINGS_FILE}", 'ok')
log(f"panel_reportes:  {PANEL_HTML if PANEL_HTML else 'NO ENCONTRADO (se omite)'}",
    'ok' if PANEL_HTML else 'warn')
print("=" * 62)
print()

# Confirmar
print("Se modificarán (con backup previo):")
for f in [MODELS_FILE, VIEWS_FILE, URLS_FILE, SETTINGS_FILE, PANEL_HTML]:
    if f and f.exists():
        print(f"   - {f.relative_to(BASE_DIR)}")
print()
resp = input("¿Continuar? (s/N): ").strip().lower()
if resp not in ('s', 'si', 'sí', 'y', 'yes'):
    print("Cancelado.")
    sys.exit(0)


# ============================================================
# 2. BACKUP ÚNICO (nunca sobrescribe)
# ============================================================
print()
log("Creando copia de seguridad...", 'step')
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
BACKUP_DIR = BASE_DIR / f'_backup_auditoria_{timestamp}'
contador = 1
while BACKUP_DIR.exists():
    BACKUP_DIR = BASE_DIR / f'_backup_auditoria_{timestamp}_{contador}'
    contador += 1
BACKUP_DIR.mkdir()

archivos_backup = [MODELS_FILE, VIEWS_FILE, URLS_FILE, SETTINGS_FILE, PANEL_HTML]
for f in archivos_backup:
    if f and f.exists():
        shutil.copy2(f, BACKUP_DIR / f.name)
        log(f"Backup: {f.name}", 'ok')

zip_path = BACKUP_DIR / f'backup_app_{APP_NAME}.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for py_file in APP_DIR.rglob('*.py'):
        zf.write(py_file, py_file.relative_to(BASE_DIR))
log(f"Backup ZIP: {zip_path.name}", 'ok')


# ============================================================
# 3. <app>/auditoria.py
# ============================================================
print()
log("Módulo auditoria.py...", 'step')

if AUDITORIA_PY.exists():
    log(f"{APP_NAME}/auditoria.py ya existe, se omite", 'skip')
else:
    AUDITORIA_PY.write_text('''# -*- coding: utf-8 -*-
"""
auditoria.py
============
Sistema de auditoría automática.

Campos añadidos a cada modelo que herede de AuditoriaMixin:
    - fecha_creacion
    - usuario_creacion
    - fecha_modificacion
    - usuario_modificacion
    - activo
"""

import threading
from django.db import models
from django.db.models.signals import class_prepared, pre_save
from django.utils import timezone


_thread_locals = threading.local()


def set_current_user(user):
    _thread_locals.user = user


def get_current_user():
    return getattr(_thread_locals, 'user', None)


def clear_current_user():
    if hasattr(_thread_locals, 'user'):
        del _thread_locals.user


class AuditoriaMixin(models.Model):
    fecha_creacion = models.DateTimeField(
        default=timezone.now, null=True, blank=True,
        verbose_name='Fecha de creación',
    )
    usuario_creacion = models.ForeignKey(
        'Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(app_label)s_%(class)s_creados',
        verbose_name='Usuario que creó',
    )
    fecha_modificacion = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Fecha de modificación',
    )
    usuario_modificacion = models.ForeignKey(
        'Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(app_label)s_%(class)s_modificados',
        verbose_name='Usuario que modificó',
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
    )

    class Meta:
        abstract = True


def _fill_audit_fields(sender, instance, **kwargs):
    user = get_current_user()
    uid = getattr(user, 'id_usuario', None) if user else None

    if instance._state.adding:
        if getattr(instance, 'fecha_creacion', None) is None:
            instance.fecha_creacion = timezone.now()
        if uid and getattr(instance, 'usuario_creacion_id', None) is None:
            instance.usuario_creacion_id = uid
    else:
        if hasattr(instance, 'fecha_modificacion'):
            instance.fecha_modificacion = timezone.now()
        if uid and hasattr(instance, 'usuario_modificacion_id'):
            instance.usuario_modificacion_id = uid


def _connect_audit_signal(sender, **kwargs):
    try:
        if issubclass(sender, AuditoriaMixin) and not sender._meta.abstract:
            pre_save.connect(
                _fill_audit_fields,
                sender=sender,
                weak=False,
                dispatch_uid=f'audit_{sender.__module__}_{sender.__name__}',
            )
    except Exception:
        pass


class_prepared.connect(_connect_audit_signal, weak=False)
''', encoding='utf-8')
    log(f"Creado: {APP_NAME}/auditoria.py", 'ok')


# ============================================================
# 4. <app>/middleware.py
# ============================================================
print()
log("Middleware...", 'step')

if MIDDLEWARE_PY.exists():
    log(f"{APP_NAME}/middleware.py ya existe, se omite", 'skip')
else:
    MIDDLEWARE_PY.write_text('''# -*- coding: utf-8 -*-
"""
middleware.py
=============
Inyecta el usuario de la sesión actual en un thread-local
para que las señales de auditoría rellenen
'usuario_creacion' y 'usuario_modificacion'.
"""

from .auditoria import set_current_user, clear_current_user


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
''', encoding='utf-8')
    log(f"Creado: {APP_NAME}/middleware.py", 'ok')


# ============================================================
# 5. models.py
# ============================================================
print()
log("models.py...", 'step')
content = MODELS_FILE.read_text(encoding='utf-8')

if 'from .auditoria import AuditoriaMixin' in content:
    log("models.py ya tenía el import del mixin, se omite", 'skip')
else:
    # Import
    if 'from django.utils import timezone' in content:
        content = content.replace(
            'from django.utils import timezone',
            'from django.utils import timezone\n\nfrom .auditoria import AuditoriaMixin',
            1,
        )
    else:
        content = 'from .auditoria import AuditoriaMixin\n' + content
    log("Import de AuditoriaMixin agregado", 'ok')

    # Herencia
    modelos = [
        'Usuario', 'Material', 'Modelo', 'MaterialModelo',
        'LoteProduccion', 'Etapa', 'RegistroEtapa',
        'DesperdicioMaterial', 'Maquinaria', 'Incidente',
    ]
    for modelo in modelos:
        patron = rf'class\s+{modelo}\(models\.Model\):'
        content, n = re.subn(patron, f'class {modelo}(AuditoriaMixin):', content)
        if n > 0:
            log(f"   {modelo} → AuditoriaMixin", 'ok')

    # Resolver conflicto fecha_creacion en LoteProduccion
    patron_conflicto = r'\n[ \t]*fecha_creacion\s*=\s*models\.DateTimeField\(auto_now_add=True\)'
    content, n = re.subn(
        patron_conflicto,
        '\n    # fecha_creacion viene del mixin AuditoriaMixin',
        content, count=1,
    )
    if n > 0:
        log("   Conflicto 'fecha_creacion' resuelto", 'ok')

    MODELS_FILE.write_text(content, encoding='utf-8')
    log("models.py actualizado", 'ok')


# ============================================================
# 6. settings.py
# ============================================================
print()
log("settings.py...", 'step')
settings_content = SETTINGS_FILE.read_text(encoding='utf-8')

if 'CurrentUserMiddleware' in settings_content:
    log("Middleware ya registrado, se omite", 'skip')
else:
    middleware_path = f"{APP_NAME}.middleware.CurrentUserMiddleware"
    patron = r"([ \t]*['\"]django\.contrib\.sessions\.middleware\.SessionMiddleware['\"],?\r?\n)"
    match = re.search(patron, settings_content)
    if match:
        linea = match.group(1)
        indent = re.match(r'^([ \t]*)', linea).group(1)
        comilla = "'" if "'" in linea else '"'
        nueva_linea = f"{indent}{comilla}{middleware_path}{comilla},\n"
        settings_content = (
            settings_content[:match.end()] + nueva_linea + settings_content[match.end():]
        )
        SETTINGS_FILE.write_text(settings_content, encoding='utf-8')
        log(f"Middleware añadido a {SETTINGS_FILE.name}", 'ok')
    else:
        log("No se pudo insertar automáticamente. Agrega manualmente en MIDDLEWARE:", 'warn')
        log(f"   '{middleware_path}',", 'warn')


# ============================================================
# 7. <app>/reportes_auditoria_pdf.py
# ============================================================
print()
log("reportes_auditoria_pdf.py...", 'step')

if REPORTES_AUD.exists():
    log(f"{APP_NAME}/reportes_auditoria_pdf.py ya existe, se omite", 'skip')
else:
    REPORTES_AUD.write_text('''# -*- coding: utf-8 -*-
"""
reportes_auditoria_pdf.py
=========================
Reporte PDF de auditoría: muestra para cada tabla principal
el usuario y fecha de creación, usuario y fecha de modificación
y el estado 'activo'.
"""

import io
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
)
from reportlab.platypus.flowables import HRFlowable

from .models import (
    Usuario, Modelo, Material, LoteProduccion, Etapa,
    RegistroEtapa, Incidente, Maquinaria,
)
from .reportes_pdf import get_estilos, crear_tabla_pdf, agregar_footer


# ============================================================
# Helpers
# ============================================================
def _descripcion(obj):
    for attr in ('nombre_completo', 'nombre', 'nombre_etapa',
                 'nombre_material', 'id_lote', 'id_incidente',
                 'id_registro', 'id_maquina'):
        if hasattr(obj, attr):
            val = getattr(obj, attr)
            if val:
                return str(val)[:40]
    return str(obj)[:40]


def _formato_usuario(u):
    if not u:
        return '—'
    return f"{u.id_usuario}"


def _formato_fecha(f):
    if not f:
        return '—'
    try:
        return f.strftime('%d/%m/%Y %H:%M')
    except Exception:
        return str(f)


# ============================================================
# Reporte
# ============================================================
def generar_reporte_auditoria(request, tabla=None, usuario=None,
                              fecha_desde=None, fecha_hasta=None,
                              solo_activos=False):
    TABLAS = {
        'Usuario':        Usuario,
        'Modelo':         Modelo,
        'Material':       Material,
        'LoteProduccion': LoteProduccion,
        'Etapa':          Etapa,
        'RegistroEtapa':  RegistroEtapa,
        'Incidente':      Incidente,
        'Maquinaria':     Maquinaria,
    }

    registros = []
    modelos_a_revisar = TABLAS if not tabla else {tabla: TABLAS.get(tabla)}

    for nombre_tabla, modelo in modelos_a_revisar.items():
        if modelo is None:
            continue
        try:
            qs = modelo.objects.all()
            if solo_activos and hasattr(modelo, 'activo'):
                qs = qs.filter(activo=True)
            if usuario and hasattr(modelo, 'usuario_creacion'):
                qs = qs.filter(usuario_creacion_id=usuario)
            if fecha_desde:
                qs = qs.filter(fecha_creacion__date__gte=fecha_desde)
            if fecha_hasta:
                qs = qs.filter(fecha_creacion__date__lte=fecha_hasta)
            qs = qs.order_by('-fecha_modificacion', '-fecha_creacion')[:200]
            for obj in qs:
                registros.append({
                    'tabla':  nombre_tabla,
                    'id':     str(getattr(obj, 'pk', '—')),
                    'desc':   _descripcion(obj),
                    'u_crea': _formato_usuario(getattr(obj, 'usuario_creacion', None)),
                    'f_crea': _formato_fecha(getattr(obj, 'fecha_creacion', None)),
                    'u_mod':  _formato_usuario(getattr(obj, 'usuario_modificacion', None)),
                    'f_mod':  _formato_fecha(getattr(obj, 'fecha_modificacion', None)),
                    'activo': 'Sí' if getattr(obj, 'activo', True) else 'No',
                })
        except Exception:
            continue

    registros.sort(key=lambda r: r['f_mod'], reverse=True)

    # ---- PDF ----
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm,
    )

    styles = get_estilos()
    elements = []

    fecha_actual = timezone.now().strftime('%d/%m/%Y %H:%M')
    elements.append(Paragraph(f'Generado: {fecha_actual}', styles['FechaHeader']))
    elements.append(Spacer(1, 5))

    titulo = 'Reporte de Auditoría del Sistema'
    if tabla:
        titulo += f' - {tabla}'
    if usuario:
        titulo += f' - Usuario: {usuario}'
    if solo_activos:
        titulo += ' (solo activos)'

    elements.append(Paragraph(titulo, styles['TituloPrincipal']))
    elements.append(Paragraph(
        f'Total de registros listados: {len(registros)}',
        styles['Subtitulo'],
    ))
    elements.append(HRFlowable(width='100%', thickness=1,
                               color=colors.HexColor('#059669')))
    elements.append(Spacer(1, 15))

    datos = [[
        'Tabla', 'ID', 'Descripción',
        'Usuario Creó', 'Fecha Creación',
        'Usuario Modificó', 'Fecha Modificación', 'Activo',
    ]]
    for r in registros[:300]:
        datos.append([
            r['tabla'], r['id'], r['desc'],
            r['u_crea'], r['f_crea'],
            r['u_mod'], r['f_mod'], r['activo'],
        ])

    col_widths = [2.5*cm, 2*cm, 5*cm, 3*cm, 3*cm, 3*cm, 3*cm, 1.5*cm]
    elements.append(crear_tabla_pdf(datos, col_widths))

    # Resumen
    elements.append(Spacer(1, 20))
    elements.append(Paragraph('Resumen por Tabla', styles['Subtitulo']))

    resumen = {}
    for r in registros:
        resumen[r['tabla']] = resumen.get(r['tabla'], 0) + 1

    resumen_datos = [['Tabla', 'Registros Auditados']]
    for t, c in sorted(resumen.items()):
        resumen_datos.append([t, str(c)])

    elements.append(crear_tabla_pdf(resumen_datos, [8*cm, 5*cm]))

    doc.build(elements, onFirstPage=agregar_footer, onLaterPages=agregar_footer)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f'reporte_auditoria_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    buffer.close()
    return response
''', encoding='utf-8')
    log(f"Creado: {APP_NAME}/reportes_auditoria_pdf.py", 'ok')


# ============================================================
# 8. views.py (añadir vista al final)
# ============================================================
print()
log("views.py...", 'step')
views_content = VIEWS_FILE.read_text(encoding='utf-8')

if 'def reporte_auditoria_pdf' in views_content:
    log("Vista 'reporte_auditoria_pdf' ya existe, se omite", 'skip')
else:
    # Import de la función generadora (antes de la vista)
    import_marker = '# ============================================================\n# VISTA: REPORTE PDF DE AUDITORÍA'
    import_line = (
        'from .reportes_auditoria_pdf import generar_reporte_auditoria'
    )

    vista_code = f'''

# ============================================================
# VISTA: REPORTE PDF DE AUDITORÍA (solo admin)
# ============================================================
{import_line}


def reporte_auditoria_pdf(request):
    """Genera el PDF de auditoría. Solo accesible para staff."""
    usuario = get_usuario_sesion(request)
    if not usuario or not usuario.is_staff:
        messages.error(request, 'No tiene permisos para acceder.')
        return render(request, 'errors/403.html', status=403)

    if tiene_password_temporal(usuario.id_usuario):
        return redirect('core:cambiar_password_temporal')

    return generar_reporte_auditoria(
        request,
        tabla=request.GET.get('tabla', '') or None,
        usuario=request.GET.get('usuario', '') or None,
        fecha_desde=request.GET.get('fecha_desde', '') or None,
        fecha_hasta=request.GET.get('fecha_hasta', '') or None,
        solo_activos=request.GET.get('solo_activos', '') in ('1', 'true', 'on'),
    )
'''
    views_content = views_content.rstrip() + '\n' + vista_code
    VIEWS_FILE.write_text(views_content, encoding='utf-8')
    log("Vista añadida al final de views.py", 'ok')


# ============================================================
# 9. urls.py (añadir ruta)
# ============================================================
print()
log("urls.py...", 'step')
urls_content = URLS_FILE.read_text(encoding='utf-8')

if 'reporte_auditoria_pdf' in urls_content:
    log("URL ya registrada, se omite", 'skip')
else:
    # Insertar después de la línea de reporte_etapas_pdf
    patron = r"([ \t]*path\(['\"]reportes/etapas/['\"],[^\n]*\n)"
    match = re.search(patron, urls_content)
    if match:
        indent = re.match(r'^([ \t]*)', match.group(1)).group(1)
        nueva_linea = (
            f"{indent}path('reportes/auditoria/', "
            f"views.reporte_auditoria_pdf, name='reporte_auditoria_pdf'),\n"
        )
        urls_content = (
            urls_content[:match.end()] + nueva_linea + urls_content[match.end():]
        )
        URLS_FILE.write_text(urls_content, encoding='utf-8')
        log("URL añadida a urls.py", 'ok')
    else:
        log("No se pudo insertar automáticamente. Añade manualmente en urls.py:", 'warn')
        log("   path('reportes/auditoria/', views.reporte_auditoria_pdf, "
            "name='reporte_auditoria_pdf'),", 'warn')


# ============================================================
# 10. panel_reportes.html
# ============================================================
print()
log("panel_reportes.html...", 'step')

if not PANEL_HTML or not PANEL_HTML.exists():
    log("No se encontró panel_reportes.html, se omite", 'warn')
else:
    html_content = PANEL_HTML.read_text(encoding='utf-8')
    cambios = []

    # --- 10.1 Arreglar el botón roto del card de Usuarios ---
    patron_boton_roto = (
        r'<a href="\{% url \'core:reporte_usuarios_pdf\' %\}" '
        r'class="btn-reporte btn-blue" onclick="[^"]*">\s*'
        r'<i class="bi bi-download"></i> Descargar PDF\s*</a>'
    )
    reemplazo_boton = (
        '<button type="button" class="btn-reporte btn-blue" '
        'onclick="descargarConFiltros(\'form-usuarios\', '
        '\'{% url \'core:reporte_usuarios_pdf\' %}\');">\n'
        '                <i class="bi bi-download"></i> Descargar PDF\n'
        '            </button>'
    )
    if re.search(patron_boton_roto, html_content, re.DOTALL):
        html_content = re.sub(patron_boton_roto, reemplazo_boton, html_content,
                              count=1, flags=re.DOTALL)
        cambios.append("Botón de Usuarios corregido")
    else:
        # Variante 2 (por si el html difiere mínimamente)
        if 'querySelector(\'form\').serialize()' in html_content:
            html_content = html_content.replace(
                'querySelector(\'form\').serialize()',
                'querySelector(\'form\')'
            )
            cambios.append("Bug '.serialize()' parcheado")

    # --- 10.2 Añadir id al form de Usuarios ---
    if 'id="form-usuarios"' not in html_content:
        # buscar el form de usuarios y añadirle id
        patron_form_user = (
            r'(<form method="get" action="\{% url \'core:reporte_usuarios_pdf\' %\}" '
            r'class="filtros-form")>'
        )
        if re.search(patron_form_user, html_content):
            html_content = re.sub(
                patron_form_user,
                r'\1 id="form-usuarios">',
                html_content, count=1
            )
            cambios.append("id='form-usuarios' añadido")

    # --- 10.3 Añadir ids a forms de Lotes e Incidentes ---
    if 'id="form-lotes"' not in html_content:
        patron = (
            r'(<form method="get" action="\{% url \'core:reporte_lotes_pdf\' %\}" '
            r'class="filtros-form")>'
        )
        if re.search(patron, html_content):
            html_content = re.sub(patron, r'\1 id="form-lotes">', html_content, count=1)
            cambios.append("id='form-lotes' añadido")

    if 'id="form-incidentes"' not in html_content:
        patron = (
            r'(<form method="get" action="\{% url \'core:reporte_incidentes_pdf\' %\}" '
            r'class="filtros-form")>'
        )
        if re.search(patron, html_content):
            html_content = re.sub(patron, r'\1 id="form-incidentes">', html_content, count=1)
            cambios.append("id='form-incidentes' añadido")

    # --- 10.4 Reemplazar botones/enlaces por onclick en Lotes e Incidentes ---
    # Lotes
    patron_lotes = (
        r'<a href="\{% url \'core:reporte_lotes_pdf\' %\}" '
        r'class="btn-reporte btn-orange">\s*'
        r'<i class="bi bi-download"></i> Descargar PDF\s*</a>'
    )
    reemplazo_lotes = (
        '<button type="button" class="btn-reporte btn-orange" '
        'onclick="descargarConFiltros(\'form-lotes\', '
        '\'{% url \'core:reporte_lotes_pdf\' %}\');">\n'
        '                <i class="bi bi-download"></i> Descargar PDF\n'
        '            </button>'
    )
    if re.search(patron_lotes, html_content, re.DOTALL):
        html_content = re.sub(patron_lotes, reemplazo_lotes, html_content,
                              count=1, flags=re.DOTALL)
        cambios.append("Botón de Lotes actualizado")

    # Incidentes
    patron_inc = (
        r'<a href="\{% url \'core:reporte_incidentes_pdf\' %\}" '
        r'class="btn-reporte btn-red">\s*'
        r'<i class="bi bi-download"></i> Descargar PDF\s*</a>'
    )
    reemplazo_inc = (
        '<button type="button" class="btn-reporte btn-red" '
        'onclick="descargarConFiltros(\'form-incidentes\', '
        '\'{% url \'core:reporte_incidentes_pdf\' %}\');">\n'
        '                <i class="bi bi-download"></i> Descargar PDF\n'
        '            </button>'
    )
    if re.search(patron_inc, html_content, re.DOTALL):
        html_content = re.sub(patron_inc, reemplazo_inc, html_content,
                              count=1, flags=re.DOTALL)
        cambios.append("Botón de Incidentes actualizado")

    # --- 10.5 Insertar card de Auditoría (antes del cierre de reportes-grid) ---
    if 'Auditoría del Sistema' not in html_content:
        card_auditoria = '''
        <!-- ============================================================
             AUDITORÍA DEL SISTEMA (auto-instalado)
             ============================================================ -->
        {% if usuario.is_staff %}
        <div class="reporte-card">
            <div class="reporte-icon blue"><i class="bi bi-shield-check"></i></div>
            <h3>Auditoría del Sistema</h3>
            <p>Reporte completo de trazabilidad: quién creó, quién modificó,
               cuándo y estado activo de cada registro del sistema.</p>

            <form method="get" action="{% url 'core:reporte_auditoria_pdf' %}"
                  class="filtros-form" id="form-auditoria">

                <select name="tabla" class="filtro-select">
                    <option value="">Todas las tablas</option>
                    <option value="Usuario">Usuarios</option>
                    <option value="Modelo">Modelos</option>
                    <option value="Material">Materiales</option>
                    <option value="LoteProduccion">Lotes de Producción</option>
                    <option value="Etapa">Etapas</option>
                    <option value="RegistroEtapa">Registros de Etapa</option>
                    <option value="Incidente">Incidentes</option>
                    <option value="Maquinaria">Maquinaria</option>
                </select>

                <input type="text" name="usuario" class="filtro-select"
                       placeholder="ID de usuario (opcional)">

                <input type="date" name="fecha_desde" class="filtro-select"
                       placeholder="Creado desde">

                <input type="date" name="fecha_hasta" class="filtro-select"
                       placeholder="Creado hasta">

                <label class="filtro-checkbox">
                    <input type="checkbox" name="solo_activos" value="1">
                    <span>Solo activos</span>
                </label>
            </form>

            <button type="button" class="btn-reporte btn-blue"
                    onclick="descargarConFiltros('form-auditoria',
                             '{% url 'core:reporte_auditoria_pdf' %}');">
                <i class="bi bi-download"></i> Descargar PDF
            </button>
        </div>
        {% endif %}

'''
        # Insertar antes del último </div> que cierra reportes-grid
        # (buscamos el último </div>\n</div> antes de {% endblock %})
        patron_cierre = r'(\s*</div>\s*</div>\s*\{% endblock %\})'
        if re.search(patron_cierre, html_content):
            html_content = re.sub(
                patron_cierre,
                card_auditoria + r'\1',
                html_content, count=1
            )
            cambios.append("Card de Auditoría insertada")
        else:
            log("No se pudo insertar el card de auditoría (estructura no detectada)", 'warn')

    # --- 10.6 Añadir <script> helper al final (antes de {% endblock %}) ---
    if 'function descargarConFiltros' not in html_content:
        js_helper = '''
<!-- ================================================================
     Helper JS (auto-instalado): arma URL con filtros del formulario
     ================================================================ -->
<script>
function descargarConFiltros(formId, baseUrl) {
    const form = document.getElementById(formId);
    if (!form) { window.location.href = baseUrl; return; }
    const fd = new FormData(form);
    const params = new URLSearchParams();
    for (const [key, value] of fd.entries()) {
        if (value !== null && value !== undefined && String(value).trim() !== '') {
            params.append(key, value);
        }
    }
    const qs = params.toString();
    window.location.href = qs ? `${baseUrl}?${qs}` : baseUrl;
}
</script>

<style>
    .filtro-checkbox {
        display: flex; align-items: center; gap: 6px;
        font-size: 0.9rem; color: #334155;
        padding: 6px 10px; border: 1px solid #e2e8f0;
        border-radius: 6px; background: #f8fafc;
        cursor: pointer; user-select: none;
    }
    .filtro-checkbox input[type="checkbox"] { accent-color: #059669; cursor: pointer; }
    .btn-reporte {
        display: inline-flex; align-items: center; justify-content: center;
        gap: 6px; padding: 10px 16px; border: none; border-radius: 8px;
        color: #fff; font-weight: 600; cursor: pointer; text-decoration: none;
        transition: transform .15s ease;
    }
    .btn-reporte:hover { transform: translateY(-1px); }
    .btn-blue{background:#2563eb;} .btn-green{background:#059669;}
    .btn-orange{background:#ea580c;} .btn-red{background:#dc2626;}
    .btn-purple{background:#7c3aed;} .btn-teal{background:#0d9488;}
</style>
'''
        patron_endblock = r'(\{% endblock %\})'
        # solo el último endblock
        posiciones = [m.start() for m in re.finditer(patron_endblock, html_content)]
        if posiciones:
            pos = posiciones[-1]
            html_content = html_content[:pos] + js_helper + '\n' + html_content[pos:]
            cambios.append("Helper JS + estilos añadidos")
        else:
            log("No se pudo añadir el JS helper (no se encontró {% endblock %})", 'warn')

    # Guardar
    PANEL_HTML.write_text(html_content, encoding='utf-8')
    if cambios:
        for c in cambios:
            log(f"   - {c}", 'ok')
        log("panel_reportes.html actualizado", 'ok')
    else:
        log("panel_reportes.html no necesitaba cambios", 'skip')


# ============================================================
# 11. Resumen final
# ============================================================
print()
print("=" * 62)
print("   INSTALACIÓN COMPLETADA")
print("=" * 62)
print()
print(f"Backup en: {BACKUP_DIR}")
print()
print("PRÓXIMOS PASOS:")
print("   1) python manage.py makemigrations")
print("   2) python manage.py migrate")
print("   3) python manage.py runserver")
print()
print("Accede al panel de reportes como ADMINISTRADOR (is_staff=True)")
print("para ver la nueva card 'Auditoría del Sistema'.")
print()
print("Notas:")
print("   - Los campos nuevos son NULL/DEFAULT: NO rompen funcionalidad.")
print("   - Si algo falla, restaura los .py y .html desde:")
print(f"       {BACKUP_DIR}")
print("   - El script es idempotente: puedes volver a ejecutarlo sin riesgo.")
print()