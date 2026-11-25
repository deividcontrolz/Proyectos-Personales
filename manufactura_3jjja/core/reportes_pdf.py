# -*- coding: utf-8 -*-
"""
reportes_pdf.py - Generacion de Reportes PDF
Manufacturera de Calzado 3-JJJ-A

Genera reportes PDF de:
  - Usuarios registrados
  - Modelos de calzado
  - Lotes de produccion
  - Incidentes
  - Materiales
  - Etapas de produccion

Django 4.2 compatible - Windows 7
"""

import io
from datetime import datetime
from django.http import HttpResponse
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    Image, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable

from .models import (
    Usuario, Modelo, Material, LoteProduccion, Etapa,
    RegistroEtapa, Incidente, Maquinaria, MaterialModelo,
    ESTADO_INCIDENTE_CHOICES,   # ← AÑADIR
    SEVERIDAD_CHOICES,          # ← recomendado
    TIPO_INCIDENTE_CHOICES,     # ← recomendado
    ROLES_CHOICES,              # ← usado en reporte_usuarios
)

# ============================================================
# ESTILOS COMUNES
# ============================================================
def get_estilos():
    """Devuelve los estilos personalizados para los PDFs."""
    styles = getSampleStyleSheet()

    # Estilo para titulo principal
    styles.add(ParagraphStyle(
        name='TituloPrincipal',
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=colors.HexColor('#059669'),
        alignment=TA_CENTER,
        spaceAfter=20,
        spaceBefore=10,
    ))

    # Estilo para subtitulo
    styles.add(ParagraphStyle(
        name='Subtitulo',
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=colors.HexColor('#334155'),
        alignment=TA_LEFT,
        spaceAfter=12,
        spaceBefore=12,
    ))

    # Estilo para fecha/encabezado
    styles.add(ParagraphStyle(
        name='FechaHeader',
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#64748b'),
        alignment=TA_RIGHT,
    ))

    # Estilo para footer
    styles.add(ParagraphStyle(
        name='Footer',
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#94a3b8'),
        alignment=TA_CENTER,
    ))

    return styles


