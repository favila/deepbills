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
    