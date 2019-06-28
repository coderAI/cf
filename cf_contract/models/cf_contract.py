# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning
import re
from odoo.tools.float_utils import float_compare
from odoo.osv.orm import setup_modifiers
from odoo.tools.safe_eval import safe_eval
from lxml import etree
from datetime import datetime
import logging
from odoo.addons.cf_convert_money.models.convert_money import amount_to_text_vi


class ContractLocation(models.Model):
    _name = 'contract.location'

    name = fields.Char()


class ContractFolder(models.Model):
    _name = 'contract.folder'

    name = fields.Char()


class ContractFolderPage(models.Model):
    _name = 'contract.folder.page'

    name = fields.Char()


class CFContract(models.Model):
    _name = "cf.contract"
    _inherit = 'mail.thread'

    def check_edit(self):
        for con in self:
            con.is_edit = False
            if self.user_has_groups('cf_security.group_sale_operator'):
                con.is_edit = True
            else:
                if con.state == 'draft':
                    con.is_edit = True

    name = fields.Char(copy=False, readonly=True, track_visibility='onchange',
                       index=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', "Customer", track_visibility='onchange')
    approved_date = fields.Date("Approved Date", track_visibility='onchange')
    approved_user = fields.Many2one('res.users', "Approved User", track_visibility='onchange')
    location_id = fields.Many2one('contract.location', "Location", track_visibility='onchange')
    folder_id = fields.Many2one('contract.folder', "Folder", track_visibility='onchange')
    page_id = fields.Many2one('contract.folder.page', "Page", track_visibility='onchange')
    attachment_ids = fields.Many2many('ir.attachment', 'contract_attachment_rel', 'contract_id', 'attachment_id',
                                      string="Attachments")
    state = fields.Selection([('draft', 'Draft'),
                              ('waiting', 'Waiting'),
                              ('done', 'Done'),
                              ('refuse', 'Refused'),
                              ('cancel', 'Canceled')], default='draft', string="Status", track_visibility='onchange')
    appendix_ids = fields.One2many('cf.contract.appendix', 'contract_id', "Appendixes")
    appendix_count = fields.Integer(compute='get_appendix_count')
    is_edit = fields.Boolean(compute='check_edit')

    @api.constrains('folder_id', 'page_id')
    def constrains_page(self):
        if self.folder_id and self.page_id:
            contract_id = self.search([('id', '!=', self.id),
                                       ('folder_id', '=', self.folder_id.id),
                                       ('page_id', '=', self.page_id.id)], limit=1)
            if contract_id:
                raise ValidationError("Page %s of Folder %s have used in contract %s. Pls choose another page" %
                                      (self.page_id.name, self.folder_id.name, contract_id.name))

    @api.depends('appendix_ids')
    def get_appendix_count(self):
        for con in self:
            con.appendix_count = len(con.appendix_ids)

    @api.model
    def create(self, vals):
        if self.search_count([('partner_id', '=', vals.get('partner_id'))]):
            raise Warning(_("Contract already exists."))
        if vals.get('name', 'New') != 'New':
            if self.sudo().search_count([('name', '=', vals.get('name', 'New'))]) > 0:
                raise Warning(_("Contract name have exists."))
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code('cf.contract') or 'New'
        return super(CFContract, self).create(vals)

    @api.multi
    def write(self, vals):
        res = super(CFContract, self).write(vals)
        if self.search_count([('partner_id', '=', self.partner_id.id),
                              ('id', '!=', self.id)]):
            raise Warning(_("Contract already exists."))
        if 'name' in vals:
            if self.sudo().search_count([('id', '!=', self.id), ('name', '=', vals.get('name', 'New'))]) > 0:
                raise Warning(_("Contract name have exists."))
        return res

    @api.multi
    def send_to_approve(self):
        self.state = 'waiting'

    @api.multi
    def action_approve(self):
        if not self.location_id or not self.folder_id or not self.page_id:
            raise Warning(_("Pls input Location, Folder and Page."))
        self.write({
            'state': 'done',
            'approved_date': datetime.now().date(),
            'approved_user': self._uid
        })

    @api.multi
    def action_refuse(self):
        self.state = 'refuse'

    @api.multi
    def action_cancel(self):
        self.state = 'cancel'

    @api.multi
    def set_to_draft(self):
        self.state = 'draft'

    @api.multi
    def action_open_appendix(self):
        list_view_id = self.env['ir.model.data'].xmlid_to_res_id('cf_contract.view_cf_contract_appendix_tree')
        form_view_id = self.env['ir.model.data'].xmlid_to_res_id('cf_contract.view_cf_contract_appendix_form')
        return {
            "type": "ir.actions.act_window",
            "res_model": "cf.contract.appendix",
            "views": [[list_view_id, "tree"], [form_view_id, "form"]],
            "domain": [('id', 'in', self.appendix_ids and self.appendix_ids.ids or [])],
            "context": {"create": False, "delete": False},
            "name": "Appendix",
            'view_mode': 'tree,form',
            'view_type': 'form',
        }

    @api.multi
    def print_contract(self):
        datas = {'ids': self.ids}
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['model'] = 'cf.contract'
        if self.partner_id.company_type == 'person':
            report_name = 'cf_contract_person_report'
        else:
            report_name = 'cf_contract_company_report'
        report = self.env['ir.actions.report.xml'].search(
            [('report_name', '=', report_name)])
        if report:
            datas['report_type'] = report[0].report_type
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
        }

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CFContract, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                           submenu=submenu)
        doc = etree.XML(res['arch'])
        if view_type == 'tree':
            if self.user_has_groups('cf_security.group_sale_operator'):
                tree_view = doc.xpath("//tree")
                tree_view[0].set('create', 'true')
                setup_modifiers(tree_view[0])
                res['arch'] = etree.tostring(doc)
            else:
                doc = etree.XML(res['arch'])
                tree_view = doc.xpath("//tree")
                tree_view[0].set('create', 'false')
                setup_modifiers(tree_view[0])
                res['arch'] = etree.tostring(doc)
        elif view_type == 'form':
            if self.user_has_groups('cf_security.group_sale_operator'):
                field_name = doc.xpath("//field[@name='name']")
                field_partner_id = doc.xpath("//field[@name='partner_id']")
                field_approved_date = doc.xpath("//field[@name='approved_date']")
                field_approved_user = doc.xpath("//field[@name='approved_user']")
                field_attachment_ids = doc.xpath("//field[@name='attachment_ids']")
                fields_to_options = doc.xpath("//field")
                for node in fields_to_options:
                    if field_name and field_partner_id and field_approved_date and field_approved_user and \
                            node in (field_name[0], field_partner_id[0],
                                         field_approved_user[0], field_approved_date[0]):
                        node.set('readonly', "0")
                        setup_modifiers(node)
                    if field_attachment_ids and node == field_attachment_ids[0]:
                        node.set('attrs', "{}")
                        setup_modifiers(node)
        res['arch'] = etree.tostring(doc)
        return res