# ============================================================
# FUNCION AUXILIAR: CREAR TABLA CON ESTILO
# ============================================================
# PDF-FIX-APLICADO
def crear_tabla_pdf(datos, col_widths=None, estilo_personalizado=None):
    """
    Crea una tabla PDF con estilo profesional y texto auto-ajustado.

    Cada celda se envuelve en un Paragraph para que el texto haga
    salto de linea automatico dentro de la celda y nunca se superponga
    con las celdas vecinas ni se salga del cuadro.
    """
    from xml.sax.saxutils import escape as _xml_escape

    if not datos:
        datos = [['Sin datos']]

    estilo_header = ParagraphStyle(
        name='CeldaHeaderPDF',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.whitesmoke,
        wordWrap='CJK',
        splitLongWords=1,
        spaceBefore=0,
        spaceAfter=0,
    )

    estilo_celda = ParagraphStyle(
        name='CeldaBodyPDF',
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#1e293b'),
        wordWrap='CJK',
        splitLongWords=1,
        spaceBefore=0,
        spaceAfter=0,
    )

    # Envolver cada celda en un Paragraph
    datos_parrafo = []
    for i, fila in enumerate(datos):
        fila_nueva = []
        for celda in fila:
            texto = '' if celda is None else str(celda)
            texto = _xml_escape(texto)
            estilo = estilo_header if i == 0 else estilo_celda
            fila_nueva.append(Paragraph(texto, estilo))
        datos_parrafo.append(fila_nueva)

    tabla = Table(datos_parrafo, colWidths=col_widths, repeatRows=1)

    estilo_base = [
        # ---- Encabezado ----
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
        ('VALIGN',     (0, 0), (-1, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 7),

        # ---- Cuerpo ----
        ('VALIGN',     (0, 1), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),

        # ---- Padding lateral ----
        ('LEFTPADDING',  (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),

        # ---- Bordes ----
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cbd5e1')),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, colors.HexColor('#047857')),

        # ---- Fondo base ----
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]

    # Filas alternas
    for i in range(1, len(datos_parrafo)):
        if i % 2 == 0:
            estilo_base.append(
                ('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f8fafc'))
            )

    if estilo_personalizado:
        estilo_base.extend(estilo_personalizado)

    tabla.setStyle(TableStyle(estilo_base))
    return tabla


# ============================================================
# FUNCION AUXILIAR: ENCABEZADO Y PIE DE PAGINA
# ============================================================
# PDF-DESIGN-FIX-APLICADO
# ============================================================
# ENCABEZADO Y PIE DE PAGINA (diseño con LOGO)
# ============================================================
GRIS_PLATA = '#A8A9AD'
GRIS_PLATA_CLARO = '#C8C9CD'


def agregar_encabezado(elements, styles, titulo, subtitulo=None, nombre_reporte=None):
    """
    Encabezado estandar con LOGO, fecha de generacion y nombre del reporte.

    Args:
        titulo:         titulo visible del reporte (cuerpo).
        subtitulo:      linea adicional bajo el titulo.
        nombre_reporte: nombre corto para la cabecera. Si es None se usa 'titulo'.
    """
    fecha_actual = timezone.now().strftime('%d/%m/%Y')
    nombre_rep = nombre_reporte or titulo

    # ---- Estilos del encabezado ----
    estilo_logo = ParagraphStyle(
        name='LogoMarca',
        fontName='Helvetica-Bold',
        fontSize=22, leading=26,
        textColor=colors.HexColor(GRIS_PLATA),
        alignment=TA_CENTER,
    )
    estilo_logo_sub = ParagraphStyle(
        name='LogoSub',
        fontName='Helvetica',
        fontSize=9, leading=11,
        textColor=colors.HexColor(GRIS_PLATA_CLARO),
        alignment=TA_CENTER,
    )
    estilo_info_izq = ParagraphStyle(
        name='InfoEncabezado',
        fontName='Helvetica',
        fontSize=9, leading=12,
        textColor=colors.HexColor('#475569'),
        alignment=TA_LEFT,
    )
    estilo_info_der = ParagraphStyle(
        name='InfoEncabezadoDer',
        fontName='Helvetica',
        fontSize=9, leading=12,
        textColor=colors.HexColor('#475569'),
        alignment=TA_RIGHT,
    )

    # ---- LOGO (gris plata) ----
    elements.append(Paragraph('MANUFACTURAS 3-JJJ-A', estilo_logo))
    elements.append(Paragraph('Sistema de Gestion de Produccion', estilo_logo_sub))
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width='100%', thickness=2,
                               color=colors.HexColor(GRIS_PLATA)))
    elements.append(Spacer(1, 8))

    # ---- Datos de generacion ----
    info_izq = Paragraph(
        f'<b>Reporte generado:</b> {fecha_actual}', estilo_info_izq
    )
    info_der = Paragraph(
        f'<b>Reporte:</b> {nombre_rep}', estilo_info_der
    )
    info_tabla = Table([[info_izq, info_der]], colWidths=['50%', '50%'])
    info_tabla.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW',     (0, 0), (-1, -1), 0.8,
         colors.HexColor('#059669')),
    ]))
    elements.append(info_tabla)
    elements.append(Spacer(1, 12))

    # ---- Titulo del reporte ----
    elements.append(Paragraph(titulo, styles['TituloPrincipal']))
    if subtitulo:
        elements.append(Paragraph(subtitulo, styles['Subtitulo']))

    elements.append(HRFlowable(width='100%', thickness=0.5,
                               color=colors.HexColor('#cbd5e1')))
    elements.append(Spacer(1, 12))


def agregar_footer(canvas, doc):
    """Pie de pagina con marca en gris plata y numeracion."""
    canvas.saveState()

    # Linea superior del footer
    canvas.setStrokeColor(colors.HexColor('#cbd5e1'))
    canvas.setLineWidth(0.5)
    canvas.line(2*cm, 1.9*cm, A4[0]-2*cm, 1.9*cm)

    # Izquierda: marca en gris plata
    canvas.setFont('Helvetica-Bold', 8)
    canvas.setFillColor(colors.HexColor(GRIS_PLATA))
    canvas.drawString(2*cm, 1.4*cm, 'MANUFACTURAS 3-JJJ-A')

    # Centro: sistema
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#94a3b8'))
    canvas.drawCentredString(A4[0]/2, 1.4*cm, 'Sistema de Gestion de Produccion')

    # Derecha: pagina
    canvas.drawRightString(A4[0]-2*cm, 1.4*cm, f'Pagina {doc.page}')

    canvas.restoreState()



