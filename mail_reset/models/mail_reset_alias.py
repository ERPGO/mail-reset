from odoo import models, exceptions, fields, api, _
from odoo.exceptions import Warning, ValidationError
from . import common

class Mail_Reset_Aliases(models.Model):
    _name = 'mail_reset.aliases'
    _description = "Mail Aliases"
    
    active = fields.Boolean(string="Active", default=True)
    goto = fields.Text(string="Forward to:", required=True)
    domain = fields.Many2one('mail_reset.domain', string="Domain", required=True)
    name = fields.Char(string="Address", required=True)

    def _create_user_alias(self):
        sql = 'INSERT alias (address,goto,domain) VALUES("{address}","{goto}","{domain}");'.format(
            address=f'{self.name}@{self.domain.name}',
            goto=common._newline_to_comma(self.goto),
            domain=self.domain.name
        )
        
        common._run_sql_on_maildb(self.domain.api_url, self.domain.api_token, self.domain.namespace, self.domain.label, sql)

    def _update_user_alias(self):
        sql = 'UPDATE alias SET goto="{goto}", active={active} WHERE address="{address}";'.format(
            address=f'{self.name}@{self.domain.name}',
            goto=common._newline_to_comma(self.goto),
            active=self.active
        )

        common._run_sql_on_maildb(self.domain.api_url, self.domain.api_token, self.domain.namespace, self.domain.label, sql)

    @api.constrains('name')
    def _check_address(self):
        if common._is_username(self.name):
            raise ValidationError('Address is invalid!')
        
    @api.model
    def create(self, vals):
        record = super(Mail_Reset_Aliases, self).create(vals)
        record._create_user_alias()
        return record

    def write(self, vals):
        res = super(Mail_Reset_Aliases, self).write(vals)
        self._update_user_alias()
        return res
