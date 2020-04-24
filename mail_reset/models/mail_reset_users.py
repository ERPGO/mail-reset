# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Mail_Reset_Users(models.Model):
    _name = 'mail_reset.users'
    _description = "Users"

    name = fields.Char(string="Full Name")
    username = fields.Char(string="Username")
    domain = fields.Many2one('mail_reset.domain', string="Domain")
    recovery_email = fields.Char(string="Recovery email")
    email = fields.Char(string='Email', readonly=True)
    
    @api.onchange('domain','username')
    def _set_email(self):
        if self.domain and self.username:
            email = f'{self.username}@{self.domain.name}'
            self.email = email