# ============================================================
# 1. REPORTE: USUARIOS REGISTRADOS
# ============================================================
def generar_reporte_usuarios(request, rol_filtro=None, estado_filtro=None):
    """
    Genera un PDF con el listado de usuarios registrados.

    Args:
        rol_filtro: Filtrar por rol (opcional)
        estado_filtro: 'activo', 'inactivo' o None
    """
    # Obtener datos
    usuarios = Usuario.objects.all().order_by('-fecha_registro')

    if rol_filtro:
        usuarios = usuarios.filter(rol=rol_filtro)
    if estado_filtro == 'activo':
        usuarios = usuarios.filter(is_active=True)
    elif estado_filtro == 'inactivo':
        usuarios = usuarios.filter(is_active=False)

    # Crear buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm
    )

    elements = []
    styles = get_estilos()

    # Encabezado
    titulo = 'Reporte de Usuarios Registrados'
    if rol_filtro:
        titulo += f' - Rol: {rol_filtro}'
    if estado_filtro:
        titulo += f' ({estado_filtro.title()})'

    agregar_encabezado(elements, styles, titulo, f'Total de usuarios: {usuarios.count()}')

    # Preparar datos de la tabla
    datos = [['Usuario', 'Nombre Completo', 'Rol', 'Etapa', 'Estado', 'Fecha Registro']]

    for u in usuarios:
        etapa = u.etapa_asignada.nombre_etapa if u.etapa_asignada else 'N/A'
        estado = 'Activo' if u.is_active else 'Inactivo'
        fecha = u.fecha_registro.strftime('%d/%m/%Y')

        datos.append([
            u.id_usuario,
            u.nombre_completo,
            u.get_rol_display(),
            etapa,
            estado,
            fecha
        ])

    # Crear tabla
    col_widths = [2.8*cm, 4.5*cm, 3*cm, 3*cm, 2*cm, 1.7*cm]
    tabla = crear_tabla_pdf(datos, col_widths)
    elements.append(tabla)

    # Estadisticas resumen
    elements.append(Spacer(1, 20))
    elements.append(Paragraph('Resumen por Rol', styles['Subtitulo']))

    resumen_datos = [['Rol', 'Cantidad']]
    from .models import ROLES_CHOICES
    for rol_codigo, rol_nombre in ROLES_CHOICES:
        cantidad = usuarios.filter(rol=rol_codigo).count()
        resumen_datos.append([rol_nombre, str(cantidad)])

    resumen_tabla = crear_tabla_pdf(resumen_datos, [8*cm, 4*cm])
    elements.append(resumen_tabla)

    # Construir PDF
    doc.build(elements, onFirstPage=agregar_footer, onLaterPages=agregar_footer)

    # Preparar respuesta
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_usuarios_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
    buffer.close()

    return response


# ============================================================
# 2. REPORTE: MODELOS DE CALZADO
# ============================================================
def generar_reporte_modelos(request):
    """Genera un PDF con el catalogo de modelos de calzado."""
    modelos = Modelo.objects.all().order_by('-fecha_registro')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm
    )

    elements = []
    styles = get_estilos()

    agregar_encabezado(elements, styles, 'Catalogo de Modelos de Calzado', f'Total de modelos: {modelos.count()}')

    datos = [['ID Modelo', 'Nombre', 'Materiales', 'Fecha Registro']]

    for m in modelos:
        # Obtener materiales del modelo
        materiales = MaterialModelo.objects.filter(id_modelo=m).select_related('id_material')
        mats_texto = ', '.join([f'{mm.id_material.nombre_material} ({mm.cantidad_por_par})' for mm in materiales]) or 'Sin materiales'

        datos.append([
            m.id_modelo,
            m.nombre,
            mats_texto[:60] + '...' if len(mats_texto) > 60 else mats_texto,
            m.fecha_registro.strftime('%d/%m/%Y')
        ])

    col_widths = [3.5*cm, 4*cm, 7*cm, 2.5*cm]
    tabla = crear_tabla_pdf(datos, col_widths)
    elements.append(tabla)

    doc.build(elements, onFirstPage=agregar_footer, onLaterPages=agregar_footer)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_modelos_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
    buffer.close()

    return response


# ============================================================
# 3. REPORTE: LOTES DE PRODUCCION
# ============================================================
def generar_reporte_lotes(request, estado=None):
    """Genera un PDF con los lotes de produccion."""
    lotes = LoteProduccion.objects.select_related('id_modelo').all().order_by('-fecha_creacion')

    if estado:
        lotes = lotes.filter(estado_actual=estado)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm
    )

    elements = []
    styles = get_estilos()

    agregar_encabezado(elements, styles, 'Reporte de Lotes de Produccion', f'Total de lotes: {lotes.count()}')

    datos = [['ID Lote', 'Modelo', 'Cantidad Solicitada', 'Estado', 'Fecha Creacion']]

    for l in lotes:
        datos.append([
            l.id_lote,
            l.id_modelo.nombre,
            str(l.cant_solicitada),
            l.estado_actual,
            l.fecha_creacion.strftime('%d/%m/%Y %H:%M')
        ])

    col_widths = [4*cm, 5*cm, 4*cm, 3*cm, 4*cm]
    tabla = crear_tabla_pdf(datos, col_widths)
    elements.append(tabla)

    doc.build(elements, onFirstPage=agregar_footer, onLaterPages=agregar_footer)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_lotes_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
    buffer.close()

    return response


