# Propuesta de Servicios — MVP

## Sistema de Gestión de Producción
### Indigo Decors · Impact Door Decoration

---

**Preparada para:** Majela — Indigo Decors
**Preparada por:** Luis Bencomo · `lbencomo94@gmail.com`
**Fecha:** 22 de mayo de 2026
**Versión:** 1.0 (MVP por fases)
**Validez de la oferta:** 30 días

---

\newpage

## Carta de presentación

Majela,

Después de revisar el material que compartiste — las órdenes por WhatsApp,
las hojas de Lock Tight, las etiquetas que armas a mano para el diseñador
y la hoja del pintor — quedó claro que el problema de Indigo no es el taller,
es la **administración de cada orden**: la información se transcribe varias
veces y los documentos se hacen a mano.

Esta propuesta plantea una **primera fase MVP** que arranca el sistema con
lo más crítico — tienda online + flujo de órdenes + ficha imprimible —
**en 4 semanas y por USD 1,000**. A partir de ahí, vamos sumando módulos
en fases acotadas y con precio cerrado, de manera que ustedes ven resultados
rápido y van invirtiendo a medida que el sistema demuestra valor.

Es un modelo pensado para que Indigo arranque ya, sin comprometerse a un
proyecto grande de entrada, y para que cada peso que invierten produzca
mejoras visibles en la operación.

Un saludo,
**Luis Bencomo**

---

\newpage

## 1. Resumen ejecutivo

| | |
|---|---|
| **Modelo de trabajo** | MVP de arranque + roadmap por fases con precio cerrado |
| **Stack** | Odoo 17 Community (sin licencia) + módulo a medida `indigo_decors` |
| **Inversión MVP (Fase 1)** | **USD 1,000** — 4 semanas |
| **Roadmap completo (Fases 1–6)** | USD 5,200 — distribuido en el tiempo según prioridades |
| **Costos recurrentes** | ~USD 350 / año (hosting + dominio) |
| **Garantía** | 15 días de hipercare incluidos en el MVP |

### Por qué arrancar por un MVP

- **Resultados en 4 semanas**, no en 3 meses
- **Inversión inicial baja** — riesgo controlado
- **Cada fase es opcional** — contratan las que quieran, cuando quieran
- **Precio cerrado por fase** — sin sorpresas
- **El sistema queda funcionando desde el día 30**, no esperan al final

---

\newpage

## 2. Fase 1 — MVP (USD 1,000 · 4 semanas)

### Qué incluye

#### A · Setup de infraestructura
- Contratación y configuración del servidor (VPS)
- Instalación de Odoo 17 Community
- Dominio + certificado SSL + correos transaccionales
- Backups automáticos diarios

#### B · Tienda online básica
- Catálogo cargado con los diseños del catálogo Lock Tight 2026
- Variantes por tipo de puerta (SD / DD / Sidelite) y color
- Checkout funcionando
- Login para dealers (precios B2B)
- Personalización visual con paleta Indigo (azul institucional)

#### C · Módulo `indigo_decors` — versión inicial
- **Captura de orden** con todos los campos del taller (cliente, dealer,
  diseño, tipo, color, vidrio, SQF, piezas, referencia, fotos)
- **Tablero kanban** con las 13 etapas del flujo de producción
- Movimiento drag & drop entre etapas
- Historial de cambios por orden
- **Ficha de Orden imprimible (PDF)** — generada automáticamente desde la orden

#### D · Capacitación y arranque
- 1 sesión de capacitación en vivo (Zoom, 1.5 hs)
- Manual express en PDF
- **15 días de hipercare** post-producción para ajustes y dudas

### Qué NO incluye en el MVP (queda para fases siguientes)
- Etiqueta del diseñador con QR
- Hoja del pintor automática
- Configurador de pipeline por dealer (todos usan el mismo flujo)
- Portal móvil para instaladores
- Liquidación automática a contratistas
- Mini-CRM de dealers con KPIs
- Permisos granulares por rol (todos los internos ven todo)
- Migración de datos desde la instancia Odoo actual

---

\newpage

## 3. Roadmap de fases — agregar lo que necesiten cuando quieran

> Cada fase tiene **precio cerrado** y se puede contratar de forma
> independiente. No están obligados a comprometerse a todas hoy.

