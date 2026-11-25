# -*- coding: utf-8 -*-
"""
Tests del modulo de incidentes: reportar_incidente, historial_incidentes
y la API de actualizacion.

    python manage.py test core.tests.test_incidentes
"""
import shutil
import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse, NoReverseMatch
from django.contrib.messages import get_messages
from django.utils import timezone

from core import views
from core.models import (
    Usuario, Etapa, Incidente,
    ROL_OPERARIO, ROL_GERENTE,
    TIPO_INCIDENTE_CHOICES, SEVERIDAD_CHOICES,
)

TIPO = TIPO_INCIDENTE_CHOICES[0][0]
SEVERIDAD = SEVERIDAD_CHOICES[0][0]


def mensajes(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


def crear_usuario(pk='op1', rol=ROL_OPERARIO, staff=False):
    u = Usuario(id_usuario=pk, nombre_completo='Usuario ' + pk, rol=rol,
                is_staff=staff)
    u.set_password('clave1234')
    u.save()
    return u


def login_sesion(client, pk):
    s = client.session
    s[views.SESSION_KEY] = pk
    s.save()


def crear_incidente(reporta, etapa=None, estado='PENDIENTE'):
    return Incidente.objects.create(
        id_usuario_reporta=reporta,
        id_etapa=etapa,
        tipo_incidente=TIPO,
        severidad=SEVERIDAD,
        descripcion='Descripcion de prueba del incidente',
        estado=estado,
        fecha_reporte=timezone.now(),
    )


class BaseIncidentes(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def setUp(self):
        super().setUp()
        self._ovr = override_settings(MEDIA_ROOT=self.tmpdir)
        self._ovr.enable()
        self.addCleanup(self._ovr.disable)
        self.etapa = Etapa.objects.create(
            id_etapa='ETP-1', nombre_etapa='Corte', secuencia=1)


class ReportarIncidenteTests(BaseIncidentes):
    def setUp(self):
        super().setUp()
        self.operario = crear_usuario('op1')

    def _data(self, **over):
        base = {
            'tipo_incidente': TIPO,
            'severidad': SEVERIDAD,
            'id_etapa': str(self.etapa.id_etapa),
            'descripcion': 'La maquina MQ-1 vibra anormalmente.',
        }
        base.update(over)
        return base

    def test_get_muestra_formulario(self):
        login_sesion(self.client, 'op1')
        r = self.client.get(reverse('core:reportar_incidente'))
        self.assertEqual(r.status_code, 200)

    def test_sin_sesion_redirige_a_login(self):
        r = self.client.get(reverse('core:reportar_incidente'))
        self.assertRedirects(r, reverse('core:login'))

    def test_post_valido_crea_incidente_pendiente(self):
        login_sesion(self.client, 'op1')
        r = self.client.post(reverse('core:reportar_incidente'), self._data())
        self.assertEqual(r.status_code, 302)
        inc = Incidente.objects.get()
        self.assertEqual(inc.estado, 'PENDIENTE')
        self.assertEqual(inc.id_usuario_reporta, self.operario)
        self.assertEqual(inc.id_etapa, self.etapa)

    def test_post_invalido_no_crea_incidente(self):
        login_sesion(self.client, 'op1')
        r = self.client.post(reverse('core:reportar_incidente'),
                             self._data(descripcion=''))
        self.assertEqual(r.status_code, 200)  # re-renderiza con errores
        self.assertEqual(Incidente.objects.count(), 0)

    def test_descripcion_muy_corta_rechazada(self):
        login_sesion(self.client, 'op1')
        self.client.post(reverse('core:reportar_incidente'),
                         self._data(descripcion='corto'))
        self.assertEqual(Incidente.objects.count(), 0)


class HistorialIncidentesTests(BaseIncidentes):
    def setUp(self):
        super().setUp()
        self.gerente = crear_usuario('g1', rol=ROL_GERENTE)
        self.operario = crear_usuario('op1')
        login_sesion(self.client, 'g1')

    def test_get_muestra_historial(self):
        r = self.client.get(reverse('core:historial_incidentes'))
        self.assertEqual(r.status_code, 200)

    def test_operario_recibe_403(self):
        login_sesion(self.client, 'op1')
        r = self.client.get(reverse('core:historial_incidentes'))
        self.assertEqual(r.status_code, 403)

    def test_sin_sesion_redirige_a_login(self):
        self.client.session.flush()
        r = self.client.get(reverse('core:historial_incidentes'))
        self.assertRedirects(r, reverse('core:login'))

    def test_stats_conteo_por_estado(self):
        crear_incidente(self.operario, self.etapa, 'PENDIENTE')
        crear_incidente(self.operario, self.etapa, 'PENDIENTE')
        crear_incidente(self.operario, self.etapa, 'RESUELTO')
        r = self.client.get(reverse('core:historial_incidentes'))
        stats = r.context['stats']
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['pendientes'], 2)
        self.assertEqual(stats['resueltos'], 1)

    def test_filtro_por_estado(self):
        crear_incidente(self.operario, self.etapa, 'PENDIENTE')
        crear_incidente(self.operario, self.etapa, 'RESUELTO')
        r = self.client.get(reverse('core:historial_incidentes'),
                            {'estado': 'RESUELTO'})
        incidentes = r.context['incidentes']
        self.assertEqual(incidentes.count(), 1)
        self.assertEqual(incidentes[0].estado, 'RESUELTO')
        self.assertEqual(r.context['stats']['total'], 1)

    def test_filtro_por_etapa(self):
        otra = Etapa.objects.create(id_etapa='ETP-2', nombre_etapa='Suela',
                                  secuencia=2)
        crear_incidente(self.operario, self.etapa)
        crear_incidente(self.operario, otra)
        r = self.client.get(reverse('core:historial_incidentes'),
                            {'etapa': 'ETP-2'})
        self.assertEqual(r.context['incidentes'].count(), 1)

    def test_post_actualizar_a_resuelto_fija_fecha_resolucion(self):
        inc = crear_incidente(self.operario, self.etapa, 'EN_PROCESO')
        r = self.client.post(reverse('core:historial_incidentes'), {
            'incidente_id': str(inc.pk),
            'estado': 'RESUELTO',
        })
        self.assertEqual(r.status_code, 302)
        inc.refresh_from_db()
        self.assertEqual(inc.estado, 'RESUELTO')
        self.assertIsNotNone(inc.fecha_resolucion)


class ApiActualizarIncidenteTests(BaseIncidentes):
    def setUp(self):
        super().setUp()
        crear_usuario('g1', rol=ROL_GERENTE)
        self.operario = crear_usuario('op1')
        self.inc = crear_incidente(self.operario, self.etapa)
        try:
            self.url = reverse('core:api_actualizar_incidente',
                               args=[self.inc.pk])
        except NoReverseMatch:
            self.url = None

    def test_post_valido_actualiza_estado(self):
        if not self.url:
            self.skipTest('Ajusta el nombre de la URL de la API en urls.py')
        login_sesion(self.client, 'g1')
        r = self.client.post(self.url, {'estado': 'EN_PROCESO'})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data['success'])
        self.inc.refresh_from_db()
        self.assertEqual(self.inc.estado, 'EN_PROCESO')

    def test_estado_invalido_devuelve_400(self):
        if not self.url:
            self.skipTest('Ajusta el nombre de la URL de la API en urls.py')
        login_sesion(self.client, 'g1')
        r = self.client.post(self.url, {'estado': 'INVENTADO'})
        self.assertEqual(r.status_code, 400)

    def test_get_devuelve_405(self):
        if not self.url:
            self.skipTest('Ajusta el nombre de la URL de la API en urls.py')
        login_sesion(self.client, 'g1')
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_sin_sesion_redirige_a_login(self):
        if not self.url:
            self.skipTest('Ajusta el nombre de la URL de la API en urls.py')
        r = self.client.post(self.url, {'estado': 'EN_PROCESO'})
        self.assertEqual(r.status_code, 302)