# ============================================================
# 4. REPORTE: INCIDENTES
# ============================================================
def generar_reporte_incidentes(request, estado=None, fecha_desde=None, fecha_hasta=None):
    """Genera un PDF con el historial de incidentes."""
    incidentes = Incidente.objects.select_related('id_usuario_reporta', 'id_etapa').all().order_by('-fecha_reporte')

    if estado:
        incidentes = incidentes.filter(estado=estado)
    if fecha_desde:
        incidentes = incidentes.filter(fecha_reporte__date__gte=fecha_desde)
    if fecha_hasta:
        incidentes = incidentes.filter(fecha_reporte__date__lte=fecha_hasta)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm
    )

    elements = []
    styles = get_estilos()

    agregar_encabezado(elements, styles, 'Reporte de Incidentes', f'Total de incidentes: {incidentes.count()}')

    datos = [['ID', 'Tipo', 'Severidad', 'Estado', 'Etapa', 'Reportado por', 'Fecha']]

    for inc in incidentes:
        datos.append([
            f'#{inc.id_incidente}',
            inc.get_tipo_incidente_display(),
            inc.get_severidad_display(),
            inc.get_estado_display(),
            inc.id_etapa.nombre_etapa if inc.id_etapa else 'N/A',
            inc.id_usuario_reporta.nombre_completo,
            inc.fecha_reporte.strftime('%d/%m/%Y %H:%M')
        ])

    col_widths = [2*cm, 4*cm, 2.5*cm, 2.5*cm, 3*cm, 4*cm, 3*cm]
    tabla = crear_tabla_pdf(datos, col_widths)
    elements.append(tabla)

    # Estadisticas
    elements.append(Spacer(1, 20))
    elements.append(Paragraph('Resumen por Estado', styles['Subtitulo']))

    estados_datos = [['Estado', 'Cantidad']]
    for estado_codigo, estado_nombre in ESTADO_INCIDENTE_CHOICES:
        cantidad = incidentes.filter(estado=estado_codigo).count()
        estados_datos.append([estado_nombre, str(cantidad)])

    estados_tabla = crear_tabla_pdf(estados_datos, [6*cm, 3*cm])
    elements.append(estados_tabla)

    doc.build(elements, onFirstPage=agregar_footer, onLaterPages=agregar_footer)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_incidentes_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
    buffer.close()

    return response


# ============================================================
# 5. REPORTE: MATERIALES
# ============================================================
def generar_reporte_materiales(request):
    """Genera un PDF con el inventario de materiales."""
    materiales = Material.objects.all().order_by('nombre_material')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm
    )

    elements = []
    styles = get_estilos()

    agregar_encabezado(elements, styles, 'Reporte de Materiales', f'Total de materiales: {materiales.count()}')

    datos = [['ID', 'Nombre Material', 'Unidad de Medida', 'Usado en Modelos']]

    for m in materiales:
        # Contar en cuantos modelos se usa
        usado_en = MaterialModelo.objects.filter(id_material=m).count()

        datos.append([
            str(m.id_material),
            m.nombre_material,
            m.unidad_medida,
            str(usado_en)
        ])

    col_widths = [2.5*cm, 6*cm, 3.5*cm, 3.5*cm]
    tabla = crear_tabla_pdf(datos, col_widths)
    elements.append(tabla)

    doc.build(elements, onFirstPage=agregar_footer, onLaterPages=agregar_footer)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_materiales_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
    buffer.close()

    return response


# ============================================================
# 6. REPORTE: ETAPAS DE PRODUCCION
# ============================================================
def generar_reporte_etapas(request):
    """Genera un PDF con las etapas de produccion y sus estadisticas."""
    etapas = Etapa.objects.all().order_by('secuencia')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm
    )

    elements = []
    styles = get_estilos()

    agregar_encabezado(elements, styles, 'Reporte de Etapas de Produccion', f'Total de etapas: {etapas.count()}')

    datos = [['Secuencia', 'ID Etapa', 'Nombre', 'Operarios Asignados', 'Maquinas', 'Registros']]

    for e in etapas:
        operarios = Usuario.objects.filter(etapa_asignada=e).count()
        maquinas = Maquinaria.objects.filter(id_etapa=e).count()
        registros = RegistroEtapa.objects.filter(id_etapa=e).count()

        datos.append([
            str(e.secuencia),
            e.id_etapa,
            e.nombre_etapa,
            str(operarios),
            str(maquinas),
            str(registros)
        ])

    col_widths = [2*cm, 3*cm, 4*cm, 3*cm, 2.5*cm, 2.5*cm]
    tabla = crear_tabla_pdf(datos, col_widths)
    elements.append(tabla)

    doc.build(elements, onFirstPage=agregar_footer, onLaterPages=agregar_footer)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_etapas_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
    buffer.close()

    return response
