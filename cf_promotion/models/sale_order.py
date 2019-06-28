# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import datetime
import logging
from odoo.exceptions import Warning
import warnings
import calendar
from dateutil.relativedelta import relativedelta
from decimal import Decimal

def is_number(value):
    try:
        Decimal(int(value))
        return True
    except:
        return False

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def get_product_category(self, product_category_ids):
        if not product_category_ids:
            return []
        return self.env['product.category'].search([('id', 'child_of', product_category_ids.ids)])

    @api.multi
    def check_promotion_condition(self):
        coupon_id = self.env['mb.coupon'].search([('name', '=', self.coupon.strip())])
        if not coupon_id:
            self._cr.commit()
            raise Warning(_("Coupon not exists"))
        match, promotion_group, count = False, [], 0
        count_order = self.env['sale.order'].sudo().search_count([('state', 'in', ('paid', 'done')),
                                                                  ('coupon', '=', self.coupon.strip())])
        if count_order >= coupon_id.max_used_time:
            self._cr.commit()
            raise Warning(_("Coupon used exceeded number of times allowed"))
        if datetime.now().strftime('%Y-%m-%d %H:%M:%S') > coupon_id.expired_date:
            self._cr.commit()
            raise Warning(_("Coupon used over expired time"))
        # logging.info("......................................")
        promotion_id = coupon_id.promotion_id
        if promotion_id.status != 'run':
            self._cr.commit()
            raise Warning(_("Promotion have stopped"))
        if promotion_id.date_from > datetime.now().strftime('%Y-%m-%d %H:%M:%S') or \
                datetime.now().strftime('%Y-%m-%d %H:%M:%S') > promotion_id.date_to:
            self._cr.commit()
            raise Warning(_("Promotion not yet started"))
        # Check A Customer only used once
        if promotion_id.only_used_once:
            order_ids = self.search_count([('partner_id', '=', self.partner_id.id),
                                           ('coupon', '=', self.coupon.strip()),
                                           ('state', 'in', ('paid', 'done'))])
            if order_ids >= 1:
                self._cr.commit()
                raise Warning(_("Customer used the coupon code in another order"))
        # Check Total Product Discount
        if promotion_id.is_total_product_discount and len(promotion_id.total_product_discount) > 0:
            for item in promotion_id.total_product_discount:
                category_ids = self.env['product.category'].search([('id', 'child_of', item.product_category_id.id)])
                domain = [('product_category_id', 'in', category_ids.ids),
                          ('order_id.state', 'in', ('paid', 'done')),
                          ('order_id.coupon', 'in', promotion_id.coupon_ids.mapped('name'))]
                if promotion_id.is_register_type and promotion_id.register_type:
                    domain.append(('register_type', 'in', promotion_id.register_type.mapped('code')))
                order_line_ids = self.env['sale.order.line'].search_count(domain)
                order_count_service = self.order_line.filtered(
                    lambda l: l.product_category_id in category_ids)
                if promotion_id.is_register_type and promotion_id.register_type:
                    order_count_service = order_count_service.filtered(lambda l: l.register_type in promotion_id.register_type.mapped('code'))
                if order_line_ids + len(order_count_service) > item.total:
                    self._cr.commit()
                    raise Warning(_("%s has run out of numbers for registration" % item.product_category_id.name))
        pass_line = []
        order_line_temp = self.order_line
        if promotion_id.type == 'and':
            for line in self.order_line:
                if line in pass_line:
                    continue
                temp = []
                match = False
                # Danh dau da duyet qua trong cac dieu kien, True neu thoa dieu kien truoc, False neu chua duyet dieu kien hoac khong thoa dieu kien
                flag = False
                # Check condition Total Amount Sale Order
                if promotion_id.is_amount_order and promotion_id.period_total_amount_order > 0:
                    if self.amount_untaxed < promotion_id.period_total_amount_order:
                        return False, []
                    if line not in pass_line:
                        match = True
                        temp.append(line)
                # Check Order Type
                if promotion_id.is_order_type and promotion_id.order_type:
                    if self.type not in [t.code for t in promotion_id.order_type]:
                        return False, []
                    if line not in pass_line:
                        match = True
                        temp.append(line)
                # Check Customer Type
                if promotion_id.is_customer_type and promotion_id.customer_type:
                    if self.partner_id.company_type not in [t.code for t in promotion_id.customer_type]:
                        return False, []
                    if line not in pass_line:
                        match = True
                        temp.append(line)
                # Check Customer in List
                if promotion_id.is_list_customer and promotion_id.customer_ids:
                    if self.partner_id not in promotion_id.customer_ids:
                        return False, []
                    if line not in pass_line:
                        match = True
                        temp.append(line)
                # Check Customer Email
                if promotion_id.is_customer_email and promotion_id.customer_email:
                    if self.partner_id.email not in promotion_id.customer_email.mapped('email'):
                        return False, []
                    if line not in pass_line:
                        match = True
                        temp.append(line)
                # # Check Customer Level
                # if promotion_id.is_customer_level and promotion_id.customer_level:
                #     if self.partner_id.level not in [t.code for t in promotion_id.customer_level]:
                #         return False, []
                #     if line not in pass_line:
                #         match = True
                #         temp.append(line)
                # Check Register Type
                if promotion_id.is_register_type and promotion_id.register_type:
                    if line.register_type not in [t.code for t in promotion_id.register_type]:
                        continue
                    if line not in pass_line:
                        match = True
                        temp.append(line)
                # Check Count Product
                if promotion_id.is_count_product and promotion_id.count_product:
                    if promotion_id.is_register_type and promotion_id.register_type:
                        if promotion_id.product_category_type and promotion_id.promotion_product_category:
                            count_line = self.order_line.filtered(
                                lambda l: l.product_category_id in self.get_product_category(
                                    promotion_id.promotion_product_category) and l.register_type in
                                          [t.code for t in promotion_id.register_type])
                            if len(count_line) < promotion_id.count_product:
                                return False, []
                        if promotion_id.register_time_type and promotion_id.promotion_register_time:
                            count_line = 0
                            for li in promotion_id.promotion_register_time:
                                count_line += len(self.order_line.filtered(
                                    lambda l: l.product_category_id in self.get_product_category(li.product_category_id)
                                              and ((l.order_id.type == 'for_rent' and l.time >= li.month_from) or
                                                   (l.order_id.type == 'for_sale' and l.product_uom_qty >= li.month_from))))
                            if count_line < promotion_id.count_product:
                                return False, []
                        if promotion_id.is_amount_product and promotion_id.promotion_amount_product:
                            count_line = 0
                            for li in promotion_id.promotion_amount_product:
                                count_line += len(self.order_line.filtered(
                                    lambda l: l.product_category_id in self.get_product_category(li.product_category_id)
                                              and l.price_subtotal >= li.amount))
                            if count_line < promotion_id.count_product:
                                return False, []
                    if promotion_id.is_register_type and promotion_id.register_type and len(self.order_line.filtered(
                            lambda l: l.register_type in promotion_id.register_type.mapped(
                                    'code'))) < promotion_id.count_product:
                        return False, []
                    if len(self.order_line) < promotion_id.count_product:
                        return False, []
                    if line not in pass_line:
                        match = True
                        temp.append(line)
                # Check Product Category
                if promotion_id.product_category_type and promotion_id.promotion_product_category:
                    product_category_ids = self.get_product_category(promotion_id.promotion_product_category)
                    if line.product_category_id not in product_category_ids:
                        continue
                    if line not in temp:
                        temp.append(line)
                    match = True
                    flag = True
                    if promotion_id.product_category_type == 'and':
                        match, temp = self.check_product_category(promotion_id, temp, self.order_line.filtered(
                            lambda l: l not in pass_line))
                    if not match:
                        break
                # Check Register Time
                if promotion_id.register_time_type and promotion_id.promotion_register_time:
                    if line not in temp:
                        temp.append(line)
                    match, temp = self.check_register_time(promotion_id, temp, self.order_line.filtered(
                        lambda l: l not in pass_line), flag)
                    if not match:
                        continue
                    flag = True
                # Check Amount Product
                if promotion_id.is_amount_product and promotion_id.promotion_amount_product:
                    if line not in temp:
                        temp.append(line)
                    match, temp = self.check_amount_product(promotion_id, temp, self.order_line.filtered(
                        lambda l: l not in pass_line), flag)
                    if not match:
                        continue
                if match:
                    promotion_group.append(temp)
                    for item in temp:
                        order_line_temp -= item
                        if item not in pass_line:
                            pass_line.append(item)
        else:
            for line in self.order_line:
                if line in pass_line:
                    continue
                temp = [line]
                match = False
                # Check condition Total Amount Sale Order
                if promotion_id.is_amount_order and promotion_id.period_total_amount_order > 0:
                    if self.amount_untaxed >= promotion_id.period_total_amount_order:
                        promotion_group.append(temp)
                        for item in temp:
                            if item not in pass_line:
                                pass_line.append(item)
                        continue
                # Check Customer Type
                if promotion_id.is_customer_type and promotion_id.customer_type:
                    if self.partner_id.company_type in [t.code for t in promotion_id.customer_type]:
                        promotion_group.append(temp)
                        for item in temp:
                            if item not in pass_line:
                                pass_line.append(item)
                        continue
                # Check Order Type
                if promotion_id.is_order_type and promotion_id.order_type:
                    if self.type in [t.code for t in promotion_id.order_type]:
                        promotion_group.append(temp)
                        for item in temp:
                            if item not in pass_line:
                                pass_line.append(item)
                        continue
                # Check List Customer
                if promotion_id.is_list_customer and promotion_id.customer_ids:
                    if self.partner_id in promotion_id.customer_ids:
                        promotion_group.append(temp)
                        for item in temp:
                            if item not in pass_line:
                                pass_line.append(item)
                        continue
                # Check Customer Email
                if promotion_id.is_customer_email and promotion_id.customer_email:
                    if self.partner_id.email in promotion_id.customer_email.mapped('email'):
                        promotion_group.append(temp)
                        for item in temp:
                            if item not in pass_line:
                                pass_line.append(item)
                        continue
                # Check Customer Level
                # if promotion_id.is_customer_level and promotion_id.customer_level:
                #     if self.partner_id.level in [t.code for t in promotion_id.customer_level]:
                #         promotion_group.append(temp)
                #         for item in temp:
                #             if item not in pass_line:
                #                 pass_line.append(item)
                #         continue
                # Check Register Type
                if promotion_id.is_register_type and promotion_id.register_type:
                    if line.register_type in [t.code for t in promotion_id.register_type]:
                        promotion_group.append(temp)
                        for item in temp:
                            if item not in pass_line:
                                pass_line.append(item)
                        continue
                # Check Count Product
                if promotion_id.is_count_product and promotion_id.count_product:
                    if promotion_id.is_register_type and promotion_id.register_type and len(self.order_line.filtered(
                            lambda l: l.register_type in promotion_id.register_type.mapped(
                                    'code'))) >= promotion_id.count_product:
                        promotion_group.append(temp)
                        for item in temp:
                            if item not in pass_line:
                                pass_line.append(item)
                        continue
                    if len(self.order_line) >= promotion_id.count_product:
                        promotion_group.append(temp)
                        for item in temp:
                            if item not in pass_line:
                                pass_line.append(item)
                        continue
                # Check condition Product Category
                if promotion_id.product_category_type and promotion_id.promotion_product_category:
                    if line.product_category_id in self.get_product_category(promotion_id.promotion_product_category):
                        if promotion_id.product_category_type == 'or':
                            match = True
                            promotion_group.append(temp)
                            for item in temp:
                                order_line_temp -= item
                                if item not in pass_line:
                                    pass_line.append(item)
                            continue
                        if promotion_id.product_category_type == 'and':
                            match, temp = self.check_product_category(promotion_id, temp, self.order_line.filtered(
                                lambda l: l not in pass_line))
                            if match:
                                promotion_group.append(temp)
                                for item in temp:
                                    order_line_temp -= item
                                    if item not in pass_line:
                                        pass_line.append(item)
                                continue
                # Check condition Register Time
                if promotion_id.register_time_type and promotion_id.promotion_register_time:
                    match, temp = self.check_register_time(promotion_id, temp, self.order_line.filtered(
                        lambda l: l not in pass_line))
                    if match:
                        promotion_group.append(temp)
                        for item in temp:
                            order_line_temp -= item
                            if item not in pass_line:
                                pass_line.append(item)
                        continue
                # Check Amount Product Category
                if promotion_id.is_amount_product and promotion_id.promotion_amount_product:
                    match, temp = self.check_amount_product(promotion_id, temp, self.order_line.filtered(
                        lambda l: l not in pass_line))
                    if match:
                        promotion_group.append(temp)
                        for item in temp:
                            order_line_temp -= item
                            if item not in pass_line:
                                pass_line.append(item)
                        continue
        return len(promotion_group) > 0 and True or False, promotion_group

    @api.multi
    def check_product_category(self, promotion_id, temp, order_line):
        """Kiem tra danh sach dieu kien Product Category.
        1. Kiem tra ngoai danh sach da lay ra duoc, con goi nao trong promotion ma chua lay. Neu da het thi tra ve thoa
        dieu kien: True, danh sach dang co.
        2. Neu dk 1 khong thoa, kiem tra voi danh sach category con lai, lay category tiep theo category_ids[0],
        trong don hang co dich vu nao thoa dieu kien khong, neu khong co thi tra ve False (khong thoa dieu kien),
        neu co thi de quy tiep tuc voi category tiep theo"""
        get_category = temp and [l.product_category_id for l in temp] or []
        category_ids = promotion_id.promotion_product_category.filtered(
            lambda c: not any(item in self.get_product_category(c) for item in get_category))
        if not category_ids:
            return True, temp
        if not any(l.product_category_id in self.get_product_category(category_ids[0]) for l in order_line):
            return False, temp
        aaa = order_line.filtered(lambda line: line.product_category_id in self.get_product_category(category_ids[0]))
        temp.append(aaa[0])
        return self.check_product_category(promotion_id, temp, order_line.filtered(lambda l: l not in temp))

    @api.multi
    def check_register_time(self, promotion_id, temp, order_line, flag=False):
        """Kiem tra danh sach dieu kien Register Time"""
        if promotion_id.register_time_type == 'or':
            if promotion_id.type == 'or':
                for item in temp:
                    if any(item.product_category_id in self.get_product_category(line.product_category_id)
                           and ((item.order_id.type == 'for_rent' and item.time >= line.month_from) or
                                (item.order_id.type == 'for_sale' and item.product_uom_qty >= line.month_from))
                           for line in promotion_id.promotion_register_time):
                        return True, temp
                return False, temp
            if promotion_id.type == 'and':
                if len(temp) == 1 and not flag:
                    if any(temp[0].product_category_id in self.get_product_category(line.product_category_id)
                           and ((temp[0].order_id.type == 'for_rent' and temp[0].time >= line.month_from) or
                                (temp[0].order_id.type == 'for_sale' and temp[0].product_uom_qty >= line.month_from))
                           for line in promotion_id.promotion_register_time):
                        return True, temp
                    return False, temp
                else:
                    for line in promotion_id.promotion_register_time:
                        if any(l.product_category_id in self.get_product_category(line.product_category_id) and
                               ((l.order_id.type == 'for_rent' and l.time >= line.month_from) or
                                (l.order_id.type == 'for_sale' and l.product_uom_qty >= line.month_from)) for l in temp):
                            return True, temp
                        if any(l.product_category_id in self.get_product_category(line.product_category_id) and
                               ((l.order_id.type == 'for_rent' and l.time < line.month_from) or
                                (l.order_id.type == 'for_sale' and l.product_uom_qty < line.month_from)) for l in temp):
                            continue
                        if not any(l.product_category_id in self.get_product_category(line.product_category_id) and
                                   ((l.order_id.type == 'for_rent' and l.time >= line.month_from) or
                                    (l.order_id.type == 'for_sale' and l.product_uom_qty >= line.month_from))
                                   for l in order_line.filtered(lambda o: o not in temp)):
                            if line == promotion_id.promotion_register_time[-1]:
                                return False, temp
                            else:
                                continue
                        aaa = order_line.filtered(lambda l: l.product_category_id in self.get_product_category(
                            line.product_category_id) and
                            ((l.order_id.type == 'for_rent' and l.time >= line.month_from) or
                             (l.order_id.type == 'for_sale' and l.product_uom_qty >= line.month_from)))
                        temp.append(aaa[0])
                        return True, temp
        else:
            if not flag:
                for item in temp:
                    if item.product_category_id not in self.get_product_category(
                            promotion_id.promotion_register_time.mapped('product_category_id')) \
                        or not any(item.product_category_id in self.get_product_category(line.product_category_id)
                                   and ((item.order_id.type == 'for_rent' and item.time >= line.month_from) or
                                        (item.order_id.type == 'for_sale' and item.product_uom_qty >= line.month_from))
                                   for line in promotion_id.promotion_register_time):
                        return False, temp
            for line in promotion_id.promotion_register_time:
                if any(l.product_category_id in self.get_product_category(line.product_category_id) and
                       ((l.order_id.type == 'for_rent' and l.time >= line.month_from) or
                        (l.order_id.type == 'for_sale' and l.product_uom_qty >= line.month_from)) for l in temp):
                    continue
                if any(l.product_category_id in self.get_product_category(line.product_category_id) and
                       ((l.order_id.type == 'for_rent' and l.time < line.month_from) or
                        (l.order_id.type == 'for_sale' and l.product_uom_qty < line.month_from)) for l in temp):
                    return False, temp
                if not any(l.product_category_id in self.get_product_category(line.product_category_id) and 
                           ((l.order_id.type == 'for_rent' and l.time >= line.month_from) or
                            (l.order_id.type == 'for_sale' and l.product_uom_qty >= line.month_from))
                           for l in order_line.filtered(lambda o: o not in temp)):
                    return False, temp
                aaa = order_line.filtered(
                    lambda l: l.product_category_id in self.get_product_category(line.product_category_id) and
                              ((l.order_id.type == 'for_rent' and l.time >= line.month_from) or
                               (l.order_id.type == 'for_sale' and l.product_uom_qty >= line.month_from)))
                temp.append(aaa[0])
            return True, temp

    @api.multi
    def check_amount_product(self, promotion_id, temp, order_line, flag=False):
        """Kiem tra danh sach dieu kien Register Time"""
        if promotion_id.amount_product_type == 'or':
            if promotion_id.type == 'or':
                for item in temp:
                    if any(item.product_category_id in self.get_product_category(line.product_category_id) and
                           item.price_subtotal >= line.amount for line in promotion_id.promotion_amount_product):
                        return True, temp
                return False, temp
            if promotion_id.type == 'and':
                if len(temp) == 1 and not flag:
                    if any(temp[0].product_category_id in self.get_product_category(line.product_category_id) and
                           temp[0].price_subtotal >= line.amount for line in promotion_id.promotion_amount_product):
                        return True, temp
                    return False, temp
                else:
                    for line in promotion_id.promotion_amount_product:
                        if any(l.product_category_id in self.get_product_category(line.product_category_id) and
                               l.price_subtotal >= line.amount for l in temp):
                            return True, temp
                        if any(l.product_category_id in self.get_product_category(line.product_category_id) and
                               l.price_subtotal < line.amount for l in temp):
                            continue
                        if not any(l.product_category_id in self.get_product_category(line.product_category_id) and
                                   l.price_subtotal >= line.amount for l in order_line.filtered(lambda o: o not in temp)):
                            if line == promotion_id.promotion_amount_product[-1]:
                                return False, temp
                            else:
                                continue
                        aaa = order_line.filtered(lambda l: l.product_category_id in self.get_product_category(
                            line.product_category_id) and l.price_subtotal >= line.amount)
                        temp.append(aaa[0])
                        return True, temp
        else:
            if not flag:
                for item in temp:
                    if item.product_category_id not in self.get_product_category(promotion_id.promotion_amount_product.mapped('product_category_id')) \
                            or not any(item.product_category_id in self.get_product_category(line.product_category_id)
                                       and item.price_subtotal >= line.amount for line in promotion_id.promotion_amount_product):
                        return False, temp
            for line in promotion_id.promotion_amount_product:
                if any(l.product_category_id in self.get_product_category(line.product_category_id) and
                       l.price_subtotal >= line.amount for l in temp):
                    continue
                if any(l.product_category_id in self.get_product_category(line.product_category_id) and
                       l.price_subtotal < line.amount for l in temp):
                    return False, temp
                if not any(l.product_category_id in self.get_product_category(line.product_category_id) and
                           l.price_subtotal >= line.amount for l in order_line.filtered(lambda o: o not in temp)):
                    return False, temp
                aaa = order_line.filtered(lambda l: l.product_category_id == line.product_category_id and
                                                          l.price_subtotal >= line.amount)
                temp.append(aaa[0])
            return True, temp

    @api.multi
    def discount_analytic(self, arr, count):
        if not arr:
            return {}
        rsl = {}
        for item in arr:
            rsl.update({item: count})
        return rsl

    @api.multi
    def check_condition_discount(self, promotion_id, line):
        if promotion_id.type == 'and':
            if promotion_id.register_time_type and promotion_id.promotion_register_time:
                if line.product_category_id in self.get_product_category(
                        promotion_id.promotion_register_time.mapped('product_category_id')):
                    for item in promotion_id.promotion_register_time:
                        if line.product_category_id in self.get_product_category(
                                item.product_category_id) and \
                                ((line.order_id.type == 'for_rent' and line.time < item.month_from) or
                                 (line.order_id.type == 'for_sale' and line.product_uom_qty < item.month_from)):
                            return False
            if promotion_id.is_amount_product and promotion_id.promotion_amount_product:
                if line.product_category_id in self.get_product_category(
                        promotion_id.promotion_amount_product.mapped('product_category_id')):
                    for item in promotion_id.promotion_amount_product:
                        if line.product_category_id in self.get_product_category(
                                item.product_category_id) and line.price_subtotal < item.amount:
                            return False
        return True

    @api.multi
    def update_price_by_odoo(self):
        self.write({'coupon': self.coupon})
        rsl, arr, coupon_id, count_used_time, count_product, count_money, count_percent = False, [], False, 0, 0, 0, 0
        product_dict, used_time_dict, money_dict, percent_dict = {}, {}, {}, {}
        for line in self.order_line:
            line.get_price_order()
        if self.coupon:
            coupon_id = self.env['mb.coupon'].search([('name', '=', self.coupon.strip())])
            rsl, arr = self.check_promotion_condition()
            count_used_time, count_product, count_money, count_percent = len(arr), len(arr), len(arr), len(arr)
            if coupon_id.promotion_id.discount_used_time and coupon_id.promotion_id.is_discount_used_time:
                used_time_dict = self.discount_analytic(
                    coupon_id.promotion_id.mapped('discount_used_time').mapped('product_category_id'), count_used_time)
            if coupon_id.promotion_id.promotion_discount_money and coupon_id.promotion_id.is_discount_money:
                money_dict = self.discount_analytic(
                    coupon_id.promotion_id.mapped('promotion_discount_money').mapped('product_category_id'),
                    count_money)
            if coupon_id.promotion_id.is_discount_percent and coupon_id.promotion_id.promotion_discount_percent:
                percent_dict = self.discount_analytic(
                    coupon_id.promotion_id.mapped('promotion_discount_percent').mapped('product_category_id'),
                    count_percent)
            if coupon_id.promotion_id.promotion_discount_product and coupon_id.promotion_id.is_discount_product:
                product_dict = self.discount_analytic(
                    coupon_id.promotion_id.mapped('promotion_discount_product').mapped('product_category_id'),
                    count_product)
            tmp = []
            for x in arr:
                tmp += x
            arr = tmp
        for line in self.order_line:
            renew_before_refund = line.renew_price + line.refund_amount
            if self.coupon:
                if rsl and arr:
                    if coupon_id.promotion_id.promotion_discount_money and coupon_id.promotion_id.is_discount_money:
                        discount = coupon_id.promotion_id.promotion_discount_money.filtered(
                            lambda l: line.product_category_id in self.get_product_category(l.product_category_id))
                        if discount:
                            if line in arr:
                                if line.order_id.type == 'for_rent':
                                    line.write({
                                        'register_price': line.register_price - (discount[0].setup_amount or 0),
                                        'renew_price': line.renew_price - (discount[0].renew_amount or 0),
                                        'promotion_discount': (discount[0].setup_amount or 0) +
                                                              (discount[0].renew_amount or 0)
                                    })
                                else:
                                    line.write({
                                        'price_unit': line.price_unit - (discount[0].setup_amount or 0),
                                        'promotion_discount': (discount[0].setup_amount or 0)
                                    })
                            else:
                                key, value = False, 0
                                for item in money_dict:
                                    if line.product_category_id not in self.get_product_category(item):
                                        continue
                                    key = item
                                    value = money_dict[key]
                                    break
                                if value > 0 and line.product_category_id in \
                                    self.get_product_category(
                                        coupon_id.promotion_id.promotion_discount_money.mapped('product_category_id')) \
                                    and line.product_category_id not in [c.product_category_id for c in arr]:
                                    if self.check_condition_discount(coupon_id.promotion_id, line):
                                        if line.order_id.type == 'for_rent':
                                            line.write({
                                                'register_price': line.register_price - (discount[0].setup_amount or 0),
                                                'renew_price': line.renew_price - (discount[0].renew_amount or 0),
                                                'promotion_discount': (discount[0].setup_amount or 0) +
                                                                      (discount[0].renew_amount or 0)
                                            })
                                        else:
                                            line.write({
                                                'price_unit': line.price_unit - (discount[0].setup_amount or 0),
                                                'promotion_discount': (discount[0].setup_amount or 0)
                                            })
                                        money_dict[key] -= 1
                    if coupon_id.promotion_id.is_discount_percent and coupon_id.promotion_id.promotion_discount_percent:
                        discount = coupon_id.promotion_id.promotion_discount_percent.filtered(
                            lambda l: line.product_category_id in self.get_product_category(l.product_category_id))
                        if discount:
                            if line in arr:
                                if line.order_id.type == 'for_rent':
                                    line.write({
                                        'register_price': line.register_price - line.register_price *
                                                                (discount[0].setup_percent or 0) / 100,
                                        'renew_price': line.renew_price - renew_before_refund *
                                                             (discount[0].renew_percent or 0) / 100,
                                        'promotion_discount': line.register_price *
                                                              (discount[0].setup_percent or 0) / 100 +
                                                              renew_before_refund * (discount[0].renew_percent or 0) / 100
                                    })
                                else:
                                    line.write({
                                        'price_unit': line.price_unit - line.price_unit *
                                                                (discount[0].setup_percent or 0) / 100,
                                        'promotion_discount': line.price_unit * (discount[0].setup_percent or 0) / 100
                                    })
                            else:
                                key, value = False, 0
                                for item in percent_dict:
                                    if line.product_category_id not in self.get_product_category(item):
                                        continue
                                    key = item
                                    value = percent_dict[key]
                                    break
                                if value > 0 and line.product_category_id in \
                                        self.get_product_category(
                                            coupon_id.promotion_id.promotion_discount_percent.mapped(
                                                'product_category_id')) \
                                        and line.product_category_id not in [c.product_category_id for c in arr]:
                                    if self.check_condition_discount(coupon_id.promotion_id, line):
                                        if line.order_id.type == 'for_rent':
                                            line.write({
                                                'register_price': line.register_price - line.register_price *
                                                                        (discount[0].setup_percent or 0) / 100,
                                                'renew_price': line.renew_price - line.renew_price *
                                                                     (discount[0].renew_percent or 0) / 100,
                                                'promotion_discount': line.register_price *
                                                                      (discount[0].setup_percent or 0) / 100 +
                                                                      line.renew_price *
                                                                      (discount[0].renew_percent or 0) / 100
                                            })
                                        else:
                                            line.write({
                                                'price_unit': line.price_unit - line.price_unit *
                                                                        (discount[0].setup_percent or 0) / 100,
                                                'promotion_discount': line.price_unit *
                                                                      (discount[0].setup_percent or 0) / 100
                                            })
                                        percent_dict[key] -= 1
                    if coupon_id.promotion_id.discount_used_time and coupon_id.promotion_id.is_discount_used_time:
                        discount = coupon_id.promotion_id.discount_used_time.filtered(
                            lambda l: line.product_category_id in self.get_product_category(l.product_category_id))
                        if discount:
                            if line in arr:
                                if line.order_id.type == 'for_rent':
                                    line.write({
                                        'time': (line.original_time or line.time) + discount.time,
                                        'promotion_discount': discount.time * line.product_category_id.renew_price
                                    })
                                else:
                                    line.write({
                                        'product_uom_qty': (line.original_time or line.product_uom_qty) + discount.time,
                                        'promotion_discount': discount.time * line.product_id.list_price
                                    })
                            else:
                                key, value = False, 0
                                for item in used_time_dict:
                                    if line.product_category_id not in self.get_product_category(item):
                                        continue
                                    key = item
                                    value = used_time_dict[key]
                                    break
                                if value > 0 and line.product_category_id in \
                                        self.get_product_category(
                                            coupon_id.promotion_id.discount_used_time.mapped('product_category_id')) \
                                        and line.product_category_id not in [c.product_category_id for c in arr]:
                                    if self.check_condition_discount(coupon_id.promotion_id, line):
                                        if line.order_id.type == 'for_rent':
                                            line.write({
                                                'time': (line.original_time or line.time) + discount.time,
                                                'promotion_discount': discount.time * line.product_category_id.renew_price
                                            })
                                        else:
                                            line.write({
                                                'product_uom_qty': (line.original_time or line.product_uom_qty) + discount.time,
                                                'promotion_discount': discount.time * line.product_id.list_price
                                            })
                                        used_time_dict[key] -= 1
                    if coupon_id.promotion_id.promotion_discount_product and coupon_id.promotion_id.is_discount_product:
                        discount = coupon_id.promotion_id.promotion_discount_product.filtered(
                            lambda l: line.product_category_id in self.get_product_category(l.product_category_id))
                        if discount:
                            if line in arr:
                                total = line.get_total_by_time(discount[0].time) * \
                                                (discount[0].percent and discount[0].percent / 100 or 1)
                                if line.order_id.type == 'for_rent':
                                    line.write({
                                            'renew_price': (line.renew_price - total > 0) and line.renew_price - total or 0,
                                            'promotion_discount': (line.promotion_discount + total < line.price_subtotal_no_discount)
                                                                  and line.promotion_discount + total or line.price_subtotal_no_discount
                                        })
                                else:
                                    line.write({
                                            'promotion_discount': (line.promotion_discount + total < line.price_subtotal_no_discount)
                                                                  and line.promotion_discount + total or line.price_subtotal_no_discount
                                        })
                            else:
                                key, value = False, 0
                                for item in product_dict:
                                    if line.product_category_id not in self.get_product_category(item):
                                        continue
                                    key = item
                                    value = product_dict[key]
                                    break
                                if value > 0 and line.product_category_id in \
                                        self.get_product_category(
                                            coupon_id.promotion_id.promotion_discount_product.mapped('product_category_id')) \
                                        and line.product_category_id not in [c.product_category_id for c in arr]:
                                    if self.check_condition_discount(coupon_id.promotion_id, line):
                                        total = line.get_total_by_time(discount[0].time) * \
                                                (discount[0].percent and discount[0].percent / 100 or 1)
                                        if line.order_id.type == 'for_rent':
                                            line.write({
                                                'renew_price': (line.renew_price - total > 0) and
                                                                     line.renew_price - total or 0,
                                                'promotion_discount': (line.promotion_discount + total < line.price_subtotal_no_discount) and
                                                                      line.promotion_discount + total or line.price_subtotal_no_discount
                                            })
                                        else:
                                            line.write({
                                                'promotion_discount': (line.promotion_discount + total < line.price_subtotal_no_discount) and
                                                                      line.promotion_discount + total or line.price_subtotal_no_discount
                                            })
                                        product_dict[key] -= 1

    @api.multi
    def update_coupon_and_update_price(self, coupon):
        logging.info("***************** %s, %s **************", self, coupon)
        if not coupon:
            raise Warning(_("Pls input coupon."))
        self.write({'coupon': coupon})

    @api.model
    def update_order_wo_line(self, order_name, params={}):
        SaleOrder = self.env['sale.order']
        Partner = self.env['res.partner']
        if not order_name:
            return {'"code"': 0, '"msg"': '"Order Name could not be empty"'}
        order_id = SaleOrder.search([('name', '=', order_name)])
        if not order_id:
            return {'"code"': 0, '"msg"': '"Order not exists"'}
        if len(order_id) > 1:
            return {'"code"': 0, '"msg"': '"Many Orders."'}
        if order_id.state not in ('not_received', 'draft', 'sale'):
            return {'"msg"': '"Order status must be in Not Assign, Quotation, Processing"', '"code"': 0}
        if 'partner_id' not in params:
            return {'"code"': 0, '"msg"': '"Customer could not be empty"'}
        partner_id = Partner.search([('ref', '=', params.get('partner_id'))])
        if not partner_id:
            return {'"code"': 0, '"msg"': '"Partner not exists"'}
        if len(partner_id) > 1:
            return {'"code"': 0, '"msg"': '"Many Partner."'}
        params.update({
            'partner_id': partner_id.id,
            'company_id': partner_id.company_id.id
        })
        try:
            order_id.write(params)
            order_id.update_price_by_odoo()
            return {'"msg"': '"Update Order Successfully"', '"code"': 1, '"data"': '"%s"' % order_id.name}
        except Exception as e:
            self._cr.rollback()
            return {'"code"': 0,
                    '"msg"': '"Can`t update order line for SO %s: %s"' % (order_name, e.message or repr(e))}


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    promotion_discount = fields.Float("Discount")
    price_subtotal_no_discount = fields.Float('Total No Discount', compute='get_price_subtotal_no_discount', store=True)
    original_time = fields.Float("Original Time")
    price_new_category = fields.Float("Price New Category (Untaxed)")
    refund_amount = fields.Float("Refund Amount (Untaxed)")

    @api.depends('register_price', 'renew_price', 'up_price', 'promotion_discount')
    def get_price_subtotal_no_discount(self):
        for line in self:
            line.price_subtotal_no_discount = line.register_price + line.renew_price + \
                                              line.up_price + line.promotion_discount

    @api.multi
    def get_setup_price_renew_price(self):
        if self.order_id.type == 'for_rent':
            if self.order_id.partner_id.customer_type != 'agency':
                setup_price = self.product_category_id.setup_price
                renew_price = self.product_category_id.renew_price
            else:
                # setup_price = 0
                # renew_price = 0
                price = self.env['product.agency.price'].search(
                    [('categ_id', '=', self.product_category_id.id),
                     ('level_id', '=', self.order_id.partner_id.agency_level)],
                    order='id desc', limit=1)
                if price:
                    setup_price = price.setup_price
                    renew_price = price.renew_price
                else:
                    setup_price = self.product_category_id.setup_price
                    renew_price = self.product_category_id.renew_price
            return setup_price, renew_price
        else:
            return self.product_id.list_price, 0

    @api.multi
    def get_time_order_line(self):
        used_time = 0
        if self.order_id.billing_type == 'prepaid':
            time = (self.original_time or self.time)
        else:
            time = 1
            if self.register_type == 'renew':
                # categ = self.env['product.category'].search([('code', '=', 'License-P')])
                # license_categ_ids = False
                # if categ:
                #     license_categ_ids = self.env['product.category'].search([('id', 'child_of', categ.id)])
                order_date = datetime.strptime(self.order_id.date_order, '%Y-%m-%d %H:%M:%S').date().replace(day=1)
                service_id = self.env['sale.service'].search([('product_id', '=', self.product_id.id)], limit=1)
                if not service_id:
                    raise Warning(_("Service of product %s not found." % self.product_id.display_name))
                service_date = datetime.strptime(service_id.start_date, '%Y-%m-%d').date()
                # if self.product_category_id not in license_categ_ids:
                if order_date.year > service_date.year:
                    if service_id.end_date and datetime.now().date().strftime('%Y-%m-01') > service_id.end_date:
                        if datetime.strptime(service_id.end_date, '%Y-%m-%d').month == service_date.month and \
                                datetime.strptime(service_id.end_date, '%Y-%m-%d').year == service_date.year:
                            used_time = (datetime.strptime(service_id.end_date, '%Y-%m-%d').date() - service_date).days
                        else:
                            used_time = datetime.strptime(service_id.end_date, '%Y-%m-%d').day
                    elif (order_date - relativedelta(months=1)).month == service_date.month and \
                            (order_date - relativedelta(years=1)).year == service_date.year and \
                                    service_date.month == 12:
                        used_time = (order_date - service_date).days
                        logging.info("1111111111111, %s, %s, %s, %s", self.product_category_id.name, order_date, service_date, used_time)
                else:
                    if service_id.end_date and datetime.now().date().strftime('%Y-%m-01') > service_id.end_date:
                        if datetime.strptime(service_id.end_date, '%Y-%m-%d').month == service_date.month and \
                                datetime.strptime(service_id.end_date, '%Y-%m-%d').year == service_date.year:
                            used_time = (datetime.strptime(service_id.end_date, '%Y-%m-%d').date() - service_date).days
                        else:
                            used_time = datetime.strptime(service_id.end_date, '%Y-%m-%d').day
                    elif service_date.month < (datetime.now() - relativedelta(months=1)).month:
                        used_time = 0
                    elif service_date.month == (datetime.now() - relativedelta(months=1)).month:
                        used_time = (datetime.now().date().replace(day=1) - service_date).days
                # else:
                #     used_time = 0
                #     if service_id.end_date:
                #         end_date = datetime.strptime(service_id.end_date, '%Y-%m-%d').date()
                #         if end_date.day < service_date.day:
                #             time = 0
        logging.info("bbbbbbbbbbbbbb %s, %s", time, used_time)
        return time, used_time

    @api.multi
    def get_price_order(self):
        if self.product_category_id:
            tax_number = is_number(self.product_category_id.default_tax)
            tax = self.env['account.tax'].search([('type_tax_use', '=', 'sale'),
                                                  ('amount', '=', tax_number and
                                                   int(self.product_category_id.default_tax) or -1),
                                                  ('company_id', '=', self.order_id.company_id.id)], limit=1)
            if self.order_id.type == 'for_rent':
                setup_price, renew_price = self.get_setup_price_renew_price()
                # print 'price', setup_price, renew_price
                time, used_time = self.get_time_order_line()
                # print 'time', time, used_time
                if self.register_type == 'register':
                    self.write({
                        'register_price': setup_price,
                        'renew_price': 0 if self.order_id.billing_type == 'postpaid'
                                         else time * renew_price * (self.license or 1),
                        'tax_id': [(6, 0, tax.ids)],
                        'price_updated': True,
                        'promotion_discount': 0
                    })
                elif self.register_type == 'renew':
                    # if self.order_id.billing_type == 'prepaid':
                    price = time * renew_price * (self.license or 1)
                    # else:
                    #     if used_time == 0:
                    #         price = time * renew_price * (self.license or 1)
                    #     else:
                    #         last_month = datetime.now() + relativedelta(months=-1)
                    #         nom = calendar.monthrange(last_month.year, last_month.month)[1]
                    #         # print nom,
                    #         price = used_time * renew_price / nom * (self.license or 1)
                    self.write({
                        # 'register_price': setup_price,
                        'register_price': 0,
                        'renew_price': long(price),
                        'tax_id': [(6, 0, tax.ids)],
                        'price_updated': True,
                        'promotion_discount': 0
                    })
                elif self.register_type == 'upgrade':
                    if self.order_id.billing_type == 'prepaid':
                        price = time * renew_price * (self.license or 1) - (self.refund_amount or 0)
                    else:
                        if used_time == 0:
                            price = time * renew_price * (self.license or 1) - (self.refund_amount or 0)
                        else:
                            last_month = datetime.now() + relativedelta(months=-1)
                            nom = calendar.monthrange(last_month.year, last_month.month)[1]
                            price = used_time * renew_price / nom * (self.license or 1) - (self.refund_amount or 0)
                    self.write({
                        'register_price': setup_price,
                        'renew_price': long(price),
                        'tax_id': [(6, 0, tax.ids)],
                        'price_updated': True,
                        'promotion_discount': 0
                    })
            else:
                self.write({
                    'price_unit': self.product_id.list_price,
                    'tax_id': [(6, 0, tax.ids)],
                    'price_updated': True,
                    'promotion_discount': 0
                })

    @api.multi
    def get_total_by_time(self, time):
        total = 0
        if self.order_id.type == 'for_rent':
            if self.product_category_id:
                setup_price, renew_price = self.get_setup_price_renew_price()
                total = time * renew_price
        else:
            total = time * self.product_id.list_price
        return total

    @api.model
    def create(self, vals):
        if vals.get('time') != vals.get('original_time'):
            vals['original_time'] = vals.get('time')
        return super(SaleOrderLine, self).create(vals)

    @api.model
    def create_new_line(self, order_id, line=[]):
        try:
            order = self.env['sale.order'].browse(order_id)
            order_lines = self.env['external.so'].with_context(
                force_company=order.partner_id.company_id.id).create_order_lines(line)
            if order_lines:
                cur_lines = order.order_line
                order.write({
                    'order_line': order_lines['line_ids']
                })
                line_id = order.order_line - cur_lines
                order.update_price_by_odoo()
                data = {
                    '"id"': line_id and line_id.id or 0,
                    '"price_subtotal"': line_id and line_id.price_subtotal_no_discount or 0,
                    '"amount_untaxed"': line_id and line_id.order_id.amount_untaxed or 0,
                    '"amount_tax"': line_id and line_id.order_id.amount_tax or 0,
                    '"amount_total"': line_id and line_id.order_id.amount_total or 0,
                }
                return {'"code"': 1, '"msg"': '"Create new line completed"', '"data"': data}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}

    @api.model
    def update_line(self, line_id, vals=[]):
        try:
            line = self.env['sale.order.line'].browse(line_id)
            order_lines = self.env['external.so'].with_context(
                force_company=line.order_id.partner_id.company_id.id).create_order_lines(vals)
            if order_lines['msg']:
                return {'"code"': 0, '"msg"': order_lines['msg']}
            if order_lines:
                line_vals = list(order_lines['line_ids'][0])
                line.write(line_vals[2])
                line.order_id.update_price_by_odoo()
                data = {
                    '"price_subtotal"': line and line.price_subtotal_no_discount or 0,
                    '"amount_untaxed"': line.order_id.amount_untaxed or 0,
                    '"amount_tax"': line.order_id.amount_tax or 0,
                    '"amount_total"': line.order_id.amount_total or 0,
                }
                return {'"code"': 1, '"msg"': '"Update completed"', '"data"': data}
            return {'"code"': 0, '"msg"': '"Can not get lines"'}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}

    @api.model
    def delete_line(self, line_id):
        try:
            line = self.env['sale.order.line'].browse(line_id)
            order_id = line.order_id
            line.unlink()
            order_id.update_price_by_odoo()
            data = {
                '"amount_untaxed"': order_id.amount_untaxed or 0,
                '"amount_tax"': order_id.amount_tax or 0,
                '"amount_total"': order_id.amount_total or 0,
            }
            return {'"code"': 1, '"msg"': '"Deleted completed"', '"data"': data}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}