"""
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at
        http://www.apache.org/licenses/LICENSE-2.0
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
import os
from django.conf import settings

engines = {
    'direct': 'haystack.backends.simple_backend.SimpleEngine',
    'solr': 'haystack.backends.solr_backend.SolrEngine',
}

def getDefaultConfig():
    return {
      'ENGINE': engines['direct'],
    }

def getSolrUrl():
    solrUrl = os.getenv('SOLR_URL', '').lower()
    if not solrUrl:
      serviceName = os.getenv('SOLR_SERVICE_NAME', '').upper().replace('-', '_')   
      if serviceName:
        coreName = os.getenv('SOLR_CORE_NAME', 'autocore')
        serviceHost = os.getenv('{}_SERVICE_HOST'.format(serviceName))
        servicePort = os.getenv('{}_SERVICE_PORT'.format(serviceName))
        solrUrl = 'http://{}:{}/solr/{}'.format(serviceHost, servicePort, coreName)

    return solrUrl

def getConfig():
    config = getDefaultConfig() 
    solrUrl = getSolrUrl()
    if solrUrl:
      engine = engines.get(os.getenv('SOLR_ENGINE'), engines['solr'])
      config = {
        'ENGINE': engine,
        'URL': solrUrl,
      }

    return config

def config():
    return getConfig()