# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import Warning

class ServiceAddonOrderLinesWizard(models.TransientModel):
    _inherit = "service.addon.order.lines.wizard"

    @api.multi
    def get_line_values(self, line):
        vals = super(ServiceAddonOrderLinesWizard, self).get_line_values(line=line)
        vals.update({'original_time': line.time})
        return vals