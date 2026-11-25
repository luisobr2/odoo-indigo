# DEPLOY.md — Desplegar un cambio en producción

Runbook vigente (2026-11-25). El montaje inicial del VPS y de Coolify está en
`DEPLOY_COOLIFY.md`; esto es lo que se hace **cada vez** que se sube un cambio.
El panel tiene el suyo en `indigo-next/DEPLOY.md` (mismo orden).

Credenciales (token de Coolify, SSH, contraseña maestra) **nunca** en este repo:
están en la configuración privada de quien despliega.

## Dónde corre

- VPS Hostinger `2.25.137.220`, Ubuntu 24.04, con **Coolify** (`:8000`).
- Recurso Odoo `f57xxcgj6dph9nkrvekz91h6`: Odoo 17 (imagen del `Dockerfile` de
  este repo, con `addons/` y `config/` copiados dentro) + Postgres 15 (volumen
  `db-data`). Base: **`indigo-prod`**.
- Recurso panel `qjalaa0kakcwbjkb1t3j2tqg` (repo `indigo-next`).

## Antes

1. Pruebas en verde contra el Odoo local:
   `docker exec indigo-odoo odoo -c /etc/odoo/odoo.conf -d indigo-prod -u indigo_decors --no-http --test-enable --test-tags /indigo_decors,/indigo_quickbooks --stop-after-init`
   (en Git Bash, con `MSYS_NO_PATHCONV=1`).
2. Cambios visuales vistos en local y aprobados.
3. **Permiso explícito** para desplegar y para cualquier escritura de datos en
   producción. Cada vez.
4. Si el cambio necesita migración, súbele la versión en `__manifest__.py` y pon
   el script en `migrations/<versión>/post-migrate.py` (idempotente).

## Pasos

1. **Copia de la base** (siempre):
   ```
   docker exec <contenedor db> pg_dump -U odoo -Fc indigo-prod > /root/backups/indigo-prod-<fecha>.dump
   ```
2. **Push** a `main` de `luisobr2/odoo-indigo`.
3. **Deploy en Coolify**:
   `POST /api/v1/deploy?uuid=f57xxcgj6dph9nkrvekz91h6&force=true` con
   `Authorization: Bearer <token>`. Tarda 2–6 min; seguir el estado en
   `/api/v1/deployments/<uuid>` hasta `finished`.
4. **Actualizar el módulo** si cambian modelos, vistas, datos, permisos o la
   versión (aquí corren las migraciones):
   ```
   docker exec <contenedor odoo> odoo -c /etc/odoo/odoo.conf -d indigo-prod -u indigo_decors --stop-after-init --no-http
   docker restart <contenedor odoo>
   ```
   Revisar que la salida no tenga `ERROR`/`CRITICAL`. Tras un `-u` por CLI el
   servidor vivo tiene el registro viejo: **el restart es obligatorio**.
5. **Panel** si también cambió (ver `indigo-next/DEPLOY.md`). Si el panel llama a
   un método nuevo de Odoo, va **después** de Odoo.
6. **Comprobar**: `https://indigodecors.com` y `https://app.indigodecors.com/login`
   responden 200, y la funcionalidad cambiada hace lo que debe (una consulta de
   solo lectura a la base vale para confirmar datos o migraciones).

## Si algo sale mal

- El deploy falla al compilar: Coolify sigue sirviendo la imagen anterior.
  Arreglar y repetir.
- El `-u` falla: el log dice qué archivo/modelo. Si la base quedó a medias,
  restaurar la copia del paso 1 **con el nombre exacto `indigo-prod`**: con
  `list_db = False` y `dbfilter = ^indigo-prod$`, una base con otro nombre deja
  sin servicio la tienda **y** el panel.
- Volver atrás el código: `git revert` + push + deploy (no reescribir historia).

## Cosas que viven en la base, no en git

Si alguna vez se recrea el volumen `db-data`, hay que volver a poner a mano:
el servidor de correo (`ir.mail_server` BanaHosting, `mail.indigodecors.com:465`
SSL) y sus parámetros `mail.bounce.alias=no-reply` / `mail.default.from=no-reply`;
la conexión con QuickBooks; las claves de Anota; las tarifas y reglas de pago.

## Pendiente

- **Copias automáticas** del volumen `db-data` fuera del VPS (hoy solo las
  manuales del paso 1, en el mismo disco).
