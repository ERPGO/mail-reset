# -*- coding: utf-8 -*-

from . import common
from odoo import models, fields, api
from odoo.exceptions import Warning, ValidationError


class Mail_Reset_Domain(models.Model):
    _name = 'mail_reset.domain'
    _description = 'Mail Domain'

    name = fields.Char(string="Domain name", required=True)
    contact = fields.Many2one('res.partner', string="Contact")
    namespace = fields.Char("Namespace", required=True, default="default")
    label = fields.Char("Label selector:", required=True, default="app=mailserver")
    api_url = fields.Char(string="API URL", required=True)
    api_token = fields.Char(string="API Token", required=True)
    last_status = fields.Text(string="Last status info:", readonly=True, default='Never Connected!')
    first_connection = fields.Boolean(string="First connection", default=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('success', 'Successs'),
        ('fail', 'Fail'),
        ], string='Status', copy=False, index=True, default='draft', readonly=True)
    

    users_count = fields.Integer(string="Users count", compute="_count_mailboxes")
    aliases_count = fields.Integer(string="Aliases count", compute="_count_aliases")
    
    
    _sql_constraints = [ ('name_unique','UNIQUE(name)','Domain name must be unique') ]
    
    def _count_mailboxes(self):
        results = self.env['mail_reset.users'].read_group([('domain', 'in', self.ids)], ['domain'], ['domain'])
        dic = {}
        for x in results:
            dic[x['domain'][0]] = x['domain_count']
        for record in self:
            record['users_count'] = dic.get(record.id, 0)

    def _count_aliases(self):
        results = self.env['mail_reset.aliases'].read_group([('domain', 'in', self.ids)], ['domain'], ['domain'])
        dic = {}
        for x in results:
            dic[x['domain'][0]] = x['domain_count']
        for record in self:
            record['aliases_count'] = dic.get(record.id, 0)

    @api.constrains('name')
    def _fix_name(self):
        if not "." in self.name:
            raise ValidationError('Name should be domain like "example.com"')
    
    def _sync_aliases(self):
        sql = f'SELECT address,goto,domain,active from alias WHERE domain = "{self.name.lower()}";'
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
            data['name'] = data['name'].split('@')[0]
            if data['name'] == '':
                data['name'] = '*'
            data['goto'] = common._comma_to_newline(data['goto'])
            data['domain'] = self.env['mail_reset.domain'].search([('name','=', data['domain'])] ,limit=1).id
            
            alias = self.env['mail_reset.aliases'].create(data)
            
            if alias:
                print(f"{alias.id}: {alias.name}@{alias.domain.name} created")

    def _sync_mailboxes(self):
        sql = f'SELECT name,email_other,local_part,domain,quota,active from mailbox WHERE domain = "{self.name.lower()}";'
        output = common._run_sql_on_maildb(self.api_url, 
                                           self.api_token, 
                                           self.namespace, 
                                           self.label, sql)

        fields = ['name','recovery_email','username','domain','quota','active']
        records = common._get_record_data(output, fields)

        # Cleanup all active/inactive mailbox records
        all_mailboxes = self.env['mail_reset.users'].with_context(active_test=False).search([])
        for mailbox in all_mailboxes:
            mailbox.unlink()

        for data in records:
            data['quota'] = common._reverse_quota_value(int(data['quota']))
            data['domain'] = self.env['mail_reset.domain'].search([('name','=', data['domain'])] ,limit=1).id

            mailbox = self.env['mail_reset.users'].create(data)

            if mailbox:
                print(f"{mailbox.id}: {mailbox.name}@{mailbox.domain.name} created")

    def _domain_active_in_db(self):
        sql = f'SELECT * from domain where ( domain = "{self.name.lower()}" AND active = 1);'
        output = common._run_sql_on_maildb(self.api_url, 
                                       self.api_token, 
                                       self.namespace, 
                                       self.label, sql)
        if output:
            return True
        return False
            
    def check_k8s_access(self):
        A = [('get','pods'),
             ('list','pods'),
             ('get','pods/log'),
             ('list','pods/log'),
             ('*','pods/exec'),
            ]
        for verb, resource in A:
            if common._check_api_rights(self.api_url, self.api_token, self.namespace, verb, resource) == False:
                MESSAGE = "Connection is BROKEN!"
                return self.write({'state': 'fail', 'last_status': MESSAGE})
        if self._domain_active_in_db():
            MESSAGE = "Connection was successfull!"
            return self.write({'state': 'success','first_connection': 1, 'last_status': MESSAGE})
        else:
            MESSAGE = f"Domain: {self.name.lower()} => doesn't exist or Inactive in database!"
            return self.write({'state': 'fail', 'last_status': MESSAGE})

    def sync_domain(self):
        self.check_k8s_access()
        if self.state == 'success':
            self._sync_mailboxes()
            self._sync_aliases()
            
    @api.model
    def create(self, vals):
        record = super(Mail_Reset_Domain, self).create(vals)
        record.name = record.name.lower()
        return record
