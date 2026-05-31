# 🔐 Credenciales — Demo Indigo Decors

> **Sistema desplegado en**: http://2.25.137.220:8069
> **Última actualización**: 2026-05-31
> **Estado**: Producción VPS Hostinger + Coolify (datos demo, todos los emails/clientes son ficticios)

---

## 📌 Información importante para todos

- **Todas las passwords son temporales** — quien reciba sus credenciales debe **cambiarlas en el primer login** desde el avatar arriba a la derecha → **Preferences** → **Account Security** → **Change Password**.
- Los datos de las 12 órdenes activas, los homeowners (Andrea Vargas, Patricia Morales, etc.) y los precios son **ficticios para la demo** — los reales se cargan más adelante.
- **No mandar credenciales por canales públicos** (Discord/Slack abierto, foros). Usar email corporativo, WhatsApp privado o 1Password.

---

## 1. 👑 Administrador total (vos, Luis)

Quien tiene acceso a TODO: instalar módulos, configurar settings, ver/editar cualquier registro, deploys, etc.

```
URL       : http://2.25.137.220:8069/web/login
Email     : lbencomo94@gmail.com
Password  : demo2026
Nivel     : Administrator (base.group_system)
```

**Primeros 5 minutos al loguearte**:
1. Cambiar password (Preferences → Account Security)
2. Subir tu foto (Preferences) → aparece en notificaciones del chatter
3. Verificar `Settings → Companies → Indigo Publicity Corp` que muestre la dirección real (6752 NE 4th Avenue Miami FL 33148, +1 305 785-6666)

---

## 2. 👩‍💼 Majela — Gerente operativa

Confirma órdenes con el cliente, hace seguimiento, asigna a Javier / pintor / instalador. **Acceso de administrador total** (mismas perms que vos por ahora — se puede acotar después).

```
URL       : http://2.25.137.220:8069/web/login
Email     : majela@indigodecors.com
Password  : IndigoMajela2026!
Nivel     : Administrator
Idioma    : Español (es_ES)
Timezone  : America/New_York
```

**Qué tiene que probar Majela primero**:
- Menú **Indigo → Órdenes** → ver el Kanban de 13 etapas con 12 órdenes
- Abrir IND/2026/00010 → tab **Incidents** → ver el ajuste de medición que registró Javier
- Mover IND/2026/00009 desde "Design Confirmed" a "Measurement Pending" arrastrando el card
- Print → Etiqueta del diseñador / Hoja del pintor / Ficha de orden

---

## 3. 🛠️ Javier — Medición e instalación

Mide en sitio, sube fotos de contrato, mueve a "Measured". También participa en instalación.

```
URL       : http://2.25.137.220:8069/web/login
Email     : javier@indigodecors.com
Password  : IndigoJavier2026!
Nivel     : Internal user + Sales (All Documents)
Idioma    : Español
```

---

## 4. 🎨 Mario — Pintor

Pinta las piezas cortadas, mueve a "Ready for Installation" cuando termina.

```
URL       : http://2.25.137.220:8069/web/login
Email     : pintor@indigodecors.com
Password  : IndigoPintor2026!
Nivel     : Internal user + Sales (All Documents)
Idioma    : Español
```

---

## 5. 🔧 Carlos — Instalador

Recibe órdenes en su portal móvil para instalar en sitio, sube foto post-instalación.

```
URL       : http://2.25.137.220:8069/web/login
Email     : instalador@indigodecors.com
Password  : IndigoInstalador2026!
Nivel     : Internal user + Sales (All Documents)
Idioma    : Español
```

---

## 6. 🖌️ Pedro — Diseñador / CNC

Digitaliza el archivo, opera el router CNC.

```
URL       : http://2.25.137.220:8069/web/login
Email     : disenador@indigodecors.com
Password  : IndigoDisenador2026!
Nivel     : Internal user + Sales (All Documents)
Idioma    : Español
```

---

## 7. 🏢 Lock Tight — Dealer (acceso portal externo)

**Esto es lo que ve un dealer cliente desde su lado**. Solo ve SUS órdenes (filter por security rule), no ve backend admin ni datos de otros dealers.

```
URL       : http://2.25.137.220:8069/web/login
Email     : orders@locktightfl.com
Password  : LockTightDemo2026!
Nivel     : Portal (sin acceso al backend)
```

