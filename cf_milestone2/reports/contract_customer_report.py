# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

class ContractReport(models.Model):
    _name = 'contract.customer.report'
    _auto = False
    _description = "Contract Analysis"

    partner_id = fields.Many2one('res.partner', "Customer", readonly=True)
    contract_id = fields.Many2one('ods.contract', 'Contract', readonly=True)
    type = fields.Selection([('yes', 'Yes'), ('no', 'No')])
    create_user = fields.Many2one('res.users', 'Create User')
    create_date = fields.Date('Create Date')

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'contract_customer_report')
        self.env.cr.execute("""
            CREATE or REPLACE VIEW contract_customer_report as (
                SELECT rp.id, rp.id AS partner_id, rp.contract_id, oc.create_uid AS create_user, oc.create_date,
                        CASE WHEN rp.contract_id IS NOT NULL THEN 'yes' ELSE 'no' END AS type
                FROM res_partner rp
                    LEFT JOIN ods_contract oc ON oc.id = rp.contract_id
            )""")