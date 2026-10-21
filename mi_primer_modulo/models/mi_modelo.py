from odoo import models, fields


class MiModelo(models.Model):
    _name = "mi.modelo"
    _description = "Registro de práctica"

    name = fields.Char(
        string="Nombre",
        required=True,
    )

    description = fields.Text(
        string="Descripción",
    )