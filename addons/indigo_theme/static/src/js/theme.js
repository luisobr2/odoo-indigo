/* Indigo Theme - micro-interactions (vanilla JS, no deps) */
(function() {
    'use strict';

    function ready(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }

    ready(function() {
        // === Scroll-triggered fade-in animations ===
        if ('IntersectionObserver' in window) {
            var fadeEls = document.querySelectorAll('[data-indigo-fade]');
            if (fadeEls.length) {
                var observer = new IntersectionObserver(function(entries) {
                    entries.forEach(function(entry) {
                        if (entry.isIntersecting) {
                            entry.target.classList.add('in-view');
                            observer.unobserve(entry.target);
                        }
                    });
                }, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });
                fadeEls.forEach(function(el) { observer.observe(el); });
            }
        } else {
            // Fallback: show all
            document.querySelectorAll('[data-indigo-fade]').forEach(function(el) {
                el.classList.add('in-view');
            });
        }

        // === Back-to-top button ===
        var btt = document.querySelector('.indigo-back-to-top');
        if (btt) {
            window.addEventListener('scroll', function() {
                if (window.scrollY > 400) btt.classList.add('show');
                else btt.classList.remove('show');
            }, { passive: true });
            btt.addEventListener('click', function(e) {
                e.preventDefault();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        }

        // === Quote-to-cash B2B: price-on-request labels ===
        // Cart + Add-to-cart work normally. We only annotate the hidden $0
        // prices with a friendly pill so users understand pricing comes
        // from sales after they submit the cart.
        function injectPricePills() {
            // ---- Shop grid (each .oe_product card) ----
            document.querySelectorAll('.oe_product').forEach(function(card) {
                if (card.querySelector('.indigo-price-on-request')) return;
                var price = card.querySelector('.product_price');
                if (!price) return;
                var pill = document.createElement('span');
                pill.className = 'indigo-price-on-request';
                pill.textContent = 'Quote on request';
                price.parentNode.insertBefore(pill, price);
            });
            // ---- PDP — only the main #product_details container ----
            document.querySelectorAll('#product_details').forEach(function(container) {
                var price = container.querySelector('.product_price');
                if (price && !price.parentNode.querySelector('.indigo-price-on-request')) {
                    var pill = document.createElement('span');
                    pill.className = 'indigo-price-on-request';
                    pill.textContent = 'Price set after submission — based on dealer, finish, glass & SQF';
                    price.parentNode.insertBefore(pill, price);
                }
            });
        }
        injectPricePills();
        if (window.MutationObserver) {
            var target = document.querySelector('#product_details');
            if (target) {
                new MutationObserver(function() {
                    setTimeout(injectPricePills, 50);
                }).observe(target, { childList: true, subtree: true });
            }
        }

        // === Rename "Add to cart" / cart copy to match B2B quote-list semantics ===
        function renameQuoteWording() {
            // PDP main CTA button
            document.querySelectorAll('#add_to_cart, button[name="add"]').forEach(function(btn) {
                if (btn.dataset.indigoRenamed) return;
                // Preserve any icon children, replace text node only
                btn.childNodes.forEach(function(node) {
                    if (node.nodeType === 3 && /add\s*to\s*cart/i.test(node.textContent)) {
                        node.textContent = ' Add to quote list ';
                    }
                });
                if (btn.textContent && /add\s*to\s*cart/i.test(btn.textContent) && !btn.querySelector('span')) {
                    btn.textContent = 'Add to quote list';
                }
                btn.dataset.indigoRenamed = '1';
            });
            // Cart icon tooltip
            document.querySelectorAll('header a[href="/shop/cart"]').forEach(function(a) {
                a.setAttribute('title', 'Quote list');
                a.setAttribute('aria-label', 'Quote list');
            });
            // /shop/payment final "Pay Now" button -> "Submit quote request"
            document.querySelectorAll('button[name="o_payment_submit_button"], button.o_payment_submit_button, #o_payment_submit_button').forEach(function(btn) {
                if (btn.dataset.indigoRenamed) return;
                btn.childNodes.forEach(function(node) {
                    if (node.nodeType === 3 && /pay\s*now|pay\b/i.test(node.textContent)) {
                        node.textContent = ' Submit quote request ';
                    }
                });
                if (!btn.querySelector('span') && /pay\s*now|pay\b/i.test(btn.textContent)) {
                    btn.textContent = 'Submit quote request';
                }
                btn.dataset.indigoRenamed = '1';
            });
            // Pre-fill email placeholder in payment banner with logged user email if available
            var emailPl = document.getElementById('indigo_quote_email_pl');
            if (emailPl) {
                var emailEl = document.querySelector('input[name="email"], input[type="email"]');
                if (emailEl && emailEl.value) emailPl.textContent = emailEl.value;
            }
        }
        renameQuoteWording();
        // Re-run on dynamic re-renders (Odoo's payment form is JS-driven)
        if (window.MutationObserver) {
            var paymentForm = document.querySelector('form[name="o_payment_checkout"], #wrap');
            if (paymentForm) {
                new MutationObserver(function() { setTimeout(renameQuoteWording, 50); })
                    .observe(paymentForm, { childList: true, subtree: true });
            }
        }

        // === Gallery filter buttons ===
        var filterButtons = document.querySelectorAll('[data-indigo-filter]');
        var galleryItems = document.querySelectorAll('[data-indigo-tags]');
        if (filterButtons.length && galleryItems.length) {
            filterButtons.forEach(function(btn) {
                btn.addEventListener('click', function() {
                    var filter = btn.getAttribute('data-indigo-filter');
                    // Toggle active state
                    filterButtons.forEach(function(b) {
                        b.classList.remove('btn-dark');
                        b.classList.add('btn-outline-secondary');
                    });
                    btn.classList.remove('btn-outline-secondary');
                    btn.classList.add('btn-dark');
                    // Filter items
                    galleryItems.forEach(function(item) {
                        var tags = (item.getAttribute('data-indigo-tags') || '').split(/\s+/);
                        if (filter === 'all' || tags.indexOf(filter) !== -1) {
                            item.style.display = '';
                            item.style.animation = 'indigoFadeIn 0.4s ease';
                        } else {
                            item.style.display = 'none';
                        }
                    });
                });
            });
        }
    });
})();
