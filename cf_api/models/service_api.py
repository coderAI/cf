# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF, DEFAULT_SERVER_DATE_FORMAT as DF
import re
import logging as _logger
import json
from odoo.addons.cf_sale.models.sale_order_line import REGISTER_TYPE
from odoo.addons.cf_sale.models.sale_order import STATES


class ServiceAPI(models.AbstractModel):
    _description = 'External Service API'
    _name = 'service.api'

    @api.model
    def get_service(self, customer='', category=[], state=[]):
        try:
            domain = []
            if not customer and not state and not category:
                return {'"code"': 0, '"msg"': '"Pls enter category or customer code or state."'}
            if category:
                category_id = self.env['product.category'].search([('code', 'in', list(category))])
                if not category_id:
                    return {'"code"': 0, '"msg"': '"Category not found"'}
                child_ids = self.env['product.category'].search([('id', 'child_of', category_id.ids)])
                domain.append(('product_category_id', 'in', child_ids.ids))
            if customer:
                customer_id = self.env['res.partner'].search([('ref', '=', customer)])
                if not customer_id:
                    return {'"code"': 0, '"msg"': '"Customer not exists."'}
                if len(customer_id) > 1:
                    return {'"code"': 0, '"msg"': '"Have %s customer with code %s"' % (len(customer_id), customer)}
                domain.append(('customer_id', '=', customer_id.id))
            if state:
                if any(s not in ('draft', 'waiting', 'active', 'refused', 'stop') for s in state):
                    return {'"code"': 0,
                            '"msg"': '"Status must be `draft`(Draft), `waiting`(Waiting), `active`(Active), "'
                                     '"`refused`(Refused) or `stop`(Stop)"'}
                domain.append(('status', 'in', list(state)))
            service_ids = self.env['sale.service'].search(domain)
            data = []
            for service in service_ids:
                item = {}
                item.update({
                    '"id"': service.id,
                    '"reference"': '\"' + (service.reference or '') + '\"',
                    '"name"': '\"' + service.name + '\"',
                    '"customer_id"': service.customer_id and service.customer_id.id or '""',
                    '"customer_code"': '\"' + (service.customer_id and service.customer_id.ref or '') + '\"',
                    '"start_date"': '\"' + (service.start_date or '') + '\"',
                    '"end_date"': '\"' + (service.end_date or '') + '\"',
                    '"product_code"': '\"' + (service.product_id and service.product_id.default_code or '') + '\"',
                    '"product_name"': '\"' + (service.product_id and service.product_id.name or '') + '\"',
                    '"product_category_id"': service.product_category_id and service.product_category_id.id or '""',
                    '"product_category_code"': '\"' + (service.product_category_id.code or '') + '\"',
                    '"product_category_name"': '\"' + (service.product_category_id.name or '') + '\"',
                    '"parent_product_category_code"': '\"' + (service.product_category_id and
                                                              service.product_category_id.parent_id and
                                                              service.product_category_id.parent_id.code or '') + '\"',
                    '"ip"': '\"' + (service.ip or '') + '\"',
                    '"sub_ip"': '\"' + (service.sub_ip or '') + '\"',
                    '"status"': '\"' + (service.status or '') + '\"',
                    '"parent_product_id"': '\"' + (service.parent_product_id and
                                                   service.parent_product_id.default_code or '') + '\"',
                    '"billing_type"': '\"' + (service.billing_type or '') + '\"',
                    '"can_be_register"': service.product_category_id and service.product_category_id.can_be_register
                                         and '"True"' or '"False"',
                    '"can_be_renew"': service.product_category_id and service.product_category_id.can_be_renew
                                      and '"True"' or '"False"',
                    '"uom"': '\"' + (service.product_category_id and service.product_category_id.uom_id and
                                     service.product_category_id.uom_id.name or
                                     (service.uom_id and service.uom_id.name or '')) + '\"',
                    '"is_addons"': '\"' + (service.product_category_id and service.product_category_id.is_addons
                                           and 'True' or 'False') + '\"',
                    '"setup_price_cycle"': service.setup_price_cycle or 0,
                    '"renew_price_cycle"': service.renew_price_cycle or 0,
                    '"license"': service.license or 0,
                    '"phone_number"': '\"' + (service.phone_number or '') + '\"',
                    '"recording_capacity"': '\"' + (service.recording_capacity or '') + '\"',
                    '"extension_capacity"': '\"' + (service.extension_capacity or '') + '\"',
                    '"routing_number"': '\"' + (service.routing_number or '') + '\"',
                    '"to_cloudfone"': '\"' + (service.to_cloudfone or '') + '\"',
                    '"from_telcp"': '\"' + (service.from_telcp or '') + '\"',
                    '"imsi_sim"': '\"' + (service.imsi_sim or '') + '\"',
                    '"imei_port"': '\"' + (service.imei_port or '') + '\"',
                    '"serial_number"': '\"' + (service.serial_number or '') + '\"',
                    '"mac_address"': '\"' + (service.mac_address or '') + '\"',
                    '"type_crm"': '\"' + (service.type_crm or '') + '\"',
                    '"connect_str"': '\"' + (service.connect_str or '') + '\"',
                    '"type"': '\"' + (service.type or '') + '\"',
                    '"network_info"': '\"' + (service.network_info or '') + '\"',
                    '"end_point"': '\"' + (service.end_point or '') + '\"',
                })
                data.append(item)
            return {'"code"': 1, '"msg"': '"Successfully"', '"data"': data}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}

    @api.model
    def get_service_info(self, reference):
        try:
            service = self.env['sale.service'].search([('reference', '=', reference)])
            if not service:
                return {'"code"': 0, '"msg"': '"Service not found"'}
            data = {
                '"id"': service.id,
                '"reference"': '\"' + (service.reference or '') + '\"',
                '"name"': '\"' + service.name + '\"',
                '"customer_id"': service.customer_id and service.customer_id.id or '""',
                '"customer_code"': '\"' + (service.customer_id and service.customer_id.ref or '') + '\"',
                '"start_date"': '\"' + (service.start_date or '') + '\"',
                '"end_date"': '\"' + (service.end_date or '') + '\"',
                '"product_code"': '\"' + (service.product_id and service.product_id.default_code or '') + '\"',
                '"product_name"': '\"' + (service.product_id and service.product_id.name or '') + '\"',
                '"product_category_id"': service.product_category_id and service.product_category_id.id or '""',
                '"product_category_code"': '\"' + (service.product_category_id.code or '') + '\"',
                '"product_category_name"': '\"' + (service.product_category_id.name or '') + '\"',
                '"parent_product_category_code"': '\"' + (service.product_category_id and
                                                          service.product_category_id.parent_id and
                                                          service.product_category_id.parent_id.code or '') + '\"',
                '"ip"': '\"' + (service.ip or '') + '\"',
                '"sub_ip"': '\"' + (service.sub_ip or '') + '\"',
                '"status"': '\"' + (service.status or '') + '\"',
                '"parent_product_id"': '\"' + (service.parent_product_id and
                                               service.parent_product_id.default_code or '') + '\"',
                '"billing_type"': '\"' + (service.billing_type or '') + '\"',
                '"can_be_register"': service.product_category_id and service.product_category_id.can_be_register
                                     and '"True"' or '"False"',
                '"can_be_renew"': service.product_category_id and service.product_category_id.can_be_renew
                                  and '"True"' or '"False"',
                '"uom"': '\"' + (service.product_category_id and service.product_category_id.uom_id and
                                 service.product_category_id.uom_id.name or
                                 (service.uom_id and service.uom_id.name or '')) + '\"',
                '"is_addons"': '\"' + (service.product_category_id and service.product_category_id.is_addons
                                       and 'True' or 'False') + '\"',
                '"setup_price_cycle"': service.setup_price_cycle or 0,
                '"renew_price_cycle"': service.renew_price_cycle or 0,
                '"license"': service.license or 0,
                '"phone_number"': '\"' + (service.phone_number or '') + '\"',
                '"recording_capacity"': '\"' + (service.recording_capacity or '') + '\"',
                '"extension_capacity"': '\"' + (service.extension_capacity or '') + '\"',
                '"routing_number"': '\"' + (service.routing_number or '') + '\"',
                '"to_cloudfone"': '\"' + (service.to_cloudfone or '') + '\"',
                '"from_telcp"': '\"' + (service.from_telcp or '') + '\"',
                '"imsi_sim"': '\"' + (service.imsi_sim or '') + '\"',
                '"imei_port"': '\"' + (service.imei_port or '') + '\"',
                '"serial_number"': '\"' + (service.serial_number or '') + '\"',
                '"mac_address"': '\"' + (service.mac_address or '') + '\"',
                '"type_crm"': '\"' + (service.type_crm or '') + '\"',
                '"connect_str"': '\"' + (service.connect_str or '') + '\"',
                '"type"': '\"' + (service.type or '') + '\"',
                '"network_info"': '\"' + (service.network_info or '') + '\"',
                '"end_point"': '\"' + (service.end_point or '') + '\"',
            }
            return {'"code"': 1, '"msg"': '"Successfully"', '"data"': data}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}

    @api.model
    def get_product_category(self, category_code=''):
        ProductCategory = self.env['product.category']
        domain = [('child_id', '=', False)]
        if category_code:
            category_id = ProductCategory.search([('code', '=', category_code)])
            if not category_id:
                return {'"code"': 0, '"msg"': '"Category Code not exists."'}
            domain += [('id', 'child_of', category_id.ids)]
        category_ids = ProductCategory.search(domain)
        data = []
        try:
            for categ in category_ids:
                data.append({
                    '"code"': '"%s"' % (categ.code or ''),
                    '"name"': '"%s"' % (categ.name or ''),
                    '"setup_price"': categ.setup_price or 0,
                    '"renew_price"': categ.renew_price or 0,
                    '"default_tax"': int(categ.default_tax or 0),
                    '"can_be_register"': categ.can_be_register and '"True"' or '"False"',
                    '"can_be_renew"': categ.can_be_renew and '"True"' or '"False"',
                    '"is_addons"': categ.is_addons and '"True"' or '"False"',
                    '"capacity_price"': categ.capacity_price and '"True"' or '"False"',
                    '"refund_percent"': categ.refund_percent and 0,
                })
            return {'"code"': 1, '"msg"': '"Successfully"', '"data"': data}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}