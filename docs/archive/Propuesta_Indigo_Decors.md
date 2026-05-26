# Propuesta de Servicios

## Sistema de Gestión de Producción
### Indigo Decors · Impact Door Decoration

---

**Preparada para:** Majela — Indigo Decors
**Preparada por:** Luis Bencomo · `lbencomo94@gmail.com`
**Fecha:** 22 de mayo de 2026
**Versión:** 1.0
**Validez de la oferta:** 30 días

---

\newpage

## Carta de presentación

Majela,

Después de revisar el material que compartiste — las órdenes que llegan por
WhatsApp, las hojas de papel de Lock Tight, las etiquetas que armas a mano
para el diseñador y la hoja del pintor — quedó claro que el cuello de botella
de Indigo no es el taller, es la **administración de cada orden**: información
que se escribe varias veces, documentos que se hacen a mano y un equipo que
trabaja con herramientas que no fueron pensadas para ustedes.

Esta propuesta plantea un sistema que **automatiza ese trabajo** y deja a
cada persona del equipo enfocada en lo suyo: que Javier solo vea lo que tiene
que medir e instalar, que el pintor reciba su hoja impresa, que el diseñador
tenga su etiqueta, que vos veas el estado real de cada orden de un vistazo,
y que la administración cobre y pague sin sorpresas.

Quedo a tu disposición para cualquier ajuste de alcance o conversar los puntos
que consideres.

Un saludo,
**Luis Bencomo**

---

\newpage

## 1. Resumen ejecutivo

| | |
|---|---|
| **Qué proponemos** | Un sistema de gestión de producción a medida para Indigo Decors |
| **Sobre qué se construye** | Odoo 17 Community (open source, sin costo de licencia) + un módulo a medida diseñado exclusivamente para el flujo de Indigo |
| **Plazo de implementación** | 12 semanas (aproximadamente 3 meses) |
| **Inversión estimada** | USD 9,000 – 13,500 (rango sujeto a alcance final tras cuestionario de levantamiento) |
| **Modelo de trabajo** | Por fases con entregables verificables al final de cada una |
| **Garantía** | 30 días de soporte intensivo post-puesta en producción incluidos |

### Lo que resuelve

| Hoy | Con el sistema |
|---|---|
| Las órdenes se transcriben varias veces (web, WhatsApp, papel → Odoo) | Una sola carga; toda la información viaja con la orden |
| La etiqueta del diseñador y la hoja del pintor se hacen a mano | Se imprimen con un clic desde la orden |
| Cada dealer pasa por las mismas 13 etapas aunque no apliquen | Cada dealer tiene su propio flujo, configurable sin programar |
| El cálculo de pago al pintor sale con calculadora | El sistema lo calcula y arma la liquidación lista para firmar |
| El estado de pago de cada dealer está en cabeza o en Excel | Pantalla con deuda en vivo por dealer |
| Los instaladores reportan por WhatsApp y suben fotos sueltas | Portal móvil con sus tareas del día, cámara y "marcar hecho" |
| La pantalla actual de Odoo es de ERP genérico | Pantallas diseñadas a medida para Indigo, simples y al grano |

---

\newpage

## 2. Diagnóstico del flujo actual

A partir de las capturas, conversaciones y muestras de documentos que
compartiste, el flujo de Indigo hoy es:

```
Orden entra (web / WhatsApp / papel)
      ↓
Confirmación con cliente  ──┐
Medición en obra            │  (a veces aplica, depende del dealer)
Digitalización del diseño ──┘
      ↓
Corte CNC / Router
      ↓
Pintura
      ↓
Programación e instalación
      ↓
Facturación y pagos a contratistas
```

### Cómo llegan las órdenes hoy
- **Portal web** — los dealers compran logueados (Odoo eCommerce actual)
- **WhatsApp** — Majela transcribe a mano al sistema
- **Papel** — "Quote Items" de Lock Tight con anotaciones manuscritas

Ningún dealer se integra por API: **toda la entrada hoy es manual**, con el
costo de tiempo y los errores que eso implica.

### Documentos que hoy se hacen a mano
1. **Ficha de orden** — se imprime y se envía por correo
2. **Etiqueta del diseñador** — se imprime y se pega detrás de cada pieza
   cortada. Lleva cliente, dealer, medidas, tipo de puerta, color, vidrio,
   N° de orden, cantidad de piezas, código de diseño
3. **Hoja del pintor** — tabla con dealer, orden, cliente, color, tipo,
   SQF, tarifa y total (SQF × tarifa)

---

\newpage

## 3. La solución

### 3.1 Visión general

Un sistema corriendo sobre **Odoo 17 Community** (la versión gratuita y open
source de Odoo) extendido con un **módulo a medida** que modela exactamente
el negocio de Indigo. La diferencia con la instancia Odoo que usaron antes:

- **Pantallas a medida** para Indigo — no la interfaz genérica de Odoo
- **Cero costo de licencia** (Community vs Enterprise)
- **Flujo configurable por dealer** sin necesidad de programar
- **Documentos generados automáticamente** desde la orden
- **Portal móvil propio** para Javier y los instaladores

