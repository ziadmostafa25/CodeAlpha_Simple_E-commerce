// nice-store | Interface behaviour: mobile menu, product options, payment cards.
(function () {
    'use strict';

    // Mobile menu ----------------------------------------------------------
    const toggle = document.querySelector('.menu-toggle');
    const menu = document.getElementById('site-menu');

    if (toggle && menu) {
        const setOpen = function (isOpen) {
            menu.classList.toggle('is-open', isOpen);
            toggle.setAttribute('aria-expanded', String(isOpen));
            toggle.setAttribute('aria-label', isOpen ? 'Close menu' : 'Open menu');
        };

        toggle.addEventListener('click', function () {
            setOpen(toggle.getAttribute('aria-expanded') !== 'true');
        });

        menu.addEventListener('click', function (event) {
            if (event.target.closest('a')) {
                setOpen(false);
            }
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
                setOpen(false);
                toggle.focus();
            }
        });

        window.matchMedia('(min-width: 900px)').addEventListener('change', function (event) {
            if (event.matches) {
                setOpen(false);
            }
        });
    }

    // Product page: colour changes the photos and the sizes shown ---------
    const purchase = document.querySelector('[data-purchase]');

    if (purchase) {
        const galleries = document.querySelectorAll('[data-gallery]');
        const sizeGroups = purchase.querySelectorAll('[data-sizes-for]');
        const colorName = purchase.querySelector('[data-color-name]');
        const stockHint = purchase.querySelector('[data-stock-hint]');
        const quantity = purchase.querySelector('[data-quantity]');
        const maxQuantity = Number(quantity.dataset.max);

        const updateStock = function () {
            const size = purchase.querySelector('input[name="size"]:checked');
            if (!size) {
                stockHint.textContent = '';
                quantity.max = maxQuantity;
                return;
            }
            const stock = Number(size.dataset.stock);
            quantity.max = Math.min(stock, maxQuantity);
            if (Number(quantity.value) > Number(quantity.max)) {
                quantity.value = quantity.max;
            }
            stockHint.textContent = stock <= 3 ? 'Only ' + stock + ' left' : '';
        };

        const showColor = function (id, label) {
            galleries.forEach(function (gallery) {
                const isMatch = gallery.dataset.gallery === id;
                gallery.hidden = !isMatch;
                if (isMatch) {
                    const firstThumb = gallery.querySelector('.gallery-thumb');
                    if (firstThumb) {
                        gallery.querySelectorAll('.gallery-thumb').forEach(function (t) {
                            t.classList.remove('is-active');
                            t.setAttribute('aria-pressed', 'false');
                        });
                        firstThumb.classList.add('is-active');
                        firstThumb.setAttribute('aria-pressed', 'true');
                        const mainImg = gallery.querySelector('[data-gallery-main]');
                        if (mainImg && firstThumb.dataset.full) {
                            mainImg.src = firstThumb.dataset.full;
                        }
                    }
                }
            });
            sizeGroups.forEach(function (group) {
                group.hidden = group.dataset.sizesFor !== id;
            });
            colorName.textContent = label;
            // A size belongs to one colour, so start the new colour with no size chosen.
            purchase.querySelectorAll('input[name="size"]').forEach(function (input) {
                input.checked = false;
            });
            updateStock();
        };

        purchase.querySelectorAll('[data-color-input]').forEach(function (input) {
            input.addEventListener('change', function () {
                if (input.checked) {
                    showColor(input.value, input.dataset.colorLabel);
                }
            });
        });

        purchase.addEventListener('change', function (event) {
            if (event.target.name === 'size') {
                updateStock();
            }
        });

        document.querySelectorAll('.gallery-thumb').forEach(function (thumb) {
            thumb.addEventListener('click', function () {
                const gallery = thumb.closest('[data-gallery]');
                if (!gallery) return;
                const mainImg = gallery.querySelector('[data-gallery-main]');
                if (mainImg && thumb.dataset.full) {
                    mainImg.src = thumb.dataset.full;
                }
                gallery.querySelectorAll('.gallery-thumb').forEach(function (t) {
                    t.classList.remove('is-active');
                    t.setAttribute('aria-pressed', 'false');
                });
                thumb.classList.add('is-active');
                thumb.setAttribute('aria-pressed', 'true');
            });
        });
    }

    // Checkout: show the instructions of the chosen payment method -------
    const payments = document.querySelector('[data-payment-options]');

    if (payments) {
        const syncPayments = function () {
            const chosen = payments.querySelector('[data-payment-input]:checked');
            payments.querySelectorAll('[data-payment-panel]').forEach(function (panel) {
                panel.hidden = !chosen || panel.dataset.paymentPanel !== chosen.value;
            });
            payments.querySelectorAll('.payment-card').forEach(function (card) {
                card.classList.toggle(
                    'is-selected',
                    card.querySelector('[data-payment-input]').checked
                );
            });
        };

        payments.addEventListener('change', syncPayments);
        syncPayments();
    }

    // Forms that must not be sent twice -------------------------------------
    document.querySelectorAll('form[data-single-submit]').forEach(function (form) {
        form.addEventListener('submit', function () {
            const button = form.querySelector('button[type="submit"]');
            if (button) {
                button.disabled = true;
            }
        });
    });

    // Coming back with the browser's Back button must not leave a disabled button.
    window.addEventListener('pageshow', function (event) {
        if (event.persisted) {
            document.querySelectorAll('form[data-single-submit] button[type="submit"]').forEach(
                function (button) {
                    button.disabled = false;
                }
            );
        }
    });
})();
