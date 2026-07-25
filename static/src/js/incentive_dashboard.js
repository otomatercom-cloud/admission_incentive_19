/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

const MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];

export class IncentiveDashboard extends Component {
    static template = "admission_incentive_19.IncentiveDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        const now = new Date();
        this.state = useState({
            loading: true,
            year: now.getFullYear(),
            month: now.getMonth() + 1,
            data: null,
            error: "",
            expandedOfficerId: false,
            officerStudents: [],
            officerStudentsLoading: false,
            generatingPayouts: false,
        });
        onWillStart(() => this.loadData());
    }

    get monthLabel() {
        return `${MONTH_NAMES[this.state.month]} ${this.state.year}`;
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = "";
        try {
            this.state.data = await this.orm.call(
                "hr.employee", "get_incentive_report",
                [this.state.year, this.state.month]
            );
            const officers = this.officers;
            if (officers.length === 1) {
                await this.toggleOfficer(officers[0]);
            }
        } catch (e) {
            console.error("Incentive report load failed", e);
            this.state.error = "Failed to load incentive report. Please refresh.";
        } finally {
            this.state.loading = false;
        }
    }

    prevMonth() {
        this.state.month -= 1;
        if (this.state.month < 1) { this.state.month = 12; this.state.year -= 1; }
        this.state.expandedOfficerId = false;
        this.loadData();
    }

    nextMonth() {
        this.state.month += 1;
        if (this.state.month > 12) { this.state.month = 1; this.state.year += 1; }
        this.state.expandedOfficerId = false;
        this.loadData();
    }

    get summary() {
        return (this.state.data && this.state.data.summary) || {};
    }

    get isManager() {
        return !!(this.state.data && this.state.data.is_manager);
    }

    get officers() {
        return (this.state.data && this.state.data.officers) || [];
    }

    get slabs() {
        return (this.state.data && this.state.data.slabs) || [];
    }

    fmt(n) {
        return (n || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    async toggleOfficer(officer) {
        if (this.state.expandedOfficerId === officer.officer_id) {
            this.state.expandedOfficerId = false;
            return;
        }
        this.state.expandedOfficerId = officer.officer_id;
        this.state.officerStudentsLoading = true;
        try {
            this.state.officerStudents = await this.orm.call(
                "hr.employee", "get_officer_assigned_students",
                [officer.officer_id, this.state.year, this.state.month]
            );
        } finally {
            this.state.officerStudentsLoading = false;
        }
    }

    openBalances() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Balances to Collect",
            res_model: "student.enrollment",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["due_amount", ">", 0]],
            target: "current",
        });
    }

    async generatePayouts() {
        this.state.generatingPayouts = true;
        try {
            const result = await this.orm.call(
                "hr.employee", "generate_payouts_for_month",
                [this.state.year, this.state.month]
            );
            this.notification.add(
                result.created
                    ? `${result.created} payout(s) created.`
                    : "No new payouts to create — all up to date.",
                { type: "success" }
            );
            await this.loadData();
        } finally {
            this.state.generatingPayouts = false;
        }
    }

    openPayout(officer, ev) {
        if (ev) { ev.stopPropagation(); }
        if (officer.payout_id) {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Incentive Payout",
                res_model: "incentive.payout",
                res_id: officer.payout_id,
                view_mode: "form",
                views: [[false, "form"]],
                target: "current",
            });
        }
    }
}

registry
    .category("actions")
    .add("admission_incentive_19.incentive_dashboard", IncentiveDashboard);
