import requests
from datetime import datetime, timedelta
from odoo.exceptions import Warning
import re 
import random
from kubernetes import client, config
from kubernetes.stream import stream

def _check_api_rights(api_url, api_token, namespace, verb, resource):
    hed = {'Authorization': 'Bearer ' + api_token}
    data = {"kind":"SelfSubjectAccessReview",
            "apiVersion":"authorization.k8s.io/v1",
            "metadata":{"creationTimestamp":None},
            "spec":{"resourceAttributes":{
                "namespace":namespace,
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
    
def now(**kwargs):
    return datetime.now() + timedelta(**kwargs)

def _random_token():
    # the token has an entropy of about 120 bits (6 bits/char * 20 chars)
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return ''.join(random.SystemRandom().choice(chars) for _ in range(20))

def _generate_password():
    s = "abcdefghijklmnopqrstuvwxyz01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()?"
    passlen = 8
    p =  "".join(random.sample(s,passlen ))
    return p

def _email_is_valid(email): 
    regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
    if re.search(regex, email):
        return True
    else:
        return False

def _newline_to_comma(string):
    return string.replace("\n", ",").strip()

def _is_username(username):
    regex = '[@]'
    if re.search(regex, username):
        return True
    else:
        return False
    
def _get_k8s_conf(api_url, api_token):
    configuration = client.Configuration()
    configuration.api_key["authorization"] = api_token
    configuration.api_key_prefix['authorization'] = 'Bearer'
    configuration.host = api_url
    configuration.verify_ssl = False
    return configuration

def _get_pods(api_url, api_token, namespace, label):
    configuration = _get_k8s_conf(api_url,api_token)
    v1 = client.CoreV1Api(client.ApiClient(configuration))
    pod_list = v1.list_namespaced_pod(namespace, pretty=False, label_selector=label)
    return pod_list


def _get_maildb_name(api_url, api_token, namespace, label):
    pod_list = _get_pods(api_url, api_token, namespace, label)
    for item in pod_list.items:
        if 'mariadb' in item.metadata.name:
            return item.metadata.name
    return False


def _run_sql_on_maildb(api_url, api_token, namespace, label, sql):
    configuration = _get_k8s_conf(api_url,api_token)
    v1 = client.CoreV1Api(client.ApiClient(configuration))
    sql_command = f"mysql -u postfix -p$MYSQL_PASSWORD -D postfix -e '{sql}'"
    print(sql_command)
    exec_command = [
        '/bin/bash',
        '-c',
        sql_command,
        ]

    c = configuration
    c.assert_hostname = False

    name = _get_maildb_name(api_url, api_token, namespace, label)

    resp = stream(v1.connect_get_namespaced_pod_exec,
                  name,
                  namespace,
                  command=exec_command,
                  stderr=True, stdin=False,
                  stdout=True, tty=False)

    return print(resp)
