# -*- coding: utf-8 -*-
"""
views.py - Vistas del Sistema de Gestion de Produccion
Manufacturera de Calzado 3-JJJ-A

Sistema de contraseña temporal SIN modificar la base de datos:
el estado se guarda en media/sistema/password_temporal.json
"""

import json
import logging
import os
from pathlib import Path

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.utils import timezone
from django.core.files.storage import default_storage
from django.conf import settings
from datetime import datetime, timedelta

from .models import (
    Usuario, Material, Modelo, MaterialModelo,
    LoteProduccion, Etapa, RegistroEtapa,
    DesperdicioMaterial, Maquinaria, Incidente,
    ROL_OPERARIO, ROL_GERENTE, ROL_SUBGERENTE,
    ROL_DIRECTOR_PRODUCCION, ROL_DIRECTOR_DESPACHO,
    ROLES_CHOICES,
    TIPO_INCIDENTE_CHOICES, ESTADO_INCIDENTE_CHOICES, SEVERIDAD_CHOICES
)
from .forms import (
    IncidenteForm, ActualizarIncidenteForm,
    ModeloCalzadoForm, BusquedaModeloForm, RegistroUsuarioForm,
    LoginForm, MaquinariaForm,
    CambiarPasswordTemporalForm,
    validar_password_completa,
)
from .services import (
    obtener_resumen_dashboard,
    obtener_incidentes_activos,
    obtener_estadisticas_incidentes,
    calcular_oee_global,
    obtener_eficiencia_por_area,
    obtener_modelos_activos,
    obtener_todos_modelos,
    obtener_datos_operario,
    obtener_datos_calidad,
    obtener_datos_configuracion,
    calcular_consumo_energetico,
)

logger = logging.getLogger(__name__)


# ============================================================
# SISTEMA DE CONTRASEÑA TEMPORAL (archivo JSON - sin BD)
# ============================================================
def _ruta_archivo_temporales():
    """Ruta del archivo JSON donde se registran los usuarios con pass temporal."""
    base = Path(getattr(settings, 'MEDIA_ROOT', settings.BASE_DIR))
    carpeta = base / 'sistema'
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta / 'password_temporal.json'


def _cargar_temporales():
    """Devuelve la lista de IDs de usuario con contraseña temporal."""
    ruta = _ruta_archivo_temporales()
    if not ruta.exists():
        return []
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x) for x in data]
        return []
    except (json.JSONDecodeError, OSError):
        return []


def _guardar_temporales(lista):
    """Guarda la lista de IDs en el archivo JSON (sin duplicados)."""
    ruta = _ruta_archivo_temporales()
    unicos = sorted(set(str(x) for x in lista))
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(unicos, f, ensure_ascii=False, indent=2)


def marcar_password_temporal(id_usuario):
    """Marca al usuario como poseedor de contraseña temporal."""
    if not id_usuario:
        return
    lista = _cargar_temporales()
    id_usuario = str(id_usuario)
    if id_usuario not in lista:
        lista.append(id_usuario)
        _guardar_temporales(lista)


def quitar_password_temporal(id_usuario):
    """Quita la marca de contraseña temporal del usuario."""
    if not id_usuario:
        return
    lista = _cargar_temporales()
    id_usuario = str(id_usuario)
    if id_usuario in lista:
        lista.remove(id_usuario)
        _guardar_temporales(lista)


def tiene_password_temporal(id_usuario):
    """Verifica si el usuario tiene contraseña temporal pendiente."""
    if not id_usuario:
        return False
    return str(id_usuario) in _cargar_temporales()


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




# ============================================================
# HELPER: Imagenes de modelos (sin campo en BD)
# ============================================================
def get_imagen_modelo_url(id_modelo):
    extensiones = ['.jpg', '.jpeg', '.png', '.webp']
    for ext in extensiones:
        ruta = os.path.join('modelos', f"{id_modelo}{ext}")
        if default_storage.exists(ruta):
            return os.path.join(settings.MEDIA_URL, ruta).replace('\\', '/')
    return None


def guardar_imagen_modelo(id_modelo, archivo):
    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
        ext = '.jpg'
    nombre_archivo = f"modelos/{id_modelo}{ext}"
    for old_ext in ['.jpg', '.jpeg', '.png', '.webp']:
        old_ruta = f"modelos/{id_modelo}{old_ext}"
        if default_storage.exists(old_ruta):
            default_storage.delete(old_ruta)
    default_storage.save(nombre_archivo, archivo)
    return os.path.join(settings.MEDIA_URL, nombre_archivo).replace('\\', '/')


def eliminar_imagen_modelo(id_modelo):
    eliminada = False
    for ext in ['.jpg', '.jpeg', '.png', '.webp']:
        ruta = f"modelos/{id_modelo}{ext}"
        if default_storage.exists(ruta):
            default_storage.delete(ruta)
            eliminada = True
    return eliminada


# ============================================================
# SESION Y AUTENTICACION PROPIA
# ============================================================
SESSION_KEY = 'usuario_id'


def get_usuario_sesion(request):
    usuario_id = request.session.get(SESSION_KEY)
    if usuario_id:
        try:
            return Usuario.objects.get(id_usuario=usuario_id)
        except Usuario.DoesNotExist:
            pass
    return None


