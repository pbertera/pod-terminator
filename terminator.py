import datetime
import logging
import os
import requests
import sys
import time
from kubernetes import config, client 
from openshift.dynamic import DynamicClient
from openshift.helper.userpassauth import OCPLoginConfiguration
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Disable SSL Warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def make_logger():
  logger = logging.getLogger('Terminator')
  logger.setLevel(logging.DEBUG)
  console_handler = logging.StreamHandler()
  logger.addHandler(console_handler)
  formatter = logging.Formatter('%(asctime)s  %(name)s  %(levelname)s: %(message)s')
  console_handler.setFormatter(formatter)
  return logger

class Terminator:

  def __init__(self, api, username, password, logger):

    self.api = api
    self.username = username
    self.password = password
    self.logger = logger
    self.dry_run = False
    self.namespace = None
    self.cycle_delay = 10
    self.max_seconds = 10
    self.k8s_client = self._get_client()
    self.dyn_client = DynamicClient(self.k8s_client)

  def _ocp_login(self):
    self._kubeConfig = OCPLoginConfiguration(ocp_username=self.username, ocp_password=self.password)
    self._kubeConfig.host = self.api
    self._kubeConfig.verify_ssl = False
    #self._kubeConfig.ssl_ca_cert = './ocp.pem' # use a certificate bundle for the TLS validation
    self._ocp_get_token()
    return client.ApiClient(self._kubeConfig)

  def _ocp_get_token(self):
    # Retrieve the auth token
    self._kubeConfig.get_token()
    self._token_created_at = datetime.datetime.utcnow()
    self.logger.debug('Auth token: {}'.format(self._kubeConfig.api_key))
    self.logger.debug('Token expires: in {} seconds'.format(self._kubeConfig.api_key_expires))
 

  def _get_client(self):
    # Login with credentials if provided (works on OCP4 only!)
    if self.username != '':
      return self._ocp_login()
    else:
      return config.new_client_from_config()

  def run(self):
    v1_pods = self.dyn_client.resources.get(api_version='v1', kind='Pod')

    while True:
      pod_list = v1_pods.get(self.namespace)
      self.logger.info("Found {} total pods".format(len(pod_list.items)))

      for pod in pod_list.items:
        if not pod.metadata.deletionTimestamp:
          continue

        pod_name = pod.metadata.name
        pod_namespace = pod.metadata.namespace
        ##deletion_grace_period = datetime.timedelta(seconds=pod.metadata.deletionGracePeriodSeconds or 0)
        ##termination_grace_period = datetime.timedelta(seconds=pod.spec.terminationGracePeriodSeconds or 0)

        #deletion_timestamp_s = pod.metadata.deletionTimestamp.replace("Z","")
        deletion_timestamp = datetime.datetime.strptime(pod.metadata.deletionTimestamp.replace("Z",""), "%Y-%m-%dT%H:%M:%S")
        #deletion_timestamp = datetime.datetime.fromisoformat(deletion_timestamp_s)
        now = datetime.datetime.utcnow()# + deletion_grace_period
        
        timediff = now - deletion_timestamp
        #timediff = now - ( deletion_timestamp - termination_grace_period )
        #timediff = now -  ( deletion_timestamp - deletion_grace_period - termination_grace_period )
        timediff_s = timediff.total_seconds()

        #self.logger.debug("deletionTimestamp: {}".format(deletion_timestamp))
        #self.logger.debug("now: {}".format(now))
        #self.logger.debug("terminationGracePeriod: {}".format(termination_grace_period))
        #self.logger.debug("deletionGracePeriod: {}".format(deletion_grace_period))
        #self.logger.debug("timediff: {} - {}".format(timediff, timediff_s))

        self.logger.info("Found pod {}/{} in Terminating state since {} seconds, treshold is {}".format(pod_namespace, pod_name, timediff_s, MAX_SECONDS))
        if timediff_s > self.max_seconds:
          self.logger.warning("Found pod {}/{} to be terminated".format(pod_namespace, pod_name))
          if not self.dry_run:
            body = {"apiVersion": "v1", "kind": "DeleteOptions", "gracePeriodSeconds":0, "propagationPolicy":"Background"}
            self.logger.warning("Deleting pod {}/{}".format(pod_namespace, pod_name))
            v1_pods.delete(namespace=pod_namespace, name=pod_name, body=body)

      if self.username != '':
        token_timediff = datetime.datetime.utcnow() - self._token_created_at
        token_timediff_s = token_timediff.total_seconds()

        # Renew the OAuth token at the alf of the expiry
        if token_timediff_s > self._kubeConfig.api_key_expires / 2:
          self.logger.warning("Renewing token")
          self._ocp_get_token()

      time.sleep(self.cycle_delay)

if __name__ == '__main__':
  logger = make_logger()

  API = os.getenv('API', '')
  USERNAME = os.getenv('USERNAME', '')
  PASSWORD = os.getenv('PASSWORD', '')
  MAX_SECONDS = os.getenv('MAX_SECONDS', '10')
  NAMESPACE = os.getenv('NAMESPACE', '')
  CYCLE_DELAY = os.getenv('CYCLE_DELAY', '10')
  DRY_RUN = os.getenv('DRY_RUN', 'False')

  logger.info("Configuration: MAX_SECONDS:{} NAMESPACE:{} CYCLE_DELAY:{} DRY_RUN:{}".format(MAX_SECONDS, NAMESPACE, CYCLE_DELAY, DRY_RUN))

  t = Terminator(API, USERNAME, PASSWORD, logger)
  t.max_seconds = int(MAX_SECONDS)
  t.namespace = NAMESPACE
  t.cycle_delay = int(CYCLE_DELAY)

  if DRY_RUN.upper() == 'TRUE' or DRY_RUN.upper() == "YES" :
    t.dry_run = True
  else:
    t.dry_run = False

  try:
    t.run()
  except KeyboardInterrupt:
    logger.info("Bye")
