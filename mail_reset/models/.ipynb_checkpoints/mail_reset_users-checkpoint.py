# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Mail_Reset_Users(models.Model):
    _name = 'mail_reset.users'

    name = fields.Char()