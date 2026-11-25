# -*- coding: utf-8 -*-
"""
services.py - Logica de Negocio y KPIs del Sistema
Manufacturera de Calzado 3-JJJ-A

Django 4.2 compatible - Windows 7
"""

from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import (
    Incidente, Modelo, Material, MaterialModelo,
    LoteProduccion, Etapa, RegistroEtapa,
    DesperdicioMaterial, Maquinaria, Usuario,
    TIPO_INCIDENTE_CHOICES, ESTADO_INCIDENTE_CHOICES, SEVERIDAD_CHOICES
)


# ============================================================
# 1. SERVICIO: CONSUMO ENERGETICO
# ============================================================
def calcular_consumo_energetico(minutos, maquina):
    if not maquina or not maquina.potencia_kw:
        return 0.0
    horas = minutos / 60.0
    return round(horas * maquina.potencia_kw * (maquina.factor_carga or 1.0), 3)


def calcular_kw_hora():
    etapas = Etapa.objects.all().order_by('secuencia')
    labels = []
    values = []
    for etapa in etapas:
        labels.append(etapa.nombre_etapa)
        registros = RegistroEtapa.objects.filter(id_etapa=etapa)
        total_kwh = sum(r.consumo_energetico_kwh for r in registros) or 0
        if total_kwh == 0:
            valores_simulados = {'Corte': 45.2, 'Bordado': 32.8, 'Taller': 28.5,
                                'Inyeccion': 56.3, 'Calidad': 12.1}
            total_kwh = valores_simulados.get(etapa.nombre_etapa, 20.0)
        values.append(round(total_kwh, 2))
    return {'labels': labels, 'values': values}


# ============================================================
# 2. SERVICIO: QUEUE TIME
# ============================================================
def calcular_queue_time():
    etapas = Etapa.objects.all().order_by('secuencia')
    labels = []
    values = []
    for etapa in etapas:
        labels.append(etapa.nombre_etapa)
        registros = RegistroEtapa.objects.filter(id_etapa=etapa, hora_salida__isnull=False)
        if registros.exists():
            tiempos = []
            for reg in registros:
                etapa_anterior = Etapa.objects.filter(secuencia__lt=etapa.secuencia).order_by('-secuencia').first()
                if etapa_anterior:
                    reg_anterior = RegistroEtapa.objects.filter(
                        id_lote=reg.id_lote, id_etapa=etapa_anterior
                    ).order_by('-hora_salida').first()
                    if reg_anterior and reg_anterior.hora_salida:
                        espera = (reg.hora_entrada - reg_anterior.hora_salida).total_seconds() / 60
                        if espera > 0:
                            tiempos.append(espera)
            valor = round(sum(tiempos) / len(tiempos), 1) if tiempos else 0
        else:
            valores_simulados = {'Corte': 5, 'Bordado': 12, 'Taller': 8,
                                'Inyeccion': 15, 'Calidad': 3}
            valor = valores_simulados.get(etapa.nombre_etapa, 5)
        values.append(valor)
    return {'labels': labels, 'values': values}


# ============================================================
# 3. SERVICIO: THROUGHPUT
# ============================================================
def calcular_throughput():
    etapas = Etapa.objects.all().order_by('secuencia')
    labels = []
    values = []
    for etapa in etapas:
        labels.append(etapa.nombre_etapa)
        registros = RegistroEtapa.objects.filter(id_etapa=etapa, hora_salida__isnull=False)
        if registros.exists():
            throughput_vals = []
            for reg in registros:
                duracion_horas = (reg.hora_salida - reg.hora_entrada).total_seconds() / 3600
                if duracion_horas > 0:
                    pares = reg.pares_aprobados + reg.pares_rechazados
                    throughput_vals.append(pares / duracion_horas)
            valor = round(sum(throughput_vals) / len(throughput_vals), 1) if throughput_vals else 0
        else:
            valores_simulados = {'Corte': 85, 'Bordado': 72, 'Taller': 90,
                                'Inyeccion': 68, 'Calidad': 95}
            valor = valores_simulados.get(etapa.nombre_etapa, 70)
        values.append(valor)
    return {'labels': labels, 'values': values}


