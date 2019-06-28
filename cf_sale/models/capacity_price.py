from odoo import api, fields, models, _
from odoo.exceptions import Warning
from datetime import datetime

class CapacityPrice(models.Model):
    _name = 'capacity.price'
    _inherit = ['mail.thread']
    _description = "Capacity Price"

    name = fields.Char('Number')
    date = fields.Date("Capacity Date")
    telephone_price = fields.Float("Telephone Price")
    mobile_price = fields.Float("Mobile Price")
    service_price = fields.Float("Service Price")
    order_id = fields.Many2one('sale.order', "Sale Order")
    invoice_id = fields.Many2one('account.invoice', "Refund Invoice")

    @api.multi
    def unlink(self):
        if any(record.order_id or record.invoice_id for record in self):
            raise Warning(_("Record have create Order or Invoice, can't delete."))
        return super(CapacityPrice, self).unlink()

    @api.model
    def create_order_capacity(self, month, year):
        data = {}
        cr = self.env.cr
        cr.execute("""SELECT id
                      FROM capacity_price
                      WHERE EXTRACT(MONTH FROM capacity_price.date) = %s
                          AND EXTRACT(YEAR FROM capacity_price.date) = %s 
                          AND COALESCE(order_id, 0) = 0""", (month, year))
        capacity_ids = cr.dictfetchall()
        capacity_ids = capacity_ids and [cp['id'] for cp in capacity_ids] or []
        capacity_ids = self.browse(capacity_ids)
        for capacity in capacity_ids:
            service_id = self.env['sale.service'].search([
                ('product_id.name', '=', capacity.name),
                ('product_category_id.capacity_price', '=', True),
                ('product_category_id.refund_percent', '=', 0)
            ], limit=1)
            if not service_id:
                continue
            customer_id = service_id.customer_id.id
            # time = service_id.product_category_id.billing_cycle
            tax_id = service_id.product_category_id.default_tax and \
                     self.env['account.tax'].search([
                         ('amount', '=', int(service_id.product_category_id.default_tax)),
                         ('type_tax_use', '=', 'sale'),
                         ('company_id', '=', service_id.customer_id.company_id.id)
                     ]) or False
            vals = {
                'register_type': 'capacity',
                'product_category_id': service_id.product_category_id.id,
                'product_id': service_id.product_id.id,
                'parent_product_id': service_id.parent_product_id.id,
                'time': 1,
                'capacity_price': capacity.telephone_price + capacity.mobile_price + capacity.service_price,
                'product_uom': service_id.product_category_id.uom_id.id,
                'service_status': 'draft',
                'tax_id': tax_id and [(6, 0, tax_id.ids)] or False,
                'company_id': service_id.customer_id.company_id.id
            }
            user_id = service_id.customer_id.user_id and service_id.customer_id.user_id.id or False
            team_id = False
            if user_id:
                team_id = self.env['crm.team'].sudo().search([('member_ids', 'in', [user_id])])
            if customer_id not in data:
                source_id = self.env['sale.order.source'].search([('code', '=', 'capacity')], limit=1)
                data[customer_id] = {
                    'cf_source_id': source_id and source_id.id or False,
                    'partner_id': customer_id,
                    'state': 'draft',
                    'type': 'for_rent',
                    'billing_type': 'prepaid',
                    'date_order': datetime.now(),
                    'order_line': [(0, 0, vals)],
                    'user_id': service_id.customer_id.user_id and service_id.customer_id.user_id.id or False,
                    'team_id': team_id and team_id.id or False,
                    'company_id': service_id.customer_id.company_id.id
                }
            else:
                data[customer_id]['order_line'].append((0, 0, vals))
        for index, order in enumerate(data):
            order_id = self.env['sale.order'].with_context(force_company=data[order].get('company_id')).sudo().create(
                data[order])
            product_name = order_id.order_line.mapped('product_id').mapped('name')
            capacity_id = capacity_ids.filtered(lambda cp: cp.name in product_name)
            if capacity_id:
                capacity_id.order_id = order_id.id
        self._cr.commit()
        return {'"msg"': 1, '"code"': '"Successfully"'}

    @api.model
    def create_invoice_capacity(self, month, year):
        data = {}
        cr = self.env.cr
        cr.execute("""SELECT id
                      FROM capacity_price
                      WHERE EXTRACT(MONTH FROM capacity_price.date) = %s
                          AND EXTRACT(YEAR FROM capacity_price.date) = %s 
                          AND COALESCE(invoice_id, 0) = 0""", (month, year))
        capacity_ids = cr.dictfetchall()
        capacity_ids = capacity_ids and [cp['id'] for cp in capacity_ids] or []
        capacity_ids = self.browse(capacity_ids)
        for capacity in capacity_ids:
            service_id = self.env['sale.service'].search([
                ('product_id.name', '=', capacity.name),
                ('product_category_id.capacity_price', '=', True),
                ('product_category_id.refund_percent', '>', 0)
            ], limit=1)
            if not service_id:
                continue
            customer_id = service_id.customer_id.id
            # time = service_id.product_category_id.billing_cycle
            tax_id = service_id.product_category_id.default_tax and \
                     self.env['account.tax'].search([
                         ('amount', '=', int(service_id.product_category_id.default_tax)),
                         ('type_tax_use', '=', 'sale'),
                         ('company_id', '=', service_id.customer_id.company_id.id)
                     ]) or False
            vals = {
                'register_type': 'capacity',
                'name': service_id.product_id.display_name,
                'account_id': service_id.product_category_id.capacity_account_income_id.id,
                'price_unit': (capacity.telephone_price + capacity.mobile_price + capacity.service_price)
                              * service_id.product_category_id.refund_percent / 100,
                'quantity': 1,
                'uom_id': service_id.product_id.uom_id.id,
                'product_id': service_id.product_id.id,
                # 'invoice_line_tax_ids': tax_id and [(6, 0, tax_id.ids)] or False,
                'invoice_line_tax_ids': False,
                'account_analytic_id': service_id.product_category_id.capacity_analytic_income_account_id.id,
            }
            user_id = service_id.customer_id.user_id and service_id.customer_id.user_id.id or False
            team_id = False
            if user_id:
                team_id = self.env['crm.team'].sudo().search([('member_ids', 'in', [user_id])])
            if customer_id not in data:
                journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
                currency_id = self.env['account.journal'].browse(journal_id).currency_id or \
                              self.env['account.journal'].browse(journal_id).company_id.currency_id or \
                              self.env.user.company_id.currency_id
                data[customer_id] = {
                    'type': 'out_refund',
                    'account_id': service_id.customer_id.property_account_receivable_id.id,
                    'partner_id': service_id.customer_id.id,
                    'journal_id': journal_id,
                    'currency_id': currency_id.id,
                    'payment_term_id': service_id.customer_id.property_payment_term_id and
                                       service_id.customer_id.property_payment_term_id.id or False,
                    'fiscal_position_id': service_id.customer_id.property_account_position_id.id,
                    'company_id': service_id.customer_id.company_id.id,
                    'user_id': user_id,
                    'team_id': team_id and team_id.id or False,
                    'invoice_line_ids': [(0, 0, vals)],
                }
            else:
                data[customer_id]['invoice_line_ids'].append((0, 0, vals))
        for index, invoice in enumerate(data):
            invoice_id = self.env['account.invoice'].with_context(
                force_company=data[invoice].get('company_id')).sudo().create(data[invoice])
            product_name = invoice_id.invoice_line_ids.mapped('product_id').mapped('name')
            capacity_id = capacity_ids.filtered(lambda cp: cp.name in product_name)
            if capacity_id:
                capacity_id.invoice_id = invoice_id.id
        self._cr.commit()
        return {'"msg"': 1, '"code"': '"Successfully"'}