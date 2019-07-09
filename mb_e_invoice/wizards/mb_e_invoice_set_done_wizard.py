# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import Warning
import logging

_logger = logging.getLogger(__name__)

class mb_e_invoice_set_done_line_wizard(models.TransientModel):
    _name = 'mb.e.invoice.set.done.line.wizard'
    Code = fields.Char(string='Code')
    sequence = fields.Integer('sequence')
    ProdName = fields.Char(string='ProdName')
    ProdUnit = fields.Char(string='ProdUnit')
    ProdQuantity = fields.Char(string='ProdQuantity')
    ProdPrice = fields.Float(string='ProdPrice', compute="compute_sum")
    VATRate = fields.Char(string='VATRate')
    VATRate_str = fields.Char(string='VATRate_str')
    VATAmount_str = fields.Char(string='VATAmount_str')
    VATAmount = fields.Float(string='VATAmount')
    Total = fields.Float(string='Total')
    Amount = fields.Float(string='Amount')
    e_invoice_set_done_wizard_id= fields.Many2one('mb.e.invoice.set.done.wizard')



    @api.depends('Total', 'ProdQuantity')
    @api.multi
    def compute_sum(self):
        for record in self:
            if record.ProdQuantity:
                if float(record.ProdQuantity) <= 0:
                    raise Warning(_("You can't set Time/Quantity smaller than 0"))
            else:
                record.ProdQuantity='1'
            record.ProdPrice = record.Total/float(record.ProdQuantity)

