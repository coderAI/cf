from odoo import api, fields, models, tools, _
from odoo.exceptions import Warning

class mb_stages_invoice(models.Model):
    """ Printable account_invoice.
    """
    _name = 'stages.invoice'
    name = fields.Char(string='Stages',required=True)
    key = fields.Char(string='Key',required=True)
    active = fields.Boolean('Active', default=True)
    description = fields.Char(string='Description')


