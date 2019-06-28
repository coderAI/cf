# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import Warning
import logging

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_service_count(self):
        for r in self:
            r.service_count = self.env['sale.service'].search_count([('customer_id', '=', r.id)])

    service_count = fields.Integer(compute='_compute_service_count', string='# of Service')

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        args = args or []
        # ctx = self._context
        team_id = self.env['crm.team']._get_default_team_id()
        if team_id and team_id.type == 'sale':
            args += [('new_customer', '=', True)]
        return super(ResPartner, self).search(args, offset, limit, order, count)

    # @api.model
    # def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
    #     ctx = self._context
    #     if ctx.get('current_model') and ctx.get('sale_team_id'):
    #         team_id = self.env['crm.team'].browse(ctx.get('sale_team_id'))
    #         if team_id.type == 'sale':
    #             domain += [['new_customer', '=', True]]
    #     return super(ResPartner, self).read_group(domain, fields, groupby, offset=offset,
    #                                               limit=limit, orderby=orderby, lazy=lazy)
    #
    # @api.model
    # def name_search(self, name, args=None, operator='ilike', limit=100):
    #     args = args or []
    #     team_id = self.env['crm.team']._get_default_team_id()
    #     if team_id and team_id.type == 'sale':
    #         args += [('new_customer', '=', True)]
    #     return super(ResPartner, self).name_search(name, args=args, operator=operator, limit=limit)