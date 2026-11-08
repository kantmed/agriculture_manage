/** @odoo-module **/
import { registry } from "@web/core/registry";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, proxy } from "@odoo/owl";

class MesComptesDashboard extends Component {
    static template = "mes_comptes.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = proxy({
            loading: true,
            data: null,
            error: null,
            activeTab: "vue_generale",   // onglets : vue_generale | activite | evolution
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    // ── Données ────────────────────────────────────────────────────────────────

    async loadData(referenceDate) {
        this.state.loading = true;
        this.state.error = null;
        try {
            this.state.data = await this.orm.call(
                "mes.comptes.dashboard", "get_dashboard_data", [referenceDate]
            );
        } catch (error) {
            this.state.error = _t("Impossible de charger les données du tableau de bord.");
        } finally {
            this.state.loading = false;
        }
    }

    async changeMonth(offset) {
        if (!this.state.data) return;
        const reference = this.state.data.reference_date || new Date().toISOString().slice(0, 10);
        const [year, month] = reference.split("-").map(Number);
        const current = new Date(year, month - 1 + offset, 1);
        const iso = `${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, "0")}-01`;
        await this.loadData(iso);
    }

    async goToday() {
        await this.loadData(null);
    }

    // ── Onglets ────────────────────────────────────────────────────────────────

    setTab(tab) {
        this.state.activeTab = tab;
    }

    isTab(tab) {
        return this.state.activeTab === tab;
    }

    // ── Formatage ──────────────────────────────────────────────────────────────

    format(value, currencyId) {
        return formatCurrency(value || 0, currencyId);
    }

    chartHeight(value, chart) {
        const values = chart.monthly_trend.flatMap((m) => [m.income, m.expense]);
        const max = Math.max(...values, 1);
        return `${Math.max(value ? (Math.abs(value) / max) * 100 : 0, value ? 4 : 0)}%`;
    }

    comparisonWidth(value, item) {
        const values = [item.income, item.expense, item.previous.income, item.previous.expense];
        return `${Math.max(value ? (Math.abs(value) / Math.max(...values, 1)) * 100 : 0, value ? 2 : 0)}%`;
    }

    transactionTypeLabel(type) {
        return type === "income" ? _t("Recette") : _t("Dépense");
    }

    financialTypeLabel(type) {
        return type === "income" ? _t("Recettes") : _t("Dépenses");
    }

    // ── Navigation ─────────────────────────────────────────────────────────────

    openTransactions() {
        this.action.doAction("mes_comptes.action_mes_transactions");
    }

    get currentMonthLabel() {
        if (!this.state.data || !this.state.data.reference_date) return "";
        const d = this.state.data.reference_date;
        return d.slice(5, 7) + "/" + d.slice(0, 4);
    }
}

registry.category("actions").add("mes_comptes.dashboard", MesComptesDashboard);
