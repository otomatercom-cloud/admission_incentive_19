from odoo import _, api, fields, models


class StudentEnrollmentOfficerAssignment(models.Model):
    _inherit = 'student.enrollment'

    assigned_officer_id = fields.Many2one(
        'hr.employee', string='Assigned Admission Officer', tracking=True,
        domain="[('id', 'in', assignable_officer_ids)]",
        help="The officer following up to collect this student's "
             "remaining balance. Uses the same Admission Officer roster "
             "as the call center (lead.team.member).",
    )
    assigned_officer_date = fields.Datetime(
        string='Assigned On', readonly=True, copy=False)
    assignable_officer_ids = fields.Many2many(
        'hr.employee', compute='_compute_assignable_officers')

    @api.depends_context('uid')
    def _compute_assignable_officers(self):
        officers = self.env['lead.team.member'].sudo().search([]).mapped('employee_id')
        for rec in self:
            rec.assignable_officer_ids = officers

    def write(self, vals):
        if vals.get('assigned_officer_id'):
            vals.setdefault('assigned_officer_date', fields.Datetime.now())
        return super().write(vals)
