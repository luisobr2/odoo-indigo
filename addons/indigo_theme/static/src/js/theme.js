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
    });
})();
