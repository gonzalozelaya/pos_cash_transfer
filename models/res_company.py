from odoo import models, fields, _,api
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = "res.company"

    cash_journal = fields.Many2one(
        'account.journal',
        string='Diario efectivo',
        domain=[('type', '=', 'cash')],
        help='Diario que se usara para enviar/recibir transferencias entre compañias.'
    )

    transfer_journal = fields.Many2one(
        'account.journal',
        string='Diario transferencias',
        domain=[('type', 'in', ['bank', 'cash'])],
        help='Diario para anotar las transferencias'
    )

    @api.model
    def get_all_companies(self):
        """Devuelve todas las compañías sin restricciones de acceso."""
        return self.sudo().search_read([], ['id', 'name'])

    @api.model
    def get_transfer_account(self):
        """Devuelve el diario de transferencia configurado para la compañía actual."""
        company_id = self.env.company.id  # Compañía actual
        if company.transfer_journal:
            return [{
                "id": company.transfer_journal.id,
                "name": company.transfer_journal.name,
            }]
        return []

    @api.model
    def get_all_journals(self):
        """Devuelve todos los diarios que sean de tipo efectivo."""
        cash_journals = self.env['account.journal'].search([('type', '=', 'cash'),
                                                            ('company_id', '=', self.env.company.id),
                                                            ('use_supplier','=',True)])
                                                            
        return cash_journals.read(['id', 'name'])

