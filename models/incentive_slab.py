from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class IncentiveSlab(models.Model):
    """A collection-amount tier. The officer's ENTIRE collected amount for
    the month is paid at whichever slab it reaches — e.g. cross ₹1.25L and
    the whole ₹1.25L is commissioned at that slab's %, not just the
    portion above ₹1L. This is deliberately not marginal/bracket-style."""
    _name = 'incentive.slab'
    _description = 'Admission Officer Incentive Slab'
    _order = 'from_amount'

    name = fields.Char(required=True)
    from_amount = fields.Float(string='From ₹', required=True)
    to_amount = fields.Float(
        string='To ₹', help="Leave 0 for no upper limit (open-ended top slab).")
    percentage = fields.Float(string='Incentive %', required=True)
    active = fields.Boolean(default=True)

    @api.constrains('from_amount', 'to_amount', 'active')
    def _check_no_overlap(self):
        for rec in self.filtered('active'):
            others = self.search([
                ('id', '!=', rec.id), ('active', '=', True),
            ])
            for other in others:
                other_to = other.to_amount or float('inf')
                rec_to = rec.to_amount or float('inf')
                if rec.from_amount < other_to and other.from_amount < rec_to:
                    raise ValidationError(_(
                        "Slab '%(name)s' (₹%(f)s–%(t)s) overlaps with "
                        "'%(oname)s' (₹%(of)s–%(ot)s)."
                    ) % {
                        'name': rec.name, 'f': rec.from_amount,
                        't': rec.to_amount or '∞',
                        'oname': other.name, 'of': other.from_amount,
                        'ot': other.to_amount or '∞',
                    })

    @api.model
    def get_slab_for_amount(self, amount):
        """The highest slab whose from_amount the collected amount
        reaches — the whole amount is commissioned at this slab's %."""
        slabs = self.search([('active', '=', True), ('from_amount', '<=', amount)],
                             order='from_amount desc', limit=1)
        return slabs

    @api.model
    def calculate_incentive(self, amount):
        slab = self.get_slab_for_amount(amount)
        if not slab:
            return 0.0, False
        return round(amount * slab.percentage / 100, 2), slab
