/* Indigo Theme - micro-interactions (vanilla JS, no deps) */
(function() {
    'use strict';

    function ready(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }

    ready(function() {
        // === Scroll-triggered animations (fade-in + image reveal) ===
        // Uses Odoo's wrapwrap as the scroll root (Odoo 17 puts scroll there,
        // not on window) — falls back to viewport otherwise.
        var scrollRoot = document.querySelector('#wrapwrap') || null;

        function makeObserver(threshold) {
            return new IntersectionObserver(function(entries) {
                entries.forEach(function(entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('in-view');
                        observer.unobserve(entry.target);
                    }
                });
            }, { root: scrollRoot, threshold: threshold, rootMargin: '0px 0px -8% 0px' });
        }

        if ('IntersectionObserver' in window) {
            var observer = makeObserver(0.12);
            document.querySelectorAll('[data-indigo-fade], [data-indigo-reveal]').forEach(function(el) {
                observer.observe(el);
            });
        } else {
            document.querySelectorAll('[data-indigo-fade], [data-indigo-reveal]').forEach(function(el) {
                el.classList.add('in-view');
            });
        }

        // Smooth-scroll for in-page anchor links (Odoo's #wrapwrap is the
        // scroll container, not window — native CSS smooth-scroll alone
        // does not work here).
        document.querySelectorAll('a[href^="#"]:not([href="#"])').forEach(function(a) {
            a.addEventListener('click', function(e) {
                var id = a.getAttribute('href').substring(1);
                var target = document.getElementById(id) || document.querySelector('[name="' + id + '"]');
                if (!target) return;
                e.preventDefault();
                if (scrollRoot) {
                    var top = target.getBoundingClientRect().top - scrollRoot.getBoundingClientRect().top + scrollRoot.scrollTop - 80;
                    scrollRoot.scrollTo({ top: top, behavior: 'smooth' });
                } else {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
                history.replaceState(null, '', '#' + id);
            });
        });

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

        // === Capture per-door custom fields on PDP (customer, ref, install
        //     address+phone, width, height) and POST to a dedicated
        //     endpoint after Odoo confirms the add-to-cart. Stored
        //     server-side on sale.order.line and also in localStorage as a
        //     fallback for the cart preview. ===
        function readIndigoFields() {
            var $ = function(sel) { return document.querySelector(sel); };
            var vals = {
                indigo_customer_name:     $('input[data-indigo-spec="customer_name"]')?.value?.trim() || '',
                indigo_order_ref:         $('input[data-indigo-spec="order_ref"]')?.value?.trim() || '',
                indigo_install_address:   $('input[data-indigo-spec="install_address"]')?.value?.trim() || '',
                indigo_install_phone:     $('input[data-indigo-spec="install_phone"]')?.value?.trim() || '',
                indigo_door_width:        $('input[data-indigo-spec="width"]')?.value?.trim() || '',
                indigo_door_height:       $('input[data-indigo-spec="height"]')?.value?.trim() || '',
            };
            var hasAny = Object.values(vals).some(Boolean);
            return hasAny ? vals : null;
        }

        function postLineMeta(productId, values) {
            return fetch('/indigo/cart/update_line_meta', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: Object.assign({ product_id: productId }, values),
                }),
            }).then(function(r) { return r.json(); });
        }

        function attachPdpCustomCapture() {
            var addBtn = document.querySelector('#add_to_cart, button[name="add"]');
            if (!addBtn || addBtn.dataset.indigoCustomCapture === '1') return;
            addBtn.dataset.indigoCustomCapture = '1';

            addBtn.addEventListener('click', function() {
                var values = readIndigoFields();
                if (!values) return;

                // Resolve product_id from a hidden input nearby
                var prodInput = document.querySelector('input[name="product_id"]');
                var productId = prodInput ? parseInt(prodInput.value, 10) : null;
                if (!productId) return;

                // localStorage fallback for the cart preview (kept in sync
                // with server-side write)
                try {
                    var slug = window.location.pathname;
                    var store = JSON.parse(localStorage.getItem('indigo_dims') || '{}');
                    var key = slug + '|' + Date.now();
                    store[key] = {
                        w: values.indigo_door_width,
                        h: values.indigo_door_height,
                        customer: values.indigo_customer_name,
                        ref: values.indigo_order_ref,
                        address: values.indigo_install_address,
                        phone: values.indigo_install_phone,
                        slug: slug,
                        ts: Date.now(),
                    };
                    var keys = Object.keys(store).sort(function(a, b) { return store[b].ts - store[a].ts; });
                    while (keys.length > 30) { delete store[keys.pop()]; }
                    localStorage.setItem('indigo_dims', JSON.stringify(store));
                } catch (e) { /* noop */ }

                // Wait for Odoo's add-to-cart JSON-RPC to settle, then POST
                // our custom values onto the line.
                setTimeout(function() {
                    postLineMeta(productId, values).catch(function() {});
                }, 600);
                // Retry once a bit later in case the first one races ahead
                // of line creation on a cold cart.
                setTimeout(function() {
                    postLineMeta(productId, values).catch(function() {});
                }, 1600);
            }, { capture: true });
        }
        attachPdpCustomCapture();

        // On /shop/cart: display the captured per-line context (customer,
        // ref, address, phone, dimensions) as a small block under each
        // matching line item. Sourced from localStorage (server-side is
        // authoritative; this is a UX preview before the dealer submits).
        if (window.location.pathname.indexOf('/shop/cart') === 0) {
            try {
                var store = JSON.parse(localStorage.getItem('indigo_dims') || '{}');
                var bySlug = {};
                Object.values(store).forEach(function(d) {
                    if (!bySlug[d.slug] || bySlug[d.slug].ts < d.ts) bySlug[d.slug] = d;
                });
                document.querySelectorAll('tr.o_cart_product, .o_cart_product, .o_wsale_cart_line').forEach(function(row) {
                    var link = row.querySelector('a[href*="/shop/"]');
                    if (!link) return;
                    var slug = new URL(link.href).pathname;
                    var d = bySlug[slug];
                    if (!d || row.querySelector('.indigo-line-meta')) return;
                    var parts = [];
                    if (d.customer) parts.push('<strong>Customer:</strong> ' + escapeHtml(d.customer));
                    if (d.ref) parts.push('<strong>Ref:</strong> ' + escapeHtml(d.ref));
                    if (d.address) parts.push('<strong>Install:</strong> ' + escapeHtml(d.address));
                    if (d.phone) parts.push('<strong>Phone:</strong> ' + escapeHtml(d.phone));
                    var dim = (d.w || d.h)
                        ? '<strong>Size:</strong> ' + (d.w ? d.w + ' in W' : '') +
                          (d.w && d.h ? ' × ' : '') +
                          (d.h ? d.h + ' in H' : '')
                        : '';
                    if (dim) parts.push(dim);
                    if (!parts.length) return;
                    var hint = document.createElement('div');
                    hint.className = 'indigo-line-meta small mt-2';
                    hint.innerHTML = parts.join(' · ');
                    var infoCell = row.querySelector('.td-product_name, .o_cart_product_name, td') || row;
                    infoCell.appendChild(hint);
                });
            } catch (e) { /* noop */ }
        }
        function escapeHtml(s) {
            return String(s).replace(/[&<>"']/g, function(c) {
                return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
            });
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

        // === Tabs (Featured products section on home, reusable anywhere) ===
        document.querySelectorAll('[data-indigo-tab]').forEach(function(tab) {
            tab.addEventListener('click', function() {
                var key = tab.getAttribute('data-indigo-tab');
                var scope = tab.closest('section') || document;
                scope.querySelectorAll('[data-indigo-tab]').forEach(function(t) {
                    t.classList.toggle('is-active', t === tab);
                });
                scope.querySelectorAll('[data-indigo-tab-panel]').forEach(function(p) {
                    p.classList.toggle('is-active', p.getAttribute('data-indigo-tab-panel') === key);
                });
            });
        });

        // === Gallery filter buttons ===
        var filterButtons = document.querySelectorAll('[data-indigo-filter]');
        var galleryItems = document.querySelectorAll('[data-indigo-tags]');
        if (filterButtons.length && galleryItems.length) {
            filterButtons.forEach(function(btn) {
                btn.addEventListener('click', function() {
                    var filter = btn.getAttribute('data-indigo-filter');
                    // Toggle active state (supports both old btn-dark and new .is-active patterns)
                    filterButtons.forEach(function(b) {
                        b.classList.remove('btn-dark', 'is-active');
                        b.classList.add('btn-outline-secondary');
                    });
                    btn.classList.remove('btn-outline-secondary');
                    btn.classList.add('btn-dark', 'is-active');
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