class mb_e_invoice_set_done_wizard(models.TransientModel):
    _name = 'mb.e.invoice.set.done.wizard'


    name = fields.Char(string='Name')
    mb_e_invoice_set_done_line_wizard = fields.One2many('mb.e.invoice.set.done.line.wizard','e_invoice_set_done_wizard_id')


    @api.model
    def create(self, values):
        e_invoice_set_done_line_obj = self.env['mb.e.invoice.set.done.line.wizard']
        line=[]
        for i in values.get('mb_e_invoice_set_done_line_wizard'):
            if i[2] != False:
                e_invoice_set_done_line = e_invoice_set_done_line_obj.browse(i[1])
                e_invoice_set_done_line.write(i[2])
                e_invoice_set_done_line_obj
                line.append([4,i[1],False])
            else:
                line.append(i)
        values.update({'mb_e_invoice_set_done_line_wizard':line})
        return super(mb_e_invoice_set_done_wizard, self).create(values)

    @api.multi
    def write(self, values):
        e_invoice_set_done_line_obj = self.env['mb.e.invoice.set.done.line.wizard']
        line=[]
        for i in values.get('mb_e_invoice_set_done_line_wizard'):
            if i[2] != False:
                e_invoice_set_done_line = e_invoice_set_done_line_obj.browse(i[1])
                e_invoice_set_done_line.write(i[2])
                e_invoice_set_done_line_obj
                line.append([4,i[1],False])
            else:
                line.append(i)
        values.update({'mb_e_invoice_set_done_line_wizard':line})
        return super(mb_e_invoice_set_done_wizard, self).write(values)

    @api.model
    def default_get(self, fields):
        res = super(mb_e_invoice_set_done_wizard, self).default_get(fields)
        rec_context = dict(self.env.context)
        line_ids=[]
        if rec_context:
            rec_context = dict(self.env.context)
            e_invoice_id = rec_context.get('e_invoice_id')
            is_detail = rec_context.get('is_detail')
            e_invoice_set_done_line_obj = self.env['mb.e.invoice.set.done.line.wizard']
            mb_e_invoice_obj = self.env['mb.e.invoices']
            mb_e_invoice = mb_e_invoice_obj.browse(e_invoice_id)
            if is_detail:
                for i in mb_e_invoice_obj.get_data_products(mb_e_invoice.invoice_line_ids):
                    e_invoice_set_done_line = e_invoice_set_done_line_obj.create(i)
                    line_ids.append(e_invoice_set_done_line.id)
            else:
                total_none = 0
                total_0 = 0
                total_5 = 0
                total_10 = 0
                check_none = False
                check_0 = False
                check_5 = False
                check_10 = False
                def create_values_line (Code,total, VATRate, VATRate_str, VATAmount, amount):
                    return {
                        'Code': Code,
                        'ProdName': '',  # “Tên sản phẩm”
                        'ProdUnit': '',  # “Đơn vị tính”
                        'ProdQuantity': '1',  # “Số lượng”
                        'ProdPrice': total,  # “Giá”
                        'VATRate': VATRate,
                        'VATRate_str': VATRate_str,
                        'VATAmount_str': ' ' + str(VATAmount)+ ' ',  # “Tiền thuế”
                        'VATAmount': VATAmount,  # “Tiền thuế”
                        'Total': total,  # “Tổng tiền trước thuế”
                        'Amount': amount,  # “Tổng tiền sau thuế”
                    }

                for i in mb_e_invoice.invoice_line_ids:
                    if i.invoice_line_tax_ids.amount:
                        if i.invoice_line_tax_ids.amount == 0:
                            total_0 = total_0 + i.price_subtotal
                            check_0 = True
                        elif i.invoice_line_tax_ids.amount == 5:
                            total_5 = total_5 + i.price_subtotal
                            check_5 = True
                        elif i.invoice_line_tax_ids.amount == 10:
                            total_10 = total_10 + i.price_subtotal
                            check_10 = True
                    else:
                        total_none = total_none + i.price_subtotal
                        check_none = True

                if check_none:
                    e_invoice_set_done_line = e_invoice_set_done_line_obj.create(create_values_line('code_none',total_none,-1,'None Tax',0,total_none))
                    line_ids.append(e_invoice_set_done_line.id)
                if check_0:
                    e_invoice_set_done_line = e_invoice_set_done_line_obj.create(
                        create_values_line('code_0',total_0,0,'Tax 0',0,total_0))
                    line_ids.append(e_invoice_set_done_line.id)
                if check_5:
                    Amount_5 = total_5 / 100 * 5 if total_5 > 0 else 0
                    e_invoice_set_done_line = e_invoice_set_done_line_obj.create(
                        create_values_line('code_5',total_5,5,'Tax 5',Amount_5,total_5+Amount_5))
                    line_ids.append(e_invoice_set_done_line.id)
                if check_10:
                    Amount_10 = total_10 / 100 * 10 if total_10 > 0 else 0
                    e_invoice_set_done_line = e_invoice_set_done_line_obj.create(
                        create_values_line('code_10',total_10,10,'Tax 10',Amount_10,total_10+Amount_10))
                    line_ids.append(e_invoice_set_done_line.id)
        res['mb_e_invoice_set_done_line_wizard']=line_ids

        return res

    @api.multi
    def save_btn(self):
        rec_context = dict(self.env.context)
        e_invoice_id = rec_context.get('e_invoice_id')
        fields_name = ['Code', 'ProdName', 'ProdUnit', 'ProdQuantity', 'ProdPrice','VATRate','VATRate_str','VATAmount','Total','Amount']
        mb_e_invoice_obj = self.env['mb.e.invoices']
        e_invoice_set_done_line_obj = self.env['mb.e.invoice.set.done.line.wizard']
        mb_e_invoice = mb_e_invoice_obj.browse(e_invoice_id)
        line_wizard=[]
        for i_line_wizard in self.mb_e_invoice_set_done_line_wizard:
            one_line={}
            for i_fields_name in fields_name:
                one_line.update({i_fields_name:i_line_wizard[i_fields_name]})
            line_wizard.append(one_line)
        mb_e_invoice.post_order_to_api(False,line_wizard)
        mb_e_invoice.stages_id = mb_e_invoice_obj.change_stages('done')
        mb_e_invoice.export_user_id = self._uid