### Fase 2 — Documentos completos + roles (USD 800 · 2-3 semanas)

- **Etiqueta del Diseñador** — formato para impresora térmica, con QR
  que linkea a la orden
- **Hoja del Pintor** — PDF con cálculo automático SQF × tarifa
- **Permisos granulares por rol** — cada persona ve solo lo que le toca
  (Majela, Javier, diseñador, CNC, pintor, administración)
- Plantillas de email automáticas (confirmación al cliente, notificación al dealer)

### Fase 3 — Configurador de pipeline + mini-CRM de dealers (USD 900 · 2-3 semanas)

- **Configurador de pipeline** — pantalla donde Administración activa o
  desactiva las etapas opcionales (confirmación de diseño, medición) por
  cada dealer, **sin programar**
- **Mini-CRM de dealers** — ficha completa con contacto, tarifa, condiciones
  y notas, más KPIs en vivo: órdenes, facturación, **deuda pendiente**
- Filtro y agrupación del tablero por dealer (LOCKTIGHT, USA WINDOWS, SAFEGUARD)

### Fase 4 — Portal móvil de instaladores + fotos (USD 1,200 · 3 semanas)

- **Portal móvil** para Javier y otros instaladores: entran desde el celular
  y ven solo sus tareas del día con dirección y teléfono del cliente
- Botón "subir foto" con cámara del celular
- Botón "marcar tarea como hecha"
- **Gestión de fotos por orden** — galería con contrato, medidas, avance,
  instalación final
- **Tareas dentro de la orden** — varias tareas asignables por orden

### Fase 5 — Liquidación automática a contratistas (USD 700 · 1-2 semanas)

- Cálculo automático del pago al pintor (SQF × tarifa)
- Cálculo automático del pago al instalador (por puerta × tarifa)
- Período configurable (semanal / quincenal / mensual)
- **PDF de liquidación firmable** + marca de pagado + historial

### Fase 6 — Migración de datos + capacitación extendida (USD 600 · 2 semanas)

- Auditoría de la instancia Odoo actual del cliente
- Migración de clientes, dealers, productos y órdenes históricas
- Convivencia 30 días con la instancia vieja (sin borrar nada)
- 3 sesiones extra de capacitación por rol
- Videos cortos tutoriales (1 por flujo principal)

---

\newpage

## 4. Resumen de inversión

| Fase | Qué entrega | Duración | Inversión |
|:--:|---|:--:|---:|
| **1 (MVP)** | Tienda online + flujo de órdenes + ficha imprimible | 4 sem | **USD 1,000** |
| 2 | Documentos completos + roles | 2-3 sem | USD 800 |
| 3 | Configurador de pipeline + CRM dealers | 2-3 sem | USD 900 |
| 4 | Portal móvil de instaladores + fotos | 3 sem | USD 1,200 |
| 5 | Liquidación automática | 1-2 sem | USD 700 |
| 6 | Migración + capacitación extendida | 2 sem | USD 600 |
| | **Total acumulado si contratan todo** | **≈ 4-5 meses** | **USD 5,200** |

### Forma de pago del MVP (Fase 1)

- **50% al firmar** (USD 500)
- **50% al pasar a producción** (USD 500)

### Fases siguientes
Se cotizan/firman individualmente cuando ustedes decidan avanzar. Pueden
contratarlas en cualquier orden — no son secuenciales obligatorias.

---

\newpage

## 5. Costos recurrentes (no incluidos en lo anterior)

