/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CashMovePopup } from "@point_of_sale/app/navbar/cash_move_popup/cash_move_popup";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(CashMovePopup.prototype, {
    setup() {
        // Llama al método original de setup
        super.setup();

        // Obtiene el contexto del POS
        this.pos = usePos();

        // Inicializa `branchJournals` si no está definido
        if (!this.pos.branchJournals) {
            this.pos.branchJournals = [];
        }

        // Configura el estado inicial
        this.state.branchJournalId = this.pos.branchJournals.length
            ? this.pos.branchJournals[0].id
            : null;

        // Carga los diarios si aún no están disponibles
        if (!this.pos.branchJournals.length) {
            this.loadBranchJournals();
        }
    },

    async loadBranchJournals() {
        try {
            const branchJournals = await this.orm.searchRead(
                "account.journal",
                [["type", "=", "cash"]],
                ["id", "name"]
            );
            this.pos.branchJournals = branchJournals;

            // Configura el diario predeterminado después de cargar los diarios
            if (branchJournals.length) {
                this.state.branchJournalId = branchJournals[0].id;
            }
        } catch (error) {
            console.error("Error loading branch journals:", error);
            this.notification.add("Failed to load branch journals.", 3000);
        }
    },

    async confirm() {
        const amount = parseFloat(this.state.amount || 0);
        const formattedAmount = this.env.utils.formatCurrency(amount);

        if (!amount || !this.state.branchJournalId) {
            this.notification.add("Please specify an amount and branch journal.", 3000);
            return this.props.close();
        }
        const type = this.state.type || "out";
        //const translatedType = this.env._t(type);
        const extras = {
            formattedAmount,
            type,
            branch_journal_id: this.state.branchJournalId,
        };
        const reason = this.state.reason ? this.state.reason.trim() : "";

        try {
            await this.orm.call("pos.session", "try_cash_in_out", [
                [this.pos.pos_session.id],
                type,
                amount,
                reason,
                extras,
            ]);
            await this.pos.logEmployeeMessage(
                `("Transfer Amount"): ${formattedAmount}`,
                "CASH_DRAWER_ACTION"
            );

            this.props.close();
            this.notification.add(
                `Successfully transferred ${type} of ${formattedAmount}.`,
                3000
            );
        } catch (error) {
            console.error("Error during cash transfer:", error);
            this.notification.add("Failed to process cash transfer.", 3000);
        }
    },
});