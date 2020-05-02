# -*- coding: utf-8 -*-
from odoo import http
# from ..mail_reset import mail_resset_users.Mail_Reset_Users

class MailReset(http.Controller):
    
    @http.route('/test-url', type='http', auth='public', website=True, csrf=False)
    def test_url(self, **kw):
        return http.request.env['mail_reset.users'].say_hello()
    
    def _get_user(self, email):
        domain = email.split('@')[1]
        username = email.split('@')[0]
        username = http.request.env['mail_reset.users'].search([
            ('username','=', username),
            ('active','=', True),
            ('domain','=',domain)],limit=1)
        return username
    
    def _email_registered(self, email):
        if self._get_user(email):
            return True
        else:
            return False
    
    @http.route('/mail_reset/ask', type='http', auth='public', website=True, csrf=False)
    def reset_form(self, **kw):
        email = kw.get('email')
        return http.request.render('mail_reset.some-id')

    @http.route('/mail_reset/submit', methods=['POST'], type='http', auth='public', website=True, csrf=True)
    def reset_form_submit(self, **kw):
        email = kw.get('email')
        if self._email_registered(email):
            user = self._get_user(email)
            user.reset_mail_password()
            return user.send_reset_email()[0]
#             return f"Reset instructions has been sent to your recovery email"
        else:
            return f"{email} is not registered"
            
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