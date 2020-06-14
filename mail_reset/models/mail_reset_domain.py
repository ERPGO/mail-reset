# -*- coding: utf-8 -*-

from . import common
from odoo import models, fields, api

class Mail_Reset_Domain(models.Model):
    _name = 'mail_reset.domain'
    _description = 'Mail Domain'

    name = fields.Char(string="Domain name", required=True)
    contact = fields.Many2one('res.partner', string="Contact")
    namespace = fields.Char("Namespace", required=True, default="default")
    label = fields.Char("Label selector:", required=True, default="app=mailserver")
    api_url = fields.Char(string="API URL", required=True)
    api_token = fields.Char(string="API Token", required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('success', 'Successs'),
        ('fail', 'Fail'),
        ], string='Status', copy=False, index=True, default='draft', readonly=True)
    
    def check_k8s_access_rights(self):
        A = [('get','pods'),
             ('list','pods'),
             ('get','pods/log'),
             ('list','pods/log'),
             ('*','pods/exec'),
            ]
        for verb, resource in A:
            if common._check_api_rights(self.api_url, self.api_token, self.namespace, verb, resource) == False:
                return self.write({'state': 'fail'})
        return self.write({'state': 'success'})

    
    def sync_aliases(self):
        sql = 'SELECT address,goto,domain,active from alias;'
        output = common._run_sql_on_maildb(self.api_url, 
                                           self.api_token, 
                                           self.namespace, 
                                           self.label, sql)

        fields = ['name','goto','domain','active']
        records = common._get_record_data(output, fields)
        
        # Cleanup all active/inactive alias records
        all_aliases = self.env['mail_reset.aliases'].with_context(active_test=False).search([])
        for alias in all_aliases:
            alias.unlink()

        for data in records:
            if data['name'] == '':
                data['name'] = '*'
            data['goto'] = common._comma_to_newline(data['goto'])
            data['domain'] = self.env['mail_reset.domain'].search([('name','=', data['domain'])]).id
            alias = self.env['mail_reset.aliases'].create(data)
            if alias:
                print(f"{alias.id}: {alias.name}@{alias.domain.name} created")
