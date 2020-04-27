# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Mail_Reset_Domain(models.Model):
    _name = 'mail_reset.domain'
    _description = 'Mail Domain'

    name = fields.Char(string="Domain name")
    contact = fields.Many2one('res.partner', string="Contact")
    api_url = fields.Char(string="API URL")
    api_token = fields.Char(string="API Token")
    host = fields.Char(string="Host")
    database = fields.Char(string="Database") 
    user = fields.Char(string="User")
    password = fields.Char(string="Password")
    
    #this is for minimum "." symbol requirement in name field
#     if not any(char.isdigit() for char in passwd): 
#         print('Password should have at least one numeral') 
#         val = False