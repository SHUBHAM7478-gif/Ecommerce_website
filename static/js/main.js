// ---------- User dropdown ----------
document.addEventListener('DOMContentLoaded', function () {
    const trigger = document.getElementById('navUserTrigger');
    const user    = document.getElementById('navUser');

    if (!trigger || !user) return;

    trigger.addEventListener('click', function (e) {
        e.stopPropagation();
        user.classList.toggle('is-open');
    });

    // Close when clicking outside
    document.addEventListener('click', function (e) {
        if (!user.contains(e.target)) {
            user.classList.remove('is-open');
        }
    });

    // Close on Escape
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            user.classList.remove('is-open');
        }
    });
});

// ---------- Cart quantity stepper ----------
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.js-qty-form').forEach(function (form) {
        const input = form.querySelector('.qty-input');
        const decBtn = form.querySelector('[data-action="decrement"]');
        const incBtn = form.querySelector('[data-action="increment"]');
        const max = parseInt(input.getAttribute('max'), 10) || 999;

        if (!input || !decBtn || !incBtn) return;

        let current = parseInt(input.value, 10) || 1;

        decBtn.addEventListener('click', function () {
            if (current <= 0) return;
            current--;
            input.value = current;
            form.submit();
        });

        incBtn.addEventListener('click', function () {
            if (current >= max) return;
            current++;
            input.value = current;
            form.submit();
        });
    });
});