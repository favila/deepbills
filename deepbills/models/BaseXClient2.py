#!/usr/bin/env python
# encoding: utf-8
"""
Enhanced Python 2.7.3 and 3.x client for BaseX.
Requires python3/BaseXClient.py

Created by Francis Avila on 2012-08-07.
Copyright (c) 2012 Dancing Mammoth, Inc. All rights reserved.
"""
import BaseXClient

class Session(BaseXClient.Session):
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        self.close()
        return False
    
    def query(self, querytxt, boundnames=None):
        """Return a Query with the necessary preambles for the boundnames"""
        if boundnames is not None:
            querytxt = declare_external(boundnames)+"\n"+querytxt
        return Query(self, querytxt, boundnames)

class Query(BaseXClient.Query):
    def __init__(self, session, querytxt, binds=None):
        BaseXClient.Query.__init__(self, session, querytxt)
        self.__bindnames = binds

    def execute(self, binds=None):
        """Execute the query with binds and return the result"""
        if binds is not None:
            for bname, bval in binds.items():
                self.bind(bname, bval)
        return super(Query, self).execute()
    
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        self.close()
        return False


def declare_external(bindnames):
    dec_tmpl = "declare variable ${} external;"
    declarations = [dec_tmpl.format(name) for name in bindnames]
    return '\n'.join(declarations)

def escapebindings(D):
    """Return a string escaped for the SET BINDINGS BaseX command for a mapping

    D should be a mapping, such as a dict with the following structure:

    >>> d = {
        ('namespaceURI', 'varname') : 'value', # for a namespaced variable name
        'varname' : 'value', # for a variable name in no namespace
        }

    """
    return ','.join(escapebinding(k, v) for k,v in D.items())

def escapebinding(name, value):
    """Return a string escaped for SET BINDINGS BaseX Command for a name, value pair

    -- name may be a tuple of ('namespaceURI', 'name')
    -- value is a string

    """
    if isinstance(name, basestring):
        name = ('', name)
    namespace, localname = name
    if namespace:
        binding = "{%s}%s=%s" % (namespace, localname, value.replace(',',',,'))
    else:
        binding = "$%s=%s" % (localname, value.replace(',',',,'))
    return binding

def sessionfactory(host, port, user, pass_):
    session = Session(host, port, user, pass_)
    defaultbindings = {
        'DBua': 'deepbills'
    }
    session.execute('SET BINDINGS '+ escapebindings(defaultbindings))
    return session

def basexsession_tween_factory(handler, registry):
    basexsettings = registry.settings.get('basex.connection_settings')
    if basexsettings:
        basexsettings = basexsettings.split(', ')
        basexsettings[1] = int(basexsettings[1])
        basexsettings = tuple(basexsettings)
    else:
        return handler
    requestproperty = registry.settings.get('basex.request_property', 'basex')
    def _basexconnect(request):
        session = sessionfactory(*basexsettings)
        request.add_finished_callback(lambda request: getattr(request, requestproperty).close())
        return session

    def basexsession_tween(request):
        request.set_property(_basexconnect, requestproperty, reify=True)
        return handler(request)
    return basexsession_tween

def xquery_escape(s):
    "Return a string escaped for literal inclusion in an xquery"
    return s.replace(u'"', u'&quot;').replace(u"'", u'&apos;')
