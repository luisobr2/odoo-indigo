# Propuesta — Sistema de Gestión de Producción
## Indigo Decors · Impact Door Decoration

**Cliente:** Indigo Decors (https://www.indigodecors.com)
**Fecha:** 2026-05-22
**Versión:** 1.0 — Stack Odoo Community + Módulo a Medida

---

## Resumen ejecutivo

Hoy Indigo Decors gestiona toda la producción de puertas decorativas (corte,
pintura e instalación) de forma **manual**: las órdenes llegan por web, WhatsApp
y papel; la información se reescribe varias veces; y los documentos de cada
área (ficha de orden, etiqueta del diseñador, hoja del pintor) se hacen a mano,
con el costo en tiempo y errores que eso implica.

La propuesta es **automatizar todo ese ciclo** sobre **Odoo Community** (sin
costo de licencia) sumándole una **personalización a medida** pensada para el
taller. Lo que entregamos como base incluye:

- Las 13 etapas de producción, **activables o desactivables por dealer** desde
  un panel — sin depender de un programador
- Generación automática de los 3 documentos críticos del día a día
  (ficha de orden, etiqueta del diseñador, hoja del pintor)
- Cálculo automático del pago al pintor y otros contratistas por SQF
- Acceso móvil para instaladores con fotos de obra
- Vista de dealers con sus tarifas, condiciones y deuda al día

**Por qué Odoo y no empezar desde cero:** Indigo ya tenía Odoo funcionando.
Lo que les incomodaba era la interfaz "tipo ERP" y el costo de la versión
Enterprise — no la herramienta en sí. Apoyándonos en la versión Community
(gratuita) y agregando solo las pantallas y reportes propios del taller,
evitamos pagar licencias y resolvemos la parte que realmente molestaba: la
experiencia de uso.

> **Nota importante sobre el alcance:** lo descrito en esta propuesta es el
> **paquete base mínimo** acordado para arrancar. A medida que avance el
> proyecto, si surgen nuevas ideas o ajustes adicionales (pantallas extras,
> integraciones, automatizaciones más finas), el costo y el plazo se ajustan
> en función del tiempo real de desarrollo que requiera cada personalización.
> Lo trabajamos por etapas, con visibilidad clara antes de avanzar.

---

## 1. Diagnóstico — cómo trabaja el taller hoy

### 1.1 Flujo actual
```
Orden Web → Confirmación de diseño → Medición → Digitalización
   → CNC/Router → Pintura → Instalación → Facturación / Pago a contratistas
```

### 1.2 Cómo llegan las órdenes
- **Web (Odoo eCommerce actual):** cada dealer tiene cuenta y compra logueado.
- **WhatsApp:** Majela transcribe a mano al sistema.
- **Papel:** quote items de Lock Tight con anotaciones manuscritas.

Ningún dealer puede integrarse por API; **toda la entrada es manual**. El costo
de transcripción es alto y produce errores.

### 1.3 Puntos de dolor identificados
| # | Situación actual | Impacto en el negocio |
|---|---|---|
| 1 | Cada orden se transcribe a mano al sistema | Tiempo perdido y errores de captura |
| 2 | Etiqueta del diseñador y hoja del pintor se arman manualmente | Trabajo repetido en cada orden |
| 3 | El flujo de etapas se aplica igual a todos los dealers, aunque no todos lo necesiten | Pasos innecesarios que frenan la producción |
| 4 | El pago al pintor se calcula con calculadora pieza por pieza | Errores y discusiones a fin de mes |
| 5 | El estado de pago de cada dealer se lleva de memoria o en Excel | Falta de visibilidad sobre cuentas por cobrar |
| 6 | Los instaladores en obra no tienen un sistema común | Fotos sueltas por WhatsApp, papeles que se pierden |
| 7 | La interfaz actual de Odoo es percibida como "complicada" | El equipo evita entrar al sistema |

---

## 2. Solución propuesta

### 2.1 Plataforma elegida

La base del sistema es **Odoo 17 en su versión Community** — una plataforma
sólida y open source, que ya viene con todo lo esencial para operar:
clientes, productos, pedidos, inventario, contabilidad básica, tienda online,
gestión de proyectos y portal para usuarios externos. No tiene costo de
licencia.

Sobre esa base agregamos una **personalización propia para Indigo Decors**
que adapta la herramienta al flujo real del taller: las pantallas que ve
cada rol, los documentos que se imprimen, el cálculo de pagos a contratistas
y la lógica de etapas configurables por dealer.

| Componente | Qué aporta |
|---|---|
| Odoo 17 Community | Plataforma base, sin costo de licencia |
| Tienda online (Website + eCommerce) | Catálogo, carrito y cuenta de dealer — totalmente personalizable visualmente |
| Módulo de producción a medida | Tablero por etapas, fichas, etiquetas, hoja del pintor, liquidaciones |
| Acceso móvil para instaladores | Vista web optimizada para celular, se abre desde el navegador y puede instalarse como ícono en la pantalla de inicio. Sin app que publicar en tiendas y sin licencia adicional |
| Hosting | Servidor VPS dedicado en Hostinger (plan KVM 2: 2 vCPU, 8 GB RAM, 100 GB NVMe, 8 TB de tráfico) |
| Mantenimiento y respaldos | Respaldos automáticos + revisión periódica (opcional) |

> **¿Por qué no la versión Enterprise de Odoo?** Las funciones que Enterprise
> agrega encima de Community no son críticas para este flujo, y su costo es
> recurrente (licencia mensual por usuario). Ese presupuesto rinde mucho más
> invertido en la personalización del primer año.

### 2.2 Otras alternativas evaluadas

| Alternativa considerada | Por qué se descartó |
|---|---|
| Construir todo desde cero (WooCommerce + aplicación a medida) | Implicaría reescribir funciones que Odoo ya trae resueltas (gestión de tareas, kanban, adjuntos, portal). Más meses de desarrollo y mantenimiento permanente, sin un beneficio claro |
| WooCommerce + plugins externos | Depender de varios plugins de terceros genera fricción y limita lo que se puede personalizar cuando el negocio crece |
| Seguir con la instancia Odoo actual sin personalización | Mantendría todos los dolores actuales: documentos a mano, sin liquidación automática y sin flujo adaptado al dealer |

---

## 3. Qué incluye la personalización para Indigo

Esta sección describe el **paquete base** que se entrega como parte del
proyecto. Cada bloque está pensado para resolver un dolor concreto del taller.

> El alcance aquí descrito es el mínimo acordado. Cualquier ajuste, pantalla
> extra o automatización adicional que surja durante el proyecto se cotiza
> aparte, en función del tiempo real que requiera.

### A. Captura rápida de orden
Una pantalla pensada para que cargar una orden por WhatsApp o papel tome
segundos: cliente, dealer, código de diseño, tipo de puerta, color, medidas,
fotos del contrato. El sistema autocompleta el diseño desde el catálogo y
calcula automáticamente el área y el precio al dealer.

### B. Tablero visual de producción
Un tablero por etapas (al estilo "tarjetas que se mueven de columna en
columna") que muestra en qué punto está cada orden. Las 13 etapas son
configurables: las opcionales (confirmación de diseño, medición) **solo
aparecen para los dealers que efectivamente las usan**. Incluye filtros por
dealer, responsable y urgencia, y la vista agrupada por dealer que pidió
Majela.

### C. Panel para configurar el flujo por dealer
Una pantalla donde Administración activa o desactiva etapas opcionales por
cada dealer, **sin necesidad de un programador**. El cambio se refleja al
instante en el tablero.

### D. Tareas dentro de cada orden
Cada orden puede dividirse en tareas asignadas a distintos responsables
(medición, corte, pintura, instalación). Cada tarea lleva su asignado,
plazo, estado, notas y fotos.

### E. Documentos automáticos (los 3 que hoy se hacen a mano)
1. **Ficha de Orden** — imprimible y enviable por correo con un clic
2. **Etiqueta del Diseñador** — formato para impresora térmica, con código
   QR opcional que linkea a la orden. Incluye cliente, dealer, medidas,
   tipo de puerta–color–vidrio, número de orden, piezas y código de diseño
3. **Hoja del Pintor** — tabla con compañía, número de orden, cliente,
   color, tipo de puerta, área (SQF), tarifa y total. El total se calcula
   automáticamente

### F. Liquidación de contratistas
El sistema calcula solo cuánto se le debe al pintor, al instalador y a otros
contratistas, según el área (SQF) o las piezas trabajadas en cada período
(semanal, quincenal o mensual, configurable). Genera un PDF de liquidación
y registra los pagos realizados.

### G. Acceso móvil para instaladores
Una vista simplificada pensada para celular, con "mis tareas de hoy", botón
de cámara para subir fotos de obra y botón para marcar la tarea como
completada.

**Aclaración importante sobre cómo funciona este acceso móvil:**
No se trata de una aplicación nativa publicada en Play Store o App Store.
El instalador entra desde el navegador del celular (Chrome / Safari) a una
dirección propia del taller, con su usuario y contraseña, y ve únicamente
las tareas que le fueron asignadas. La pantalla está diseñada para verse y
operarse cómodamente desde el teléfono.

Adicionalmente, desde el mismo navegador el instalador puede usar la opción
"agregar a pantalla de inicio" y obtener un **ícono en su celular** que abre
la herramienta en pantalla completa — visualmente se comporta como una app,
sin necesidad de descargarla de ninguna tienda y sin actualizaciones
manuales.

**Ventajas de este enfoque:**
- No tiene costo de licencia adicional (los instaladores entran como
  usuarios de tipo portal, incluidos sin costo en Odoo Community)
- No hay que publicar ni mantener una app en tiendas (Apple / Google)
- Las mejoras y cambios se reflejan al instante, sin tener que actualizar
  nada en cada celular

**Cuándo haría falta una app nativa de verdad** (no incluida en esta
propuesta, se cotizaría aparte): si en el futuro se necesitara trabajar
sin conexión a internet, recibir notificaciones push complejas o usar
funciones específicas del celular (GPS continuo, bluetooth, etc.).

### H. Vista de dealers (mini-CRM)
Una ficha por cada dealer con su información, tarifa, condiciones de pago,
historial de órdenes y, sobre todo, **deuda pendiente en vivo**.

### I. Roles y permisos
| Rol | Qué ve / qué puede hacer |
|---|---|
| Administración (dueño) | Acceso total al sistema |
| Majela (confirmación / seguimiento) | Captura, tablero completo, comentarios, dealers |
| Javier (medición / instalación) | Sus tareas + acceso móvil + fotos |
| Diseñador | Solo etapa de digitalización + sus tareas |
| CNC / Pintor | Solo las etapas que les corresponden |
| Instalador externo | Acceso móvil, solo sus tareas asignadas |

### J. Tienda online personalizable
La tienda actual de Odoo queda totalmente editable en lo visual (colores,
logo, tipografías, layout, páginas y bloques de contenido) desde el editor
incluido en Community. Si el cliente quiere un rediseño visual completo de
la tienda, se cotiza aparte como un módulo de diseño adicional.

---

## 4. Migración desde Odoo actual

1. Acceso de administrador a la instancia Odoo actual del cliente
   (URL exacta a confirmar con el cliente al inicio del proyecto)
2. Auditoría de qué datos conservar: clientes, dealers, catálogo de productos,
   órdenes históricas, facturas, contactos
3. Export → transformación → import en la nueva instancia con el módulo
   `indigo_decors` instalado
4. Convivencia 30 días: ambas instancias activas, congelar la vieja
5. Cierre de la instancia anterior

---

## 5. Cronograma estimado

El proyecto se entrega por fases, con visibilidad al cliente en cada cierre.
Los tiempos son estimados de referencia: el plazo final depende del nivel
de personalización que se acuerde en cada fase y de la velocidad de
respuesta del cliente para validar entregables.

| Fase | Plazo estimado | Qué se entrega |
|---|---|---|
| 1 — Puesta en marcha y análisis fino | ~1 semana | Servidor Odoo Community listo, base del proyecto configurada |
| 2 — Modelo de datos y flujo configurable | ~2 semanas | Dealers, órdenes, etapas y panel de configuración funcionando |
| 3 — Documentos automáticos | ~2 semanas | Ficha de orden, etiqueta del diseñador y hoja del pintor listas |
| 4 — Tareas y acceso móvil de instaladores | ~2 semanas | Tablero por etapas y vista móvil operativos |
| 5 — Liquidación a contratistas y vista de dealers | ~1–2 semanas | Cálculo automático de pagos + ficha de dealers |
| 6 — Migración de datos y capacitación | ~1–2 semanas | Datos pasados desde la instancia actual + capacitación al equipo |
| 7 — Acompañamiento post-arranque | ~2 semanas | Soporte intensivo el primer mes en producción |
| **Plazo total estimado** | **≈ 10–14 semanas** | Sistema en producción |

> Estos plazos asumen el alcance base descrito en §3. Si durante el proyecto
> se suman pantallas extras, integraciones o ajustes adicionales, el plazo
> se reajusta junto con el cliente antes de avanzar.

---

## 6. Costos

### 6.1 Costos fijos de plataforma
| Concepto | Costo |
|---|---|
| Licencia Odoo Community | **$0** (open source) |
| Hosting — Hostinger VPS **KVM 2** (2 vCPU, 8 GB RAM, 100 GB NVMe, 8 TB tráfico) | **$9.99 / mes** el primer período (precio promocional), luego **$16.99 / mes** en la renovación |
| Dominio + certificado SSL | aprox. **$15 / año** (SSL gratuito disponible) |

### 6.2 Desarrollo de la personalización

El paquete base descrito en §3 se entrega por un **monto cerrado de
USD 2,000**, que cubre todo el alcance detallado en esta propuesta:
puesta en marcha, modelo de datos, flujo configurable por dealer,
documentos automáticos, tareas y acceso móvil, liquidación a contratistas,
ficha de dealers, migración de datos, capacitación al equipo y
acompañamiento post-arranque.

> **Importante sobre el costo final:** los **USD 2,000** cubren el paquete
> base descrito en esta propuesta. Si durante el proyecto el cliente
> solicita personalizaciones adicionales (más pantallas, ajustes de
> diseño en la tienda, integraciones con terceros, automatizaciones
> específicas, reportes extras, etc.), se cotizan por separado en función
> del tiempo real de desarrollo que requieran. Cada solicitud se estima y
> se aprueba **antes** de ejecutarla: el cliente siempre sabe qué costo
> asume antes de avanzar.

### 6.3 Mantenimiento posterior (opcional)
- **Pack mensual de horas** para mejoras, ajustes y soporte continuo
- **Actualización anual de versión de Odoo** (cuando salga la versión
  nueva): se estima por separado según los cambios necesarios para
  adaptar la personalización

---

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Falta de desarrolladores Odoo en el mercado local | Documentar el módulo y publicar README; el código es Python estándar |
| Cada upgrade anual de Odoo rompe módulos custom | Acotar el módulo a lo mínimo necesario; suscripción de mantenimiento |
| El equipo del taller resiste cambiar de sistema | Capacitación + hipercare de 30 días + UX simplificada por rol |
| Migración de datos pierde información | Convivencia 30 días con la instancia vieja, sin borrar nada |
| Limitaciones de portal en Community (vs Enterprise) | Para casos puntuales (firma digital, app móvil offline), evaluar plugin OCA antes de saltar a Enterprise |

---

## 8. Validación previa al arranque — preguntas pendientes al cliente

> El cuestionario enviado al cliente **sigue pendiente de respuesta**. Antes
> de firmar contrato, conviene cerrar estos puntos para ajustar alcance y costos:

1. Volumen de órdenes por semana/mes (impacta dimensionamiento del VPS)
2. ¿Una orden trae varias piezas o una sola?
3. ¿Una orden puede regresar a etapas anteriores?
4. ¿Necesitan estados "En espera / Cancelada / Pausada"?
5. ¿Una etapa la trabaja una persona o varias?
6. Notificaciones: ¿sistema, correo, WhatsApp?
7. Medida exacta de la etiqueta y modelo de impresora térmica
8. ¿Agregar código de barras / QR a la etiqueta?
9. ¿Otros documentos manuales no listados?
10. Confirmar tarifa del pintor (¿SQF × $8 fijo?)
11. ¿La tarifa varía por color / tipo / dealer?
12. ¿Otros contratistas pagados por SQF o pieza? Tarifas
13. Frecuencia de liquidación (semanal / quincenal / mensual)
14. Lista oficial completa de códigos de diseño (catálogo 2026 + anteriores)
15. Precio al dealer: ¿por SQF? ¿igual para todos o por dealer?
16. Acceso admin a Odoo actual y qué datos conservar
17. Dispositivos del equipo (PC / móvil), dominio / hosting actual

---

## 9. Próximos pasos

1. **Cliente:** responder el cuestionario de la §8
2. **Cliente:** dar acceso de auditoría a la instancia Odoo actual
3. **Nosotros:** cerrar alcance fino y emitir cotización en firme
4. **Nosotros:** plan de migración detallado

---

*Documento vivo — se actualizará tras la respuesta del cuestionario y la
auditoría de la instancia Odoo actual.*
