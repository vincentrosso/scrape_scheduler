__author__ = 'Steven Ogdahl'

from datetime import datetime
import json
import pytz
import re
import requests
from simplejson import JSONDecodeError
from threading import Timer
import urllib
import urlparse

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.http import urlencode
from django.utils.timezone import now as utcnow

from vdsClientPortal.enums import SystemAudit_types
import vdsWorkPortal.common.utils
import vdsWorkPortal.common.enums


class SystemAudit(models.Model):
    auditTimeStamp = models.DateTimeField(default=utcnow)
    auditMessage = models.TextField(default="")
    auditType = models.TextField(default="INFO")

    @staticmethod
    def add(msg, audit_type):
        sa = SystemAudit()
        sa.auditMessage = msg
        sa.auditType = audit_type
        sa.save()
        return sa


def SystemAudit_add(msg, audit_type):
    sa = SystemAudit()
    sa.auditMessage = msg
    sa.auditType = audit_type
    sa.save()
    return sa


class ScrapeSource(models.Model):
    from titleapi.copied_models import County
    contract_name = models.TextField()
    url = models.TextField()
    urlFormat = models.TextField()
    county = models.ForeignKey(County, default=None, null=True, blank=True, verbose_name="County", related_name="+")
    state = models.CharField(max_length=2, default=None, null=True, blank=True)
    type = models.TextField()
    is_enabled = models.BooleanField(default=True, blank=False, null=False, verbose_name="IsEnabled")
    max_retries = models.PositiveSmallIntegerField(default=0, blank=False, null=False, verbose_name="Maximum retries")
    retry_delay = models.PositiveSmallIntegerField(default=0, blank=False, null=False, verbose_name= "Retry delay (seconds)")
    scaling_pool = models.CharField(max_length=100, default='', null=False, blank=True)

    _readonly = False
    formatted_url = None
    response = None
    scrape_log = None

    @property
    def is_synchronous(self):
        return '/scrape_sync/' in self.urlFormat

    def save(self, *args, **kwargs):
        if self._readonly:
            return
        super(ScrapeSource, self).save(*args, **kwargs)

    @staticmethod
    def filter_by_county(county, *args, **kwargs):
        county_overrides_state = False
        if 'county_overrides_state' in kwargs:
            county_overrides_state = kwargs.pop('county_overrides_state')

        ss_list = ScrapeSource.objects.filter(Q(county=county) | Q(county__isnull=True, state=county.state_short)).\
            filter(*args, **kwargs).order_by('county__county_name')

        # If there are county and state scrapes and 'county_overrides_state' is True, then filter out the state scrapes
        if county_overrides_state and ss_list.filter(state__isnull=True).exists():
            ss_list = ss_list.exclude(state__isnull=False)

        # Set the county and "readonly" for each of the scrape sources.  The "readonly" bit is so the scrape source
        # doesn't accidentally get overwritten (important for state-level scrapes)
        for ss in ss_list:
            ss.county = county
            ss._readonly = True
        return ss_list

    def format_url(self, dictionary):
        url_format = self.urlFormat
        d = dictionary.copy()
        if "url" not in d:
            d['url'] = self.url
        if 'fips' not in d and self.county:
            d['fips'] = self.county.fips
        if 'county' not in d and self.county:
            d['county'] = self.county.county_name
        url_parts = url_format.split("?")
        url_query = ""
        if len(url_parts) > 1:
            url_query = "?" + urlencode([[y[0].format(**d), y[1].format(**d)] for y in [x.split('=') for x in url_parts[1].split('&')]])

        return url_parts[0].format(**d) + url_query

    @staticmethod
    def list_contracts_by_county(county):
        available = []
        scrapes = ScrapeSource.filter_by_county(county, is_enabled=True).order_by('contract_name')
        contracts = vdsWorkPortal.common.enums.scrape_contract_type().as_list()
        contracts.sort()
        for s in scrapes:
            for c in contracts:
                if c in s.contract_name:
                    available.append((c, s.contract_name))
        return available

    def __unicode__(self):
        return u'[%s] %s %s' % (
            self.contract_name,
            self.state if self.state else
                "{0}/{1}".format(self.county.state_short, self.county.county_name) if self.county else 'None',
            self.type
        )

    @property
    def display(self):
        return {
            'contract_name': self.contract_name,
            'url': self.url,
            'urlFormat': self.urlFormat,
            'county': self.county.display if self.county else None,
            'state': self.state,
            'type': self.type,
            'is_enabled': self.is_enabled,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'scaling_pool': self.scaling_pool,
            'str': str(self)
        }

    def execute(self, method=None, data=None, parameters=None, synchronous=False):
        if not self.is_enabled:
            return self.response

        if parameters:
            self.formatted_url = self.format_url(parameters)
        else:
            self.formatted_url = self.format_url({})

        # Hack for now -- this could be a bit cleaner
        if synchronous:
            self.formatted_url = self.formatted_url.replace("/scrape/", "/scrape_sync/")
        else:
            self.formatted_url = self.formatted_url.replace("/scrape_sync/", "/scrape/")

        s_data = ""
        try:
            s_data = "data=None" if data is None else json.dumps(data)
        except Exception:
            pass

        self.scrape_log = ScrapeSourceLog()
        self.scrape_log.scrape_source = self
        self.scrape_log.request_url = self.formatted_url
        if method:
            self.scrape_log.request_method = method
        if data:
            self.scrape_log.request_data = data
        self.scrape_log.save()
        try:
            if settings.ENV_HOST in ('sm1', 'sm1.vanguardds.com', 'stage.vanguardds.com', 'Lynx', 'sogdahl-Vanguard'):
                if type(data) is dict:
                    data['postback_url'] = '{0}/'.format(settings.BASE_URL)
                    self.scrape_log.request_data = data
                else:
                    self.formatted_url = "{0}{1}postback_url={2}/".format(
                        self.formatted_url,
                        '&' if '?' in self.formatted_url else '?',
                        settings.BASE_URL
                    )
                    self.scrape_log.request_url = self.formatted_url
            if settings.ENV_HOST in ("VPro.local", "web346.webfaction.com"):
                #data['postback_url'] = 'https://work.vanguardds.com/'
                self.formatted_url += "&postback_url=https://work.vanguardds.com/"
                self.scrape_log.request_url = self.formatted_url
                if method is not None and "POST" in method:
                    self.response = requests.post(self.formatted_url, data=json.dumps(data))
                else:
                    self.response = requests.get(self.formatted_url)
            else:
                v = {}
                if 'titleapi.com' in self.url:
                    v = {'verify': '/usr/local/ssl/cacert.pem'}
                #celery broken for the moment
                if method is not None and "POST" in method:
                    self.response = requests.post(self.formatted_url, data=json.dumps(data), **v)
                else:
                    self.response = requests.get(self.formatted_url, **v)
            SystemAudit_add("scrape.execute {0} {1}".format(self.formatted_url, s_data), SystemAudit_types.ROBOT_ACTION)

            try:
                response_json = self.response.json()
                status = response_json['status']
                token = response_json['track_id']
                self.scrape_log.response_message = response_json.get('message')
            except JSONDecodeError:
                status, token = self.response.text.split(", ")
            self.scrape_log.status = ScrapeSourceLog.STATUS__SUBMITTED
            self.scrape_log.response_status = status
            self.scrape_log.token = token
            # Currently, this is the only way to tell if it's still running or it waited to return.  "status" needs
            # to be more descriptive from the scrape server's side
            if "/scrape_sync/" in self.formatted_url:
                self.scrape_log.complete(self.response.text)
            else:
                self.scrape_log.save()

        except Exception, err:
            SystemAudit_add("Error in scrape.execute scrape: {0} {1} error: {2}".format(self.formatted_url, s_data, err), SystemAudit_types.ROBOT_ACTION_ERROR)
            print str(err)
            import traceback
            print traceback.print_exc()

        return self.response


