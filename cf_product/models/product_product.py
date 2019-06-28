# -*- coding: utf-8 -*-
from odoo import api, models
from lxml import etree
from odoo.osv.orm import setup_modifiers


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def create(self, vals):
        IrSequence = self.env['ir.sequence']
        if not vals.get('default_code'):
            vals.update({
                'default_code': IrSequence.next_by_code('product.product')
            })
        return super(ProductProduct, self).create(vals)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ProductProduct, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                          submenu=submenu)
        if view_type == 'tree':
            if self.user_has_groups('base.group_system'):
                doc = etree.XML(res['arch'])
                tree_view = doc.xpath("//tree")
                tree_view[0].set('create', 'true')
                tree_view[0].set('delete', 'true')
                setup_modifiers(tree_view[0])
                res['arch'] = etree.tostring(doc)
            else:
                doc = etree.XML(res['arch'])
                tree_view = doc.xpath("//tree")
                tree_view[0].set('create', 'false')
                tree_view[0].set('delete', 'false')
                setup_modifiers(tree_view[0])
                res['arch'] = etree.tostring(doc)
        if view_type == 'form':
            if self.user_has_groups('base.group_system'):
                doc = etree.XML(res['arch'])
                form_view = doc.xpath("//form")
                form_view[0].set('create', 'true')
                form_view[0].set('edit', 'true')
                form_view[0].set('delete', 'true')
                setup_modifiers(form_view[0])
                res['arch'] = etree.tostring(doc)
            else:
                doc = etree.XML(res['arch'])
                form_view = doc.xpath("//form")
                form_view[0].set('create', 'false')
                form_view[0].set('edit', 'false')
                form_view[0].set('delete', 'false')
                setup_modifiers(form_view[0])
                res['arch'] = etree.tostring(doc)
        return res
