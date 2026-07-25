from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

PAYMENT_MODES = [
    ('cash', 'Cash'),
    ('bank_transfer', 'Bank Transfer'),
    ('upi', 'UPI'),
    ('cheque', 'Cheque'),
    ('other', 'Other'),
]


class IncentivePayout(models.Model):
    """One record per officer per month — the manager approves the
    calculated incentive and pays it out, possibly in several
    installments (payment_line_ids), the same shape as
    agent.wallet.transaction in agent_management_19."""
    _name = 'incentive.payout'
    _description = 'Admission Officer Incentive Payout'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'year desc, month desc, id desc'
    _rec_name = 'display_name'

    officer_id = fields.Many2one('hr.employee', required=True, readonly=True, tracking=True)
    year = fields.Integer(required=True, readonly=True)
    month = fields.Integer(required=True, readonly=True)
    period_label = fields.Char(compute='_compute_period_label', store=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)

    # Snapshot at generation time — the payout must not silently change
    # if new payments get recorded later against the same period.
    collected_amount = fields.Float(string='Collected ₹', readonly=True)
    slab_name = fields.Char(readonly=True)
    slab_percentage = fields.Float(readonly=True)
    incentive_amount = fields.Float(string='Incentive Earned ₹', required=True, readonly=True, tracking=True)

    payment_line_ids = fields.One2many('incentive.payout.line', 'payout_id', string='Payments')
    paid_amount = fields.Float(
        string='Paid ₹', compute='_compute_amounts', store=True, digits=(10, 2))
    balance_amount = fields.Float(
        string='Balance ₹', compute='_compute_amounts', store=True, digits=(10, 2))

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True, copy=False)

    approved_by = fields.Many2one('res.users', readonly=True, copy=False)
    approved_date = fields.Datetime(readonly=True, copy=False)
    notes = fields.Text()

    _sql_constraints = [
        ('officer_period_unique', 'unique(officer_id, year, month)',
         'A payout already exists for this officer and month.'),
    ]

    @api.depends('year', 'month')
    def _compute_period_label(self):
        names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                 'July', 'August', 'September', 'October', 'November', 'December']
        for rec in self:
            rec.period_label = f"{names[rec.month]} {rec.year}" if rec.month else ''

    @api.depends('officer_id', 'period_label')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.officer_id.name} — {rec.period_label}"

    @api.depends('payment_line_ids.amount', 'incentive_amount', 'state')
    def _compute_amounts(self):
        for rec in self:
            paid = sum(rec.payment_line_ids.mapped('amount'))
            rec.paid_amount = paid
            rec.balance_amount = round(rec.incentive_amount - paid, 2)

    @api.constrains('payment_line_ids', 'incentive_amount')
    def _check_payment_lines_not_over(self):
        for rec in self:
            paid = sum(rec.payment_line_ids.mapped('amount'))
            if paid - rec.incentive_amount > 0.01:
                raise ValidationError(_(
                    "Total payments (₹%(paid)s) cannot exceed the incentive "
                    "amount (₹%(amt)s) for %(name)s."
                ) % {'paid': paid, 'amt': rec.incentive_amount, 'name': rec.display_name})

    def _sync_state_from_payments(self):
        for rec in self:
            if rec.state in ('draft', 'cancelled'):
                continue
            if rec.paid_amount <= 0:
                new_state = 'approved'
            elif rec.balance_amount <= 0.01:
                new_state = 'paid'
            else:
                new_state = 'partially_paid'
            if rec.state != new_state:
                rec.state = new_state

    def action_approve(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only draft payouts can be approved."))
            rec.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            rec.message_post(body=_("Incentive approved: ₹%s") % rec.incentive_amount)

    def action_cancel(self):
        for rec in self:
            if rec.paid_amount > 0:
                raise UserError(_("Cannot cancel a payout that already has payments recorded."))
            rec.state = 'cancelled'

    def write(self, vals):
        res = super().write(vals)
        if 'payment_line_ids' in vals:
            self._sync_state_from_payments()
        return res


class IncentivePayoutLine(models.Model):
    _name = 'incentive.payout.line'
    _description = 'Incentive Payout — Payment Line'
    _order = 'payment_date desc, id desc'

    payout_id = fields.Many2one('incentive.payout', required=True, ondelete='cascade')
    amount = fields.Float(required=True, digits=(10, 2))
    payment_date = fields.Date(default=fields.Date.today, required=True)
    payment_mode = fields.Selection(PAYMENT_MODES, default='bank_transfer', required=True)
    remarks = fields.Char()
    paid_by = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)

    @api.constrains('amount')
    def _check_amount_positive(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("Payment amount must be greater than zero."))
