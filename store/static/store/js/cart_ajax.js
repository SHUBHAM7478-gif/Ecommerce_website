/**
 * cart_ajax.js
 * ---------------------------------------------------------------
 * Handles "Add to Cart" via AJAX so the page doesn't reload.
 *
 * Responsibilities:
 *   - Intercept submit events on forms with class `js-add-to-cart`
 *   - POST to /cart/add/<product_id>/ with CSRF + quantity
 *   - Update the navbar cart badge from the JSON response
 *   - Show a small toast confirming success/error
 *   - Provide visual feedback on the button (loading, success)
 *
 * Falls back to normal form submission if fetch() isn't supported
 * or if the server responds with anything other than JSON.
 * ---------------------------------------------------------------
 */

(function () {
    'use strict';

    // ---------- Config ----------
    const CART_BADGE_SELECTOR = '.cart-badge';
    const TOAST_DURATION_MS = 2500;

    // ---------- Helpers ----------

    /**
     * Read a cookie by name (used for Django's CSRF token).
     */
    function getCookie(name) {
        const cookies = document.cookie ? document.cookie.split(';') : [];
        for (let i = 0; i < cookies.length; i++) {
            const c = cookies[i].trim();
            if (c.startsWith(name + '=')) {
                return decodeURIComponent(c.substring(name.length + 1));
            }
        }
        return null;
    }

    /**
     * Update every `.cart-badge` element on the page with the new count.
     * Hides the badge if the count is 0.
     */
    function updateCartBadge(count) {
        document.querySelectorAll(CART_BADGE_SELECTOR).forEach(function (badge) {
            badge.textContent = count;
            if (count > 0) {
                badge.style.display = '';
            } else {
                badge.style.display = 'none';
            }
        });
    }

    /**
     * Show a small toast at the top-right of the screen.
     */
    function showToast(message, type, options) {
    options = options || {};

    // Remove any existing toast
    const existing = document.querySelector('.cart-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'cart-toast cart-toast--' + (type || 'info');

    // Build content
    const messageEl = document.createElement('span');
    messageEl.className = 'cart-toast__message';
    messageEl.textContent = message;
    toast.appendChild(messageEl);

    // Add "View Cart" link for success toasts
    if (type === 'success' && options.showCartLink !== false) {
        const cartLink = document.createElement('a');
        cartLink.href = '/cart/';
        cartLink.className = 'cart-toast__action';
        cartLink.textContent = 'View Cart →';
        toast.appendChild(cartLink);
    }

    const closeBtn = document.createElement('button');
    closeBtn.className = 'cart-toast__close';
    closeBtn.innerHTML = '×';
    closeBtn.setAttribute('aria-label', 'Dismiss');
    closeBtn.addEventListener('click', function () {
        toast.classList.remove('cart-toast--visible');
        setTimeout(function () { toast.remove(); }, 250);
    });
    toast.appendChild(closeBtn);

    document.body.appendChild(toast);

    // Fade in
    requestAnimationFrame(function () {
        toast.classList.add('cart-toast--visible');
    });

    // Auto-dismiss (longer when there's a link — user might want to click it)
    const duration = options.showCartLink === false ? TOAST_DURATION_MS : 4000;
    setTimeout(function () {
        if (toast.parentNode) {
            toast.classList.remove('cart-toast--visible');
            setTimeout(function () { toast.remove(); }, 300);
        }
    }, duration);
}

    /**
     * Temporarily change a button's text to show loading / success state.
     */
    function setButtonState(button, state) {
        if (!button) return;

        const originalText = button.dataset.originalText || button.textContent;

        if (!button.dataset.originalText) {
            button.dataset.originalText = originalText;
        }

        if (state === 'loading') {
            button.disabled = true;
            button.textContent = 'Adding...';
            button.classList.add('is-loading');
        } else if (state === 'success') {
            button.disabled = true;
            button.textContent = '✓ Added';
            button.classList.add('is-success');
            setTimeout(function () {
                button.disabled = false;
                button.textContent = button.dataset.originalText;
                button.classList.remove('is-success');
                button.classList.remove('is-loading');
            }, 1200);
        } else {
            button.disabled = false;
            button.textContent = button.dataset.originalText;
            button.classList.remove('is-loading');
            button.classList.remove('is-success');
        }
    }

    // ---------- Main handler ----------

    function handleAddToCart(event) {
        event.preventDefault();

        const form = event.currentTarget;
        const button = form.querySelector('button[type="submit"]');

        // The form's action contains the product ID: /cart/add/<id>/
        // We grab the quantity from the form and post it.
        const action = form.getAttribute('action');
        const quantity = form.querySelector('input[name="quantity"]');
        const qty = quantity ? quantity.value : '1';

        if (!action) return;

        setButtonState(button, 'loading');

        // Build form body
        const body = new URLSearchParams();
        body.append('quantity', qty);

        fetch(action, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
            },
            body: body.toString(),
            credentials: 'same-origin',
        })
            .then(function (response) {
                // If the server didn't return JSON, fall back to form submit
                const contentType = response.headers.get('content-type') || '';
                if (!contentType.includes('application/json')) {
                    throw new Error('non-json');
                }
                return response.json();
            })
            .then(function (data) {
                if (data.success) {
                    updateCartBadge(data.cart_count);
                    showToast(data.message || 'Added to cart', 'success');
                    setButtonState(button, 'success');
                } else {
                    showToast(data.error || 'Could not add to cart', 'error');
                    setButtonState(button, 'reset');
                }
            })
            .catch(function (err) {
                // Fallback: do a normal form submit
                if (err && err.message === 'non-json') {
                    form.removeEventListener('submit', handleAddToCart);
                    form.submit();
                    return;
                }
                showToast('Something went wrong. Please try again.', 'error');
                setButtonState(button, 'reset');
            });
    }

    // ---------- Attach to all add-to-cart forms ----------

    function attachHandlers() {
        document.querySelectorAll('form.js-add-to-cart').forEach(function (form) {
            // Guard against double-binding
            if (form.dataset.ajaxBound === '1') return;
            form.dataset.ajaxBound = '1';
            form.addEventListener('submit', handleAddToCart);
        });
    }

    // ---------- Init ----------

    document.addEventListener('DOMContentLoaded', attachHandlers);

    // Re-scan if content is injected dynamically (e.g. product cards loaded by JS)
    if (typeof MutationObserver !== 'undefined') {
        const observer = new MutationObserver(function () {
            attachHandlers();
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }
})();