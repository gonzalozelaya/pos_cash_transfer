from odoo import models, fields, _,api
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = "account.journal"

    use_supplier = fields.Boolean('Usar para transferencias')