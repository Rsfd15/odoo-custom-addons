from odoo import http
from odoo.http import request


class ServicioInspeccionLocationController(http.Controller):

    @http.route(
        "/gestion_servicios/reverse_geocode",
        type="http",
        auth="user",
        methods=["GET"],
    )
    def reverse_geocode(self, lat=None, lon=None, **kwargs):
        """Devuelve el nombre del lugar para las coordenadas GPS del teléfono."""
        address = request.env["servicio.inspeccion"].reverse_geocode(lat, lon)
        return request.make_json_response({"address": address or False})