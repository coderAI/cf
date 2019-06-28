# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning
import re
from odoo.tools.float_utils import float_compare
from odoo.osv.orm import setup_modifiers
from odoo.tools.safe_eval import safe_eval
from lxml import etree


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.multi
    def _validate_email(self):
        """
            TO DO:
            - Validate the format of emails
        """
        for partner in self:
            email_list = []
            if partner.email:
                email_list.append(partner.email)
            if partner.sub_email_1:
                email_list.append(partner.sub_email_1)
            if partner.sub_email_2:
                email_list.append(partner.sub_email_2)
            if any(re.match("^[a-zA-Z0-9._%-]+@[a-zA-Z0-9._%-]+.[a-zA-Z]{2,6}$", email) == None for email in email_list):
                return False
        return True

    ref = fields.Char(readonly=True, copy=False)
    identify_number = fields.Char(string='Identify Card/Passport Number')
    date_of_birth = fields.Date(string='Date of Birth')
    date_of_founding = fields.Date(string='Date of Founding')
    sub_email_1 = fields.Char(string='Sub Email 1')
    sub_email_2 = fields.Char(string='Sub Email 2')
    representative = fields.Char(string='Representative')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('waiting', "Waiting"),
         ('done', 'Done'),
         ('refused', 'Refused')],
        default='draft', readonly=True, string='Status')
    gender = fields.Selection(
        [('male', 'Male'),
         ('female', 'Female'),
         ('others', 'Others')],
        string='Gender')
    country_id = fields.Many2one('res.country', string='Country',ondelete='restrict', required=True,
        default=lambda self: self.env['res.country'].search([('code', '=', 'VN')], limit=1))
    street = fields.Char(required=True)
    email = fields.Char(required=True)
    city = fields.Char()
    company_type = fields.Selection(default='person', compute=False)
    customer_type = fields.Selection([('person', 'Personal'), ('agency', 'Agency')], default='person',
                                     string="Customer Type")
    vat = fields.Char(string='Tax Code')
    agency_level = fields.Integer('Agency Level', copy=False)
    max_debt = fields.Integer("Max Debt")
    new_customer = fields.Boolean("New Customer", default=True)
    password = fields.Char()

    _constraints = [
        (_validate_email, 'Please enter a valid email address.',
         ['email', 'sub_email_1', 'sub_email_2']),
    ]

    @api.constrains("vat")
    def check_vat(self):
        pass


    @api.multi
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.ref:
                name = '[' + record.ref + '] ' + record.name
            res.append((record.id, name))
        return res

    @api.multi
    def button_submit_to_operation(self):
        customer = self.sudo().filtered(lambda c: c.state == 'draft')
        if customer:
            customer.write({'state': 'waiting'})
        return True

    @api.multi
    def button_approve(self):
        customer = self.filtered(lambda c: c.state == 'waiting')
        if customer:
            customer.write({'state': 'done'})
        return True

    @api.multi
    def button_refuse(self):
        customer = self.filtered(lambda c: c.state in ('waiting', 'done'))
        if customer:
            customer.write({'state': 'refused'})
        return True

    @api.multi
    def button_set_to_draft(self):
        customer = self.filtered(lambda c: c.state == 'refused')
        if customer:
            customer.write({'state': 'draft'})
        return True

    def get_ref_partner(self):
        IrSequence = self.env['ir.sequence']
        ref = IrSequence.next_by_code('res.partner')
        if self.search_count([('ref', '=', ref)]) > 0:
            return self.get_ref_partner()
        return ref

    @api.model
    def create(self, vals):
        if (vals.get('customer', False) or vals.get('supplier', False)) and not vals.get('ref', False) \
                and not vals.get('parent_id', False):
            vals.update({
                'ref': self.get_ref_partner() or '',
            })
        res = super(ResPartner, self).create(vals)
        res.check_update_right()
        return res

    @api.multi
    def write(self, vals):
        self.check_update_right()
        res = super(ResPartner, self).write(vals)
        for cus in self:
            if not cus.ref and (cus.customer or cus.supplier) and not cus.parent_id:
                cus.write({
                    'ref': self.get_ref_partner() or '',
                })
        return res

    @api.multi
    def check_update_right(self):
        for r in self:
            if (not r.parent_id and r.state not in ('done', 'waiting')) or \
                    (r.parent_id and r.parent_id.state not in ('done', 'waiting')) or \
                    self.user_has_groups('cf_security.group_sale_operator') or \
                    self.user_has_groups('sales_team.group_sale_manager'):
                continue
            raise Warning('''Cannot add a new contact or edit information when customer status is Done or Waiting.
                             Pls contact Operator.''')
        return True

    @api.multi
    def get_customer_address(self):
        self.ensure_one()
        return ', '.join([self.street or '', self.state_id and self.state_id.name or '',
                          self.country_id and self.country_id.name or ''])

    @api.multi
    def view_customer(self):
        partner_form = self.env.ref(
            'cf_customer.view_res_partner_form_inherit', False)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer',
            'res_model': 'res.partner',
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'self',
            'view_id': partner_form.id,
        }

