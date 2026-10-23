{
    "name": "Gestión de Inspecciones y Servicios",
    "version": "18.0.1.2.0",
    "summary": "Reportes de inspección y mantenimiento de equipos",
    "description": """
        Gestión de reportes de inspección de sistemas contra incendio,
        alarmas, detección y mantenimiento.
    """,
    "category": "Services",
    "author": "Personalizado",
    "license": "LGPL-3",
    "depends": ["base", "web", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/inspeccion_views.xml",
        "report/inspeccion_report.xml",
        "data/mail_template.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "gestion_servicios/static/src/scss/inspeccion.scss",
        ],
    },
    "application": True,
    "installable": True,
}
