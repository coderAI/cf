# -*- coding: utf-8 -*-
from odoo import api, fields, models
# import time
# from datetime import datetime, timedelta
# from dateutil import relativedelta
import logging

class ProductCategory(models.Model):
    _inherit = "product.category"

    default_tax = fields.Char("Default Tax", default='10')

    @api.model
    def get_category_info(self, category_code=''):
        if category_code:
            category_ids = self.search([('code', '=', category_code)])
        else:
            category_ids = self.search([])
        if not category_ids:
            return {'"code"': 0, '"msg"': '"No data"'}
        try:
            data = []
            for category in category_ids:
                data.append({
                    '"name"': '"%s"' % (category.name or ''),
                    '"code"': '"%s"' % (category.code or ''),
                    '"uom"': '"%s"' % (category.uom_id and category.uom_id.name or ''),
                    '"setup_price"': category.setup_price or 0,
                    '"renew_price"': category.renew_price or 0,
                    '"default_tax"': category.default_tax and int(category.default_tax) or -1,
                    '"promotion_register_price"': category.promotion_register_price or 0,
                    '"promotion_renew_price"': category.promotion_renew_price or 0,
                })
            return {'"code"': 1, '"msg"': '"Successfully"', '"data"': data}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}

    @api.model
    def get_coupon_as_category(self, type='', category_code=''):
        import logging
        try:
            cr = self._cr
            domain = """"""
            if type:
                if type == 'DM':
                    cr.execute("""select id from product_category where left(code) = '.'""")
                else:
                    cr.execute("""select id from product_category where left(code) <> '.'""")
                categ_ids = cr.dictfetchall()
                categ_ids = categ_ids and [item['id'] for item in categ_ids] or []
                if categ_ids:
                    domain += """AND pc.id in %s """ % (tuple(categ_ids))
            if category_code:
                categ_id = self.search([('code', '=', category_code)], limit=1)
                if categ_id:
                    categ_ids = self.search([('id', 'child_of', categ_id.id)])
                    categ_ids = [c.id for c in categ_ids]
                    logging.info("========= %s, %s =========", categ_ids, tuple(categ_ids))
                    if categ_ids:
                        if len(categ_ids) > 1:
                            domain += """AND pc.id IN %s """ % (tuple(categ_ids))
                        else:
                            domain += """AND pc.id = %s """ % categ_ids[0]
            logging.info("========= %s =========", domain)
            cr.execute("""SELECT pc.id, pc.code, string_agg(mc.name, ', ') AS coupon
                          FROM product_category pc
                            JOIN promotion_product_category ppc ON ppc.product_category_id = pc.id
                            JOIN mb_promotion mp ON mp.id = ppc.promotion_id
                            JOIN mb_coupon mc ON mc.promotion_id = mp.id
                          WHERE now() <= mc.expired_date + '7 hour'::interval
                              AND (mp.date_from + '7 hour'::interval) <= now()
                              AND (mp.date_to + '7 hour'::interval) >= now()
                              AND mp.status = 'run'
                              %s
                          GROUP BY pc.id, pc.code
                          UNION ALL
                          SELECT pc.id, pc.code, string_agg(mc.name, ', ') AS coupon
                          FROM product_category pc
                            JOIN promotion_register_time prt ON prt.product_category_id = pc.id
                            JOIN mb_promotion mp ON mp.id = prt.promotion_id
                            JOIN mb_coupon mc ON mc.promotion_id = mp.id
                          WHERE now() <= mc.expired_date + '7 hour'::interval
                              AND (mp.date_from + '7 hour'::interval) <= now()
                              AND (mp.date_to + '7 hour'::interval) >= now()
                              AND mp.status = 'run'
                              %s
                          GROUP BY pc.id, pc.code
                          UNION ALL
                          SELECT pc.id, pc.code, string_agg(mc.name, ', ') AS coupon
                          FROM product_category pc
                            JOIN promotion_amount_product pap ON pap.product_category_id = pc.id
                            JOIN mb_promotion mp ON mp.id = pap.promotion_id
                            JOIN mb_coupon mc ON mc.promotion_id = mp.id
                          WHERE now() <= mc.expired_date + '7 hour'::interval
                              AND (mp.date_from + '7 hour'::interval) <= now()
                              AND (mp.date_to + '7 hour'::interval) >= now()
                              AND mp.status = 'run'
                              %s
                          GROUP BY pc.id, pc.code
                          UNION ALL
                          SELECT pc.id, pc.code, string_agg(mc.name, ', ') AS coupon
                          FROM product_category pc
                            JOIN promotion_total_product_discount ptpd ON ptpd.product_category_id = pc.id
                            JOIN mb_promotion mp ON mp.id = ptpd.promotion_id
                            JOIN mb_coupon mc ON mc.promotion_id = mp.id
                          WHERE now() <= mc.expired_date + '7 hour'::interval
                              AND (mp.date_from + '7 hour'::interval) <= now()
                              AND (mp.date_to + '7 hour'::interval) >= now()
                              AND mp.status = 'run'
                              %s
                          GROUP BY pc.id, pc.code
--                           UNION ALL
--                           SELECT pc.id, pc.code, string_agg(mc.name, ', ') AS coupon
--                           FROM product_category pc
--                             JOIN promotion_discount_money pdm ON pdm.product_category_id = pc.id
--                             JOIN mb_promotion mp ON mp.id = pdm.promotion_id
--                             JOIN mb_coupon mc ON mc.promotion_id = mp.id
--                           WHERE now() <= mc.expired_date + '7 hour'::interval
--                               AND (mp.date_from + '7 hour'::interval) <= now()
--                               AND (mp.date_to + '7 hour'::interval) >= now()
--                               AND mp.status = 'run'
--                               
--                           GROUP BY pc.id, pc.code
--                           UNION ALL
--                           SELECT pc.id, pc.code, string_agg(mc.name, ', ') AS coupon
--                           FROM product_category pc
--                             JOIN promotion_discount_percent pdp ON pdp.product_category_id = pc.id
--                             JOIN mb_promotion mp ON mp.id = pdp.promotion_id
--                             JOIN mb_coupon mc ON mc.promotion_id = mp.id
--                           WHERE now() <= mc.expired_date + '7 hour'::interval
--                               AND (mp.date_from + '7 hour'::interval) <= now()
--                               AND (mp.date_to + '7 hour'::interval) >= now()
--                               AND mp.status = 'run'
--                               
--                           GROUP BY pc.id, pc.code
--                           UNION ALL
--                           SELECT pc.id, pc.code, string_agg(mc.name, ', ') AS coupon
--                           FROM product_category pc
--                             JOIN promotion_discount_used_time pdut ON pdut.product_category_id = pc.id
--                             JOIN mb_promotion mp ON mp.id = pdut.promotion_id
--                             JOIN mb_coupon mc ON mc.promotion_id = mp.id
--                           WHERE now() <= mc.expired_date + '7 hour'::interval
--                               AND (mp.date_from + '7 hour'::interval) <= now()
--                               AND (mp.date_to + '7 hour'::interval) >= now()
--                               AND mp.status = 'run'
--                               
--                           GROUP BY pc.id, pc.code""" % (domain, domain, domain, domain))
            rsl = cr.dictfetchall()
            data = []
            for item in rsl:
                data.append({
                    '"id"': item.get('id'),
                    '"code"': '"%s"' % (item.get('code') or ''),
                    '"promotion"': '"%s"' % (self.env['mb.coupon'].browse(item.get('id')).promotion_id.name or ''),
                    '"coupon"': item.get('coupon') and
                                ['"%s"' % coupon for coupon in item.get('coupon').split(', ')] or []
                })
            return {'"code"': 1, '"msg"': '"Successfully"', '"data"': data}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}

    @api.model
    def get_coupon_as_order(self, order):
        try:
            cr = self._cr
            domain = """"""
            order_id = self.env['sale.order'].browse(order)
            # if not order_id:
            #     return {'"code"': 0, '"msg"': '"Order not found"'}
            # if len(order_id) > 1:
            #     return {'"code"': 0, '"msg"': '"Have %s Order %s"' % (len(order_id), order)}
            categ_ids = order_id.mapped('order_line').mapped('product_category_id')
            if categ_ids:
                categ_ids = [c.id for c in categ_ids]
                if len(categ_ids) > 1:
                    domain += """AND pc.id IN %s """ % str(tuple(categ_ids))
                else:
                    domain += """AND pc.id = %s """ % categ_ids[0]
            cr.execute("""SELECT id, code, promotion, string_agg(name, ', ') AS coupon
                          FROM
                              (-------------- Product Category level 0 ----------------
                               SELECT pc.id, pc.code, mp.id promotion, mc.name
                               FROM product_category pc
                                   JOIN promotion_product_category ppc ON ppc.product_category_id = pc.id
                                   JOIN mb_promotion mp ON mp.id = ppc.promotion_id
                                   JOIN mb_coupon mc ON mc.promotion_id = mp.id
                                   LEFT JOIN sale_order so ON so.coupon = mc.name
                               WHERE now() <= mc.expired_date + '7 hour'::INTERVAL 
                                     AND (mp.date_from + '7 hour'::INTERVAL) <= now()
                                     AND (mp.date_to + '7 hour'::INTERVAL) >= now()
                                     AND mp.status = 'run'
                                     %s
                                     AND (so.id IS NULL
                                          OR (COALESCE(so.fully_paid, FALSE) = FALSE AND mc.max_used_time = 1)
                                          OR mc.max_used_time > 1)
                               GROUP BY pc.id, pc.code, mp.id, mc.name                               
                               UNION ALL 
                               -------------- Product Category level 1 ----------------
                               SELECT pc.id, pc.code, mp.id, mc.name
                               FROM product_category pc
                                   JOIN product_category pc1 ON pc1.id = pc.parent_id
                                   JOIN promotion_product_category ppc ON ppc.product_category_id = pc1.id
                                   JOIN mb_promotion mp ON mp.id = ppc.promotion_id
                                   JOIN mb_coupon mc ON mc.promotion_id = mp.id
                                   LEFT JOIN sale_order so ON so.coupon = mc.name
                               WHERE now() <= mc.expired_date + '7 hour'::INTERVAL 
                                     AND (mp.date_from + '7 hour'::INTERVAL) <= now()
                                     AND (mp.date_to + '7 hour'::INTERVAL) >= now()
                                     AND mp.status = 'run'
                                     %s
                                     AND (so.id IS NULL
                                          OR (COALESCE(so.fully_paid, FALSE) = FALSE AND mc.max_used_time = 1)
                                          OR mc.max_used_time > 1)
                               GROUP BY pc.id, pc.code, mp.id, mc.name                               
                               UNION ALL 
                               -------------- Product Category level 2 ----------------
                               SELECT pc.id, pc.code, mp.id, mc.name
                               FROM product_category pc
                                   JOIN product_category pc1 ON pc1.id = pc.parent_id
                                   JOIN product_category pc2 ON pc2.id = pc1.parent_id
                                   JOIN promotion_product_category ppc ON ppc.product_category_id = pc2.id
                                   JOIN mb_promotion mp ON mp.id = ppc.promotion_id
                                   JOIN mb_coupon mc ON mc.promotion_id = mp.id
                                   LEFT JOIN sale_order so ON so.coupon = mc.name
                               WHERE now() <= mc.expired_date + '7 hour'::INTERVAL 
                                     AND (mp.date_from + '7 hour'::INTERVAL) <= now()
                                     AND (mp.date_to + '7 hour'::INTERVAL) >= now()
                                     AND mp.status = 'run'
                                     %s
                                     AND (so.id IS NULL
                                          OR (COALESCE(so.fully_paid, FALSE) = FALSE AND mc.max_used_time = 1)
                                          OR mc.max_used_time > 1)
                               GROUP BY pc.id, pc.code, mp.id, mc.name                               
                               UNION ALL 
                               -------------- Register Time level 0 ----------------
                               SELECT pc.id, pc.code, mp.id, mc.name
                               FROM product_category pc
                                   JOIN promotion_register_time prt ON prt.product_category_id = pc.id
                                   JOIN mb_promotion mp ON mp.id = prt.promotion_id
                                   JOIN mb_coupon mc ON mc.promotion_id = mp.id
                                   LEFT JOIN sale_order so ON so.coupon = mc.name
                               WHERE now() <= mc.expired_date + '7 hour'::INTERVAL
                                     AND (mp.date_from + '7 hour'::INTERVAL) <= now()
                                     AND (mp.date_to + '7 hour'::INTERVAL) >= now()
                                     AND mp.status = 'run'
                                     %s
                                     AND (so.id IS NULL
                                          OR (coalesce(so.fully_paid, FALSE) = FALSE AND mc.max_used_time = 1)
                                          OR mc.max_used_time > 1)
                               GROUP BY pc.id, pc.code, mp.id, mc.name
                               UNION ALL 
                               -------------- Register Time level 1 ----------------
                               SELECT pc.id, pc.code, mp.id, mc.name
                               FROM product_category pc
                                   JOIN product_category pc1 ON pc1.id = pc.parent_id
                                   JOIN promotion_register_time prt ON prt.product_category_id = pc1.id
                                   JOIN mb_promotion mp ON mp.id = prt.promotion_id
                                   JOIN mb_coupon mc ON mc.promotion_id = mp.id
                                   LEFT JOIN sale_order so ON so.coupon = mc.name
                               WHERE now() <= mc.expired_date + '7 hour'::INTERVAL
                                     AND (mp.date_from + '7 hour'::INTERVAL) <= now()
                                     AND (mp.date_to + '7 hour'::INTERVAL) >= now()
                                     AND mp.status = 'run'
                                     %s
                                     AND (so.id IS NULL
                                          OR (coalesce(so.fully_paid, FALSE) = FALSE AND mc.max_used_time = 1)
                                          OR mc.max_used_time > 1)
                               GROUP BY pc.id, pc.code, mp.id, mc.name
                               UNION ALL 
                               -------------- Register Time level 2 ----------------
                               SELECT pc.id, pc.code, mp.id, mc.name
                               FROM product_category pc
                                   JOIN product_category pc1 ON pc1.id = pc.parent_id
                                   JOIN product_category pc2 ON pc2.id = pc1.parent_id
                                   JOIN promotion_register_time prt ON prt.product_category_id = pc2.id
                                   JOIN mb_promotion mp ON mp.id = prt.promotion_id
                                   JOIN mb_coupon mc ON mc.promotion_id = mp.id
                                   LEFT JOIN sale_order so ON so.coupon = mc.name
                               WHERE now() <= mc.expired_date + '7 hour'::INTERVAL
                                     AND (mp.date_from + '7 hour'::INTERVAL) <= now()
                                     AND (mp.date_to + '7 hour'::INTERVAL) >= now()
                                     AND mp.status = 'run'
                                     %s
                                     AND (so.id IS NULL
                                          OR (coalesce(so.fully_paid, FALSE) = FALSE AND mc.max_used_time = 1)
                                          OR mc.max_used_time > 1)
                               GROUP BY pc.id, pc.code, mp.id, mc.name
                               UNION ALL 
                               -------------- Amount Product level 0 ----------------
                               SELECT pc.id, pc.code, mp.id, mc.name
                               FROM product_category pc
                                   JOIN promotion_amount_product pap ON pap.product_category_id = pc.id
                                   JOIN mb_promotion mp ON mp.id = pap.promotion_id
                                   JOIN mb_coupon mc ON mc.promotion_id = mp.id
                                   LEFT JOIN sale_order so ON so.coupon = mc.name
                               WHERE now() <= mc.expired_date + '7 hour'::INTERVAL
                                     AND (mp.date_from + '7 hour'::INTERVAL) <= now()
                                     AND (mp.date_to + '7 hour'::INTERVAL) >= now()
                                     AND mp.status = 'run'
                                     %s
                                     AND (so.id IS NULL
                                          OR (coalesce(so.fully_paid, FALSE) = FALSE AND mc.max_used_time = 1)
                                          OR mc.max_used_time > 1)
                               GROUP BY pc.id, pc.code, mp.id, mc.name
                               UNION ALL  
                               -------------- Amount Product level 1 ----------------
                               SELECT pc.id, pc.code, mp.id, mc.name
                               FROM product_category pc
                                   JOIN product_category pc1 ON pc1.id = pc.parent_id
                                   JOIN promotion_amount_product pap ON pap.product_category_id = pc1.id
                                   JOIN mb_promotion mp ON mp.id = pap.promotion_id
                                   JOIN mb_coupon mc ON mc.promotion_id = mp.id
                                   LEFT JOIN sale_order so ON so.coupon = mc.name
                               WHERE now() <= mc.expired_date + '7 hour'::INTERVAL
                                     AND (mp.date_from + '7 hour'::INTERVAL) <= now()
                                     AND (mp.date_to + '7 hour'::INTERVAL) >= now()
                                     AND mp.status = 'run'
                                     %s
                                     AND (so.id IS NULL
                                          OR (coalesce(so.fully_paid, FALSE) = FALSE AND mc.max_used_time = 1)
                                          OR mc.max_used_time > 1)
                               GROUP BY pc.id, pc.code, mp.id, mc.name
                               UNION ALL 
                               -------------- Amount Product level 2 ----------------
                               SELECT pc.id, pc.code, mp.id, mc.name
                               FROM product_category pc
                                   JOIN product_category pc1 ON pc1.id = pc.parent_id
                                   JOIN product_category pc2 ON pc2.id = pc1.parent_id
                                   JOIN promotion_amount_product pap ON pap.product_category_id = pc2.id
                                   JOIN mb_promotion mp ON mp.id = pap.promotion_id
                                   JOIN mb_coupon mc ON mc.promotion_id = mp.id
                                   LEFT JOIN sale_order so ON so.coupon = mc.name
                               WHERE now() <= mc.expired_date + '7 hour'::INTERVAL
                                     AND (mp.date_from + '7 hour'::INTERVAL) <= now()
                                     AND (mp.date_to + '7 hour'::INTERVAL) >= now()
                                     AND mp.status = 'run'
                                     %s
                                     AND (so.id IS NULL
                                          OR (coalesce(so.fully_paid, FALSE) = FALSE AND mc.max_used_time = 1)
                                          OR mc.max_used_time > 1)
                               GROUP BY pc.id, pc.code, mp.id, mc.name
                               UNION ALL 
                               -------------- Total Product Discount level 0 ----------------
                               SELECT pc.id, pc.code, mp.id, mc.name
                               FROM product_category pc
                                   JOIN promotion_total_product_discount ptpd ON ptpd.product_category_id = pc.id
                                   JOIN mb_promotion mp ON mp.id = ptpd.promotion_id
                                   JOIN mb_coupon mc ON mc.promotion_id = mp.id
                                   LEFT JOIN sale_order so ON so.coupon = mc.name
                               WHERE now() <= mc.expired_date + '7 hour'::INTERVAL
                                     AND (mp.date_from + '7 hour'::INTERVAL) <= now()
                                     AND (mp.date_to + '7 hour'::INTERVAL) >= now()
                                     AND mp.status = 'run'
                                     %s
                                     AND (so.id IS NULL
                                          OR (COALESCE(so.fully_paid, FALSE) = FALSE AND mc.max_used_time = 1)
                                          OR mc.max_used_time > 1)
                               GROUP BY pc.id, pc.code, mp.id, mc.name
                               UNION ALL 
                               -------------- Total Product Discount level 1 ----------------
                               SELECT pc.id, pc.code, mp.id, mc.name
                               FROM product_category pc
                                   JOIN product_category pc1 ON pc1.id = pc.parent_id
                                   JOIN promotion_total_product_discount ptpd ON ptpd.product_category_id = pc1.id
                                   JOIN mb_promotion mp ON mp.id = ptpd.promotion_id
                                   JOIN mb_coupon mc ON mc.promotion_id = mp.id
                                   LEFT JOIN sale_order so ON so.coupon = mc.name
                               WHERE now() <= mc.expired_date + '7 hour'::INTERVAL
                                     AND (mp.date_from + '7 hour'::INTERVAL) <= now()
                                     AND (mp.date_to + '7 hour'::INTERVAL) >= now()
                                     AND mp.status = 'run'
                                     %s
                                     AND (so.id IS NULL
                                          OR (COALESCE(so.fully_paid, FALSE) = FALSE AND mc.max_used_time = 1)
                                          OR mc.max_used_time > 1)
                               GROUP BY pc.id, pc.code, mp.id, mc.name
                               UNION ALL 
                               -------------- Total Product Discount level 2 ----------------
                               SELECT pc.id, pc.code, mp.id, mc.name
                               FROM product_category pc
                                   JOIN product_category pc1 ON pc1.id = pc.parent_id
                                   JOIN product_category pc2 ON pc2.id = pc1.parent_id
                                   JOIN promotion_total_product_discount ptpd ON ptpd.product_category_id = pc2.id
                                   JOIN mb_promotion mp ON mp.id = ptpd.promotion_id
                                   JOIN mb_coupon mc ON mc.promotion_id = mp.id
                                   LEFT JOIN sale_order so ON so.coupon = mc.name
                               WHERE now() <= mc.expired_date + '7 hour'::INTERVAL
                                     AND (mp.date_from + '7 hour'::INTERVAL) <= now()
                                     AND (mp.date_to + '7 hour'::INTERVAL) >= now()
                                     AND mp.status = 'run'
                                     %s
                                     AND (so.id IS NULL
                                          OR (COALESCE(so.fully_paid, FALSE) = FALSE AND mc.max_used_time = 1)
                                          OR mc.max_used_time > 1)
                               GROUP BY pc.id, pc.code, mp.id, mc.name) A
                          GROUP BY id, code, promotion
                        """,
                       (domain, domain, domain, domain, domain, domain, domain, domain, domain, domain, domain, domain))
            rsl = cr.dictfetchall()
            data = []
            for item in rsl:
                promotion_id = self.env['mb.promotion'].browse(item.get('promotion'))
                data.append({
                    '"code"': '"%s"' % (item.get('code') or ''),
                    '"promotion"': '"%s"' % (promotion_id.name or ''),
                    '"promotion_id"': promotion_id.id,
                    '"coupon"': '"%s"' % (item.get('coupon') or '')
                })
            return {'"code"': 1, '"msg"': '"Successfully"', '"data"': data}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}
