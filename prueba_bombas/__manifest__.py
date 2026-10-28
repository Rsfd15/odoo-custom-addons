{
    "name": "Pruebas de Bombas Contra Incendios",
    "version": "20.0.1.0.0",
    "summary": "Fire Pump Test Results on Net Basis: mediciones, curva de rendimiento y reporte PDF",
    "description": """
        Registro de pruebas de rendimiento de bombas contra incendios:
        datos de la bomba, mediciones de campo (churn, 100 % y 150 %),
        cálculo de caudal por pitot, presión neta, corrección a velocidad
        nominal, curva CAMPO vs. PLACA y reporte PDF enviable por correo.
    """,
    "category": "Services",
    "author": "Personalizado",
    "license": "LGPL-3",
    "depends": ["base", "web", "mail"],
    "data": [
        "security/ir.access.csv",
        "data/sequence.xml",
        "views/prueba_bomba_views.xml",
        "report/prueba_bomba_report.xml",
        "data/mail_template.xml",
    ],
    "application": True,
    "installable": True,
}
