# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models, SUPERUSER_ID
from odoo.tools.translate import _
import logging


class TicketAPI(models.AbstractModel):
    _description = 'External Ticket API'
    _name = 'ticket.api'

    @api.model
    def create_ticket(self, customer_code, subject, assign_to, team, description, service, ticket_type='', tags=[]):
        res = {'"code"': 0}
        args = {}
        customer_id = False
        if customer_code:
            customer_id = self.env['res.partner'].search([('ref', '=', customer_code)])
            if not customer_id:
                res['"msg"'] = '"Customer not exists"'
                return res
        args['partner_id'] = customer_id and customer_id.id or False
        if not subject:
            res['"msg"'] = '"Subject could not be empty"'
            return res
        args['name'] = subject
        if assign_to:
            user_id = self.env['rss.users'].search([('login', '=', assign_to)])
            if not user_id:
                res['"msg"'] = '"Assign To not exists"'
                return res
            args['user_id'] = user_id.id
        if team:
            team_id = self.env['helpdesk.team'].search([('name', '=', team)])
            if not team_id:
                res['"msg"'] = '"Helpdesk Team not exists"'
                return res
            args['team_id'] = team_id.id
        if description:
            args['description'] = description
        if service and customer_id:
            service_id = self.env['sale.service'].search([('customer_id', '=', customer_id.id),
                                                          ('reference', '=', service)], limit=1)
            if not service_id:
                res['"msg"'] = '"Service not found or Service not belong customer."'
                return res
            args['service_id'] = service_id.id
        try:
            ticket_id = self.env['helpdesk.ticket'].create(args)
            if ticket_type:
                ticket_type_id = self.env['helpdesk.ticket.type'].search([('name', '=', ticket_type)], limit=1)
                ticket_id.ticket_type_id = ticket_type_id and ticket_type_id.id or False
            if tags:
                tag_ids = self.env['helpdesk.tag'].search([('name', 'in', list(tags))])
                ticket_id.tag_ids = tag_ids and [(6, 0, tag_ids.ids)] or False
            return {'"code"': 1, '"msg"': '"Create successfully"', '"ticket"': ticket_id.id}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}

    @api.model
    def get_ticket(self, customer_code, service=''):
        if not customer_code:
            return {'"code"': 0, '"msg"': '"Customer Code could be not empty"'}
        customer_id = self.env['res.partner'].search([('ref', '=', customer_code)])
        if not customer_id:
            return {'"code"': 0, '"msg"': '"Customer not found"'}
        if len(customer_id) > 1:
            return {'"code"': 0, '"msg"': '"Have %s Customer"' % len(customer_id)}
        domain = [('partner_id', '=', customer_id.id)]
        if service:
            domain.append(('service_id.reference', '=', service))
        try:
            data = []
            ticket_ids = self.env['helpdesk.ticket'].search(domain)
            for ticket in ticket_ids:
                data.append({
                    '"id"': ticket.id,
                    '"subject"': '"%s"' % (ticket.name or ''),
                    '"assign_to"': '"%s"' % (ticket.user_id and ticket.user_id.name or ''),
                    '"team"': '"%s"' % (ticket.team_id and ticket.team_id.name or ''),
                    '"description"': '"%s"' % (ticket.description or ''),
                    '"customer_code"': '"%s"' % (ticket.partner_id and ticket.partner_id.ref or ''),
                    '"customer_name"': '"%s"' % (ticket.partner_id and ticket.partner_id.name or ''),
                    '"ticket_type"': '"%s"' % (ticket.ticket_type_id and ticket.ticket_type_id.name or ''),
                    '"tags"': ticket.tag_ids and ['"%s"' % tag.name for tag in ticket.tag_ids] or [],
                    '"service"': '"%s"' % (ticket.service_id and ticket.service_id.reference or ''),
                    '"stage"': '"%s"' % (ticket.stage_id and ticket.stage_id.name or ''),
                    '"create_date"': '"%s"' % (ticket.create_date or ''),
                })
            return {'"code"': 1, '"msg"': '"Get successfully"', '"data"': data}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}

    @api.model
    def get_ticket_info(self, ticket):
        ticket = self.env['helpdesk.ticket'].browse(ticket)
        if not ticket:
            return {'"code"': 0, '"msg"': '"Ticket not found"'}
        try:
            data = {
                '"subject"': '"%s"' % (ticket.name or ''),
                '"assign_to"': '"%s"' % (ticket.user_id and ticket.user_id.name or ''),
                '"team"': '"%s"' % (ticket.team_id and ticket.team_id.name or ''),
                '"description"': '"%s"' % (ticket.description or ''),
                '"customer_code"': '"%s"' % (ticket.partner_id and ticket.partner_id.ref or ''),
                '"customer_name"': '"%s"' % (ticket.partner_id and ticket.partner_id.name or ''),
                '"ticket_type"': '"%s"' % (ticket.ticket_type_id and ticket.ticket_type_id.name or ''),
                '"tags"': ticket.tag_ids and ['"%s"' % tag.name for tag in ticket.tag_ids] or [],
                '"service"': '"%s"' % (ticket.service_id and ticket.service_id.reference or ''),
                '"stage"': '"%s"' % (ticket.stage_id and ticket.stage_id.name or ''),
                '"create_date"': '"%s"' % (ticket.create_date or ''),
            }
            return {'"code"': 1, '"msg"': '"Get successfully"', '"data"': data}
        except Exception as e:
            return {'"code"': 0, '"msg"': '"Error: %s"' % (e.message or repr(e))}