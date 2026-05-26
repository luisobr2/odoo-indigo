# Asigna SLA por defecto a las etapas existentes (idempotente)
env = env  # noqa
SLA_BY_CODE = {
    "new": 2,
    "design_pending": 3,
    "design_confirmed": 1,
    "measure_pending": 5,
    "measured": 2,
    "ready_digitalization": 3,
    "cnc": 5,
    "painting": 7,
    "ready_install": 3,
    "install_scheduled": 7,
    "installed": 2,
    "invoiced": 5,
    # closed: sin SLA
}
for code, days in SLA_BY_CODE.items():
    stage = env["indigo.stage"].search([("code", "=", code)], limit=1)
    if stage:
        stage.sla_days = days
        print("STAGE", code, "-> sla_days=", days)
env.cr.commit()