# ============================================================
# 4. SERVICIO: BALANCEO DE LINEA
# ============================================================
def calcular_balanceo_linea():
    etapas = Etapa.objects.all().order_by('secuencia')
    labels = []
    actual = []
    teorico = []
    for etapa in etapas:
        labels.append(etapa.nombre_etapa)
        cap_teorica = 1000
        registros = RegistroEtapa.objects.filter(id_etapa=etapa, hora_salida__isnull=False)
        if registros.exists():
            pares_totales = sum(r.pares_aprobados + r.pares_rechazados for r in registros)
            horas_totales = sum((r.hora_salida - r.hora_entrada).total_seconds() / 3600 for r in registros if r.hora_salida)
            cap_real = round((pares_totales / horas_totales) if horas_totales > 0 else 0, 1)
        else:
            valores_simulados = {'Corte': 85, 'Bordado': 72, 'Taller': 90,
                                'Inyeccion': 68, 'Calidad': 95}
            cap_real = valores_simulados.get(etapa.nombre_etapa, 80)
        actual.append(cap_real)
        teorico.append(cap_teorica)
    return {'labels': labels, 'actual': actual, 'teorico': teorico}


# ============================================================
# 5. SERVICIO: TIEMPO MUERTO
# ============================================================
def calcular_tiempo_muerto_sistema():
    dias = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab']
    valores = []
    for i, dia in enumerate(dias):
        fecha_inicio = timezone.now().date() - timedelta(days=timezone.now().weekday() - i)
        registros = RegistroEtapa.objects.filter(hora_entrada__date=fecha_inicio, hora_salida__isnull=False)
        if registros.exists():
            tiempo_total = sum((r.hora_salida - r.hora_entrada).total_seconds() / 60 for r in registros)
            tiempo_disponible = len(registros) * 480
            tiempo_muerto = max(0, tiempo_disponible - tiempo_total)
            valores.append(round(tiempo_muerto, 1))
        else:
            valores_simulados = [12, 8, 15, 6, 10, 4]
            valores.append(valores_simulados[i])
    return {'labels': dias, 'values': valores}


# ============================================================
# 6. SERVICIO: CAPACIDAD REAL
# ============================================================
def calcular_capacidad_real():
    etapas = Etapa.objects.all().order_by('secuencia')
    labels = []
    real = []
    teorica = []
    for etapa in etapas:
        labels.append(etapa.nombre_etapa)
        cap_teorica = 1000
        registros = RegistroEtapa.objects.filter(id_etapa=etapa, hora_salida__isnull=False)
        if registros.exists():
            pares_totales = sum(r.pares_aprobados + r.pares_rechazados for r in registros)
            horas_totales = sum((r.hora_salida - r.hora_entrada).total_seconds() / 3600 for r in registros if r.hora_salida)
            cap_real = round((pares_totales / horas_totales) if horas_totales > 0 else 0, 1)
        else:
            valores_simulados = {'Corte': 880, 'Bordado': 720, 'Taller': 950,
                                'Inyeccion': 680, 'Calidad': 1000}
            cap_real = valores_simulados.get(etapa.nombre_etapa, 800)
        real.append(cap_real)
        teorica.append(cap_teorica)
    return {'labels': labels, 'real': real, 'teorica': teorica}


# ============================================================
# 7. SERVICIO: INCIDENTES ACTIVOS
# ============================================================
def obtener_incidentes_activos(limite=None):
    queryset = Incidente.objects.filter(
        estado__in=['PENDIENTE', 'EN_PROCESO', 'ESCALADO']
    ).select_related('id_usuario_reporta', 'id_etapa', 'id_lote').order_by('-fecha_reporte')
    if limite:
        queryset = queryset[:limite]
    return queryset


def obtener_todos_incidentes(fecha_desde=None, fecha_hasta=None, etapa=None, estado=None):
    queryset = Incidente.objects.select_related('id_usuario_reporta', 'id_etapa', 'id_lote')
    if fecha_desde:
        queryset = queryset.filter(fecha_reporte__date__gte=fecha_desde)
    if fecha_hasta:
        queryset = queryset.filter(fecha_reporte__date__lte=fecha_hasta)
    if etapa:
        queryset = queryset.filter(id_etapa__id_etapa=etapa)
    if estado:
        queryset = queryset.filter(estado=estado)
    return queryset.order_by('-fecha_reporte')


