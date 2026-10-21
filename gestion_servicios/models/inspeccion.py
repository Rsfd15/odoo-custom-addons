import base64

from odoo import api, fields, models
from odoo.tools.image import image_data_uri


SECTION_SELECTION = [
    ("detail", "1. Detalle del servicio"),
    ("system_type", "2. Tipo de sistemas"),
    (
        "alarm_inspection",
        "3. Inspección a sistemas de alarmas y detección de incendios",
    ),
    (
        "fire_protection",
        "4. Inspección de asistencia de protección contra incendios",
    ),
    (
        "kitchen_suppression",
        "5. Inspección a sistemas de supresión de incendios de cocina (ANSUL)",
    ),
    ("general_observations", "6. Observaciones generales de servicio"),
    ("conclusion", "7. Conclusión y recomendaciones del servicio"),
    ("equipment_status", "8. Equipo o sistema quedan en"),
    ("training", "9. Capacitación"),
    ("customer_evaluation", "10. Evaluación por parte del cliente"),
    ("received_by", "11. Recibido por"),
]

SECTION_ORDER = [key for key, _label in SECTION_SELECTION]

# Grupos (barras desplegables) de la sección 3
SUBSECTION_SELECTION = [
    ("panel", "Panel de alarmas"),
    ("power", "Fuente de poder auxiliar"),
    ("smoke", "Detectores de humo"),
    ("gas", "Detectores de gas"),
    ("manual", "Estaciones manuales"),
    ("module", "Módulos"),
    ("audiovisual", "Alarmas audiovisuales"),
    # Sección 4
    ("riser", "Tubería vertical (Risers)"),
    ("sprinkler", "Rociadores"),
    ("hydrant", "Red de hidrantes"),
    ("water", "Alimentación de agua"),
    ("diesel", "Bomba diésel"),
    ("electric", "Bomba eléctrica"),
    ("jockey", "Bomba jockey"),
    ("pumproom", "Cuarto de bombas"),
]

# Prefijo de la pregunta (texto antes de los dos puntos) -> grupo
SUBSECTION_PREFIXES = {
    "Panel de alarmas": "panel",
    "Fuente de poder auxiliar": "power",
    "Detectores de humo": "smoke",
    "Detectores de gas": "gas",
    "Detectores de dióxido de carbono": "gas",
    "Estaciones manuales": "manual",
    "Módulos": "module",
    "Módulos relay": "module",
    "Alarmas audiovisuales": "audiovisual",
    # Sección 4
    "Tubería vertical (Risers)": "riser",
    "Rociadores": "sprinkler",
    "Red de hidrantes": "hydrant",
    "Alimentación de agua": "water",
    "Bomba diésel": "diesel",
    "Bomba eléctrica": "electric",
    "Bomba jockey": "jockey",
    "Cuarto de bombas": "pumproom",
}

