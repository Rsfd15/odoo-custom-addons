import base64
import math

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError

from .chart import interpolate, performance_curve_svg


# Constante de la fórmula de caudal por tubo pitot: Q = 29.83 · Cd · d² · √P
PITOT_CONSTANT = 29.83
PITOT_FIELDS = ["pitot_%d" % i for i in range(1, 9)]

POINT_SELECTION = [
    ("churn", "Churn (0 %)"),
    ("100", "100 %"),
    ("150", "150 %"),
    ("other", "Otro"),
]

RESULT_SELECTION = [
    ("pending", "Sin evaluar"),
    ("pass", "Aceptada"),
    ("fail", "No aceptada"),
]

CHECK_SELECTION = [
    ("na", "N/A"),
    ("pass", "Cumple"),
    ("fail", "No cumple"),
]


def _velocity(flow_gpm, diameter_in):
    """Velocidad del agua en ft/s para un caudal (gpm) y diámetro interior (in)."""
    if not flow_gpm or not diameter_in:
        return 0.0
    return 0.4085 * flow_gpm / diameter_in ** 2


def _velocity_head_psi(flow_gpm, diameter_in):
    """Carga de velocidad v²/2g expresada en psi."""
    v = _velocity(flow_gpm, diameter_in)
    return v ** 2 / (2 * 32.174) * 0.433


