/* ===== SCRIPT DEL OJO ===== */
function togglePasswordEye(inputId, btn) {
    var input = document.getElementById(inputId);
    if (!input) return;
    var offIcon = btn.querySelector('.eye-off');
    var onIcon  = btn.querySelector('.eye-on');
    if (input.type === 'password') {
        input.type = 'text';
        if (offIcon) offIcon.style.display = 'none';
        if (onIcon)  onIcon.style.display  = 'block';
    } else {
        input.type = 'password';
        if (offIcon) offIcon.style.display = 'block';
        if (onIcon)  onIcon.style.display  = 'none';
    }
}

// Reset al cerrar el modal (envuelve cerrarModalPassword sin romperla)
(function () {
    var timer = setInterval(function () {
        if (typeof window.cerrarModalPassword === 'function' && !window.__ojoFix) {
            window.__ojoFix = true;
            var _orig = window.cerrarModalPassword;
            window.cerrarModalPassword = function () {
                try { _orig(); } catch (e) {}
                ['nueva_password', 'confirmar_password'].forEach(function (id) {
                    var inp = document.getElementById(id);
                    if (inp) inp.type = 'password';
                });
                document.querySelectorAll('.toggle-password-eye').forEach(function (b) {
                    var off = b.querySelector('.eye-off');
                    var on  = b.querySelector('.eye-on');
                    if (off) off.style.display = 'block';
                    if (on)  on.style.display  = 'none';
                });
            };
            clearInterval(timer);
        }
    }, 100);
    setTimeout(function () { clearInterval(timer); }, 5000);
})();