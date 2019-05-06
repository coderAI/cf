from odoo import api, fields, models, tools, _
from odoo.exceptions import Warning

class mb_reason_invoice(models.Model):

    _name = 'mb.reason.invoice'
    name = fields.Char(string='Reason',required=True)
    #key = fields.Char(string='Key',required=True)
    type = fields.Selection([('e_invoice_cancel', 'Cancel E-Invoice'), ('e_invoice_reject', 'Reject E-Invoice')], 'Reason Type', default='e_invoice_cancel')
    active = fields.Boolean('Active', default=True)
    note = fields.Char(string='Note')


class mb_reason_invoice_line(models.Model):

    _name = 'mb.reason.invoice.line'
    mb_reason_invoice_id = fields.Many2one('mb.reason.invoice', string='Reason')
    name = fields.Char(related='mb_reason_invoice_id.name', string='Reason', store=True)
    mb_e_invoices_id = fields.Many2one('mb.e.invoices', string='E-Invoice')

    note = fields.Char(string='Note')



    @api.model
    def create(self, vals):
        rec_context = dict(self.env.context)
        if rec_context.get('action_type') == 'set_reject':
            vals.update({'mb_e_invoices_id': rec_context.get('default_res_id')})



        return super(mb_reason_invoice_line, self).create(vals)
