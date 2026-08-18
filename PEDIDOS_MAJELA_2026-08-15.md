# Pedidos de Majela — 15 de agosto de 2026

Fuente: grupo de WhatsApp **ODOO/INDIGO**, 6 notas de voz (10 min) + 4 capturas.
Transcripción local con faster-whisper. Audios e imágenes en el scratchpad de la
sesión; capturas en `c:/Trabajo/_tools/evolution-wa/evo_media/`.

> **Nota sobre la transcripción.** El ASR mutiló vocabulario del negocio:
> "Escobar Fit" = **SQF**, "Cien-C" = **CNC**, "dile" = **dealer**.
> "PDE"/"PDF" es el documento que ella prepara para el diseñador (la etiqueta +
> el diseño) — **conviene confirmarlo con ella antes de implementar**, porque
> toda la propuesta de Digitalización gira alrededor de ese paso.

---

## 1. Digitalización — el SQF está en el paso equivocado

**El problema, en sus palabras:** en Digitalización conviven las puertas a las
que ya les hizo el documento para el diseñador y las que no. No las distingue.
Ya le pasó que **entró una puerta con un número viejo y no se dio cuenta**
porque quedó en la segunda hoja.

**Lo que pide:**
- **Sacar la entrada de SQF de Digitalización** y moverla a **CNC**.
- Cuando ella termina el documento y se lo manda al diseñador, la puerta
  **pasa automáticamente a CNC**.
- Así el estado se vuelve legible solo: lo que está en Digitalización **no**
  tiene el documento hecho; lo que está en CNC **sí**.

**Por qué importa:** hoy la etapa no informa nada. Con el cambio, la etapa misma
es la respuesta a "¿qué me falta?".

## 2. Digitalización — los tres contadores no se pueden alcanzar

Es lo que marcó en verde en la captura: `In Progress 0`, `Completed 0`,
`On Hold 0`, con `Ready to Digitalize 8`.

**Textual:** *"no tengo la opción de que entre una puerta y poner que está en
progreso, ni que fue completada, ni que está en hold"*.

Los números existen pero **no hay acción que mueva una orden a esos estados**.
Pide además un conteo del tipo *"de las 8, hiciste 6, te quedan 2"*, y sugiere
distinguir por color las que ya tienen el documento.

## 3. Instalaciones — separar "problema del dealer" de "problema del cliente"

Hay muchas puertas viejas sin agendar, y hoy todas se ven igual. Son **dos
causas distintas** y se resuelven con gente distinta:

| Causa | Quién lo destraba | Color que pide |
|---|---|---|
| El **dealer** tiene que arreglar algo antes | el dealer | **azul** |
| El **cliente** no está disponible / no pudo | el cliente | **naranja** |

Pide contadores arriba por categoría (*"problemas con el dealer: 7 puertas"*) y
que la distinción reemplace al actual "overdue / pending schedule", que mezcla
todo.

## 4. Instalaciones — agrupar por zona y por dirección

Ya usan rangos de distancia para cobrarle *overage* al cliente (35, 45 millas…).
Quiere lo mismo para **planificar**:

- Agrupar las puertas a instalar **por rango de distancia**.
- Y separar por **dirección**: 25 millas al sur ≠ 25 millas al norte.
  *"no voy a mandar al sur y al norte el mismo día"*.
- Objetivo explícito: que el instalador **no se traslade tanto** y bajar la
  cantidad de viajes.

La captura del mockup muestra 5 rangos: 0-35 / 35-45 / 45-90 / 90-120 / 120+.

## 5. Pantalla de instaladores — es para poder pagarles

El pedido más grande, y el que **cambia el modelo de pago**. Hoy el sistema paga
**$35 por puerta instalada**, y nada más.

Ella necesita **dos modalidades** según el día:

- **Pocas puertas** (ej. 2 en el día) → se paga un **básico diario**.
- **Muchas puertas** → se paga **por puerta**, que le sale menos.

Además necesita registrar:
- Si usó **vehículo de la compañía o el propio**.
- Un **selector de rango de fechas**, porque liquida semanas vencidas
  (lunes-jueves o lunes-viernes según haya trabajado).

**Textual:** *"basándome en esa información voy a pagar a Lázaro, o a Mandy"*.
O sea: esta pantalla no es un reporte, es el **instrumento de liquidación**.

## 6. Lo que ella misma pone después

Cierra diciendo que el resto es *"más ambicioso"* y puede esperar:
mandar mensaje automático al cliente desde la orden, avisos de correos
entrantes, y automatización con IA.

---

## Lectura

Los cinco pedidos son **de flujo de trabajo, no de IA**. Y los cinco vienen de
haber usado el sistema semanas y chocarse con lo mismo: el sistema le muestra
datos pero no le deja **actuar** sobre ellos ni **distinguir** lo que tiene que
distinguir para tomar la próxima decisión.

Dos son baratos y de alto impacto (2 y 3: acciones que faltan y separar dos
causas). Uno es de esfuerzo medio (1: mover el SQF de etapa). Dos son proyectos
(4 y 5: zonas por distancia/dirección, y el modelo de pago con dos modalidades).

**El 5 toca dinero** y contradice la regla vigente en `CLAUDE.md` ($35/puerta
fijo, confirmado por el cliente en su momento). Ese cambio hay que confirmarlo
explícitamente antes de tocar nada, incluidas las liquidaciones ya emitidas.
