# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Mail_Reset_Users(models.Model):
    _name = 'mail_reset.users'

    name = fields.Char(string="Full Name")
    username = fields.Char(string="Username")
    domain = fields.Many2one('mail_reset.domain', string="Domain")
    recovery_email = fields.Char(string="Recovery email")