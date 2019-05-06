from odoo import api, fields, models

class mb_e_invoice_api_config(models.Model):
    """ Printable account_invoice.
    """
    _name = 'mb.e.invoice.api.config'
    name = fields.Char(string='Key',required=True)
    url = fields.Char(string='Url',required=True)

    active = fields.Boolean('Active', default=True)
    description = fields.Char(string='Description')