# ============================================================
# 8. SERVICIO: ESTADISTICAS DE INCIDENTES
# ============================================================
def obtener_estadisticas_incidentes():
    hoy = timezone.now().date()
    abiertos = Incidente.objects.filter(estado='PENDIENTE').count()
    en_proceso = Incidente.objects.filter(estado='EN_PROCESO').count()
    resueltos_hoy = Incidente.objects.filter(estado='RESUELTO', fecha_resolucion__date=hoy).count()
    escalados = Incidente.objects.filter(estado='ESCALADO').count()

    por_tipo = dict(
        Incidente.objects.values('tipo_incidente')
        .annotate(total=Count('id_incidente'))
        .values_list('tipo_incidente', 'total')
    )
    tipo_labels = dict(TIPO_INCIDENTE_CHOICES)
    por_tipo_formateado = {tipo_labels.get(k, k): v for k, v in por_tipo.items()}

    por_area = dict(
        Incidente.objects.values('id_etapa__nombre_etapa')
        .annotate(total=Count('id_incidente'))
        .values_list('id_etapa__nombre_etapa', 'total')
    )

    return {
        'total_pendientes': abiertos,
        'total_en_proceso': en_proceso,
        'total_resueltos_hoy': resueltos_hoy,
        'total_escalados': escalados,
        'total_activos': abiertos + en_proceso + escalados,
        'por_tipo': por_tipo_formateado,
        'por_area': por_area,
    }


# ============================================================
# 9. SERVICIO: OEE
# ============================================================
def calcular_oee_global(fecha=None):
    if fecha is None:
        fecha = timezone.now().date()

    registros = RegistroEtapa.objects.filter(hora_entrada__date=fecha, hora_salida__isnull=False)
    if not registros.exists():
        fecha = timezone.now().date() - timedelta(days=7)
        registros = RegistroEtapa.objects.filter(hora_entrada__date__gte=fecha, hora_salida__isnull=False)

    if not registros.exists():
        return {
            'oee_global': 0.0,
            'disponibilidad': 0.0,
            'rendimiento': 0.0,
            'calidad': 0.0,
            'pares_totales': 0,
        }

    pares_totales = sum(r.pares_aprobados + r.pares_rechazados for r in registros)
    pares_defectuosos = sum(r.pares_rechazados for r in registros)
    tiempo_disponible = len(registros) * 480
    tiempo_productivo = sum((r.hora_salida - r.hora_entrada).total_seconds() / 60 for r in registros)
    tiempo_parada = max(0, tiempo_disponible - tiempo_productivo)

    disponibilidad = (tiempo_productivo / tiempo_disponible * 100) if tiempo_disponible > 0 else 0
    rendimiento = 85.0
    calidad = ((pares_totales - pares_defectuosos) / pares_totales * 100) if pares_totales > 0 else 100
    oee_global = (disponibilidad / 100) * (rendimiento / 100) * (calidad / 100) * 100

    return {
        'oee_global': round(min(oee_global, 100), 2),
        'disponibilidad': round(disponibilidad, 2),
        'rendimiento': round(min(rendimiento, 100), 2),
        'calidad': round(calidad, 2),
        'pares_totales': pares_totales,
    }


# ============================================================
# 10. SERVICIO: EFICIENCIA POR AREA
# ============================================================
def obtener_eficiencia_por_area(fecha=None):
    if fecha is None:
        fecha = timezone.now().date()

    etapas = Etapa.objects.all().order_by('secuencia')
    areas_nombres = []
    eficiencia_valores = []
    calidad_valores = []
    disponibilidad_valores = []

    for etapa in etapas:
        regs = RegistroEtapa.objects.filter(id_etapa=etapa, hora_salida__isnull=False)
        if regs.exists():
            pares_totales = sum(r.pares_aprobados + r.pares_rechazados for r in regs)
            pares_defectuosos = sum(r.pares_rechazados for r in regs)
            tiempo_disponible = len(regs) * 480
            tiempo_productivo = sum((r.hora_salida - r.hora_entrada).total_seconds() / 60 for r in regs)
            disp = (tiempo_productivo / tiempo_disponible * 100) if tiempo_disponible > 0 else 0
            rend = 85.0
            cal = ((pares_totales - pares_defectuosos) / pares_totales * 100) if pares_totales > 0 else 100
            oee = (disp / 100) * (rend / 100) * (cal / 100) * 100
        else:
            disp = 0
            rend = 0
            cal = 0
            oee = 0

        areas_nombres.append(etapa.nombre_etapa)
        eficiencia_valores.append(round(min(oee, 100), 2))
        calidad_valores.append(round(cal, 2))
        disponibilidad_valores.append(round(disp, 2))

    return {
        'areas': areas_nombres,
        'eficiencia': eficiencia_valores,
        'calidad': calidad_valores,
        'disponibilidad': disponibilidad_valores,
    }


# ============================================================
# 11. SERVICIO: MODELOS
# ============================================================
def obtener_modelos_activos(busqueda=None):
    queryset = Modelo.objects.all().order_by('-fecha_registro')
    if busqueda:
        queryset = queryset.filter(Q(nombre__icontains=busqueda) | Q(id_modelo__icontains=busqueda))
    return queryset


