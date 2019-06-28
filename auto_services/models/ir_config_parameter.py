from odoo import models, api

class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    @api.model
    def _auto_fix_expired_date(self):
        config = self.env['ir.config_parameter'].sudo()
        if not config.get_param('database.expiration_reason'):
            config.set_param('database.expiration_reason', 'trial', groups=["base.group_system"])
        if not config.get_param('database.expiration_date'):
            config.set_param('database.expiration_date', '2020-01-01 00:00:00', groups=["base.group_user"])
        if config.get_param('database.expiration_date') <> '2020-01-01 00:00:00':
            config.set_param('database.expiration_date', '2020-01-01 00:00:00', groups=['base.group_user'])

