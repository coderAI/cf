# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

#-------------------------------------------------------------
#ENGLISH
#-------------------------------------------------------------
from openerp.tools.translate import _

to_19 = ( u'không', u'một', u'hai', u'ba', u'bốn', u'năm', u'sáu',
          u'bảy', u'tám', u'chín', u'mười', u'mười một', u'mười hai', u'mười ba',
          u'mười bốn', u'mười lăm', u'mười sáu', u'mười bảy', u'mười tám', u'mười chín' )
tens  = ( u'hai mươi', u'ba mươi', u'bốn mươi', u'năm mươi', u'sáu mươi', u'bảy mươi', u'tám mươi', u'chín mươi')
denom = ( '',
          u'ngàn', u'triệu', u'tỷ', u'ngàn tỷ', u'trăm ngàn tỷ',
          'Quintillion',  'Sextillion',      'Septillion',    'Octillion',      'Nonillion',
          'Decillion',    'Undecillion',     'Duodecillion',  'Tredecillion',   'Quattuordecillion',
          'Sexdecillion', 'Septendecillion', 'Octodecillion', 'Novemdecillion', 'Vigintillion' )

# convert a value < 100 to English.
to_ini = 0
def _convert_nn(val,to_ini=None):
    if val>0 and val <= 9 and to_ini == 0:
        return to_19[val]
    if val>0 and val <= 9 and to_ini != 0:
        return to_19[val]
        #return u'lẻ ' + to_19[val]
    if (val > 9 and val < 20) or val==0:
        return  to_19[val]
    for (dcap, dval) in ((k, 20 + (10 * v)) for (v, k) in enumerate(tens)):
        if dval + 10 > val:
            if val % 10:
                a = u'lăm'
                if to_19[val % 10] == u'một':
                    a = u'mốt'
                elif to_19[val % 10] == u'năm':
                    a = u'lăm'
                else:
                    a = to_19[val % 10]
                return dcap + ' ' + a
            return dcap

def _convert_nnn(val,to_ini=None):
    word = ''
    (mod, rem) = (val % 100, val // 100)
    if rem > 0:
        word = to_19[rem] + u' trăm'
        if mod > 0:
            word = word + ' '
        if mod > 0 and mod < 10:
            word = word + u' lẻ '
    if mod > 0:
        word = word + _convert_nn(mod,to_ini)
    return word

to_ini =0
def vietnam_number(val,to_ini=None):
    if to_ini == None:
        to_ini = 0
     
    if val < 100:
        return _convert_nn(val)
    if val < 1000:
         return _convert_nnn(val)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom))):
        if dval > val:
            mod = 1000 ** didx
            l = val // mod
            r = val - (l * mod)
            sodu_str = str(r)
            
            if to_ini == 0:
                ret = _convert_nnn(l,to_ini) + ' ' + denom[didx]
                to_ini = 1
            else:
                ret = _convert_nnn(l,to_ini) + ' ' + denom[didx]
            if len(str(val)) == len(str(l)) + len(str(r)):
                if r > 0:
                    ret = ret + ' ' + vietnam_number(r,to_ini)
            else:
                if r > 0:
                    sodu = '%03d'%(r)
                    cap = 0
                    if len(sodu_str)<3:
                        sodu = '%03d'%(r)
                        cap = 0
                    if len(sodu_str)>3 and len(sodu_str)<6:
                        sodu = '%06d'%(r)
                        cap = 3
                    if len(sodu_str)>6 and len(sodu_str)<9:
                        sodu = '%09d'%(r)
                        cap = 6
                    if len(sodu_str)>9 and len(sodu_str)<12:
                        sodu = '%012d'%(r)
                        cap = 9
                    if len(sodu_str)>12 and len(sodu_str)<15:
                        sodu = '%015d'%(r)
                        cap = 12
                    if len(sodu_str)>15 and len(sodu_str)<18:
                        sodu = '%018d'%(r)
                        cap = 15
                    le = ''
                    sodu_le_str = sodu
                    if cap:
                        sodu_le_str = sodu[:-cap]
                    if sodu_le_str[-1]!='0' and sodu_le_str[1]=='0':
                        le = 'lẻ '
                    ret = ret + ' không trăm ' + le + vietnam_number(r,to_ini)
            return ret

def amount_to_text(number):
    number = '%.2f' % number
    list = str(number).split('.')
    start_word = vietnam_number(int(list[0]))
    final_result = start_word[0].upper()+ start_word[1:] + u' đồng'
    final_result = final_result.split('/')[0] + '.'
    return final_result


#-------------------------------------------------------------
# Generic functions
#-------------------------------------------------------------

_translate_funcs = {'en' : amount_to_text}
    
#TODO: we should use the country AND language (ex: septante VS soixante dix)
#TODO: we should use en by default, but the translation func is yet to be implemented
def amount_to_text(nbr, lang='vn'):
    """
    Converts an integer to its textual representation, using the language set in the context if any.
    Example:
        1654: thousands six cent cinquante-quatre.
    """
    from openerp import netsvc
#    if nbr > 10000000:
#        netsvc.Logger().notifyChannel('translate', netsvc.LOG_WARNING, _("Number too large '%d', can not translate it"))
#        return str(nbr)
    
    if not _translate_funcs.has_key(lang):
        lang = 'en'
    return _translate_funcs[lang](abs(nbr))

if __name__=='__main__':
    from sys import argv
    
    lang = 'nl'
    if len(argv) < 2:
        for i in range(1,200):
            print i, ">>", int_to_text(i, lang)
        for i in range(200,999999,139):
            print i, ">>", int_to_text(i, lang)
    else:
        print int_to_text(int(argv[1]), lang)

