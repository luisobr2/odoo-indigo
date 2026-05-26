# Manual de Administrador — Indigo Decors

Para el manager / dueño del taller. Cubre configuración del sistema y operaciones que **no son del día a día** sino de setup y gestión.

---

## Índice

1. [Permisos / grupos](#1-permisos--grupos)
2. [Gestionar dealers](#2-gestionar-dealers)
3. [Crear usuarios del equipo interno](#3-crear-usuarios-del-equipo-interno)
4. [Crear accesos portal (dealers e instaladores)](#4-crear-accesos-portal-dealers-e-instaladores)
5. [Etapas del pipeline + SLA](#5-etapas-del-pipeline--sla)
6. [Tarifas de contratistas](#6-tarifas-de-contratistas)
7. [Liquidaciones](#7-liquidaciones)
8. [Inventario CNC](#8-inventario-cnc)
9. [Catálogo de diseños](#9-catálogo-de-diseños)
10. [Dashboards y rankings](#10-dashboards-y-rankings)

---

## 1. Permisos / grupos

El módulo define estos grupos. Cada usuario interno debe pertenecer a uno o más.

| Grupo | Quién | Puede |
|---|---|---|
| **Indigo / User** | Todos los usuarios internos | Ver y editar órdenes, mover etapas, asignar |
| **Indigo / Manager** | Manager / dueño | Todo lo de User + crear/editar tarifas, etapas, dealers, ejecutar wizards de liquidación |
| **Indigo / Designer** | Diseñador | (Heredado de User, sin permisos extra; para futuras restricciones) |
| **Indigo / CNC / Router** | Personal CNC | (Heredado de User) |
| **Indigo / Painter** | Pintor | (Heredado de User) |
| **Indigo / Office / Administración** | Office | (Heredado de User) |
| **Indigo / Contractor (portal)** | Instalador externo | Acceso restringido al portal `/my/installs` (sus órdenes únicamente) |

### Asignar grupos a un usuario

1. Settings → Users & Companies → Users → seleccionar el usuario
2. Pestaña **Access Rights** → buscar "Indigo Decors" → tildar los grupos

---

## 2. Gestionar dealers

Indigo → Dealers.

### Crear un dealer nuevo

1. Botón **New**
2. Completar:
   - **Name** (ej. "Lock Tight")
   - **Es dealer Indigo** ✅
   - **Codigo de dealer** (ej. "LT") — sale en algunos reportes
   - **Precio por defecto por SQF** (ej. $12.00) — se auto-asigna a las nuevas órdenes
   - **Email** (necesario para que pueda usar el portal)
3. Pestaña **Indigo Dealer**:
   - **Etapas opcionales activas**: marcar las 2-5 que apliquen para este dealer (si el dealer no usa "Design Confirmation Pending", no la actives — el kanban filtrará la columna cuando se filtre por este dealer)

### Editar precio del dealer

El precio se puede:
- Cambiar en la ficha del dealer (afecta órdenes futuras)
- Override en una orden específica (campo `Precio por SQF` en la orden)

---

## 3. Crear usuarios del equipo interno

Settings → Users & Companies → Users → **New**.

| Campo | Valor |
|---|---|
| Name | Nombre completo |
| Email | Email de trabajo (será el login) |
| Access Rights | Indigo Decors → User + el rol que aplique (Designer, Painter, etc.) |

Al guardar, Odoo envía email de invitación con link para fijar password. **En dev este correo queda capturado en MailHog (http://localhost:8025).**

---

## 4. Crear accesos portal (dealers e instaladores)

Para que un dealer o instalador externo pueda usar su portal:

1. Ir a la ficha del partner (Indigo → Dealers, o crear el contacto)
2. Verificar que tenga **Email** completo
3. En la pestaña **Indigo Dealer**, click **"Crear acceso portal"**
4. Odoo crea un `res.users` con grupo "Portal" y envía email de invitación (capturado en MailHog en dev)
5. El usuario fija su password desde el email

**Para instaladores**: mismo flujo pero el partner es el contratista (Indigo → Dealers no aplica directo; ir a Contacts → crear → marcar como individual; luego en la ficha podés usar el mismo botón si lo añades a la vista — o usar `scripts/setup_portal_installer.py`).

---

## 5. Etapas del pipeline + SLA

Indigo → Configuration → Etapas.

13 etapas pre-cargadas (3 obligatorias + 4 opcionales por dealer + 6 obligatorias finales). Para cada una se puede configurar:

| Campo | Para qué |
|---|---|
| **Name** | Nombre visible en el Kanban |
| **Codigo** | Identificador interno (no cambiar para `painting` e `installed` — disparan lógica de payout) |
| **Sequence** | Orden en el Kanban |
| **Opcional por dealer** | Si está tildado, la etapa solo aparece para dealers que la tengan en `Etapas opcionales activas` |
| **Plegada en kanban** | Si está tildada, la columna empieza colapsada (útil para "Closed") |
| **Plantilla de notificacion** | Mail template específico que se envía al entrar a esta etapa (override del genérico) |
| **Dias SLA** | Días máximos esperados en esta etapa antes de marcarse atrasada. `0` = sin SLA |

### SLAs por defecto (cargados con `scripts/set_sla_defaults.py`)

| Etapa | Días |
|---|---|
| New Order | 2 |
| Design Confirmation Pending | 3 |
| Design Confirmed | 1 |
| Measurement Pending | 5 |
| Measured | 2 |
| Ready for Digitalization | 3 |
| CNC / Router | 5 |
| Painting | 7 |
| Ready for Installation | 3 |
| Installation Scheduled | 7 |
| Installed | 2 |
| Invoiced / Paid | 5 |
| Closed | — |

Un cron diario revisa las órdenes atrasadas y crea actividad `todo` para los asignados.

---

## 6. Tarifas de contratistas

Indigo → Configuration → Tarifas.

Define las tarifas por SQF / pieza. El sistema usa la **primera tarifa activa** del tipo correspondiente.

| Tipo | Default | Unidad |
|---|---|---|
| Painter | $8.00 | Por SQF |
| Installer | $35.00 | Por pieza (puerta) |

Para cambiar: simplemente editar el `rate` en la línea correspondiente. **Afecta a las nuevas liquidaciones que se generen** — las ya creadas no se recalculan.

Para tarifas escalonadas (ej. $8 hasta 100 SQF, $10 después): hoy no está implementado. Si se necesita, se agrega lógica en `_get_painter_rate`.

---

## 7. Liquidaciones

Indigo → Liquidaciones.

### Cómo se generan

- **Pintor**: al mover una orden DE `Painting` a la siguiente etapa, se crea automáticamente un draft payout con una línea por pieza (cantidad = SQF de la línea, tarifa = $8).
- **Instalador**: al mover una orden A `Installed`, se crea un draft payout por cada instalador asignado (cantidad = puertas / N_instaladores, tarifa = $35).

### Workflow del payout

```
Borrador → [Aprobar] → Aprobada → [Marcar pagada] → Pagada
                                                       ↓
                                                  [Pasar a borrador]
```

### Liquidación semanal consolidada (instaladores)

Cuando hay varias órdenes en draft del mismo instalador en una semana:

1. Indigo → **Consolidar semanal**
2. Seleccionar **Contratista** + **Tipo** + rango **Desde / Hasta**
3. **Consolidar**
4. El wizard:
   - Crea un nuevo payout consolidado con todas las líneas
   - Marca los draft originales como **Cancelados** con nota cruzada
5. Aprobar el consolidado → imprimir comprobante PDF (botón Print) → pagar → marcar pagado

---

## 8. Inventario CNC

Indigo → Inventario CNC.

Inventario simple de piezas ya cortadas listas para pintar. Se ajusta manualmente:

1. Al producir piezas en CNC, agregar/incrementar el **on_hand** del diseño + tipo correspondiente
2. El sistema computa automáticamente:
   - **Reservadas** = piezas comprometidas en órdenes activas (no closed/installed/invoiced)
   - **Disponibles** = on_hand − reservadas
3. Si `Disponibles < umbral` (default 5), un cron diario crea actividad de alerta para los managers

Si la operación lo requiere, se puede extender para que auto-descuente al pasar órdenes de `Painting` a etapas siguientes.

---

## 9. Catálogo de diseños

Indigo → Catalogo de disenos.

33 diseños cargados como demo (ID01-ID34 SD/DD + TD-SD/TD-DED). Para agregar:

1. **New**
2. **Codigo** (único, ej. "ID35-SD") + **Nombre**
3. **Tipo** (SD / DD / Sidelite)
4. **Imagen** (sube foto del diseño — sale en la vista Kanban del catálogo y en el portal del dealer)
5. **Save**

Para reemplazar imágenes en bulk: usa la importación de Odoo (Settings → Imports) con un CSV `code, name, image (base64)`.

---

## 10. Dashboards y rankings

| Menú | Qué muestra |
|---|---|
| **Indigo → Dashboard** | Graph + Pivot de órdenes agrupadas por etapa, dealer, mes, con medidas total_dealer_charge, total_sqf, door_count |
| **Indigo → Ranking dealers** | Comparativa por dealer: cuánto facturó, cuántas órdenes, cuántos SQF |
| **Indigo → Ranking contratistas** | Sobre liquidaciones: cuánto se le pagó a cada contratista, por tipo (pintor/instalador) |
| **Indigo → Calendario instalaciones** | Vista mensual con las instalaciones programadas (basadas en `installation_date`) |

Cada vista permite cambiar entre Graph / Pivot / Lista / Kanban. Los filtros y groupings se pueden guardar (botón estrella).

---

## Resumen de defaults / asunciones

Estas son las decisiones tomadas. Cambialas según convenga:

| Default | Dónde se ajusta |
|---|---|
| Pintor $8/SQF | Indigo → Config → Tarifas |
| Instalador $35/puerta | Indigo → Config → Tarifas |
| Precio dealer Lock Tight $12/SQF | Ficha del dealer |
| Precio dealer Web Indigo $11/SQF | Ficha del dealer |
| Precio dealer USA Windows $11.50/SQF | Ficha del dealer |
| SLAs por etapa | Indigo → Config → Etapas |
| Umbral stock bajo | Indigo → Inventario CNC (campo `low_stock_threshold` por item) |
| Notificaciones | Solo email por defecto. Para activar SMS/WhatsApp ver `docs/OPERACIONES.md` |

---

## Casos especiales

### Una orden tiene un cliente final que paga directo (no el dealer)

- Marcar `Estado de pago` directamente desde la orden
- Subir comprobante en pestaña "Recibos de pago"

### Re-trabajo (pintura mal, hay que repetir)

- Mover la orden atrás (de "Ready for Installation" a "Painting", por ejemplo)
- Registrar incidencia explicando el motivo
- El payout previo NO se duplica (idempotencia) — si necesitas pagarle al pintor por el rework, agregar manualmente una línea al payout existente

### Cliente cancela a última hora

- Mover orden a "Closed" (sin firmar) o agregarle estado adicional
- Registrar incidencia "Cliente — cancelación tardía"
- Si ya pintaron, generar payout manualmente al pintor por el material gastado
