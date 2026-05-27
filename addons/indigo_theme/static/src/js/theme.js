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

        // === Request-a-quote model: replace Add-to-cart with Quote CTA ===
        // Indigo does NOT sell direct; every product is quoted manually
        // based on dealer, finishes, glass brand, measurements and SQF.
        function injectQuoteCTA() {
            var quoteSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';

            // ---- PDP (product detail) ----
            // Inject the quote button right after the (now hidden) add-to-cart form.
            // Only target the PDP container (#product_details). The .o_wsale_product_information
            // selector also matches shop-grid cards in Odoo 17, which is why we exclude it here.
            document.querySelectorAll('#product_details').forEach(function(container) {
                if (container.querySelector('.indigo-quote-cta')) return;
                var nameEl = container.querySelector('h1[itemprop="name"], h1.product_name, h1');
                var name = nameEl ? nameEl.innerText.trim() : 'a door';
                var subject = encodeURIComponent('Quote request — ' + name);
                var body = encodeURIComponent('Hi Indigo Decors team,\n\nI would like to request a quote for ' + name + '.\n\nFinish color: \nPrivacy glass: \nDoor brand: \nQuantity: \nDelivery zip code: \n\nThanks.');
                var anchor = container.querySelector('#add_to_cart, button[name="add"], form#sale_buy_now');
                if (!anchor) anchor = container.querySelector('.product_price') || container.querySelector('h1');
                if (!anchor) return;
                var cta = document.createElement('a');
                cta.className = 'indigo-quote-cta';
                cta.href = '/contactus?subject=' + subject + '&description=' + body;
                cta.innerHTML = quoteSvg + '<span>Request a quote</span>';
                anchor.parentNode.insertBefore(cta, anchor.nextSibling);
                // Also drop a "price on request" pill where price was
                var price = container.querySelector('.product_price');
                if (price && !price.querySelector('.indigo-price-on-request')) {
                    var pill = document.createElement('span');
                    pill.className = 'indigo-price-on-request';
                    pill.textContent = 'Price on request — every door is quoted to spec';
                    price.parentNode.insertBefore(pill, price);
                }
            });

            // ---- Shop grid ----
            document.querySelectorAll('.oe_product').forEach(function(card) {
                if (card.querySelector('.indigo-price-on-request')) return;
                var price = card.querySelector('.product_price');
                if (!price) return;
                var pill = document.createElement('span');
                pill.className = 'indigo-price-on-request';
                pill.textContent = 'Quote on request';
                price.parentNode.insertBefore(pill, price);
            });
        }
        injectQuoteCTA();
        // Observe DOM mutations: Odoo re-renders the product detail panel when
        // the user changes attributes (color, glass, brand) → re-inject.
        if (window.MutationObserver) {
            var target = document.querySelector('#product_details') || document.querySelector('.o_wsale_product_grid_wrapper');
            if (target) {
                new MutationObserver(function() {
                    setTimeout(injectQuoteCTA, 50);
                }).observe(target, { childList: true, subtree: true });
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
