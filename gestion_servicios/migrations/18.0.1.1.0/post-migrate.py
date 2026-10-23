from odoo import SUPERUSER_ID, api

from odoo.addons.gestion_servicios.models.inspeccion import MEDIA_SECTIONS, _media_vals


def migrate(cr, version):
    """Aplica el nuevo límite de fotos ANTES/DESPUÉS a las inspecciones ya creadas."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    items = env["servicio.inspeccion.item"].search([("section", "in", MEDIA_SECTIONS)])
    for item in items:
        item.write(_media_vals(item.section, item.question))
