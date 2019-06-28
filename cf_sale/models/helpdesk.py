# -*- coding: utf-8 -*-
from odoo import models, fields, api, SUPERUSER_ID, _
from lxml import etree
from odoo.osv.orm import setup_modifiers
from odoo.exceptions import Warning
import logging


class HelpDesk(models.Model):
    _inherit = 'helpdesk.ticket'

    service_id = fields.Many2one('sale.service', string='Service', track_visibility='onchange')

