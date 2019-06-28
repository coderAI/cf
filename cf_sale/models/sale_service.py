# -*- coding: utf-8 -*-
from odoo import models, fields, api, SUPERUSER_ID, _
from datetime import datetime, timedelta
import logging
from odoo.exceptions import Warning, ValidationError
from odoo.osv.orm import setup_modifiers
from lxml import etree


STATUS = [('draft', 'Draft'),
          ('waiting', 'Waiting'),
          ('active', 'Active'),
          ('stop', 'Stop')]

class SaleService(models.Model):
    _name = 'sale.service'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char("Name", default=lambda self: _('New'), track_visibility='onchange')
    customer_id = fields.Many2one('res.partner', required=True, string="Customer", track_visibility='onchange')
    ip = fields.Char("IP Address / Domain", track_visibility='onchange')
    sub_ip = fields.Char("Sub IP", track_visibility='onchange')
    product_category_id = fields.Many2one('product.category', required=True,
                                          string="Product Category", track_visibility='onchange')
    product_id = fields.Many2one('product.product', required=True, string="Product", track_visibility='onchange')
    parent_id = fields.Many2one('sale.service', "Parent Service", track_visibility='onchange')
    parent_product_id = fields.Many2one('product.product', string="Parent Product", track_visibility='onchange')
    reference = fields.Char(string="Reference", readonly=True, track_visibility='onchange')
    start_date = fields.Date("Start Date", default=fields.Date.context_today, track_visibility='onchange')
    end_date = fields.Date("End Date", track_visibility='onchange')
    addon_list_ids = fields.One2many('sale.service', 'parent_id', string="ADD-ON LIST")
    status = fields.Selection(STATUS, string="Status", readonly=True, default='draft', track_visibility='onchange')
    description = fields.Char('Description')
    time = fields.Float("Time")
    uom_id = fields.Many2one('product.uom', string="UOM", track_visibility='onchange')
    billing_type = fields.Selection([('prepaid', 'Prepaid'), ('postpaid', 'Postpaid')],
                                    "Billing Type", track_visibility='onchange')
    billing_cycle = fields.Selection([('month', 'Month'), ('year', 'Year')],
                                     "Billing Cycle", track_visibility='onchange')
    setup_price_cycle = fields.Float("Setup Price Cycle", track_visibility='onchange')
    renew_price_cycle = fields.Float("Renew Price Cycle", track_visibility='onchange')
    sales_order_ids = fields.Many2many('sale.order', 'service_sale_order_rel', 'service_id', 'order_id',
                                       string="Sales Order")
    so_line_id = fields.Many2one('sale.order.line', string="Sale order line")
    license = fields.Integer(string='License', track_visibility='onchange')
    phone_number = fields.Char("Phone Number", track_visibility='onchange')
    recording_capacity = fields.Char("Recording Capacity")
    extension_capacity = fields.Char("Extension Capacity")
    routing_number = fields.Char("Routing Number")
    to_cloudfone = fields.Char("To CloudFone")
    from_telcp = fields.Char("From Telcp")
    imsi_sim = fields.Char("IMSI Sim")
    imei_port = fields.Char("IMEI Port")
    serial_number = fields.Char("Serial Number")
    mac_address = fields.Char("Mac Address")
    type_crm = fields.Char("Type CRM")
    connect_str = fields.Char("Connect String")
    type = fields.Char()
    network_info = fields.Char("Network Info")
    end_point = fields.Char("End Point")

    @api.model
    def create(self, vals):
        res = super(SaleService, self).create(vals)
        if not res.reference:
            if res.product_category_id.code:
                if res.product_category_id.service_sequence_id:
                    sequence_number = \
                        res.product_category_id.service_sequence_id.next_by_id()
                    res.reference = ''.join(
                        [res.product_category_id.code, sequence_number])
            else:
                raise Warning(_("Please update the product category code!"))
        if res.reference:
            res.name = res.reference + ' - ' + res.product_id.name
        else:
            res.name = res.product_id.name
        return res

    @api.multi
    def start(self):
        self.write({'status': 'active'})

    @api.multi
    def close(self):
        self.write({'status': 'stop'})

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(SaleService, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                       submenu=submenu)
        doc = etree.XML(res['arch'])
        if view_type == 'tree':
            tree_view = doc.xpath("//tree")
            tree_view[0].set('delete', 'false')
            setup_modifiers(tree_view[0])
            if self.env.uid == SUPERUSER_ID:
                tree_view[0].set('delete', 'true')
                setup_modifiers(tree_view[0])
        elif view_type == 'form':
            form_view = doc.xpath("//form")
            if self.user_has_groups('base.group_system') or self.user_has_groups('cf_security.group_sale_support') \
                    or self.user_has_groups('cf_security.group_sale_operator'):
                form_view[0].set('create', 'true')
                form_view[0].set('edit', 'true')
                form_view[0].set('delete', 'false')
                setup_modifiers(form_view[0])
            else:
                form_view[0].set('create', 'false')
                form_view[0].set('edit', 'false')
                form_view[0].set('delete', 'false')
                setup_modifiers(form_view[0])
            if self.env.uid == SUPERUSER_ID:
                form_view[0].set('create', 'true')
                form_view[0].set('edit', 'true')
                form_view[0].set('delete', 'true')
                setup_modifiers(form_view[0])

            check_ref = doc.xpath("//field[@name='reference']")
            check_end_date = doc.xpath("//field[@name='end_date']")
            check_setup_price = doc.xpath("//field[@name='setup_price_cycle']")
            check_renew_price = doc.xpath("//field[@name='renew_price_cycle']")
            check_customer_id = doc.xpath("//field[@name='customer_id']")
            check_product_id = doc.xpath("//field[@name='product_id']")
            check_parent_product_id = doc.xpath("//field[@name='parent_product_id']")
            check_product_category_id = doc.xpath("//field[@name='product_category_id']")
            check_billing_type = doc.xpath("//field[@name='billing_type']")
            check_license = doc.xpath("//field[@name='license']")
            fields_to_options = doc.xpath("//field")
            for node in fields_to_options:
                if (self.user_has_groups('cf_security.group_sale_support') or
                    self.user_has_groups('cf_security.group_sale_operator')) and \
                        check_ref and node not in (check_ref[0]):
                    node.set('readonly', "0")
                    # Support can not edit end date
                    if self.user_has_groups('cf_security.group_sale_support') and \
                            check_end_date and node == check_end_date[0]:
                        node.set('readonly', "0")
                    setup_modifiers(node)
                else:
                    node.set('readonly', "1")
                    setup_modifiers(node)
                if self.user_has_groups('base.group_system') and check_ref and node == check_ref[0]:
                    node.set('readonly', "0")
                    setup_modifiers(node)
                elif not self.user_has_groups('base.group_system') and check_ref and node == check_ref[0]:
                    node.set('readonly', "1")
                    setup_modifiers(node)
                # Support can not see setup price and renew price
                if self.user_has_groups('cf_security.group_sale_support') and \
                        not self.user_has_groups('cf_security.group_sale_operator'):
                    if check_setup_price and check_renew_price and node in (check_setup_price[0], check_renew_price[0]):
                        node.set('invisible', "1")
                        setup_modifiers(node)
                    if check_customer_id and node == check_customer_id[0]:
                        node.set('readonly', "1")
                        setup_modifiers(node)
                    if check_product_id and node == check_product_id[0]:
                        node.set('readonly', "1")
                        setup_modifiers(node)
                    if check_parent_product_id and node == check_parent_product_id[0]:
                        node.set('readonly', "1")
                        setup_modifiers(node)
                    if check_product_category_id and node == check_product_category_id[0]:
                        node.set('readonly', "1")
                        setup_modifiers(node)
                    if check_billing_type and node == check_billing_type[0]:
                        node.set('readonly', "1")
                        setup_modifiers(node)
                    if check_license and node == check_license[0]:
                        node.set('readonly', "1")
                        setup_modifiers(node)
        res['arch'] = etree.tostring(doc)
        return res