SECTION_QUESTIONS = {
    "detail": [
        "Tipo de reporte",
        "Cliente",
        "Ubicación",
        "Fecha de realización",
        "Nombre del técnico",
        "Nombre de representante del cliente",
        "Número de reporte",
    ],
    "system_type": ["Tipo de sistema"],
    "alarm_inspection": [
        "Panel de alarmas: ¿está encendido y operando?",
        "Panel de alarmas: cantidad y ubicación de cada panel",
        "Panel de alarmas: marcas y modelos",
        "Panel de alarmas: ¿se encuentra sin problemas o alarmas activas? Incluya fallas, códigos y acción correctiva sugerida.",
        "Panel de alarmas: ¿la integridad del gabinete es óptima?",
        "Panel de alarmas: ¿funcionan correctamente los indicadores LED?",
        "Panel de alarmas: ¿funcionan correctamente el display y teclado?",
        "Panel de alarmas: ¿los voltajes de corriente directa son correctos? Indique valores.",
        "Panel de alarmas: ¿la alimentación de 120 VCA es regulada, tiene tres hilos, circuito dedicado e identificado?",
        "Panel de alarmas: ¿la conexión de terminales, lazos y fuente está completa y funciona correctamente?",
        "Panel de alarmas: indique si el estado de las baterías es adecuado.",
        "Panel de alarmas: ¿se cuenta con la fecha de cambio de baterías?",
        "Panel de alarmas: observaciones",
        "Fuente de poder auxiliar: cantidad y ubicación",
        "Fuente de poder auxiliar: ¿el estado físico es óptimo?",
        "Fuente de poder auxiliar: indique el tipo de daño, si aplica.",
        "Fuente de poder auxiliar: indique el estado de las baterías.",
        "Fuente de poder auxiliar: ¿el voltaje NAC es óptimo?",
        "Fuente de poder auxiliar: ¿se cuenta con la fecha de cambio de baterías?",
        "Fuente de poder auxiliar: observaciones",
        "Detectores de humo: ¿reportan correctamente al panel?",
        "Detectores de humo: ¿el estado físico es óptimo?",
        "Detectores de humo: ¿se realizaron pruebas?",
        "Detectores de humo: ¿existen detectores autónomos de CA y baterías? Indique cantidad.",
        "Detectores de humo: indique otras áreas si no están solamente en habitaciones.",
        "Detectores de humo: observaciones",
        "Detectores de gas: ¿la instalación cuenta con detectores direccionados?",
        "Detectores de gas: indique su estado.",
        "Detectores de dióxido de carbono: ¿la instalación cuenta con detectores direccionados?",
        "Detectores de dióxido de carbono: indique su estado.",
        "Detectores de gas: resultados de pruebas con gas patrón, si aplica.",
        "Detectores de gas: observaciones",
        "Estaciones manuales: indique su estado.",
        "Estaciones manuales: indique el resultado de las pruebas.",
        "Estaciones manuales: observaciones",
        "Módulos: indique el estado de los módulos de control.",
        "Módulos: indique el estado de los módulos de supervisión.",
        "Módulos: indique si existen módulos relay y dónde están instalados.",
        "Módulos relay: indique el resultado de la prueba, si aplica.",
        "Alarmas audiovisuales: indique su estado.",
        "Alarmas audiovisuales: ¿existe alarma en la habitación de personas con discapacidad?",
        "Alarmas audiovisuales: resultado de las pruebas de activación.",
        "Alarmas audiovisuales: observaciones",
    ],
    "fire_protection": [
        "Tubería vertical (Risers): ¿Las válvulas del riser están identificadas correctamente?",
        "Tubería vertical (Risers): ¿Las válvulas operan suavemente (abren y cierran completamente sin dificultad)?",
        "Tubería vertical (Risers): ¿Las válvulas de control se encuentran supervisadas y/o aseguradas?",
        "Tubería vertical (Risers): ¿La tubería se encuentra libre de corrosión visible o desgaste?",
        "Tubería vertical (Risers): ¿La tubería está libre de fugas, humedad o rastros de filtración?",
        "Tubería vertical (Risers): ¿Los soportes y abrazaderas están firmes y en buen estado?",
        "Tubería vertical (Risers): ¿El sistema mantiene presión adecuada, indique la presión?",
        "Tubería vertical (Risers): Observaciones",
        "Rociadores: Indique el estado físico de los rociadores.",
        "Rociadores: ¿Los rociadores están libres de obstrucciones que puedan afectar su funcionamiento?",
        "Rociadores: ¿Los rociadores se encuentran correctamente instalados?",
        "Rociadores: Observaciones",
        "Red de hidrantes: Indique la cantidad de hidrantes. Compartir foto de evidencia con número de hidrantes ya con tarjeta de inspección nueva.",
        "Red de hidrantes: ¿El estado de las mangueras de hidrantes es correcto?",
        "Red de hidrantes: ¿Válvulas angulares se encuentran en buen estado y sin fuga?",
        "Red de hidrantes: La accesibilidad al hidrante no presenta obstrucciones.",
        "Red de hidrantes: ¿Están completos los accesorios de hidrante (chiflón, llave spanner, manguera, señalamiento)? Si falta algún accesorio o se encuentra en mal estado indique su ubicación, qué le falta, o cuál es el daño que tiene.",
        "Red de hidrantes: ¿El estado de gabinetes (acrílico, soporte, pintura, bisagras y cerradura) es óptimo?",
        "Red de hidrantes: ¿La presión y condiciones de operación son correctas?",
        "Red de hidrantes: ¿Cuenta con toma siamesa? Favor de compartir fotos.",
        "Red de hidrantes: Observaciones",
        "Alimentación de agua: ¿Se encuentra en funcionamiento la alimentación de agua del sistema?",
        "Alimentación de agua: ¿Se cuenta con la capacidad necesaria para el edificio? (85 mt3 mínimo)",
        "Alimentación de agua: Indique el nivel de agua en la cisterna.",
        "Alimentación de agua: Observaciones",
        "Bomba diésel: ¿Se cuenta con bomba de combustión? Enviar foto de la placa",
        "Bomba diésel: ¿La bomba de combustión está siendo monitoreada por el panel de alarmas?",
        "Bomba diésel: ¿El equipo se encuentra en automático?",
        "Bomba diésel: ¿Los niveles de aceite son correctos?",
        "Bomba diésel: ¿Los niveles de anticongelante son correctos?",
        "Bomba diésel: ¿El estado de las baterías es correcto?",
        "Bomba diésel: ¿El nivel de combustible en el tanque diésel es el adecuado, mínimo 3/4?",
        "Bomba diésel: Indique el resultado de la revisión al sistema de enfriamiento.",
        "Bomba diésel: ¿Se encuentran las válvulas del sistema de enfriamiento en su posición correcta?",
        "Bomba diésel: ¿La temperatura del motor diésel es correcta? (mín. 35° C)",
        "Bomba diésel: ¿Al realizarse la limpieza del equipo se detectaron fugas? Indique la ubicación de las fugas encontradas.",
        "Bomba diésel: ¿Realizó los 6 intentos de arranque indicados por NFPA? (de forma anual)",
        "Bomba diésel: Indique el estado del funcionamiento del tablero del motor.",
        "Bomba diésel: Indique el resultado de la prueba al tablero del motor (de forma anual).",
        "Bomba diésel: ¿Tubería de escape se encuentra en buenas condiciones?",
        "Bomba diésel: Indique el resultado de las pruebas de arranque de la bomba diésel.",
        "Bomba diésel: ¿Cuenta el equipo con línea de pruebas Venturi?",
        "Bomba diésel: Indique si se realizó la prueba de eficiencia a la bomba (de forma anual).",
        "Bomba eléctrica: ¿Se cuenta con bomba eléctrica? Enviar foto de la placa",
        "Bomba eléctrica: ¿El controlador de la bomba eléctrica está siendo monitoreado desde el panel de alarmas?",
        "Bomba eléctrica: ¿El controlador de la bomba eléctrica se encuentra en automático?",
        "Bomba eléctrica: Indique el estado del motor eléctrico.",
        "Bomba eléctrica: Indique si el enfriamiento del motor es el adecuado. (En caso de aceite indique el nivel)",
        "Bomba eléctrica: ¿Cuenta con válvula de alivio a la descarga de la bomba?",
        "Bomba eléctrica: Indique el resultado de las pruebas de arranque a la bomba eléctrica.",
        "Bomba jockey: Indique el estado de la bomba jockey (envíe foto de la placa).",
        "Bomba jockey: Indique si está en automático el controlador de la bomba jockey.",
        "Bomba jockey: Indique los hallazgos al realizar la limpieza de bomba jockey y su controlador.",
        "Bomba jockey: Indique el funcionamiento de bomba jockey en manual y en automático.",
        "Cuarto de bombas: ¿Las condiciones del cuarto de bombas son aceptables para realizar operación del equipo?",
        "Cuarto de bombas: ¿El cuarto de bombas cuenta con sistema de ventilación?",
        "Cuarto de bombas: ¿Las válvulas de succión y descarga de las bombas se encuentran abiertas, aseguradas y/o supervisadas?",
        "Cuarto de bombas: ¿Las condiciones de tuberías de succión y descarga del cuarto de bombas son óptimas?",
        "Cuarto de bombas: Observaciones",
    ],
    "kitchen_suppression": [
        "¿Cuántos sistemas de supresión de cocina están instalados?",
        "¿El sistema de supresión de incendios en cocina está en operación?",
        "¿Se cuenta con válvulas de corte de gas? Indique su estado.",
        "¿El estado de los cilindros y sus conexiones son óptimos?",
        "¿El estado de las boquillas de descarga es óptimo y se encuentran alineadas?",
        "Indique el estado de las estaciones manuales y si cuenta con testigo.",
        "¿Las boquillas cuentan con tapones?",
        "Verifique el estado del cartucho de nitrógeno, indique peso y fecha de prueba hidrostática.",
        "Verifique el estado del tanque de Ansulex (indique su hermeticidad y sello).",
        "¿Se realizó el cambio de los fusibles?",
        "Indique el resultado de las pruebas de activación sin descarga.",
        "Observaciones",
    ],
    "training": ["¿Se impartió capacitación?"],
    "customer_evaluation": [
        "¿Cómo considera la calidad del servicio?",
        "¿Cómo considera el conocimiento del técnico sobre los sistemas?",
        "¿Cómo considera la comunicación del técnico?",
        "¿Cómo considera la presentación del técnico?",
        "Escriba alguna queja, sugerencia o cómo le pareció el servicio.",
    ],
}

