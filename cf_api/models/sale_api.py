# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF, DEFAULT_SERVER_DATE_FORMAT as DF
import re
import logging as _logger
import json
from odoo.addons.cf_sale.models.sale_order_line import REGISTER_TYPE
from odoo.addons.cf_sale.models.sale_order import STATES


class SaleAPI(models.AbstractModel):
    _description = 'External SO API'
    _name = 'sale.api'

    @api.multi
    def _validate_email(self, email_list):
        """
            TO DO:
            - Validate the format of emails
        """
        if any(re.match("^[a-zA-Z0-9._%-]+@[a-zA-Z0-9._%-]+.[a-zA-Z]{2,6}$", email) == None for email in email_list):
            return False
        return True

    def _convert_str(self, value):
        if type(value) is str:
            return (unicode(value, "utf-8")).strip()
        else:
            return value

    @api.model
    def create_customer(self, vals):
        """
            TO DO:
            - Check and create customer
        """
        # Check type of data
        if type(vals) is not dict:
            return {'code': 0, 'msg': "Invalid CustomerEntity"}

        ResCountyState = self.env['res.country.state']
        ResUsers = self.env['res.users']
        ResPartner = self.env['res.partner']
        ResCountry = self.env['res.country']
        msg = ""
        customer_vals = {'customer': True}
        # Get Ref
        if vals.get('ref'):
            ref = vals.get('ref')
            customer = ResPartner.search([('ref', '=', ref)], limit=1)
            if customer:
                return {'code': 1, 'customer': customer, 'msg': msg}
        else:
            ref = self.env['ir.sequence'].next_by_code('res.partner') or '/'
        # Get Name
        name = self._convert_str(vals.get('name'))
        if not name:
            return {'code': 0, 'msg': "Customer name could not be empty"}

        customer_vals.update({'name': name, 'ref': ref})
        list_fields = ['street', 'email', 'mobile', 'website', 'vat',
                       'identify_number', 'function', 'phone', 'fax', 'agency_level',
                       'sub_email_1', 'sub_email_2', 'representative', 'company_id', 'new_customer', 'password']
        for field in list_fields:
            if not vals.get(field):
                continue
            if field in ['email', 'sub_email_1', 'sub_email_2']:
                if not self._validate_email([vals[field]]):
                    return {'code': 0, 'msg': 'Invalid email {} : {} .'.format(field, vals[field])}
            customer_vals.update({field: vals[field]})

        if 'new_customer' in vals:
            customer_vals.update({'new_customer': vals.get('new_customer') == 1 and True or False})

        # Get salesperson
        if vals.get('user_id'):
            user_id = ResUsers.search([('login', '=', vals['user_id'])], limit=1)
            if user_id:
                customer_vals.update({'user_id': user_id.id})
            else:
                pass
                # return {'code': 0, 'msg': 'Salesperson {} is not found'.format(vals['user_id'])}

        # Get state id
        if vals.get('state_code'):
            state_id = ResCountyState.search(
                [('code', '=', vals['state_code'])], limit=1)
            if state_id:
                customer_vals.update({'state_id': state_id.id})
            else:
                return {'code': 0, 'msg': 'State Code {} is not found'.format(vals['state_code'])}

        # Get Date of Birth and Date of Founding
        try:
            if vals.get('date_of_birth'):
                date_of_birth = datetime.strptime(str(vals['date_of_birth']), DF)
                customer_vals.update({'date_of_birth': date_of_birth})
            if vals.get('date_of_founding'):
                date_of_founding = datetime.strptime(str(vals['date_of_founding']), DF)
                customer_vals.update({'date_of_founding': date_of_founding})
        except ValueError:
            return {'code': 0, 'msg': 'Invalid date_of_birth or date_of_founding yyyy-mm-dd'}

        # Get Country id
        if vals.get('country_code'):
            country_id = ResCountry.search([('code', '=', vals.get('country_code'))], limit=1)
            if country_id:
                customer_vals.update({'country_id': country_id.id})
            else:
                return {'code': 0, 'msg': 'Country Code {} is not found'.format(vals.get('country_code'))}

        # Get company type
        if not vals.get('company_type') or vals.get('company_type') not in ('person', 'company'):
            return {
                'code': 0,
                'msg': ("Company type must be in "
                        "['person', 'company']")
            }
        customer_vals.update({'company_type': vals['company_type']})

        # Get customer type
        if not vals.get('customer_type') or vals.get('customer_type') not in ('person', 'agency'):
            return {
                'code': 0,
                'msg': ("Customer type must be in "
                        "['person', 'agency']")
            }
        customer_vals.update({'customer_type': vals['customer_type']})

        # Check gender value
        if vals.get('gender'):
            if vals['gender'] not in ['male', 'female', 'others']:
                return {
                    'code': 0,
                    'msg': ("Gender must be in "
                            "['male', 'female', 'others']")
                }
            customer_vals.update({'gender': vals['gender']})

        # Check company
        if not vals.get('company_id'):
            return {'code': 0, 'msg': "Company ID is not found."}
        customer_vals.update({'company_id': vals['company_id']})

        # Check source
        if vals.get('source'):
            source_id = self.env['res.partner.source'].search([('code', '=', vals['source'])], limit=1)
            if not source_id:
                return {'code': 0, 'msg': ("Customer source '%s' is not found.  " % (vals['source']))}
            customer_vals.update({'source_id': source_id.id})

        customer = ResPartner.create(customer_vals)
        return {'code': 1, 'customer': customer, 'msg': msg}

    def create_order_lines(self, vals):
        """
            TO DO:
            - Checking Order line vals
        """
        # Check type of data
        if type(vals) is not list:
            return {'msg': "Invalid OrderLineEntity"}

        ProductProduct = self.env['product.product']
        ProductCategory = self.env['product.category']
        ProductUom = self.env['product.uom']
        AccountTax = self.env['account.tax']

        error_msg = ''
        order_lines = []
        line_num = 1

        required_arguments = [
            'register_type', 'categ_code', 'product_code', 'product_name',
            'qty', 'uom', 'register_price', 'renew_price', 'capacity_price', 'price_updated',
            'tax', 'company_id', 'notes', 'price_unit']
        non_required_arguments = ['parent_product_code', 'parent_product_name', 'license',
                                  'up_price', 'refund_amount', 'refund_remain_time', 'product_uom_qty']
        for line in sorted(vals, key=lambda l: l['stt']):
            if type(line) is not dict:
                return {
                    'msg': "Invalid OrderLineEntity"}
            argument_error = ''
            line_vals = {}
            parent_product = False

            # Check required arguments
            for argument in required_arguments:
                if argument in line:
                    line_vals[argument] = line[argument]
                    continue
                argument_error += "'%s', " % argument

            if argument_error:
                error_msg += ("### The required arguments: %s of"
                              " order line at line %s are not found! ") % (argument_error, line_num)
                return {'msg': error_msg}

            # Get non required arguments
            for argument in non_required_arguments:
                if line.get(argument):
                    line_vals[argument] = line.get(argument)
            # Check Register type
            if line_vals['register_type'] not in \
                    [re_type[0] for re_type in REGISTER_TYPE]:
                error_msg += ("### Please check 'register_type' of"
                              " order line at line %s ") % line_num

            # Check Product Category
            if not self._convert_str(line_vals['categ_code']):
                error_msg += "### Can't find product category at line %s " % line_num
            product_categ = ProductCategory.search([('code', '=', line_vals['categ_code'])])
            if not product_categ:
                error_msg += "### Can't find product category at line %s " % line_num
            if not line_vals['company_id']:
                error_msg += "### Company ID at line %s is not found! " % line_num

            # Check Product Uom
            product_uom = self._convert_str(line_vals['uom'])
            if not product_uom:
                error_msg += "### Product Uom '%s' at line %s is not found! " % (product_uom, line_num)
            else:
                product_uom = ProductUom.search([('name', '=', product_uom)], limit=1)
                if not product_uom:
                    error_msg += "### Product Uom '%s' at line %s is not found! " % (product_uom, line_num)

            product_ids = ProductProduct
            # Check Product Code
            product_code = self._convert_str(line_vals['product_code'])
            if product_code:
                product_ids = ProductProduct.search([('default_code', '=', line_vals['product_code'])], limit=1)
            else:
                product_code = self.env['ir.sequence'].next_by_code('product.product')

            # Check Price Updated
            if not line_vals.get('price_updated'):
                error_msg += "### Price Updated could be not empty"
            price_updated = line_vals.get('price_updated') == 1 and True or False

            # check tax
            tax_id = AccountTax.with_context(force_company=line_vals['company_id']).search([
                ('amount', '=', float(line_vals['tax'])),
                ('type_tax_use', '=', 'sale'),
                ('company_id', '=', line_vals['company_id'])], limit=1)

            product_name = self._convert_str(line['product_name'])
            if not product_name:
                error_msg += "### Invalid product name at line %s " % line_num

            # Check parent product
            if line_vals.get('parent_product_code', False):
                parent_product = ProductProduct.search([
                    ('default_code', '=', line_vals.get('parent_product_code'))
                ], limit=1)

                if not parent_product:
                    error_msg += ("### Can't find parent product with code"
                                  " '%s' at line %s ") % \
                                 (line_vals.get('parent_product_code'), line_num)

            # Create new product
            if not product_ids and not error_msg:
                new_product_vals = {
                    'default_code': product_code,
                    'name': product_name,
                    'uom_id': product_uom.id,
                    'uom_po_id': product_uom.id,
                    'categ_id': product_categ.id,
                    'minimum_register_time':
                        product_categ.minimum_register_time,
                    'billing_cycle': product_categ.billing_cycle,
                    'type': 'service'
                }
                product_ids = ProductProduct.create(new_product_vals)

            # Create oder lines
            if product_ids and not error_msg:
                new_line_vals = {
                    'register_type': line_vals['register_type'],
                    'product_id': product_ids.id,
                    'parent_product_id': parent_product and parent_product.id or False,
                    'product_category_id': product_categ.id,
                    'time': line_vals['qty'],
                    'original_time': line_vals['qty'],
                    'tax_id': tax_id and [(6, 0, [tax_id.id])] or False,
                    'register_price': line_vals['register_price'],
                    'renew_price': line_vals['renew_price'],
                    'capacity_price': line_vals['capacity_price'],
                    'price_unit': line_vals['price_unit'],
                    'company_id': line_vals['company_id'],
                    'notes': line_vals['notes'] or '',
                    'product_uom': product_uom.id,
                    'price_updated': price_updated,
                }
                if 'license' in line_vals:
                    new_line_vals.update({'license': line_vals['license'] or ''})
                if 'up_price' in line_vals:
                    new_line_vals.update({'up_price': line_vals['up_price'] or 0})
                if 'product_uom_qty' in line_vals:
                    new_line_vals.update({'product_uom_qty': line_vals['product_uom_qty'] or 1})
                if 'refund_amount' in line_vals:
                    new_line_vals.update({'refund_amount': line_vals['refund_amount'] or 0})
                if 'refund_remain_time' in line_vals:
                    new_line_vals.update({'refund_remain_time': line_vals['refund_remain_time'] or 0})
                order_lines.append((0, 0, new_line_vals))
            for item in vals:
                if item.get('parent_stt') == line.get('stt') and not item.get('parent_product_code'):
                    item['parent_product_code'] = product_ids.default_code
            line_num += 1
        return {'line_ids': order_lines, 'msg': error_msg, 'data': {}}

    @api.model
    def create_so(self, billing_type, coupon, date_order, salesperson, sales_team, order_type, customer, status,
                  company_id, type='for_rent', lines=[], source=False):
        """
        TO DO:
            - Create New Sale Order and Customer in Odoo
        """
        # Objects
        CrmTeam = self.env['crm.team']
        SaleOrder = self.env['sale.order']
        # variables
        error_msg = ''
        order_type = order_type
        customer_vals = customer
        team_id = False
        user_id = False

        if not billing_type or billing_type not in ('prepaid', 'postpaid'):
            return {'"code"': 0, '"msg"': '"Billing Type could not be empty and must be in `prepaid` or `postpaid`"'}
        if not date_order:
            return {'"code"': 0, '"msg"': '"Order Date could not be empty"'}
        if not company_id:
            return {'"code"': 0, '"msg"': '"Company ID could not be empty"'}
        if source:
            source_id = self.env['utm.source'].search([('name', '=', source)])
        else:
            source_id = False
        if not order_type:
            return {'"code""': 0, '"msg"': '"Order Type could be not empty"'}
        order_type_id = self.env['sale.order.source'].search([('code', '=', order_type)], limit=1)
        if not order_type_id:
            return {'"code""': 0, '"msg"': '"Order Type not found"'}
        if not customer:
            return {'"code"': 0, '"msg"': '"Customer info could not be empty"'}
        if not status or status not in [state[0] for state in STATES]:
            return {'"code"': 0,
                    '"msg"': '"Status info could not be empty. "'
                             '"\nStatus must be `draft`(Quotation), `waiting`(Waiting), `sale`(In Progress), "'
                             '"`paid`(Paid), `done`(Active), `refuse`(Refused) or `cancel`(Cancelled)"'}
        if not lines:
            return {'"code"': 0, '"msg"': '"Order detail could not be empty"'}
        # Check date_order
        try:
            date_order = datetime.strptime(date_order, DTF) + timedelta(hours=-7)
        except ValueError:
            return {'"code"': 0, '"msg"': '"Invalid order date yyyy-mm-dd h:m:s"'}

        # Check Salesperson
        if salesperson:
            user_id = self.env['res.users'].browse(salesperson)
            if not user_id:
                return {'"code"': 0,
                        '"msg"': '"Salesperson is not found"'}

        # check sale team
        if sales_team:
            team_id = CrmTeam.search([('name', '=', sales_team)], limit=1)
            if not team_id:
                return {'"code"': 0,
                        '"msg"': '"Sales Team {} is not found"'.format(sales_team)}
        try:
            # Prepare Order lines:
            order_lines = self.create_order_lines(lines)
            if order_lines['msg']:
                error_msg += order_lines['msg']

            # Check Customer exits or create a new customer
            customer_result = self.create_customer(customer_vals)
            if customer_result.get('msg') or not customer_result.get('code'):
                self._cr.rollback()
                return {'"code"': 0, '"msg"': '"%s"' % customer_result['msg']}
            customer = customer_result['customer']

            if error_msg:
                self._cr.rollback()
                return {'"code"': 0, '"msg"': '"%s"' % error_msg}

            so_vals = {'partner_id': customer.id,
                       'date_order': date_order,
                       'user_id': user_id and user_id.id or False,
                       'team_id': team_id and team_id.id or False,
                       'state': status,
                       'cf_source_id': order_type_id.id,
                       'coupon': coupon,
                       'company_id': company_id,
                       'source_id': source_id and source_id.id or False,
                       'order_line': order_lines['line_ids'],
                       'billing_type': billing_type,
                       'type': type,
                       }
            so = SaleOrder.with_context(force_company=company_id).create(so_vals)
            return {'"code"': 1, '"msg"': '"Create Order Successful!"', '"order"': '"%s"' % so.name}
        except Exception as e:
            self._cr.rollback()
            return {'"code"': 0, '"msg"': 'Error: %s' % (e.message or repr(e))}

    @api.model
    def get_order_by_customer(self, customer='', state=[]):
        try:
            domain = []
            if not customer and not state:
                return {'"code"': 0, '"msg"': '"Pls enter customer code or state."'}
            if customer:
                customer_id = self.env['res.partner'].search([('ref', '=', customer)])
                if not customer_id:
                    return {'"code"': 0, '"msg"': '"Customer not exists."'}
                if len(customer_id) > 1:
                    return {'"code"': 0, '"msg"': '"Have %s customer with code %s"' % (len(customer_id), customer)}
                domain.append(('partner_id', '=', customer_id.id))
            if state:
                if any(s not in [state[0] for state in STATES] for s in list(state)):
                    return {'"code"': 0, '"msg"': '"Status must be `draft`(Quotation), `sale`(In Progress), `paid`(Paid), '
                                                  '"`done`(Active), `refuse`(Refused) or `cancel`(Cancelled)"'}
                domain.append(('state', 'in', list(state)))
            order_ids = self.env['sale.order'].search(domain)
            data = []
            for order in order_ids:
                item = {}
                item.update({
                    '"id"': order.id,
                    '"name"': '\"' + order.name + '\"',
                    '"partner_id"': order.partner_id and order.partner_id.id or '""',
                    '"partner_code"': '\"' + (order.partner_id and order.partner_id.ref or '') + '\"',
                    '"date_order"': '\"' + (order.date_order or '') + '\"',
                    '"create_date"': '\"' + (order.create_date or '') + '\"',
                    '"coupon"': '\"' + (order.coupon or '') + '\"',
                    '"salesperson"': order.user_id and order.user_id.id or '""',
                    '"salesperson_name"': '"%s"' % (order.user_id and order.user_id.name or ''),
                    '"sales_team_id"': order.team_id and order.team_id.id or '""',
                    '"sales_team_name"': '\"' + (order.team_id and order.team_id.name or '') + '\"',
                    '"type"': '\"' + (order.type or '') + '\"',
                    '"source"': '\"' + (order.cf_source_id and order.cf_source_id.name or '') + '\"',
                    '"company_id"': order.company_id and order.company_id.id or 0,
                    '"amount_untaxed"': order.amount_untaxed or 0,
                    '"amount_tax"': order.amount_tax or 0,
                    '"amount_total"': order.amount_total or 0,
                    '"state"': '\"' + (order.state or '') + '\"',
                    '"billing_type"': '\"' + (order.billing_type or '') + '\"',
                    '"order_line"': []
                })
                for line in order.order_line:
                    order_line = {}
                    order_line.update({
                        '"register_type"': '\"' + (line.register_type or '') + '\"',
                        '"service_status"': '\"' + (line.service_status or '') + '\"',
                        '"product_id"': line.product_id and line.product_id.id or 0,
                        '"product_code"': '\"' + (line.product_id and line.product_id.default_code or '') + '\"',
                        '"product"': '\"' + (line.product_id and line.product_id.name or '') + '\"',
                        '"product_category_id"': line.product_category_id and line.product_category_id.id or 0,
                        '"product_category_code"': '\"' + (
                                    line.product_category_id and line.product_category_id.code or '') + '\"',
                        '"product_category"': '\"' + (
                                    line.product_category_id and line.product_category_id.display_name or '') + '\"',
                        '"parent_product_id"': line.parent_product_id and line.parent_product_id.id or 0,
                        '"parent_product_code"': '\"' + (
                                    line.parent_product_id and line.parent_product_id.default_code or '') + '\"',
                        '"parent_product"': '\"' + (line.parent_product_id and line.parent_product_id.name or '') + '\"',
                        '"product_uom"': '\"' + (line.product_uom and line.product_uom.name or '') + '\"',
                        '"time"': line.time or 0,
                        '"product_uom_qty"': line.product_uom_qty or 0,
                        '"register_price"': line.register_price or 0,
                        '"renew_price"': line.renew_price or 0,
                        '"capacity_price"': line.renew_price or 0,
                        '"price_subtotal"': line.price_subtotal or 0,
                        '"price_tax"': line.price_tax or 0,
                        '"price_total"': line.price_total or 0,
                        '"price_unit"': line.price_unit or 0,
                        '"notes"': '\"' + (line.notes or '') + '\"',
                        '"is_addons"': '\"' + (line.product_category_id and line.product_category_id.is_addons
                                               and 'True' or 'False') + '\"',
                        '"id"': line.id,
                        '"promotion_discount"': line.promotion_discount or 0,
                        '"price_subtotal_no_discount"': line.price_subtotal_no_discount or 0,
                        '"original_time"': line.original_time or 0,
                    })
                    item['"order_line"'].append(order_line)
                data.append(item)
            return {'"code"': 1, '"msg"': '"Successfully"', '"data"': data}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}

    @api.model
    def get_order_by_name(self, name):
        try:
            order = self.env['sale.order'].search([('name', '=', name)], limit=1)
            if not order:
                return {'"code"': 0, '"msg"': '"Order not found"'}
            data = {
                '"id"': order.id,
                '"name"': '\"' + order.name + '\"',
                '"partner_id"': order.partner_id and order.partner_id.id or '""',
                '"partner_code"': '\"' + (order.partner_id and order.partner_id.ref or '') + '\"',
                '"date_order"': '\"' + (order.date_order or '') + '\"',
                '"create_date"': '\"' + (order.create_date or '') + '\"',
                '"coupon"': '\"' + (order.coupon or '') + '\"',
                '"salesperson"': order.user_id and order.user_id.id or '""',
                '"salesperson_name"': '"%s"' % (order.user_id and order.user_id.name or ''),
                '"sales_team_id"': order.team_id and order.team_id.id or '""',
                '"sales_team_name"': '\"' + (order.team_id and order.team_id.name or '') + '\"',
                '"type"': '\"' + (order.type or '') + '\"',
                '"source"': '\"' + (order.cf_source_id and order.cf_source_id.name or '') + '\"',
                '"company_id"': order.company_id and order.company_id.id or 0,
                '"amount_untaxed"': order.amount_untaxed or 0,
                '"amount_tax"': order.amount_tax or 0,
                '"amount_total"': order.amount_total or 0,
                '"state"': '\"' + (order.state or '') + '\"',
                '"billing_type"': '\"' + (order.billing_type or '') + '\"',
                '"order_line"': []
            }
            for line in order.order_line:
                order_line = {}
                order_line.update({
                    '"register_type"': '\"' + (line.register_type or '') + '\"',
                    '"service_status"': '\"' + (line.service_status or '') + '\"',
                    '"product_id"': line.product_id and line.product_id.id or 0,
                    '"product_code"': '\"' + (line.product_id and line.product_id.default_code or '') + '\"',
                    '"product"': '\"' + (line.product_id and line.product_id.name or '') + '\"',
                    '"product_category_id"': line.product_category_id and line.product_category_id.id or 0,
                    '"product_category_code"': '\"' + (
                                line.product_category_id and line.product_category_id.code or '') + '\"',
                    '"product_category"': '\"' + (
                                line.product_category_id and line.product_category_id.display_name or '') + '\"',
                    '"parent_product_id"': line.parent_product_id and line.parent_product_id.id or 0,
                    '"parent_product_code"': '\"' + (
                                line.parent_product_id and line.parent_product_id.default_code or '') + '\"',
                    '"parent_product"': '\"' + (line.parent_product_id and line.parent_product_id.name or '') + '\"',
                    '"product_uom"': '\"' + (line.product_uom and line.product_uom.name or '') + '\"',
                    '"time"': line.time or 0,
                    '"product_uom_qty"': line.product_uom_qty or 0,
                    '"register_price"': line.register_price or 0,
                    '"renew_price"': line.renew_price or 0,
                    '"price_subtotal"': line.price_subtotal or 0,
                    '"price_tax"': line.price_tax or 0,
                    '"price_total"': line.price_total or 0,
                    '"price_unit"': line.price_unit or 0,
                    '"notes"': '\"' + (line.notes or '') + '\"',
                    '"is_addons"': '\"' + (line.product_category_id and line.product_category_id.is_addons
                                           and 'True' or 'False') + '\"',
                    '"id"': line.id,
                    '"promotion_discount"': line.promotion_discount or 0,
                    '"price_subtotal_no_discount"': line.price_subtotal_no_discount or 0,
                    '"original_time"': line.original_time or 0,
                })
                data['"order_line"'].append(order_line)
            return {'"code"': 1, '"msg"': '"Successfully"', '"data"': data}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}

    