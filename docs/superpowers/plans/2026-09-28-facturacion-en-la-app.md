# Facturar desde la app — plan

**Fecha:** 2026-09-28 · **Pedido por:** Majela (WhatsApp, 28-sep) · **Estado:** Fases 1 y 2 hechas en local (ver §8); nada desplegado.

**Objetivo:** que Indigo deje de hacer las facturas en QuickBooks y las haga
desde la app, a partir de la orden. Y, detrás, registrar gastos y mano de
obra para saber cuánto cuesta hacer una puerta y cuánto deja.

---

## 1. Lo que pidió Majela, agrupado

| # | Pedido | Dónde cae |
|---|---|---|
| 1 | Factura con el formato de QuickBooks, generada desde la orden | Fase 2 |
| 2 | Impuesto de Florida 7 % sobre las puertas; el recargo de instalación fuera de rango **no** lleva impuesto | Fase 1 |
| 3 | Recargo de instalación por región: A 0-35 mi, B 35-45, C 45-90, D 90-120 | Fase 1 |
| 4 | Elegir qué dato va en la descripción de cada puerta (cliente, cliente + dirección, «REF: PO …») | Fase 2 |
| 5 | Un dealer necesita el PO del cliente en la factura | Fase 2 (plantilla por dealer) |
| 6 | La factura lleva adjuntas las fotos de la instalación y se envía por correo a varios destinatarios | Fase 2 |
| 7 | El logo sale con fondo negro: que la factura se vea como la de QuickBooks | Fase 1 |
| 8 | Una etapa/pantalla de facturación con resumen por rango de fechas | Fase 2 |
| 9 | Pagos: registrar lo cobrado, saldo abierto y vencido por dealer (como la ficha de cliente de QuickBooks) | Fase 2 |
| 10 | Gastos: proveedor, monto, tipo; idealmente foto del recibo y que se llene solo | Fase 3 |
| 11 | Pagos de mano de obra entrados a mano | Fase 3 |
| 12 | Segundo pintor en el taller: «Paint Michel» a 8 $/sqf y «Paint Indigo» a 4 $/sqf | Fase 3 |
| 13 | Incidencias en la orden, con el costo del error (p. ej. repintar porque el instalador se equivocó) | Fase 4 |
| 14 | Reportes: pérdidas y ganancias, gasto por sqf, costo por puerta contra precio de venta | Fase 5 |

## 2. Lo que dicen las facturas de ejemplo (carpeta `Factura`)

- **Numeración** correlativa de QuickBooks (1009 … 1363 en los ejemplos y capturas).
- **Condiciones:** «Due on receipt»; fecha de vencimiento = fecha de factura.
- **Líneas de puerta:** producto «DESIGN SINGLE DOOR» / «DESIGN DOUBLE DOOR»
  (en QuickBooks está escrito «DESING»), cantidad 1, precio fijo por tipo de
  puerta, y en la descripción el dato del cliente.
- **Línea de instalación:** siempre aparece, aunque sea 0 $ en la región A.
- **Varias órdenes en una factura:** un ejemplo junta dos puertas de clientes
  distintos más una línea libre («production · Display»). Hay que permitir
  agrupar y añadir líneas libres.
- **Impuesto:** 7 % sobre el subtotal de puertas. Uno de los ejemplos no
  lleva impuesto: hay dealers exentos, o esa línea libre no tributa. Pendiente de confirmar.
- **Fotos:** un ejemplo trae dos páginas extra con fotos de la puerta.
- **Pago en línea:** «View and pay» con tarjeta es de QuickBooks Payments.

## 3. Lo que hay hoy en el sistema (medido en producción, 28-sep)

- **Contabilidad de Odoo instalada pero vacía:** 0 plan de cuentas, 0
  impuestos, 0 diarios, 0 facturas. Hay que configurarla desde cero.
- **Empresa en Odoo:** «Indigo Publicity Corp.». Las facturas de QuickBooks
  salen como **«Indigo Decors LLC»** con otro correo. **Hay que decidir cuál
  es la razón social que factura** antes de emitir nada.
- **Precio por puerta** ya existe (pantalla Pricing, por tipo de puerta y
  con precio especial por diseño) y coincide con los ejemplos.
- **Recargo de instalación:** el código lo pone a 0 porque «la instalación
  va incluida». Las facturas cobran B/C/D. Además hay **dos tablas que no
  coinciden**: zonas por ZIP (0 / 35 / 70 / 150 $) y rangos por millas
  (0-35 / 35-45 / 45-90 / 90-120 / 120+), que son exactamente las regiones de
  la factura pero sin precio.