| Concepto | Costo aproximado |
|---|---|
| Licencia Odoo Community | **USD 0** (gratis) |
| Hosting VPS (4 GB RAM / 80 GB SSD) | USD 25 – 40 / mes |
| Dominio + SSL | USD 15 / año (o gratis con Let's Encrypt) |
| **Total recurrente** | **~USD 350 / año** |

> Estos costos los paga Indigo directamente al proveedor (VPS y dominio).
> Yo configuro todo, pero la cuenta queda a nombre de ustedes.

---

\newpage

## 6. Plan de trabajo del MVP

| Semana | Hito |
|:--:|---|
| 0 | Firma + cuestionario respondido + acceso a Odoo actual |
| 1 | Servidor montado, Odoo instalado, dominio y SSL funcionando |
| 2 | Catálogo cargado, tienda online publicada, login de dealers |
| 3 | Módulo `indigo_decors`: captura de orden + kanban + ficha PDF |
| 4 | Capacitación, ajustes finales, **paso a producción** |
| 5-6 | **Hipercare** (15 días de soporte intensivo incluidos) |

### Modalidad de trabajo
- Revisión semanal contigo (15-30 min) para mostrar avance
- Entregable verificable al final de cada semana
- Cambios de alcance acordados por escrito antes de ejecutarse

---

\newpage

## 7. Garantías y soporte

- **15 días de hipercare** post-producción en el MVP — corrección
  inmediata de errores funcionales y ajustes menores sin costo
- **Garantía de 60 días** sobre el código entregado: cualquier defecto
  reproducible se corrige sin costo
- **Código entregado a Indigo** — son dueños del módulo a medida
- **Documentación técnica básica** del módulo
- **Manual de usuario** del MVP

---

\newpage

## 8. Próximos pasos

Para arrancar la Fase 1:

1. **Responder el cuestionario de la sección 10** (18 preguntas cortas)
2. **Dar acceso de auditoría** a la instancia Odoo actual
3. **Aprobar esta propuesta y firmar** (envío contrato simple)
4. **50% inicial** transferido para reservar el lugar en el calendario
5. Arrancamos la semana siguiente

---

\newpage

## 9. Por qué este modelo conviene a Indigo

| Razón | Detalle |
|---|---|
| **Bajo riesgo** | USD 1,000 para tener el sistema corriendo en 30 días — si no les sirve, no siguen |
| **Resultados visibles rápido** | El equipo empieza a usarlo desde el día 30, no esperan meses |
| **Inversión escalable** | Cada fase produce mejoras concretas; van pagando lo que les sirve |
| **No quedan atados** | Cada fase es independiente — si en algún momento quieren cortar, ya tienen lo entregado funcionando |
| **Precio cerrado por fase** | Saben exactamente cuánto van a pagar y qué reciben |
| **Sin licencias mensuales** | Odoo Community es gratis — ahorran ~USD 1,800-2,400/año vs Enterprise |

---

\newpage

## 10. Cuestionario de levantamiento

Necesario antes de arrancar la Fase 1 para confirmar alcance.

### Sobre el negocio
1. ¿Cuál es la lista completa de dealers con los que trabajan hoy?
2. ¿Cuántas órdenes manejan en promedio por semana / mes?
3. ¿Una orden trae varias piezas o una sola?
4. ¿Puede una orden regresar a etapas anteriores?
5. ¿Necesitan estados especiales (en espera / cancelada / pausada)?
6. Cada etapa: ¿la trabaja una persona o varias?

### Sobre comunicación y notificaciones
7. ¿Quieren notificaciones automáticas? Si sí, ¿dónde — sistema, correo, WhatsApp?

### Sobre documentos (relevante para Fase 2)
8. Medida exacta de la etiqueta del diseñador y modelo de impresora
9. ¿Quieren agregar código de barras o QR a la etiqueta?
10. ¿Hay otros documentos manuales que no estén listados?

### Sobre pagos y tarifas (relevante para Fase 5)
11. Confirmar tarifa del pintor: ¿SQF × $8 fijo, o varía?
12. ¿La tarifa varía por color / tipo de puerta / dealer?
13. ¿Hay otros contratistas pagados por SQF o por pieza? ¿Cuáles y a qué tarifa?
14. ¿Con qué frecuencia liquidan a los contratistas?

### Sobre el catálogo
15. ¿Pueden compartir la lista oficial completa de códigos de diseño?

### Sobre precios a dealers
16. ¿Cobran por SQF? ¿Precio único o por dealer?

### Sobre el sistema actual
17. Acceso admin a la instancia Odoo actual y qué datos quieren conservar

### Sobre infraestructura
18. ¿Qué dispositivos usa el equipo (PC, móvil)? ¿Preferencia de dominio/hosting?
    ¿Interés en integrar con WhatsApp más adelante?

---

\newpage

## 11. Sobre quien presenta esta propuesta

**Luis Bencomo**
Desarrollo de software a medida — Odoo, sistemas web, automatización
de procesos para PYMES.

📧 lbencomo94@gmail.com

---

*Esta propuesta es confidencial y de uso exclusivo de Indigo Decors.
Documento generado el 22 de mayo de 2026 — versión 1.0.*
