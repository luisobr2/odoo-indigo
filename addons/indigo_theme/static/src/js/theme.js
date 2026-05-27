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
