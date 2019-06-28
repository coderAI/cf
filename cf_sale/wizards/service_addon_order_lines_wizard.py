# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import Warning
import urllib2
import urllib
import json


class ServiceAddonOrderLinesWizard(models.TransientModel):
    _name = "service.addon.order.lines.wizard"
    _description = "Wizard to add services/addons to the current active SO"

    line_ids = fields.One2many('order.lines.wizard', 'parent_id', string='Order Lines')

    @api.multi
    def get_line_values(self, line):
        vals = {
            'register_type': line.register_type,
            'product_category_id': line.product_category_id.id,
            'time': line.time,
            'product_uom': line.product_category_id.uom_id.id,
            'notes': line.notes,
        }
        return vals

    @api.multi
    def write_service_orders(self):
        self.ensure_one()
        if self._context.get('active_model') != 'sale.order':
            return False
        order_id = self.env.context.get('active_id')
        order = self.env['sale.order'].browse(order_id)
        lines = []
        for line in self.line_ids:
            product_uom = line.product_category_id.uom_id.id
            if not product_uom:
                raise Warning(_("Please set UOM for Product Category!"))

            vals = self.get_line_values(line)

            # product_id = None
            # product_name = None
            is_add_service = self._context.get('service')
            if line.register_type in ['register']:
                product_data = {
                    'name': line.product_name.strip(),
                    'type': 'service',
                    'categ_id': line.product_category_id.id,
                    'minimum_register_time': line.product_category_id.minimum_register_time,
                    'billing_cycle': line.product_category_id.billing_cycle,
                    'uom_id': line.product_category_id.uom_id.id,
                    'uom_po_id': line.product_category_id.uom_id.id,
                }
                new_prod = self.env['product.product'].create(product_data)
                product_id = new_prod.id
                product_name = is_add_service and line.product_name.strip() or \
                    line.parent_product_id.name.strip()
            else:
                product_id = line.product_id.id
                product_name = line.product_id.name.strip()

            vals.update({
                'product_id': product_id,
                'name': product_name.strip(),
                'parent_product_id': is_add_service and False or line.parent_product_id.id
            })

            lines.append((0, 0, vals))
        if lines:
            order.write({'order_line': lines})
