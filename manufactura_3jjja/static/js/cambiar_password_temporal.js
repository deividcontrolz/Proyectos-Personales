/* cambiar_password_temporal.js
   Alterna la visibilidad de los campos de contraseña en la
   pantalla de cambio obligatorio de contraseña.
*/
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.toggle-password-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            var targetId = this.getAttribute('data-target');
            var input = targetId ? document.getElementById(targetId) : null;
            var icon = this.querySelector('i');
            if (!input) return;

            if (input.type === 'password') {
                input.type = 'text';
                if (icon) icon.className = 'bi bi-eye';
            } else {
                input.type = 'password';
                if (icon) icon.className = 'bi bi-eye-slash';
            }
        });
    });
});
