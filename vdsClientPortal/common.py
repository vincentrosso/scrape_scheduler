__author__ = 'Steven Ogdahl'

class ChoiceBase():
    def as_choices(self):
        c =[(k,v) for k,v in self.__class__.__dict__.iteritems() if not k.startswith('__')]
        return tuple(c)

    def as_pretty_choices(self):
        c =[(v,v) for k,v in self.__class__.__dict__.iteritems() if not k.startswith('__')]
        return c

    def as_list(self):
     return sorted([k for k,v in self.__class__.__dict__.iteritems() if not k.startswith('__')])

    def get(self, k, d=None):
        return self.__class__.__dict__.get(k, d)