### 3.2 Lo que va a tener Indigo

#### A · Captura rápida de orden
Una sola pantalla con todos los campos que hoy se escriben a mano (cliente,
dealer, código de diseño, tipo de puerta, color, vidrio, SQF, piezas,
referencia, fotos del contrato). Validación en vivo y autocompletado desde
el catálogo de diseños.

#### B · Tablero de producción (Kanban)
Las 13 etapas del flujo en columnas. Las órdenes se mueven con drag & drop.
Las etapas opcionales (confirmación de diseño, medición) **solo aparecen
para los dealers que las usan** — Web Indigo, por ejemplo, ve un flujo más
corto que Lock Tight.

Filtros por dealer, asignado, urgencia. Vista agrupada por compañía origen
(Lock Tight / USA Windows / Safeguard) — como pediste en el WhatsApp.

#### C · Configurador de flujo por dealer (sin programar)
Una pantalla donde activás o desactivás las etapas opcionales por cada
dealer. Lo cambias hoy y mañana ya aplica al tablero. **No requiere
desarrollador para cada cambio.**

#### D · Detalle de orden
Toda la información de la orden en una vista: datos, etapa actual,
historial, tareas asignadas, fotos (contrato, medidas, avance, instalada),
comentarios del equipo, documentos imprimibles.

#### E · Documentos imprimibles
Generados automáticamente desde la orden, sin reescribir nada:
- **Ficha de orden** (PDF)
- **Etiqueta del diseñador** (impresora térmica, con QR opcional)
- **Hoja del pintor** (PDF con cálculo de tarifa)
- **Liquidación de contratistas** (período, total, firma)

#### F · Liquidación a contratistas
El sistema calcula automáticamente:
- Al pintor: suma SQF de las órdenes pintadas × tarifa
- Al instalador: por puerta instalada × tarifa (variable por tipo)

Período configurable (semanal / quincenal / mensual). PDF firmable. Marca
de pago y historial por persona.

#### G · Portal del instalador (móvil)
Javier y otros instaladores entran desde el celular y ven solo:
- Sus tareas del día con dirección y teléfono del cliente
- Botón de cámara para subir fotos
- Botón "marcar hecho"

Funciona en cualquier teléfono — no hay que instalar nada.

#### H · Mini-CRM de dealers
Ficha por dealer con contacto, dirección, tarifa por SQF, condiciones
de pago, notas internas. Pantalla con KPIs en vivo:
- Órdenes totales del dealer
- Facturación estimada
- **Deuda pendiente de cobro**

#### I · Roles y permisos
Cada persona del equipo entra y ve solo lo que le corresponde:

| Persona | Qué ve |
|---|---|
| Administración (dueño) | Todo |
| Majela | Captura, kanban completo, comentarios, dealers, reportes |
| Javier | Sus tareas, portal móvil, fotos |
| Diseñador | Etapa de digitalización + sus tareas |
| CNC / Pintor | Sus etapas + sus tareas |
| Instalador externo | Portal móvil con sus tareas |

---

\newpage

## 4. Prototipo de UX disponible

Junto a esta propuesta podemos compartir un **prototipo navegable** de las
pantallas custom (corre en cualquier navegador, no requiere instalación).
Sirve para que valides **cómo se va a ver y comportar** el sistema antes de
empezar a programar — y para hacer ajustes con costo cero.

El prototipo incluye:
- Tablero kanban con etapas configurables
- Captura de orden
- Detalle de orden con tareas, fotos, comentarios y documentos
- Configurador de flujo
- Catálogo de diseños
- Mini-CRM de dealers
- Portal móvil del instalador

> *Avisame cuando lo quieras ver y te lo paso.*

---

\newpage

## 5. Plan de trabajo

| Fase | Duración | Entregable verificable |
|:--:|:--:|---|
| 1 | 1 semana | Servidor Odoo Community 17 levantado, módulo base instalado |
| 2 | 2 semanas | Modelos de datos + tablero kanban + configurador de flujo por dealer |
| 3 | 2 semanas | Documentos imprimibles: ficha, etiqueta del diseñador, hoja del pintor |
| 4 | 2 semanas | Tareas dentro de la orden + portal móvil del instalador |
| 5 | 1.5 semanas | Liquidación de contratistas + mini-CRM de dealers |
| 6 | 1.5 semanas | Migración de datos + capacitación del equipo |
| 7 | 2 semanas | **Hipercare**: soporte intensivo durante el primer mes en producción |
| **TOTAL** | **≈ 12 semanas** | Sistema en producción y equipo capacitado |

### Modalidad de trabajo
- Revisión semanal contigo (15–30 min) para mostrar avance
- Entregables verificables al cierre de cada fase
- Cambios de alcance acordados por escrito antes de ejecutarse

---

\newpage

## 6. Inversión

### 6.1 Desarrollo del sistema

