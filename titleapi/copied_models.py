__author__ = 'Steven Ogdahl'

from datetime import datetime

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from vdsClientPortal.enums import SystemAudit_types
from vdsClientPortal import workday
import vdsWorkPortal.common.enums
from vdsWorkPortal.copied_models import SystemAudit

class County(models.Model):
    state_short = models.CharField(max_length=2)
    county_name = models.CharField(max_length=200)
    fips = models.CharField(max_length=5)

    def __unicode__(self):
        return u'%s %s %s' % (self.state_short, self.county_name, unicode(self.fips))

    @property
    def location(self):
        return '{0}/{1}'.format(self.state_short, self.county_name)

    @staticmethod
    def by_state_choices(state_short):
        counties = County.objects.filter(state_short=state_short).all()
        return [(c.county_name, c.id) for c in counties]

    @staticmethod
    def find_by_name(county_name, state_short, fallback=False):
        # First, we'll try to get the County directly, without any funny business
        matching_counties = County.objects.filter(county_name__iexact=county_name, state_short__iexact=state_short)
        if matching_counties.count() == 1:
            return matching_counties[0]

        # We didn't find an exact match, so next, we query CountyMap for a match
        matching_maps = CountyMap.objects.filter(
            county_name__iexact=county_name,
            state_short__iexact=state_short,
            is_validated=True)
        if matching_maps.count() == 1:
            return matching_maps[0].mapped_county

        # Now we get to the fun stuff.  No direct county map was found, so we
        # should try some fuzzy matching to see if we can find anything
        import Levenshtein
        matching_counties = County.objects.filter(state_short__iexact=state_short)
        if matching_counties.count() == 0:
            # Wow, we're really bad off if we couldn't even find the state!
            from vdsWorkPortal.copied_models import SystemAudit
            SystemAudit.add(
                "Unable to find any matching counties for state {0}".format(state_short),
                SystemAudit_types.COUNTY_MAP_ERROR)
            if fallback:
                return County.find_by_fips(fips='00000')
            return None

        levenshtein_ratios = {}
        county_name_u_u = unicode(county_name).upper()
        for matching_county in matching_counties:
            ratio = Levenshtein.ratio(unicode(matching_county.county_name).upper(), county_name_u_u)
            if ratio not in levenshtein_ratios:
                levenshtein_ratios[ratio] = []
            levenshtein_ratios[ratio].append(matching_county)

        ratios = levenshtein_ratios.keys()
        ratios.sort(reverse=True)
        # Only if:
        # 1. this is a "decent" match
        # 2. there's only 1 of them
        # 3. either there's only 1 ratio or the best ratio is at least 10%
        #    better than the next-best ratio
        if ratios[0] > 0.5 and len(levenshtein_ratios[ratios[0]]) == 1 and \
                (len(ratios) == 1 or ratios[0] > 1.1 * ratios[1]):
            from vdsWorkPortal.copied_models import SystemAudit
            SystemAudit.add(
                "Encountered unmapped county {0}/{1}.  Applying temporary map to {2}/{3} based off a Levenshtein ratio of {4}".format(
                    state_short, county_name,
                    levenshtein_ratios[ratios[0]][0].state_short, levenshtein_ratios[ratios[0]][0].county_name,
                    ratios[0]
                ),
                SystemAudit_types.COUNTY_MAP)

            # Only add an unvalidated map if there isn't one there already
            if CountyMap.objects.filter(
                    county_name__iexact=county_name,
                    state_short__iexact=state_short).count() == 0:
                cm = CountyMap()
                cm.state_short = state_short
                cm.county_name = county_name
                cm.mapped_county = levenshtein_ratios[ratios[0]][0]
                cm.is_validated = False
                cm.save()

            return levenshtein_ratios[ratios[0]][0]

        # Now we're getting into shady territory.  Even Levenshtein couldn't
        # figure out any decent match, so just pick one of the remaining
        # counties in the best-ratio list
        from vdsWorkPortal.copied_models import SystemAudit
        SystemAudit.add(
            "Encountered unmapped county {0}/{1}.  Could not safely determine mapping based on Levenshtein ratio, so choosing {2}/{3} mostly at random".format(
                state_short, county_name,
                levenshtein_ratios[ratios[0]][0].state_short, levenshtein_ratios[ratios[0]][0].county_name
            ),
            SystemAudit_types.COUNTY_MAP_ERROR)
        import random
        return random.choice(levenshtein_ratios[ratios[0]])

    @staticmethod
    def find_by_fips(fips="", state_fips="", county_fips=""):
        try:
            if fips != "":
                return County.objects.get(fips=fips.strip().zfill(5))
            elif state_fips != "" and county_fips != "":
                return County.objects.get(fips=state_fips.strip().zfill(2) + county_fips.strip().zfill(3))
        except Exception:
            return None

    @property
    def display(self):
        return {
            'id': self.id,
            'state': self.state_short,
            'county': self.county_name,
            'fips': self.fips
        }


