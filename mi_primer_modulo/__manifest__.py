{
    "name": "Mi Primer Módulo",
    "version": "18.0.1.0.0",
    "category": "Tools",
    "summary": "Mi primer módulo personalizado de Odoo",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/mi_modelo_views.xml",
    ],
    "installable": True,
    "application": True,
}