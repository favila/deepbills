# coding: utf-8
import unittest
from pyramid import testing
from pyramid.httpexceptions import HTTPNotFound

class QueryTests(unittest.TestCase):
    testdbname = 'testdb'
    def setUp(self):
        from .views import sessionfactory
        self.session = sessionfactory()
        self.session.execute('SET MAINMEM true')
        self.session.execute('CREATE DB %s' % self.testdbname)
        self.session.execute('SET MAINMEM false')

    def TearDown(self):
        self.session.execute('DROP DB %s' % self.testdbname)
        self.session.close()

    def test_utf8_document_xquery_add(self):
        sess = self.session
        specialchardoc = u'<root>\u2014</root>'
        specialchardoc_utf8 = specialchardoc.encode('utf-8')
        resourcepath = 'QueryTests/test_utf8_document_xquery_add.xml'
        
        xqadd = ("db:add($testdb, $data, $path)", ['testdb','data','path'])
        with sess.query(*xqadd) as q:
            q.bind('testdb', self.testdbname)
            q.bind('data', specialchardoc)
            q.bind('path', resourcepath)
            q.execute()
        
        xqverify = ("db:open($testdb, $path)", ['testdb', 'path'])
        with sess.query(*xqverify) as q:
            q.bind('testdb', self.testdbname)
            q.bind('path', resourcepath)
            result = q.execute()
        self.assertEqual(specialchardoc, result)