def obtener_todos_modelos(busqueda=None):
    queryset = Modelo.objects.all().order_by('-fecha_registro')
    if busqueda:
        queryset = queryset.filter(Q(nombre__icontains=busqueda) | Q(id_modelo__icontains=busqueda))
    return queryset


# ============================================================
# 12. SERVICIO: RESUMEN DASHBOARD
# ============================================================
def obtener_resumen_dashboard():
    return {
        'oee': calcular_oee_global(),
        'eficiencia_area': obtener_eficiencia_por_area(),
        'incidentes': obtener_estadisticas_incidentes(),
        'incidentes_activos': obtener_incidentes_activos(limite=10),
        'total_modelos': Modelo.objects.count(),
        'total_lotes': LoteProduccion.objects.count(),
        'total_etapas': Etapa.objects.count(),
        'total_operarios': Usuario.objects.filter(rol='OPERARIO').count(),
        'kw_hora': calcular_kw_hora(),
        'queue_time': calcular_queue_time(),
        'throughput': calcular_throughput(),
        'balanceo_linea': calcular_balanceo_linea(),
        'tiempo_muerto': calcular_tiempo_muerto_sistema(),
        'capacidad_real': calcular_capacidad_real(),
    }


# ============================================================
# 13. SERVICIO: DATOS OPERARIO
# ============================================================
def obtener_datos_operario(etapa, usuario):
    movimientos = RegistroEtapa.objects.filter(
        id_etapa=etapa
    ).select_related('id_lote', 'id_usuario').order_by('-hora_entrada')[:20]

    lotes_activos = RegistroEtapa.objects.filter(
        id_etapa=etapa, hora_salida__isnull=True
    ).select_related('id_lote').order_by('-hora_entrada')

    hoy = timezone.now().date()
    registros_hoy = RegistroEtapa.objects.filter(id_etapa=etapa, hora_entrada__date=hoy)

    total_pares_hoy = sum(r.pares_aprobados + r.pares_rechazados for r in registros_hoy)
    total_aprobados_hoy = sum(r.pares_aprobados for r in registros_hoy)
    total_rechazados_hoy = sum(r.pares_rechazados for r in registros_hoy)

    eficiencia = 0
    if registros_hoy.exists():
        tiempo_productivo = sum(
            (r.hora_salida - r.hora_entrada).total_seconds() / 3600
            for r in registros_hoy if r.hora_salida
        )
        if tiempo_productivo > 0:
            eficiencia = round((total_pares_hoy / tiempo_productivo) / 100 * 100, 2)

    return {
        'etapa': etapa,
        'movimientos': movimientos,
        'lotes_activos': lotes_activos,
        'total_pares_hoy': total_pares_hoy,
        'total_aprobados_hoy': total_aprobados_hoy,
        'total_rechazados_hoy': total_rechazados_hoy,
        'eficiencia_turno': eficiencia,
        'total_registros_hoy': registros_hoy.count(),
    }


# ============================================================
# 14. SERVICIO: DATOS CALIDAD
# ============================================================
def obtener_datos_calidad():
    lotes = LoteProduccion.objects.select_related('id_modelo').all().order_by('-fecha_creacion')[:50]

    registros_calidad = RegistroEtapa.objects.filter(id_etapa__nombre_etapa__iexact='Calidad')

    total_auditados = registros_calidad.count()
    total_aprobados = sum(r.pares_aprobados for r in registros_calidad)
    total_rechazados = sum(r.pares_rechazados for r in registros_calidad)
    total_pares = total_aprobados + total_rechazados

    tasa_calidad = round((total_aprobados / total_pares * 100), 2) if total_pares > 0 else 100

    return {
        'lotes': lotes,
        'total_auditados': total_auditados,
        'total_aprobados': total_aprobados,
        'total_rechazados': total_rechazados,
        'tasa_calidad': tasa_calidad,
    }


# ============================================================
# 15. SERVICIO: DATOS CONFIGURACION
# ============================================================
def obtener_datos_configuracion():
    return {
        'modelos': Modelo.objects.select_related().all().order_by('-fecha_registro'),
        'materiales': Material.objects.all(),
        'etapas': Etapa.objects.all().order_by('secuencia'),
        'maquinarias': Maquinaria.objects.select_related('id_etapa').all(),
        'lotes': LoteProduccion.objects.select_related('id_modelo').all().order_by('-fecha_creacion')[:20],
    }
