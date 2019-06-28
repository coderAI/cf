# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning
import re
from odoo.tools.float_utils import float_compare
from odoo.osv.orm import setup_modifiers
from odoo.tools.safe_eval import safe_eval
from lxml import etree


class ResPartner(models.Model):
    _inherit = "res.partner"

    contract_id = fields.Many2one('cf.contract', "Contract")

    @api.depends(lambda self: self._display_address_depends())
    def _compute_contact_address(self):
        for partner in self:
            partner.contact_address = ', '.join([partner.street or '',
                                                 partner.state_id and partner.state_id.name or '',
                                                 partner.country_id and partner.country_id.name or ''])