__author__ = 'Steven Ogdahl'

from django.utils.http import urlquote

from scrapeService.copied_models import ScheduledScrape

def pre_request_execute(log, scheduled_scrape):
    return (ScheduledScrape.UNKNOWN, {})

def post_request_execute(log, scheduled_scrape, response):
    return (ScheduledScrape.ERROR, "Automatically failing")
