{
    'name': 'Admission Officer Incentive',
    'version': '19.0.1.0.0',
    'summary': 'Slab-based monthly collection incentive for Admission Officers, following custom_leads_19 call-center team structure',
    'description': """
        Admission Officers get assigned partially-paid students (via
        student.enrollment) to follow up on for balance collection, using
        the same Admission Officer roster as custom_leads_19's call
        center (lead.team.member / hr.employee). Each month, an officer's
        total collected amount is matched against a configurable slab
        table (e.g. ₹1L → 3%, ₹1.25L → 4%) to compute their incentive —
        the whole collected amount is paid at whichever slab it reaches,
        not a marginal/bracket calculation. The dashboard also shows the
        potential incentive if every assigned balance were fully collected.
    """,
    'author': 'Ajesh',
    'category': 'Human Resources',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'hr', 'student_details_19', 'custom_leads_19'],
    'data': [
        'security/incentive_security.xml',
        'security/ir.model.access.csv',
        'wizard/bulk_assign_wizard_views.xml',
        'views/incentive_slab_views.xml',
        'views/enrollment_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'admission_incentive_19/static/src/css/incentive_dashboard.css',
            'admission_incentive_19/static/src/js/incentive_dashboard.js',
            'admission_incentive_19/static/src/xml/incentive_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
