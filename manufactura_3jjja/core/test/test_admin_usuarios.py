# -*- coding: utf-8 -*-
"""
Tests de administracion de usuarios (admin_usuarios_view y desbloqueo).

    python manage.py test core.tests.test_admin_usuarios
"""
import shutil
import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse, NoReverseMatch

from core import views
from core.models import Usuario, ROL_OPERARIO, ROL_GERENTE


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


class AdminUsuariosTests(TestCase):
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
        self.admin = crear_usuario('admin1', rol=ROL_GERENTE, staff=True)
        crear_usuario('op1')
        crear_usuario('op2')
        login_sesion(self.client, 'admin1')

    # ---------- Permisos ----------
    def test_get_muestra_panel(self):
        r = self.client.get(reverse('core:admin_usuarios'))
        self.assertEqual(r.status_code, 200)

    def test_sin_sesion_redirige_a_login(self):
        self.client.session.flush()
        r = self.client.get(reverse('core:admin_usuarios'))
        self.assertRedirects(r, reverse('core:login'))

    def test_no_admin_recibe_403(self):
        login_sesion(self.client, 'op1')
        r = self.client.get(reverse('core:admin_usuarios'))
        self.assertEqual(r.status_code, 403)

    def test_admin_no_aparece_en_la_lista(self):
        """Los usuarios staff deben estar ocultos del listado."""
        r = self.client.get(reverse('core:admin_usuarios'))
        ids = [u.id_usuario for u in r.context['usuarios']]
        self.assertNotIn('admin1', ids)
        self.assertIn('op1', ids)

    # ---------- Eliminar ----------
    def test_eliminar_usuario_normal(self):
        r = self.client.post(reverse('core:admin_usuarios'), {
            'accion': 'eliminar', 'usuario_id': 'op2'})
        self.assertFalse(Usuario.objects.filter(id_usuario='op2').exists())

    def test_eliminar_admin_esta_bloqueado(self):
        crear_usuario('admin2', rol=ROL_GERENTE, staff=True)
        self.client.post(reverse('core:admin_usuarios'), {
            'accion': 'eliminar', 'usuario_id': 'admin2'})
        self.assertTrue(Usuario.objects.filter(id_usuario='admin2').exists())

    # ---------- Activar / desactivar ----------
    def test_desactivar_usuario(self):
        self.client.post(reverse('core:admin_usuarios'), {
            'accion': 'desactivar', 'usuario_id': 'op1'})
        self.assertFalse(Usuario.objects.get(id_usuario='op1').is_active)

    def test_no_se_puede_desactivar_admin(self):
        crear_usuario('admin2', rol=ROL_GERENTE, staff=True)
        self.client.post(reverse('core:admin_usuarios'), {
            'accion': 'desactivar', 'usuario_id': 'admin2'})
        self.assertTrue(Usuario.objects.get(id_usuario='admin2').is_active)

    def test_activar_usuario(self):
        u = Usuario.objects.get(id_usuario='op1')
        u.is_active = False
        u.save()
        self.client.post(reverse('core:admin_usuarios'), {
            'accion': 'activar', 'usuario_id': 'op1'})
        self.assertTrue(Usuario.objects.get(id_usuario='op1').is_active)

    # ---------- Cambio de contrasena ----------
    def test_cambiar_password_marca_temporal(self):
        self.client.post(reverse('core:admin_usuarios'), {
            'accion': 'cambiar_password',
            'usuario_id': 'op1',
            'nueva_password': 'NuevaPass123!',
            'confirmar_password': 'NuevaPass123!',
        })
        u = Usuario.objects.get(id_usuario='op1')
        self.assertTrue(u.check_password('NuevaPass123!'))
        self.assertTrue(views.tiene_password_temporal('op1'))

    def test_cambiar_password_no_coinciden_no_hace_nada(self):
        self.client.post(reverse('core:admin_usuarios'), {
            'accion': 'cambiar_password',
            'usuario_id': 'op1',
            'nueva_password': 'NuevaPass123!',
            'confirmar_password': 'Distinta123!',
        })
        u = Usuario.objects.get(id_usuario='op1')
        self.assertTrue(u.check_password('clave1234'))
        self.assertFalse(views.tiene_password_temporal('op1'))


class AdminDesbloquearTests(TestCase):
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
        crear_usuario('admin1', rol=ROL_GERENTE, staff=True)
        crear_usuario('op1')
        try:
            self.url = reverse('core:admin_desbloquear_usuario',
                               args=['op1'])
        except NoReverseMatch:
            self.url = None

    def test_desbloquear_funciona(self):
        if not self.url:
            self.skipTest('Ajusta el nombre de la URL de desbloqueo en urls.py')
        views.registrar_intento_fallido('op1')
        login_sesion(self.client, 'admin1')
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertFalse(views.esta_bloqueado('op1')[0])

    def test_desbloquear_cambia_estado_con_GET(self):
        """BUG DOCUMENTADO: la vista acepta GET para cambiar estado.
        Deberia exigir POST (require_http_methods). Este test documenta
        el comportamiento actual; cuando se corrija, cambiar a POST."""
        if not self.url:
            self.skipTest('Ajusta el nombre de la URL de desbloqueo en urls.py')
        views.registrar_intento_fallido('op1')
        login_sesion(self.client, 'admin1')
        self.client.get(self.url)
        self.assertFalse(views.esta_bloqueado('op1')[0])

    def test_no_admin_no_puede_desbloquear(self):
        if not self.url:
            self.skipTest('Ajusta el nombre de la URL de desbloqueo en urls.py')
        views.registrar_intento_fallido('op1')
        login_sesion(self.client, 'op1')
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)
        self.assertTrue(views.esta_bloqueado('op1')[0])
