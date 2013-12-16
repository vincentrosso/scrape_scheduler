__author__ = 'Steven Ogdahl'

from django.utils.http import urlquote

from scrapeService.copied_models import ScheduledScrape

def pre_request_execute(log, scheduled_scrape):
    return (ScheduledScrape.UNKNOWN, {'get_url': urlquote(scheduled_scrape.parameters)})

def post_request_execute(log, scheduled_scrape, response):
    print "Response: {0}".format(response.text)
    if response.status_code == 200:
        return (ScheduledScrape.SUCCESS, "Success")

    return (ScheduledScrape.ERROR, "Error, return code was: {0}".format(response.status_code))
