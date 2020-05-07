# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning

import requests


def _check_api_rights(api_token, api_url, verb, resource):
    hed = {'Authorization': 'Bearer ' + api_token}
    data = {"kind":"SelfSubjectAccessReview",
            "apiVersion":"authorization.k8s.io/v1",
            "metadata":{"creationTimestamp":None},
            "spec":{"resourceAttributes":{
                "namespace":"default",
                "verb": verb,
                "resource":resource}},
            "status":{"allowed":False}}
        
        
    url = f'{api_url}/apis/authorization.k8s.io/v1/selfsubjectaccessreviews'
    response = requests.post(url, json=data, headers=hed, verify=False)
    output = response.json()
    if output['status'] == 'Failure':
        raise Warning('You are NOT authorized!')
    else:
        return output['status']['allowed']


class Mail_Reset_Domain(models.Model):
    _name = 'mail_reset.domain'
    _description = 'Mail Domain'

    name = fields.Char(string="Domain name", required=True)
    contact = fields.Many2one('res.partner', string="Contact")
    api_url = fields.Char(string="API URL", required=True)
    api_token = fields.Char(string="API Token", required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('success', 'Successs'),
        ('fail', 'Fail'),
        ], string='Status', copy=False, index=True, default='draft', readonly=True)

    def _check_api_rights(self, verb, resource):
        hed = {'Authorization': 'Bearer ' + self.api_token}
        data = {"kind":"SelfSubjectAccessReview",
                "apiVersion":"authorization.k8s.io/v1",
                "metadata":{"creationTimestamp":None},
                "spec":{"resourceAttributes":{
                    "namespace":"default",
                    "verb": verb,
                    "resource":resource}},
                "status":{"allowed":False}}


        url = f'{self.api_url}/apis/authorization.k8s.io/v1/selfsubjectaccessreviews'
        response = requests.post(url, json=data, headers=hed, verify=False)
        output = response.json()
        if output['status'] == 'Failure':
            self.write({'state': 'fail'})
            return False
        else:
            return output['status']['allowed']
    
    @api.one    
    def check_k8s_access_rights(self):
        A = [('get','pods'),
             ('list','pods'),
             ('get','pods/log'),
             ('list','pods/log'),
             ('*','pods/exec'),
            ]
        for verb, resource in A:
            if self._check_api_rights(verb,resource) == False:
                return self.write({'state': 'fail'})
        return self.write({'state': 'success'})



        