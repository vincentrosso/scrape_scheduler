__author__ = 'Steven Ogdahl'

from datetime import timedelta
from django.db import models
from vdsWorkPortal.copied_models import ScrapeSource

class ScheduledScrape(models.Model):
    scrapesource = models.ForeignKey(ScrapeSource, verbose_name='Scrape Source')
    _time_of_day = models.TimeField(verbose_name='Time of day to run', db_column='time_of_day', default=None, blank=True, null=True)
    _frequency = models.BigIntegerField(verbose_name='Frequency to run, in seconds', db_column='frequency', default=None, blank=True, null=True)
    processing_module = models.CharField(verbose_name='Module to load for processing the scrape', max_length=500, default='', blank=True)
    parameters = models.TextField(verbose_name='Parameters', default='', blank=True)
    last_run = models.DateTimeField(verbose_name='Last time this scrape was run', default=None, null=True)
    last_message = models.TextField(verbose_name='Message from the most-recent run', default='', blank=True)

    @property
    def time_of_day(self):
        return self._time_of_day

    @time_of_day.setter
    def time_of_day_set(self, value):
        self._frequency = None
        self._time_of_day = value

    @property
    def frequency(self):
        return self._frequency

    @frequency.setter
    def frequency_set(self, value):
        self._time_of_day = None
        self._frequency = value

    @property
    def frequency_timedelta(self):
        return timedelta(minutes=self.frequency)
