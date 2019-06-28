# -*- coding: utf-8 -*-
from openerp import models, api, SUPERUSER_ID
from openerp.tools.translate import _
import logging as _logger
from odoo.tools.safe_eval import safe_eval


class CFUpdateFunctionData(models.TransientModel):
    _name = "cf.update.function.data"
    _description = "CloudFone Module Post Object"

    @api.model
    def start(self):
        self.run_post_object_one_time(
            'cf.update.function.data',
            ['_create_service_sequence_auto',
             '_set_default_vendor',
             ])
        return True

    @api.model
    def run_post_object_one_time(self, object_name, list_functions=[]):
        """
        Generic function to run post object one time
        Input:
            + Object name: where you define the functions
            + List functions: to run
        Result:
            + Only functions which are not run before will be run
        """
        _logger.info('==START running one time functions for post object: %s'
                     % object_name)
        if isinstance(list_functions, (str, unicode)):  # @UndefinedVariable
            list_functions = [list_functions]
        if not list_functions\
                or not isinstance(list_functions, (list)):
            _logger.warning('Invalid value of parameter list_functions.\
                            Exiting...')
            return False

        ir_conf_para_env = self.env['ir.config_parameter']
        post_object_env = self.env[object_name]
        ran_functions = \
            ir_conf_para_env.get_param(
                'List_post_object_one_time_functions', '[]')
        ran_functions = safe_eval(ran_functions)
        if not isinstance(ran_functions, (list)):
            ran_functions = []
        for function in list_functions:
            if (object_name + ':' + function) in ran_functions:
                continue
            getattr(post_object_env, function)()
            ran_functions.append(object_name + ':' + function)
        if ran_functions:
            ir_conf_para_env.set_param('List_post_object_one_time_functions',
                                       str(ran_functions))
        _logger.info('==END running one time functions for post object: %s'
                     % object_name)
        return True

    @api.model
    def _create_service_sequence_auto(self):
        """
            TO DO:
            - Create sequences for all product categories
        """
        _logger.info("=== START: create sequence for categories ===")
        IrSequence = self.env['ir.sequence']
        no_sequence_categories = self.env['product.category'].search(
            [('service_sequence_id', '=', False)])
        for category in no_sequence_categories:
            new_service_sequence = IrSequence.create({'name': category.name,
                                                      'padding': '7'})
            category.service_sequence_id = new_service_sequence
        _logger.info("=== END: create sequence for categories ===")

    @api.model
    def _set_default_vendor(self):
        """
            TO DO:
            - Set default vendor for purchase order
        """
        _logger.info("=== START: set default vendor ===")
        ir_values_obj = self.env['ir.values']
        default_vendor = self.env['res.partner'].search(
            [('name', '=', 'Default Vendor'), ('supplier', '=', True)],
            limit=1)
        if default_vendor:
            ir_values_obj.sudo().set_default(
                'purchase.order', "partner_id", default_vendor.id)
            ir_values_obj.sudo().set_default(
                'purchase.config.settings', 'partner_id', default_vendor.id)
        _logger.info("=== END: set default vendor ===")