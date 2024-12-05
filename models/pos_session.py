from odoo import models, fields, _, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class PosSession(models.Model):
    _inherit = 'pos.session'
    
    @api.depends('payment_method_ids', 'order_ids', 'cash_register_balance_start')
    def _compute_cash_balance(self):
        for session in self:
            _logger.info('Computing balance')
            cash_payment_method = session.payment_method_ids.filtered('is_cash_count')[:1]
            if cash_payment_method:
                total_cash_payment = 0.0
                last_session = session.search([('config_id', '=', session.config_id.id), ('id', '<', session.id)], limit=1)
    
                # Leer pagos en efectivo de la sesión
                result = self.env['pos.payment']._read_group(
                    [('session_id', '=', session.id), ('payment_method_id', '=', cash_payment_method.id)],
                    aggregates=['amount:sum']
                )
                total_cash_payment = result[0][0] or 0.0
                _logger.info(f"Total cash payment {total_cash_payment}")
                # Leer transferencias internas
                cash_transfers = self.env['account.payment'].search([
                    ('pos_session_id', '=', session.id),
                    ('is_internal_transfer', '=', True),
                    ('payment_type', '=', 'outbound'),
                ])
                _logger.info(f'Cash transfers{cash_transfers}')
                total_transfer_amount = sum(cash_transfers.mapped('amount'))
                _logger.info(f'Total transfer amount{total_transfer_amount}')
                if session.state == 'closed':
                    session.cash_register_total_entry_encoding = session.cash_real_transaction + total_cash_payment - total_transfer_amount
                    _logger.info(f'Total: {session.cash_register_total_entry_encoding}')
                else:
                    session.cash_register_total_entry_encoding = (
                        sum(session.statement_line_ids.mapped('amount')) + total_cash_payment - total_transfer_amount
                    )
    
                session.cash_register_balance_end = (
                    last_session.cash_register_balance_end_real
                    + session.cash_register_total_entry_encoding
                )
                session.cash_register_difference = session.cash_register_balance_end_real - session.cash_register_balance_end
            else:
                session.cash_register_total_entry_encoding = 0.0
                session.cash_register_balance_end = 0.0
                session.cash_register_difference = 0.0