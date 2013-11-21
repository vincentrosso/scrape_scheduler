#!/usr/bin/python
__author__ = 'Steven Ogdahl'
__version__ = '0.2a'

import sys
import socket
import logging
import uuid
import requests
import re
import pytz
import os
from datetime import datetime, timedelta, time

ENV_HOST = socket.gethostname()

from django.conf import settings

if ENV_HOST == 'Lynx':
    settings.configure(
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': 'workportal',
                'USER': 'workportal',
                'PASSWORD': 'PYddT2rEk02d',
                'HOST': '127.0.0.1',
                'PORT': '5432',
                'OPTIONS': {'autocommit': True,}
            }
        },
        TIME_ZONE = 'US/Central'
    )

elif ENV_HOST == 'stage.vanguardds.com':
    settings.configure(
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': 'workportal',
                'USER': 'workportal',
                'PASSWORD': 'PYddT2rEk02d',
                'HOST': '127.0.0.1',
                'PORT': '5432',
                'OPTIONS': {'autocommit': True,}
            }
        },
        TIME_ZONE = 'US/Pacific'
    )

elif ENV_HOST == 'work.vanguardds.com':
    settings.configure(
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': 'workportal',
                'USER': 'workportal',
                'PASSWORD': 'PYddT2rEk02d',
                'HOST': '127.0.0.1',
                'PORT': '5432',
                'OPTIONS': {'autocommit': True,}
            }
        },
        TIME_ZONE = 'US/Pacific'
    )

elif ENV_HOST == 'atisearch.com':
    settings.configure(
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': 'workportal',
                'USER': 'workportal',
                'PASSWORD': 'PYddT2rEk02d',
                'HOST': '127.0.0.1',
                'PORT': '5432',
                'OPTIONS': {'autocommit': True,}
            }
        },
        TIME_ZONE = 'US/Pacific'
    )

from scrapeService.copied_models import ScheduledScrape
tz = pytz.timezone(settings.TIME_ZONE)

# Set up basic defaults
DRY_RUN = False
URL_FORMAT_DICT = {
    'token': uuid.uuid4()
}

TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'
MIN_LOG_LEVEL = logging.WARNING
LOGFILE = 'scrape_scheduler.log'

def log(level, message, scheduled_scrape=None):
    if scheduled_scrape:
        logstr = "SchScrapeId: {0} -- {1}".format(scheduled_scrape.id, message)
    else:
        logstr = message
    logging.log(level, logstr)

def print_help():
    print "usage: %s [OPTIONS]" % sys.argv[0]
    print "OPTIONS can be any of (default in parenthesis):"

    print "  -l(F|C|E|W|I|D)\tSets the minimum logging level to Fatal, Critical, "
    print "\t\tError, Warning, or Info, or Debug (W)"
    print "  -LFILE\tSets logfile to FILE"
    print "\t\tLeave blank for STDOUT"
    print "  -p##\t\tSets main polling interval (2)"
    print "  -w##\t\tSets credential waiting timeout value (90)"

    print "  -d\t\tPerforms a dry run (does everything but execute the scrapes)"
    print "  -kKEY=VALUE\tAdds the specified key/value pair to the scrape URL mapping dict"
    print "\t\t\tCan be specified multiple times"
    print "  -h/--help\t\tPrints this message"
    print "  -v/--version\t\tPrints the current version"


