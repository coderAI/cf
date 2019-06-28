# -*- coding: utf-8 -*-

import time
from openerp.osv import osv
from openerp.report import report_sxw


class Convert_money(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(Convert_money, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
                'time': time,
                'wage_to_text': self.wage_to_text,
            })

    def wage_to_text(self, amount, currency='VND'):
        result = amount_to_text_vi(amount, currency)
        return result[0].upper() + result[1:]

to_19 = (u'không', u'một', u'hai', u'ba', u'bốn', u'năm', u'sáu',
          u'bảy', u'tám', u'chín', u'mười', u'mười một', u'mười hai', u'mười ba',
          u'mười bốn', u'mười lăm', u'mười sáu', u'mười bảy', u'mười tám', u'mười chín')
tens = (u'hai mươi', u'ba mươi', u'bốn mươi', u'năm mươi', u'sáu mươi', u'bảy mươi', u'tám mươi', u'chín mươi')
denom = ('',
          u'ngàn', u'triệu', u'tỉ', u'ngàn tỉ', u'triệu tỉ',
          u'tỉ tỉ', u'ngàn tỉ tỉ', u'triệu tỉ tỉ', u'tỉ tỉ tỉ', u'Nonillion',
          u'Decillion', u'Undecillion', u'Duodecillion', u'Tredecillion', u'Quattuordecillion',
          u'Sexdecillion', u'Septendecillion', u'Octodecillion', u'Icosillion', u'Vigintillion')

# convert a value < 100 to Vietnamese.

def _convert_nn(val):
    """convert a value < 100 to Vietnamese.
    """
    if val < 20:
        return to_19[val]
    for (dcap, dval) in ((k, 20 + (10 * v)) for (v, k) in enumerate(tens)):
        if dval + 10 > val:
            if (val % 10) == 1:
                return dcap + u' mốt'
            elif (val % 10) == 5:
                return dcap + u' lăm'
            elif val % 10:
                return dcap + ' ' + to_19[val % 10]
            return dcap


def _convert_nnn(val):
    """
        convert a value < 1000 to Vietnamese, special cased because it is the level that kicks
        off the < 100 special case.  The rest are more general.  This also allows you to
        get strings in the form of 'forty-five hundred' if called directly.
    """
    word = ''
    (mod, rem) = (val % 100, val // 100)
    if rem > 0:
        word = to_19[rem] + u' trăm'
        if mod > 0:
            word += u' '
    if mod > 0:
        if mod < 10:
            word += u'lẻ '
        word = word + _convert_nn(mod)
    return word


def vi_number(val):
    if val < 100:
        return _convert_nn(val)
    if val < 1000:
         return _convert_nnn(val)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom))):
        if dval > val:
            mod = 1000 ** didx
            l = val // mod
            r = val - (l * mod)
            if l < 10:
                ret = _convert_nn(l) + u' ' + denom[didx]
            else:
                ret = _convert_nnn(l) + u' ' + denom[didx]
            if r > 0:
                ret = ret + u' ' + vi_number(r)
            return ret

def upperfirst(x):
    return x[0].upper() + x[1:]

def amount_to_text_vi(number, currency):
    if currency == 'VND':
        currency = u'đồng'
    number = '%.2f' % number
    units_name = currency
    list = str(number).split('.')
    start_word = vi_number(abs(int(list[0])))
    cents_number = int(list[1])
    end_word = u''
    if cents_number > 0:
        end_word = u' ' + vi_number(int(list[1]))
    cents_name = (cents_number > 1) and u' xu' or u''
    final_result = start_word + ' ' + units_name + end_word + cents_name
    return upperfirst(final_result)

def amount_to_text_en(number, currency):
    if currency == 'VND':
        currency = u'đồng'
    munber = '%.2f' % number
    units_name = currency
    list = str(munber).split('.')
    start_word = vi_number(abs(int(list[0])))
    cents_number = int(list[1])
    end_word = u''
    if cents_number > 0:
        end_word = u' ' + vi_number(int(list[1]))
    cents_name = (cents_number > 1) and u'xu' or u'chẵn'
    final_result = start_word + u' ' + units_name + end_word + cents_name
    return final_result