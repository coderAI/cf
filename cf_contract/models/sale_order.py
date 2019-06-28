# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import Warning
from odoo.tools.float_utils import float_compare
from odoo.osv.orm import setup_modifiers
from odoo.tools.safe_eval import safe_eval
from lxml import etree
import urllib2
import urllib
import json
from datetime import datetime
import calendar


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    appendix_ids = fields.One2many('cf.contract.appendix', 'order_id', "Appendix")
    contract_id = fields.Many2one('cf.contract', related='partner_id.contract_id', readonly=True, string="Contract")

    @api.multi
    def action_open_contract(self):
        list_view_id = self.env['ir.model.data'].xmlid_to_res_id('cf_contract.view_cf_contract_tree')
        form_view_id = self.env['ir.model.data'].xmlid_to_res_id('cf_contract.view_cf_contract_form')
        return {
            "type": "ir.actions.act_window",
            "res_model": "cf.contract",
            "views": [[list_view_id, "tree"], [form_view_id, "form"]],
            "domain": [('id', '=', self.contract_id and self.contract_id.id or False)],
            "context": {"create": False, "delete": False},
            "name": "Contract",
            'view_mode': 'tree,form',
            'view_type': 'form',
        }

    @api.multi
    def create_contract(self):
        ProductCategory = self.env['product.category']
        contract_id = self.env['cf.contract'].search([('partner_id', '=', self.partner_id.id)])
        if not contract_id:
            contract_id = self.env['cf.contract'].create({
                'partner_id': self.partner_id.id
            })
        self.partner_id.sudo().contract_id = contract_id.id
        data = []
        for line in self.order_line:
            parent_categ = ProductCategory.get_parent_product_category(line.product_category_id)
            if parent_categ.id not in data:
                data.append(parent_categ.id)
        for categ in data:
            domain = [('contract_id', '=', contract_id.id),
                      ('product_category_id', '=', categ),
                      ('order_id', '=', self.id)]
            appendix = self.env['cf.contract.appendix'].search_count(domain)
            if not appendix:
                self.env['cf.contract.appendix'].create({
                    'partner_id': self.partner_id.id,
                    'order_id': self.id,
                    'contract_id': contract_id.id,
                    'product_category_id': categ,
                })


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # @api.multi
    # def get_upgrade_service(self):
    #     if self.product_category_id != self.product_id.categ_id:
    #         return self.product_id.categ_id, self.product_category_id
    #     invoice_line_ids = self.order_id.invoice_ids.filtered(lambda inv: inv.state != 'cancel').mapped(
    #         'invoice_line_ids').filtered(lambda line: line.product_id == self.product_id)
    #     old_category_id = invoice_line_ids.filtered(lambda line: line.price_subtotal < 0)
    #     old_category_id = old_category_id and old_category_id.product_category_id or False
    #     if old_category_id:
    #         return old_category_id, self.product_category_id
    #     else:
    #         return self.product_category_id, self.product_category_id