class CFContractAppendix(models.Model):
    _name = 'cf.contract.appendix'
    _inherit = 'mail.thread'

    def get_order_line(self):
        for apd in self:
            apd.order_line_ids = False
            if apd.order_id and apd.order_id.order_line and apd.product_category_id:
                categ_ids = self.env['product.category'].search([('id', 'child_of', apd.product_category_id.id)])
                order_line_ids = apd.order_id.order_line.filtered(lambda line: line.product_category_id in categ_ids)
                apd.order_line_ids = order_line_ids and [(6, 0, order_line_ids.ids)] or False

    def check_edit(self):
        for con in self:
            con.is_edit = False
            if self.user_has_groups('cf_security.group_sale_operator'):
                con.is_edit = True
            else:
                if con.state == 'draft':
                    con.is_edit = True

    name = fields.Char(copy=False, readonly=True, track_visibility='onchange',
                       index=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', "Customer", track_visibility='onchange')
    order_id = fields.Many2one('sale.order', "Sale Order", track_visibility='onchange')
    product_category_id = fields.Many2one('product.category', "Product Category", domain=[('primary', '=', True)])
    contract_id = fields.Many2one('cf.contract', "Contract")
    approved_date = fields.Date("Approved Date", track_visibility='onchange')
    approved_user = fields.Many2one('res.users', "Approved User", track_visibility='onchange')
    location_id = fields.Many2one('contract.location', "Location", track_visibility='onchange')
    folder_id = fields.Many2one('contract.folder', "Folder", track_visibility='onchange')
    page_id = fields.Many2one('contract.folder.page', "Page", track_visibility='onchange')
    attachment_ids = fields.Many2many('ir.attachment', 'appendix_attachment_rel', 'contract_id', 'attachment_id',
                                      string="Attachments")
    state = fields.Selection([('draft', 'Draft'),
                              ('waiting', 'Waiting'),
                              ('done', 'Done'),
                              ('refuse', 'Refused'),
                              ('cancel', 'Canceled')], default='draft', string="Status", track_visibility='onchange')
    order_line_ids = fields.Many2many('sale.order.line', compute='get_order_line', string="Order Lines")
    is_edit = fields.Boolean(compute='check_edit')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code('cf.contract.appendix') or 'New'
        return super(CFContractAppendix, self).create(vals)

    @api.multi
    def send_to_approve(self):
        self.state = 'waiting'

    @api.multi
    def action_approve(self):
        if not self.contract_id.location_id or not self.contract_id.folder_id or not self.contract_id.page_id:
            raise Warning(_("Can't get Location, Folder and Page from Contract."))
        self.write({
            'location_id': self.contract_id.location_id.id,
            'folder_id': self.contract_id.folder_id.id,
            'page_id': self.contract_id.page_id.id,
            'state': 'done',
            'approved_date': datetime.now().date(),
            'approved_user': self._uid
        })

    @api.multi
    def action_refuse(self):
        self.state = 'refuse'

    @api.multi
    def action_cancel(self):
        self.state = 'cancel'

    @api.multi
    def set_to_draft(self):
        self.state = 'draft'

    @api.multi
    def print_contract(self):
        datas = {'ids': self.ids}
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['model'] = 'cf.contract.appendix'
        if any(line.register_type == 'upgrade' for line in self.order_id.order_line):
            if self.partner_id.company_type == 'person':
                report_name = 'cf_contract_appendix_upgrade_person'
            else:
                report_name = 'cf_contract_appendix_upgrade_company'
        elif self.product_category_id.code == '1800':
            if self.partner_id.company_type == 'person':
                report_name = 'cf_contract_appendix_1800_person'
            else:
                report_name = 'cf_contract_appendix_1800_company'
        elif self.product_category_id.code == '1900':
            if self.partner_id.company_type == 'person':
                report_name = 'cf_contract_appendix_1900_person'
            else:
                report_name = 'cf_contract_appendix_1900_company'
        elif self.product_category_id.code == 'MobilePhone':
            if self.partner_id.company_type == 'person':
                report_name = 'cf_contract_appendix_mobifone_person'
            else:
                report_name = 'cf_contract_appendix_mobifone_company'
        elif self.product_category_id.code in ('CloudFone', 'CF4U'):
            if self.partner_id.company_type == 'person':
                report_name = 'cf_contract_appendix_cloudfone_person'
            else:
                report_name = 'cf_contract_appendix_cloudfone_company'
        elif self.product_category_id.code == 'cloudfoneassis':
            if self.partner_id.company_type == 'person':
                report_name = 'cf_contract_appendix_assistant_person'
            else:
                report_name = 'cf_contract_appendix_assistant_company'
        elif self.product_category_id.code in ('Equipment', 'EquipmentForSale'):
            if self.partner_id.company_type == 'person':
                report_name = 'cf_contract_appendix_equipment_person'
            else:
                report_name = 'cf_contract_appendix_equipment_company'
        elif self.product_category_id.code == 'Upgrade':
            if self.partner_id.company_type == 'person':
                report_name = 'cf_contract_appendix_upgrade_person'
            else:
                report_name = 'cf_contract_appendix_upgrade_company'
        else:
            raise Warning(_("No Appendix template to print"))
        report = self.env['ir.actions.report.xml'].search([('report_name', '=', report_name)])
        if report:
            datas['report_type'] = report[0].report_type
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
        }

    @api.model
    def format_number(self, number):
        if number:
            return format(int(number), ',').split('.')[0].replace(',', '.')
        return 0

    @api.model
    def get_report_uom(self, uom_id):
        if not uom_id:
            return ''
        if uom_id.name == 'Lần':
            return 'Vĩnh viễn'
        return uom_id.name

    @api.model
    def get_total_amount_contract(self, order_line_ids):
        if not order_line_ids:
            return 0
        return self.format_number(sum(line.price_subtotal + line.price_subtotal *
                                      sum(tax.amount for tax in line.tax_id) / 100 for line in order_line_ids))

    @api.model
    def get_total_amount_wt_contract(self, order_line_ids):
        if not order_line_ids:
            return 0
        return self.format_number(sum(line.price_subtotal_no_discount for line in order_line_ids))

    @api.model
    def get_total_discount_contract(self, order_line_ids):
        if not order_line_ids:
            return 0
        return self.format_number(sum(line.promotion_discount for line in order_line_ids))

    @api.multi
    def get_list_category(self, is_addons=False):
        if not self.product_category_id:
            return False
        category_ids = self.env['product.agency.price'].search([('categ_id', 'child_of', self.product_category_id.id),
                                                                ('level_id', '=', self.partner_id.agency_level),
                                                                ('categ_id.is_addons', '=', is_addons)])
        return category_ids

    @api.multi
    def get_tax_amount_contract(self):
        if not self.order_line_ids:
            return 0
        # tax = 0
        # for line in self.order_line_ids:
        #     tax += sum(line.price_subtotal * tax.amount / 100 for tax in line.tax_id)
        return self.format_number(
            sum((sum(line.price_subtotal * tax.amount / 100 for tax in line.tax_id)) for line in self.order_line_ids))

    @api.multi
    def get_index_line(self, line):
        if self.product_category_id.code == '1800':
            order_line_ids = self.order_line_ids.filtered(lambda l: l.register_type == 'register')
        else:
            order_line_ids = self.order_line_ids
        for index, item in enumerate(order_line_ids):
            if item == line:
                return index + 1

    @api.multi
    def convert_money_to_string(self, amount=False):
        if not amount:
            return self.order_line_ids and \
                   amount_to_text_vi(sum(line.price_subtotal+
                                         sum(line.price_subtotal * tax.amount / 100 for tax in line.tax_id)
                                         for line in self.order_line_ids), 'VND') or \
                   u'Không đồng'
        else:
            return amount_to_text_vi(amount, 'VND')

    @api.multi
    def get_description_domain(self, line_id):
        if line_id.register_type == 'register':
            return u'Phí đăng ký Tên miền'
        else:
            return u'Phí duy trì Tên miền'

    @api.multi
    def get_price_unit(self, line):
        if line.order_id.partner_id.customer_type == 'agency':
            price_id = self.env['product.agency.price'].search(
                [('categ_id', '=', line.product_category_id.id),
                 ('level_id', '=', line.order_id.partner_id.agency_level)],
                order='id desc', limit=1)
            return self.format_number(price_id and price_id.renew_price) or 0
        else:
            return self.format_number(line.product_category_id.renew_price) or 0

    @api.multi
    def get_register_price(self):
        price = 0
        tax = 0
        total = 0
        qty = 0
        subtotal = 0
        if self.product_category_id.code in ('CloudFoneAssistant', 'cloudfoneassis', 'CloudFone', 'CF4U'):
            price = self.order_line_ids and \
                    sum(line.product_category_id.setup_price
                        for line in self.order_line_ids.filtered(lambda line: line.register_price > 0)) or 0
            tax = self.order_line_ids.filtered(lambda line: line.register_price > 0) and \
                  sum(line.product_category_id.setup_price * sum(t.amount for t in line.tax_id) / 100
                      for line in self.order_line_ids.filtered(lambda line: line.register_price > 0)) or 0
            total = price + tax
            return self.format_number(price), self.format_number(tax), \
                   self.format_number(total), amount_to_text_vi(total, 'VND')
        else:
            for line in self.order_line_ids.filtered(lambda l: l.register_type == 'register'):
                qty += 1
                price = line.register_price
                tax += line.register_price * sum(t.amount for t in line.tax_id) / 100
                total += line.register_price + line.register_price * sum(t.amount for t in line.tax_id) / 100
                subtotal += line.register_price
            return self.format_number(price), self.format_number(tax), \
                   self.format_number(total), amount_to_text_vi(total, 'VND'), qty, subtotal

    @api.multi
    def get_renew_price(self):
        price = 0
        tax = 0
        total = 0
        qty = 0
        subtotal = 0
        if self.product_category_id.code in ('CloudFoneAssistant', 'cloudfoneassis', 'CloudFone', 'CF4U'):
            price = sum(line.product_category_id.renew_price * line.time
                        for line in self.order_line_ids.filtered(lambda line: line.renew_price > 0)) or 0
            tax = self.order_line_ids.filtered(lambda line: line.renew_price > 0) and \
                    sum(line.product_category_id.renew_price * line.time * sum(t.amount for t in line.tax_id) / 100
                        for line in self.order_line_ids.filtered(lambda line: line.renew_price > 0)) or 0
            total = price + tax
            return self.format_number(price), self.format_number(tax), \
                   self.format_number(total), amount_to_text_vi(total, 'VND')
        else:
            for line in self.order_line_ids.filtered(lambda l: l.renew_price > 0):
                qty += line.time
                price = line.product_category_id.renew_price
                tax += line.product_category_id.renew_price * line.time * sum(t.amount for t in line.tax_id) / 100
                total += price * line.time + \
                         price * line.time * sum(t.amount for t in line.tax_id) / 100
                subtotal += line.product_category_id.renew_price * line.time
            return self.format_number(price), self.format_number(tax), \
                   self.format_number(total), amount_to_text_vi(total, 'VND'), qty, subtotal

    @api.multi
    def get_upgrade_service(self):
        order_line_id = self.order_id.order_line[0]
        return order_line_id.old_category_id.name, order_line_id.product_category_id.name

    @api.multi
    def get_info_cloudfone(self, line, type='register'):
        if type == 'register':
            count = 1
            for l in self.order_line_ids.filtered(lambda li: li.register_type == 'register'):
                if l == line:
                    return count, line.product_id.name, self.format_number(line.register_price)
                count += 1
        else:
            count = 1
            for l in self.order_line_ids.filtered(lambda li: li.renew_price > 0):
                if l == line:
                    return count, line.product_id.name, \
                           self.format_number(line.product_category_id.renew_price * line.time)
                count += 1

    @api.multi
    def get_info_equipment(self, line):
        count = 1
        for l in self.order_line_ids:
            if l == line:
                return count, line.product_id.name, line.name, \
                       line.product_uom and line.product_uom.name or '', \
                       self.format_number(line.price_unit or 0), \
                       self.format_number(line.product_uom_qty), \
                       self.format_number(line.price_subtotal)
            count += 1