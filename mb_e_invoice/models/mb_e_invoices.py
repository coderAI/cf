# -*- coding: utf-8 -*-
from odoo import api, fields, models,  _
from odoo.exceptions import Warning
import datetime
import urllib2
import sys
from lxml import etree

from odoo.addons.mb_e_invoice.models import amount_to_text_vn
import logging
import requests
import json
reload(sys)
sys.setdefaultencoding('utf8')

_logger = logging.getLogger(__name__)
STAGE={
        'draft':'mb_e_draft',
        'open':'mb_e_open',
        'done':'mb_e_done',
        'refuse':'mb_e_refuse',
        'cancel':'mb_e_cancel',
       }
KEY_URL_API=[
            'key_e_invoice api_call_get',
            'key_e_invoice api_call_post',
            'key_e_invoice domain',
             ]

DATE_FORMAT = "%Y-%m-%d"
#có menu cho người khoái ngọt không chị

class AccountInvoiceLine(models.Model):
    """ Printable account_invoice.
    """
    _inherit = 'account.invoice.line'
    mb_e_invoice_ids = fields.Many2one('mb.e.invoices', string='E-Invoices')


class AccountInvoice(models.Model):
    """ Printable account_invoice.
    """
    _inherit = 'account.invoice'
    mb_e_invoices_ids = fields.Many2many('mb.e.invoices', 'account_invoice_e_invoice_rel', 'account_invoice_id', 'e_invoices_id',
                                   string='E-invoice')


