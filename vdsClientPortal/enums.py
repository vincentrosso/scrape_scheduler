__author__ = 'Steven Ogdahl'

from vdsClientPortal.common import ChoiceBase

class SystemAudit_types(ChoiceBase):
    ROBOT_JOB = "ROBOT JOB"
    ROBOT_ACTION = "ROBOT ACTION"
    ROBOT_JOB_ERROR = "ROBOT JOB ERROR"
    ROBOT_ACTION_ERROR = "ROBOT ACTION ERROR"
    ROBOT_POST = "ROBOT POST"
    ROBOT_POST_ERROR = "ROBOT POST ERROR"
    API_REQUEST = "API REQUEST"
    API_ERROR = "API ERROR"
    COUNTY_MAP = "COUNTY MAP"
    COUNTY_MAP_ERROR = "COUNTY MAP ERROR"
    SYSTEM_ERROR = "SYSTEM ERROR"