# -*- coding: utf-8 -*-
"""
fix_reporte_pdf.py
==================

Corrige el problema de texto superpuesto en los reportes PDF.

El problema viene de que las celdas de las tablas contienen strings
planos que ReportLab NO envuelve; el texto se sale de la celda y se
superpone con las celdas vecinas.

Este script:
  1. Hace un respaldo con fecha de reportes_pdf.py.
  2. Reemplaza la funcion crear_tabla_pdf para que envuelva cada celda
     en un Paragraph (que hace salto de linea automatico).
  3. Ajusta los anchos de columna de los reportes de Usuarios y Etapas
     para que quepan en una hoja A4 vertical.

NO modifica ninguna otra funcionalidad del sistema (vistas, modelos,
formularios, autenticacion, auditoria, etc. quedan intactos).

Uso:
    python fix_reporte_pdf.py
"""

import re
import sys
import shutil
from datetime import datetime
from pathlib import Path


ARCHIVO = Path(__file__).resolve().parent / 'reportes_pdf.py'
MARCA = '# PDF-FIX-APLICADO'


# ------------------------------------------------------------------
# Nueva version de crear_tabla_pdf: envuelve cada celda en Paragraph
# ------------------------------------------------------------------
NUEVA_FUNCION = '''# PDF-FIX-APLICADO
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
'''


# ------------------------------------------------------------------
# Anchos corregidos para los reportes que se salian de la hoja A4
# (sumaban 20 cm y 18 cm cuando solo hay 17 cm utiles)
# ------------------------------------------------------------------
CORRECCIONES_ANCHOS = [
    (
        'col_widths = [3.5*cm, 5*cm, 3.5*cm, 3*cm, 2.5*cm, 2.5*cm]',
        'col_widths = [2.8*cm, 4.5*cm, 3*cm, 3*cm, 2*cm, 1.7*cm]',
    ),
    (
        'col_widths = [2.5*cm, 3.5*cm, 4*cm, 3*cm, 2.5*cm, 2.5*cm]',
        'col_widths = [2*cm, 3*cm, 4*cm, 3*cm, 2.5*cm, 2.5*cm]',
    ),
]


def _reemplazar_funcion(contenido):
    """Reemplaza la funcion crear_tabla_pdf completa."""
    inicio = contenido.find('def crear_tabla_pdf(')
    if inicio == -1:
        return None, 'No se encontro la funcion crear_tabla_pdf.'

    resto = contenido[inicio:]
    # Fin: proximo bloque de comentario de seccion o proximo def
    m = re.search(r'\n\n# ={5,}', resto)
    if m:
        fin = inicio + m.start()
    else:
        m = re.search(r'\n\ndef ', resto)
        fin = inicio + m.start() if m else len(contenido)

    nuevo = contenido[:inicio] + NUEVA_FUNCION + contenido[fin:]
    return nuevo, None


def main():
    print('=' * 64)
    print(' FIX Reportes PDF: texto superpuesto en las celdas')
    print('=' * 64)

    if not ARCHIVO.exists():
        print('[ERROR] No se encontro el archivo:')
        print('        ' + str(ARCHIVO))
        print('        Coloque este script junto a reportes_pdf.py')
        return 1

    contenido = ARCHIVO.read_text(encoding='utf-8')

    if MARCA in contenido:
        print('[INFO] El fix ya estaba aplicado anteriormente.')
        print('       Nada que hacer.')
        return 0

    # 1) Respaldo con fecha
    respaldo = ARCHIVO.with_name(
        'reportes_pdf_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.py'
    )
    shutil.copy2(ARCHIVO, respaldo)
    print('[OK] Respaldo creado: ' + respaldo.name)

    # 2) Reemplazar crear_tabla_pdf
    nuevo, err = _reemplazar_funcion(contenido)
    if err:
        print('[ERROR] ' + err)
        return 1
    print('[OK] Funcion crear_tabla_pdf reemplazada (celdas con Paragraph).')

    # 3) Corregir anchos que se salian de la hoja
    cambios = 0
    for viejo, nuevo_ancho in CORRECCIONES_ANCHOS:
        if viejo in nuevo:
            nuevo = nuevo.replace(viejo, nuevo_ancho)
            cambios += 1
    print('[OK] Anchos de columna corregidos: ' + str(cambios))

    # 4) Guardar
    ARCHIVO.write_text(nuevo, encoding='utf-8')
    print()
    print('LISTO. Reinicie el servidor Django y regenere los PDFs.')
    print('Si algo sale mal, restaure el respaldo *.py.bak_* que se creo.')
    return 0


if __name__ == '__main__':
    sys.exit(main())