- **Pagos:** la orden ya tiene estado de pago (pagado / parcial / sin pagar),
  fecha de pago y un asistente para registrar lo cobrado. Unas 200 órdenes
  están en «Invoiced / Paid». Hoy es un registro paralelo a QuickBooks.
- **PO del cliente:** relleno en ~75 % de las órdenes. La referencia del dealer, en ~20 %.
- **Incidencias:** existe el modelo (categoría, descripción, fotos), pero sin
  costo y **sin ningún registro**: solo se usa la casilla «incidence».
- **Pagos a contratistas:** 177 liquidaciones, todas de instaladores. El
  pago al pintor por sqf nunca se usó.
- **Pantalla Billing** de la app: lista «To invoice», «Outstanding» y
  liquidaciones, calculadas desde las órdenes. No genera facturas.

## 4. Decisión de arquitectura

**Recomendación: usar el módulo de facturación de Odoo (`account.move`), no
un modelo propio.** Ya está instalado y trae resuelto lo difícil:
numeración legal, impuestos, facturas parciales, pagos, saldo por cliente,
envío por correo con adjuntos y facturas de proveedor, que sirven para los gastos.
La app pone encima las pantallas simples, como ya hace con las órdenes.

Lo que Odoo Community **no** trae: el informe de pérdidas y ganancias (es de
Enterprise) y la lectura automática de recibos (servicio de pago). Los dos
se hacen en la app: el P&L se calcula sobre las facturas y los gastos, y el
recibo lo lee la IA como ya hace `create_order` con la hoja del dealer, con
confirmación humana.

**Alternativa descartada por ahora:** mandar las facturas a QuickBooks por
su API. Conserva a su contable tal cual, pero no resuelve el problema de acceso
de Majela ni el costo por puerta, y ata la app a otra plataforma. Se
retoma si el contable exige seguir en QuickBooks.

## 5. Fases

### Fase 0 — Decisiones (bloquea todo lo demás)

Preguntas para Majela y la dirección:

1. **Razón social que factura:** ¿Indigo Decors LLC o Indigo Publicity Corp.? Dirección, ZIP y correo exactos de la factura.
2. **QuickBooks:** ¿se deja de usar o convive? ¿Qué necesita su contable para la declaración del impuesto de ventas de Florida?
3. **Número de factura:** ¿seguimos la numeración de QuickBooks (siguiente después de la última emitida)?
4. **Impuesto:** 7 % en todas las puertas. ¿Qué dealers están exentos (certificado de reventa)? ¿Las líneas libres («Display», producción) tributan?
5. **Recargo de instalación:** ¿valen los de QuickBooks (A 0, B 35, C 70, D 120)? ¿Y más de 120 millas?
6. **Descripción por dealer:** para cada dealer, qué va en la línea de puerta (cliente · cliente + dirección · «REF: PO» + cliente + número de PO).
7. **Agrupar:** ¿una factura por orden, o varias órdenes del mismo dealer en una?
8. **Destinatarios:** correos de facturación de cada dealer (hoy 4 de 13 dealers no tienen correo).
9. **Pago con tarjeta en línea:** ¿hace falta ya? En Odoo se puede con Stripe, como fase aparte.
10. **Saldos abiertos de QuickBooks:** ¿se traen las facturas abiertas para que el saldo por dealer cuadre, o se cobran allí hasta cerrarlas?

### Fase 1 — Base contable (Odoo, sin pantallas nuevas)

- Plan de cuentas de EE. UU. (`l10n_us` / genérico), datos de la empresa y logo **en PNG con fondo transparente**, lo que arregla el fondo negro.
- Impuesto «FL Sales Tax 7 %» de venta, aplicado solo a los productos de puerta.
- Productos: Design Single Door, Design Double Door, Design Door with Sidelites (con impuesto); Installation Fee A-D (sin impuesto); Production / otros (línea libre).
- Precio del recargo en los **rangos por millas**, que es lo que ya calcula cada orden, y retirar el precio de las zonas por ZIP. Así hay una sola tabla.
- Diario de ventas con la numeración acordada. Plazo «Due on receipt».
- Plantilla PDF de factura que replica la de QuickBooks: cabecera, «Bill to / Ship to», detalles, líneas, subtotal, impuesto y total, más páginas de fotos al final.
- Datos del dealer: correos de facturación (varios), exento de impuesto sí/no, plantilla de descripción.

