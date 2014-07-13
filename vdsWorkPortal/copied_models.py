__author__ = 'Steven Ogdahl'

from datetime import datetime
from time import strftime

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.http import urlencode

import vdsClientPortal.enums
import vdsWorkPortal.common.utils
import vdsWorkPortal.common.enums

class ScrapeSource(models.Model):
    from titleapi.copied_models import County
    contract_name = models.TextField()
    url = models.TextField()
    urlFormat = models.TextField()
    county = models.ForeignKey(County, default=None, null=True, blank=True, verbose_name="County", related_name="+")
    type = models.TextField()
    is_enabled = models.BooleanField(default=True, blank=False, null=False, verbose_name="IsEnabled")

    def get_image_scrape_url(self, token="",  AFN="", book="", page="", recdate="", scrape_type="Image", county=None, contract_name=None, pages=None, property_type=""):
        try:
            scrape = None
            url = ""
            extra = ""
            if contract_name != None:
                scrape = ScrapeSource.objects.get(is_enabled=True, contract_name=contract_name)
            else:
                doctype = "docid"
                if book !="" and page != "":
                    doctype = "book"
                if pages is not None:
                    doctype = "fetcher"
                scrapeList = ScrapeSource.objects.filter(
                    is_enabled=True,
                    county=county,
                    type=scrape_type,
                    contract_name__contains=doctype)
                if len(scrapeList) > 0:
                    scrape = scrapeList[0]
            if scrape != None:
                recdateprased = vdsWorkPortal.common.utils.dateparse(recdate)
                formattedDate = strftime("%m%d%Y", recdateprased)
                d = dict()
                d["url"] = scrape.url
                d["token"] = token
                d["docid"] = AFN
                d["book"] = book
                d["page"] = page
                d["date"] = formattedDate
                if property_type and len(property_type) > 0:
                    d["property_type"] = property_type[:1]
                if pages is not None:
                    d["numpages"] = pages
                try:
                    d["fips"] = county.fips
                except Exception:
                    pass
                url = scrape.format_url(d).replace(' ','%20')
            return url
        except Exception, err:
            SystemAudit.add("exception in get_image_scrape_url {0}".format(err), vdsClientPortal.enums.SystemAudit_types.ROBOT_ACTION_ERROR)
            return None

    def format_url(self, dictionary): # format, url, token=None, AFN=None, book=None, page=None, recdate=None):
        url_format = self.urlFormat
        d = dictionary.copy()
        if "url" not in d:
            d['url'] = self.url
        if 'fips' not in d and self.county:
            d['fips'] = self.county.fips
        url_format = url_format.format(**d)
        url_parts = url_format.split("?")
        url_path = url_parts[0]
        url_query = ""
        if len(url_parts) > 1:
            url_query = "?" + urlencode(dict( (n,v) for n,v in (a.split('=') for a in url_parts[1].split("&") ) )) #gotta love python!

        return url_path + url_query

    def __unicode__(self):
        return u'[%s] %s %s' % (self.contract_name, self.county.county_name if self.county else 'None', self.type)

    @property
    def display(self):
        return {
            'contract_name': self.contract_name,
            'url': self.url,
            'urlFormat': self.urlFormat,
            'county': self.county,
            'type': self.type,
            'is_enabled': self.is_enabled
        }


class SystemAudit(models.Model):
    auditTimeStamp = models.DateTimeField()
    auditMessage = models.TextField(default="")
    auditType = models.TextField(default="INFO")

    @staticmethod
    def add(msg, audit_type):
        sa = SystemAudit()
        sa.auditMessage = msg
        sa.auditTimeStamp = datetime.now()
        sa.auditType = audit_type
        sa.save()
        return sa

# This method NULLs out the effective_date_business_days field if both it and effective_date_exact
# are populated, so there's no confusion about which one is "correct"
@receiver(pre_save, sender=CountyDataSourceIndexRange)
def verify_effective_date(sender, instance=None, **kwargs):
    if not instance or not isinstance(instance, CountyDataSourceIndexRange):
        return

    if instance.effective_date_exact:
        instance.effective_date_business_days = None
