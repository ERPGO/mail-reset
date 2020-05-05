# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.exceptions import UserError
import werkzeug
import time

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
    def reset_ask_form(self, **kw):
        email = kw.get('email')
        return http.request.render('mail_reset.some-id')

    @http.route('/mail_reset/reset_password', type='http', auth='public', website=True, sitemap=False)
    def reset_mail_password_form(self, **kw):
        qcontext = http.request.params.copy()
        if not qcontext.get('token'):
            raise werkzeug.exceptions.NotFound()
        token = qcontext.get('token')
        user = http.request.env['mail_reset.users'].sudo()._reset_retrieve_partner(token)
        if not user:
            raise werkzeug.exceptions.NotFound()
        qcontext['email'] = user.email
        qcontext['name'] = user.name
        try:
            if http.request.httprequest.method == 'POST':
                values = { key: qcontext.get(key) for key in ('email', 'name', 'password') }
                if not values:
                    raise UserError(_("The form was not properly filled in."))
                if values.get('password') != qcontext.get('confirm_password'):
                    raise UserError(_("Passwords do not match; please retype them."))
                user = http.request.env['mail_reset.users'].sudo()._reset_retrieve_partner(token)
                if not user or (user and not user.reset_valid):
                    raise werkzeug.exceptions.NotFound()
                user.reset_mail_password(qcontext.get('password'))
                qcontext['message'] = 'Your email password has been reset successfully!'
#                 time.sleep(5)
#                 return werkzeug.utils.redirect(f'https://webmail.{user.domain.name}')
        except UserError as e:
            qcontext['error'] = e.name or e.value
        except Exception as e:
            qcontext['error'] = str(e)

        response = http.request.render('mail_reset.reset_password', qcontext)
        response.headers['X-Frame-Options'] = 'DENY'
        return response
            

    @http.route('/mail_reset/submit', methods=['POST'], type='http', auth='public', website=True, csrf=True)
    def reset_form_submit(self, **kw):
        email = kw.get('email')
        if self._email_registered(email):
            user = self._get_user(email)
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