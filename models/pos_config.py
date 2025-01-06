from odoo import api, fields, models, _

class pos_config(models.Model):
    _inherit = "pos.config"

    pos_keep_amount = fields.Monetary(
        string='Monto a conservar',
        help='Se conservara este monto al cerrar sesión',
        default= 0
    )