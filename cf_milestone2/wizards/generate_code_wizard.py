# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import Warning
import hashlib
import string
import random

class GenerateCodeWizard(models.TransientModel):
    _inherit = 'generate.code.wizard'

    partner_id = fields.Many2one('res.partner', "Customer")
    related_name = fields.Char("Code", compute='get_name')

    @api.depends('name')
    def get_name(self):
        self.related_name = self.name

    def generate_code(self, leng):
        """ The leng is the length of the coupon code, arr is the list of available coupons"""
        code = ''.join(random.choice(string.ascii_letters + string.digits[1:]) for _ in range(leng))
        return code

    @api.model
    def default_get(self, fields):
        res = super(GenerateCodeWizard, self).default_get(fields)
        if 'display_name' not in fields:
            res.update({
                'name': self.generate_code(10),
                'partner_id': self._context.get('active_id')
            })
        return res

    def action_generate(self):
        partner_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        partner_id.write({
            'password': hashlib.md5(self.name.encode("utf-8")).hexdigest()
        })
        template = self.env.ref('ods_customer.ods_reset_password_notification_template')
        try:
            template.send_mail(res_id=self.id, force_send=True, email_values={'email_from': '%s <%s>' % (
            partner_id.company_id.rml_header1 or partner_id.company_id.name, partner_id.company_id.email)})
        except Exception as e:
            raise Warning(_("Can't send email to customer: %s" % (e.message or repr(e))))

