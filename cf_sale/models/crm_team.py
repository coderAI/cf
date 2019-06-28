# -*- coding: utf-8 -*-
from odoo import models, api, fields, SUPERUSER_ID, _

class CRMTeam(models.Model):
    _inherit = 'crm.team'

    type = fields.Selection([('cs', 'Customer Service'), ('sale', 'Sale')])
