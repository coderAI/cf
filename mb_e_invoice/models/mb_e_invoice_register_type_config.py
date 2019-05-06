from odoo import api, fields, models

class mb_e_invoice_register_type_config(models.Model):
    """ Printable account_invoice.
    """
    _name = 'mb.e.invoice.register.type.config'
    name = fields.Char(string='Key')
    value = fields.Char(string='Value',required=True)

    active = fields.Boolean('Active', default=True)
    description = fields.Char(string='Description')
