/** @odoo-module */

import { registry } from "@web/core/registry";
import { CashMovePopup as OriginalCashMovePopup } from "@point_of_sale/app/navbar/cash_move_popup/cash_move_popup";

export class CashMovePopup extends OriginalCashMovePopup {
    setup() {
        super.setup();

        // Cargar los diarios de sucursales
        this.pos.branchJournals = this.pos.branchJournals || [];
        if (!this.pos.branchJournals.length) {
            this.loadBranchJournals();
        }

        // Añadir el estado para el selector de diario
        this.state.branchJournalId = this.pos.branchJournals.length
            ? this.pos.branchJournals[0].id
            : null;
    }

    async loadBranchJournals() {
        const branchJournals = await this.orm.searchRead(
            "account.journal",
            [["type", "=", "cash"]],
            ["id", "name"]
        );
        this.pos.branchJournals = branchJournals;
        if (branchJournals.length && !this.state.branchJournalId) {
            this.state.branchJournalId = branchJournals[0].id;
        }
    }

    async confirm() {
        const amount = parseFloat(this.state.amount);
        const formattedAmount = this.env.utils.formatCurrency(amount);
        if (!amount || !this.state.branchJournalId) {
            this.notification.add(_t("Please specify an amount and branch journal."), 3000);
            return this.props.close();
        }

        const type = this.state.type;
        const translatedType = _t(type);
        const extras = {
            formattedAmount,
            translatedType,
            branch_journal_id: this.state.branchJournalId,
        };
        const reason = this.state.reason.trim();

        await this.orm.call("pos.session", "try_cash_in_out", [
            [this.pos.pos_session.id],
            type,
            amount,
            reason,
            extras,
        ]);

        await this.pos.logEmployeeMessage(
            `${_t("Transfer")} ${translatedType} - ${_t("Amount")}: ${formattedAmount}`,
            "CASH_DRAWER_ACTION"
        );

        this.props.close();
        this.notification.add(
            _t("Successfully transferred %s of %s.", type, formattedAmount),
            3000
        );
    }
}

// Registra el popup personalizado
registry.category("popups").add("CashMovePopup", CashMovePopup);