from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .inspeccion import _pdf_download_action

MAX_DIAGNOSTICS = 4  # el diagnóstico principal + 3 adicionales
MAX_MATERIALS = 3


class ServicioCotizacion(models.Model):
    _name = "servicio.cotizacion"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Solicitud de cotización"
    _order = "request_date desc, id desc"

    name = fields.Char(
        string="No. de solicitud",
        copy=False,
        readonly=True,
        default="Nuevo",
    )

    # ---------------- 1. Datos de la solicitud ----------------
    reference_type = fields.Selection(
        [
            ("none", "Sin reporte"),
            ("preventive", "Reporte de servicio preventivo"),
            ("single", "Reporte único"),
            ("emergency", "Visita de emergencia"),
        ],
        string="Referencias",
    )
    reference_note = fields.Text(string="Nota de referencias")
    reference_attachment_ids = fields.Many2many(
        "ir.attachment", "servicio_cot_ref_att_rel", string="Archivos de referencias"
    )
    request_date = fields.Date(
        string="Fecha", default=fields.Date.context_today, required=True)
    customer_id = fields.Many2one("res.partner", string="Cliente", required=True)
    customer_phone = fields.Char(
        string="Teléfono del cliente",
        compute="_compute_customer_phone",
        store=True,
        readonly=False,
    )
    zone = fields.Char(string="Zona")
    location = fields.Char(string="Ubicación")
    technician_id = fields.Many2one(
        "res.users", string="Nombre del técnico", default=lambda self: self.env.user, required=True
    )
    required_time = fields.Char(
        string="Tiempo requerido para realizar el servicio", help="Por ejemplo: 4 horas, 2 días")
    people_count = fields.Integer(string="Número de personas para realizar el trabajo")
    customer_contact = fields.Char(string="Nombre del cliente")

    # ---------------- 2. Detalle de la cotización ----------------
    supply_option = fields.Selection(
        [
            ("send", "Envío al cliente"),
            ("next_visit", "En próxima visita"),
            ("install", "Instalación por técnico"),
            ("supply_only", "Solo suministro"),
            ("emergency", "Visita de emergencia"),
            ("subcontract", "Subcontratado"),
        ],
        string="Selecciona la siguiente opción",
    )
    diagnostic_ids = fields.One2many(
        "servicio.cotizacion.diagnostico", "cotizacion_id", string="Diagnósticos", copy=True
    )
    material_ids = fields.One2many(
        "servicio.cotizacion.material", "cotizacion_id", string="Material a cotizar", copy=True
    )
    # Notas y fotos debajo de la tabla de material
    material_description_note = fields.Text(string="Nota de descripción")
    material_brand_note = fields.Text(string="Nota de marca")
    material_model_note = fields.Text(string="Nota de modelo")
    material_serial_note = fields.Text(string="Nota de número de serie")
    material_quantity_note = fields.Text(string="Nota de cantidad")
    material_images_note = fields.Text(string="Nota de imágenes")
    material_attachment_ids = fields.Many2many(
        "ir.attachment", "servicio_cot_mat_att_rel", string="Imágenes del material"
    )

    @api.depends("customer_id")
    def _compute_customer_phone(self):
        for rec in self:
            if rec.customer_id.phone:
                rec.customer_phone = rec.customer_id.phone

    @api.constrains("diagnostic_ids", "material_ids")
    def _check_limits(self):
        for rec in self:
            if len(rec.diagnostic_ids) > MAX_DIAGNOSTICS:
                raise ValidationError(
                    "Solo se permiten %d diagnósticos (el principal y 3 adicionales)." % MAX_DIAGNOSTICS
                )
            if len(rec.material_ids) > MAX_MATERIALS:
                raise ValidationError(
                    "Solo se permiten %d materiales en la tabla." % MAX_MATERIALS
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = self.env["ir.sequence"].next_by_code("servicio.cotizacion") or "Nuevo"
        return super().create(vals_list)

    def action_download_report(self):
        self.ensure_one()
        return _pdf_download_action(
            self, "gestion_servicios.action_report_cotizacion", "Solicitud-Cotizacion-%s.pdf" % self.name
        )

    def action_send_email(self):
        """Abre el correo al cliente con el PDF de la solicitud adjunto."""
        self.ensure_one()
        template = self.env.ref("gestion_servicios.mail_template_cotizacion")
        return {
            "type": "ir.actions.act_window",
            "name": "Enviar solicitud por correo",
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


class ServicioCotizacionDiagnostico(models.Model):
    _name = "servicio.cotizacion.diagnostico"
    _description = "Diagnóstico de la solicitud de cotización"
    _order = "sequence, id"

    cotizacion_id = fields.Many2one("servicio.cotizacion", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    fault_description = fields.Text(string="Descripción de la falla", required=True)
    fault_note = fields.Text(string="Nota de la falla")
    corrective_action = fields.Text(string="Acción correctiva")
    corrective_note = fields.Text(string="Nota de la acción correctiva")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "servicio_cot_diag_att_rel",
        "diagnostico_id",
        "attachment_id",
        string="Archivos de la acción correctiva",
    )


class ServicioCotizacionMaterial(models.Model):
    _name = "servicio.cotizacion.material"
    _description = "Material a cotizar"
    _order = "sequence, id"

    cotizacion_id = fields.Many2one("servicio.cotizacion", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    description = fields.Char(string="Descripción", required=True)
    brand = fields.Char(string="Marca")
    product_model = fields.Char(string="Modelo")
    serial_number = fields.Char(string="Número de serie")
    quantity = fields.Float(string="Cantidad", default=1.0)


class ReportCotizacion(models.AbstractModel):
    _name = "report.gestion_servicios.report_cotizacion_document"
    _description = "Reporte PDF de solicitud de cotización"

    @api.model
    def _get_report_values(self, docids, data=None):
        # Mismas funciones de fotos, logo y pie que el reporte de inspección
        values = self.env["report.gestion_servicios.report_inspeccion_document"]._get_report_values(
            [], data
        )
        values.update({
            "doc_ids": docids,
            "doc_model": "servicio.cotizacion",
            "docs": self.env["servicio.cotizacion"].browse(docids),
        })
        return values