# Las 4 primeras preguntas de la sección 10 se responden con calificación
RATING_QUESTIONS = set(SECTION_QUESTIONS["customer_evaluation"][:4])

RATING_SELECTION = [
    ("excellent", "Excelente"),
    ("very_good", "Muy bueno"),
    ("acceptable", "Aceptable"),
    ("regular", "Regular"),
]


class ServicioInspeccion(models.Model):
    _name = "servicio.inspeccion"
    _description = "Reporte de inspección de servicios"
    _order = "create_date desc"

    name = fields.Char(
        string="Número de reporte",
        copy=False,
        readonly=True,
        default="Nuevo",
    )
    state = fields.Selection(
        [("draft", "Borrador"), ("in_progress", "En inspección"), ("done", "Finalizado")],
        string="Estado",
        default="draft",
        required=True,
    )
    section = fields.Selection(
        SECTION_SELECTION,
        string="Sección actual",
        default="detail",
        required=True,
    )
    report_type = fields.Char(string="Tipo de reporte", required=True)
    customer_id = fields.Many2one("res.partner", string="Cliente", required=True)
    location = fields.Char(string="Ubicación", required=True)
    inspection_date = fields.Date(string="Fecha de realización", default=fields.Date.context_today)
    technician_id = fields.Many2one(
        "res.users", string="Nombre del técnico", default=lambda self: self.env.user, required=True
    )
    customer_representative = fields.Char(string="Representante del cliente")
    system_type = fields.Selection(
        [("fire", "Sistema contra incendio"), ("alarm", "Sistema de alarmas y detección"), ("kitchen", "Sistema de supresión en cocina")],
        string="Tipo de sistema",
        required=True,
        default="alarm",
    )
    inspection_item_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id", string="Respuestas de inspección", copy=True
    )

    # Un campo por cada barra desplegable de la sección 3
    item_panel_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("subsection", "=", "panel")], string="Panel de alarmas")
    item_power_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("subsection", "=", "power")], string="Fuente de poder auxiliar")
    item_smoke_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("subsection", "=", "smoke")], string="Detectores de humo")
    item_gas_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("subsection", "=", "gas")], string="Detectores de gas")
    item_manual_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("subsection", "=", "manual")], string="Estaciones manuales")
    item_module_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("subsection", "=", "module")], string="Módulos")
    item_audiovisual_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("subsection", "=", "audiovisual")], string="Alarmas audiovisuales")

    item_riser_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("subsection", "=", "riser")], string="Tubería vertical (Risers)")
    item_sprinkler_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("subsection", "=", "sprinkler")], string="Rociadores")
    item_hydrant_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("subsection", "=", "hydrant")], string="Red de hidrantes")
    item_water_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("subsection", "=", "water")], string="Alimentación de agua")
    item_diesel_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("subsection", "=", "diesel")], string="Bomba diésel")
    item_electric_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("subsection", "=", "electric")], string="Bomba eléctrica")
    item_jockey_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("subsection", "=", "jockey")], string="Bomba jockey")
    item_pumproom_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("subsection", "=", "pumproom")], string="Cuarto de bombas")

    # Sección 5, 9 y 10 (listas)
    item_kitchen_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("section", "=", "kitchen_suppression")], string="Supresión de cocina")
    item_training_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("section", "=", "training")], string="Capacitación")
    item_evaluation_ids = fields.One2many(
        "servicio.inspeccion.item", "inspection_id",
        domain=[("section", "=", "customer_evaluation")], string="Evaluación del cliente")

    # Sección 6: Observaciones generales de servicio
    observations_text = fields.Text(string="Deficiencias encontradas")
    observations_note = fields.Text(string="Nota")
    observations_attachment_ids = fields.Many2many("ir.attachment", "servicio_insp_obs_att_rel", string="Archivos multimedia")

    # Sección 7: Conclusión y recomendaciones
    recommendations_text = fields.Text(string="Recomendaciones generales")
    recommendations_note = fields.Text(string="Nota")
    recommendations_attachment_ids = fields.Many2many("ir.attachment", "servicio_insp_rec_att_rel", string="Archivos multimedia")

    # Sección 8: Equipo o sistema quedan en
    equipment_status_text = fields.Text(string="Estado en que quedan los equipos")
    equipment_status_note = fields.Text(string="Nota")
    equipment_status_attachment_ids = fields.Many2many("ir.attachment", "servicio_insp_eq_att_rel", string="Archivos multimedia")

    # Sección 11: Recibido por
    report_made_by = fields.Char(
        string="Reporte elaborado por", default=lambda self: self.env.user.name)
    report_made_signature = fields.Binary(
        string="Firma de quien elabora", attachment=True, copy=False)
    report_date = fields.Date(string="Fecha", default=fields.Date.context_today)
    report_received_by = fields.Char(string="Reporte recibido por")
    report_received_signature = fields.Binary(
        string="Firma de quien recibe", attachment=True, copy=False)
    received_note = fields.Text(string="Nota")
    received_attachment_ids = fields.Many2many("ir.attachment", "servicio_insp_recv_att_rel", string="Archivos multimedia")

    notes = fields.Text(string="Observaciones generales")
    attachment_ids = fields.Many2many("ir.attachment", string="Archivos multimedia")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = self.env["ir.sequence"].next_by_code("servicio.inspeccion") or "Nuevo"
        records = super().create(vals_list)
        records._ensure_section_items()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "section" in vals:
            self._ensure_section_items()
        return result

    def _ensure_section_items(self):
        line_model = self.env["servicio.inspeccion.item"]
        for record in self:
            existing = set(record.inspection_item_ids.mapped("section"))
            for section, questions in SECTION_QUESTIONS.items():
                if section in existing:
                    continue
                line_model.create([
                    {
                        "inspection_id": record.id,
                        "section": section,
                        "sequence": index,
                        "question": question,
                        "answer_type": "rating" if question in RATING_QUESTIONS else "text",
                    }
                    for index, question in enumerate(questions, 1)
                ])

    def _move_section(self, offset):
        for record in self:
            current = SECTION_ORDER.index(record.section)
            target = max(0, min(len(SECTION_ORDER) - 1, current + offset))
            record.section = SECTION_ORDER[target]
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_next_section(self):
        return self._move_section(1)

    def action_previous_section(self):
        return self._move_section(-1)

    def action_start_inspection(self):
        self.write({"state": "in_progress"})
        return True

    def action_complete_inspection(self):
        self.write({"state": "done"})
        return True

    def action_download_report(self):
        self.ensure_one()
        return self.env.ref(
            "gestion_servicios.action_report_inspeccion"
        ).report_action(self)


