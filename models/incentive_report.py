import calendar
from datetime import datetime

from odoo import _, api, models
from odoo.exceptions import AccessError


class HrEmployeeIncentiveReport(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _month_bounds(self, year=None, month=None):
        today = datetime.now()
        year = int(year) if year else today.year
        month = int(month) if month else today.month
        last_day = calendar.monthrange(year, month)[1]
        start = f"{year:04d}-{month:02d}-01 00:00:00"
        end = f"{year:04d}-{month:02d}-{last_day:02d} 23:59:59"
        return year, month, start, end

    @api.model
    def _current_employee(self):
        return self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.uid)], limit=1)

    @api.model
    def _is_incentive_manager(self):
        return self.env.user.has_group('admission_incentive_19.group_incentive_manager')

    @api.model
    def get_incentive_report(self, year=None, month=None):
        year, month, start, end = self._month_bounds(year, month)
        Slab = self.env['incentive.slab'].sudo()
        Enrollment = self.env['student.enrollment'].sudo()
        Payment = self.env['student.fee.payment'].sudo()

        is_manager = self._is_incentive_manager()
        if is_manager:
            officer_ids = set(
                self.env['lead.team.member'].sudo().search([]).mapped('employee_id').ids
            )
            assigned_enrollments = Enrollment.search([('assigned_officer_id', '!=', False)])
            officer_ids |= set(assigned_enrollments.mapped('assigned_officer_id').ids)
        else:
            # Self-service: an officer only ever sees their own row, no
            # matter what — never trust a client-supplied officer filter.
            me = self._current_employee()
            officer_ids = {me.id} if me else set()
            assigned_enrollments = Enrollment.search(
                [('assigned_officer_id', 'in', list(officer_ids))]) if officer_ids \
                else Enrollment.browse()

        officers_data = []
        total_collected = 0.0
        total_balance = 0.0
        total_commission = 0.0

        for officer in self.browse(list(officer_ids)):
            enrollments = assigned_enrollments.filtered(
                lambda e: e.assigned_officer_id.id == officer.id)
            balance_now = sum(enrollments.mapped('due_amount'))

            # Only FULLY paid admissions are incentive-eligible — a partial
            # payment (e.g. admission fee only, or any amount short of the
            # total) contributes nothing until the whole total_fee is
            # settled. Once settled, the FULL total_fee counts (not just
            # what was paid this month), attributed to whichever month the
            # final/completing payment landed in.
            collected = 0.0
            pending_total_fee = 0.0
            for e in enrollments:
                if e.due_amount <= 0:
                    last_payment = Payment.search(
                        [('enrollment_id', '=', e.id)],
                        order='payment_date desc', limit=1)
                    completed_on = last_payment.payment_date if last_payment else False
                    if completed_on and start[:10] <= completed_on.isoformat() <= end[:10]:
                        collected += e.total_fee
                else:
                    pending_total_fee += e.total_fee

            commission, slab = Slab.calculate_incentive(collected)
            potential_total = collected + pending_total_fee
            potential_commission, potential_slab = Slab.calculate_incentive(potential_total)

            total_collected += collected
            total_balance += balance_now
            total_commission += commission

            officers_data.append({
                'officer_id': officer.id,
                'officer_name': officer.name,
                'assigned_count': len(enrollments),
                'cleared_count': len(enrollments.filtered(lambda e: e.due_amount <= 0)),
                'collected': collected,
                'balance_pending': balance_now,
                'slab_name': slab.name if slab else False,
                'slab_percentage': slab.percentage if slab else 0.0,
                'commission_earned': commission,
                'potential_total': potential_total,
                'potential_slab_name': potential_slab.name if potential_slab else False,
                'potential_slab_percentage': potential_slab.percentage if potential_slab else 0.0,
                'potential_commission': potential_commission,
            })

        officers_data.sort(key=lambda o: -o['collected'])

        return {
            'year': year, 'month': month,
            'is_manager': is_manager,
            'summary': {
                'total_collected': total_collected,
                'total_balance_pending': total_balance,
                'total_commission_earned': total_commission,
                'officer_count': len(officers_data),
            },
            'officers': officers_data,
            'slabs': Slab.search_read(
                [('active', '=', True)],
                ['name', 'from_amount', 'to_amount', 'percentage'], order='from_amount'),
        }

    @api.model
    def get_officer_assigned_students(self, officer_id, year=None, month=None):
        """Drill-down: every assigned student for this officer, with what
        they owe, what's been collected from them this month, and their
        overall balance — answers 'how much did they collect and what's
        still pending' per student."""
        if not self._is_incentive_manager():
            me = self._current_employee()
            if not me or me.id != int(officer_id):
                raise AccessError(_("You can only view your own assigned students."))
        year, month, start, end = self._month_bounds(year, month)
        Enrollment = self.env['student.enrollment'].sudo()
        Payment = self.env['student.fee.payment'].sudo()

        enrollments = Enrollment.search([('assigned_officer_id', '=', int(officer_id))])
        rows = []
        for e in enrollments:
            payments_this_month = Payment.search([
                ('enrollment_id', '=', e.id),
                ('payment_date', '>=', start[:10]),
                ('payment_date', '<=', end[:10]),
            ])
            last_payment = Payment.search(
                [('enrollment_id', '=', e.id)], order='payment_date desc', limit=1)
            completed_on = last_payment.payment_date if last_payment else False
            counted = bool(
                e.due_amount <= 0 and completed_on
                and start[:10] <= completed_on.isoformat() <= end[:10]
            )
            rows.append({
                'enrollment_id': e.id,
                'student_name': e.student_id.name,
                'batch_name': e.batch_id.name,
                'total_fee': e.total_fee,
                'paid_amount': e.paid_amount,
                'due_amount': e.due_amount,
                'collected_this_month': sum(payments_this_month.mapped('amount')),
                'counted_for_incentive': counted,
                'last_payment_date': last_payment.payment_date.isoformat()
                    if last_payment and last_payment.payment_date else False,
            })
        rows.sort(key=lambda r: -r['due_amount'])
        return rows
