from odoo import api, fields, models


class ServicioCorrectivo(models.Model):
    _name = "servicio.correctivo"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Reporte correctivo"
    _order = "report_date desc, id desc"

    name = fields.Char(
        string="No. de reporte",
        copy=False,
        readonly=True,
        default="Nuevo",
    )
    report_date = fields.Date(
        string="Fecha", default=fields.Date.context_today, required=True)
    work_name = fields.Char(string="Nombre de la obra", required=True)
    customer_id = fields.Many2one("res.partner", string="Empresa", required=True)
    supervisor_id = fields.Many2one(
        "res.users", string="Supervisor", default=lambda self: self.env.user, required=True
    )
    address = fields.Char(string="Dirección")
    requester = fields.Char(string="Solicitante")
    line_ids = fields.One2many(
        "servicio.correctivo.linea", "correctivo_id", string="Trabajos realizados", copy=True
    )

    # Firmas (igual que en la inspección)
    report_made_by = fields.Char(
        string="Reporte elaborado por", default=lambda self: self.env.user.name)
    report_made_signature = fields.Binary(
        string="Firma de quien elabora", attachment=True, copy=False)
    report_received_by = fields.Char(string="Reporte recibido por")
    report_received_signature = fields.Binary(
        string="Firma de quien recibe", attachment=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = self._next_number(vals.get("report_date"))
        return super().create(vals_list)

    def _next_number(self, report_date):
        """Número con la fecha y un consecutivo del día, p. ej. 261026-1."""
        day = fields.Date.to_date(report_date) or fields.Date.context_today(self)
        prefix = day.strftime("%y%m%d") + "-"
        names = self.search([("name", "=like", prefix + "%")]).mapped("name")
        last = max(
            (int(n[len(prefix):]) for n in names if n[len(prefix):].isdigit()),
            default=0,
        )
        return "%s%d" % (prefix, last + 1)

    def action_download_report(self):
        self.ensure_one()
        return self.env.ref(
            "gestion_servicios.action_report_correctivo"
        ).report_action(self)

    def action_send_email(self):
        """Abre el correo al cliente con el PDF del reporte adjunto."""
        self.ensure_one()
        template = self.env.ref("gestion_servicios.mail_template_correctivo")
        return {
            "type": "ir.actions.act_window",
            "name": "Enviar reporte por correo",
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


class ServicioCorrectivoLinea(models.Model):
    _name = "servicio.correctivo.linea"
    _description = "Trabajo realizado en el reporte correctivo"
    _order = "sequence, id"

    correctivo_id = fields.Many2one("servicio.correctivo", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    description = fields.Text(string="Trabajo realizado", required=True)
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "servicio_correctivo_linea_att_rel",
        "linea_id",
        "attachment_id",
        string="Fotos",
    )
    photo_count = fields.Integer(string="Fotos", compute="_compute_photo_count")

    @api.depends("attachment_ids")
    def _compute_photo_count(self):
        for line in self:
            line.photo_count = len(line.attachment_ids)


class ReportCorrectivo(models.AbstractModel):
    _name = "report.gestion_servicios.report_correctivo_document"
    _description = "Reporte PDF correctivo"

    @api.model
    def _get_report_values(self, docids, data=None):
        # Mismas funciones de fotos (tamaño, enlace a la foto grande) que la inspección
        values = self.env["report.gestion_servicios.report_inspeccion_document"]._get_report_values(
            [], data
        )
        values.update({
            "doc_ids": docids,
            "doc_model": "servicio.correctivo",
            "docs": self.env["servicio.correctivo"].browse(docids),
        })
        return values
