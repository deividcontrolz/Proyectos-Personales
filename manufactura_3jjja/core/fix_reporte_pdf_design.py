# -*- coding: utf-8 -*-
"""
fix_reporte_pdf_design.py
=========================

Cambia SOLO el diseño visual de los reportes PDF:

  * LOGO "MANUFACTURAS 3-JJJ-A" en gris plata (#A8A9AD).
  * Encabezado con:
        - Reporte generado: DD/MM/AAAA
        - Nombre del reporte
  * Footer con la marca de la empresa en gris plata.
  * Se conservan los colores originales (verde #059669, grises).

NO altera vistas, modelos, formularios, autenticacion ni auditoria.

Uso:
    python fix_reporte_pdf_design.py
"""

import sys
import shutil
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).resolve().parent
ARCHIVO_PDF = BASE / 'reportes_pdf.py'
ARCHIVO_AUD = BASE / 'reportes_auditoria_pdf.py'

MARCA_PDF = '# PDF-DESIGN-FIX-APLICADO'
MARCA_AUD = '# PDF-DESIGN-FIX-AUD-APLICADO'


# ==================================================================
# NUEVAS FUNCIONES agregar_encabezado / agregar_footer
# ==================================================================
NUEVAS_FUNCIONES = '''# PDF-DESIGN-FIX-APLICADO
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
'''


# ==================================================================
# Fix 1: reportes_pdf.py  -> reemplazar encabezado y footer
# ==================================================================
def _fix_reportes_pdf():
    print('--- reportes_pdf.py ---')
    if not ARCHIVO_PDF.exists():
        print('[ERROR] No se encontro: ' + str(ARCHIVO_PDF))
        return False

    contenido = ARCHIVO_PDF.read_text(encoding='utf-8')
    if MARCA_PDF in contenido:
        print('[INFO] Ya estaba aplicado. Nada que hacer.')
        return True

    # Respaldo con fecha
    respaldo = ARCHIVO_PDF.with_name(
        'reportes_pdf_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.py'
    )
    shutil.copy2(ARCHIVO_PDF, respaldo)
    print('[OK] Respaldo: ' + respaldo.name)

    # Localizar bloque completo: def agregar_encabezado ... def agregar_footer ... restoreState()
    inicio = contenido.find('def agregar_encabezado(')
    if inicio == -1:
        print('[ERROR] No se encontro "def agregar_encabezado("')
        return False

    # Fin del bloque: proxima seccion "# ====..." despues de agregar_footer
    resto = contenido[inicio:]
    marca_fin = resto.find('\n\n\n# ============================================================')
    if marca_fin == -1:
        print('[ERROR] No se encontro el fin del bloque encabezado/footer.')
        return False

    fin = inicio + marca_fin
    nuevo = contenido[:inicio] + NUEVAS_FUNCIONES + contenido[fin:]
    ARCHIVO_PDF.write_text(nuevo, encoding='utf-8')
    print('[OK] Encabezado y footer actualizados con LOGO en gris plata.')
    return True


# ==================================================================
# Fix 2: reportes_auditoria_pdf.py -> usar agregar_encabezado
# ==================================================================
def _fix_auditoria():
    print('--- reportes_auditoria_pdf.py ---')
    if not ARCHIVO_AUD.exists():
        print('[INFO] No existe, se omite.')
        return True

    contenido = ARCHIVO_AUD.read_text(encoding='utf-8')
    if MARCA_AUD in contenido:
        print('[INFO] Ya estaba aplicado. Nada que hacer.')
        return True

    respaldo = ARCHIVO_AUD.with_name(
        'reportes_auditoria_pdf_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.py'
    )
    shutil.copy2(ARCHIVO_AUD, respaldo)
    print('[OK] Respaldo: ' + respaldo.name)

    # 1. Importar agregar_encabezado
    viejo_import = 'from .reportes_pdf import get_estilos, crear_tabla_pdf, agregar_footer'
    nuevo_import = ('from .reportes_pdf import (get_estilos, crear_tabla_pdf, '
                    'agregar_footer, agregar_encabezado)')
    if viejo_import in contenido:
        contenido = contenido.replace(viejo_import, nuevo_import)
        print('[OK] Import actualizado.')
    else:
        print('[WARN] No se encontro el import esperado (se continua).')

    # 2. Reemplazar el bloque inline del encabezado
    inicio_marca = "    # Encabezado\n    fecha_actual = timezone.now().strftime('%d/%m/%Y %H:%M')"
    inicio = contenido.find(inicio_marca)
    if inicio == -1:
        print('[WARN] No se encontro el bloque de encabezado inline.')
        return True

    fin_marca = '    elements.append(Spacer(1, 15))\n'
    fin = contenido.find(fin_marca, inicio)
    if fin == -1:
        print('[WARN] No se encontro el fin del bloque inline.')
        return True
    fin += len(fin_marca)

    nuevo_bloque = (
        "    # Encabezado estandar con LOGO\n"
        "    titulo = 'Reporte de Auditoria del Sistema'\n"
        "    if tabla:\n"
        "        titulo += f' - {tabla}'\n"
        "    if usuario:\n"
        "        titulo += f' - Usuario: {usuario}'\n"
        "    if solo_activos:\n"
        "        titulo += ' (solo activos)'\n"
        "\n"
        "    agregar_encabezado(\n"
        "        elements, styles,\n"
        "        titulo,\n"
        "        f'Total de registros listados: {len(registros)}',\n"
        "        nombre_reporte='Auditoria del Sistema',\n"
        "    )\n"
    )
    contenido = contenido[:inicio] + nuevo_bloque + contenido[fin:]

    # 3. Marca
    contenido = contenido.replace(
        'import io\n',
        'import io\n' + MARCA_AUD + '\n',
        1,
    )

    ARCHIVO_AUD.write_text(contenido, encoding='utf-8')
    print('[OK] Encabezado de auditoria actualizado.')
    return True


# ==================================================================
def main():
    print('=' * 64)
    print(' Fix de diseño de reportes PDF')
    print('   * LOGO "MANUFACTURAS 3-JJJ-A" en gris plata')
    print('   * Encabezado: reporte generado + nombre del reporte')
    print('   * Footer con la marca de la empresa')
    print('   * Colores originales conservados')
    print('=' * 64)

    ok1 = _fix_reportes_pdf()
    print()
    ok2 = _fix_auditoria()

    print()
    if ok1 and ok2:
        print('LISTO. Reinicie Django y regenere los PDFs para ver el cambio.')
        return 0
    print('Hubo errores. Revise los mensajes anteriores.')
    return 1


if __name__ == '__main__':
    sys.exit(main())