if __name__ == "__main__":
    start_time = datetime.now(tz)

    #  VERY basic options parsing
    if len(sys.argv) >= 2:
        for arg in sys.argv[1:]:
            if arg[:2] == '-l':
                if arg[-1] in ('f', 'F'):
                    MIN_LOG_LEVEL = logging.FATAL
                elif arg[-1] in ('c', 'C'):
                    MIN_LOG_LEVEL = logging.CRITICAL
                elif arg[-1] in ('e', 'E'):
                    MIN_LOG_LEVEL = logging.ERROR
                elif arg[-1] in ('w', 'W'):
                    MIN_LOG_LEVEL = logging.WARNING
                elif arg[-1] in ('i', 'I'):
                    MIN_LOG_LEVEL = logging.INFO
                elif arg[-1] in ('d', 'D'):
                    MIN_LOG_LEVEL = logging.DEBUG
                else:
                    print "unknown parameter '{0}' specified for -l.  Please use F, C, E, W, I, or D"
                    sys.exit(2)
            elif arg[:2] == '-L':
                LOGFILE = arg[2:]
            elif arg[:2] == '-d':
                DRY_RUN = True
            elif arg[:2] == '-k':
                mo = re.match(r'(?P<key>[^=\s]+)\s*=\s*(?P<value>.*)', arg[2:])
                if mo:
                    URL_FORMAT_DICT[mo.group('key')] = mo.group('value')
            elif arg[:2] in ('-h', '--help'):
                print_help()
                sys.exit(1)
            elif arg[:2] in ('-v', '--version'):
                print "%s version %s" % (sys.argv[0], __version__)
                sys.exit(1)
            else:
                print "Unknown argument passed.  Please consult --help"
                sys.exit(2)

    os.environ['TZ'] = settings.TIME_ZONE
    logging.basicConfig(
        filename=LOGFILE,
        level=MIN_LOG_LEVEL,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt=TIMESTAMP_FORMAT
    )

    scheduled_scrapes = ScheduledScrape.objects.filter(
        scrapesource__is_enabled=True
    ).exclude(
        _time_of_day__isnull=True,
        _frequency__isnull=True
    ).order_by('pk')
    log(logging.INFO, "Checking {0} scheduled scrapes".format(len(scheduled_scrapes)))

    for scheduled_scrape in scheduled_scrapes:
        now = datetime.now(tz)
        # If this is a time-of-day-based scrape and the last time it was run is
        # between that time and now, then we can skip this scrape
        if scheduled_scrape.last_status != ScheduledScrape.ERROR and \
                scheduled_scrape.time_of_day and scheduled_scrape.last_run:
            now = datetime.now(tz)
            last_run_tod = datetime.combine(scheduled_scrape.last_run.date(), scheduled_scrape.time_of_day)
            now_tod = datetime.combine(now.date(), scheduled_scrape.time_of_day.replace(tzinfo=tz))
            next_run_tod = None
            if scheduled_scrape.last_run.replace(tzinfo=tz) > now_tod:
                next_run_tod = now_tod + timedelta(days=1)
            elif now_tod > now:
                next_run_tod = now_tod
            if next_run_tod:
                log(logging.DEBUG, "Skipping because of time_of_day. Last run at {0:%Y-%m-%d %H:%M}. Next run on or after {1:%Y-%m-%d %H:%M}.".format(scheduled_scrape.last_run, next_run_tod), scheduled_scrape)
                continue

        # If this is a frequency-based scrape and we last ran it more
        # recently than the frequency, then we can skip this scrape
        if  scheduled_scrape.last_status != ScheduledScrape.ERROR and \
                scheduled_scrape.frequency and scheduled_scrape.last_run and now - scheduled_scrape.last_run < scheduled_scrape.frequency_timedelta:
            log(logging.DEBUG, "Skipping because of frequency ({1:0.0f} < {2:0.0f}). Last run at {0:%Y-%m-%d %H:%M}. Next run on or after: {3:%Y-%m-%d %H:%M}.".format(scheduled_scrape.last_run, (now - scheduled_scrape.last_run).total_seconds(), scheduled_scrape.frequency_timedelta.total_seconds(), scheduled_scrape.last_run + scheduled_scrape.frequency_timedelta), scheduled_scrape)
            continue

        log(logging.INFO, "Running scrape", scheduled_scrape)

        message = ''
        status = ScheduledScrape.UNKNOWN
        module = None
        if scheduled_scrape.processing_module and not sys.modules.has_key(scheduled_scrape.processing_module):
            module = __import__('execute_methods.{0}'.format(scheduled_scrape.processing_module), fromlist=[''])

        if module and hasattr(module, 'pre_request_execute'):
            try:
                s = module.pre_request_execute(log, scheduled_scrape)
                if s != ScheduledScrape.UNKNOWN:
                    status = s
            except:
                log(logging.WARNING, "pre_request_execute failed with the following exception: {0}".format(sys.exc_info()), scheduled_scrape)
                scheduled_scrape.last_run = start_time
                scheduled_scrape.last_message = str(sys.exc_info())
                scheduled_scrape.last_status = ScheduledScrape.WARNING
                scheduled_scrape.save()
                continue

        scrape_url = scheduled_scrape.scrapesource.format_url(URL_FORMAT_DICT)
        log(logging.DEBUG, "Executing scrape: {0}".format(scrape_url), scheduled_scrape)
        # Now that we've filtered out all scrapes that *shouldn't* run, we should run the ones that pass through!
        response = requests.get(scrape_url)

        if module and hasattr(module, 'post_request_execute'):
            try:
                status, message = module.post_request_execute(log, scheduled_scrape, response)
            except:
                log(logging.WARNING, "post_request_execute failed with the following exception: {0}".format(sys.exc_info()), scheduled_scrape)
                message = str(sys.exc_info())
                status = ScheduledScrape.WARNING

        # Use the cached datetime.now() so that it won't get screwed up with time_of_day execution
        scheduled_scrape.last_run = start_time
        scheduled_scrape.last_message = message
        scheduled_scrape.last_status = status
        scheduled_scrape.save()

    log(logging.INFO, "Done checking scheduled scrapes")