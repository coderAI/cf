# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import Warning

class SearchCustomerWizard(models.TransientModel):
    _name = "search.customer.wizard"
    _description = "Allows sales users to search customer information"

    name = fields.Char("Name", default="Search Customer")
    customer_code = fields.Char(string="Customer Code")
    customer_name = fields.Char(string="Customer Name")
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    mobile_phone = fields.Char(string="Mobile Phone")
    identification = fields.Char(string='Identification / Passport Number')
    vat = fields.Char(string='Tax Code')
    customer_ids = fields.Many2many("res.partner")

    @api.multi
    def search_customer(self):
        self.ensure_one()
        args = []
        customers = False
        domain = [('customer', '=', True)]
        if self.customer_name and len(self.customer_name.strip()) < 3:
            raise Warning(_("Pls input Customer Name longer 3 chars"))
        if self.customer_code:
            args += [('ref', '=', self.customer_code)]
        if self.customer_name:
            args += [('name', 'like', self.customer_name)]
        if self.email:
            args += [('email', '=', self.email)]
        if self.phone:
            args += [('phone', '=', self.phone)]
        if self.mobile_phone:
            args += [('mobile', '=', self.mobile_phone)]
        if self.identification:
            args += [('identify_number', '=', self.identification)]
        if self.vat:
            args += [('vat', '=', self.vat)]
        if args:
            customers = self.env['res.partner'].sudo().search(args + domain)
        self.customer_ids = [(6, 0, customers and customers.ids or [])]