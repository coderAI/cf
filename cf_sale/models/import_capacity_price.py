# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import xlrd
import base64
from odoo.exceptions import UserError
from datetime import datetime

def get_code(value):
  try:
    return str(int(float(value)))
  except ValueError:
    return value

class ImportCapacityPrice(models.TransientModel):
    _name = 'import.capacity.price'

    excel_file = fields.Binary(string='Excel File')
    log = fields.Text()

    def check_data(self):
        if not self.excel_file:
            raise UserError(_("Pls import file"))
        try:
            record_list = base64.decodestring(self.excel_file)
            excel = xlrd.open_workbook(file_contents=record_list)
            sh = excel.sheet_by_index(0)
        except Exception as e:
            raise UserError(_(str(e)))
        if sh:
            self.log = False
            flag = False
            for row in range(sh.nrows):
                if sh.cell(row, 0).value == 'NUMBER':
                    flag = True
                    continue
                if flag:
                    number = sh.cell(row, 0).value or ''
                    date = datetime.strptime((str(sh.cell(row, 1).value) or '').strip(), '%Y-%m-%d')
                    telephone_price = sh.cell(row, 2).value or 0
                    mobile_price = sh.cell(row, 3).value or 0
                    service_price = sh.cell(row, 4).value or 0
                    if not number or not isinstance(number, basestring):
                        self.log = '%s' % (self.log and self.log + '\n' or '') + \
                                   'Error at line %s: Number %s could be not empty and must be string' % (
                                   row+1, number)
                        continue
                    if not date:
                        self.log = '%s' % (self.log and self.log + '\n' or '') + \
                                   'Error at line %s: Date %s could be not empty' % (row+1, date)
                        continue
                    if not telephone_price and not mobile_price and not service_price:
                        self.log = '%s' % (self.log and self.log + '\n' or '') + \
                                   'Error at line %s: One in Telephone Price %s, Mobile Price %s and ' \
                                   'Service Price %s must be different 0' % \
                                   (row+1, telephone_price, mobile_price, service_price)
                        continue
                    self.log = '%s' % (self.log and self.log + '\n' or '') + 'Check Line %s: Successfully' % (row+1)

    def import_excel(self):
        CapacityPrice = self.env['capacity.price']
        if not self.excel_file:
            raise UserError(_("Pls import file"))
        try:
            record_list = base64.decodestring(self.excel_file)
            excel = xlrd.open_workbook(file_contents = record_list)
            sh = excel.sheet_by_index(0)
        except Exception as e:
            raise UserError(_(str(e)))
        if sh:
            self.log = False
            flag = False
            for row in range(sh.nrows):
                if sh.cell(row, 0).value == 'NUMBER':
                    flag = True
                    continue
                if flag:
                    number = sh.cell(row, 0).value or ''
                    date = datetime.strptime((str(sh.cell(row, 1).value) or '').strip(), '%Y-%m-%d')
                    telephone_price = sh.cell(row, 2).value or 0
                    mobile_price = sh.cell(row, 3).value or 0
                    service_price = sh.cell(row, 4).value or 0
                    if not number or not isinstance(number, basestring):
                        self._cr.rollback()
                        self.log = '%s' % (self.log and self.log + '\n' or '') + \
                                   'Error at line %s: Number %s could be not empty and must be string' % (row+1, number)
                        return True
                    if not date:
                        self._cr.rollback()
                        self.log = '%s' % (self.log and self.log + '\n' or '') + \
                                   'Error at line %s: Date %s could be not empty' % (row+1, date)
                        return True
                    if not telephone_price and not mobile_price and not service_price:
                        self._cr.rollback()
                        self.log = '%s' % (self.log and self.log + '\n' or '') + \
                                   'Error at line %s: One in Telephone Price %s, Mobile Price %s and ' \
                                   'Service Price %s must be different 0' % \
                                   (row+1, telephone_price, mobile_price, service_price)
                        return True
                    try:
                        vals = {
                            'name': number,
                            'date': date,
                            'telephone_price': telephone_price,
                            'mobile_price': mobile_price,
                            'service_price': service_price,
                        }
                        CapacityPrice.create(vals)
                        self.log = '%s' % (self.log and self.log + '\n' or '') + 'Line %s: Successfully' % (row+1)
                    except Exception as e:
                        self._cr.rollback()
                        self.log = '%s' % (self.log and self.log + '\n' or '') + 'Error Line %s: %s' % (row+1, e)
                        return True


