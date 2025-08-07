# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountReportExtended(models.Model):
    _inherit = "account.report"

    def _get_options(self, previous_options=None):
        # OVERRIDE
        options = super(AccountReportExtended, self)._get_options(previous_options)

        # If manual values were stored in the context, we store them as options.
        # This is useful for report printing, were relying only on the context is
        # not enough, because of the use of a route to download the report (causing
        # a context loss, but keeping the options).
        if self._context.get('magento_report'):
            magento_instance_ids = self.env['magento.instance'].search([('active', '=', 'True')])
            if magento_instance_ids:
                options.update(
                    {
                        'analytic_accounts_groupby': magento_instance_ids.magento_website_ids.m_website_analytic_account_id.ids or magento_instance_ids.mapped(
                            'magento_analytic_account_id').ids})
        return options
