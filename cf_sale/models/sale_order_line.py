# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import Warning
import odoo.addons.decimal_precision as dp
from datetime import datetime

REGISTER_TYPE = [("register", "Register"),
                 ("renew", "Renew"),
                 ("capacity", "Capacity"),
                 ('upgrade', "Upgrade"),
                 ('sale', 'Sale')]

SERVICE_STATUS = [("draft", "Draft"),
                  ("waiting", "Waiting"),
                  ("done", "Done"),
                  ("refused", "Refused")]


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def check_button_activate_show(self):
        for line in self:
            line.active_show = False
            if line.order_id.type == 'for_rent' and line.service_status == 'draft' and \
                    line.register_type != 'capacity' and \
                    ((line.order_id.billing_type == 'prepaid' and line.order_id.fully_paid) or
                     (line.order_id.billing_type == 'postpaid' and
                      line.order_id.state not in ('draft', 'waiting', 'refuse', 'cancel') and
                      line.register_type == 'register')):
                line.active_show = True

    register_type = fields.Selection(REGISTER_TYPE, required=False, string="Register Type")
    parent_product_id = fields.Many2one('product.product', string="Parent Product")
    service_status = fields.Selection(SERVICE_STATUS, string="Status", readonly=True, default='draft', copy=False)
    product_category_id = fields.Many2one('product.category', string="Product Category", required=True)
    register_price = fields.Float('Setup Price', readonly=True)
    renew_price = fields.Float('Renew Price', readonly=True)
    capacity_price = fields.Float("Capacity Price")
    time = fields.Float("Time", required=False)
    price_updated = fields.Boolean(string="Price Updated?", readonly=True, copy=False)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Taxes', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)
    notes = fields.Char(string='Notes')
    promotion_discount = fields.Float("Discount")
    price_subtotal_no_discount = fields.Float('Total No Discount', compute='get_price_subtotal_no_discount', store=True)
    original_time = fields.Float("Original Time")
    up_price = fields.Float('Up Price', default=0)
    license = fields.Integer(string='License')
    date_active = fields.Datetime("Active Date")
    active_show = fields.Boolean(compute="check_button_activate_show")
    register_taxed_amount = fields.Float('Setup Taxed Amount', readonly=True)
    renew_taxed_amount = fields.Float('Renew taxed Amount', readonly=True)
    # type = fields.Selection([('for_sale', 'For Sale'), ('for_rent', 'For Rent')],
    #                         string='Type')

    @api.depends('register_price', 'renew_price', 'capacity_price',
                 'up_price', 'promotion_discount', 'product_uom_qty', 'price_unit')
    def get_price_subtotal_no_discount(self):
        for line in self:
            if line.order_id.type == 'for_rent':
                line.price_subtotal_no_discount = line.register_price + line.renew_price + line.capacity_price + \
                                                  line.up_price + line.promotion_discount
            else:
                line.price_subtotal_no_discount = line.product_uom_qty * line.price_unit

    @api.depends('product_uom_qty', 'discount', 'price_unit',
                 'register_price', 'renew_price', 'capacity_price', 'register_type', 'time')
    def _compute_amount(self):
        for line in self:
            if line.order_id.type == 'for_rent':
                # Compute Tax
                taxes = line.tax_id.compute_all(
                            line.register_price + line.renew_price + line.capacity_price, line.order_id.currency_id,
                            line.product_uom_qty, product=line.product_id,
                            partner=line.order_id.partner_shipping_id)
                tax_amount = taxes['total_included'] - taxes['total_excluded']
                # Compute Up Price
                if line.up_price < 0:
                    raise Warning(_("Can't enter Up Price less than 0"))
                tax = line.tax_id and sum(t.amount for t in line.tax_id) / 100 or 0
                up_tax = line.up_price * tax
                # Compute total
                total = sum([line.register_price, line.renew_price, line.capacity_price, line.up_price, up_tax, tax_amount])
                line.update({'price_tax': tax_amount,
                             'price_total': total,
                             'price_subtotal': total - tax_amount - up_tax})
            else:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                product=line.product_id, partner=line.order_id.partner_shipping_id)
                line.update({
                    'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                })

    def prepare_po_vals(self):
        self.ensure_one()
        ir_values_obj = self.env['ir.values']
        partner_id = ir_values_obj.get_default('purchase.config.settings',
                                               'partner_id')
        if not partner_id:
            raise Warning(_('The default Vendor has been deleted!'))
        return {'partner_id': partner_id,
                'date_planned': fields.Datetime.now(),
                'sale_order_line_id': self.id,
                'company_id': self.order_id.company_id.id}

    @api.multi
    def create_po(self):
        PurchaseOrder = self.env['purchase.order'].with_context(company_id=self.order_id.partner_id.company_id.id,
                                                                force_company=self.order_id.partner_id.company_id.id)
        PurchaseOrderLine = self.env['purchase.order.line'].with_context(
            company_id=self.order_id.partner_id.company_id.id, force_company=self.order_id.partner_id.company_id.id)

        new_pos = self.env['purchase.order']
        for order_line in self:
            # Check PO exists
            if PurchaseOrder.search([('sale_order_line_id', '=', order_line.id)]):
                raise Warning(_("Can't create PO. Order Line have created PO."))
            # Create new Purchase Order
            po_vals = self.with_context(force_company=self.order_id.partner_id.company_id.id).prepare_po_vals()
            new_po = PurchaseOrder.with_context(force_company=self.order_id.partner_id.company_id.id).create(po_vals)
            new_pos |= new_po
            # Create new purchase order lines
            line_vals = {
                'name': self.product_id.display_name,
                'product_id': order_line.product_id.id,
                'product_qty': order_line.time,
                'price_unit': 0,
                'taxes_id': [],
                'order_id': new_po.id,
                'product_uom': order_line.product_uom and order_line.product_uom.id or
                               order_line.product_id.uom_po_id.id,
                'date_planned': new_po.date_order,
                'sale_order_line_id': self.id,
                'register_type': self.register_type,
                'company_id': self.order_id.company_id.id,
                'notes': self.notes,
            }
            PurchaseOrderLine.with_context(company_id=self.order_id.partner_id.company_id.id,
                                           force_company=self.order_id.partner_id.company_id.id).create(line_vals)
        return new_pos

    @api.multi
    def create_service(self):
        SaleService = self.env['sale.service'].with_context(company_id=self.order_id.company_id.id,
                                                            force_company=self.order_id.partner_id.company_id.id)
        for record in self:
            data = {
                'customer_id': record.order_id.partner_id.id,
                'product_category_id': record.product_category_id.id,
                'product_id': record.product_id.id,
                'salesperson_id': record.order_id.user_id.id,
                'sales_order_ids': [(4, record.order_id.id)],
                'time': record.time,
                'uom_id': record.product_uom.id,
                'status': 'waiting',
                'so_line_id': record.id,
                'license': record.license,
                'billing_type': record.order_id.billing_type,
                'billing_cycle': record.order_id.billing_type == 'postpaid' and 'month' or '',
                'setup_price_cycle': record.register_price,
                'renew_price_cycle': record.renew_price,
            }
            domain = [('customer_id', '=', record.order_id.partner_id.id),
                      ('product_category_id', '=', record.product_category_id.id),
                      ('product_id', '=', record.product_id.id)]
            if record.parent_product_id:  # addon
                data['parent_product_id'] = record.parent_product_id.id
                args = [('product_id', '=', record.parent_product_id.id),
                        '|', '&',
                        ('sales_order_ids', 'not in', [record.order_id.id]),
                        ('status', '=', 'active'),
                        '&',
                        ('sales_order_ids', 'in', [record.order_id.id]),
                        ('status', 'in', ('waiting', 'draft'))]
                parent_service = SaleService.search(args, limit=1)
                if parent_service:
                    data['parent_id'] = parent_service.id
                    domain += [('parent_id', '=', parent_service.id)]
                old_services = SaleService.search(domain)
                if not old_services:
                    old_services = SaleService.with_context(
                        force_company=self.order_id.partner_id.company_id.id).create(data)
                else:
                    old_services.write({
                        'so_line_id': record.id,
                        'sales_order_ids': [(4, record.order_id.id)]})
                return old_services

            else:  # service
                service = SaleService.search(domain)
                if not service:
                    service = SaleService.with_context(
                        force_company=self.order_id.partner_id.company_id.id).create(data)
                else:
                    service.write({
                        'so_line_id': record.id,
                        'sales_order_ids': [(4, record.order_id.id)]})

                args = [('sales_order_ids', 'in', [record.order_id.id]),
                        ('parent_product_id', '=', data['product_id']),
                        ('parent_id', '=', False)]
                addon_list = SaleService.search(args)
                addon_vals = []
                for addon in addon_list:
                    addon_vals += [(4, addon.id, None)]
                if addon_vals:
                    service.addon_list_ids = addon_vals
                return service

    @api.multi
    def activate(self):
        for line in self:
            if line.order_id.billing_type != 'postpaid' and \
                    not line.order_id.invoice_ids.filtered(lambda inv: inv.state in ('open', 'paid')):
                raise Warning(_("Invoice have canceled or deleted. Pls create Invoice"))
            if line.register_type == 'renew':
                service = self.env['sale.service'].search_count([('product_id', '=', line.product_id.id),
                                                                 ('customer_id', '=', line.order_id.partner_id.id)])
                if service < 1:
                    raise Warning(_("Service {%s} of Customer {%s} not exists." %
                                    (line.product_id.name, line.order_id.partner_id.display_name)))
            line.write({
                'date_active': datetime.now()
            })
        self.write({'service_status': 'waiting'})
        po = self.create_po()
        service = self.create_service()
        for line in self:
            if not any(line.order_id.order_line.filtered(lambda l: l.service_status == 'draft')) \
                    and line.order_id.type == 'for_rent' and line.order_id.state == 'sale':
                line.order_id.write({'state': 'done'})
        po.write({
            'customer_id': self.order_id.partner_id.id,
            'service_id': service.id
        })
        return service

    @api.model
    def default_get(self, fields):
        res = super(SaleOrderLine, self).default_get(fields)
        if self._context.get('type', False) == 'for_sale':
            res.update({
                'register_type': 'sale',
            })
        return res

    @api.multi
    def _action_procurement_create(self):
        if self._context.get('mb_confirm_sale'):
            return True
        return super(SaleOrderLine, self)._action_procurement_create()