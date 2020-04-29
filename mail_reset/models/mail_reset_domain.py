# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Mail_Reset_Domain(models.Model):
    _name = 'mail_reset.domain'
    _description = 'Mail Domain'

    name = fields.Char(string="Domain name")
    contact = fields.Many2one('res.partner', string="Contact")
    api_url = fields.Char(string="API URL")
    api_token = fields.Char(string="API Token")
    status = fields.Selection(string="Status")
    
    #this is for minimum "." symbol requirement in name field
#     if not any(char.isdigit() for char in pawsswd): 
#         print('Password should have at least one numeral') 
#         val = False


verb = "*"
resource = "pods/exec"

def check_api_rights(api_token, api_url, verb, resource):
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
    return output['status']['allowed']

def _check_access_rights(ACCESS_LIST):
    for verb, resource in A:
        if check_api_rights(api_token,api_url,verb,resource) == False:
            return False
    return True



        