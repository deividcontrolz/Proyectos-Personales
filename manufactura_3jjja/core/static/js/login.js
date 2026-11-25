/* login.js
   Alterna la visibilidad de la contraseña y el icono del ojo.
   Regla visual:
       Contraseña OCULTA  ->  ojo CON RAYA (tachado)
       Contraseña VISIBLE ->  ojo ABIERTO (sin raya)
   Los iconos son SVG inline (no dependen de librerias externas).
*/
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.toggle-password-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();

            var wrapper = this.closest('.password-input-wrapper');
            var input = wrapper ? wrapper.querySelector('input') : null;
            if (!input) { return; }

            var eyeOpen = this.querySelector('.eye-open');
            var eyeClosed = this.querySelector('.eye-closed');

            if (input.type === 'password') {
                // pasa de OCULTA a VISIBLE -> mostrar OJO ABIERTO
                input.type = 'text';
                if (eyeOpen)   { eyeOpen.style.display = 'block'; }
                if (eyeClosed) { eyeClosed.style.display = 'none'; }
            } else {
                // pasa de VISIBLE a OCULTA -> mostrar OJO CON RAYA
                input.type = 'password';
                if (eyeOpen)   { eyeOpen.style.display = 'none'; }
                if (eyeClosed) { eyeClosed.style.display = 'block'; }
            }
        });
    });
});