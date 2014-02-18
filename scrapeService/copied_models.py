__author__ = 'Steven Ogdahl'

from datetime import datetime, timedelta
from django.db import models
from vdsWorkPortal.copied_models import ScrapeSource

class ScheduledScrape(models.Model):
    UNKNOWN = 0
    SUCCESS = 1
    WARNING = 2
    ERROR = 3
    STATUS_CHOICES = (
        (UNKNOWN, 'Unknown'),
        (SUCCESS, 'Success'),
        (WARNING, 'Warning'),
        (ERROR, 'Error')
    )

    scrapesource = models.ForeignKey(ScrapeSource, verbose_name='Scrape Source')
    _time_of_day = models.TimeField(verbose_name='Time of day to run', db_column='time_of_day', default=None, blank=True, null=True)
    _frequency = models.BigIntegerField(verbose_name='Frequency to run, in minutes', db_column='frequency', default=None, blank=True, null=True)
    processing_module = models.CharField(verbose_name='Module to load for processing the scrape', max_length=500, default='', blank=True)
    parameters = models.TextField(verbose_name='Parameters', default='', blank=True)
    last_run = models.DateTimeField(verbose_name='Last time this scrape was run', default=None, null=True)
    last_message = models.TextField(verbose_name='Message from the most-recent run', default='', blank=True)
    last_status = models.PositiveSmallIntegerField(verbose_name='Status from most-recent run', default=UNKNOWN, choices=STATUS_CHOICES)
    is_enabled = models.BooleanField(verbose_name="Scrape is enabled", default=True, blank=False, null=False)
    retry_timeout = models.BigIntegerField(verbose_name='Time to wait before being retried from failure', default=None, blank=True, null=True)
    max_retries = models.BigIntegerField(verbose_name='Maximum number of times to retry a scrape before giving up', default=0, blank=False, null=False)
    retry_count = models.BigIntegerField(verbose_name='Current number of times to retries', default=0, blank=False, null=False)
    disable_on_max_retries = models.BooleanField(verbose_name='Disable the scheduled scrape when it hits maximum retries?', default=False, blank=False, null=False)

    @property
    def time_of_day(self):
        return self._time_of_day

    @time_of_day.setter
    def time_of_day(self, value):
        if value:
            if type(value) in (str, unicode):
                try:
                    value = datetime.strptime(value, '%I:%M %p')
                except:
                    pass
            self._frequency = None
            self._time_of_day = value

    @property
    def frequency(self):
        return self._frequency

    @frequency.setter
    def frequency(self, value):
        if value:
            self._time_of_day = None
            self._frequency = value

    @property
    def frequency_timedelta(self):
        return timedelta(minutes=self.frequency)
