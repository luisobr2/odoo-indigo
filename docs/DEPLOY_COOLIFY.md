# Deploy a Hostinger VPS + Coolify

Guía paso a paso para montar Indigo Decors en producción usando:
- **VPS Hostinger** (KVM 2 o superior recomendado)
- **Coolify** (PaaS open-source self-hosted)
- **Odoo 17** desde este repo

---

## Índice

1. [Comprar y preparar el VPS](#1-comprar-y-preparar-el-vps)
2. [Instalar Coolify](#2-instalar-coolify)
3. [Apuntar dominio](#3-apuntar-dominio)
4. [Deploy del repo en Coolify](#4-deploy-del-repo-en-coolify)
5. [Configurar variables y secretos](#5-configurar-variables-y-secretos)
6. [Crear la base de datos Odoo](#6-crear-la-base-de-datos-odoo)
7. [Instalar y configurar el módulo](#7-instalar-y-configurar-el-módulo)
8. [Configurar SMTP real](#8-configurar-smtp-real)
9. [Cargar datos reales](#9-cargar-datos-reales)
10. [Backups automáticos](#10-backups-automáticos)
11. [Activar Stripe + Twilio](#11-activar-stripe--twilio)
12. [Updates y operación](#12-updates-y-operación)

---

## 1. Comprar y preparar el VPS

### Recomendación de tier

| Tier Hostinger | Specs | Cuándo |
|---|---|---|
| KVM 1 ($5/mes) | 1 vCPU, 4GB RAM, 50GB | **No** — Coolify + Odoo necesitan mínimo 4GB libres |
| KVM 2 ($8/mes) | 2 vCPU, 8GB RAM, 100GB SSD | **Recomendado** para arranque |
| KVM 4 ($15/mes) | 4 vCPU, 16GB RAM, 200GB SSD | Si crecen a >50 órdenes/día |

OS: **Ubuntu 22.04 LTS**.

### Pasos iniciales (SSH al VPS)

```bash
ssh root@<IP_VPS>

# Update
apt update && apt upgrade -y

# Usuario dedicado (opcional, recomendado)
adduser indigo
usermod -aG sudo indigo

# Hardening basico
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp  # Coolify UI
ufw --force enable

# Swap (importante para Odoo en VPS con poco RAM)
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab
```

---

## 2. Instalar Coolify

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

Esto instala Docker + Coolify en `/data/coolify`. Toma ~5 min.

Acceder a la UI: **http://`<IP_VPS>`:8000**

1. Crear cuenta admin (email + password)
2. Aceptar términos
3. Listo

---

## 3. Apuntar dominio

En tu DNS provider (Hostinger DNS, Cloudflare, etc.), crear:

| Tipo | Nombre | Valor |
|---|---|---|
| A | `app.indigodecors.com` (o el subdominio que uses) | `<IP_VPS>` |
| A | `*.indigodecors.com` (opcional, para subdomains adicionales) | `<IP_VPS>` |

Coolify usa Traefik para SSL automático via Let's Encrypt — esperar ~5 min de propagación DNS antes de continuar.

---

## 4. Deploy del repo en Coolify

### 4.1 Conectar GitHub a Coolify

1. Coolify → **Sources** → Add → GitHub App
2. Seguir el flujo OAuth (autorizar Coolify a leer tu repo `luisobr2/odoo-indigo`)
3. Verificar que aparece el repo en la lista

### 4.2 Crear el proyecto

1. Coolify → **Projects** → New Project → "Indigo Decors"
2. **Add new Resource** → **Docker Compose**
3. Source: GitHub → repo `luisobr2/odoo-indigo`, rama `main`
4. **Compose file location**: `docker-compose.yml`
5. **Build pack**: Docker Compose
6. Click **Save**

### 4.3 Configurar dominio en Coolify

En el resource → tab **Domains**:
- Domain: `https://app.indigodecors.com`
- Coolify automáticamente provisiona Let's Encrypt para HTTPS
- Mapping: puerto interno `8069` → externo `443/HTTPS`

> Para que Odoo funcione bien detrás del proxy, asegurar que `config/odoo.conf` tenga `proxy_mode = True` (ya lo tiene).

---

## 5. Configurar variables y secretos

En el resource → tab **Environment Variables**:

| Variable | Valor en producción |
|---|---|
| `POSTGRES_USER` | `odoo` |
| `POSTGRES_PASSWORD` | **Generar password fuerte** (32+ chars random) |
| `POSTGRES_HOST_PORT` | `5433` (sin exponer público en prod, dejar interno) |
| `ODOO_HOST_PORT` | `8069` |

**Importante**: en prod NO exponer Postgres (puerto 5432/5433) al internet. En Coolify, modificar `docker-compose.yml` para quitar el mapeo `ports: 5433:5432` o ponerlo en `127.0.0.1:5433:5432` (solo localhost).

### Cambiar el master password de Odoo

Editar `config/odoo.conf` localmente, reemplazar `admin_passwd = ...` por un hash fresco:

```bash
python3 -c "import passlib.hash; print(passlib.hash.pbkdf2_sha512.hash('TU_MASTER_PASSWORD_AQUI'))"
```

Commit + push. Coolify auto-redeployará.

---

## 6. Crear la base de datos Odoo

1. Abrir `https://app.indigodecors.com`
2. Click **"Create Database"**
3. Datos:
   - Master Password: el de `config/odoo.conf`
   - Database Name: `indigo` (sin guion para evitar issues)
   - Email admin (tu email real)
   - Password admin (fuerte)
   - Demo Data: **NO marcar** (es prod)
4. Click Create — toma ~30s
5. Verifica acceso → estás en la home de Odoo

---

## 7. Instalar y configurar el módulo

1. Settings → activar **Developer Mode**
2. Apps → **Update Apps List**
3. Quitar filtro "Apps" del buscador → buscar "Indigo Decors" → **Install**
4. Esperar ~1 min (instala dependencias: sale_management, website_sale, etc.)

### Cargar SLAs por defecto

Desde el host del VPS:

```bash
ssh root@<IP_VPS>
cd /data/coolify/applications/<resource-id>
docker compose exec -T odoo odoo shell -c /etc/odoo/odoo.conf -d indigo --no-http < scripts/set_sla_defaults.py
```

> El path `/data/coolify/applications/<resource-id>` lo da Coolify en el detail del resource.

---

## 8. Configurar SMTP real

Editar `config/odoo.conf` reemplazando la sección SMTP (default apunta a MailHog dev). Ejemplos:

### Opción A: Gmail / Google Workspace

```ini
smtp_server = smtp.gmail.com
smtp_port = 587
smtp_ssl = False
smtp_user = noreply@indigodecors.com
smtp_password = <app password generado en https://myaccount.google.com/apppasswords>
email_from = noreply@indigodecors.com
```

### Opción B: SendGrid (recomendado para volumen)

```ini
smtp_server = smtp.sendgrid.net
smtp_port = 587
smtp_user = apikey
smtp_password = <SG.xxxxxxxxxx>
email_from = noreply@indigodecors.com
```

Commit + push → Coolify redeploya.

**Test**: en Odoo, Settings → Técnico → Outgoing Mail Servers → Test Connection.

---

## 9. Cargar datos reales

### 9.1 Dealers reales

Indigo → Dealers → New. Marca `Es dealer Indigo` y completa código, precio/SQF, email.

**Para varios dealers (importar CSV)**:

1. Crear `dealers.csv`:
   ```csv
   name,is_indigo_dealer,is_company,indigo_dealer_code,indigo_default_price_per_sqf,email,phone
   Lock Tight,True,True,LT,12.00,ops@locktight.com,+13055551234
   Web Indigo,True,True,WI,11.00,orders@webindigo.com,+13055551235
   USA Windows,True,True,UW,11.50,contact@usawindows.com,+13055551236
   ```
2. Indigo → Dealers → action menu (⚙) → **Import records**
3. Subir CSV, mapear columnas, Import.

### 9.2 Productos del catálogo (33 diseños)

Idem importar desde CSV o crear manualmente. Marcar cada uno con `is_indigo_design=True` + medidas default.

**Importante**: si los productos existen ya en el Odoo viejo de `indigodecors.com`, exportarlos primero desde allá:

1. Login al Odoo viejo como admin
2. Inventory → Products → Filter por tags / categoría Indigo
3. Action menu → Export → seleccionar campos (`name`, `default_code`, `list_price`, `image_1920`, etc.)
4. Importar el CSV resultante al nuevo Odoo
5. En el nuevo, marcar todos como `is_indigo_design=True` (bulk edit desde la lista de productos)

### 9.3 Imágenes del catálogo

Si están en el PDF del catálogo, hay que extraerlas y subirlas una por una en `product.template.image_1920`. Para bulk:

1. Renombrar cada PNG/JPG con el `default_code` del producto (ej. `ID01-SD.png`)
2. Comprimir todas en un ZIP
3. Usar el wizard de "Import Images" de Odoo (Settings → Technical → opcional) o un script Python con `xmlrpc.client`

---

## 10. Backups automáticos

### Vía Coolify

1. Resource → **Backups** → Add Backup
2. **Type**: Database
3. **Frequency**: Daily (recomendado: 03:00 server time)
4. **Retention**: 7 days local + 30 days remote
5. **S3** (opcional para offsite): configurar bucket AWS / DigitalOcean Spaces / R2

Coolify hace `pg_dump` automático + sube a S3.

### Backup del filestore (adjuntos)

Coolify no respalda volúmenes Docker automáticamente. Para los adjuntos (fotos contrato, recibos, firmas):

Cron en el VPS:

```cron
0 4 * * * docker exec indigo-odoo tar czf - /var/lib/odoo/filestore | aws s3 cp - s3://indigo-backups/filestore-$(date +\%Y\%m\%d).tgz
```

(Requiere `aws-cli` instalado y configurado en el host.)

---

## 11. Activar Stripe + Twilio

### Stripe (cuando decidan habilitar pagos online)

1. Crear cuenta en https://dashboard.stripe.com
2. En modo **Live**, obtener:
   - Publishable key (`pk_live_…`)
   - Secret key (`sk_live_…`)
   - Webhook signing secret (configurar webhook a `https://app.indigodecors.com/payment/stripe/webhook`)
3. En Odoo:
   - Apps → buscar "Stripe Payment" → Install
   - Accounting → Configuration → Payment Providers → Stripe → Edit credentials, activar
   - Website → Configuration → Payment Providers → habilitar Stripe
4. **Test**: en `/shop` agregar producto → checkout → debería ofrecer Stripe

### Twilio (SMS/WhatsApp)

1. Crear cuenta https://www.twilio.com
2. Comprar número (A2P 10DLC registrado para US) o usar el sandbox de WhatsApp
3. Settings → Técnico → Parámetros del sistema → New (uno por cada):
   ```
   indigo.twilio_account_sid     = ACxxxxxxxxxx
   indigo.twilio_auth_token      = xxxxxxxxxx
   indigo.twilio_sms_from        = +1xxxxxxxxxx
   indigo.twilio_whatsapp_from   = +14155238886
   ```
4. La librería `twilio` ya está pre-instalada en el Dockerfile.

---

## 12. Updates y operación

### Aplicar cambios al código

1. Editar/probar local en tu PC
2. `git commit -m "descripcion"`
3. `git push origin main`
4. Coolify detecta push → triggers auto-deploy → ~1-2 min y prod actualizada

### Forzar redeploy

Coolify UI → Resource → **Redeploy**

### Aplicar cambios al módulo (upgrade)

Tras un push que cambia models o data XML del módulo, Odoo requiere `-u indigo_decors` manualmente:

```bash
ssh root@<IP_VPS>
cd /data/coolify/applications/<resource-id>
docker compose exec -T odoo odoo -c /etc/odoo/odoo.conf -d indigo -u indigo_decors --stop-after-init
docker compose restart odoo
```

(Considerar agregar este paso al hook post-deploy de Coolify si se vuelve frecuente.)

### Logs

Coolify UI → Resource → **Logs** muestra stdout/stderr en tiempo real.

Alternativa CLI:

```bash
docker compose logs -f odoo
docker compose logs --tail 200 odoo
```

### Restore de un backup

1. Coolify UI → Backups → seleccionar backup → **Restore**
2. Coolify reemplaza la DB. **Esto NO restaura el filestore** — recuperarlo manual del S3.

---

## Resumen de costos mensuales (estimado)

| Item | Costo | Notas |
|---|---|---|
| VPS Hostinger KVM 2 | $8 | 2 vCPU, 8GB RAM |
| Coolify | $0 | Self-hosted, gratis |
| Dominio | $0 si ya tienen | `indigodecors.com` ya es suyo |
| Backups S3 (DigitalOcean Spaces) | $5 | 250GB |
| SendGrid (correos) | $0 | Free tier 100/día — suficiente para arranque |
| Twilio SMS | $0 hasta usar | Pay-per-use ~$0.0075/SMS |
| Stripe | $0 setup | 2.9% + $0.30 por transacción |
| **Total fijo** | **~$13/mes** | + variables (SMS, transacciones) |

---

## Checklist pre-lanzamiento

- [ ] VPS provisionado y SSH funcionando
- [ ] Coolify instalado y UI accesible
- [ ] Dominio apunta al VPS (verificar con `dig`)
- [ ] HTTPS activo (Let's Encrypt vía Coolify/Traefik)
- [ ] Master password de Odoo cambiado (no `admin`)
- [ ] DB `indigo` creada SIN demo data
- [ ] Módulo `indigo_decors` instalado
- [ ] SLAs default cargados
- [ ] SMTP real configurado y test enviado OK
- [ ] Dealers reales creados
- [ ] Catálogo de productos cargado con imágenes
- [ ] Algunos productos marcados `is_indigo_design=True` con medidas default
- [ ] Usuarios internos creados (Office, Diseñador, CNC, Pintor)
- [ ] Portal users para dealers e instaladores creados
- [ ] Backup automático configurado y test de restore probado
- [ ] (Opcional) Stripe configurado y probado con tarjeta de test
- [ ] (Opcional) Twilio configurado y SMS de prueba enviado
- [ ] 2 sesiones de capacitación al equipo agendadas
