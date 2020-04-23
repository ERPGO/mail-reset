# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Mail_Reset_Domain(models.Model):
    _name = 'mail_reset.domain'

    name = fields.Char()