def requiere_rol(*roles_permitidos):
    """Decorador para restringir vistas por rol y forzar cambio de contraseña temporal."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            usuario = get_usuario_sesion(request)
            if not usuario:
                messages.error(request, 'Debe iniciar sesion para acceder.')
                return redirect('core:login')
            if tiene_password_temporal(usuario.id_usuario):
                messages.warning(
                    request,
                    'Debe cambiar su contraseña temporal antes de continuar.'
                )
                return redirect('core:cambiar_password_temporal')
            if usuario.rol not in roles_permitidos and not usuario.is_staff:
                return render(request, 'errors/403.html', status=403)
            request.usuario_actual = usuario
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# 0. VISTA: LOGIN PERSONALIZADO
# ============================================================
def login_view(request):
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


def logout_view(request):
    if SESSION_KEY in request.session:
        del request.session[SESSION_KEY]
    messages.info(request, 'Ha cerrado sesion correctamente.')
    return redirect('core:login')


# ============================================================
# VISTA: CAMBIO OBLIGATORIO DE CONTRASEÑA TEMPORAL
# ============================================================
def cambiar_password_temporal_view(request):
    usuario = get_usuario_sesion(request)
    if not usuario:
        messages.error(request, 'Debe iniciar sesion para acceder.')
        return redirect('core:login')

    if not tiene_password_temporal(usuario.id_usuario):
        return redirect('core:redirect_por_rol')

    if request.method == 'POST':
        form = CambiarPasswordTemporalForm(request.POST)
        if form.is_valid():
            nueva = form.cleaned_data['password1']
            usuario.set_password(nueva)
            usuario.save()
            quitar_password_temporal(usuario.id_usuario)
            messages.success(
                request,
                'Contraseña actualizada correctamente. Bienvenido al sistema.'
            )
            return redirect('core:redirect_por_rol')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = CambiarPasswordTemporalForm()

    return render(
        request,
        'registration/cambiar_password_temporal.html',
        {'form': form, 'usuario': usuario}
    )


def redirect_por_rol(request):
    usuario = get_usuario_sesion(request)
    if not usuario:
        messages.error(request, 'Debe iniciar sesion primero.')
        return redirect('core:login')

    if tiene_password_temporal(usuario.id_usuario):
        return redirect('core:cambiar_password_temporal')

    if usuario.rol in (ROL_GERENTE, ROL_SUBGERENTE):
        return redirect('core:dashboard')
    elif usuario.rol in (ROL_DIRECTOR_PRODUCCION, ROL_DIRECTOR_DESPACHO):
        return redirect('core:configuracion')
    elif usuario.rol == ROL_OPERARIO:
        if usuario.etapa_asignada:
            return redirect('core:operario_etapa', etapa_id=usuario.etapa_asignada.id_etapa)
        return redirect('core:operario')
    return redirect('core:dashboard')


# ============================================================
# 1. VISTA: DASHBOARD GERENCIAL
# ============================================================
@requiere_rol(ROL_GERENTE, ROL_SUBGERENTE)
def dashboard_view(request):
    resumen = obtener_resumen_dashboard()
    contexto = {
        'usuario': request.usuario_actual,
        'oee': resumen['oee'],
        'eficiencia_area': resumen['eficiencia_area'],
        'incidentes_stats': resumen['incidentes'],
        'incidentes_activos': resumen['incidentes_activos'],
        'total_modelos': resumen['total_modelos'],
        'total_lotes': resumen['total_lotes'],
        'total_etapas': resumen['total_etapas'],
        'total_operarios': resumen['total_operarios'],
        'areas_json': resumen['eficiencia_area']['areas'],
        'eficiencia_json': resumen['eficiencia_area']['eficiencia'],
        'calidad_json': resumen['eficiencia_area']['calidad'],
        'oee_valor': resumen['oee']['oee_global'],
        'kw_hora': resumen['kw_hora'],
        'total_kwh': sum(resumen['kw_hora']['values']),
        'queue_time': resumen['queue_time'],
        'throughput': resumen['throughput'],
        'balanceo_linea': resumen['balanceo_linea'],
        'tiempo_muerto': resumen['tiempo_muerto'],
        'capacidad_real': resumen['capacidad_real'],
    }

    dashboard_data = {
        'oee_global': resumen['oee']['oee_global'],
        'kw_hora_labels': resumen['kw_hora']['labels'],
        'kw_hora_values': resumen['kw_hora']['values'],
        'throughput_labels': resumen['throughput']['labels'],
        'throughput_values': resumen['throughput']['values'],
        'queue_time_labels': resumen['queue_time']['labels'],
        'queue_time_values': resumen['queue_time']['values'],
        'balanceo_labels': resumen['balanceo_linea']['labels'],
        'balanceo_actual': resumen['balanceo_linea']['actual'],
        'balanceo_teorico': resumen['balanceo_linea']['teorico'],
        'capacidad_labels': resumen['capacidad_real']['labels'],
        'capacidad_real': resumen['capacidad_real']['real'],
        'capacidad_teorica': resumen['capacidad_real']['teorica'],
        'tiempo_muerto_labels': resumen['tiempo_muerto']['labels'],
        'tiempo_muerto_values': resumen['tiempo_muerto']['values'],
        'eficiencia_areas': resumen['eficiencia_area']['areas'],
        'eficiencia_values': resumen['eficiencia_area']['eficiencia'],
        'calidad_values': resumen['eficiencia_area']['calidad'],
    }
    contexto['dashboard_data'] = dashboard_data

    return render(request, 'dashboard/dashboard.html', contexto)


# ============================================================
# 2. VISTA: CONFIGURACION
# ============================================================
@requiere_rol(ROL_DIRECTOR_PRODUCCION, ROL_DIRECTOR_DESPACHO)
def configuracion_view(request):
    datos = obtener_datos_configuracion()
    if request.method == 'POST':
        form_type = request.POST.get('form_type', '')
        if form_type == 'modelo':
            nombre = request.POST.get('nombre_modelo', '').strip()
            material_nombre = request.POST.get('material', '').strip()
            materiales_list = request.POST.getlist('materiales[]')
            cantidades_list = request.POST.getlist('cantidades[]')
            if nombre:
                id_modelo = f"MOD-{timezone.now().strftime('%Y%m%d')}-{Modelo.objects.count() + 1:03d}"
                modelo = Modelo.objects.create(id_modelo=id_modelo, nombre=nombre)
                if material_nombre:
                    mat, _ = Material.objects.get_or_create(nombre_material=material_nombre, defaults={'unidad_medida': 'm'})
                    MaterialModelo.objects.create(id_modelo=modelo, id_material=mat, cantidad_por_par=1.0)
                for i, mat_nombre in enumerate(materiales_list):
                    if mat_nombre.strip() and i < len(cantidades_list):
                        try:
                            cant = float(cantidades_list[i])
                            mat, _ = Material.objects.get_or_create(nombre_material=mat_nombre.strip(), defaults={'unidad_medida': 'm'})
                            MaterialModelo.objects.create(id_modelo=modelo, id_material=mat, cantidad_por_par=cant)
                        except ValueError:
                            pass
                messages.success(request, f'Modelo "{nombre}" registrado exitosamente.')
                return redirect('core:configuracion')
        elif form_type == 'energia':
            maquina_id = request.POST.get('maquina_id', '').strip()
            potencia = request.POST.get('potencia_kw', '').strip()
            factor = request.POST.get('factor_carga', '').strip()
            if maquina_id:
                try:
                    maquina = Maquinaria.objects.get(id_maquina=maquina_id)
                    if potencia:
                        maquina.potencia_kw = float(potencia)
                    if factor:
                        maquina.factor_carga = float(factor)
                    maquina.save()
                    messages.success(request, f'Maquina {maquina_id} actualizada.')
                except Maquinaria.DoesNotExist:
                    etapa = Etapa.objects.first()
                    Maquinaria.objects.create(
                        id_maquina=maquina_id,
                        potencia_kw=float(potencia) if potencia else 0,
                        factor_carga=float(factor) if factor else 1.0,
                        id_etapa=etapa
                    )
                    messages.success(request, f'Maquina {maquina_id} creada.')
                except ValueError:
                    messages.error(request, 'Valores numericos invalidos.')
            return redirect('core:configuracion')
        elif form_type == 'etapa':
            id_etapa = request.POST.get('id_etapa', '').strip().upper()
            nombre_etapa = request.POST.get('nombre_etapa', '').strip()
            secuencia = request.POST.get('secuencia', '').strip()
            if id_etapa and nombre_etapa:
                if Etapa.objects.filter(id_etapa=id_etapa).exists():
                    messages.error(request, f'La etapa con ID "{id_etapa}" ya existe.')
                else:
                    try:
                        sec = int(secuencia) if secuencia else 0
                        Etapa.objects.create(id_etapa=id_etapa, nombre_etapa=nombre_etapa, secuencia=sec)
                        messages.success(request, f'Etapa "{nombre_etapa}" registrada exitosamente.')
                    except ValueError:
                        messages.error(request, 'La secuencia debe ser un numero entero.')
            else:
                messages.error(request, 'El ID y nombre de la etapa son obligatorios.')
            return redirect('core:configuracion')
        elif form_type == 'lotes':
            lotes_ids = request.POST.getlist('lotes[]')
            cantidades = request.POST.getlist('cantidades[]')
            modelo_id = request.POST.get('modelo_id', '')
            if modelo_id:
                try:
                    modelo = Modelo.objects.get(id_modelo=modelo_id)
                    creados = 0
                    for i, lote_id in enumerate(lotes_ids):
                        if lote_id.strip() and i < len(cantidades):
                            try:
                                cant = int(cantidades[i])
                                LoteProduccion.objects.create(id_lote=lote_id.strip(), cant_solicitada=cant, id_modelo=modelo)
                                creados += 1
                            except ValueError:
                                pass
                    messages.success(request, f'{creados} lotes registrados para modelo {modelo.nombre}.')
                except Modelo.DoesNotExist:
                    messages.error(request, 'Modelo no encontrado.')
            return redirect('core:configuracion')
        elif form_type == 'maquinaria':
            form = MaquinariaForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, f'Maquina "{form.instance.id_maquina}" registrada exitosamente.')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
            return redirect('core:configuracion')
        elif form_type == 'eliminar_etapa':
            etapa_id = request.POST.get('etapa_id', '').strip()
            if etapa_id:
                try:
                    etapa = Etapa.objects.get(id_etapa=etapa_id)
                    tiene_maquinarias = Maquinaria.objects.filter(id_etapa=etapa).exists()
                    tiene_usuarios = Usuario.objects.filter(etapa_asignada=etapa).exists()
                    tiene_registros = RegistroEtapa.objects.filter(id_etapa=etapa).exists()
                    tiene_incidentes = Incidente.objects.filter(id_etapa=etapa).exists()
                    if tiene_maquinarias or tiene_usuarios or tiene_registros or tiene_incidentes:
                        msgs = []
                        if tiene_maquinarias:
                            msgs.append('maquinarias asignadas')
                        if tiene_usuarios:
                            msgs.append('usuarios asignados')
                        if tiene_registros:
                            msgs.append('registros de produccion')
                        if tiene_incidentes:
                            msgs.append('incidentes relacionados')
                        messages.error(
                            request,
                            f'No se puede eliminar la etapa "{etapa.nombre_etapa}" porque tiene: {", ".join(msgs)}.'
                        )
                    else:
                        etapa.delete()
                        messages.success(request, f'Etapa "{etapa.nombre_etapa}" eliminada exitosamente.')
                except Etapa.DoesNotExist:
                    messages.error(request, 'Etapa no encontrada.')
            return redirect('core:configuracion')
    contexto = {
        'usuario': request.usuario_actual,
        'modelos': datos['modelos'],
        'materiales': datos['materiales'],
        'etapas': datos['etapas'],
        'maquinarias': datos['maquinarias'],
        'lotes': datos['lotes'],
        'maquinaria_form': MaquinariaForm(),
    }
    return render(request, 'configuracion/configuracion.html', contexto)


# ============================================================
# 3. VISTA: OPERARIO POR ETAPA
# ============================================================
@requiere_rol(ROL_OPERARIO)
def operario_etapa_view(request, etapa_id):
    usuario = request.usuario_actual
    etapa = get_object_or_404(Etapa, id_etapa=etapa_id)
    if usuario.etapa_asignada and usuario.etapa_asignada.id_etapa != etapa_id:
        messages.error(request, 'No tiene permiso para acceder a esta etapa.')
        return redirect('core:operario')
    if request.method == 'POST':
        accion = request.POST.get('accion', '')
        lote_id = request.POST.get('lote_id', '').strip().upper()
        if lote_id:
            try:
                lote = LoteProduccion.objects.get(id_lote__iexact=lote_id)
                if accion == 'Entrada':
                    RegistroEtapa.objects.create(
                        hora_entrada=timezone.now(),
                        id_lote=lote,
                        id_etapa=etapa,
                        id_usuario=usuario,
                        estado_actual='EN_PROCESO'
                    )
                    messages.success(request, f'Entrada registrada: Lote {lote_id} en {etapa.nombre_etapa}.')
                elif accion == 'Salida':
                    registro = RegistroEtapa.objects.filter(
                        id_lote=lote,
                        id_etapa=etapa,
                        hora_salida__isnull=True
                    ).order_by('-hora_entrada').first()
                    if registro:
                        registro.hora_salida = timezone.now()
                        delta = registro.hora_salida - registro.hora_entrada
                        horas = int(delta.total_seconds() // 3600)
                        minutos = int((delta.total_seconds() % 3600) // 60)
                        registro.tiempo_total_etapa = f"{horas}h {minutos}m"
                        maquina = Maquinaria.objects.filter(id_etapa=etapa).first()
                        if maquina:
                            minutos_totales = delta.total_seconds() / 60
                            registro.consumo_energetico_kwh = calcular_consumo_energetico(minutos_totales, maquina)
                        registro.estado_actual = 'COMPLETADO'
                        registro.save()
                        messages.success(request, f'Salida registrada: Lote {lote_id} de {etapa.nombre_etapa}.')
                    else:
                        messages.error(request, f'No se encontro entrada activa para el lote {lote_id}.')
            except LoteProduccion.DoesNotExist:
                messages.error(request, f'Lote {lote_id} no encontrado.')
        return redirect('core:operario_etapa', etapa_id=etapa_id)
    datos = obtener_datos_operario(etapa, usuario)
    contexto = {
        'usuario': usuario,
        'etapa': etapa,
        'etapa_actual': etapa.nombre_etapa,
        'movimientos': datos['movimientos'],
        'lotes_activos': datos['lotes_activos'],
        'total_pares_hoy': datos['total_pares_hoy'],
        'total_aprobados_hoy': datos['total_aprobados_hoy'],
        'total_rechazados_hoy': datos['total_rechazados_hoy'],
        'eficiencia_turno': datos['eficiencia_turno'],
        'total_registros_hoy': datos['total_registros_hoy'],
    }
    return render(request, 'operario/operario.html', contexto)


@requiere_rol(ROL_OPERARIO)
def operario_redirect_view(request):
    usuario = request.usuario_actual
    if usuario.etapa_asignada:
        return redirect('core:operario_etapa', etapa_id=usuario.etapa_asignada.id_etapa)
    etapas = Etapa.objects.all().order_by('secuencia')
    return render(request, 'operario/seleccionar_etapa.html', {'usuario': usuario, 'etapas': etapas})


# ============================================================
# 4. VISTA: CONTROL DE CALIDAD
# ============================================================
def calidad_view(request):
    usuario = get_usuario_sesion(request)
    if not usuario:
        messages.error(request, 'Debe iniciar sesion para acceder.')
        return redirect('core:login')

    if tiene_password_temporal(usuario.id_usuario):
        return redirect('core:cambiar_password_temporal')

    es_admin = usuario.is_staff
    es_operario_calidad = (
        usuario.rol == ROL_OPERARIO and
        usuario.etapa_asignada and
        usuario.etapa_asignada.nombre_etapa.lower() == 'calidad'
    )
    if not (es_admin or es_operario_calidad):
        return render(request, 'errors/403.html', status=403)
    request.usuario_actual = usuario
    if request.method == 'POST':
        lote_id = request.POST.get('lote_id', '').strip()
        pares_aprobados = request.POST.get('pares_aprobados', '0')
        pares_rechazados = request.POST.get('pares_rechazados', '0')
        if lote_id:
            try:
                lote = LoteProduccion.objects.get(id_lote__iexact=lote_id)
                etapa_calidad = Etapa.objects.filter(nombre_etapa__iexact='Calidad').first()
                if not etapa_calidad:
                    etapa_calidad = Etapa.objects.create(id_etapa='ETP-CALIDAD', nombre_etapa='Calidad', secuencia=99)
                registro, created = RegistroEtapa.objects.get_or_create(
                    id_lote=lote,
                    id_etapa=etapa_calidad,
                    defaults={'hora_entrada': timezone.now(), 'id_usuario': request.usuario_actual, 'estado_actual': 'EN_PROCESO'}
                )
                registro.pares_aprobados = int(pares_aprobados) if pares_aprobados else 0
                registro.pares_rechazados = int(pares_rechazados) if pares_rechazados else 0
                registro.hora_salida = timezone.now()
                registro.estado_actual = 'COMPLETADO'
                registro.save()
                if registro.pares_rechazados > registro.pares_aprobados:
                    lote.estado_actual = 'RECHAZADO'
                else:
                    lote.estado_actual = 'APROBADO'
                lote.save()
                messages.success(request, f'Inspeccion de calidad registrada para lote {lote_id}.')
            except LoteProduccion.DoesNotExist:
                messages.error(request, f'Lote {lote_id} no encontrado.')
            except ValueError:
                messages.error(request, 'Valores numericos invalidos.')
        return redirect('core:calidad')
    datos = obtener_datos_calidad()
    contexto = {
        'usuario': request.usuario_actual,
        'lotes': datos['lotes'],
        'total_auditados': datos['total_auditados'],
        'total_aprobados': datos['total_aprobados'],
        'total_rechazados': datos['total_rechazados'],
        'tasa_calidad': datos['tasa_calidad'],
    }
    return render(request, 'calidad/calidad.html', contexto)


# ============================================================
# 5. VISTA: CATALOGO DE MODELOS
# ============================================================
@requiere_rol(ROL_GERENTE, ROL_SUBGERENTE)
def catalogo_modelos_view(request):
    form_busqueda = BusquedaModeloForm(request.GET or None)
    termino_busqueda = ''
    if form_busqueda.is_valid():
        termino_busqueda = form_busqueda.cleaned_data.get('q', '')
    if termino_busqueda:
        modelos = Modelo.objects.filter(
            Q(id_modelo__icontains=termino_busqueda) |
            Q(nombre__icontains=termino_busqueda)
        ).order_by('-fecha_registro')
    else:
        modelos = Modelo.objects.all().order_by('-fecha_registro')
    modelos_data = []
    for modelo in modelos:
        modelos_data.append({
            'modelo': modelo,
            'imagen_url': get_imagen_modelo_url(modelo.id_modelo),
        })
    total_modelos = Modelo.objects.count()
    contexto = {
        'usuario': request.usuario_actual,
        'modelos_data': modelos_data,
        'form_busqueda': form_busqueda,
        'termino_busqueda': termino_busqueda,
        'total_modelos': total_modelos,
    }
    return render(request, 'catalogo/catalogo_modelos.html', contexto)


@requiere_rol(ROL_GERENTE, ROL_SUBGERENTE)
def registrar_modelo_view(request):
    if request.method == 'POST':
        form = ModeloCalzadoForm(request.POST, request.FILES)
        if form.is_valid():
            modelo = form.save(commit=False)
            modelo.id_modelo = f"MOD-{timezone.now().strftime('%Y%m%d')}-{Modelo.objects.count() + 1:03d}"
            modelo.save()
            if 'imagen' in request.FILES:
                guardar_imagen_modelo(modelo.id_modelo, request.FILES['imagen'])
            messages.success(request, f'Modelo "{modelo.nombre}" registrado exitosamente.')
            return redirect('core:catalogo_modelos')
        else:
            messages.error(request, 'Por favor corrija los errores del formulario.')
    else:
        form = ModeloCalzadoForm()
    contexto = {
        'usuario': request.usuario_actual,
        'form': form,
        'titulo': 'Registrar Nuevo Modelo',
        'modo': 'crear',
    }
    return render(request, 'catalogo/registrar_modelo.html', contexto)


@requiere_rol(ROL_GERENTE, ROL_SUBGERENTE)
def editar_modelo_view(request, pk):
    modelo = get_object_or_404(Modelo, pk=pk)
    if request.method == 'POST':
        form = ModeloCalzadoForm(request.POST, request.FILES, instance=modelo)
        if form.is_valid():
            form.save()
            if request.POST.get('eliminar_imagen'):
                if eliminar_imagen_modelo(modelo.id_modelo):
                    messages.info(request, 'Imagen eliminada.')
            elif 'imagen' in request.FILES:
                guardar_imagen_modelo(modelo.id_modelo, request.FILES['imagen'])
            messages.success(request, f'Modelo "{modelo.nombre}" actualizado correctamente.')
            return redirect('core:catalogo_modelos')
        else:
            messages.error(request, 'Por favor corrija los errores.')
    else:
        form = ModeloCalzadoForm(instance=modelo)
    contexto = {
        'usuario': request.usuario_actual,
        'form': form,
        'modelo': modelo,
        'titulo': f'Editar Modelo: {modelo.id_modelo}',
        'modo': 'editar',
        'imagen_url': get_imagen_modelo_url(modelo.id_modelo),
    }
    return render(request, 'catalogo/registrar_modelo.html', contexto)


@requiere_rol(ROL_GERENTE, ROL_SUBGERENTE)
def detalle_modelo_view(request, pk):
    modelo = get_object_or_404(Modelo, pk=pk)
    materiales = MaterialModelo.objects.filter(id_modelo=modelo).select_related('id_material')
    incidentes = Incidente.objects.filter(id_lote__id_modelo=modelo).order_by('-fecha_reporte')[:10]
    contexto = {
        'usuario': request.usuario_actual,
        'modelo': modelo,
        'materiales': materiales,
        'incidentes_relacionados': incidentes,
        'imagen_url': get_imagen_modelo_url(modelo.id_modelo),
    }
    return render(request, 'catalogo/detalle_modelo.html', contexto)


# ============================================================
# 6. VISTA: REPORTAR INCIDENTE
# ============================================================
@requiere_rol(ROL_OPERARIO, ROL_GERENTE, ROL_SUBGERENTE, ROL_DIRECTOR_PRODUCCION, ROL_DIRECTOR_DESPACHO)
def reportar_incidente_view(request):
    if request.method == 'POST':
        form = IncidenteForm(request.POST)
        if form.is_valid():
            incidente = form.save(commit=False)
            incidente.id_usuario_reporta = request.usuario_actual
            incidente.estado = 'PENDIENTE'
            incidente.save()
            messages.success(request, 'Incidente reportado exitosamente.')
            return redirect('core:reportar_incidente')
        else:
            messages.error(request, 'Por favor corrija los errores del formulario.')
    else:
        form = IncidenteForm()
    mis_incidentes = Incidente.objects.filter(id_usuario_reporta=request.usuario_actual).order_by('-fecha_reporte')[:5]
    contexto = {
        'usuario': request.usuario_actual,
        'form': form,
        'mis_incidentes': mis_incidentes,
        'estado_colores': {
            'PENDIENTE': '#ef4444',
            'EN_PROCESO': '#f59e0b',
            'RESUELTO': '#10b981',
            'ESCALADO': '#8b5cf6',
        },
    }
    return render(request, 'incidentes/reportar_incidente.html', contexto)


# ============================================================
# 7. VISTA: HISTORIAL DE INCIDENTES
# ============================================================
@requiere_rol(ROL_GERENTE, ROL_SUBGERENTE)
def historial_incidentes_view(request):
    filtro_etapa = request.GET.get('etapa', '')
    filtro_estado = request.GET.get('estado', '')
    incidentes = Incidente.objects.select_related('id_usuario_reporta', 'id_etapa', 'id_lote')
    if filtro_etapa:
        incidentes = incidentes.filter(id_etapa__id_etapa=filtro_etapa)
    if filtro_estado:
        incidentes = incidentes.filter(estado=filtro_estado)
    incidentes = incidentes.order_by('-fecha_reporte')
    stats = {
        'total': incidentes.count(),
        'pendientes': incidentes.filter(estado='PENDIENTE').count(),
        'en_proceso': incidentes.filter(estado='EN_PROCESO').count(),
        'resueltos': incidentes.filter(estado='RESUELTO').count(),
        'escalados': incidentes.filter(estado='ESCALADO').count(),
    }
    if request.method == 'POST':
        incidente_id = request.POST.get('incidente_id')
        if incidente_id:
            incidente = get_object_or_404(Incidente, pk=incidente_id)
            form_update = ActualizarIncidenteForm(request.POST, instance=incidente)
            if form_update.is_valid():
                instancia = form_update.save(commit=False)
                if instancia.estado == 'RESUELTO':
                    instancia.fecha_resolucion = timezone.now()
                instancia.save()
                messages.success(request, 'Estado del incidente actualizado.')
                return redirect('core:historial_incidentes')
    contexto = {
        'usuario': request.usuario_actual,
        'incidentes': incidentes,
        'stats': stats,
        'filtro_etapa': filtro_etapa,
        'filtro_estado': filtro_estado,
        'etapas': Etapa.objects.all(),
        'estados': ESTADO_INCIDENTE_CHOICES,
        'form_update': ActualizarIncidenteForm(),
    }
    return render(request, 'incidentes/historial_incidentes.html', contexto)


# ============================================================
# 8. VISTA: ACCESO DENEGADO (403)
# ============================================================
def error_403_view(request, exception=None):
    return render(request, 'errors/403.html', status=403)


# ============================================================
# 9. API: ACTUALIZAR ESTADO DE INCIDENTE
# ============================================================
@requiere_rol(ROL_GERENTE, ROL_SUBGERENTE)
@require_http_methods(["POST"])
def api_actualizar_incidente(request, pk):
    try:
        incidente = get_object_or_404(Incidente, pk=pk)
        nuevo_estado = request.POST.get('estado')
        notas = request.POST.get('acciones_tomadas', '').strip()
        if nuevo_estado not in ['PENDIENTE', 'EN_PROCESO', 'RESUELTO', 'ESCALADO']:
            return JsonResponse({'success': False, 'message': 'Estado no valido.'}, status=400)
        incidente.estado = nuevo_estado
        if notas:
            from django.utils.html import strip_tags, escape
            incidente.acciones_tomadas = escape(strip_tags(notas))
        if nuevo_estado == 'RESUELTO':
            incidente.fecha_resolucion = timezone.now()
        incidente.save()
        return JsonResponse({
            'success': True,
            'message': 'Incidente actualizado correctamente.',
            'estado': incidente.get_estado_display(),
            'estado_codigo': incidente.estado,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'}, status=500)


# ============================================================
# VISTA: PANEL DE ADMINISTRACION
# ============================================================
def panel_admin_view(request):
    usuario = get_usuario_sesion(request)
    if not usuario:
        messages.error(request, 'Debe iniciar sesion para acceder.')
        return redirect('core:login')
    if not usuario.is_staff:
        messages.error(request, 'No tiene permisos para acceder al panel de administracion.')
        return render(request, 'errors/403.html', status=403)

    if tiene_password_temporal(usuario.id_usuario):
        return redirect('core:cambiar_password_temporal')

    request.usuario_actual = usuario

    # === OCULTAR_ADMINS (igual que admin_usuarios_view) ===
    usuarios_no_admin = Usuario.objects.exclude(is_staff=True)

    total_usuarios = usuarios_no_admin.count()
    total_operarios = usuarios_no_admin.filter(rol=ROL_OPERARIO).count()
    total_gerentes = usuarios_no_admin.filter(rol__in=[ROL_GERENTE, ROL_SUBGERENTE]).count()
    total_directores = usuarios_no_admin.filter(rol__in=[ROL_DIRECTOR_PRODUCCION, ROL_DIRECTOR_DESPACHO]).count()

    total_etapas = Etapa.objects.count()
    total_maquinas = Maquinaria.objects.count()
    total_modelos = Modelo.objects.count()
    total_lotes = LoteProduccion.objects.count()
    total_materiales = Material.objects.count()
    total_incidentes = Incidente.objects.count()
    incidentes_pendientes = Incidente.objects.filter(estado='PENDIENTE').count()
    incidentes_resueltos = Incidente.objects.filter(estado='RESUELTO').count()
    total_registros = RegistroEtapa.objects.count()
    registros_hoy = RegistroEtapa.objects.filter(hora_entrada__date=timezone.now().date()).count()

    # === Usuarios recientes SIN admins ===
    usuarios_recientes = Usuario.objects.exclude(
        is_staff=True
    ).order_by('-fecha_registro')[:10]

    incidentes_recientes = Incidente.objects.select_related(
        'id_usuario_reporta', 'id_etapa'
    ).order_by('-fecha_reporte')[:10]
    modelos_recientes = Modelo.objects.order_by('-fecha_registro')[:10]
    lotes_recientes = LoteProduccion.objects.select_related(
        'id_modelo'
    ).order_by('-fecha_creacion')[:10]
    registros_recientes = RegistroEtapa.objects.select_related(
        'id_lote', 'id_etapa', 'id_usuario'
    ).order_by('-hora_entrada')[:10]

    hoy = timezone.now().date()
    incidentes_hoy = Incidente.objects.filter(fecha_reporte__date=hoy).count()

    etapas_con_datos = []
    for etapa in Etapa.objects.all().order_by('secuencia'):
        operarios_count = Usuario.objects.filter(
            etapa_asignada=etapa
        ).exclude(is_staff=True).count()
        maquinas_count = Maquinaria.objects.filter(id_etapa=etapa).count()
        etapas_con_datos.append({
            'etapa': etapa,
            'operarios': operarios_count,
            'maquinas': maquinas_count
        })

    contexto = {
        'usuario': request.usuario_actual,
        'total_usuarios': total_usuarios,
        'total_operarios': total_operarios,
        'total_gerentes': total_gerentes,
        'total_directores': total_directores,
        'total_etapas': total_etapas,
        'total_maquinas': total_maquinas,
        'total_modelos': total_modelos,
        'total_lotes': total_lotes,
        'total_materiales': total_materiales,
        'total_incidentes': total_incidentes,
        'incidentes_pendientes': incidentes_pendientes,
        'incidentes_resueltos': incidentes_resueltos,
        'total_registros': total_registros,
        'registros_hoy': registros_hoy,
        'incidentes_hoy': incidentes_hoy,
        'usuarios_recientes': usuarios_recientes,
        'incidentes_recientes': incidentes_recientes,
        'modelos_recientes': modelos_recientes,
        'lotes_recientes': lotes_recientes,
        'registros_recientes': registros_recientes,
        'etapas_con_datos': etapas_con_datos,
    }
    return render(request, 'admin/panel_admin.html', contexto)


# ============================================================
# VISTA: GESTIONAR USUARIOS (Admin)
# ============================================================
def admin_usuarios_view(request):
    usuario = get_usuario_sesion(request)
    if not usuario:
        messages.error(request, 'Debe iniciar sesion para acceder.')
        return redirect('core:login')
    if not usuario.is_staff:
        messages.error(request, 'No tiene permisos para acceder.')
        return render(request, 'errors/403.html', status=403)

    if tiene_password_temporal(usuario.id_usuario):
        return redirect('core:cambiar_password_temporal')

    request.usuario_actual = usuario
    if request.method == 'POST':
        accion = request.POST.get('accion', '')
        usuario_id = request.POST.get('usuario_id', '')
        if accion == 'eliminar' and usuario_id:
            # === BLOQUEO_ELIMINAR_ADMIN_ACTIVO ===
            _target = Usuario.objects.filter(id_usuario=usuario_id).first()
            if _target and _target.is_staff:
                messages.error(request, 'No puede eliminar un administrador.')
                return redirect('core:admin_usuarios')

            try:
                user = Usuario.objects.get(id_usuario=usuario_id)
                if not user.is_staff:
                    user.delete()
                    quitar_password_temporal(usuario_id)
                    messages.success(request, f'Usuario {usuario_id} eliminado.')
                else:
                    messages.error(request, 'No puede eliminar un administrador.')
            except Usuario.DoesNotExist:
                messages.error(request, 'Usuario no encontrado.')
        elif accion == 'activar' and usuario_id:
            try:
                user = Usuario.objects.get(id_usuario=usuario_id)
                user.is_active = True
                user.save()
                messages.success(request, f'Usuario {usuario_id} activado.')
            except Usuario.DoesNotExist:
                messages.error(request, 'Usuario no encontrado.')
        elif accion == 'desactivar' and usuario_id:
            try:
                user = Usuario.objects.get(id_usuario=usuario_id)
                if not user.is_staff:
                    user.is_active = False
                    user.save()
                    messages.success(request, f'Usuario {usuario_id} desactivado.')
                else:
                    messages.error(request, 'No puede desactivar un administrador.')
            except Usuario.DoesNotExist:
                messages.error(request, 'Usuario no encontrado.')
        elif accion == 'cambiar_password' and usuario_id:
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
            return redirect('core:admin_usuarios')
        return redirect('core:admin_usuarios')
    rol_filtro = request.GET.get('rol', '')
    estado_filtro = request.GET.get('estado', '')
    # === OCULTAR_ADMINS_ACTIVO ===
    usuarios_qs = Usuario.objects.all().order_by('-fecha_registro').exclude(is_staff=True)
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
    }
    return render(request, 'admin/admin_usuarios.html', contexto)


# ============================================================
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


# ============================================================
# 10. VISTA: REGISTRO DE NUEVO USUARIO
# ============================================================
def registro_view(request):
    usuario_actual = get_usuario_sesion(request)
    es_admin = usuario_actual and usuario_actual.is_staff

    if usuario_actual and tiene_password_temporal(usuario_actual.id_usuario):
        return redirect('core:cambiar_password_temporal')

    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            if es_admin:
                marcar_password_temporal(user.id_usuario)
                messages.success(
                    request,
                    f'Usuario "{user.id_usuario}" registrado con contraseña temporal.'
                )
                messages.info(request, 'El usuario deberá cambiarla al iniciar sesión.')
                return redirect('core:admin_usuarios')
            else:
                messages.success(
                    request,
                    f'Usuario "{user.id_usuario}" registrado exitosamente. Ahora puede iniciar sesion.'
                )
                return redirect('core:login')
        else:
            messages.error(request, 'Por favor corrija los errores del formulario.')
    else:
        form = RegistroUsuarioForm()
    contexto = {
        'form': form,
        'titulo': 'Registro de Usuario',
        'es_admin': es_admin,
    }
    return render(request, 'registration/registro.html', contexto)


# ============================================================
# VISTA: TRAZABILIDAD DE LOTES
# ============================================================
@requiere_rol(ROL_DIRECTOR_PRODUCCION)
def trazabilidad_view(request):
    etapas = Etapa.objects.all().order_by('secuencia')

    lotes_en_proceso = LoteProduccion.objects.exclude(
        estado_actual__in=['COMPLETADO', 'APROBADO', 'RECHAZADO']
    ).select_related('id_modelo').order_by('-fecha_creacion')

    lote_seleccionado = None
    etapa_actual = None
    progreso = []
    registros_lote = []

    lote_id = request.GET.get('lote')
    if lote_id:
        lote_seleccionado = get_object_or_404(LoteProduccion, pk=lote_id)

        registros_lote = RegistroEtapa.objects.filter(
            id_lote=lote_seleccionado
        ).select_related('id_etapa', 'id_usuario').order_by('hora_entrada')

        registro_actual = registros_lote.filter(estado_actual='EN_PROCESO').first()
        if registro_actual:
            etapa_actual = registro_actual.id_etapa

        for etapa in etapas:
            reg = registros_lote.filter(id_etapa=etapa).first()
            if reg:
                if reg.estado_actual == 'COMPLETADO':
                    estado = 'completado'
                elif reg.estado_actual == 'EN_PROCESO':
                    estado = 'actual'
                else:
                    estado = 'pendiente'
            else:
                estado = 'pendiente'

            progreso.append({
                'etapa': etapa,
                'estado': estado,
                'registro': reg,
            })

    contexto = {
        'usuario': request.usuario_actual,
        'etapas': etapas,
        'lotes_en_proceso': lotes_en_proceso,
        'lote_seleccionado': lote_seleccionado,
        'etapa_actual': etapa_actual,
        'progreso': progreso,
        'registros_lote': registros_lote,
    }
    return render(request, 'trazabilidad/trazabilidad.html', contexto)


# ============================================================
# VISTAS DE REPORTES PDF
# ============================================================
from .reportes_pdf import (
    generar_reporte_usuarios,
    generar_reporte_modelos,
    generar_reporte_lotes,
    generar_reporte_incidentes,
    generar_reporte_materiales,
    generar_reporte_etapas,
)


@requiere_rol(ROL_GERENTE, ROL_SUBGERENTE)
def panel_reportes_view(request):
    return render(request, 'reportes/panel_reportes.html', {'usuario': request.usuario_actual})


@requiere_rol(ROL_GERENTE, ROL_SUBGERENTE)
def reporte_usuarios_pdf(request):
    rol = request.GET.get('rol', '')
    estado = request.GET.get('estado', '')
    return generar_reporte_usuarios(request, rol_filtro=rol or None, estado_filtro=estado or None)


@requiere_rol(ROL_GERENTE, ROL_SUBGERENTE)
def reporte_modelos_pdf(request):
    return generar_reporte_modelos(request)


@requiere_rol(ROL_GERENTE, ROL_SUBGERENTE)
def reporte_lotes_pdf(request):
    estado = request.GET.get('estado', '')
    return generar_reporte_lotes(request, estado=estado or None)


@requiere_rol(ROL_GERENTE, ROL_SUBGERENTE)
def reporte_incidentes_pdf(request):
    estado = request.GET.get('estado', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    return generar_reporte_incidentes(
        request,
        estado=estado or None,
        fecha_desde=fecha_desde or None,
        fecha_hasta=fecha_hasta or None
    )


@requiere_rol(ROL_GERENTE, ROL_SUBGERENTE)
def reporte_materiales_pdf(request):
    return generar_reporte_materiales(request)


@requiere_rol(ROL_GERENTE, ROL_SUBGERENTE)
def reporte_etapas_pdf(request):
    return generar_reporte_etapas(request)




# ============================================================
# VISTA: REPORTE PDF DE AUDITORÍA (solo admin)
# ============================================================
from .reportes_auditoria_pdf import generar_reporte_auditoria


def reporte_auditoria_pdf(request):
    """Genera el PDF de auditoría. Solo accesible para staff."""
    usuario = get_usuario_sesion(request)
    if not usuario or not usuario.is_staff:
        messages.error(request, 'No tiene permisos para acceder.')
        return render(request, 'errors/403.html', status=403)

    if tiene_password_temporal(usuario.id_usuario):
        return redirect('core:cambiar_password_temporal')

    tabla = request.GET.get('tabla', '') or None
    usuario_filtro = request.GET.get('usuario', '') or None
    solo_activos = request.GET.get('solo_activos', '') in ('1', 'true', 'on')

    return generar_reporte_auditoria(
        request,
        tabla=tabla,
        usuario=usuario_filtro,
        solo_activos=solo_activos,
    )