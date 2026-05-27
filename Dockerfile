# Imagen Odoo 17 con dependencias adicionales para indigo_decors
FROM odoo:17

USER root

# Dependencias del modulo indigo_decors
RUN pip install --no-cache-dir --break-system-packages \
    twilio \
    qrcode \
    Pillow \
 || pip install --no-cache-dir \
    twilio \
    qrcode \
    Pillow

# wkhtmltopdf ya viene en la imagen base de odoo:17

# Permisos correctos
RUN mkdir -p /mnt/extra-addons /etc/odoo /var/lib/odoo \
 && chown -R odoo:odoo /mnt/extra-addons /etc/odoo /var/lib/odoo

# Bake addons y config dentro de la imagen (Coolify no preserva el repo fuera del build)
COPY --chown=odoo:odoo addons/ /mnt/extra-addons/
COPY --chown=odoo:odoo config/ /etc/odoo/

USER odoo

EXPOSE 8069 8072

# El comando default se sobreescribe via docker-compose
CMD ["odoo"]
