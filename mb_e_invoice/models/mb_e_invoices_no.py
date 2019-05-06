from odoo import api, fields, models, tools, _


class mb_e_invoices(models.Model):
    _name       = 'mb.e.invoices.no'
    _inherit    = 'mail.thread'

    @api.depends('number_id', 'notation_id')
    def _get_name(self):
        for record in self:
            record.name = record.number_id.name + ' / ' + record.notation_id.name

    @api.depends('line_ids')
    def _get_count_line(self):
        for record in self:
            record.countline = False
            if len(record.line_ids) > 0:
                record.countline = True

    name        = fields.Char(compute='_get_name')
    number_id   = fields.Many2one('invoice.number', string='Template', track_visibility='onchange')
    notation_id = fields.Many2one('invoice.notation', string='Reference No.', track_visibility='onchange')
    no_from     = fields.Integer(string='From', track_visibility='onchange', default=1)
    no_to       = fields.Integer(string="To", track_visibility='onchange', default=10)
    create_uid  = fields.Many2one('res.users', string='Create User', default=lambda self: self.env.uid)
    line_ids    = fields.One2many('mb.invoice.no.line', 'no_id', string='VAT Invoice No.')
    countline   = fields.Boolean(compute='_get_count_line', default=False)

    @api.constrains('no_from', 'no_to')
    def check_no(self):
        if self.no_to and self.no_from and self.no_from > self.no_to:
            raise Warning(_("Start Number must be less than End Number."))

    @api.multi
    def unlink(self):
        for record in self:
            list_no = record.line_ids.mapped('is_used')
            if 'used' in list_no or 'cancel' in list_no or 'lost' in list_no:
                raise Warning(_("Can't delete this record because it has been used."))
        super(mb_e_invoices, self).unlink()

    @api.one
    def create_action(self):
        if self.no_from == 0 and self.no_to == 0:
            return True
        if not self.line_ids:
            self.line_ids = [(0, 0, {'number': num, 'is_used': 'no_use'}) for num in range(self.no_from, self.no_to + 1)]
        else:
            max_no = max(map(int, self.line_ids.mapped('number')))
            if self.no_to > max_no:
                for num in range(max_no + 1, self.no_to + 1):
                    self.env['mb.invoice.no.line'].create({
                        'number': num,
                        'is_used': 'no_use',
                        'no_id': self.id,
                    })