class CountyMap(models.Model):
    state_short = models.CharField(max_length=2)
    county_name = models.CharField(max_length=200)
    mapped_county = models.ForeignKey(County)
    is_validated = models.BooleanField(verbose_name="Is this mapping validated?", default=False)


class CountyDataSource(models.Model):
    county = models.ForeignKey(County)
    source_type = models.CharField(max_length=200, choices=vdsWorkPortal.common.enums.CountyDataSource_source_type().as_choices())
    source_name = models.CharField(max_length=1000)
    source_url = models.URLField(default=None, blank=True, null=True)
    source_data_type = models.CharField(max_length=200, default=vdsWorkPortal.common.enums.CountyDataSource_source_data_type.Website, choices=vdsWorkPortal.common.enums.CountyDataSource_source_data_type().as_choices())
    notes= models.TextField(blank=True)

    def __unicode__(self):
        return u'[%s] %s' % (self.county, self.source_name)

    @property
    def county_display(self):
        return self.county.display


class CountyDataSourceIndexRange(models.Model):
    county_data_source = models.ForeignKey(CountyDataSource)
    index_type = models.CharField(max_length=1000, choices=vdsWorkPortal.common.enums.CountyDataSourceIndex_type().as_choices())
    index_subtype = models.CharField(max_length=1000, choices=vdsWorkPortal.common.enums.blank_choice + vdsWorkPortal.common.enums.CountyDataSourceIndex_subtype().as_choices(), blank=True)
    start_date = models.DateField()

    effective_date_exact = models.DateField(verbose_name="Exact Effective Date", default=None, blank=True, null=True)
    effective_date_business_days = models.PositiveIntegerField(verbose_name="Business days from today to calculate Effective Date", default=None, blank=True, null=True)

    @property
    def effective_date(self):
        if self.effective_date_exact:
            return self.effective_date_exact

        if self.effective_date_business_days is not None:
            try:
                # Now that the calendar is loaded, we can use that to calculate business days properly
                return workday.workdayadd(
                    datetime.now().date(),
                    -self.effective_date_business_days,
                    holidays=workday.icalendar_holidays()
                )

            except Exception, ex:
                SystemAudit.add("Error calculating Business Days: {0}".format(ex), SystemAudit_types.SYSTEM_ERROR)
                return None

        return None

    def __unicode__(self):
        return u'[%s] %s' % (self.county_data_source, self.index_type)


# This method NULLs out the effective_date_business_days field if both it and effective_date_exact
# are populated, so there's no confusion about which one is "correct"
@receiver(pre_save, sender=CountyDataSourceIndexRange)
def verify_effective_date(sender, instance=None, **kwargs):
    if not instance or not isinstance(instance, CountyDataSourceIndexRange):
        return

    if instance.effective_date_exact:
        instance.effective_date_business_days = None
