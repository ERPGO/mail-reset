# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Mail_Reset_Request(models.Model):
    _name = 'mail_reset.request'

    name = fields.Char()