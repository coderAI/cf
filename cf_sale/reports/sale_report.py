# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools
from odoo.addons.cf_sale.models.sale_order import STATES
from odoo.addons.cf_sale.models.sale_order_line import REGISTER_TYPE, SERVICE_STATUS

# STATES = [('draft', 'Quotation'),
#           ('waiting', 'Waiting'),
#           ('sale', 'Sale Order'),
#           ('done', 'Active'),
#           ('paid', 'Paid'),
#           ('refuse', 'Refused'),
#           ('cancel', 'Cancelled')]

class SaleReport(models.Model):
    _inherit = 'sale.report'

    product_uom_qty = fields.Float('Quantity', readonly=True)
    # vat_status = fields.Selection([('new', 'Draft'), ('to_export', 'Open'), ('exported', 'Done'),
    #                                ('cancel', 'Cancel'), ('lost', 'Lose'), ('refuse', 'Refuse')],
    #                                    string='VAT Status', readonly=True)
    # contract_status = fields.Selection([('new', 'Draft'), ('to_sign', 'Waiting to sign'), ('signed', 'Signed'), ('submit', 'Waiting for Approve'),
    #                                     ('return', 'Approved'), ('refuse_ac', 'Refuse sign'), ('refuse_op', 'Refuse approve'), ('cancel', 'Canceled')],
    #                                    string='Contract Status', readonly=True)
    fully_paid = fields.Char(string='Paid', readonly=True)
    register_type = fields.Selection(REGISTER_TYPE, string='Register Type', readonly=True)
    state = fields.Selection(STATES, string='Status', readonly=True)

    def _select(self):
        super(SaleReport, self)._select()
        res = """
            WITH currency_rate as (%s)
             SELECT min(l.id) as id,
                    l.register_type,
                    l.product_id as product_id,
                    t.uom_id as product_uom,
                    sum(l.product_uom_qty) as product_uom_qty,
                    sum(l.qty_invoiced) as qty_invoiced,
                    sum(l.qty_to_invoice) as qty_to_invoice,
                    sum(l.price_total / COALESCE(cr.rate, 1.0)) as price_total,
                    sum(l.price_subtotal / COALESCE(cr.rate, 1.0)) as price_subtotal,
                    count(*) as nbr,
                    s.name as name,
                    (s.date_order + INTERVAL '7' HOUR) as date,
                    s.state as state,
                    s.partner_id as partner_id,
                    s.user_id as user_id,
                    s.company_id as company_id,
                    extract(epoch from avg(date_trunc('day',s.date_order)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
                    t.categ_id as categ_id,
                    s.pricelist_id as pricelist_id,
                    s.project_id as analytic_account_id,
                    s.team_id as team_id,
                    p.product_tmpl_id,
                    partner.country_id as country_id,
                    partner.commercial_partner_id as commercial_partner_id,
                    case when s.state = 'paid' then 'Paid' else 'Not Paid' end fully_paid
        """ % self.env['res.currency']._select_companies_rates()
        return res
    
    def _from(self):
        super(SaleReport, self)._from()
        from_str = """
                sale_order_line l
                    join sale_order s on (l.order_id=s.id)
                    join res_partner partner on s.partner_id = partner.id
                    left join product_product p on (l.product_id=p.id)
                    left join product_template t on (p.product_tmpl_id=t.id)
                    left join product_uom u on (u.id=l.product_uom)
                    left join product_uom u2 on (u2.id=t.uom_id)
                    left join product_pricelist pp on (s.pricelist_id = pp.id)
                    left join currency_rate cr on (cr.currency_id = pp.currency_id and
                        cr.company_id = s.company_id and
                        cr.date_start <= coalesce(s.date_order, now()) and
                        (cr.date_end is null or cr.date_end > coalesce(s.date_order, now())))
        """
        return from_str

    def _group_by(self):
        super(SaleReport, self)._group_by()
        group_by_str = """
            GROUP BY l.product_id, l.register_type,
                    l.order_id,
                    t.uom_id,
                    t.categ_id,
                    s.name,
                    s.date_order,
                    s.partner_id,
                    s.user_id,
                    s.state,
                    s.company_id,
                    s.pricelist_id,
                    s.project_id,
                    s.team_id,
                    p.product_tmpl_id,
                    partner.country_id,
                    partner.commercial_partner_id,
                    s.fully_paid
        """
        return group_by_str
