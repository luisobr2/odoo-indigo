# Mockup UI — Indigo Decors

Mockup HTML/Tailwind del nuevo storefront. Para aprobación del cliente antes
de implementar como tema Odoo.

## Ver el mockup

Abrir cualquier `.html` directo en el navegador (no requiere server):

```
mockup/
├── index.html          Home con hero, productos destacados, dealer program
├── shop.html           Catálogo (grid + filtros)
├── product.html        Detalle de producto (galería + variants + reviews)
├── cart.html           Carrito
├── checkout.html       Checkout (Stripe-ready)
├── account.html        Perfil del dealer
├── dealer-orders.html  "Mis órdenes" del dealer
└── installer.html      Portal móvil del instalador
```

## Stack

- **Tailwind CSS** (CDN — para producción se compila con prefix `tw-`)
- **Alpine.js** (CDN — interactividad ligera, no requiere build)
- **Heroicons** (inline SVG)
- **Inter font** (Google Fonts)

## Paleta

```
Azul Indigo principal   #1f4486
Azul Indigo claro       #3a5ea3
Negro / texto           #0f172a
Gris claro / bg         #f8fafc
Gris medio / borders    #e2e8f0
Verde éxito             #10b981
Rojo error              #ef4444
```

## Próximos pasos

1. Cliente revisa el mockup en su navegador
2. Itera cambios (colores, copy, secciones)
3. Aprobado → convertir a tema Odoo `indigo_theme` con templates QWeb

El mockup es **navegable entre páginas** (links internos funcionan).
