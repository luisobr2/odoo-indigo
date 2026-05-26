import uuid
env = env  # noqa
orders = env["indigo.order"].search([("access_token", "=", False)])
for o in orders:
    o.access_token = uuid.uuid4().hex
env.cr.commit()
for o in env["indigo.order"].search([], limit=5):
    print(o.name, "->", o.access_token)
