from odoo import _, api, fields, models
from odoo.exceptions import UserError


class IncentiveBulkAssignWizard(models.TransientModel):
    _name = 'incentive.bulk.assign.wizard'
    _description = 'Bulk Assign Balances to Admission Officer'

    enrollment_ids = fields.Many2many('student.enrollment', string='Students', readonly=True)
    enrollment_count = fields.Integer(compute='_compute_enrollment_count')
    officer_id = fields.Many2one(
        'hr.employee', string='Assign To',
        domain=lambda self: [
            ('id', 'in', self.env['lead.team.member'].sudo().search([]).mapped('employee_id').ids)
        ],
    )

    @api.depends('enrollment_ids')
    def _compute_enrollment_count(self):
        for rec in self:
            rec.enrollment_count = len(rec.enrollment_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids') or []
        if active_ids:
            res['enrollment_ids'] = [(6, 0, active_ids)]
        return res

    def action_open_wizard(self):
        return {
            'name': _('Bulk Assign to Admission Officer'),
            'type': 'ir.actions.act_window',
            'res_model': 'incentive.bulk.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_ids': self.env.context.get('active_ids', [])},
        }

    def action_bulk_assign(self):
        self.ensure_one()
        if not self.enrollment_ids:
            raise UserError(_(
                "No students selected. Please close and select students "
                "from the list first."
            ))
        if not self.officer_id:
            raise UserError(_("Please select an Admission Officer."))
        self.enrollment_ids.write({
            'assigned_officer_id': self.officer_id.id,
            'assigned_officer_date': fields.Datetime.now(),
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bulk Assignment Done'),
                'message': _('%d student(s) assigned to %s.') % (
                    len(self.enrollment_ids), self.officer_id.name
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