**Qué muestra al loguearse**:
- `/my` → My Account con 4 cards: Your Orders, Your Invoices, Connection & Security, **+ New order**
- `/my/orders` → tabla con las 6 órdenes de Lock Tight (Andrea Vargas, Karen O'Reilly, Sebastián Cortés, Patricia Morales, Michelle Kowalski, Federico Mancini)
- `/my/order/<id>` → detalle con botón **"Duplicate this order"** y formulario para subir comprobante de pago
- `/my/order/new` → formulario con **autocompletado de homeowners pasados** (escribir "Pa" → sugiere Patricia Morales y auto-llena phone/email/address)

**Features que va a notar**:
- Botón **Duplicate** en cada fila — clona todo (cliente, dirección, piezas, medidas), solo cambian lo que sea distinto
- Autocomplete de homeowners en formulario de nueva orden
- Dimensiones en formato pulgadas+octavos (`36 1/8`) — no decimales

---

## 📧 Templates de email para mandar al equipo

### Email para Majela

> **Asunto**: Acceso al sistema Indigo Decors
>
> Hola Majela,
>
> Te dejo el acceso al sistema de gestión de órdenes. Es una demo con datos ficticios para que te familiarices antes de cargar los reales.
>
> 🔗 **URL**: http://2.25.137.220:8069/web/login
> 📧 **Usuario**: majela@indigodecors.com
> 🔑 **Password (temporal)**: IndigoMajela2026!
>
> **Lo primero al entrar**:
> 1. Cambiá la password desde el avatar arriba a la derecha → Preferences → Change Password
> 2. Ve al menú **Indigo → Órdenes** para ver el tablero Kanban con las 13 etapas
> 3. Hay 12 órdenes de prueba distribuidas (incluyendo una "On Hold" y otra "Closed/Paid")
>
> Cualquier duda me decís.

### Email para Javier / Pintor / Instalador / Diseñador

> **Asunto**: Acceso al sistema Indigo Decors
>
> Hola [Nombre],
>
> Te dejo el acceso al sistema. Por ahora es modo demo con datos de prueba.
>
> 🔗 **URL**: http://2.25.137.220:8069/web/login
> 📧 **Usuario**: [tu-email]@indigodecors.com
> 🔑 **Password (temporal)**: [tu-password]
>
> **Primer paso**: cambiá la password desde el avatar arriba a la derecha → Preferences → Change Password.
>
> Vas a ver el menú **Indigo → Órdenes** con el tablero del taller. Las órdenes que te asignen las vas a recibir por email.

### Email para Lock Tight (dealer demo)

> **Asunto**: Demo del portal de dealer — Indigo Decors
>
> Hola,
>
> Te dejo un acceso temporal al portal de dealer del nuevo sistema de gestión que estamos armando con Indigo Decors. Es una demo con datos ficticios.
>
> 🔗 **URL**: http://2.25.137.220:8069/web/login
> 📧 **Usuario**: orders@locktightfl.com
> 🔑 **Password**: LockTightDemo2026!
>
> Cuando entres vas a ver:
> - Tu listado de órdenes activas (datos de prueba)
> - Un botón **"+ New order"** para crear una nueva — si ya pediste antes para un homeowner, escribir su nombre autocompleta dirección y teléfono
> - Un botón **"Duplicate"** en cada orden — útil si pedís repetidamente para el mismo desarrollo
>
> Cualquier feedback me decís — sobre todo si hay algo que te ahorraría más tiempo en tu día a día.

---

## 🛠️ Para administrar (vos)

### Crear más usuarios

Menú **Settings → Users & Companies → Users** → **+ New**.

Para usuarios de **portal de dealer**: marcar el partner como `Indigo Dealer` (tab Indigo Dealer en su contacto), luego usar el botón **"Crear acceso portal"** que aparece en la ficha del dealer.

### Reset password de un usuario

**Settings → Users → [usuario]** → click los 3 puntos arriba → **Reset Password** (manda email automático).

### Otros accesos relacionados (no son del Odoo)

| Servicio | URL | Para qué |
|---|---|---|
| Coolify panel | http://2.25.137.220:8000 | Deploys, logs, env vars, backups |
| GitHub repo | https://github.com/luisobr2/odoo-indigo | Código fuente |
| VPS SSH | `root@2.25.137.220` | Sólo emergencias / docker exec |

**Credenciales de Coolify, SSH y DB están en tu memoria persistente** (`~/.claude/projects/.../memory/indigo_prod_credentials.md`) — NO en este archivo porque va a circular por email.

---

## ⚠️ Hardening pendiente antes de go-live real

Ver `CLAUDE.md` sección 7 — los puntos clave:

- [ ] Cambiar `db_password` del Postgres (actualmente `odoo`)
- [ ] Cambiar `admin_passwd` del Odoo (actualmente plaintext en config)
- [ ] `list_db = False` en `config/odoo.conf`
- [ ] DNS + SSL: apuntar `app.indigodecors.com → 2.25.137.220` → Coolify habilita Let's Encrypt
- [ ] Reemplazar SMTP MailHog con SendGrid / SES / Mailgun (real)
- [ ] Backups automáticos del volumen `db-data` en Coolify

Cuando estés listo para el go-live, hacemos los 6 puntos arriba en un sprint corto.
