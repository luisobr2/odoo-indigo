# Manual de Usuario — Indigo Decors

Manual práctico para el día a día. Está dividido por rol — abre la sección que aplica a tu trabajo.

> URL del sistema: **http://localhost:8069** (en producción será el dominio del cliente)

---

## Índice

1. [Iniciar sesión](#1-iniciar-sesión)
2. [Office / Administración](#2-office--administración) — Majela
3. [Diseñador](#3-diseñador)
4. [CNC / Router](#4-cnc--router)
5. [Pintor](#5-pintor)
6. [Instalador (portal móvil)](#6-instalador-portal-móvil) — Javier
7. [Dealer (portal web)](#7-dealer-portal-web)
8. [Reportes e impresiones](#8-reportes-e-impresiones)

---

## 1. Iniciar sesión

1. Entrar a la URL del sistema
2. Email + contraseña (lo asigna el administrador)
3. Cambiar idioma (opcional): arriba a la derecha → tu nombre → **Preferences** → Language → **English / Español**

---

## 2. Office / Administración

Responsable: capturar órdenes que llegan por WhatsApp / papel / teléfono, asignar responsables, marcar pagos, gestionar el flujo general.

### Crear una orden manual

1. Menú **Indigo → Orders → New**
2. Completar:
   - **Dealer**: empresa que envía el pedido (Lock Tight, Web Indigo, USA Windows, …)
   - **Ref. dealer**: número/nombre que el dealer usa internamente para este cliente final
   - **Cliente final**: nombre, teléfono, email, dirección de instalación
   - **Pintor asignado**: contratista pintor
   - **Instaladores**: uno o varios (el monto $35/puerta se divide equitativamente)
   - **Fecha entrega prometida** + **Fecha instalación programada** (opcionales)
   - **PRIV**: referencia interna libre que sale en la etiqueta del diseñador
3. En la pestaña **Piezas** (líneas), agregar cada puerta:
   - Diseño (autocomplete del catálogo)
   - Tipo (Single Door / Double Door / Sidelite)
   - Color (White / Bronze / Black / Custom)
   - Tipo de vidrio (ej. ESW)
   - Medidas (ancho × alto en pulgadas)
   - Cantidad
   - El SQF se calcula solo: `width × height × qty / 144`
4. Subir fotos del contrato/puerta en pestaña **Fotos del contrato**
5. **Save**

Al guardar, Odoo le asigna automáticamente número (`IND/YYYY/NNNNN`), token público de tracking y precio por SQF del dealer.

### Mover la orden por las etapas (Kanban)

1. Menú **Indigo → Orders** (vista por defecto: Kanban)
2. Arrastrar la card de columna a columna:
   - **New Order → Design Confirmation Pending → … → Painting → Ready for Installation → Installation Scheduled → Installed → Invoiced → Closed**
3. Cada cambio:
   - Envía un correo automático al/los asignados
   - Guarda un audit log en la pestaña inferior (chatter)

**Indicadores visuales en la card**:
- **Borde rojo + badge "Atrasada Xd"** → la orden lleva más días en esa etapa que el SLA configurado
- **Badge "On hold"** → orden pausada (ver siguiente sección)
- **Color del progressbar superior** → estado de pago (rojo / amarillo / verde)

### Pausar una orden ("On Hold")

Cuando una instalación se aplaza por causa externa (cliente no responde, falta material, etc.):

1. Abrir la orden
2. Marcar el check **En espera / Pospuesta**
3. Escribir el motivo en **Motivo de espera**
4. La card del Kanban queda atenuada con badge amarillo "En espera"
5. Quitar el check para reactivar

### Registrar una incidencia

Cuando ocurre un error (medida mal, pintura mal, cliente cancela, etc.):

1. Abrir la orden
2. Pestaña **Incidencias** → agregar línea con categoría (Medida / Pintura / Cliente / Instalación / Otro) + descripción
3. Quedan logueadas con autor y fecha

### Marcar pago

Pestaña principal → campo **Estado de pago** → seleccionar:
- **Sin pagar** (default)
- **Pago parcial**
- **Pagado**

El dealer puede subir comprobante desde su portal — se ve en la pestaña **Recibos de pago**.

---

## 3. Diseñador

Etapa: **Ready for Digitalization** → **CNC / Router**.

Recibe correo cuando una orden entra a "Ready for Digitalization" o cuando lo asignan.

1. Abrir la orden
2. Verificar medidas y diseño elegido (pestaña Piezas)
3. Digitalizar en su software CAD/CAM externo
4. Cuando termina → arrastrar la card en Kanban a la columna **CNC / Router**
5. Imprimir **Etiquetas del diseñador** desde el botón **Print** (una etiqueta por puerta, con QR del número de orden)

### Imprimir etiquetas

1. Indigo → Orders → seleccionar la orden (o varias)
2. Botón **Print → Etiquetas del diseñador**
3. Sale PDF con N etiquetas (una por puerta, multiplicada por qty)
4. Imprimir en la impresora térmica (12.7 × 57.15 mm)

---

## 4. CNC / Router

Etapa: **CNC / Router** → **Painting**.

1. Recibe la lista en Kanban filtrando por columna **CNC / Router**
2. Corta las piezas según el diseño digitalizado
3. Pegar la etiqueta del diseñador detrás de cada pieza cortada
4. Cuando termina → mover card a **Painting**
5. (Opcional) Actualizar stock en **Indigo → Inventario CNC** si las piezas quedan en almacén antes de pintar

---

## 5. Pintor

Etapa: **Painting** → **Ready for Installation**.

1. Recibe correo cuando una orden entra a "Painting" (si está asignado como `painter_id`)
2. Pinta las piezas según color/finish de cada línea
3. Cuando termina → mover card a **Ready for Installation**
4. **Esto dispara automáticamente** la creación de su liquidación (draft payout) en `Indigo → Liquidaciones`
5. Imprimir **Hoja del pintor** desde Indigo → Orders → seleccionar la orden → Print → Hoja del pintor

La liquidación queda en estado **Borrador**. El administrador la aprueba y marca pagada cuando recibe el pago.

---

## 6. Instalador (portal móvil)

Acceso: el administrador le crea un usuario portal. Recibe email de invitación.

### Día a día del instalador

1. Entrar al sistema desde el celular o PC
2. Ver **"Mis instalaciones"** en el home → lista de órdenes asignadas
3. Tocar una orden para ver:
   - Dealer, cliente, dirección, teléfono
   - Piezas a instalar con medidas
   - Etapa actual
4. **Subir foto del trabajo** (cámara del teléfono): ayuda como evidencia
5. Al terminar la instalación:
   - Pedir al cliente que firme en el canvas (con el dedo)
   - Confirmar **"Confirmar instalación completada"**
6. La orden pasa a **Installed**, se genera automáticamente el payout de instalación ($35/puerta dividido entre los instaladores asignados)

### Firma del cliente

- El cliente firma con el dedo directamente en pantalla del teléfono/tablet
- Botón **Borrar firma** si necesita repetirla
- El nombre del firmante se pre-rellena con el nombre del cliente
- La firma queda guardada como imagen + fecha en la orden (legal proof)

---

## 7. Dealer (portal web)

Acceso: el administrador crea su usuario portal (botón "Crear acceso portal" en la ficha del dealer). Recibe email de invitación.

### Mis órdenes

1. Login → "Mis órdenes" en el home
2. Ver la lista de todas las órdenes que ha registrado, con su estado actual

### Crear una nueva orden desde el portal

1. Botón **"+ Nueva orden"** arriba a la derecha
2. Completar datos del cliente final + referencia
3. Agregar piezas (botón **"+ Agregar pieza"** para múltiples puertas)
4. Para cada pieza: código de diseño (autocomplete), tipo, color, vidrio, medidas, cantidad
5. **Crear orden**

La orden llega a Indigo como **New Order** y el equipo del taller la procesa.

### Duplicar una orden anterior

Útil cuando el dealer pide la misma combinación para distintos clientes.

1. Abrir una orden anterior
2. Botón **"Duplicar este pedido"**
3. Se crea una copia con las mismas líneas, estado `New Order`, pago resetado, nombre del cliente con sufijo "(copia)"
4. Editar el nombre/datos del nuevo cliente final

### Subir comprobante de pago

1. Abrir la orden
2. Sección **"Subir comprobante de pago"** → seleccionar archivo (imagen o PDF)
3. **Subir recibo**
4. El comprobante queda adjunto a la orden y los managers reciben notificación

### Tracking público para el cliente final

Cada orden tiene un link público sin login. El administrador puede compartirlo con el cliente final del dealer para que vea el progreso:

```
http://<dominio>/track/<access_token>
```

(El `access_token` está en el campo `Token público` de la orden. En producción, el dealer puede ver/copiar este link desde el detalle de su orden — se puede agregar como opcional.)

---

## 8. Reportes e impresiones

Todos los reportes se imprimen desde **Indigo → Orders** (selecciona una o varias órdenes) → botón **Print** → elegir reporte:

| Reporte | Descripción |
|---|---|
| **Ficha de orden** | A4/Letter con datos completos del dealer, cliente, dirección, todas las piezas, totales SQF y dealer charge. Para imprimir y/o enviar por correo. |
| **Etiquetas del diseñador** | Una etiqueta por puerta (12.7 × 57.15 mm) con dealer, cliente, medidas, tipo-color-vidrio, número orden, PRIV, cantidad, código diseño + QR del número de orden. |
| **Hoja del pintor** | Tabla Company / Order# / Client / Color / DoorType / SQF / Price ($8) / Total. Si seleccionas N órdenes, sale una sola hoja agregada (útil para liquidación semanal). |
| **Direcciones de instalación** | Tabla con órdenes en etapa "Installation Scheduled" para coordinar los días de instalación. |

Para liquidaciones:

- **Indigo → Liquidaciones** → seleccionar una → Print → **Comprobante de liquidación** (PDF firmable con líneas de detalle + total).

---

## Atajos útiles

- **Filtrar por etapa**: en Kanban, la columna ya es el filtro. En lista, click en el icono de filtros arriba.
- **Filtrar "Mis órdenes"**: filtro guardado disponible — muestra solo las asignadas a ti.
- **Buscar por número de orden / cliente / dealer**: barra de búsqueda arriba.
- **Atrasadas**: filtro en buscador "Stock bajo" / "Atrasada" según vista.
- **Idioma**: tu nombre arriba derecha → Preferences → Language.

---

## ¿Algo no anda?

- Si una etapa no aparece en kanban: el dealer probablemente no la tiene activada (etapas opcionales). El administrador la activa en la ficha del dealer.
- Si no recibes correos: chequear que tu usuario tenga email configurado y estés como asignado de la orden.
- Si el portal móvil no carga: limpia caché del navegador (Ctrl+Shift+R) o pide al admin que verifique tu acceso.
