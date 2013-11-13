from django.db import models

#general idea here is to disconnect settings from any particular application
#so that settings can be "shared" across applications by a "key"
#started b/c we need to pass account information for TitlePoint / UG
#from the portal to the api application. this way we don't have to share any models
#and don't create code dependencies which tend to get cyclic/circular
#this idea should lend itself better to breaking things into disconnected services

class AnythingSetting(models.Model):

    SETTING_TYPE_PORTAL = 'setting_type_portal'
    SETTING_TYPE_ACCOUNT = 'setting_type_account'

    SETTING_TYPE_CHOICES = (
        (SETTING_TYPE_PORTAL, 'Setting Type: Portal'),
        (SETTING_TYPE_ACCOUNT, 'Setting Type: Account')
    )

    setting_type = models.TextField(choices=SETTING_TYPE_CHOICES, default=SETTING_TYPE_PORTAL)
    #instance is indented to be a unique instance of "setting_type"
    #i.e for "setting_type_account" it would be and account name i.e "TitleSource"
    instance = models.TextField(default="", blank=True)
    name = models.TextField(default="")
    value = models.TextField(default="")

    @staticmethod
    def get_portal_value(name):
        objs = AnythingSetting.objects.filter(setting_type=AnythingSetting.SETTING_TYPE_PORTAL, instance="", name=name)
        if len(objs) >= 1:
            return objs[0].value
        objs = AnythingSetting.objects.filter(setting_type=AnythingSetting.SETTING_TYPE_PORTAL, name=name)
        if len(objs) >= 1:
            return objs[0].value
        return ""

    @staticmethod
    def get_account_value(account_name, name):
        try:
            return AnythingSetting.objects.get(setting_type=AnythingSetting.SETTING_TYPE_ACCOUNT, instance=account_name, name=name).value
        except Exception:
            return None

    class names(object):
        report_style = "report_style"

        title_point_username = "title_point_username"
        title_point_password = "title_point_password"

        data_trace_www_username = "data_trace_www_username"
        data_trace_www_password = "data_trace_www_password"
        data_trace_username = "data_trace_username"
        data_trace_password = "data_trace_password"
        data_trace_branch = "data_trace_branch"
        data_trace_branch_password = "data_trace_branch_password"

        new_order_email_username = "new_order_email_username"
        new_order_email_password = "new_order_email_password"
        propfacts_username = "propfacts_username"
        propfacts_password = "propfacts_password"
        lsi_webcenter_username = "lsi_webcenter_username"
        lsi_webcenter_password = "lsi_webcenter_password"
        mr_robot_username = "mr_robot_username"
        mr_robot_password = "mr_robot_password"

        icalendar_cache_timestamp = "icalendar_cache_timestamp"
        icalendar_cache_data = "icalendar_cache_data"

    def __unicode__(self):
        return u'[%s] %s' % (self.instance, self.name)