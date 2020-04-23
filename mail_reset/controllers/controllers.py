# -*- coding: utf-8 -*-
from odoo import http

class MailReset(http.Controller):
    @http.route('/mail_reset/ask', type='http', auth='public', website=True, csrf=False)
    def index(self, **kw):
        email = kw.get('email')
        return email
    
#     @http.route('/mail_reset/mail_reset/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('mail_reset.listing', {
#             'root': '/mail_reset/mail_reset',
#             'objects': http.request.env['mail_reset.mail_reset'].search([]),
#         })

#     @http.route('/mail_reset/mail_reset/objects/<model("mail_reset.mail_reset"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mail_reset.object', {
#             'object': obj
#         })