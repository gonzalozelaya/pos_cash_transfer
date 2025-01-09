/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";

patch(ClosePosPopup.prototype, {
    setup() {
        super.setup(); // Usar super si es compatible
        this.state.reserve_cash = 0;
    },

    async closeSession() {
        // Llamamos al método original de closeSession
        const syncSuccess = await this.pos.push_orders_with_closing_popup();
        if (!syncSuccess) {
            return;
        }

        if (this.pos.config.cash_control) {
            await this.orm.call("pos.session", "post_closing_cash_details", [
                this.pos.pos_session.id,
                {
                    counted_cash:parseFloat(String(
                        this.state.payments[this.props.default_cash_details.id]?.counted || 0
                    ).replace(/\./g, "").replace(",", ".")),
                    reserve_cash: parseFloat(this.state.reserve_cash || 0),
                },
            ]);
        }

        try {
            await this.orm.call("pos.session", "update_closing_control_state_session", [
                this.pos.pos_session.id,
                this.state.notes,
            ]);
        } catch (error) {
            if (!error.data && error.data.message !== "This session is already closed.") {
                throw error;
            }
        }

        try {
            const bankPaymentMethodDiffPairs = this.props.other_payment_methods
                .filter((pm) => pm.type == "bank")
                .map((pm) => [pm.id, this.getDifference(pm.id)]);
            const response = await this.orm.call("pos.session", "close_session_from_ui", [
                this.pos.pos_session.id,
                bankPaymentMethodDiffPairs,
            ]);
            if (!response.successful) {
                return this.handleClosingError(response);
            }
            this.pos.redirectToBackend();
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                throw error;
            } else {
                await this.popup.add(ErrorPopup, {
                    title: _t("Closing session error"),
                    body: _t(
                        "An error has occurred when trying to close the session.\n" +
                            "You will be redirected to the back-end to manually close the session."
                    ),
                });
                this.pos.redirectToBackend();
            }
        }
    },
});