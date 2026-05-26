# Manual de Operaciones — Indigo Decors

Para el DevOps / técnico que mantenga el sistema. Cubre instalación, backups, deploy, activación de Twilio, troubleshooting.

---

## Índice

1. [Stack técnico](#1-stack-técnico)
2. [Levantar entorno local](#2-levantar-entorno-local)
3. [Backup y restore](#3-backup-y-restore)
4. [Aplicar cambios al módulo](#4-aplicar-cambios-al-módulo)
5. [Activar SMS / WhatsApp (Twilio)](#5-activar-sms--whatsapp-twilio)
6. [Configurar correo real (producción)](#6-configurar-correo-real-producción)
7. [Deploy a VPS](#7-deploy-a-vps)
8. [Tests automatizados](#8-tests-automatizados)
9. [Multiidioma](#9-multiidioma)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Stack técnico

| Componente | Versión | Notas |
|---|---|---|
| Odoo | 17 Community | Sin licencia Enterprise |
| Postgres | 15 | Base de datos |
| MailHog | latest | Solo dev — captura correos sin enviarlos |
| Python | 3.10+ | Incluido en imagen `odoo:17` |
| Módulo a medida | `indigo_decors` | En `addons/indigo_decors/` |

Dependencias del módulo: `base`, `mail`, `web`, `product`, `account`, `portal`.

---

## 2. Levantar entorno local

Requisitos: Docker Desktop corriendo.

```bash
git clone https://github.com/luisobr2/odoo-indigo.git
cd odoo-indigo
docker compose up -d
```

Esto levanta 3 contenedores:

| Contenedor | Puerto host | Servicio |
|---|---|---|
| `indigo-odoo` | 8069, 8072 | Odoo web + longpolling |
| `indigo-db` | 5433 | Postgres (mapeado a 5433 porque 5432 está ocupado en el host) |
| `indigo-mailhog` | 1025, 8025 | SMTP + Web UI |

### Primera vez: crear DB e instalar módulo

1. http://localhost:8069 → "Create Database"
   - Master Password: `admin` (configurado en `config/odoo.conf`)
   - Database Name: `indigo-db`
   - Email/Password: a elección
2. Login → Settings → activar **Developer Mode** (modo desarrollador)
3. Apps → **Update Apps List**
4. Buscar "Indigo Decors" (quitar filtro "Apps" del buscador)
5. **Install**

### Verificar que todo arranca

- http://localhost:8069 → menú **Indigo** visible
- http://localhost:8025 → MailHog inbox (vacío en primera carga)
- `docker compose ps` → 3 contenedores `Up`

### Cargar SLAs por defecto

Después de instalar el módulo, ejecutar una vez:

```bash
docker compose exec -T odoo odoo shell -c /etc/odoo/odoo.conf -d indigo-db --no-http < scripts/set_sla_defaults.py
```

---

## 3. Backup y restore

### Backup completo de la DB

```bash
# Backup a archivo
docker compose exec db pg_dump -U odoo -d indigo-db -Fc -f /tmp/indigo-backup.dump
docker cp indigo-db:/tmp/indigo-backup.dump ./backups/indigo-$(date +%Y%m%d-%H%M%S).dump

# Backup filestore (adjuntos: fotos, recibos, firmas)
docker compose exec odoo tar czf /tmp/filestore.tgz /var/lib/odoo/filestore/indigo-db
docker cp indigo-odoo:/tmp/filestore.tgz ./backups/filestore-$(date +%Y%m%d-%H%M%S).tgz
```

### Restore

```bash
# Restaurar DB (CUIDADO: sobreescribe)
docker cp ./backups/indigo-XXXXXXXX.dump indigo-db:/tmp/restore.dump
docker compose exec db dropdb -U odoo indigo-db
docker compose exec db createdb -U odoo indigo-db
docker compose exec db pg_restore -U odoo -d indigo-db /tmp/restore.dump

# Restaurar filestore
docker cp ./backups/filestore-XXXXXXXX.tgz indigo-odoo:/tmp/restore-fs.tgz
docker compose exec odoo tar xzf /tmp/restore-fs.tgz -C /
docker compose restart odoo
```

### Backup desde la UI

Settings → Database Manager (al final) → Backup → descarga ZIP con todo incluido (DB + filestore). Es la forma más simple.

### Cron de backup automático (opcional, en VPS)

Agregar a `crontab` del host:

```cron
0 3 * * * cd /opt/indigo && docker compose exec db pg_dump -U odoo -d indigo-db -Fc -f /tmp/indigo-$(date +\%Y\%m\%d).dump && docker cp indigo-db:/tmp/indigo-$(date +\%Y\%m\%d).dump /backups/
```

---

## 4. Aplicar cambios al módulo

### Cambios en código Python (modelos, controllers)

```bash
# Reload sin restart
docker compose restart odoo

# Si los cambios son a modelos con campos nuevos, además:
docker compose exec -T odoo odoo -c /etc/odoo/odoo.conf -d indigo-db -u indigo_decors --stop-after-init
docker compose restart odoo
```

### Cambios en views / data XML

```bash
docker compose exec -T odoo odoo -c /etc/odoo/odoo.conf -d indigo-db -u indigo_decors --stop-after-init
docker compose restart odoo
```

### Cambios en `i18n/*.po` (traducciones)

```bash
docker compose exec -T odoo odoo -c /etc/odoo/odoo.conf -d indigo-db -u indigo_decors --i18n-overwrite --stop-after-init
docker compose restart odoo
# Browser: hard reload (Ctrl+Shift+R / F5) para invalidar cache de assets
```

### Generar/actualizar el archivo .pot

```bash
mkdir -p addons/indigo_decors/i18n
docker compose exec -T odoo odoo -c /etc/odoo/odoo.conf -d indigo-db \
  --i18n-export=/mnt/extra-addons/indigo_decors/i18n/indigo_decors.pot \
  --modules=indigo_decors --stop-after-init
```

Para agregar más traducciones a inglés: editar `scripts/generate_en_po.py` (dict `TRANSLATIONS`) y correr:

```bash
python scripts/generate_en_po.py
```

---

## 4b. Bridge eCommerce → Producción

El módulo integra con `sale_management` + `website_sale` (la tienda online de
Odoo). Cuando se confirma una `sale.order` con productos marcados `is_indigo_design`,
se crea automáticamente una `indigo.order` con líneas mapeadas.

### Marcar un producto como Indigo

1. Inventory → Products → seleccionar producto (ej. ID01-SD)
2. Pestaña **Indigo**:
   - ✅ Es diseño Indigo
   - Tipo de puerta: SD / DD / Sidelite
   - Diseño asociado (link al `indigo.design` del catálogo)
   - Medidas default (Ancho/Alto en pulgadas) — se usan al crear la orden de producción desde eCommerce
   - Color default + Vidrio default

### Flujos soportados

| Origen | Quién | Modelo origen | Indigo.order creada |
|---|---|---|---|
| Tienda online (carrito + checkout) | Cliente público o dealer logueado | sale.order | Sí, al confirmar el sale.order |
| Portal del dealer `/my/order/new` | Dealer | indigo.order directo (sin sale.order) | Sí, directa |
| Captura manual desde admin (Indigo → Orders → New) | Office / Manager | indigo.order directo | Sí, directa |

### Cuando se agrega pasarela de pago (Stripe)

1. **Instalar el módulo de Stripe**: Settings → Apps → buscar "Stripe Payment Acquirer" → Install
2. Configurar credenciales: Accounting → Configuration → Payment Providers → Stripe → Edit:
   - Publishable Key (de Stripe Dashboard)
   - Secret Key
   - Webhook Endpoint (URL pública + path) y Webhook Signing Secret
3. **Activar el provider** para producción
4. Configurar el journal contable asociado
5. En **Website → Configuration → Payment Providers**, habilitar Stripe para el sitio

**Comportamiento**: Cliente B2C compra → paga con tarjeta → Stripe confirma → `sale.order.action_confirm()` se dispara → bridge crea `indigo.order` automáticamente → workflow de producción arranca.

**Comisión Stripe**: 2.9% + $0.30 por transacción tarjeta. ACH: 0.8% (max $5). Setup: gratis.

### Limitaciones del bridge

- **No captura medidas custom desde eCommerce**: el carrito vende productos estándar con dimensiones fijas (las del campo `indigo_default_width/height` del producto). Si el cliente necesita medidas específicas, la `indigo.order` se crea con esas medidas default y el Office las ajusta después.
- **Variants no se mapean automáticamente al color**: si el producto tiene variantes (Black/White/Bronze), la lógica detecta el color por nombre del display. Para precisión, configurar `indigo_default_color` o agregar lógica de mapping de attribute_value a color.
- **Door Brand (vidrio)**: no se mapea automáticamente. Si el shop tiene variantes por Door Brand, copiar el nombre como `glass_type` requiere extender `_parse_*` en `indigo_sale_bridge.py`.

Estas limitaciones son intencionales — el dealer/cliente que necesite full control sigue usando el portal `/my/order/new` o la captura manual del Office.

---

## 5. Activar SMS / WhatsApp (Twilio)

El código tiene placeholders. Sin credenciales, los métodos `_send_sms` y `_send_whatsapp` solo escriben al chatter `[SMS pendiente]`. Para enviar real:

### Paso 1: instalar `twilio` en la imagen Odoo

Opción A — `pip install` en el contenedor activo (no persiste tras `docker compose down`):

```bash
docker compose exec odoo pip install twilio
docker compose restart odoo
```

Opción B — crear `Dockerfile` custom (recomendado para producción):

```dockerfile
FROM odoo:17
USER root
RUN pip install twilio
USER odoo
```

Actualizar `docker-compose.yml`:

```yaml
  odoo:
    build: .
    # ... resto igual
```

```bash
docker compose build odoo
docker compose up -d
```

### Paso 2: configurar credenciales

Settings → Técnico → Parámetros del sistema → **New** (uno por cada parámetro):

| Key | Value |
|---|---|
| `indigo.twilio_account_sid` | ACxxxxxxxxxxxxxx (de Twilio Console) |
| `indigo.twilio_auth_token` | xxxxxxxxxxxxxxxxx |
| `indigo.twilio_sms_from` | `+1xxxxxxxxxx` (número Twilio o A2P registrado) |
| `indigo.twilio_whatsapp_from` | `+14155238886` (sandbox de Twilio) o número WA Business aprobado |

### Paso 3: configurar partners

En la ficha de cada partner que deba recibir SMS/WA:
- Verificar que tenga **Mobile** o **Phone** con formato E.164 (ej. `+13055551234`)
- Cambiar **Canales de notificacion** → "Email + SMS" / "Email + WhatsApp" / "Todos"

### Paso 4: gatillar el envío

El envío se dispara al cambiar etapa solo si llamás explícitamente `order._dispatch_stage_notification()`. Para activarlo automáticamente, agregar al `write()` en `indigo_order.py`:

```python
# Después del envío de email
order._dispatch_stage_notification()
```

---

## 6. Configurar correo real (producción)

Editar `config/odoo.conf` y reemplazar:

```ini
smtp_server = mailhog
smtp_port = 1025
smtp_ssl = False
email_from = noreply@indigodecors.local
```

por (ejemplo con Gmail / Google Workspace):

```ini
smtp_server = smtp.gmail.com
smtp_port = 587
smtp_ssl = False
smtp_user = noreply@indigodecors.com
smtp_password = <app-password de google>
email_from = noreply@indigodecors.com
```

O usar SendGrid / Mailgun / SES:

```ini
smtp_server = email-smtp.us-east-1.amazonaws.com  # SES
smtp_port = 587
smtp_user = <SMTP_USERNAME>
smtp_password = <SMTP_PASSWORD>
email_from = noreply@indigodecors.com
```

Restart Odoo:

```bash
docker compose restart odoo
```

**Verificar envío**: Settings → Técnico → Email → Outgoing Mail Servers → Test Connection.

---

## 7. Deploy a VPS

### Especificación recomendada

| Recurso | Mínimo | Recomendado |
|---|---|---|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Disco | 20 GB SSD | 60 GB SSD |
| OS | Ubuntu 22.04 | Ubuntu 22.04 |

Costo aproximado: DigitalOcean $24/mes (Standard 4GB), Hetzner CX22 ~$10/mes.

### Setup en el VPS

```bash
# 1. Instalar Docker + Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. Clonar repo
sudo mkdir -p /opt && cd /opt
sudo git clone https://github.com/luisobr2/odoo-indigo.git indigo
cd indigo

# 3. Ajustar config para prod
# Editar config/odoo.conf:
#   - cambiar admin_passwd (NO dejar 'admin')
#   - smtp_server real (no mailhog)
#   - proxy_mode = True
# Editar docker-compose.yml:
#   - quitar mailhog (no usar en prod)
#   - quitar mapeo db:5432 público (innecesario fuera de docker network)

# 4. Levantar
docker compose up -d

# 5. Crear DB (igual que local pero en http://<ip-vps>:8069)
```

### Reverse proxy + HTTPS (nginx + certbot)

`/etc/nginx/sites-available/indigo`:

```nginx
upstream odoo { server 127.0.0.1:8069; }
upstream odoo-chat { server 127.0.0.1:8072; }

server {
    listen 80;
    server_name app.indigodecors.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name app.indigodecors.com;

    ssl_certificate     /etc/letsencrypt/live/app.indigodecors.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.indigodecors.com/privkey.pem;

    client_max_body_size 100M;
    proxy_buffers 16 64k;
    proxy_buffer_size 128k;

    location /longpolling { proxy_pass http://odoo-chat; }
    location / {
        proxy_pass http://odoo;
        proxy_redirect off;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/indigo /etc/nginx/sites-enabled/
sudo certbot --nginx -d app.indigodecors.com
sudo systemctl reload nginx
```

---

## 8. Tests automatizados

```bash
docker compose exec -T odoo odoo -c /etc/odoo/odoo.conf -d indigo-db \
  -u indigo_decors --test-enable --test-tags indigo --stop-after-init
```

Salida esperada:

```
... TestIndigoOrder.test_create_defaults_price_from_dealer ...
...
0 failed, 0 error(s) of 11 tests when loading database 'indigo-db'
```

11 tests cubren: creación con defaults, computos SQF y montos, tarifas vía contractor.rate, triggers de payouts pintor/instalador, idempotencia, filtro kanban por dealer.

Para agregar más tests: `addons/indigo_decors/tests/test_indigo_order.py`.

---

## 9. Multiidioma

Source: **Español** (es_ES). Traducción **Inglés** (en_US) en `i18n/en.po` (~50% de strings explícitamente traducidos; el resto fallback a Spanish source).

### Activar otro idioma en una DB existente

```python
# Shell de Odoo
wiz = env["base.language.install"].create({
    "lang_ids": [(6, 0, [env.ref("base.lang_en").id])],
    "overwrite": True,
})
wiz.lang_install()
env.cr.commit()
```

O desde UI: Settings → Translations → Load language.

### Agregar / corregir traducciones inglesas

1. Editar `scripts/generate_en_po.py` (dict `TRANSLATIONS`)
2. `python scripts/generate_en_po.py` → regenera `i18n/en.po`
3. `docker compose exec -T odoo odoo -c /etc/odoo/odoo.conf -d indigo-db -u indigo_decors --i18n-overwrite --stop-after-init`
4. Hard reload del browser

### Agregar un idioma nuevo (ej. portugués)

1. Generar `.pot` actualizado (ver §4)
2. Copiar `indigo_decors.pot` → `i18n/pt.po`
3. Editar manualmente traducciones
4. Activar idioma en Odoo y recargar módulo con `--i18n-overwrite`

---

## 10. Troubleshooting

### Logs

```bash
docker compose logs -f odoo          # En tiempo real
docker compose logs --tail 200 odoo  # Últimas 200 líneas
```

### "Module not loaded" después de un cambio

```bash
docker compose restart odoo
# Si persiste:
docker compose exec -T odoo odoo -c /etc/odoo/odoo.conf -d indigo-db -u indigo_decors --stop-after-init
docker compose restart odoo
```

### View error después de modificar un XML

El log muestra `View error context: {'file': '...', 'line': N, ...}`. Revisar el XML en esa línea. Errores comunes:
- `t-field="..."` directo en `<td>` → cambiar a `<td><span t-field="..."/></td>` o usar `t-out`
- XPath no encuentra elemento → revisar selector inherit_id
- ID duplicado en data XML → renombrar

### "Translation not loading"

```bash
docker compose exec -T odoo odoo -c /etc/odoo/odoo.conf -d indigo-db -u indigo_decors --i18n-overwrite --stop-after-init
docker compose restart odoo
# Hard reload del navegador (Ctrl+F5)
```

### "Port already in use" al levantar containers

Algo ya escucha en 8069 / 8025 / 5433 / 1025. Ver con `netstat -an | grep <puerto>` y matar el proceso, o cambiar el mapping en `docker-compose.yml`.

### El portal no muestra órdenes a un usuario

1. Verificar que el partner del user tiene `is_indigo_dealer=True` (dealer) o esté en `installer_ids` de alguna orden (instalador)
2. Verificar que el user pertenece al grupo `base.group_portal`
3. Verificar record rules: Settings → Tecnico → Security → Record Rules → filtrar "indigo"

### Cambiar password de admin

```bash
docker compose exec -T odoo odoo shell -c /etc/odoo/odoo.conf -d indigo-db --no-http <<EOF
admin = env.ref("base.user_admin")
admin.password = "NuevoPassword123!"
env.cr.commit()
EOF
```

### Resetear DB completa (DEV ONLY)

```bash
docker compose down -v   # ⚠️ borra todos los volúmenes (db + filestore)
docker compose up -d
# Recrear DB desde la UI
```

### MailHog no recibe correos

1. `docker compose ps` → verificar `indigo-mailhog` Up
2. `config/odoo.conf` debe tener `smtp_server = mailhog` y `smtp_port = 1025`
3. Restart odoo: `docker compose restart odoo`
4. En Odoo, Settings → Técnico → Outgoing Mail Servers → desactivar cualquier server custom (Odoo usa el del .conf si no hay)

---

## Estructura técnica resumida

```
addons/indigo_decors/
├── __manifest__.py            Manifest (depends, data files)
├── models/                    14 modelos Python
│   ├── indigo_order.py        Modelo principal con triggers
│   ├── indigo_order_line.py
│   ├── indigo_order_incident.py
│   ├── indigo_stage.py
│   ├── indigo_design.py
│   ├── indigo_dealer.py       Extends res.partner
│   ├── indigo_contractor_rate.py
│   ├── indigo_payout.py       + indigo.payout.line
│   ├── indigo_stock.py        Inventario CNC
│   └── indigo_notification.py SMS/WhatsApp placeholders
├── views/                     20 XMLs
├── reports/                   6 PDFs QWeb
├── controllers/portal.py      Rutas portal + tracking público
├── wizards/                   3 wizards (payout settle, bulk assign)
├── data/                      Seed: stages, sequences, dealers, designs, rates, crons
├── security/                  Groups, ACL, record rules
├── tests/                     11 tests
└── i18n/                      Translations (es source, en)
```

### Modelos principales y relaciones

```
res.partner (extended)
├── is_indigo_dealer (flag) ──→ indigo.order.dealer_id
└── indigo_optional_stage_ids ─→ indigo.stage[]

indigo.order ────────┬─→ indigo.order.line (1:N) ──→ indigo.design (N:1)
                     ├─→ indigo.order.incident (1:N)
                     ├─→ indigo.payout.line (1:N) ──→ indigo.payout (N:1) ──→ res.partner
                     ├── stage_id ──→ indigo.stage
                     ├── painter_id ──→ res.partner
                     └── installer_ids ──→ res.partner[]

indigo.stock ──→ indigo.design
indigo.contractor.rate (sin FK, lookup por tipo)
```

### Triggers principales

| Trigger | Acción |
|---|---|
| `indigo.order.write()` cambio de `stage_id` | Envía email + actualiza `last_stage_change` + crea payouts si aplica |
| Sale de etapa `painting` con `painter_id` | Crea draft payout pintor (líneas = piezas × SQF × tarifa) |
| Entra a etapa `installed` con `installer_ids` | Crea draft payouts (uno por instalador) |
| Cron diario SLA | Crea activity `todo` para asignados de órdenes atrasadas |
| Cron diario stock | Crea activity para managers si hay items con `available < threshold` |
| `indigo.order.create()` | Genera `access_token` UUID, defaultea `price_per_sqf` desde dealer |
