from odoo import api, fields, models, _
from odoo.exceptions import Warning

class AgencyPrice(models.Model):
    _name = 'product.agency.price'
    _inherit = ['mail.thread']
    _description = "Agency Price"
    _order = 'categ_id, level_id'

    categ_id = fields.Many2one('product.category', 'Category')
    code = fields.Char(related='categ_id.code')
    level_id = fields.Integer(string='Agency Level')
    setup_price = fields.Float('Setup Price')
    renew_price = fields.Float('Renew Price')
