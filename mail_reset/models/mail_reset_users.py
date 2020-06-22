# -*- coding: utf-8 -*-

from odoo import models, exceptions, fields, api, _
from odoo.exceptions import Warning
from . import common

import werkzeug.urls

from datetime import datetime, timedelta
import crypt

class Mail_Reset_Users(models.Model):
    _name = 'mail_reset.users'
    _description = "Mail Users"

    name = fields.Char(string="Full Name", required=True)
    active = fields.Boolean(string="Active", default=True)
    domain = fields.Many2one('mail_reset.domain', string="Domain", required=True)
    recovery_email = fields.Char(string="Recovery email", required=True, stored=True)
    quota = fields.Integer(string="Quota (Mb):")
    email = fields.Char(string='Email', compute="_set_email", readonly=True)
    token = fields.Char(copy=False)
    reset_expiration = fields.Datetime(copy=False, readonly=True)
    reset_valid = fields.Boolean(compute='_compute_reset_valid', string='Reset Token is Valid', default=False, readonly=True)
    reset_url = fields.Char(string='Reset URL', readonly=True)
    username = fields.Char(string="Username", copy=False, required=True)
    
#     _sql_constraints = [ ('email_unique','UNIQUE(email)','Email must be unique') ]

    def _compute_reset_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        query = dict()
        route = 'reset_password'
        fragment = dict()
        if self.reset_valid:
            self.reset_prepare()
        else:
            return None
        if self.token:
            query['token'] = self.token
            self.reset_url = werkzeug.urls.url_join(base_url, "/mail_reset/%s?%s" % (route, werkzeug.urls.url_encode(query)))

    def reset_cancel(self):
        return self.write({'token': False, 'reset_expiration': False, 'reset_url': False})

    def reset_prepare(self):
        expiration = datetime.now() + timedelta(hours=24)
        for partner in self:
            if expiration or not partner.reset_valid:
                token = common._random_token()
                while self._reset_retrieve_partner(token):
                    token = common._random_token()
                partner.write({'token': token, 'reset_expiration': expiration})
        return True

    @api.depends('token', 'reset_expiration')
    def _compute_reset_valid(self):
        dt = common.now()
        for partner, partner_sudo in zip(self, self.sudo()):
            partner.reset_valid = bool(partner.token) and \
            (not partner_sudo.reset_expiration or dt <= partner_sudo.reset_expiration)

            
    @api.model
    def _reset_retrieve_partner(self, token):
        partner = self.search([('token', '=', token)], limit=1)
        if not partner:
            return False
        if not partner.reset_valid:
            return False
        return partner
                
    @api.depends('domain','username')
    def _set_email(self):
        for record in self:
            if record.domain and record.username:
                email = f'{record.username}@{record.domain.name}'
                record.email = email
            else:
                record.email = ""

    @api.model
    def create(self, vals):
        res = super(Mail_Reset_Users, self).create(vals)
        for rec in self:
            rec._set_email()
        return res
                
    def _create_mail_user(self):
        
        random_password = common._generate_password()
        sql = 'INSERT mailbox (name,username,email_other,password,maildir,local_part,domain,quota) VALUES("{name}","{email}","{recovery_email}","{password}","{maildir}","{username}","{domain}","{quota}");INSERT alias (address,goto,domain) VALUES("{email}","{email}","{domain}");'.format(
            name=self.name,
            email=self.email,
            password=random_password,
            recovery_email=self.recovery_email,
            username=self.username,
            maildir=f'{self.domain.name}/{self.username}/',
            domain=self.domain.name,
            quota=common._calculate_quota_value(self.quota)
        )
        
        common._run_sql_on_maildb(self.domain.api_url, self.domain.api_token, self.domain.namespace, self.domain.label, sql)

    def _remove_mail_user(self):
        sql = 'DELETE from mailbox WHERE username="{username}";DELETE from alias WHERE goto="{username}";'.format(username=self.email)
        
        common._run_sql_on_maildb(self.domain.api_url, self.domain.api_token, self.domain.namespace, self.domain.label, sql)
        
    def _update_mail_user(self):
        sql = 'UPDATE mailbox SET name="{name}", email_other="{recovery_email}", active={active}, quota="{quota}" WHERE username="{username}";'.format(
            username=self.email,
            name=self.name,
            recovery_email=self.recovery_email,
            quota=common._calculate_quota_value(self.quota),
            active=self.active
        )
        
        common._run_sql_on_maildb(self.domain.api_url, self.domain.api_token, self.domain.namespace, self.domain.label, sql)
    
    def _pull_rebase(self):
        pass

    def reset_mail_password(self, password):

        password_hashed = crypt.crypt(password).replace('$','\$')
        username = self.email
        sql = 'UPDATE mailbox SET password="{password}" WHERE username="{username}";'.format(password=password_hashed,username=username)

        common._run_sql_on_maildb(self.domain.api_url, self.domain.api_token, self.domain.namespace, self.domain.label, sql)

    def send_reset_email(self):
        if not self.reset_valid:
            raise Warning(_('Reset is not valid for this user!'))
        self._compute_reset_url()
        template = self.env['ir.model.data'].get_object('mail_reset','mail_users_reset_password')
        if template.sudo().send_mail(self.id,force_send=True):
            return True
        else:
            return False
    
    @api.model
    def create(self, vals):
        record = super(Mail_Reset_Users, self).create(vals)
        record._create_mail_user()
        return record

#     def unlink(self):
#         raise Warning('Cannot remove mail user! Please instead archive the record')
        
    def write(self, vals):
        res = super(Mail_Reset_Users, self).write(vals)
        self._update_mail_user()
        return res
