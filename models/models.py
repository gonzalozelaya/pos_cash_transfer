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

        for session in sessions:
            if not session.cash_journal_id.default_account_id:
                raise UserError(_("The cash journal must have a default account configured."))
            if extras.get('payment_type') == 'transfers':
                # Validar la compañía de destino
                destination_company_id = extras.get('destination_company_id')
                try:
                    destination_company_id = int(destination_company_id)
                except ValueError:
                    raise UserError(_("Invalid destination company ID: %s") % destination_company_id)
        
                destination_company = self.env['res.company'].browse(destination_company_id).sudo()
                if not destination_company.exists():
                    raise UserError(_("The selected destination company does not exist or was deleted."))
                transfer_journal = self.env.company.transfer_journal
                if not transfer_journal:
                    raise UserError("La compania no tiene seleccionada una cuenta de transferencias")
                _logger.info("Creating transfer in origin company: %s", self.env.company.name)
                payment_out = self.env['account.payment'].create({
                    'journal_id': session.cash_journal_id.id,
                    'date': fields.Date.context_today(self),
                    'ref': f"{session.name} - Transferencia saliente a: {destination_company.name} - {reason}",
                    'amount': amount,
                    'destination_journal_id': transfer_journal.id,
                    'payment_type': 'outbound',
                    'pos_session_id': session.id, 
                    'is_internal_transfer': True,
                })
                payment_out.action_post()
    
                # Crear la transferencia en la compañía de destino usando with_company
                _logger.info("Creating transfer in destination company: %s", destination_company.name)
                payment_in = self.env['account.payment'].sudo().with_company(destination_company).create({
                    'journal_id': destination_company.cash_journal.id,
                    'date': fields.Date.context_today(self),
                    'ref': f"Transferencia entrante de: {self.env.company.name} - {reason}",
                    'amount': amount,
                    'destination_journal_id': destination_company.transfer_journal.id,
                    'payment_type': 'inbound',
                    'is_internal_transfer': True,
                    'pos_session_id': session.id, 
                    'company_id':destination_company.id,
                })
                payment_in.action_post()
            else:
                if not extras.get('branch_journal_id'):
                    raise UserError(_("A branch journal must be specified for the cash transfer."))
                branch_journal_id = extras['branch_journal_id']
                try:
                    branch_journal_id = int(extras['branch_journal_id'])
                except ValueError:
                    raise UserError(_("Invalid branch journal ID: %s") % extras['branch_journal_id'])
                branch_journal = self.env['account.journal'].browse(branch_journal_id)
                if not branch_journal.default_account_id:
                    raise UserError(_("The selected branch journal must have a default account configured."))
                payment_out = self.env['account.payment'].create({
                    'journal_id': session.cash_journal_id.id,
                    'date': fields.Date.context_today(self),
                    'ref': f"{session.name} - Salida de efectivo a: {branch_journal.name} - {reason}",
                    'amount': amount,
                    'destination_journal_id': branch_journal.id,
                    'payment_type': 'outbound',
                    'pos_session_id': session.id, 
                    'is_internal_transfer': True,
                })
                payment_out.action_post()