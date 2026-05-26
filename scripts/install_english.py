# Activa el idioma ingles y carga traducciones de indigo_decors
env = env  # noqa

# Activar ingles
Lang = env["res.lang"]
en_lang = Lang.with_context(active_test=False).search([("code", "=", "en_US")], limit=1)
if en_lang and not en_lang.active:
    en_lang.active = True
    print("Activated en_US")
else:
    print("en_US already active or not found")

# Reload del modulo para que cargue i18n/en.po
env["ir.module.module"].search([("name", "=", "indigo_decors")]).button_immediate_upgrade()
env.cr.commit()
print("Module upgraded — translations loaded")

# Cambiar idioma del admin para test
admin = env.ref("base.user_admin")
admin.lang = "en_US"
env.cr.commit()
print("Admin lang -> en_US")
