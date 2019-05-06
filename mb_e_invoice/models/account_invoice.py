from odoo import api, fields, models, tools, _
from odoo.exceptions import Warning
import logging

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    """ Printable account_invoice.
    """
    _inherit = 'account.invoice'

    support_invisible_create_e_invoice = fields.Boolean(compute='_get_refund')
    support_invisible_set_to_draft = fields.Boolean(compute='_get_refund')
    support_invisible_send_request = fields.Boolean(compute='_get_refund')
    support_invisible_export_action = fields.Boolean(compute='_get_refund')
    e_invoice_id = fields.Many2one("mb.e.invoices",string='E-invoice',compute='_get_refund')
    e_invoice_name = fields.Char(string='E-Invoice',compute='_get_refund')
    e_invoice_state = fields.Char(string='E-Invoice State',compute='_get_refund')
    e_invoice_stages_id = fields.Char(string='E-Invoice stages_id',compute='_get_refund')
    e_invoice_require_date = fields.Date(string='Require Date',compute='_get_refund')
    e_invoice_template_no = fields.Char(string='Template No',compute='_get_refund')
    e_invoice_reference_no = fields.Char(string='Reference No',compute='_get_refund')
    e_invoice_vat_no = fields.Char(string='Vat No',compute='_get_refund')
    e_invoice_reason_line = fields.Char(string='Reason',compute='_get_refund')
    # support_invisible_create_e_invoice = fields.Boolean(string='test')

    def get_data_e_invoice(self,data):
        e_invoice_reason_line = ''
        e_invoice_id = data.id
        e_invoice_require_date = data.require_date
        e_invoice_template_no = data.template_no
        e_invoice_reference_no = data.reference_no
        e_invoice_name = data.name
        e_invoice_stages_name = data.stages_name
        e_invoice_stages_id = data.stages_id.id
        e_invoice_vat_no = data.vat_no
        for i_reason_line in data.reason_line_ids:
            e_invoice_reason_line = i_reason_line.mb_reason_invoice_id.name
        return  e_invoice_id,\
                e_invoice_require_date,\
                e_invoice_template_no,\
                e_invoice_reference_no,\
                e_invoice_name,\
                e_invoice_stages_name, \
                e_invoice_stages_id, \
                e_invoice_vat_no,\
                e_invoice_reason_line

    @api.multi
    def _get_refund(self):
        mb_e_invoices_obj = self.env['mb.e.invoices']
        stages_invoice_obj = self.env['stages.invoice']
        stage_data_cancel = stages_invoice_obj.sudo().search([('key', '=', 'mb_e_cancel')], limit=1)
        stage_data_draft = stages_invoice_obj.sudo().search([('key', '=', 'mb_e_draft')], limit=1)
        stage_data_refuse = stages_invoice_obj.sudo().search([('key', '=', 'mb_e_refuse')], limit=1)
        stage_data_open = stages_invoice_obj.sudo().search([('key', '=', 'mb_e_open')], limit=1)
        stage_data_done = stages_invoice_obj.sudo().search([('key', '=', 'mb_e_done')], limit=1)
        support_invisible_create_e_invoice = True
        support_invisible_set_to_draft = True
        support_invisible_send_request = True
        support_invisible_export_action = True
        e_invoice_id = False
        e_invoice_require_date = ''
        e_invoice_template_no = ''
        e_invoice_reference_no = ''
        e_invoice_name = ''
        e_invoice_stages_name = ''
        e_invoice_stages_id = False
        e_invoice_vat_no = ''
        e_invoice_reason_line = ''
        tmp_mb_e_invoices_data = None
        if stage_data_cancel.id and stage_data_draft.id and stage_data_refuse.id:
            mb_e_invoices_data_refuse = mb_e_invoices_obj.sudo().search([('stages_id','=',stage_data_refuse.id),('invoice_ids', '=', self._ids)],order='id ASC', limit=1)
            mb_e_invoices_data = mb_e_invoices_obj.sudo().search([('stages_id','=',stage_data_draft.id),('invoice_ids', '=', self._ids)],order='id ASC', limit=1)
            mb_e_invoices_data_cancel = mb_e_invoices_obj.sudo().search([('stages_id','=',stage_data_cancel.id),('invoice_ids', '=', self._ids)],order='id ASC', limit=1)
            mb_e_invoices_data_open = mb_e_invoices_obj.sudo().search([('stages_id','=',stage_data_open.id),('invoice_ids', '=', self._ids)],order='id ASC', limit=1)
            mb_e_invoices_data_done = mb_e_invoices_obj.sudo().search([('stages_id','=',stage_data_done.id),('invoice_ids', '=', self._ids)],order='id ASC', limit=1)

            if mb_e_invoices_data_done.id:
                tmp_mb_e_invoices_data = mb_e_invoices_data_done
                support_invisible_export_action = False
                logging.info("---------------Done -----------------")
            elif mb_e_invoices_data_open.id:
                tmp_mb_e_invoices_data = mb_e_invoices_data_open
                logging.info("---------------open -----------------")
            elif mb_e_invoices_data_refuse.id:
                tmp_mb_e_invoices_data = mb_e_invoices_data_refuse
                support_invisible_set_to_draft = False
                logging.info("---------------refuse -----------------")
            elif mb_e_invoices_data.id:
                tmp_mb_e_invoices_data = mb_e_invoices_data
                if mb_e_invoices_data.id:
                    if mb_e_invoices_data.stages_id.id == stage_data_draft.id:
                        support_invisible_send_request = False
                else:
                    logging.info("---------------create -----------------")
                    support_invisible_create_e_invoice = False

            elif mb_e_invoices_data_cancel.id:
                tmp_mb_e_invoices_data = mb_e_invoices_data_cancel
                logging.info("---------------cancel -----------------")
                support_invisible_create_e_invoice = False
            else:
                support_invisible_create_e_invoice = False

            #Get data for show
            if tmp_mb_e_invoices_data != None:
                e_invoice_id,\
                e_invoice_require_date,\
                e_invoice_template_no, \
                e_invoice_reference_no, \
                e_invoice_name,\
                e_invoice_stages_name,\
                e_invoice_stages_id,\
                e_invoice_vat_no,\
                e_invoice_reason_line = self.get_data_e_invoice(tmp_mb_e_invoices_data)

        self.support_invisible_create_e_invoice = support_invisible_create_e_invoice
        self.support_invisible_set_to_draft = support_invisible_set_to_draft
        self.support_invisible_send_request = support_invisible_send_request
        self.support_invisible_export_action = support_invisible_export_action
        self.e_invoice_id = e_invoice_id
        self.e_invoice_require_date = e_invoice_require_date
        self.e_invoice_template_no = e_invoice_template_no
        self.e_invoice_reference_no = e_invoice_reference_no
        self.e_invoice_name = e_invoice_name
        self.e_invoice_state = e_invoice_stages_name
        self.e_invoice_stages_id = e_invoice_stages_id
        self.e_invoice_vat_no = e_invoice_vat_no
        self.e_invoice_reason_line = e_invoice_reason_line


    @api.multi
    def create_e_invoice(self):
        ir_model_data = self.env['ir.model.data']
        try:
            compose_form_id = ir_model_data.get_object_reference('mb_e_invoice', 'view_mb_e_invoice_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'mb.e.invoices',
            'invoice_id': self.ids[0],
            'customer_id': self.partner_id.id,
            'action_by': 'create_e_invoice',
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mb.e.invoice.wizard',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
    @api.multi
    def send_request_e_invoice(self):
        mb_e_invoices_obj = self.env['mb.e.invoices']
        mb_e_invoices_data = mb_e_invoices_obj.search([('id','=',self.e_invoice_id.id)])
        mb_e_invoices_data.write({
            'stages_id': mb_e_invoices_data.change_stages('open')
        })

    @api.multi
    def export_action(self):
        return self.e_invoice_id.download_report()

    @api.multi
    def set_to_draft(self):
        mb_e_invoices_obj = self.env['mb.e.invoices']
        mb_e_invoices_data = mb_e_invoices_obj.search([('id','=',self.e_invoice_id.id)])

        ir_model_data = self.env['ir.model.data']
        try:
            compose_form_id = ir_model_data.get_object_reference('mb_e_invoice', 'view_mb_e_invoice_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'mb.e.invoices',
            'invoice_id': self.ids[0],
            'customer_id': self.partner_id.id,
            'action_by':'set_to_draft',
            'customer_id':mb_e_invoices_data.customer_id.id,
            'address':mb_e_invoices_data.address,
            'buyer_name':mb_e_invoices_data.buyer_name,
            #'tax_code':mb_e_invoices_data.tax_code,
            'require_date':mb_e_invoices_data.require_date,
            'mb_e_invoices_id':mb_e_invoices_data.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mb.e.invoice.wizard',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

