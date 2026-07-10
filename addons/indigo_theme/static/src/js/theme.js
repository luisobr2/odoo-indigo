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
                // Server-side now renders the pill (public) or the dealer price
                // (logged-in dealers). Skip if either is already present so we
                // never double up.
                if (card.querySelector('.indigo-price-on-request, .indigo-dealer-price')) return;
                var price = card.querySelector('.product_price');
                if (!price) return;
                var pill = document.createElement('span');
                pill.className = 'indigo-price-on-request';
                pill.textContent = 'Quote on request';
                price.parentNode.insertBefore(pill, price);
            });
            // PDP price-on-request pill removed — the product detail page no
            // longer shows the "Price set after submission" banner (dealers
            // use the quote form; the public sees the Contact-sales CTA).
        }
        injectPricePills();
        if (window.MutationObserver) {
            var target = document.querySelector('#product_details');
            if (target) {
                new MutationObserver(function() {
                    setTimeout(injectPricePills, 50);
                    setTimeout(attachPlaceOrder, 60);
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
                indigo_brand_id:          $('[data-indigo-spec="brand_id"]')?.value || '',
                indigo_glass_privacy:     $('[data-indigo-spec="glass_privacy"]')?.value || '',
                indigo_door_type:         $('[data-indigo-spec="door_type"]')?.value || '',
                indigo_parts_count:       $('[data-indigo-spec="parts_count"]')?.value || '',
                indigo_color:             $('[data-indigo-spec="color"]')?.value || '',
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

        // Cart-less ordering: the dealer "Place order" button submits the
        // whole order (this variant + dimensions + install context) straight
        // to /indigo/order/submit, which creates+confirms a sale.order and
        // fires the bridge to produce the indigo.order. Then redirect to the
        // confirmation page.
        function attachFilePreview() {
            var input = document.querySelector('#indigo_reference_files');
            var list = document.querySelector('#indigo_files_list');
            if (!input || !list || input.dataset.indigoBound === '1') return;
            input.dataset.indigoBound = '1';
            input.addEventListener('change', function() {
                var files = input.files || [];
                if (!files.length) { list.textContent = ''; return; }
                var names = [];
                var total = 0;
                for (var i = 0; i < files.length; i++) {
                    total += files[i].size;
                    names.push(escapeHtml(files[i].name));
                }
                var mb = (total / (1024 * 1024)).toFixed(1);
                list.innerHTML = '<strong>' + files.length + '</strong> file(s), ' +
                    mb + ' MB — ' + names.join(', ');
            });
        }

        function attachPlaceOrder() {
            attachFilePreview();
            var btn = document.querySelector('#indigo_place_order');
            if (!btn || btn.dataset.indigoBound === '1') return;
            btn.dataset.indigoBound = '1';
            btn.addEventListener('click', function() {
                var prodInput = document.querySelector('input[name="product_id"]');
                var productId = prodInput ? parseInt(prodInput.value, 10) : null;
                // We submit the CURRENT variant (it carries the chosen color) plus
                // indigo_door_type. The server resolves the actual product to order
                // from (design family + selected type) — see indigo_variant_for_type
                // — so it can switch to the Single/Double sibling while preserving
                // the color. Client-side product switching is intentionally NOT done
                // here (it would drop the color in the color-variant case).
                if (!productId) {
                    alert('Please choose the product options first.');
                    return;
                }
                var qtyInput = document.querySelector('#indigo_qty');
                var qty = qtyInput ? (parseInt(qtyInput.value, 10) || 1) : 1;
                var vals = readIndigoFields() || {};
                // Brand + glass are required for manufacturing.
                if (!vals.indigo_brand_id) {
                    alert('Please select the door brand.');
                    return;
                }
                if (!vals.indigo_glass_privacy) {
                    alert('Please choose Clear or Privacy glass.');
                    return;
                }
                // Color / finish is required (the form always shows it).
                if (document.querySelector('[data-indigo-spec="color"]') && !vals.indigo_color) {
                    alert('Please choose the color / finish.');
                    return;
                }
                // Door type is required only when the form shows the selector
                // (flexible / custom products).
                if (document.querySelector('[data-indigo-spec="door_type"]') && !vals.indigo_door_type) {
                    alert('Please choose the door type (Single or Double).');
                    return;
                }
                // Build a multipart payload so reference files ride along with
                // the order fields. (The endpoint is now type="http", so the
                // response is a plain JSON object — no JSON-RPC {result} wrap.)
                var fd = new FormData();
                fd.append('product_id', productId);
                fd.append('add_qty', qty);
                Object.keys(vals).forEach(function(k) { fd.append(k, vals[k] || ''); });

                var fileInput = document.querySelector('#indigo_reference_files');
                var files = (fileInput && fileInput.files) ? fileInput.files : [];
                if (files.length > 10) {
                    alert('Please attach at most 10 files.');
                    return;
                }
                var totalBytes = 0;
                for (var fi = 0; fi < files.length; fi++) { totalBytes += files[fi].size; }
                if (totalBytes > 25 * 1024 * 1024) {
                    alert('Attachments are too large (max 25 MB total).');
                    return;
                }
                for (var fj = 0; fj < files.length; fj++) {
                    fd.append('indigo_reference_files', files[fj]);
                }

                var csrfEl = document.querySelector('#indigo_csrf_token');
                var csrf = (csrfEl && csrfEl.value) ||
                           (window.odoo && window.odoo.csrf_token) || '';
                if (csrf) fd.append('csrf_token', csrf);

                var original = btn.innerHTML;
                btn.disabled = true;
                btn.innerHTML = 'Placing order…';
                fetch('/indigo/order/submit', {
                    method: 'POST',
                    credentials: 'same-origin',
                    body: fd,
                }).then(function(r) { return r.json(); }).then(function(data) {
                    if (data && data.ok && data.redirect) {
                        window.location.href = data.redirect;
                    } else {
                        btn.disabled = false; btn.innerHTML = original;
                        alert((data && data.error) || 'Could not place the order. Please try again.');
                    }
                }).catch(function() {
                    btn.disabled = false; btn.innerHTML = original;
                    alert('Network error. Please try again.');
                });
            });
        }
        attachPlaceOrder();

        // === Door image swap on the PDP (follows door type + color) ===
        // The dealer picks a door type (Single/Double) and a color; the main
        // photo should show THAT type's door in THAT color. Each door-type
        // option carries data-design-id (its sibling design); the color
        // <select> carries data-indigo-design (this card's default design). We
        // build /indigo/door_image/<design>/<color> from the selected type's
        // design (falling back to the default) and the selected color.
        //
        // Delegated on `document` on purpose: Odoo's lazy frontend bundle
        // re-renders the product form after load, dropping any listener bound
        // directly to a <select>. The elements are looked up at change-time so
        // it also survives the carousel re-rendering. Preload first and swap
        // only on success, so a missing photo leaves the current image intact.
        function indigoUpdateDoorImage() {
            var colorSel = document.querySelector('[data-indigo-spec="color"]');
            if (!colorSel) return; // color/finish is a native variant here
            var typeSel = document.querySelector('[data-indigo-spec="door_type"]');
            // Design = the selected type's sibling design, else this card's default.
            var designId = '';
            if (typeSel && typeSel.value && typeSel.options[typeSel.selectedIndex]) {
                designId = typeSel.options[typeSel.selectedIndex].getAttribute('data-design-id') || '';
            }
            if (!designId) designId = colorSel.getAttribute('data-indigo-design') || '';
            if (!designId) return;
            // Color = the picked one, else the first real option so choosing a
            // type ALONE still swaps Single<->Double (with a default finish).
            var color = colorSel.value;
            if (!color) {
                // no finish picked yet — default to black (matches the shop card)
                for (var i = 0; i < colorSel.options.length; i++) {
                    if ((colorSel.options[i].value || '').toLowerCase() === 'black') {
                        color = colorSel.options[i].value; break;
                    }
                }
                for (var j = 0; !color && j < colorSel.options.length; j++) {
                    if (colorSel.options[j].value) { color = colorSel.options[j].value; break; }
                }
            }
            if (!color) return;
            var mainImg = document.querySelector('#o-carousel-product .carousel-item.active img.product_detail_img')
                       || document.querySelector('#o-carousel-product img.product_detail_img')
                       || document.querySelector('img.product_detail_img');
            if (!mainImg) return;
            if (!mainImg.dataset.indigoOrig) {
                mainImg.dataset.indigoOrig = mainImg.getAttribute('src') || '';
            }
            // Pass the door type so CUSTOM (whose SD & DD photos share one
            // design) resolves the right image; harmless for standard designs.
            var typeVal = (typeSel && typeSel.value) ? typeSel.value : '';
            var url = '/indigo/door_image/' + designId + '/' + color
                    + (typeVal ? '?type=' + encodeURIComponent(typeVal) : '');
            var probe = new Image();
            probe.onload = function () {
                mainImg.src = url;
                if (mainImg.hasAttribute('data-zoom-image')) {
                    mainImg.setAttribute('data-zoom-image', url);
                }
            };
            probe.src = url;
        }
        document.addEventListener('change', function (e) {
            var t = e.target;
            if (t && t.matches && (t.matches('[data-indigo-spec="color"]')
                || t.matches('[data-indigo-spec="door_type"]'))) {
                indigoUpdateDoorImage();
            }
        });
        // Newer designs have no base product image, so the native carousel shows
        // a placeholder until the dealer touches a selector. When the server
        // flags the card as image-less (data-indigo-noimg="1"), populate the main
        // photo on load (design + black) and retry across the lazy bundle's
        // re-render. indigoUpdateDoorImage always reflects the CURRENT selection,
        // so a later retry never overrides what the dealer has already picked.
        function indigoMaybeInitDoorImage() {
            if (document.querySelector('[data-indigo-spec="color"][data-indigo-noimg="1"]')) {
                indigoUpdateDoorImage();
            }
        }
        [150, 600, 1500, 2800].forEach(function (ms) { setTimeout(indigoMaybeInitDoorImage, ms); });

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