class mb_e_invoices(models.Model):
    _name = "mb.e.invoices"
    _description = "E Invoices"
    _rec_name = 'date_create'
    _order = 'date_create desc'
    _inherit = [
        'mail.thread',
        'ir.needaction_mixin',
    ]


    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(mb_e_invoices, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                         submenu=submenu)
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='mb_reason_invoice_id']")
        if dict(self.env.context).get('action_type') == 'set_reject':
            for node in nodes:
                node.set('domain', "[('type', '=', 'e_invoice_cancel')]")
            res['arch'] = etree.tostring(doc)
        return res


    def change_stages(self,state):
        stage_data = self.env['stages.invoice'].sudo().search([('key', '=', STAGE.get(state))], limit=1)
        if stage_data.id == False:
            raise Warning("You lost a config stage with key is '"+STAGE.get(state)+"'")
        return stage_data.id



    def _get_default_stages_id(self):
        stage_data = self.env['stages.invoice'].sudo().search([('key', '=', 'mb_e_draft')], limit=1)
        if stage_data.id == False:
            raise Warning("You lost a config stage with key is 'mb_e_draft'")
        return stage_data.id

    @api.depends('invoice_line_ids')
    def fn_invoice_line_ids(self):
        if self.invoice_ids:
            account_invoice_list=[]
            for i in self.invoice_ids:
                account_invoice_list_tmp = [invoice_line.id for invoice_line in i.invoice_line_ids]
                account_invoice_list.extend(account_invoice_list_tmp)
            self.invoice_line_ids = account_invoice_list
        else:
            self.invoice_line_ids = []


    @api.depends('support_invisible')
    def fn_support_invisible(self):

        if self.stages_name == 'Draft':
            if self.env.user.has_group('mb_e_invoice.group_e_invoice_user') or self.env.user.has_group('mb_e_invoice.group_e_invoice_manager'):
                self.support_invisible =True


    @api.depends('support_readonly_field')
    def fn_support_readonly_field(self):
        res = False
        if self.stages_name == 'Open':
            if self.env.user.has_group('mb_e_invoice.group_e_invoice_user'):
                res = False
            elif self.env.user.has_group('mb_e_invoice.group_e_invoice_exporter'):
                res = False
            elif self.env.user.has_group('mb_e_invoice.group_e_invoice_user'):
                res = True
        if self.stages_name in ['Done','Cancel']:
            res =True
        self.support_readonly_field = res



    @api.depends('support_invisible_dtd')
    def fn_support_invisible_dtd(self):
        if self.stages_name == 'Open':
            if self.env.user.has_group('mb_e_invoice.group_e_invoice_exporter') or self.env.user.has_group('mb_e_invoice.group_e_invoice_manager'):
                self.support_invisible_dtd = True




    name = fields.Char(
        'Reference',
        default=lambda self: self.env['ir.sequence'].next_by_code('mb.e.invoices') or ''
        )
    date_create = fields.Datetime('Creation Date', default=fields.Datetime.now, required=True, readonly=True, copy=False)
    stages_id = fields.Many2one('stages.invoice', string='State', readonly=True, default=lambda self: self._get_default_stages_id())

    stages_name = fields.Char(related='stages_id.name', readonly=True)#('stages.invoice', string='State', readonly=True, default=lambda self: self._get_default_stages_id())
    company_id = fields.Many2one('res.company', string='Company')
    customer_id = fields.Many2one('res.partner', string='Customer')
    customer_name_string = fields.Char(string='Customer Name')
    buyer_name = fields.Char(string='Buyer Name')
    user_id = fields.Many2one('res.users', string='User', track_visibility='onchange', readonly=True,
                              stages_name={'Draft': [('readonly', False)]}, default=lambda self: self.env.user)
    address = fields.Char(string='Address')
    tax_code = fields.Char(string='Tax Code', related='customer_id.vat')#('stages.invoice', string='State', readonly=True, default=lambda self: self._get_default_stages_id())
    payment_type = fields.Selection([('cash', 'Cash'), ('bank', 'Bank'), ('candb', 'Cash and Bank')], string='Payment Type', default='bank')

    invoice_ids = fields.Many2many('account.invoice', 'account_invoice_e_invoice_rel','e_invoices_id', 'account_invoice_id',
                                   string='Invoice')
    #invoice_ids = fields.One2many('account.invoice', 'mb_e_invoice_ids', string='Invoice')
    #invoice_line_ids = fields.One2many(related='invoice_ids.invoice_line_ids')
    invoice_line_ids = fields.One2many('account.invoice.line',compute=fn_invoice_line_ids, string='E-Invoice Lines')
    reason_line_ids = fields.One2many('mb.reason.invoice.line','mb_e_invoices_id', string='Reason Lines')
    #invoice_line_ids = fields.One2many('account.invoice.line', 'mb_e_invoice_ids', string='E Invoice Lines')
    require_date = fields.Date('Require Date')
    template_no = fields.Char(string='Template No')
    reference_no = fields.Char(string='Reference No')
    vat_no = fields.Char(string='Vat No')
    export_date = fields.Date('Export Date')
    export_user_id = fields.Many2one('res.users', string='Export User')
    subtotal = fields.Float('Subtotal')
    subtotal_0 = fields.Float('Subtotal 0%')
    subtotal_5 = fields.Float('Subtotal 5%')
    subtotal_10 = fields.Float('Subtotal 10%')
    tax_5 = fields.Float('Tax 5%')
    tax_10 = fields.Float('Tax 10%')
    total = fields.Float('Total')
    note = fields.Text('note')
    is_detail = fields.Boolean('Is Detail' ,default= True)
    support_invisible = fields.Boolean(compute=fn_support_invisible)
    support_invisible_dtd = fields.Boolean(compute=fn_support_invisible_dtd)
    # foo = fields.Char(track_visibility='always')
    support_readonly_field = fields.Boolean(compute=fn_support_readonly_field)



    def caculate_tax_and_total(self,invoice_ids,payment_type):
        account_invoice_data = self.sudo().env['account.invoice'].browse(invoice_ids)
            # vals.get('invoice_ids')[0][2])

        tax_10 = 0
        tax_5 = 0
        subtotal = 0
        subtotal_0 = 0
        subtotal_5 = 0
        subtotal_10 = 0
        for i_account_invoice in account_invoice_data:
            for i_invoice_line in i_account_invoice.invoice_line_ids:
                if i_invoice_line.invoice_line_tax_ids.type_tax_use == 'sale':
                    if i_invoice_line.invoice_line_tax_ids.amount == 10:
                        subtotal_10 = subtotal_10 + i_invoice_line.price_subtotal
                    elif i_invoice_line.invoice_line_tax_ids.amount == 5:
                        subtotal_5 = subtotal_5 + i_invoice_line.price_subtotal
                    elif i_invoice_line.invoice_line_tax_ids.amount == 0:
                        subtotal_0 = subtotal_0 + i_invoice_line.price_subtotal
                elif i_invoice_line.invoice_line_tax_ids.type_tax_use == False:
                    subtotal = subtotal + i_invoice_line.price_subtotal
        if subtotal_5 != 0:
            tax_5 = subtotal_5 / 100 * 5
        if subtotal_10 != 0:
            tax_10 = subtotal_10 / 10
        total = tax_10 + tax_5 + subtotal + subtotal_0 + subtotal_5 + subtotal_10
        if total >= 20000000 and payment_type == 'cash':
            raise Warning(_("You can't set Payment Type by Cash with total > 20.000.000"))
        return {'subtotal': subtotal,
                         'subtotal_0': subtotal_0,
                         'subtotal_5': subtotal_5,
                         'subtotal_10': subtotal_10,
                         'tax_5': tax_5,
                         'tax_10': tax_10,
                         'total': total}

    @api.model
    def create(self, vals):
        if vals.get('invoice_ids') and vals.get('payment_type'):
            vals.update(self.caculate_tax_and_total(vals.get('invoice_ids')[0][2], vals.get('payment_type')))
        return super(mb_e_invoices, self).create(vals)

    @api.model
    def _write(self, vals):
        payment_type = ''
        if vals.get('payment_type'):
            payment_type = vals.get('payment_type')
        else:
            payment_type = self.payment_type
        if vals.get('invoice_ids') and payment_type:
            vals.update(self.caculate_tax_and_total(vals.get('invoice_ids')[0][2], vals.get('payment_type')))
        elif payment_type == 'cash' and self.total >= 20000000:
            raise Warning(_("You can't set Payment Type by Cash with total > 20.000.000"))
        return super(mb_e_invoices, self)._write(vals)


    @api.onchange('customer_id')
    def onchange_customer_id(self):
        if self.customer_id:
            self.invoice_line_ids = []
            self.invoice_ids = []
            partner = self.customer_id
            stages_id = self.env['stages.invoice'].search([('key', '=', 'mb_e_cancel')], limit=1)
            invoice_id_list_check = [i.id for i in self.env['account.invoice'].search([('partner_id', '=', partner.id)])]
            invoice_ids = [i.id for i in self.env['account.invoice'].search([('partner_id', '=', partner.id)])]
            for invoice_line_id in invoice_id_list_check:
                e_invoice_data = self.search([('stages_id','!=',stages_id.id),('invoice_ids','=',invoice_line_id)], limit=1)
                if e_invoice_data.id:
                    if invoice_line_id in invoice_id_list_check:
                        invoice_ids.remove(invoice_line_id)
            #self.buyer_name = partner.name or ''
            self.address= (partner.street or '')+', '+(partner.state_id and partner.state_id.name or '')+', '+(partner.country_id and partner.country_id.name or '')#+(partner.city or '') +', '
            return {'domain': {'invoice_ids': [('id', 'in', invoice_ids)]}}

    @api.onchange('invoice_ids')
    def onchange_invoice_ids(self):
        account_invoice_list=[]
        invoice_line_list_ids=[]

        stages_id = self.env['stages.invoice'].search([('key', '=', 'mb_e_cancel')], limit=1)
        if self.customer_id:
            partner = self.customer_id
            account_invoice_data_list = self.env['account.invoice'].search([('partner_id', '=', partner.id)])
            logging.info(account_invoice_data_list)

            for i in account_invoice_data_list:
                # not add used in history
                e_invoice_data = self.search([('stages_id', '!=', stages_id.id), ('invoice_ids', '=', i.id)],
                                             limit=1)
                if e_invoice_data.id:
                    if e_invoice_data.id == self._origin.id:
                        invoice_line_list_ids.append(i.id)
                    else:
                        continue
                else:
                    invoice_line_list_ids.append(i.id)

        if self.invoice_ids:
            for i in self.invoice_ids:
                # remove user chose now
                if i in invoice_line_list_ids:
                  invoice_line_list_ids.remove(i.id)
                account_invoice_list_tmp = [invoice_line.id for invoice_line in i.invoice_line_ids]
                account_invoice_list.extend(account_invoice_list_tmp)
            self.invoice_line_ids = account_invoice_list
        else:
            self.invoice_line_ids = []
        return {'domain': {'invoice_ids': [('id', 'in', invoice_line_list_ids)]}}


    @api.multi
    def set_open(self):
        self.write({
            'stages_id': self.change_stages('open')
        })

    @api.multi
    def set_done(self):
        # if self.is_detail:
        #     self.post_order_to_api(self.is_detail)
        #     self.write({'stages_id': self.change_stages('done')})
        #     self.write({
        #         'export_user_id': self._uid})
        # else:
        ir_model_data = self.env['ir.model.data']
        try:
            compose_form_id = ir_model_data.get_object_reference('mb_e_invoice', 'view_mb_e_invoice_set_done_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({

            'e_invoice_id': self.ids[0],
            'is_detail':self.is_detail,
            'action_by': 'set_done_bt',
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mb.e.invoice.set.done.wizard',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }






    @api.multi
    def set_reject(self):
        ir_model_data = self.env['ir.model.data']
        try:
            compose_form_id = ir_model_data.get_object_reference('mb_e_invoice', 'view_mb_reason_invoice_line_wizard')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'mb.e.invoices',
            'default_res_id': self.ids[0],
            'action_type': 'set_reject',
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mb.reason.invoice.line.wizard',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def set_cancel(self):
        ir_model_data = self.env['ir.model.data']
        try:
            compose_form_id = ir_model_data.get_object_reference('mb_e_invoice', 'view_mb_reason_invoice_line_wizard')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'mb.e.invoices',
            'default_res_id': self.ids[0],
            'action_type': 'set_cancel',
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mb.reason.invoice.line.wizard',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def set_to_draft(self):
        self.write({'stages_id': self.change_stages('draft')})

    @api.multi
    def export_action(self):
        return self.download_report()


    @api.multi
    def download_report(self):
        res={}

        domain_url = self.env['mb.e.invoice.api.config'].search([('name', '=', KEY_URL_API[2])]).url
        url_e_invoice_api_get = self.env['mb.e.invoice.api.config'].search([('name', '=', KEY_URL_API[0])]).url
        try:

            token = urllib2.urlopen(url_e_invoice_api_get+'/GetCodeByFkey.aspx?id='+self.name)#+'&domain='+domain_url)#https://portal.hoadon.online/GetCodeByFkey.aspx?id=&domain=     'https://portal.hoadon.online/GetCodeByFkey.aspx?id='

            token = token.read()
            if token:
                full_url = url_e_invoice_api_get+'/Invoice/getinvoice?token=' + token
                res= {
                    'type': 'ir.actions.act_url',
                    'target': 'new',
                    'tag': 'reload',
                    'url': full_url,
                }
        except Exception as e:
            _logger.info('--------------- Download Error: %s  ----------------', (e.message or repr(e)))
            res={
                'error':'--------------- Download Error: %s  ----------------'+(e.message or repr(e)),
            }
            pass
        return res

    def convert_vnd(self, amount):
        amount_text = amount_to_text_vn.amount_to_text(amount, 'vn')
        if amount_text and len(amount_text)>1:
            amount = amount_text[1:]
            head = amount_text[:1]
            amount_text = head.upper()+amount
        return amount_text

    def convert_date(self, date):
        if date:
            date = datetime.datetime.strptime(date, DATE_FORMAT)
            return date.strftime("%d/%m/%Y")
        return ''

    def get_data_products(self,invoice_line_data):
        products = []
        #check price_subtotal <0
        specail_invoice_line_list=[]
        for line in invoice_line_data:
            if line.price_subtotal < 0 and line.register_type == 'renew':
                product_specail={
                    'price_subtotal': line.price_subtotal,
                    'product_id': line.product_id and line.product_id.id or 0,
                    'invoice_id': line.invoice_id and line.invoice_id.id or 0,
                }
                specail_invoice_line_list.append(product_specail)
        for line in invoice_line_data.sorted(lambda l: l.product_id):
            if line.price_subtotal <= 0:
                continue
            VATRate = -1
            VATRate_str = 'No Tax'
            if line.invoice_line_tax_ids.amount == 0:
                if line.invoice_line_tax_ids.name:
                    VATRate = 0
                    VATRate_str = 'Tax 0%'
                else:
                    VATRate = -1
                    VATRate_str = 'No Tax'
            elif line.invoice_line_tax_ids.amount == 5:
                VATRate = 5
                VATRate_str = 'Tax 5%'
            elif line.invoice_line_tax_ids.amount == 10:
                VATRate = 10
                VATRate_str = 'Tax 10%'
            if line.register_type == 'renew':
                tmp_check=False
                for specail_invoice_line in specail_invoice_line_list:
                    if specail_invoice_line.get('product_id') == line.product_id.id and line.invoice_id.id == specail_invoice_line.get('invoice_id'):
                        prodprice = line.price_subtotal + specail_invoice_line.get('price_subtotal')
                        tmp_check = True
                        break
                if tmp_check == False:
                    prodprice = line.price_subtotal
            else:
                prodprice = line.price_subtotal
            if line.invoice_line_tax_ids:
                if prodprice > 0:
                    VATAmount = prodprice / 100 * line.invoice_line_tax_ids.amount if line.invoice_line_tax_ids.amount > 0 else 0
                else:
                    VATAmount = 0
            else:
                VATAmount = 0
            total = prodprice
            amount = total+VATAmount
            if line.time > 0:
                prodquantity = line.time
                prodprice = prodprice / line.time
            else:
                prodquantity = line.quantity or 1
                prodprice = prodprice / prodquantity
            if line.register_type:
                prodname = self.sudo().env['mb.e.invoice.register.type.config'].search([('name','=',line.register_type)], limit=1).value or ('not data for key register_type: '+line.register_type)
                prodname = prodname +' (%s)' % (line.product_id and line.product_id.name) or ''
            else:
                prodname = line.product_id and line.product_id.name or ''
            product = {
                'Code': line.product_id and line.product_id.default_code or '',
                'ProdName' : prodname,#“Tên sản phẩm”
                'ProdUnit' : line.uom_id and line.uom_id.name or '',#“Đơn vị tính”
                'ProdQuantity' : prodquantity,#“Số lượng”
                'ProdPrice' : prodprice,#“Giá”
                'VATRate' : VATRate,
                'VATRate_str' : VATRate_str,
                'VATAmount': VATAmount,  # “Tiền thuế”
                'Total': total ,  # “Tổng tiền trước thuế”
                'Amount': amount ,  # “Tổng tiền sau thuế”
            }
            products.append(product)
        return products



    @api.multi
    def post_order_to_api(self, is_detail=True, product_is_detail= None):


        headers = {
            "Content-Type": "application/json"
        }
        paymentmethod = 'Tiền mặt/Chuyển khoản'

        if self.payment_type == 'cash':
            paymentmethod = 'Tiền mặt'
        elif self.payment_type ==  'bank':
            paymentmethod = 'Chuyển khoản'
        if is_detail:
            product = self.get_data_products(self.invoice_line_ids)
        else:
            product = product_is_detail
        data = {
            'AmountInWords': self.convert_vnd(self.total),
            'ArisingDate': self.convert_date(self.require_date) or '',
            'CusEmail': self.customer_id.sub_email_1 or '',
            'MaKH': self.customer_id.ref,
            'Company': self.customer_id.company_id.id,
            'CusAddress': self.address,
            'CusPhone': self.customer_id.phone,
            'VATAmount': self.tax_5 +self.tax_10,
            'Amount': self.total,
            'Products':product,
            'CusName': self.customer_id.name,
            'fkey': self.name,
            'Buyer': self.buyer_name,
            'Total': self.total - self.tax_5 - self.tax_10,
            'PaymentMethod': paymentmethod,
            'CusTaxCode': self.tax_code or ' ',
        }

        config_api_url_data = self.sudo().env['mb.e.invoice.api.config'].search([('name', '=', KEY_URL_API[1]),('active','=',True)], limit=1)
        if config_api_url_data:

            url_e_invoice_api = config_api_url_data.url+'/api/v1/invoice/importAndPublishInv'

            url_e_invoice_api.replace(" ", "")
        else:
            raise Warning(_(
                "this action can't run. You lost the config Api url with key "+KEY_URL_API[1]))

        data = json.dumps(data)


        r = requests.post(url_e_invoice_api, data=data, headers=headers)
        r = r.text

        try:
            result_data = json.loads(r.decode('string-escape').strip('"'))

        except Exception, e:
            raise Warning(_(r))

        try:
            if result_data['status'] == 'OK':
                _logger.info("------------------------ %s --------------------" % 'connect API maybe okay')
        except Exception, e:
            raise Warning(_("Sent Fails: %s") % (result_data.get('messages', '')))
        if result_data['status'] == 'OK':
            # save data api return
            self.template_no =  result_data['data'][0]['InvTemplate'] or 'API return Null'
            self.reference_no = result_data['data'][0]['InvSerial']
            self.vat_no = result_data['data'][0]['InvNo']
            self.export_date= self.require_date
        else:
            raise Warning(_("Sent Fails: %s")%(result_data.get('messages','')))
        return



    def cancel_order_api_call(self,e_invoices):
        res =False
        domain_url = self.env['mb.e.invoice.api.config'].search([('name', '=', KEY_URL_API[2])]).url

        config_api_url_data = self.sudo().env['mb.e.invoice.api.config'].search(
            [('name', '=', KEY_URL_API[1]), ('active', '=', True)], limit=1)
        if config_api_url_data:
            url_e_invoice_api = config_api_url_data.url+'/api/v1/invoice/CancelInvoice'
            url_e_invoice_api.replace(" ", "")
        else:
            raise Warning(_(
                "this action can't run. You lost the config Api url with key " + KEY_URL_API[1]))
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            'fkey':e_invoices.name,
            'Company':e_invoices.customer_id.company_id.id
        }

        data = json.dumps(data)
        r = requests.post(url_e_invoice_api, data=data, headers=headers)

        r = r.json()
        try:
            result_data = json.loads(r)
        except Exception, e:
            raise Warning(_(r))
        if result_data.get('status',False) == 'OK':
            _logger.info('---------------return parse API Call: %s  ----------------', (result_data.get('status','okay')))
            res= True
        else:
            raise Warning(_("Sent Fails: %s")%(result_data.get('messages','')))

        return res