class ScrapeSourceLog(models.Model):
    STATUS__CREATED = 'created'
    STATUS__SUBMITTED = 'submitted'
    STATUS__COMPLETED = 'completed'
    STATUS_CHOICES = (
        (STATUS__CREATED, 'Created'),
        (STATUS__SUBMITTED, 'Submitted'),
        (STATUS__COMPLETED, 'Completed')
    )
    scrape_source = models.ForeignKey(ScrapeSource, default=None, null=True, blank=True)
    report = None
    submission_timestamp = models.DateTimeField(auto_now_add=True)
    request_method = models.CharField(max_length=20, default="GET")
    request_url = models.TextField()
    request_data = models.TextField()
    completed_timestamp = models.DateTimeField(default=None, null=True, blank=True)
    token = models.CharField(max_length=100, default=None, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS__CREATED)
    response_status = models.CharField(max_length=40, default="")
    response_message = models.TextField(default="")
    response_payload = models.TextField()

    @staticmethod
    def find_by_token(token):
        return ScrapeSourceLog.objects.filter(token=token).first()

    def complete(self, payload):
        self.response_payload = payload
        import json
        json_body = json.loads(payload)
        if json_body:
            if 'status' in json_body:
                self.response_status = json_body['status']
            if 'message' in json_body:
                self.response_message = json_body['message'] or ''
        self.status = ScrapeSourceLog.STATUS__COMPLETED
        self.completed_timestamp = datetime.now(tz=pytz.timezone(settings.TIME_ZONE))

        self.status = ScrapeSourceLog.STATUS__COMPLETED
        # Determine if the scrape needs to be retried
        # TODO : need logic here to determine retry
        if self.response_status != "OK" and (
                        'Decaptcha failed too many times' in self.response_message or
                        'CAPTCHA was rejected due to service overload' in self.response_message or
                        'Could not solve captcha!' in self.response_message or
                        'Website timed out, please try again' in self.response_message
        ):
            retry = 0
            retry_index = -1
            # We need to first check if we're over max retries.  If we're not, then we need to add the "__retries"
            # querystring parameter with the retry count or, if it exists, increment it.  After this step, we then
            # recombine the parsed URL back into the proper string version again
            url = urlparse.urlparse(self.request_url)
            qs = urlparse.parse_qsl(url.query, keep_blank_values=True)
            for i in xrange(len(qs)):
                if qs[i][0] == '__retry':
                    retry = int(''.join(re.findall(r'\d+', qs[i][1])) or 0)
                    retry_index = i
            if retry_index >= 0:
                qs.pop(retry_index)
            qs.append(('__retry', retry + 1))

            # If we're still under the max retries, then we can execute a new scrape with the __retry count increased
            # by 1
            if self.scrape_source.max_retries > 0 and retry < self.scrape_source.max_retries:
                self.status = ScrapeSourceLog.STATUS__RETRY

                scrape = self.scrape_source
                url_parts = list(url)
                url_parts[4] = urllib.urlencode(qs)
                scrape.urlFormat = urlparse.urlunparse(url_parts)
                data = None
                if self.request_data:
                    data = json.loads(self.request_data)

                timer = Timer(scrape.retry_delay, scrape.execute, kwargs={
                    'method': self.request_method,
                    'data': data,
                    'parameters': None,
                    'synchronous': 'scrape_sync' in self.request_url,
                    'report': self.report
                })
                timer.start()

        self.save()

    @property
    def scrape_duration(self):
        if not self.completed_timestamp:
            return None
        return self.completed_timestamp - self.submission_timestamp
