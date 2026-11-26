from odoo import api, fields, models

from .inspeccion import _pdf_download_action


class ServicioEntrega(models.Model):
    _name = "servicio.entrega"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Entrega de equipo"
    _order = "delivery_date desc, id desc"

    # ---------------- 1. Datos de entrega ----------------
    name = fields.Char(
        string="No. de remisión",
        copy=False,
        readonly=True,
        default="Nuevo",
    )
    order_number = fields.Char(string="No. de pedido")
    customer_id = fields.Many2one("res.partner", string="Nombre de la empresa", required=True)
    delivery_date = fields.Date(
        string="Fecha", default=fields.Date.context_today, required=True)
    delivered_by_id = fields.Many2one(
        "res.users", string="Entregado por", default=lambda self: self.env.user, required=True
    )

    # ---------------- 2. Equipo a entregar ----------------
    line_ids = fields.One2many(
        "servicio.entrega.linea", "entrega_id", string="Equipo a entregar", copy=True
    )

    # ---------------- 3. Datos de recepción ----------------
    receiver_name = fields.Char(string="Nombre de la persona que recibe")
    receiver_position = fields.Char(string="Cargo de la persona que recibe")
    receiver_signature = fields.Binary(string="Firma de quien recibe", attachment=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = self.env["ir.sequence"].next_by_code("servicio.entrega") or "Nuevo"
        return super().create(vals_list)

    def action_download_report(self):
        self.ensure_one()
        return _pdf_download_action(
            self, "gestion_servicios.action_report_entrega", "Entrega-Equipo-%s.pdf" % self.name
        )

    def action_send_email(self):
        """Abre el correo al cliente con el PDF de la entrega adjunto."""
        self.ensure_one()
        template = self.env.ref("gestion_servicios.mail_template_entrega")
        return {
            "type": "ir.actions.act_window",
            "name": "Enviar entrega por correo",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_model": self._name,
                "default_res_ids": self.ids,
                "default_template_id": template.id,
                "default_composition_mode": "comment",
                "default_email_layout_xmlid": "mail.mail_notification_light",
                "force_email": True,
            },
        }


class ServicioEntregaLinea(models.Model):
    _name = "servicio.entrega.linea"
    _description = "Equipo a entregar"
    _order = "sequence, id"

    entrega_id = fields.Many2one("servicio.entrega", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    product_model = fields.Char(string="Modelo")
    description = fields.Char(string="Descripción", required=True)
    quantity = fields.Float(string="Cantidad", default=1.0)
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "servicio_entrega_linea_att_rel",
        "linea_id",
        "attachment_id",
        string="Fotos de evidencia",
    )


class ReportEntrega(models.AbstractModel):
    _name = "report.gestion_servicios.report_entrega_document"
    _description = "Reporte PDF de entrega de equipo"

    @api.model
    def _get_report_values(self, docids, data=None):
        # Mismas funciones de firma, logo y pie que el reporte de inspección
        values = self.env["report.gestion_servicios.report_inspeccion_document"]._get_report_values(
            [], data
        )
        values.update({
            "doc_ids": docids,
            "doc_model": "servicio.entrega",
            "docs": self.env["servicio.entrega"].browse(docids),
        })
        return values