### Fase 2 — Facturar y cobrar desde la app

- **Pantalla «Invoicing»** (sustituye la lista «To invoice» de Billing): órdenes instaladas pendientes de facturar, agrupadas por dealer.
- **Crear factura:** se eligen una o varias órdenes del mismo dealer y el sistema propone las líneas. Una por puerta, con el producto según el tipo, el precio de la orden y la descripción según la plantilla del dealer. Añade el recargo según el rango de millas y deja añadir líneas libres. Se guarda en **borrador** para revisar.
- **Confirmar y enviar:** numera, genera el PDF con las fotos de instalación de esas órdenes y lo manda por correo a los destinatarios elegidos (varios). La orden pasa a «Invoiced».
- **Registrar pago:** total o parcial, fecha, forma (cheque, transferencia, Zelle, tarjeta) y referencia. El estado de pago de la orden se deduce de la factura en vez de escribirse a mano.
- **Lista de facturas** con filtro por rango de fechas, dealer y estado (abierta / pagada / vencida), y un **resumen del periodo**: facturado, cobrado, pendiente e impuesto.
- **Ficha de dealer** como la de QuickBooks: saldo abierto, vencido y movimientos (facturas y pagos).
- Herramienta MCP para facturar por conversación, con la misma vista previa y confirmación que las demás.

### Fase 3 — Gastos, mano de obra y pintura

- **Gastos** (facturas de proveedor en Odoo): proveedor, fecha, monto, tipo (materiales, gasolina, peajes, instaladores, pintura, otros) y foto del recibo. **Opcionalmente asignado a una orden**, para el costo por puerta.
- **Leer el recibo con IA:** se sube la foto y se proponen proveedor, fecha, monto y tipo. La persona confirma antes de guardar.
- **Mano de obra manual:** pago a una persona (instalador, ayudante) con fecha, monto y orden opcional. Las liquidaciones de instaladores que ya existen generan su gasto al liquidarse.
- **Dos pintores:** en la etapa de pintura se elige «Paint Michel» (8 $/sqf) o «Paint Indigo» (4 $/sqf, taller propio). El costo de pintura de la orden = sqf × tarifa del elegido, y la hoja del pintor se imprime por pintor.

### Fase 4 — Incidencias con costo

- En la orden, **registrar la incidencia**: tipo (medida, pintura, cliente, instalación, otro), qué pasó, fotos, responsable y **costo de rehacer**. Por ejemplo, «repintar 2 puertas» se calcula con los sqf × la tarifa del pintor, o se escribe el importe.
- La casilla «incidence» pasa a ser «tiene incidencias abiertas», y el costo suma al costo de la orden.

### Fase 5 — Reportes

- **Pérdidas y ganancias** por periodo: ingresos (facturas) menos gastos por tipo, menos mano de obra, pintura e incidencias.
- **Costo por puerta y por sqf:** por orden, dealer, tipo de puerta y mes, frente al precio de venta, con el margen.
- **Costo de errores:** incidencias por tipo y responsable.
- **Cartera:** saldo por dealer con antigüedad (0-30, 31-60, 61-90, +90).

## 6. Orden recomendado

La **Fase 0** se hace ya. Sin razón social ni numeración no se puede emitir
una factura legal. Después, las **Fases 1 y 2 juntas**, que son lo mínimo
para empezar a facturar. Conviene **un mes en paralelo** con QuickBooks,
facturando en la app y comparando. Luego las Fases 3 y 4, que alimentan los
reportes de la Fase 5.

## 7. Riesgos

- **Factura legal:** una factura emitida no se borra, solo se anula con nota de crédito. Se prueba todo en local y en borrador antes de emitir la primera real.
- **Contable externo:** si llevan los libros en QuickBooks, cambiar de sistema a mitad de año complica el cierre. Preguntar antes de la Fase 1.
- **Impuesto:** exenciones mal configuradas = impuesto cobrado de más o de menos. Validar con 3 facturas reales de QuickBooks antes de salir.
- **Datos:** 4 dealers sin correo y órdenes sin ZIP (sin rango de millas, luego sin recargo calculable). Hay que completarlos antes de facturar a esos dealers.
- **No tocar los avisos automáticos a dealers:** siguen desactivados por decisión del cliente. El envío de la factura es manual, desde el botón.

## 8. Hecho el 2026-09-28 (Fases 1 y 2, en local)

Decision del usuario ese dia: **la numeracion sigue la de QuickBooks** y las
preguntas de la Fase 0 se responden despues. Todo lo que dependia de ellas
quedo como ajuste editable en Settings → Invoicing con el valor de QuickBooks
por defecto.