class BombaPrueba(models.Model):
    _name = "bomba.prueba"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Prueba de bomba contra incendios"
    _order = "test_date desc, id desc"

    name = fields.Char(string="Número de prueba", copy=False, readonly=True, default="Nuevo")
    state = fields.Selection(
        [("draft", "Borrador"), ("done", "Finalizada")],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
    )

    # ---------------- Datos generales ----------------
    customer_id = fields.Many2one("res.partner", string="Cliente", required=True, tracking=True)
    account = fields.Char(string="Cuenta (Account)")
    location = fields.Char(string="Ubicación", required=True)
    inspection_number = fields.Char(string="Inspección #")
    test_date = fields.Date(string="Fecha de la prueba", default=fields.Date.context_today, required=True)
    technician_id = fields.Many2one("res.users", string="Técnico", default=lambda self: self.env.user)
    customer_representative = fields.Char(string="Representante del cliente")

    # ---------------- Identificación de la bomba ----------------
    pump_type = fields.Char(string="Pump ID / Tipo", help="Ej. SPLIT CASE, END SUCTION, VERTICAL TURBINE")
    driver_type = fields.Selection(
        [("electric", "Motor eléctrico"), ("diesel", "Motor diésel")],
        string="Accionamiento",
        default="electric",
    )
    pump_make = fields.Char(string="Marca (Make)")
    pump_model = fields.Char(string="Modelo")
    serial_number = fields.Char(string="Número de serie")
    suction_size = fields.Float(string="Tamaño de succión (in)", digits=(6, 2))
    discharge_size = fields.Float(string="Tamaño de descarga (in)", digits=(6, 2))

    # ---------------- Valores nominales ----------------
    rated_flow = fields.Float(string="Caudal nominal (gpm)", digits=(10, 0))
    rated_pressure = fields.Float(string="Presión nominal (psi)", digits=(10, 0))
    rated_speed = fields.Float(string="Velocidad nominal (rpm)", digits=(10, 0))
    rated_volts = fields.Float(string="Voltaje nominal (V)", digits=(10, 0))
    rated_amps = fields.Float(string="Corriente nominal (A)", digits=(10, 1))

    # ---------------- Criterios de cálculo ----------------
    apply_speed_correction = fields.Boolean(
        string="Corregir a velocidad nominal",
        default=True,
        help="Aplica las leyes de afinidad: Q·(N nominal/N medida) y P·(N nominal/N medida)².",
    )
    net_includes_velocity_head = fields.Boolean(
        string="Sumar carga de velocidad a la presión neta",
        default=False,
        help="Si está marcado: neta = descarga − succión + carga de velocidad. "
             "Si no: neta = descarga − succión.",
    )
    acceptance_pct = fields.Float(
        string="Aceptación mínima vs. placa (%)",
        default=95.0,
        help="Porcentaje mínimo de la presión de placa que debe alcanzar cada punto medido "
             "(corregido a velocidad nominal).",
    )

    reading_ids = fields.One2many("bomba.prueba.lectura", "test_id", string="Mediciones de campo", copy=True)
    plate_ids = fields.One2many("bomba.prueba.placa", "test_id", string="Curva de placa", copy=True)

    # ---------------- Resultados ----------------
    chart_svg = fields.Html(string="Curva de rendimiento", compute="_compute_chart", sanitize=False)
    churn_check = fields.Selection(CHECK_SELECTION, string="Churn ≤ 140 % de la presión nominal", compute="_compute_result")
    overload_check = fields.Selection(CHECK_SELECTION, string="Al 150 % ≥ 65 % de la presión nominal", compute="_compute_result")
    plate_check = fields.Selection(CHECK_SELECTION, string="Puntos vs. curva de placa", compute="_compute_result")
    result = fields.Selection(RESULT_SELECTION, string="Resultado", compute="_compute_result")

    observations = fields.Text(string="Observaciones")
    recommendations = fields.Text(string="Recomendaciones")
    received_by = fields.Char(string="Reporte recibido por")

    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = self.env["ir.sequence"].next_by_code("bomba.prueba") or "Nuevo"
            if not vals.get("reading_ids"):
                vals["reading_ids"] = [
                    (0, 0, {"sequence": seq, "point_type": point})
                    for seq, point in ((10, "churn"), (20, "100"), (30, "150"))
                ]
        return super().create(vals_list)

    def _field_points(self):
        self.ensure_one()
        return [
            (r.corrected_flow, r.corrected_pressure)
            for r in self.reading_ids
            if r.discharge_psi or r.combined_flow
        ]

    def _plate_points(self):
        self.ensure_one()
        return [(p.flow, p.pressure) for p in self.plate_ids]

    @api.depends(
        "reading_ids.corrected_flow",
        "reading_ids.corrected_pressure",
        "plate_ids.flow",
        "plate_ids.pressure",
    )
    def _compute_chart(self):
        for rec in self:
            svg = performance_curve_svg(rec._field_points(), rec._plate_points())
            rec.chart_svg = Markup('<div style="overflow-x:auto;">%s</div>') % Markup(svg)

    @api.depends(
        "rated_pressure",
        "acceptance_pct",
        "reading_ids.point_type",
        "reading_ids.corrected_pressure",
        "reading_ids.plate_evaluation",
    )
    def _compute_result(self):
        for rec in self:
            measured = rec.reading_ids.filtered(lambda r: r.discharge_psi or r.combined_flow)
            churn = measured.filtered(lambda r: r.point_type == "churn")[:1]
            overload = measured.filtered(lambda r: r.point_type == "150")[:1]

            rec.churn_check = "na"
            if churn and rec.rated_pressure:
                rec.churn_check = (
                    "pass" if churn.corrected_pressure <= 1.40 * rec.rated_pressure else "fail"
                )
            rec.overload_check = "na"
            if overload and rec.rated_pressure:
                rec.overload_check = (
                    "pass" if overload.corrected_pressure >= 0.65 * rec.rated_pressure else "fail"
                )
            evaluated = measured.filtered(lambda r: r.plate_evaluation in ("pass", "fail"))
            rec.plate_check = "na"
            if evaluated:
                rec.plate_check = (
                    "fail" if any(r.plate_evaluation == "fail" for r in evaluated) else "pass"
                )

            checks = [rec.churn_check, rec.overload_check, rec.plate_check]
            if all(c == "na" for c in checks):
                rec.result = "pending"
            elif "fail" in checks:
                rec.result = "fail"
            else:
                rec.result = "pass"

    def chart_data_uri(self):
        """Gráfica como imagen embebida (wkhtmltopdf no dibuja bien el SVG en línea)."""
        self.ensure_one()
        svg = performance_curve_svg(self._field_points(), self._plate_points())
        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

    # ------------------------------------------------------------------
    def action_generate_plate(self):
        """Crea una curva de placa de referencia a partir de los valores nominales.

        Usa los puntos mínimos de NFPA 20 (0 %, 100 % y 150 % del caudal). Deben
        ajustarse con los valores de la curva certificada del fabricante.
        """
        for rec in self:
            if not rec.rated_flow or not rec.rated_pressure:
                raise UserError("Captura primero el caudal y la presión nominales de la bomba.")
            rec.plate_ids = [(5, 0, 0)] + [
                (0, 0, {"sequence": seq, "flow": rec.rated_flow * qf, "pressure": rec.rated_pressure * pf})
                for seq, qf, pf in ((10, 0.0, 1.20), (20, 1.0, 1.0), (30, 1.5, 0.65))
            ]
        return True

    def action_mark_done(self):
        for rec in self:
            if not rec._field_points():
                raise UserError("Captura al menos una medición de campo antes de finalizar la prueba.")
        self.write({"state": "done"})
        return True

    def action_reset_draft(self):
        self.write({"state": "draft"})
        return True

    def action_preview_report(self):
        self.ensure_one()
        return self.env.ref("prueba_bombas.action_report_prueba_bomba_html").report_action(self)

    def action_download_report(self):
        self.ensure_one()
        return self.env.ref("prueba_bombas.action_report_prueba_bomba").report_action(self)

    def action_send_email(self):
        """Abre el correo al cliente con el PDF de la prueba adjunto."""
        self.ensure_one()
        template = self.env.ref("prueba_bombas.mail_template_prueba_bomba")
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


