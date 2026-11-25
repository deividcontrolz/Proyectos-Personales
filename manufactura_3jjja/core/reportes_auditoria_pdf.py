# -*- coding: utf-8 -*-
"""
reportes_auditoria_pdf.py
=========================
Reporte PDF de auditoría: muestra para cada tabla principal
el usuario y fecha de creación, usuario y fecha de modificación
y el estado 'activo'.
"""

import io
# PDF-DESIGN-FIX-AUD-APLICADO
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)
from reportlab.platypus.flowables import HRFlowable

from .models import (
    Usuario, Modelo, Material, LoteProduccion, Etapa,
    RegistroEtapa, Incidente, Maquinaria,
)
from .reportes_pdf import (get_estilos, crear_tabla_pdf, agregar_footer, agregar_encabezado)


# ============================================================
# Helper: descripción corta de una instancia
# ============================================================
def _descripcion(obj):
    """Devuelve una descripción legible de cualquier objeto."""
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
# Reporte principal
# ============================================================
def generar_reporte_auditoria(request, tabla=None, usuario=None, solo_activos=False):
    """
    Reporte PDF de auditoría.

    Args:
        tabla: nombre del modelo a filtrar (opcional)
        usuario: id_usuario a filtrar (opcional)
        solo_activos: si True, solo muestra registros con activo=True
    """
    # Mapa de modelos soportados
    TABLAS = {
        'Usuario':           Usuario,
        'Modelo':            Modelo,
        'Material':          Material,
        'LoteProduccion':    LoteProduccion,
        'Etapa':             Etapa,
        'RegistroEtapa':     RegistroEtapa,
        'Incidente':         Incidente,
        'Maquinaria':        Maquinaria,
    }

    # Preparar registros
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
            qs = qs.order_by('-fecha_modificacion', '-fecha_creacion')[:200]
            for obj in qs:
                registros.append({
                    'tabla':      nombre_tabla,
                    'id':         str(getattr(obj, 'pk', '—')),
                    'desc':       _descripcion(obj),
                    'u_crea':     _formato_usuario(getattr(obj, 'usuario_creacion', None)),
                    'f_crea':     _formato_fecha(getattr(obj, 'fecha_creacion', None)),
                    'u_mod':      _formato_usuario(getattr(obj, 'usuario_modificacion', None)),
                    'f_mod':      _formato_fecha(getattr(obj, 'fecha_modificacion', None)),
                    'activo':     'Sí' if getattr(obj, 'activo', True) else 'No',
                })
        except Exception:
            continue

    # Ordenar por fecha de modificación descendente
    registros.sort(key=lambda r: r['f_mod'], reverse=True)

    # Crear PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm,
    )

    styles = get_estilos()
    elements = []

    # Encabezado estandar con LOGO
    titulo = 'Reporte de Auditoria del Sistema'
    if tabla:
        titulo += f' - {tabla}'
    if usuario:
        titulo += f' - Usuario: {usuario}'
    if solo_activos:
        titulo += ' (solo activos)'

    agregar_encabezado(
        elements, styles,
        titulo,
        f'Total de registros listados: {len(registros)}',
        nombre_reporte='Auditoria del Sistema',
    )

    # Tabla de datos
    datos = [[
        'Tabla', 'ID', 'Descripción',
        'Usuario Creó', 'Fecha Creación',
        'Usuario Modificó', 'Fecha Modificación', 'Activo',
    ]]

    for r in registros[:300]:  # límite para no saturar el PDF
        datos.append([
            r['tabla'], r['id'], r['desc'],
            r['u_crea'], r['f_crea'],
            r['u_mod'],  r['f_mod'], r['activo'],
        ])

    col_widths = [2.5*cm, 2*cm, 5*cm, 3*cm, 3*cm, 3*cm, 3*cm, 1.5*cm]
    tabla_pdf = crear_tabla_pdf(datos, col_widths)
    elements.append(tabla_pdf)

    # Resumen por tabla
    elements.append(Spacer(1, 20))
    elements.append(Paragraph('Resumen por Tabla', styles['Subtitulo']))

    resumen = {}
    for r in registros:
        resumen[r['tabla']] = resumen.get(r['tabla'], 0) + 1

    resumen_datos = [['Tabla', 'Registros Auditados']]
    for t, c in sorted(resumen.items()):
        resumen_datos.append([t, str(c)])

    resumen_pdf = crear_tabla_pdf(resumen_datos, [8*cm, 5*cm])
    elements.append(resumen_pdf)

    doc.build(elements, onFirstPage=agregar_footer, onLaterPages=agregar_footer)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f'reporte_auditoria_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    buffer.close()
    return response