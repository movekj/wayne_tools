import requests
import os
import yaml
import json
import argparse
from termcolor import colored

class WayneApi:
    def __init__(self, namespace, app_name, project_name, k8s_cluser_name, image, debug=False):
        self.app_name = app_name
        self.namespace = namespace
        self.project_name = project_name
        self.image = image
        self.service_name = project_name
        self.ingress_name = project_name
        self.debug = debug
        self.username = os.environ['WAYNE_USERNAME'] 
        self.password = os.environ['WAYNE_PASSWORD']
        self.wayne_url = os.environ['WAYNE_URL']
        self.k8s_cluser_name = k8s_cluser_name

        self.token_file = '%s/.wayne_token' % os.environ['HOME']
        self.namespace_id = self.get_namespace_id_by_name(self.namespace)
        self.app_id = self.get_app_id_by_name(self.namespace_id, self.app_name)
        self.project_id = self.get_project_id_id_by_name(self.namespace, self.app_id, self.project_name)

    def login(self):
        resp = requests.get('%s/login/ldap?username=%s&password=%s'  % (self.wayne_url, self.username, self.password))
        token =  resp.json()['data']['token']
        with open(self.token_file, 'w') as f:
            f.write(token)
        return token

    def get_token(self):
        if os.path.isfile(self.token_file):
            with open(self.token_file) as f:
                token = f.read()
        else:
            token = self.login()
        return token

    def get_yaml_content(self, file_path):
        with open(file_path) as f:
            try:
                content = yaml.load(f.read())
                return content
            except Exception:
                return False

    def request_wayne(self, uri, method='post', payload=None):
        request = getattr(requests,  method)    
        token = self.get_token()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % token
        }
        request_url = self.wayne_url + uri
        if self.debug:
            print 'url: %s, method: %s, payload: %s ' % (request_url, method, json.dumps(payload))
        if method == 'post':
            resp = request(request_url, json=payload, headers=headers)
            if resp.status_code == 401:
                token = self.login()
                headers['Authorization'] = 'Bearer %s' % token
                resp = request(request_url, json=payload, headers=headers)
        elif method == 'get':
            resp = request(request_url, headers=headers)
            if resp.status_code == 401:
                token = self.login()
                headers['Authorization'] = 'Bearer %s' % token
                resp = request(request_url, json=payload, headers=headers)
        return resp

    def  create_namespace(self, namespace):
        payload = self.get_yaml_content('wayne_namespace.yml')
        metaData =payload['metaData']
        metaData['namespace'] = namespace
        payload['kubeNamespace'] = namespace
        payload['name'] = namespace
        payload['metaDataObj']['namespace'] = namespace
        payload['metaData'] = json.dumps(metaData)
        resp = self.request_wayne(
            '/api/v1/namespaces',
            'post',
            payload
        )
        print resp.json()
        data = resp.json()['data']
        self.request_wayne(
            '/api/v1/kubernetes/namespaces/%s/clusters/%s' % (self.namespace, self.k8s_cluser_name),
            'post',
            {}
        )
        return data['id']

    def create_project(self, namespace_id, project_name):
        payload = self.get_yaml_content('wayne_project.yml')
        payload['name'] = project_name
        payload['namespace']['id'] = namespace_id
        payload['metaData'] = json.dumps(payload['metaData'])
        resp = self.request_wayne(
            '/api/v1/namespaces/%s/apps' %  namespace_id,
            'post',
            payload
        )
        data = resp.json()['data']
        return data['id']

    def create_project_deployment(self, namespace, project_name, project_id):
        payload = self.get_yaml_content('wayne_deployment.yml')
        payload['metaData'] = json.dumps(payload['metaData'])
        payload['name'] = namespace + '.' + project_name
        payload['appId'] = project_id
        resp = self.request_wayne(
            '/api/v1/apps/%s/deployments' % project_id,
            'post',
            payload
        )
        data = resp.json()['data']
        return data['id']

    def create_service(self, service_name, project_id):
        payload = self.get_yaml_content('wayne_service.yml')    
        payload['metaData'] = json.dumps(payload['metaData'])
        payload['name'] = self.namespace + '.' + service_name
        payload['appId'] = project_id
        resp = self.request_wayne(
            '/api/v1/apps/%s/services' % project_id,
            'post',
            payload
        )
        print resp.text
        data = resp.json()['data']
        return data['id']

    def create_ingress(self, namespace_id, project_id, ingress_name):
        payload = self.get_yaml_content('wayne_ingress.yml')
        payload['name'] = self.namespace + '.' + ingress_name
        payload['appId'] = project_id
        payload['metaData'] = json.dumps(payload['metaData'])
        resp = self.request_wayne(
            '/api/v1/apps/%s/ingresses' % project_id,
            'post',
            payload
        )
        print resp.json()
        data = resp.json()['data']
        return data['id']
        
    def get_namespace_id_by_name(self, namespace):
        resp = self.request_wayne(
            '/currentuser',
            'get'
        )
        data = resp.json()['data']
        namespaces = data['namespaces']
        for _namespace in namespaces:
            if _namespace['name'] == namespace:
                return _namespace['id']
        return self.create_namespace(namespace)

    def get_project_id_id_by_name(self, namespace, app_id, project_name):
        resp = self.request_wayne(
            '/api/v1/apps/%s/deployments?deleted=false&relate=all&appId=%s&sortby=id' % (app_id, app_id),
            'get'
        )
        data = resp.json()['data']
        if data.get('list', None):
            for  project_deployment in data.get('list'):
                if project_deployment['name'] == namespace + '.' + project_name:
                    return project_deployment['id']
        return self.create_project_deployment(namespace, project_name, app_id)

    def get_app_id_by_name(self, namespace_id, app_name):
        resp = self.request_wayne(
            '/api/v1/namespaces/%s/apps?pageNo=1&pageSize=10000&sortby=-id&deleted=false&namespace=%s&starred=false' % (namespace_id, namespace_id),
            'get'
        )
        data = resp.json()['data']
        if data.get('list', None):
            for  app in data.get('list'):
                if app['name'] == app_name:
                    return app['id']
        return self.create_project(namespace_id, app_name)

    def get_service_id_by_name(self, app_id, service_name):
        resp = self.request_wayne(
            '/api/v1/apps/%s/services?pageNo=1&pageSize=10000&deleted=false&relate=all&appId=%s&sortby=-id' % (app_id, app_id),
            'get'
        )
        data = resp.json()['data']
        if data.get('list', None):
            for  service in data.get('list'):
                if service['name'] == namespace + '.' + service_name:
                    return service['id']
        return self.create_service(service_name, app_id)

    def get_ingress_id_by_name(self, namespace_id, app_id, ingress_name):
        resp = self.request_wayne(
            '/api/v1/apps/%s/ingresses?pageNo=1&pageSize=10000&deleted=false&relate=all&appId=%s&sortby=id' % (app_id, app_id),
            'get'
        )
        data = resp.json()['data']
        if data.get('list', None):
            for ingress in data.get('list', None):
                if ingress['name']  == namespace + '.' + ingress_name:
                    return ingress['id']
        return self.create_ingress(namespace_id, app_id, ingress_name)

    def publish_deployment(self):
        payload =  self.get_yaml_content('wayne_deployment_tpl.yml')
        template = self.get_yaml_content('k8s_deployment.yml')
        template ['metadata']['name'] = self.project_name
        template['metadata']['labels']['wayne-app'] = self.app_name
        template['metadata']['labels']['wayne-ns'] = self.namespace
        template['metadata']['labels']['app'] = self.project_name
        template['spec']['selector']['matchLabels']['app'] = self.project_name
        template['spec']['template']['metadata']['labels']['wayne-app'] = self.app_name
        template['spec']['template']['metadata']['labels']['wayne-ns'] = self.namespace
        template['spec']['template']['metadata']['labels']['app'] = self.project_name
        template['spec']['template']['spec']['containers'][0]['image'] = self.image
        template['spec']['template']['spec']['containers'][0]['name'] = self.project_name
        template['spec']['template']['spec']['containers'][0]['env'] = [
            {
                "name": "ENV", 
                "value": self.namespace
            }
         ]
        payload['name'] = self.project_name
        payload['template'] = json.dumps(template)
        payload['app']['id'] = self.app_id
        payload['app']['namespace'] = self.namespace
        payload['deploymentId'] = self.project_id
        resp = self.request_wayne(
            '/api/v1/apps/%s/deployments/tpls' % self.app_id,
            'post',
            payload
        )
        data =  resp.json()['data']
        deployment_tpl_id = data['id']
        
        template['metadata']['namespace'] = self.namespace 
        payload = template
        resp = self.request_wayne(
            '/api/v1/kubernetes/apps/%s/deployments/%s/tpls/%s/clusters/%s' % (self.app_id, self.project_id, deployment_tpl_id, self.k8s_cluser_name),
            'post',
            payload
        )
        assert resp.status_code ==  200
        print colored('app: %s, project: %s, code deploy into k8s successful' % (self.app_name, self.project_name), 'green')

    def publish_service(self):
        self.service_id = self.get_service_id_by_name(self.app_id, self.service_name)
        payload = self.get_yaml_content('wayne_service_tpl.yml')
        template = self.get_yaml_content('k8s_service.yml')
        template['metadata']['name'] = self.service_name
        template['metadata']['labels']['wayne-app'] = self.app_name
        template['metadata']['labels']['wayne-ns'] = self.namespace
        template['metadata']['labels']['app']  = self.service_name
        template['spec']['selector']['app'] =  self.project_name
        template['spec']['ports'][0]['name'] = self.service_name + '-80' 
        payload['template'] = json.dumps(template)
        payload['serviceId'] = self.service_id
        payload['service']['metaData'] = json.dumps({"clusters": [self.k8s_cluser_name]})
        payload['service']['id'] = self.service_id
        payload['service']['name'] = self.service_name
        payload['service']['app']['id'] = self.app_id
        payload['name'] = self.service_name
        resp = self.request_wayne(
            '/api/v1/apps/%s/services/tpls' % self.app_id,
            'post',
            payload
        )
        data = resp.json()['data']
        service_tpl_id = data['id']
        template['metadata']['namespace'] = self.namespace
        resp = self.request_wayne(
            '/api/v1/kubernetes/apps/%s/services/%s/tpls/%s/clusters/%s' % (self.app_id, self.service_id, service_tpl_id, self.k8s_cluser_name),
            'post',
            template
        )
        assert resp.status_code == 200
        print colored('app: %s, project: %s, loadblance deploy into k8s successful' % (self.app_name, self.project_name), 'green')


    def publish_ingress(self):
        self.ingress_id = self.get_ingress_id_by_name(self.namespace_id, self.app_id, self.ingress_name)
        template = self.get_yaml_content('k8s_ingress.yml')
        template['metadata']['name'] = self.ingress_name
        template['metadata']['labels']['wayne-app'] = self.app_name
        template['metadata']['labels']['wayne-ns'] = self.namespace
        template['metadata']['labels']['app'] = self.ingress_name
        template['spec']['rules'][0]['host'] = self.ingress_name + '.api.' + self.namespace + '.yn.cn'
        template['spec']['rules'][0]['http']['paths'][0]['backend']['serviceName'] = self.project_name
        payload = {
            "description":"rabot",
            "ingressId":6,
            "template":"",
            "name":"test"
        }
        payload['ingressId'] = self.ingress_id
        payload['template'] = json.dumps(template)
        payload['name'] = self.ingress_name
        resp = self.request_wayne(
            '/api/v1/apps/%s/ingresses/tpls' % self.app_id ,
            'post',
            payload
        )
        data = resp.json()['data']
        ingress_tpl_id = data['id']
        template['metadata']['namespace'] = namespace
        resp = self.request_wayne(
            '/api/v1/kubernetes/apps/%s/ingresses/%s/tpls/%s/clusters/%s' % (self.app_id, self.ingress_id, ingress_tpl_id, self.k8s_cluser_name),
            'post',
            template
        )
        print colored('app: %s, project: %s, ingress deploy into k8s successful' % (self.app_name, self.project_name), 'green')

if __name__ == "__main__":
    def str2bool(v):
        if v.lower() in ('true'):
            return True
        elif v.lower() in ('false'):
            return False
        else:
            raise argparse.ArgumentTypeError('Boolean value expected.')

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", type=str2bool, nargs='?',
                        const=True, default='false',
                        help="activate debug mode.")
    parser.add_argument('--namespace')
    parser.add_argument('--app_name', help='wayne project name')
    parser.add_argument('--project_name', help='wayne deployment name')
    parser.add_argument('--image', help='docker image')
    parser.add_argument('--k8s_cluser_name', help='k8s cluster name in wayne')
    args  = parser.parse_args()
    namespace = args.namespace.replace ('_', '-')
    app_name = args.app_name.replace ('_', '-')
    project_name = args.project_name.replace ('_', '-')
    k8s_cluser_name = args.k8s_cluser_name
    image = args.image
    debug = args.debug
    wanye_api = WayneApi(namespace, app_name, project_name, k8s_cluser_name, image, debug)
    wanye_api.publish_deployment()
    wanye_api.publish_service()
    wanye_api.publish_ingress()
