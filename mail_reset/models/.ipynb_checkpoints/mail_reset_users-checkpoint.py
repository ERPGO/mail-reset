# -*- coding: utf-8 -*-

from odoo import models, exceptions, fields, api, _
from datetime import datetime, timedelta
import crypt
import random

from kubernetes import client, config
from kubernetes.stream import stream


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

#     token = fields.Char(copy=False, groups="base.group_erp_manager")
#     reset_expiration = fields.Datetime(copy=False, groups="base.group_erp_manager")
#     reset_valid = fields.Boolean(compute='_compute_reset_valid', string='Reset Token is Valid')
#     reset_url = fields.Char(compute='_compute_reset_url', string='Reset URL')

    
#     @api.multi
#     def reset_cancel(self):
#         return self.write({'token': False, 'reset_expiration': False})

#     @api.multi
#     def reset_prepare(self):
#         expiration = datetime.(now) + timedelta(hours=24)
#         for partner in self:
#             if expiration or not partner.reset_valid:
#                 token = random_token()
#                 while self._signup_retrieve_partner(token):
#                     token = random_token()
#                 partner.write({'token': token, 'expiration': expiration})
#         return True

#     @api.multi
#     @api.depends('token', 'reset_expiration')
#     def _compute_reset_valid(self):
#         dt = now()
#         for partner, partner_sudo in pycompat.izip(self, self.sudo()):
#             partner.reset_valid = bool(partner.token) and \
#             (not partner.reset_expiration or dt <= partner.reset_expiration)

            
#     @api.model
#     def _signup_retrieve_partner(self, token):
#         partner = self.search([('token', '=', token)], limit=1)
#         if not partner:
#             if raise_exception:
#                 raise exceptions.UserError(_("Reset token '%s' is not valid") % token)
#             return False
#         if  not partner.reset_valid:
#             if raise_exception:
#                 raise exceptions.UserError(_("Reset token '%s' is no longer valid") % token)
#             return False
#         return partner
            
            
    name = fields.Char(string="Full Name")
    username = fields.Char(string="Username")
    domain = fields.Many2one('mail_reset.domain', string="Domain")
    recovery_email = fields.Char(string="Recovery email")
    email = fields.Char(string='Email', compute="_set_email", readonly=True)
    
    @api.depends('domain','username')
    def _set_email(self):
        if self.domain and self.username:
            email = f'{self.username}@{self.domain.name}'
            self.email = email

    @api.model
    def create(self, vals):
        res = super(Mail_Reset_Users, self).create(vals)
        res._set_email()
        return res
                
    def _get_maildb_name(self):
        api_url = self.domain.api_url
        api_token = self.domain.api_token
        label = "app=mailserver"
        
        pod_list = _get_pods(api_url, api_token, label)
        for item in pod_list.items:
            if 'mariadb' in item.metadata.name:
                return item.metadata.name 

    def say_hello(self):
        return "Hello"
    
    @api.one
    def reset_mail_password(self):
        api_url = self.domain.api_url
        api_token = self.domain.api_token

        random_temp_password = _generate_password()
        temp_pass_hashed = crypt.crypt(random_temp_password)
        temp_pass = temp_pass_hashed.replace('$','\$')
        username = self.email
        sql = 'UPDATE mailbox SET password="{password}" WHERE username="{username}";'.format(password=temp_pass,username=username)

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
        
        print("Response: " + resp)
        return f"New Password is: {str(random_temp_password)}"
