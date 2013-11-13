__author__ = 'Steven Ogdahl'
from vdsClientPortal.common import ChoiceBase

blank_choice = (('', '----------'),)

class CountyDataSource_source_type(ChoiceBase):
    Recorder = "Recorder"
    Court = "Court"
    Treasurer = "Treasurer"
    Auditor = "Auditor"

class CountyDataSource_source_data_type(ChoiceBase):
    Website = "Website"
    Plant = "Plant"
    LV_Plant = "LV_Plant"

class CountyDataSourceIndex_type(ChoiceBase):
    Search = "Search"
    Archive = "Archive"
    Images = "Images"

class CountyDataSourceIndex_subtype(ChoiceBase):
    Abstract = "Abstract"
    Torrens = "Torrens"
