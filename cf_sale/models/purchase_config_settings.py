# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import Warning


class PurchaseConfigSettings(models.TransientModel):
    _inherit = 'purchase.config.settings'

    partner_id = fields.Many2one('res.partner', string='Default Vendor', domain=[('supplier', '=', True)],
                                 required=True)

    @api.multi
    def set_partner_id_defaults(self):
        ir_values_obj = self.env['ir.values']
        if self.partner_id:
            ir_values_obj.sudo().set_default(
                'purchase.order', "partner_id", self.partner_id.id)
            ir_values_obj.sudo().set_default(
                'purchase.config.settings', 'partner_id', self.partner_id.id)
