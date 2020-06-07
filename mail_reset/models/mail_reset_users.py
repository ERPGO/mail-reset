# -*- coding: utf-8 -*-

from odoo import models, exceptions, fields, api, _
from odoo.tools import pycompat
from odoo.exceptions import Warning

import werkzeug.urls

from datetime import datetime, timedelta
import crypt
import random

from kubernetes import client, config
from kubernetes.stream import stream

def now(**kwargs):
    return datetime.now() + timedelta(**kwargs)

def random_token():
    # the token has an entropy of about 120 bits (6 bits/char * 20 chars)
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return ''.join(random.SystemRandom().choice(chars) for _ in range(20))

def _generate_password():
    s = "abcdefghijklmnopqrstuvwxyz01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()?"
    passlen = 8
    p =  "".join(random.sample(s,passlen ))
    return p

def _get_k8s_conf(api_url, api_token):
    configuration = client.Configuration()
    configuration.api_key["authorization"] = api_token
    configuration.api_key_prefix['authorization'] = 'Bearer'
    configuration.host = api_url
    configuration.verify_ssl = False
    return configuration

def _get_pods(api_url, api_token, label):  
    configuration = _get_k8s_conf(api_url,api_token)
    v1 = client.CoreV1Api(client.ApiClient(configuration))
    pod_list = v1.list_namespaced_pod("default", pretty=False, label_selector=label)
    return pod_list


class Mail_Reset_Users(models.Model):
    _name = 'mail_reset.users'
    _description = "Mail Users"

    name = fields.Char(string="Full Name", required=True)
    active = fields.Boolean(string="Active", default=True)
    username = fields.Char(string="Username", required=True)
    domain = fields.Many2one('mail_reset.domain', string="Domain", required=True)
    recovery_email = fields.Char(string="Recovery email", required=True, stored=True)
    quota = fields.Integer(string="Quota (Mb):")
    email = fields.Char(string='Email', compute="_set_email", readonly=True)
    token = fields.Char(copy=False)
    reset_expiration = fields.Datetime(copy=False, readonly=True)
    reset_valid = fields.Boolean(compute='_compute_reset_valid', string='Reset Token is Valid', default=False, readonly=True)
    reset_url = fields.Char(string='Reset URL', readonly=True)

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
                token = random_token()
                while self._reset_retrieve_partner(token):
                    token = random_token()
                partner.write({'token': token, 'reset_expiration': expiration})
        return True

    @api.depends('token', 'reset_expiration')
    def _compute_reset_valid(self):
        dt = now()
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
                
    def _get_maildb_name(self):
        api_url = self.domain.api_url
        api_token = self.domain.api_token
        label = "app=mailserver"
        
        pod_list = _get_pods(api_url, api_token, label)
        for item in pod_list.items:
            if 'mariadb' in item.metadata.name:
                return item.metadata.name
        return False

    def _calculate_quota_value(self):
        value = self.quota * 1024000
        return value

    def _run_sql_on_maildb(self, sql):
        api_url = self.domain.api_url
        api_token = self.domain.api_token
        configuration = _get_k8s_conf(api_url,api_token)
        v1 = client.CoreV1Api(client.ApiClient(configuration))
        sql_command = f"mysql -u postfix -p$MYSQL_PASSWORD -D postfix -e '{sql}'"
        print(sql_command)
        exec_command = [
            '/bin/bash',
            '-c',
            sql_command,
            ]

        c = configuration
        c.assert_hostname = False

        name = self._get_maildb_name()

        resp = stream(v1.connect_get_namespaced_pod_exec,
                      name,
                      'default',
                      command=exec_command,
                      stderr=True, stdin=False,
                      stdout=True, tty=False)
        
        return "Response: " + resp

    def _create_mail_user(self):
        random_password = _generate_password()
        sql = 'INSERT mailbox (name,username,email_other,password,maildir,local_part,domain,quota) VALUES("{name}","{email}","{recovery_email}","{password}","{maildir}","{username}","{domain}","{quota}");INSERT alias (address,goto,domain) VALUES("{email}","{email}","{domain}");'.format(
            name=self.name,
            email=self.email,
            password=random_password,
            recovery_email=self.recovery_email,
            username=self.username,
            maildir=f'{self.domain.name}/{self.username}/',
            domain=self.domain.name,
            quota=self._calculate_quota_value()
        )
        self._run_sql_on_maildb(sql)

    def _remove_mail_user(self):
        sql = 'DELETE from mailbox WHERE username="{username}";DELETE from alias WHERE goto="{username}";'.format(username=self.email)
        
        self._run_sql_on_maildb(sql)
        
    def _update_mail_user(self):
        sql = 'UPDATE mailbox SET name="{name}", email_other="{recovery_email}", quota="{quota}" WHERE username="{username}";'.format(
            username=self.email,
            name=self.name,
            recovery_email=self.recovery_email,
            quota=self._calculate_quota_value()
        )
        self._run_sql_on_maildb(sql)
        
    def reset_mail_password(self, password):

        password_hashed = crypt.crypt(password).replace('$','\$')
        username = self.email
        sql = 'UPDATE mailbox SET password="{password}" WHERE username="{username}";'.format(password=password_hashed,username=username)

        self._run_sql_on_maildb(sql)

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

    def unlink(self):
        for rec in self:
            rec._remove_mail_user()
        super(Mail_Reset_Users, self).unlink()
        
    def write(self, vals):
        res = super(Mail_Reset_Users, self).write(vals)
        self._update_mail_user()
        return res