| | Mínimo | Máximo |
|---|---:|---:|
| Desarrollo a medida (12 semanas, ~260 horas) | **USD 9,000** | **USD 13,500** |

El rango contempla las variables del cuestionario de levantamiento
(sección 9). Una vez resuelto, fijamos el precio en firme.

**Forma de pago propuesta:** 30% al firmar · 40% al cierre de la fase 4
· 30% al pasar a producción (fase 7).

### 6.2 Costos recurrentes (no incluidos en lo anterior)

| Concepto | Costo aproximado |
|---|---|
| Licencia Odoo Community | **USD 0** (gratis) |
| Hosting VPS (4 GB RAM / 80 GB SSD) | USD 25 – 40 / mes |
| Dominio + SSL | USD 15 / año (o gratis con Let's Encrypt) |
| **Total recurrente estimado** | **~USD 350 – 500 / año** |

### 6.3 Mantenimiento posterior (opcional)
- Pack de horas mensuales para mejoras, bugs o nuevos requerimientos
- Migración anual de versión de Odoo: cotizada aparte cuando aplique
- Tarifa preferencial para clientes con sistema implementado por nosotros

### 6.4 Lo que NO está incluido (transparencia)
- Licencias o módulos pagos de terceros que se decidan agregar más adelante
- Integraciones a sistemas externos no listadas en esta propuesta
- Diseño gráfico o branding del portal web (si se quiere rediseño completo)
- Compra de hardware (impresora térmica, scanner de QR, etc.)

---

\newpage

## 7. Garantías y soporte

- **30 días de hipercare** post-puesta en producción incluidos: corrección
  inmediata de cualquier error funcional y ajustes menores sin costo
- **Garantía de 90 días** sobre el código entregado: cualquier defecto
  reproducible se corrige sin costo
- **Código entregado** al cliente — Indigo es dueña del módulo a medida
  y puede contratar a cualquier desarrollador Odoo para futuros cambios
- **Documentación técnica básica** del módulo a medida
- **Manual de usuario** para el equipo del taller

---

\newpage

## 8. Cronograma propuesto

| Hito | Fecha tentativa* |
|---|---|
| Devolución del cuestionario por parte del cliente | Semana 0 |
| Auditoría de datos en instancia Odoo actual | Semana 0 |
| Cotización en firme y firma de contrato | Semana 1 |
| Arranque de desarrollo | Semana 2 |
| Sistema en producción | Semana 14 |
| Cierre de hipercare | Semana 16 |

*Las fechas se anclan a la firma del contrato.

---

\newpage

## 9. Próximos pasos

Para avanzar a una cotización en firme y arrancar, necesitamos:

1. **Responder el cuestionario adjunto** (sección 10) — son 18 preguntas
   cortas que cierran el alcance fino y el precio
2. **Acceso de auditoría** a la instancia Odoo actual para evaluar qué
   datos migrar (URL a confirmar)
3. **Reunión de 30 minutos** para resolver dudas de la propuesta y, si
   estás de acuerdo, ver el prototipo de UX

Cuando tengamos los puntos 1 y 2 resueltos, entregamos:
- Cotización en firme con precio único
- Contrato y forma de pago
- Calendario de fases con fechas reales

---

\newpage

## 10. Cuestionario de levantamiento

Para cerrar el alcance y el precio final.

### Sobre el negocio
1. ¿Cuál es la lista completa de dealers con los que trabajan hoy?
2. ¿Cuántas órdenes manejan en promedio por semana / mes?
3. ¿Una orden trae varias piezas o una sola?
4. ¿Puede una orden regresar a etapas anteriores?
5. ¿Necesitan estados especiales (en espera / cancelada / pausada)?
6. Cada etapa: ¿la trabaja una persona o varias?

### Sobre comunicación y notificaciones
7. ¿Quieren notificaciones automáticas? Si sí, ¿dónde — sistema, correo,
   WhatsApp?

### Sobre documentos
8. Medida exacta de la etiqueta del diseñador y modelo de impresora
9. ¿Quieren agregar código de barras o QR a la etiqueta?
10. ¿Hay otros documentos manuales que no estén listados?

### Sobre pagos y tarifas
11. Confirmar tarifa del pintor: ¿SQF × $8 fijo, o varía?
12. ¿La tarifa varía por color / tipo de puerta / dealer?
13. ¿Hay otros contratistas pagados por SQF o por pieza? ¿Cuáles y a qué tarifa?
14. ¿Con qué frecuencia liquidan a los contratistas?

### Sobre el catálogo
15. ¿Pueden compartir la lista oficial completa de códigos de diseño?

### Sobre precios a dealers
16. ¿Cobran por SQF? ¿El precio es el mismo para todos o varía por dealer?

### Sobre el sistema actual
17. Acceso admin a la instancia Odoo actual y qué datos quieren conservar

### Sobre infraestructura
18. ¿Qué dispositivos usa el equipo (PC, móvil)? ¿Tienen preferencia de
    dominio / hosting? ¿Quieren explorar integración con WhatsApp?

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
