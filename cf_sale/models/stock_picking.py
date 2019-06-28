# -*- coding: utf-8 -*-
from odoo import models, fields, api, SUPERUSER_ID, _
from datetime import datetime, timedelta
import logging
from odoo.exceptions import Warning, ValidationError
from odoo.osv.orm import setup_modifiers
from lxml import etree

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(StockPicking, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                     submenu=submenu)
        doc = etree.XML(res['arch'])
        if view_type == 'tree':
            if not self.user_has_groups('sales_team.group_sale_manager') \
                    and not self.user_has_groups('cf_security.group_sale_support') \
                    and not self.user_has_groups('cf_security.group_sale_operator')\
                    and (self.user_has_groups('sales_team.group_sale_salesman') or
                         self.user_has_groups('sales_team.group_sale_salesman_all_leads')):
                tree_view = doc.xpath("//tree")
                tree_view[0].set('create', 'false')
                tree_view[0].set('delete', 'false')
                setup_modifiers(tree_view[0])
        if view_type == 'form':
            if not self.user_has_groups('sales_team.group_sale_manager') \
                    and not self.user_has_groups('cf_security.group_sale_support') \
                    and not self.user_has_groups('cf_security.group_sale_operator') \
                    and (self.user_has_groups('sales_team.group_sale_salesman') or
                         self.user_has_groups('sales_team.group_sale_salesman_all_leads')):
                form_view = doc.xpath("//form")
                form_view[0].set('create', 'false')
                form_view[0].set('edit', 'false')
                form_view[0].set('delete', 'false')
                setup_modifiers(form_view[0])
                buttons_to_invisible = doc.xpath("//button")
                for node in buttons_to_invisible:
                    node.set('invisible', '1')
                    setup_modifiers(node)
        res['arch'] = etree.tostring(doc)
        return res

    @api.multi
    def do_transfer(self):
        if self.user_has_groups('cf_security.group_sale_support'):
            return super(StockPicking, self.sudo()).do_transfer()
        return super(StockPicking, self).do_transfer()