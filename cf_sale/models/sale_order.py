# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import Warning
from odoo.osv.orm import setup_modifiers
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta


def format_number(number):
    if number:
        return format(int(number), ',').split('.')[0].replace(',', '.')
    return ''

def format_date(date, type='%Y-%m-%d', format='%d/%m/%Y'):
    return datetime.strptime(date, type).strftime(format)


STATES = [('draft', 'Quotation'),
          ('waiting', 'Waiting'),
          ('sale', 'Sale Order'),
          ('done', 'Active'),
          ('paid', 'Paid'),
          ('refuse', 'Refused'),
          ('cancel', 'Cancelled')]


class SaleOrderSource(models.Model):
    _name = 'sale.order.source'
    _order = 'sequence'

    sequence = fields.Integer()
    name = fields.Char()
    code = fields.Char()


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _check_button_cancel_show(self):
        for order in self:
            order.cancel_show = False
            if order.state == 'draft' or \
                    (order.billing_type == 'postpaid' and order.state == 'sale' and
                     self.user_has_groups('sales_team.group_sale_salesman_all_leads')) or \
                    (order.billing_type == 'prepaid' and order.state == 'sale'):
                order.cancel_show = True

    def _check_edit_info(self):
        for order in self:
            order.edit_info = False
            if not self.user_has_groups('sales_team.group_sale_manager') and \
                    order.billing_type == 'postpaid' and order.cf_source_id and order.cf_source_id.code == 'renew':
                order.edit_info = True

    coupon = fields.Char('Coupon')
    type = fields.Selection([('for_sale', 'For Sale'), ('for_rent', 'For Rent')],
                            string='Type', default='for_rent', readonly=False)
    cf_source_id = fields.Many2one('sale.order.source', "Source",
                                   default=lambda self: self.env['sale.order.source'].search([('code', '=', 'normal')]))
    state = fields.Selection(STATES, default='draft')
    billing_type = fields.Selection([('prepaid', 'Prepaid'), ('postpaid', 'Postpaid')], "Billing Type")
    license = fields.Integer(string='License')
    cancel_show = fields.Boolean(compute='_check_button_cancel_show')
    edit_info = fields.Boolean(compute='_check_edit_info')
    fully_paid = fields.Boolean("Fully Paid")

    @api.multi
    def assign_to_me(self):
        if any(order.user_id for order in self):
            raise Warning(_("Order have received. You can't got it."))
        self.write({
            'user_id': self._uid
        })

    @api.multi
    def action_draft(self):
        orders = self.filtered(lambda s: s.state in ['cancel', 'refuse'])
        orders.write({
            'state': 'draft',
            'procurement_group_id': False,
        })
        orders.mapped('order_line').mapped('procurement_ids').write({'sale_line_id': False})

    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'payment_term_id': False,
                'fiscal_position_id': False,
            })
            return

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        if self.env.user.company_id.sale_note:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.user.company_id.sale_note
        self.update(values)

    @api.multi
    def sent_to_approve(self):
        for order in self:
            if any(not line.price_updated for line in order.order_line):
                raise Warning(_("Please update price before confirming the sales order!"))
        self.write({'state': 'waiting'})

    @api.multi
    def sent_to_refuse(self):
        self.write({'state': 'refuse'})

    @api.multi
    def action_confirm(self):
        if self.type == 'for_rent':
            for order in self:
                if any(not line.price_updated and line.register_type != 'capacity' for line in order.order_line):
                    raise Warning(_("Please update price before confirming the sales order!"))
            res = super(SaleOrder, self).action_confirm()
            # Create Invoice and Validate Invoice
            if self.cf_source_id and self.billing_type == 'postpaid':
                invoice_id = self.with_context(force_company=self.partner_id.company_id.id).action_invoice_create()
                invoice_obj = self.env['account.invoice'].browse(invoice_id[0])
                invoice_obj.with_context(force_company=self.partner_id.company_id.id).action_invoice_open()
            self.filtered(lambda so: so.billing_type == 'postpaid').mapped('order_line').filtered(
                lambda l: l.register_type == 'renew').write({'service_status': 'done'})
            for order in self.filtered(lambda so: so.billing_type == 'postpaid'):
                if not any(line.service_status in ('draft', 'refused') for line in order.order_line):
                    order.state = 'done'
            return res
        else:
            return super(SaleOrder, self.with_context(mb_confirm_sale=True)).action_confirm()

    def _prepare_invoice_line_vals(self, register_type, price_unit, taxes_amount=0, tax_ids=[(6, 0, [])], time=1):
        vals = {
                'time': time,
                'register_type': register_type,
                'price_unit': price_unit,
                'taxes_amount': taxes_amount,
                'invoice_line_tax_ids': tax_ids
                }
        return vals

    def _create_invoice_lines(self, invoice_line, vals, is_copy):
        if is_copy:
            invoice_line.copy(vals)
        else:
            invoice_line.write(vals)
        return True

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        invoice_ids = super(SaleOrder, self).action_invoice_create(grouped=grouped, final=final)
        invoice = self.env['account.invoice'].browse(invoice_ids[0])
        if self.type == 'for_rent':
            for invoice_line in invoice.invoice_line_ids:
                order_line = invoice_line.sale_line_ids
                is_copy = False
                # Capacity Price
                if order_line.capacity_price:
                    vals = self._prepare_invoice_line_vals(
                        'capacity',
                        order_line.capacity_price,
                        taxes_amount=0,
                        tax_ids=[(6, 0, order_line.tax_id and order_line.tax_id.ids or [])])
                    is_copy = self._create_invoice_lines(invoice_line, vals, is_copy)

                if order_line.register_price:
                    # Register price
                    vals = self._prepare_invoice_line_vals(
                        'register',
                        order_line.register_price,
                        taxes_amount=0,
                        tax_ids=[(6, 0, order_line.tax_id and order_line.tax_id.ids or [])])
                    is_copy = self._create_invoice_lines(invoice_line, vals, is_copy)

                # Renews
                register_type = order_line.register_type in ('register', 'upgrade') and 'renew' or \
                                order_line.register_type
                if order_line.renew_price:
                    # Renew price
                    vals = self._prepare_invoice_line_vals(
                        register_type,
                        order_line.renew_price + order_line.up_price,
                        taxes_amount=0,
                        tax_ids=[(6, 0, order_line.tax_id and order_line.tax_id.ids or [])],
                        time=(register_type == 'register' and 1 or order_line.time))
                    is_copy = self._create_invoice_lines(
                        invoice_line, vals, is_copy)
                if not is_copy:
                    invoice_line.write({'register_type': register_type, 'price_unit': 0})
            invoice.compute_taxes()
        else:
            for invoice_line in invoice.invoice_line_ids:
                invoice_line.register_type = 'sale'
        return invoice_ids

    @api.model
    def create_order_renewed(self, days):
        data = {}
        cr = self.env.cr
        cr.execute("""SELECT ss.id
                      FROM sale_service ss
                        JOIN product_product pp ON pp.id = ss.product_id
                        JOIN product_category pc ON pc.id = ss.product_category_id AND pc.to_be_renewed = TRUE
                        LEFT JOIN sale_order_line sol ON sol.product_id = pp.id
                        LEFT JOIN sale_order so ON so.id = sol.order_id AND so.state IN ('draft', 'sale')
                      WHERE ss.end_date = now()::DATE + %s
                          AND ss.status = 'active'
                          AND ss.billing_type = 'prepaid'
                          AND so.id IS NULL
                      GROUP BY ss.id""", (days,))
        renew_service_ids = cr.dictfetchall()
        renew_service_ids = renew_service_ids and [sv['id'] for sv in renew_service_ids] or []
        renew_service_ids = self.env['sale.service'].browse(renew_service_ids)
        for service in renew_service_ids:
            customer_id = service.customer_id.id
            time = service.product_category_id.billing_cycle
            vals = {
                'register_type': 'renew',
                'product_category_id': service.product_category_id.id,
                'product_id': service.product_id.id,
                'parent_product_id': service.parent_product_id.id,
                'time': time,
                'product_uom': service.product_category_id.uom_id.id,
                'service_status': 'draft',
                'company_id': service.customer_id.company_id.id
            }
            user_id = service.customer_id.user_id and service.customer_id.user_id.id or False
            team_id = False
            if user_id:
                team_id = self.env['crm.team'].sudo().search([('member_ids', 'in', [user_id])])
            if customer_id not in data:
                source_id = self.env['sale.order.source'].search([('code', '=', 'renew')], limit=1)
                data[customer_id] = {
                    'cf_source_id': source_id and source_id.id or False,
                    'partner_id': customer_id,
                    'state': 'draft',
                    'type': 'for_rent',
                    'billing_type': 'prepaid',
                    'date_order': datetime.now(),
                    'order_line': [(0, 0, vals)],
                    'user_id': service.customer_id.user_id and service.customer_id.user_id.id or False,
                    'team_id': team_id and team_id.id or False,
                    'company_id': service.customer_id.company_id.id
                }
            else:
                data[customer_id]['order_line'].append((0, 0, vals))
        for index, order in enumerate(data):
            self.env['sale.order'].with_context(force_company=data[order].get('company_id')).sudo().create(data[order])
        self._cr.commit()
        return {'"msg"': 1, '"code"': '"Successfully"'}

    @api.model
    def create_order_renewed_postpaid(self):
        data = {}
        cr = self.env.cr
        cr.execute("""SELECT ss.id
                      FROM sale_service ss
                            JOIN product_product pp ON pp.id = ss.product_id
                            JOIN product_category pc ON pc.id = ss.product_category_id and pc.to_be_renewed = TRUE
                            LEFT JOIN sale_service ss1 ON ss1.id = ss.parent_id
                      WHERE --ss.status = 'active' AND 
                          (ss.end_date IS NULL OR ss.end_date BETWEEN (date_trunc('month', CURRENT_DATE)::DATE + INTERVAL '-1 month')::DATE AND 
                                                 (date_trunc('month', CURRENT_DATE) + INTERVAL '-1 day')::DATE) 
                          AND ss.billing_type = 'postpaid'
                          AND ss.start_date < date_trunc('MONTH',now())::DATE
                          AND (ss1.id IS NULL OR ss1.status = 'active')
                          AND ss.id NOT IN (SELECT ss.id
                                            FROM sale_service ss
                                                JOIN product_product pp ON pp.id = ss.product_id
                                                JOIN product_category pc ON pc.id = ss.product_category_id and pc.to_be_renewed = TRUE
                                                JOIN sale_order_line sol ON sol.product_id = pp.id
                                                JOIN sale_order so ON so.id = sol.order_id AND
                                                            so.date_order::DATE BETWEEN date_trunc('month', CURRENT_DATE)::DATE AND 
                                                            (date_trunc('month', CURRENT_DATE) + INTERVAL '1 month - 1 day')::DATE
                                            WHERE --ss.status = 'active' AND 
                                              (ss.end_date IS NULL OR ss.end_date BETWEEN (date_trunc('month', CURRENT_DATE)::DATE + INTERVAL '-1 month')::DATE AND 
                                                                     (date_trunc('month', CURRENT_DATE) + INTERVAL '-1 day')::DATE) 
                                              AND ss.billing_type = 'postpaid'
                                              AND ss.start_date < date_trunc('MONTH',now())::DATE
                                            GROUP BY ss.id)
                      GROUP BY ss.id""")
        renew_service_ids = cr.dictfetchall()
        renew_service_ids = renew_service_ids and [sv['id'] for sv in renew_service_ids] or []
        renew_service_ids = self.env['sale.service'].browse(renew_service_ids)
        for service in renew_service_ids:
            customer_id = service.customer_id.id
            vals = {
                'register_type': 'renew',
                'product_category_id': service.product_category_id.id,
                'product_id': service.product_id.id,
                'parent_product_id': service.parent_product_id.id,
                'time': 1,
                'product_uom': service.product_category_id.uom_id.id,
                'service_status': 'draft',
                'company_id': service.customer_id.company_id.id
            }
            user_id = service.customer_id.user_id and service.customer_id.user_id.id or False
            team_id = False
            if user_id:
                team_id = self.env['crm.team'].sudo().search([('member_ids', 'in', [user_id])])
            if customer_id not in data:
                source_id = self.env['sale.order.source'].search([('code', '=', 'renew')], limit=1)
                data[customer_id] = {
                    'cf_source_id': source_id and source_id.id or False,
                    'partner_id': customer_id,
                    'state': 'draft',
                    'type': 'for_rent',
                    'billing_type': 'postpaid',
                    'date_order': datetime.now(),
                    'order_line': [(0, 0, vals)],
                    'user_id': service.customer_id.user_id and service.customer_id.user_id.id or False,
                    'team_id': team_id and team_id.id or False,
                    'company_id': service.customer_id.company_id.id
                }
            else:
                data[customer_id]['order_line'].append((0, 0, vals))
        for index, order in enumerate(data):
            self.env['sale.order'].with_context(force_company=data[order].get('company_id')).sudo().create(data[order])
        self._cr.commit()
        return {'"msg"': 1, '"code"': '"Successfully"'}

    @api.multi
    def action_cancel(self):
        if self.type == 'for_rent':
            for order in self.filtered(lambda so: so.invoice_ids):
                if order.invoice_ids.filtered(lambda inv: inv.state in ('open', 'paid')):
                    raise Warning(_("Invoice have validate, can`t cancel SO"))
                if order.invoice_ids.filtered(lambda inv: inv.state == 'cancel'):
                    order.invoice_ids.filtered(lambda inv: inv.state == 'cancel').write({'move_name': False})
                order.invoice_ids.sudo().unlink()
        else:
            if any(inv.state in ('open', 'paid') for inv in self.invoice_ids):
                raise Warning(_("Invoice had paid. Can't cancel this order"))
            if any(pick.state == 'done' for pick in self.picking_ids):
                raise Warning(_("Delivery have done, can't cancel this order"))
        return super(SaleOrder, self).action_cancel()

    @api.multi
    def get_time_service(self, service):
        used_time = 0
        if service.billing_type == 'prepaid':
            time = 1
        else:
            time = 1
            service_date = datetime.strptime(service.start_date, '%Y-%m-%d').date()
            if datetime.now().year > service_date.year:
                if service.end_date and datetime.now().date().strftime('%Y-%m-1') > service.end_date:
                    used_time = datetime.strptime(service.end_date, '%Y-%m-%d').day
            else:
                if service_date.month < datetime.now().month - 1:
                    used_time = 0
                elif service_date.month == datetime.now().month - 1:
                    used_time = (datetime.now().date().replace(day=1) - service_date).days
        return time, used_time

    @api.model
    def format_number(self, number):
        if number:
            return format(int(number), ',').split('.')[0].replace(',', '.')
        return ''

    @api.multi
    def get_service_info(self, expired=False):
        ProductCategory = self.env['product.category']
        rsl = {}
        total, vat, count = 0, 0, 0
        if expired:
            domain = [('product_id', 'in', self.order_line.mapped('product_id').ids),
                      '|', '&',
                            ('start_date', '>=', (datetime.now().date() + relativedelta(months=-1)).replace(day=1)),
                            ('start_date', '<', datetime.now().date().replace(day=1)),
                           '&',
                            ('end_date', '>=', (datetime.now().date() + relativedelta(months=-1)).replace(day=1)),
                            ('end_date', '<', datetime.now().date().replace(day=1))]
            service_ids = self.env['sale.service'].search(domain)
            order_line = self.order_line.filtered(lambda l: l.product_id in service_ids.mapped('product_id'))
            for line in order_line:
                count += 1
                parent_categ = ProductCategory.get_parent_product_category(line.product_category_id)
                service = self.env['sale.service'].search([('product_id', '=', line.product_id.id)], limit=1)
                time, used_time = self.get_time_service(service)
                if parent_categ not in rsl:
                    rsl.update({
                        parent_categ: [{
                            'count': count,
                            'name': service and service.ip and service.ip + ' / ' + service.product_id.name or
                                    line.product_id.name,
                            'description': line.product_category_id.name or '',
                            'start_date': service and service.start_date and
                                          datetime.strptime(service.start_date, '%Y-%m-%d').strftime('%Y-%m-%d') or '',
                            'end_date': service and service.end_date and
                                        datetime.strptime(service.end_date, '%Y-%m-%d').strftime('%Y-%m-%d') or '',
                            'time': used_time,
                            'price': line.price_subtotal
                        }]
                    })
                else:
                    rsl[parent_categ].append({
                        'count': count,
                        'name': service and service.ip and service.ip + ' / ' + service.product_id.name or
                                line.product_id.name,
                        'description': line.product_category_id.name or '',
                        'start_date': service and service.start_date and
                                      datetime.strptime(service.start_date, '%Y-%m-%d').strftime('%Y-%m-%d') or '',
                        'end_date': service and service.end_date and
                                    datetime.strptime(service.end_date, '%Y-%m-%d').strftime('%Y-%m-%d') or '',
                        'time': used_time,
                        'price': line.price_subtotal
                    })
                # total += price
                # vat += price * (service.product_category_id.default_tax and
                #                 int(service.product_category_id.default_tax) or 0) / 100
                # for categ in rsl:
                #     for item in rsl[categ]:
                #         item.update({'total': sum(i['price'] for i in rsl[categ])})
        else:
            service_ids = self.env['sale.service'].search([
                ('product_id', 'in', self.order_line.mapped('product_id').ids),
                ('start_date', '<', (datetime.now().date() + relativedelta(months=-1)).replace(day=1)),
                '|', ('end_date', '>=', datetime.now().date().replace(day=1)), ('end_date', '=', False)])
            order_line = self.order_line.filtered(lambda l: l.register_type != 'renew' or
                                                            l.product_id in service_ids.mapped('product_id'))
            for line in order_line:
                count += 1
                parent_categ = ProductCategory.get_parent_product_category(line.product_category_id)
                service = self.env['sale.service'].search([('product_id', '=', line.product_id.id)], limit=1)
                if parent_categ not in rsl:
                    rsl.update({
                        parent_categ: [{
                            'count': count,
                            'name': service and service.ip and service.ip + ' / ' + service.product_id.name or
                                    line.product_id.name,
                            'description': line.product_category_id.name or '',
                            'start_date': service and service.start_date and
                                          datetime.strptime(service.start_date, '%Y-%m-%d').strftime('%Y-%m-%d') or '',
                            'end_date': service and service.end_date and
                                        datetime.strptime(service.end_date, '%Y-%m-%d').strftime('%Y-%m-%d') or '',
                            'time': 0,
                            'price': line.price_subtotal
                        }]
                    })
                else:
                    rsl[parent_categ].append({
                        'count': count,
                        'name': service and service.ip and service.ip + ' / ' + service.product_id.name or
                                line.product_id.name,
                        'description': line.product_category_id.name or '',
                        'start_date': service and service.start_date and
                                      datetime.strptime(service.start_date, '%Y-%m-%d').strftime('%Y-%m-%d') or '',
                        'end_date': service and service.end_date and
                                    datetime.strptime(service.end_date, '%Y-%m-%d').strftime('%Y-%m-%d') or '',
                        'time': 0,
                        'price': line.price_subtotal
                    })
                # total += price
                # vat += price * (service.product_category_id.default_tax and
                #                 int(service.product_category_id.default_tax) or 0) / 100
                # for categ in rsl:
                #     for item in rsl[categ]:
                #         item.update({'total': sum(i['price'] for i in rsl[categ])})
        return [rsl, total, vat, total + vat]

    @api.multi
    def action_quotation_send(self):
        self.ensure_one()
        if not self.order_line:
            raise Warning("No line")
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('cf_sale', 'cf_services_info_template')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': False,
            'custom_layout': "sale.mail_template_data_notification_email_sale_order",
            'company_id': self.company_id and self.company_id.id or False,
            'composise_wizard_from_so': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def get_date_report(self):
        # First Date of Last Month
        first_date_lm = (datetime.now().date() + relativedelta(months=-1)).strftime('01-%m-%Y')
        # End Date of Last Month
        end_date_lm = (datetime.now().date().replace(day=1) + relativedelta(days=-1)).strftime('%d-%m-%Y')
        # First Date of This Month
        first_date_tm = datetime.now().date().replace(day=1).strftime('01-%m-%Y')
        # import logging
        # logging.info("-------------- %s ----------------" % [first_date_lm, end_date_lm, first_date_tm])
        return [first_date_lm, end_date_lm, first_date_tm, (datetime.now().date() + relativedelta(months=-1)).month]

    @api.multi
    def print_report(self):
        datas = {'ids': self.ids}
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['model'] = 'sale.order'
        report_name = 'cf_sale_info_report'
        report = self.env['ir.actions.report.xml'].search([('report_name', '=', report_name)])
        if report:
            datas['report_type'] = report[0].report_type
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
        }

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(SaleOrder, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                          submenu=submenu)
        if view_type != 'form':
            return res
        doc = etree.XML(res['fields']['order_line']['views']['tree']['arch'])
        if self._context.get("for_sale", False):
            tree_view = doc.xpath("//tree")
            tree_view[0].set('create', 'true')
            setup_modifiers(tree_view[0])
            fields_to_options = doc.xpath("//field")
            for node in fields_to_options:
                if doc.xpath("//field[@name='product_category_id']") and \
                        node == doc.xpath("//field[@name='product_category_id']")[0]:
                    node.set('domain', "[('for_sale', '=', True)]")
                    setup_modifiers(node)
            res['fields']['order_line']['views']['tree']['arch'] = etree.tostring(doc)
        return res


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def _message_get_auto_subscribe_fields(self, updated_fields, auto_follow_fields=None):
        if auto_follow_fields is None:
            auto_follow_fields = ['user_id']
        user_field_lst = []
        for name, field in self._fields.items():
            if name in auto_follow_fields and name in updated_fields and getattr(field, 'track_visibility', False) and \
                    field.comodel_name == 'res.users' and self._name != 'sale.order':
                user_field_lst.append(name)
        return user_field_lst