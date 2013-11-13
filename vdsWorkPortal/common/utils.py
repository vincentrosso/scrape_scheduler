__author__ = 'Steven Ogdahl'

import parsedatetime.parsedatetime as pdt


def dateparse( s ):
    c = pdt.Calendar()
    result, what = c.parse( s )
    return result