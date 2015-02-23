__author__ = 'Steven Ogdahl'

from datetime import datetime
import json
import requests
import socket
from time import strftime
from urllib2 import urlopen

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.http import urlencode
from django.utils.timezone import now as utcnow

from vdsClientPortal.enums import SystemAudit_types
import vdsWorkPortal.common.utils
import vdsWorkPortal.common.enums


class ScrapeSource(models.Model):
    from titleapi.copied_models import County
    contract_name = models.TextField()
    url = models.TextField()
    urlFormat = models.TextField()
    county = models.ForeignKey(County, default=None, null=True, blank=True, verbose_name="County", related_name="+")
    state = models.CharField(max_length=2, default=None, null=True, blank=True)
    type = models.TextField()
    is_enabled = models.BooleanField(default=True, blank=False, null=False, verbose_name="IsEnabled")

    _readonly = False
    formatted_url = None
    response = None

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
        scrapes = ScrapeSource.filter_by_county(county, is_enabled=True)
        contracts = vdsWorkPortal.common.enums.scrape_contract_type().as_list()
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
            'county': self.county,
            'type': self.type,
            'is_enabled': self.is_enabled,
            'str': str(self)
        }

    def execute(self, method=None, data=None, parameters=None, synchronous=False):
        if parameters:
            self.formatted_url = self.format_url(parameters)
        else:
            self.formatted_url = self.format_url({})

        # Hack for now -- this could be a bit cleaner
        if synchronous:
            self.formatted_url = self.formatted_url.replace("/scrape/", "/scrape_sync/")

        s_data = ""
        try:
            s_data = "data=None" if data is None else json.dumps(data)
        except Exception:
            pass
        try:
            if method is not None and "POST" in method:
                self.response = urlopen(self.formatted_url, json.dumps(data))
            else:
                self.response = requests.get(self.formatted_url)
            SystemAudit_add("scrape.execute {0} {1}".format(self.formatted_url, s_data), SystemAudit_types.ROBOT_ACTION)
        except Exception, err:
            SystemAudit_add("Error in scrape.execute scrape: {0} {1} error: {2}".format(self.formatted_url, s_data, err), SystemAudit_types.ROBOT_ACTION_ERROR)
            print str(err)

        return self.response


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
