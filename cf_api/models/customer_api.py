# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF, DEFAULT_SERVER_DATE_FORMAT as DF
import re
import logging as _logger
import json
from odoo.addons.cf_sale.models.sale_order_line import REGISTER_TYPE
from odoo.addons.cf_sale.models.sale_order import STATES


class CustomerAPI(models.AbstractModel):
    _description = 'External Customer API'
    _name = 'customer.api'

    @api.model
    def get_partner(self, code):
        res = {'"code"': 0, '"msg"': '', '"data"': {}}
        ResPartner = self.env['res.partner']
        data = {}
        # Check partner
        if not code:
            res.update({'"msg"': '"Code could be not empty"'})
            return res
        partner_id = ResPartner.search([('ref', '=', code)], limit=1)
        if not partner_id:
            res.update({'"msg"': '"Partner not found."'})
            return res
        try:
            move_line_obj = self.env['account.move.line'].sudo()
            move_line_received_data = move_line_obj.read_group(
                [('move_id.state', '=', 'posted'),
                 ('partner_id', '=', partner_id.id),
                 ('account_id', '=', partner_id.with_context(
                     force_company=partner_id.company_id.id).property_account_receivable_id.id),
                 ('company_id', '=', partner_id.company_id.id)], ['debit', 'credit'], [])
            debit = move_line_received_data and move_line_received_data[0]['debit'] or 0.0
            credit = move_line_received_data and move_line_received_data[0]['credit'] or 0.0
            received = credit - debit
            data.update({
                '"id"': partner_id.id,
                '"name"': '\"' + partner_id.name + '\"',
                '"ref"': '\"' + (partner_id.ref or '') + '\"',
                '"company_type"': '\"' + (partner_id.company_type or '') + '\"',
                '"customer_type"': '\"' + (partner_id.customer_type or '') + '\"',
                '"street"': '\"' + (partner_id.street or '') + '\"',
                '"state_id"': '\"' + (partner_id.state_id and partner_id.state_id.name or '') + '\"',
                '"country_id"': '\"' + (partner_id.country_id and partner_id.country_id.name or '') + '\"',
                '"website"': '\"' + (partner_id.website or '') + '\"',
                '"date_of_birth"': '\"' + (partner_id.date_of_birth or '') + '\"',
                '"date_of_founding"': '\"' + (partner_id.date_of_founding or '') + '\"',
                '"vat"': '\"' + (partner_id.vat or '') + '\"',
                '"identify_number"': '\"' + (partner_id.identify_number or '') + '\"',
                '"phone"': '\"' + (partner_id.phone or '') + '\"',
                '"mobile"': '\"' + (partner_id.mobile or '') + '\"',
                '"fax"': '\"' + (partner_id.fax or '') + '\"',
                '"email"': '\"' + (partner_id.email or '') + '\"',
                '"sub_email_1"': '\"' + (partner_id.sub_email_1 or '') + '\"',
                '"sub_email_2"': '\"' + (partner_id.sub_email_2 or '') + '\"',
                '"title"': '\"' + (partner_id.title and partner_id.title.name or '') + '\"',
                '"company_id"': partner_id.company_id and partner_id.company_id.id or 0,
                '"gender"': '\"' + (partner_id.gender or '') + '\"',
                '"representative"': '\"' + (partner_id.representative or '') + '\"',
                '"agency_level"': partner_id.agency_level or 0,
                '"new_customer"': partner_id.new_customer and 1 or 0,
                '"password"': '\"' + (partner_id.password or '') + '\"',
                '"balance_131"': received,
            })
            res.update({'"code"': 1, '"msg"': '"Successfully"', '"data"': data})
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Can not get partner: %s"' % (e.message or repr(e))}
        return res

    @api.model
    def change_password(self, code, new_pass):
        ResPartner = self.env['res.partner']
        if not new_pass:
            return {'"code"': 0, '"msg"': '"New Password could be not empty"'}
        if not code:
            return {'"code"': 0, '"msg"': '"Code could be not empty"'}
        partner_id = ResPartner.search([('ref', '=', code)])
        if not partner_id:
            return {'"code"': 0, '"msg"': '"Customer not found."'}
        if len(partner_id) > 1:
            return {'"code"': 0, '"msg"': '"Have %s customer with code %s."' % (len(partner_id), code)}
        try:
            partner_id.write({'password': new_pass})
            return {'"code"': 1, '"msg"': '"Change password completed."'}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}

    @api.model
    def get_customer_balance(self, customer_code):
        customer_id = self.env['res.partner'].search([('ref', '=', customer_code)])
        if not customer_id:
            return {'"code"': 0, '"msg"': '"Customer not found"'}
        if len(customer_id) > 1:
            return {'"code"': 0, '"msg"': '"Have %s customer"' % len(customer_id)}
        account_id = customer_id.with_context(force_company=customer_id.company_id.id).property_account_receivable_id
        if not account_id:
            return {'"code"': 0, '"msg"': '"Pls config Account Receivable"'}
        try:
            move_line_ids = self.env['account.move.line'].search([
                ('move_id.state', '=', 'posted'),
                ('partner_id', '=', customer_id.id),
                ('account_id', '=', account_id.id),
                ('company_id', '=', customer_id.company_id.id)])
            debit = move_line_ids and sum(move.debit for move in move_line_ids) or 0.0
            credit = move_line_ids and sum(move.credit for move in move_line_ids) or 0.0
            data = []
            for line in move_line_ids:
                data.append({
                    '"customer"': '"%s"' % (line.partner_id.name or ''),
                    '"credit"': line.credit or 0,
                    '"debit"': line.debit or 0,
                    '"date"': '"%s"' % (line.date or ''),
                    '"name"': '"%s"' % (line.name or ''),
                    '"reference"': '"%s"' % (line.ref or ''),
                    '"entry"': '"%s"' % (line.move_id and line.move_id.name or ''),
                })
            return {'"code"': 1, '"msg"': '"Successfully"', '"balance"': credit - debit, '"data"': data}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}