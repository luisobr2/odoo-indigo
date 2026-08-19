from . import models
from . import wizards
from . import controllers
from . import tests


def post_init_hook(env):
    """Calcula la geo de instalacion en una instalacion nueva.

    Odoo calcula los campos `store=True` antes de cargar los archivos de
    datos, asi que en la primera pasada `_compute_install_geo` no tiene
    todavia ni los centroides de ZIP ni los rangos y deja todo vacio. Este
    hook corre despues de los datos. Para bases ya instaladas hace lo mismo
    el script `migrations/17.0.0.92.0/post-migrate.py`.
    """
    env["indigo.order"].indigo_recompute_install_geo()
