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
        this.state.destinationCompanyId = null; // Nuevo estado para la compañía de destino
        this.state.destinationCompanies = [];
        this.state.method = 'payments'
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
        this.loadDestinationCompanies();
    },
    
    async loadDestinationCompanies() {
        try {
            // Llamar al método personalizado del backend
            const companies = await this.orm.call("res.company", "get_all_companies", []);
            this.state.destinationCompanies = companies.length ? companies : [];
        } catch (error) {
            console.error("Error loading companies:", error);
            this.state.destinationCompanies = []; // Mantener un arreglo vacío en caso de error
        }
    },
    async loadBranchJournals() {
        try {
            const branchJournals = await this.orm.call(
                "res.company",
                "get_all_journals",
                [] // No se requieren argumentos
            );
    
            if (branchJournals && branchJournals.length) {
                this.pos.branchJournals = branchJournals;
                this.state.branchJournalId = branchJournals[0].id; // Configura el primero como predeterminado
            } else {
                this.pos.branchJournals = [];
                this.state.branchJournalId = null;
                this.notification.add("No transfer journals found.", 3000);
            }
        } catch (error) {
            console.error("Error loading branch journals:", error);
            this.notification.add("Failed to load branch journals.", 3000);
        }
    },
    async confirm() {
        const amount = parseFloat(this.state.amount || 0);
        if (!amount) {
            this.notification.add("Please specify an amount.", 3000);
            return this.props.close();
        }

        const extras = {
            branch_journal_id: this.state.branchJournalId,
            destination_company_id: this.state.destinationCompanyId,
            reason: this.state.reason.trim(),
            payment_type:this.state.method,
        };

        try {
            await this.orm.call("pos.session", "try_cash_in_out", [
                [this.pos.pos_session.id],
                "out",
                amount,
                this.state.reason,
                extras,
            ]);
            this.notification.add("Transferencia completada con éxito.", 3000);
        } catch (error) {
            console.error("Ocurrió un error durante la transferencia:", error);
            this.notification.add("Falla al completar la transferencia.", 3000);
        }
        this.props.close();
    },
});