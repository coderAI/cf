# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import Warning
import hashlib

class GenerateCodeWizard(models.TransientModel):
    _name = 'generate.code.wizard'

    name = fields.Char(string='Code', size=25)

    def action_generate(self):
        if len(self.name) < 6:
            raise Warning(_("Code must be more than 6 characters."))
        partner_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        partner_id.write({
            'password': hashlib.md5(self.name.encode("utf-8")).hexdigest()
        })

