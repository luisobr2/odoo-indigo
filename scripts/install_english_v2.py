# Instala ingles correctamente via base.language.install
env = env  # noqa

# Resetear admin a es_ES por si
env.ref("base.user_admin").lang = "es_ES"
env.cr.commit()

# Marcar en_US como inactive primero para usar el wizard
env["res.lang"].with_context(active_test=False).search([("code", "=", "en_US")]).active = False
env.cr.commit()

# Wizard oficial: instala el idioma + carga traducciones de todos los modulos
wiz = env["base.language.install"].create({
    "lang_ids": [(6, 0, [env.ref("base.lang_en").id])],
    "overwrite": True,
})
wiz.lang_install()
env.cr.commit()
print("Language en_US installed via wizard")

# Verificar
print("en_US active:", env["res.lang"].with_context(active_test=False).search([("code", "=", "en_US")]).active)
print("admin lang options should include en_US now")

# Cambiar admin a en_US
env.ref("base.user_admin").lang = "en_US"
env.cr.commit()
print("admin.lang -> en_US")