class ServicioInspeccionItem(models.Model):
    _name = "servicio.inspeccion.item"
    _description = "Respuesta de inspección de servicio"
    _order = "section, sequence, id"

    inspection_id = fields.Many2one("servicio.inspeccion", required=True, ondelete="cascade")
    section = fields.Selection(SECTION_SELECTION, required=True, index=True)
    subsection = fields.Selection(
        SUBSECTION_SELECTION,
        string="Grupo",
        compute="_compute_subsection",
        store=True,
        index=True,
    )
    sequence = fields.Integer(default=10)
    question = fields.Char(string="Pregunta", required=True, readonly=True)
    answer = fields.Text(string="Respuesta")
    answer_type = fields.Selection(
        [("text", "Texto"), ("rating", "Calificación")],
        default="text",
        required=True,
    )
    rating = fields.Selection(RATING_SELECTION, string="Calificación")
    note = fields.Text(string="Nota")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "servicio_inspeccion_item_attachment_rel",
        "item_id",
        "attachment_id",
        string="Archivos multimedia",
    )

    question_short = fields.Char(
        string="Pregunta",
        compute="_compute_question_short",
    )

    @api.depends("question", "section")
    def _compute_question_short(self):
        for item in self:
            text = item.question or ""
            if item.section in ("alarm_inspection", "fire_protection") and ":" in text:
                prefix, rest = text.split(":", 1)
                if prefix.strip() in SUBSECTION_PREFIXES:
                    text = rest.strip()
                    text = text[:1].upper() + text[1:]
            item.question_short = text

    @api.depends("question", "section")
    def _compute_subsection(self):
        for item in self:
            prefix = (item.question or "").split(":")[0].strip()
            item.subsection = (
                SUBSECTION_PREFIXES.get(prefix)
                if item.section in ("alarm_inspection", "fire_protection")
                else False
            )



