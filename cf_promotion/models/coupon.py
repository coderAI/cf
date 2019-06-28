from odoo import api, fields, models
from datetime import datetime

class Coupon(models.Model):
    _name = "mb.coupon"
    _inherit = ['mail.thread']

    name = fields.Char('Code', track_visibility='onchange')
    promotion_id = fields.Many2one('mb.promotion', 'Promotion', track_visibility='onchange')
    expired_date = fields.Datetime('Expired Date', track_visibility='onchange')
    max_used_time = fields.Integer("Max Used Time", track_visibility='onchange')
    used_date = fields.Date("Used Date")
    sale_order_count = fields.Integer(compute="_compute_sale_order_count")
    invisible_on_sale = fields.Boolean("Invisible on Sale")

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self._context.get('for_sale'):
            self._cr.execute("""SELECT mc.id
                                FROM mb_coupon mc
                                    JOIN mb_promotion mp ON mp.id = mc.promotion_id
                                WHERE mp.status = 'run' AND mc.expired_date >= %s
                                      AND mp.date_from <= %s AND mp.date_to >= %s
                                      AND COALESCE(mc.invisible_on_sale, FALSE) = FALSE
                                GROUP BY mc.id""",
                             (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                              datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                              datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            rsl = self._cr.dictfetchall()
            coupon_ids = rsl and [item['id'] for item in rsl] or []
            args.append(('id', 'in', coupon_ids))
        # logging.info("********************* %s *******************", args)
        return super(Coupon, self).search(args, offset, limit, order, count)

    def _compute_sale_order_count(self):
        for pr in self:
            pr.sale_order_count = self.env['sale.order'].search_count([('coupon', '=', pr.name)])

    @api.multi
    def open_sale_order_action(self):
        return {
            'name': 'Sale Orders',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'domain': [('coupon', 'in', self.mapped('name'))],
            "context": {"create": False, "edit": False, "delete": False},
            'target': 'self',
        }

    @api.model
    def check_coupon(self, coupon):
        coupon_id = self.search([('name', '=', coupon.strip())])
        if not coupon_id:
            return {'"code"': 0, '"msg"': '"Coupon not exists"'}
        count_order = self.env['sale.order'].search_count([('fully_paid', '=', True),
                                                           ('coupon', '=', coupon.strip())])
        if count_order >= coupon_id.max_used_time:
            return {'"code"': 0, '"msg"': '"Coupon used exceeded number of times allowed"'}
        if datetime.now().strftime('%Y-%m-%d %H:%M:%S') > coupon_id.expired_date:
            return {'"code"': 0, '"msg"': '"Coupon used over expired time"'}
        promotion_id = coupon_id.promotion_id
        if promotion_id.status <> 'run':
            return {'"code"': 0, '"msg"': '"Promotion have stopped"'}
        if promotion_id.date_from > datetime.now().strftime('%Y-%m-%d %H:%M:%S') or \
                datetime.now().strftime('%Y-%m-%d %H:%M:%S') > promotion_id.date_to:
            return {'"code"': 0, '"msg"': '"Promotion not yet started"'}
        # Check A Customer only used once
        # if promotion_id.only_used_once:
        #     order_ids = self.env['sale.order'].search_count([('partner_id', '=', partner_id.id),
        #                                                      ('coupon', '=', coupon.strip()),
        #                                                      ('fully_paid', '=', True),
        #                                                      ('state', 'not in', ('cancel',))])
        #     if order_ids >= 1:
        #         return {'"code"': 0, '"msg"': '"Customer used the coupon code in another order"'}
        return {'"code"': 1, '"msg"': '""'}
