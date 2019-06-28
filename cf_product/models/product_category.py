# -*- coding: utf-8 -*-
from odoo import api, models, fields
import logging
from odoo.exceptions import Warning
from lxml import etree
from odoo.osv.orm import setup_modifiers


class ProductCategory(models.Model):
    _name = 'product.category'
    _inherit = ["product.category", 'mail.thread']

    @api.multi
    @api.depends('name', 'parent_id', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            category.complete_name = category.name_get()[0][1]

    code = fields.Char()
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)
    service_sequence_id = fields.Many2one('ir.sequence', string="Service Sequence")
    uom_id = fields.Many2one("product.uom", string="UOM")
    minimum_register_time = fields.Float(string='Minimum Register Time',
        help='Minimum time to register one service. For example, to register'
             ' a domain, the minimum time is one year.')
    billing_cycle = fields.Float(string='Minimum Renew Time')
    # Account
    register_account_income_id = fields.Many2one('account.account', company_dependent=True,
        string="Register Income Account", domain=[('deprecated', '=', False)])
    renew_account_income_id = fields.Many2one('account.account', company_dependent=True,
        string="Renew Income Account", domain=[('deprecated', '=', False)])
    capacity_account_income_id = fields.Many2one('account.account', company_dependent=True,
        string="Capacity Income Account", domain=[('deprecated', '=', False)])
    register_account_expense_id = fields.Many2one('account.account', company_dependent=True,
        string="Register Expense Account", domain=[('deprecated', '=', False)])
    renew_account_expense_id = fields.Many2one('account.account', company_dependent=True,
        string="Renew Expense Account", domain=[('deprecated', '=', False)])
    capacity_account_expense_id = fields.Many2one('account.account', company_dependent=True,
        string="Capacity Expense Account", domain=[('deprecated', '=', False)])
    # Analytic Account
    register_analytic_income_acc_id = fields.Many2one('account.analytic.account',
                                                      string='Register Analytic Income Account',
                                                      company_dependent=True)
    renew_analytic_income_account_id = fields.Many2one('account.analytic.account',
                                                       string='Renew Analytic Income Account',
                                                       company_dependent=True)
    capacity_analytic_income_account_id = fields.Many2one('account.analytic.account',
                                                       string='Capacity Analytic Income Account',
                                                       company_dependent=True)
    register_analytic_expense_acc_id = fields.Many2one('account.analytic.account',
                                                       string='Register Analytic Expense Account',
                                                       company_dependent=True)
    renew_analytic_expense_acc_id = fields.Many2one('account.analytic.account',
                                                    string='Renew Analytic Expense Account',
                                                    company_dependent=True)
    capacity_analytic_expense_acc_id = fields.Many2one('account.analytic.account',
                                                    string='Capacity Analytic Expense Account',
                                                    company_dependent=True)
    # Price
    setup_price = fields.Float('Setup Price', track_visibility='onchange')
    renew_price = fields.Float('Renew Price', track_visibility='onchange')
    capacity_price = fields.Boolean("Is Capacity Price?", track_visibility='onchange')
    default_tax = fields.Char("Default Tax", default='10')

    can_be_register = fields.Boolean(string='Can be Register')
    can_be_renew = fields.Boolean(string='Can be Renew', default=True)
    is_addons = fields.Boolean(string="Is Addons", default=False, track_visibility='onchange')
    primary = fields.Boolean("Primary")
    to_be_renewed = fields.Boolean(string="To be Renewed", default=True)
    for_sale = fields.Boolean("For Sale", default=False)
    refund_percent = fields.Float("Refund Percent (%)")
    allow_upgrade = fields.Boolean(string='Allow Upgrade', default=False, copy=False, track_visibility='onchange')
    cf_product_category_ids = fields.Many2many('product.category', 'cf_pc_mpc', 'pc_id', 'mpc_id',
                                               string='Product Category')

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}

        if context.get('search_with_old_category', False):
            new_category_ids = []
            if context.get('old_category_id', False):
                old_category_id = context['old_category_id']
                sql = '''select mpc_id from cf_pc_mpc where pc_id = %s''' % old_category_id
                self._cr.execute(sql)
                new_category_ids = [r[0] for r in self._cr.fetchall()]
            args += [('id', 'in', new_category_ids)]

        return super(ProductCategory, self).search(args, offset, limit, order, count=count)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        res = super(ProductCategory, self).name_search(name, args=args, operator=operator, limit=limit)
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        ctx = self._context
        if ctx.get('in_service'):
            category_ids = self.env['product.category'].search(
                [('child_id', '=', False)])
            if category_ids:
                args += [('id', 'in', category_ids.ids)]
            else:
                args += [('id', 'in', [-1])]
        res = super(ProductCategory, self).name_search(name, args=args, operator=operator, limit=limit)
        return res

    @api.model
    def create(self, vals):
        IrSequence = self.env['ir.sequence']
        if not vals.get('service_sequence_id'):
            new_service_sequence = IrSequence.create({'name': vals['name'],
                                                      'padding': '7'})
            vals['service_sequence_id'] = new_service_sequence.id
        return super(ProductCategory, self).create(vals)

    @api.multi
    def unlink(self):
        for record in self:
            redundant_sequence = record.service_sequence_id
            redundant_sequence.unlink()
        return super(ProductCategory, self).unlink()

    @api.model
    def get_parent_product_category(self, categ_id):
        if categ_id and categ_id.parent_id:
            return self.get_parent_product_category(categ_id.parent_id)
        else:
            return categ_id

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ProductCategory, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                           submenu=submenu)
        if view_type == 'tree':
            if self.user_has_groups('base.group_system') or self.user_has_groups('sales_team.group_sale_manager'):
                doc = etree.XML(res['arch'])
                tree_view = doc.xpath("//tree")
                tree_view[0].set('create', 'true')
                tree_view[0].set('delete', 'true')
                setup_modifiers(tree_view[0])
                res['arch'] = etree.tostring(doc)
            else:
                doc = etree.XML(res['arch'])
                tree_view = doc.xpath("//tree")
                tree_view[0].set('create', 'false')
                tree_view[0].set('delete', 'false')
                setup_modifiers(tree_view[0])
                res['arch'] = etree.tostring(doc)
        if view_type == 'form':
            if self.user_has_groups('base.group_system') or self.user_has_groups('sales_team.group_sale_manager'):
                doc = etree.XML(res['arch'])
                form_view = doc.xpath("//form")
                form_view[0].set('create', 'true')
                form_view[0].set('edit', 'true')
                if not self.user_has_groups('base.group_system'):
                    form_view[0].set('delete', 'false')
                else:
                    form_view[0].set('delete', 'true')
                setup_modifiers(form_view[0])
                res['arch'] = etree.tostring(doc)
            else:
                doc = etree.XML(res['arch'])
                form_view = doc.xpath("//form")
                form_view[0].set('create', 'false')
                form_view[0].set('edit', 'false')
                form_view[0].set('delete', 'false')
                setup_modifiers(form_view[0])
                res['arch'] = etree.tostring(doc)
        return res