# ======================= REPORTE PDF =======================

def _section_items(doc, section):
    return doc.inspection_item_ids.filtered(
        lambda i: i.section == section
    ).sorted(lambda i: (i.sequence, i.id))


def _grouped_items(doc, section):
    """Devuelve [(titulo_de_la_barra, renglones), ...] de una sección."""
    items = _section_items(doc, section)
    result = []
    for key, label in SUBSECTION_SELECTION:
        group = items.filtered(lambda i, k=key: i.subsection == k)
        if group:
            result.append((label, group))
    rest = items.filtered(lambda i: not i.subsection)
    if rest:
        result.append(("Otros", rest))
    return result


def _is_image(attachment):
    return (attachment.mimetype or "").startswith("image/")


def _image_uri(attachment):
    """Construye una data URI usando la utilidad estándar de Odoo."""
    att = attachment.sudo()
    if not _is_image(att) or not att.datas:
        return ""
    try:
        return image_data_uri(att.datas)
    except (TypeError, ValueError, UnicodeDecodeError):
        return ""


def _attachment_url(attachment):
    """URL de respaldo para archivos que no se incrustan en el PDF."""
    return "/web/content/%s?download=true" % attachment.sudo().id


def _signature_uri(value):
    if not value:
        return ""
    if isinstance(value, bytes):
        value = value.decode()
    return "data:image/png;base64," + value


class ReportInspeccion(models.AbstractModel):
    _name = "report.gestion_servicios.report_inspeccion_document"
    _description = "Reporte PDF de inspección de servicio"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["servicio.inspeccion"].browse(docids)
        return {
            "doc_ids": docids,
            "doc_model": "servicio.inspeccion",
            "docs": docs,
            "section_items": _section_items,
            "grouped": _grouped_items,
            "is_image": _is_image,
            "image_uri": _image_uri,
            "signature_uri": _signature_uri,
        }