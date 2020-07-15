# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.exceptions import UserError
import werkzeug
import time

from ..models import common

class MailReset(http.Controller):
        
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
                if not common._get_pod_name(user.domain.api_url, user.domain.api_token, user.domain.namespace, user.domain.label):
                    raise UserError(_("Something went wrong!"))
                user.reset_mail_password(qcontext.get('password'))
                qcontext['message'] = 'Your email password has been reset successfully!'
                return werkzeug.utils.redirect(f'https://webmail.{user.domain.name}')
        except UserError as e:
            qcontext['error'] = e.name or e.value
        except Exception as e:
            qcontext['error'] = str(e)

        response = http.request.render('mail_reset.reset_password', qcontext)
        response.headers['X-Frame-Options'] = 'DENY'
        return response
            

    @http.route('/mail_reset/submit', type='http', auth='public', website=True, csrf=True)
    def reset_form_submit(self, **kw):
        qcontext = http.request.params.copy()
        try:
            if http.request.httprequest.method == 'POST':
                email = qcontext.get('email')
                if not email:
                    raise UserError(_("The form was not properly filled in!"))
                elif not common._email_is_valid(email):
                    raise UserError(_("Please enter valid email address!"))
                elif not self._email_registered(email):
                    raise UserError(_(f"{email} is not registered!"))
                user = self._get_user(email)
                user.sudo().reset_prepare()
                if not user.sudo().send_reset_email():
                    raise UserError(_("Something went wrong!"))
                qcontext['message'] = 'Reset instructions has been sent to your recovery email address!'
        except UserError as e:
            qcontext['error'] = e.name or e.value
        except Exception as e:
            qcontext['error'] = str(e)

        response = http.request.render('mail_reset.ask_form', qcontext)
        response.headers['X-Frame-Options'] = 'DENY'
        return response
