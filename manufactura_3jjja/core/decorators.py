from functools import wraps
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Usuario, ROL_OPERARIO, ROL_GERENTE, ROL_SUBGERENTE, ROL_DIRECTOR_PRODUCCION, ROL_DIRECTOR_DESPACHO


def login_requerido(view_func):
    """
    Decorador que verifica que el usuario tenga una sesión activa.
    Si no está autenticado, redirige al login.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            messages.error(request, 'Debe iniciar sesión para acceder a esta página.')
            return redirect('control_produccion:login')

        try:
            request.usuario = Usuario.objects.get(id_usuario=usuario_id)
        except Usuario.DoesNotExist:
            request.session.flush()
            messages.error(request, 'Sesión inválida. Por favor inicie sesión nuevamente.')
            return redirect('control_produccion:login')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


def rol_requerido(*roles_permitidos):
    """
    Decorador de fábrica que restringe el acceso según el rol del usuario.

    Uso:
        @rol_requerido(ROL_GERENTE, ROL_SUBGERENTE)
        def dashboard_view(request): ...

    Parámetros:
        *roles_permitidos: Lista de roles que pueden acceder a la vista.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_requerido
        def _wrapped_view(request, *args, **kwargs):
            usuario = request.usuario

            # Superusuarios (staff) siempre tienen acceso
            if usuario.is_staff:
                return view_func(request, *args, **kwargs)

            # Verificar que el rol del usuario esté en los permitidos
            if usuario.rol not in roles_permitidos:
                messages.error(
                    request, 
                    f'Acceso denegado. Su rol ({usuario.get_rol_display()}) no tiene permisos para esta sección.'
                )
                return render(request, 'errors/403.html', status=403)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
