from odoo import models, fields, _,api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)
class PosSession(models.Model):
    _inherit = 'pos.session'

    counted_money_final = fields.Monetary(string='Transaction', readonly=True)
    
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
                amount_kept = 0
                if session.cash_register_balance_end_real:
                    amount_kept = session.cash_register_balance_end_real
                    
                _logger.info(f'Total transfer amount{total_transfer_amount}')
                if session.state == 'closed':
                    session.cash_register_total_entry_encoding = session.cash_real_transaction + total_cash_payment - total_transfer_amount - amount_kept
                    _logger.info(f'Total entry encoding: {session.cash_register_total_entry_encoding}')
                else:
                    session.cash_register_total_entry_encoding = (
                        sum(session.statement_line_ids.mapped('amount')) + total_cash_payment - total_transfer_amount - amount_kept
                    )
                    _logger.info(f'Total entry encoding: {session.cash_register_total_entry_encoding}')
                session.cash_register_balance_end = (
                    last_session.cash_register_balance_end_real
                    + session.cash_register_total_entry_encoding
                )
                session.cash_register_difference = session.cash_register_balance_end_real - session.cash_register_balance_end
            else:
                session.cash_register_total_entry_encoding = 0.0
                session.cash_register_balance_end = 0.0
                session.cash_register_difference = 0.0

    
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
            try:
                destination_company = self.env['res.company'].browse(1).sudo()
            except ValueError:
                raise UserError(_("Invalid destination company ID: %s") % destination_company_id)
            transfer_journal = self.env.company.transfer_journal
            if not transfer_journal:
                raise UserError("La compañía no tiene seleccionada una cuenta de transferencias")
            payment_out = self.env['account.payment'].create({
                'journal_id': session.cash_journal_id.id,
                'date': fields.Date.context_today(self),
                'ref': f"{session.name} - Salida a Proveedor: {reason}",
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
                #'journal_id': destination_company.cash_journal.id,
                'journal_id': branch_journal.id,
                'date': fields.Date.context_today(self),
                'ref': f"Transferencia a proveedores entrante de: {self.env.company.name} - {reason}",
                'amount': amount,
                'destination_journal_id': destination_company.transfer_journal.id,
                'payment_type': 'inbound',
                'is_internal_transfer': True,
                'pos_session_id': session.id,
                'company_id': destination_company.id,
            })
            payment_in.action_post()
            
    def post_closing_cash_details(self, data):
        # Verifica si `data` es un diccionario
        _logger.info(f'Data received: {data}')

        if isinstance(data, dict):
            counted_cash = float(str(data.get("counted_cash", "0")).replace(",", "."))
            reserve_cash = float(str(data.get("reserve_cash", "0")).replace(",", "."))
        else:
            # Si `data` no es un diccionario, trata el dato directamente como un número
            counted_cash = float(data)
            reserve_cash = 0.0  # Valor predeterminado si no hay `reserve_cash`
        if reserve_cash:
            self.config_id.pos_keep_amount = reserve_cash
        else:
            self.config_id.pos_keep_amount = 0
        # Llama al método original con `counted_cash`
        self.ensure_one()
        check_closing_session = self._cannot_close_session()
        if check_closing_session:
            return check_closing_session

        if not self.cash_journal_id:
            # The user is blocked anyway, this user error is mostly for developers that try to call this function
            raise UserError(_("There is no cash register in this session."))
    
        # Lógica adicional
        self.counted_money_final = counted_cash - reserve_cash
        
        balance_real = 0
        if counted_cash > self.config_id.pos_keep_amount:
            #balance_real = counted_cash - self.config_id.pos_keep_amount
            balance_real = counted_cash - reserve_cash
        else:
            balance_real = counted_cash
    
        _logger.info(f'Balance real: {balance_real}')
    
        sessions = self.filtered('cash_journal_id')
        if not sessions:
            raise UserError(_("There is no cash payment method for this PoS Session."))
    
        for session in sessions:
            if not session.cash_journal_id.default_account_id:
                raise UserError(_("The cash journal must have a default account configured."))
            try:
                destination_company = self.env['res.company'].browse(1).sudo()
            except ValueError:
                raise UserError(_("Invalid destination company ID: %s") % destination_company_id)
            if not destination_company.exists():
                raise UserError(_("The selected destination company does not exist or was deleted."))
            transfer_journal = self.env.company.transfer_journal
            if not transfer_journal:
                raise UserError("La compañía no tiene seleccionada una cuenta de transferencias")
            _logger.info("Creating transfer in origin company: %s", self.env.company.name)
            payment_date = self.start_at.date() if self.start_at else fields.Date.context_today(self)
            payment_out = self.env['account.payment'].create({
                'journal_id': session.cash_journal_id.id,
                'date': payment_date,
                'ref': f"{session.name} - Transferencia saliente a: {destination_company.name}",
                'amount': balance_real,
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
                'date': payment_date,
                'ref': f"Transferencia entrante de: {self.env.company.name}",
                'amount': balance_real,
                'destination_journal_id': destination_company.transfer_journal.id,
                'payment_type': 'inbound',
                'is_internal_transfer': True,
                'pos_session_id': session.id,
                'company_id': destination_company.id,
            })
            payment_in.action_post()
    
        # Actualiza el balance real del registro
        self.cash_register_balance_end_real = self.config_id.pos_keep_amount
        return {'successful': True}