class BombaPruebaLectura(models.Model):
    _name = "bomba.prueba.lectura"
    _description = "Medición de campo de la prueba de bomba"
    _order = "sequence, id"

    test_id = fields.Many2one("bomba.prueba", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    point_type = fields.Selection(POINT_SELECTION, string="Punto", default="other", required=True)

    outlet_diameter = fields.Selection(
        [("1.125", '1 1/8"'), ("1.75", '1 3/4"'), ("2.5", '2 1/2"')],
        string="Salida I.D.",
        help="Diámetro de la boquilla donde se toma la lectura pitot.",
    )
    cd = fields.Float(string="Cd", default=1.0, digits=(3, 2), help="Coeficiente de descarga de la boquilla.")
    pitot_1 = fields.Float(string="Pitot 1", digits=(6, 1))
    pitot_2 = fields.Float(string="Pitot 2", digits=(6, 1))
    pitot_3 = fields.Float(string="Pitot 3", digits=(6, 1))
    pitot_4 = fields.Float(string="Pitot 4", digits=(6, 1))
    pitot_5 = fields.Float(string="Pitot 5", digits=(6, 1))
    pitot_6 = fields.Float(string="Pitot 6", digits=(6, 1))
    pitot_7 = fields.Float(string="Pitot 7", digits=(6, 1))
    pitot_8 = fields.Float(string="Pitot 8", digits=(6, 1))
    flowmeter_gpm = fields.Float(string="Flujómetro (gpm)", digits=(10, 0))

    pitot_flow = fields.Float(string="Caudal pitot (gpm)", compute="_compute_flow", store=True, digits=(10, 0))
    combined_flow = fields.Float(string="Caudal combinado (gpm)", compute="_compute_flow", store=True, digits=(10, 0))

    suction_psi = fields.Float(string="Succión (psi)", digits=(6, 1))
    discharge_psi = fields.Float(string="Descarga (psi)", digits=(6, 1))
    velocity_head = fields.Float(
        string="Carga vel. (psi)",
        compute="_compute_velocity_head",
        store=True,
        readonly=False,
        digits=(6, 1),
        help="Se calcula con el caudal y los diámetros de succión y descarga; puede corregirse a mano.",
    )
    net_pressure = fields.Float(string="Presión neta (psi)", compute="_compute_net", store=True, digits=(6, 1))
    pump_speed = fields.Float(string="Velocidad (rpm)", digits=(10, 0))
    corrected_flow = fields.Float(string="Caudal corregido (gpm)", compute="_compute_corrected", store=True, digits=(10, 0))
    corrected_pressure = fields.Float(string="Presión corregida (psi)", compute="_compute_corrected", store=True, digits=(6, 1))
    volts = fields.Float(string="Volts (V)", digits=(6, 0))
    amps = fields.Float(string="Amps (A)", digits=(6, 1))

    plate_pressure = fields.Float(string="Presión de placa (psi)", compute="_compute_plate", digits=(6, 1))
    plate_pct = fields.Float(string="% vs. placa", compute="_compute_plate", digits=(6, 1))
    plate_evaluation = fields.Selection(CHECK_SELECTION, string="Evaluación", compute="_compute_plate")

    @api.depends("outlet_diameter", "cd", "flowmeter_gpm", *PITOT_FIELDS)
    def _compute_flow(self):
        for line in self:
            diameter = float(line.outlet_diameter or 0)
            pitot_flow = 0.0
            if diameter:
                for fname in PITOT_FIELDS:
                    psi = line[fname]
                    if psi > 0:
                        pitot_flow += PITOT_CONSTANT * (line.cd or 1.0) * diameter ** 2 * math.sqrt(psi)
            line.pitot_flow = pitot_flow
            line.combined_flow = line.flowmeter_gpm or pitot_flow

    @api.depends("combined_flow", "test_id.suction_size", "test_id.discharge_size")
    def _compute_velocity_head(self):
        for line in self:
            test = line.test_id
            head = _velocity_head_psi(line.combined_flow, test.discharge_size)
            head -= _velocity_head_psi(line.combined_flow, test.suction_size)
            line.velocity_head = round(max(head, 0.0), 1)

    @api.depends("suction_psi", "discharge_psi", "velocity_head", "test_id.net_includes_velocity_head")
    def _compute_net(self):
        for line in self:
            net = line.discharge_psi - line.suction_psi
            if line.test_id.net_includes_velocity_head:
                net += line.velocity_head
            line.net_pressure = net

    @api.depends(
        "combined_flow",
        "net_pressure",
        "pump_speed",
        "test_id.rated_speed",
        "test_id.apply_speed_correction",
    )
    def _compute_corrected(self):
        for line in self:
            test = line.test_id
            ratio = 1.0
            if test.apply_speed_correction and test.rated_speed and line.pump_speed:
                ratio = test.rated_speed / line.pump_speed
            line.corrected_flow = line.combined_flow * ratio
            line.corrected_pressure = line.net_pressure * ratio ** 2

    @api.depends(
        "corrected_flow",
        "corrected_pressure",
        "test_id.plate_ids.flow",
        "test_id.plate_ids.pressure",
        "test_id.acceptance_pct",
    )
    def _compute_plate(self):
        for line in self:
            line.plate_pressure = 0.0
            line.plate_pct = 0.0
            line.plate_evaluation = "na"
            if not (line.discharge_psi or line.combined_flow):
                continue
            reference = interpolate(line.test_id._plate_points(), line.corrected_flow)
            if not reference:
                continue
            line.plate_pressure = reference
            line.plate_pct = line.corrected_pressure / reference * 100.0
            line.plate_evaluation = "pass" if line.plate_pct >= line.test_id.acceptance_pct else "fail"

    def outlet_label(self):
        self.ensure_one()
        return dict(self._fields["outlet_diameter"].selection).get(self.outlet_diameter, "N/A")


class BombaPruebaPlaca(models.Model):
    _name = "bomba.prueba.placa"
    _description = "Punto de la curva de placa de la bomba"
    _order = "flow, sequence, id"

    test_id = fields.Many2one("bomba.prueba", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    flow = fields.Float(string="Caudal (gpm)", digits=(10, 0))
    pressure = fields.Float(string="Presión neta (psi)", digits=(6, 1))