- **Odoo** (`models/indigo_invoicing.py`): factura estandar de Odoo enlazada a
  las ordenes; servicio `indigo.billing` (rol oficina/gerente, sudo) para
  estado, configuracion, propuesta, borrador, emitir, PDF, enviar, cobrar,
  lista con resumen y ficha de dealer. Recargo por **rango de millas** con
  region A-D (0 / 35 / 70 / 120). Plantilla PDF identica a QuickBooks con el
  logo sobre blanco y una pagina por foto. 13 tests.
- **La configuracion contable no la hace el upgrade**: la lanza un gerente con
  el boton «Set up invoicing». Hasta entonces Billing sigue como antes.
- **App**: Billing agrupa por dealer y crea la factura; `/billing/invoices`
  (lista y resumen por fechas), `/billing/invoices/[id]` (PDF, emitir,
  enviar a varios correos, cobrar), `/billing/dealers/[id]` (saldo, vencido,
  movimientos y como se factura a ese dealer), Settings → Invoicing.
- **Supuestos a confirmar**: emisor «Indigo Decors LLC» y sus datos de
  QuickBooks; siguiente numero 1364; 7 %; nadie exento; descripcion «cliente -
  referencia» por defecto; el correo sale del servidor de Odoo con respuesta
  al correo del emisor.

**Para produccion:** subir los dos repos, actualizar el modulo, y que un
gerente ponga el siguiente numero real de QuickBooks y pulse «Set up
invoicing». Mientras QuickBooks siga emitiendo, mover ese numero para que no
se repitan.

## 9. Auditoria del 2026-09-28 y arreglos

Probado con datos en el Odoo local (transaccion deshecha). Arreglado, cada
punto con su test (`TestIndigoInvoicingAudit`):

1. Una orden podia facturarse dos veces: ahora solo cabe en una factura viva.
2. El 7 % quedaba como impuesto por defecto de la empresa y lo heredaba todo
   producto nuevo, incluido el que crea publicar un diseno en la tienda: la
   empresa se queda sin impuesto por defecto y los 15 % genericos se apagan.
3. No habia forma de anular: «Void» conserva el numero y devuelve las ordenes
   a «por facturar». Con pagos registrados no se permite desde la app.
4. Se aceptaban lineas de otras ordenes, adjuntos ajenos (bypass de acceso
   en sudo) y productos que no son de facturacion: rechazados.
5. Una factura emitida desde el backend hacia chocar la numeracion: la
   secuencia salta a lo ya usado.
6. `date_paid` de la orden era la fecha de hoy: ahora es la del ultimo pago.

Pendientes menores, sin arreglar: Cash IN / Outstanding / ingresos del tablero
siguen leyendo las ordenes y no las facturas; el Kanban, las pantallas de etapa
y el envio en bloque aun ofrecen el asistente viejo que marca una orden como
facturada y pagada sin factura (la ficha de la orden ya no, ver §10); el mensaje propio del correo no se
escapa; el aviso de «ya facturada» sale al editar el propio borrador; el resumen
de la lista cuenta como mucho 500 facturas; el dealer queda como seguidor de sus
facturas; verificar en copia de prod que el medio de pago «Submit Quote Request»
no cambia al recibir el diario del banco.

## 10. La ficha de la orden sabe de su factura (2026-09-28)

- Tarjeta «Invoice» (solo oficina y gerente): numero, estado, total y saldo,
  enlace a la factura y al PDF; las anuladas quedan listadas, atenuadas. Si la
  orden esta instalada y sin factura viva, boton «Create invoice» (misma regla
  que «To invoice»). Servicio: `indigo_billing_order_invoices`.
- «Next action»: con la facturacion activa, «Installed» ofrece «Create invoice»,
  un borrador ofrece «Open draft» y una factura abierta «Record payment» (sobre
  la factura). «Mark as Paid» y el asistente «Invoice and mark paid» solo quedan
  donde no hay factura en la app: antes de activarla y para ordenes facturadas
  en QuickBooks. Regla en `orderBillingNext` (indigo-next), con tests.
- Fila «Payment» (Unpaid / Partly paid / Paid) en el resumen de la orden.
- Historial de la orden: emitir, enviar, cobrar (tambien desde el backend) y
  anular dejan una linea con `_message_log`, que no notifica a nadie: los
  avisos al dealer siguen apagados (`TestIndigoInvoicingOrderPage`).
