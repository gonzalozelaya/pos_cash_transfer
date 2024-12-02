from odoo import models, fields, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)
class PosSession(models.Model):
    _inherit = 'pos.session'

    def try_cash_in_out(self, _type, amount, reason, extras):
        _logger.info("Starting try_cash_in_out method")
        _logger.info("Parameters received: _type=%s, amount=%s, reason=%s, extras=%s", _type, amount, reason, extras)
        sign = 1 if _type == 'in' else -1
        sessions = self.filtered('cash_journal_id')
        if not sessions:
            raise UserError(_("There is no cash payment method for this PoS Session."))

        if not extras.get('branch_journal_id'):
            raise UserError(_("A branch journal must be specified for the cash transfer."))

        branch_journal_id = extras['branch_journal_id']
        try:
            branch_journal_id = int(extras['branch_journal_id'])
        except ValueError:
            raise UserError(_("Invalid branch journal ID: %s") % extras['branch_journal_id'])
        branch_journal = self.env['account.journal'].browse(branch_journal_id)
        _logger.info(f"Branch journal: {branch_journal}")
        if not branch_journal.default_account_id:
            raise UserError(_("The selected branch journal must have a default account configured."))

        account_move_vals = []
        for session in sessions:
            if not session.cash_journal_id.default_account_id:
                raise UserError(_("The cash journal must have a default account configured."))

            # Crear asientos contables para la transferencia
            _logger.info('Creando asiento')
            account_move_vals.append({
                'journal_id': branch_journal_id,
                'date': fields.Date.context_today(self),
                'ref': f"{session.name} - {extras['type']} - {reason}",
                'line_ids': [
                    # Línea para la salida de efectivo del diario de la sesión
                    (0, 0, {
                        'account_id': session.cash_journal_id.default_account_id.id,
                        'debit': 0.0 if sign == 1 else amount,
                        'credit': amount if sign == 1 else 0.0,
                        'name': reason,
                    }),
                    # Línea para la entrada de efectivo al diario de la sucursal
                    (0, 0, {
                        'account_id': branch_journal.default_account_id.id,
                        'debit': amount if sign == 1 else 0.0,
                        'credit': 0.0 if sign == 1 else amount,
                        'name': reason,
                    }),
                ],
            })

        # Crear los movimientos contables
        moves = self.env['account.move'].create(account_move_vals)
        moves._post()  # Publicar los movimientos contables