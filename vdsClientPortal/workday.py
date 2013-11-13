__author__ = 'Steven Ogdahl'

from datetime import date, datetime, timedelta
import urllib2

from django.conf import settings

import icalendar

from anything.copied_models import AnythingSetting

# started from the code of Casey Webster at
# http://groups.google.com/group/comp.lang.python/browse_thread/thread/ddd39a02644540b7

# Define the weekday mnemonics to match the date.weekday function
(MON, TUE, WED, THU, FRI, SAT, SUN) = range(7)


def workdaysub(start_date, end_date, whichdays=(MON, TUE, WED, THU, FRI), holidays=[]):
    """
    Calculate the number of working days between two dates inclusive
    (start_date <= end_date).

    The actual working days can be set with the optional whichdays
parameter
    (default is MON-FRI)
    """
    delta_days = (end_date - start_date).days + 1
    full_weeks, extra_days = divmod(delta_days, 7)
    # num_workdays = how many days/week you work * total # of weeks
    num_workdays = (full_weeks + 1) * len(whichdays)
    # subtract out any working days that fall in the 'shortened week'
    for d in range(1, 8 - extra_days):
        if (end_date + timedelta(d)).weekday() in whichdays:
            num_workdays -= 1

    # skip holidays that fall on weekends
    holidays = [x for x in holidays if x.weekday() in whichdays]
    # subtract out any holidays
    for d in holidays:
        if start_date <= d <= end_date:
            num_workdays -= 1

    return num_workdays

def _in_between(a,b,x):
    return a <= x <= b or b <= x <= a

def workdayadd(start_date, work_days, whichdays=(MON, TUE, WED, THU, FRI), holidays=[]):
    """
    Adds to a given date a number of working days
    2009/12/04 for example is a friday - adding one weekday
    will return 2209/12/07
    >>> workdayadd(date(year=2009,month=12,day=4),1)
    datetime.date(2009, 12, 7)
    """
    weeks, days = divmod(work_days, len(whichdays))
    new_date = start_date + timedelta(weeks=weeks)
    for i in range(days):
        new_date += timedelta(days=1)
        while new_date.weekday() not in whichdays:
            new_date += timedelta(days=1)

    # to account for days=0 case
    while new_date.weekday() not in whichdays:
        new_date += timedelta(days=1)

    # avoid this if no holidays
    if holidays:
        delta = timedelta(days=1 * cmp(work_days,0))
        # only do holidays that fall on weekdays
        holidays = [x for x in holidays if x.weekday() in whichdays]
        holidays = [x for x in holidays if x != start_date]
        for d in sorted(holidays, reverse = (days < 0)):
            # if d in between start and current push it out one working day
            if _in_between(start_date, new_date, d):
                new_date += delta
                while new_date.weekday() not in whichdays:
                    new_date += delta

    return new_date

def icalendar_holidays():
    icalendar_timestamps = AnythingSetting.objects.filter(setting_type=AnythingSetting.SETTING_TYPE_PORTAL, instance="", name=AnythingSetting.names.icalendar_cache_timestamp)
    if len(icalendar_timestamps) == 0:
        # Set up default setting if there's nothing defined yet
        icalendar_timestamp = AnythingSetting()
        icalendar_timestamp.setting_type = AnythingSetting.SETTING_TYPE_PORTAL
        icalendar_timestamp.instance = ""
        icalendar_timestamp.name = AnythingSetting.names.icalendar_cache_timestamp
        icalendar_timestamp.value = datetime(1970, 1, 1).strftime('%c')
        icalendar_timestamp.save()
    else:
        icalendar_timestamp = icalendar_timestamps[0]

    timestamp = datetime.strptime(icalendar_timestamp.value, '%c')

    icalendar_datas = AnythingSetting.objects.filter(setting_type=AnythingSetting.SETTING_TYPE_PORTAL, instance="", name=AnythingSetting.names.icalendar_cache_data)
    if len(icalendar_datas) == 0:
        # Set up default setting if there's nothing defined yet
        icalendar_data = AnythingSetting()
        icalendar_data.setting_type = AnythingSetting.SETTING_TYPE_PORTAL
        icalendar_data.instance = ""
        icalendar_data.name = AnythingSetting.names.icalendar_cache_data
        icalendar_data.value = ""
        icalendar_data.save()
    else:
        icalendar_data = icalendar_datas[0]

    # The cache has expired or the data doesn't exist, so we need to get the new data
    if datetime.now() - timestamp > timedelta(days=182) or not icalendar_data.value:
        ical_contents = urllib2.urlopen(settings.ICALENDAR_URL).read()

        cal = icalendar.Calendar.from_ical(ical_contents)
        # This trims the icalendar object down to just those events that we care about (holidays)
        for subcomponent in cal.walk('VEVENT'):
            is_valid = False
            for holiday in settings.ICALENDAR_HOLIDAYS:
                if 'SUMMARY' in subcomponent and subcomponent['SUMMARY'].startswith(holiday):
                    # This holiday has an "Eve", so add that day as well
                    if holiday in settings.ICALENDAR_HOLIDAY_EVES:
                        eve = icalendar.Event()
                        eve.add('UID', "{0}e".format(subcomponent['UID']))
                        eve.add('DTSTART', subcomponent['DTSTART'].dt - timedelta(days=1))
                        eve.add('DTEND', subcomponent['DTEND'].dt - timedelta(days=1))
                        eve.add('SUMMARY', "{0} Eve{1}".format(subcomponent['SUMMARY'][:len(holiday)], subcomponent['SUMMARY'][len(holiday):]))
                        cal.add_component(eve)
                    is_valid = True
                    break
            if not is_valid:
                cal.subcomponents.remove(subcomponent)
        icalendar_data.value = cal.to_ical()
        icalendar_data.save()
        icalendar_timestamp.value = datetime.now().strftime('%c')
        icalendar_timestamp.save()
    else:
        cal = icalendar.Calendar.from_ical(icalendar_data.value)

    return [e['DTSTART'].dt for e in cal.walk('VEVENT')]