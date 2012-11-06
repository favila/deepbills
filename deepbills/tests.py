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


class ViewTests(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_entity_lookup_success_parent(self):
        from .views import entity_lookup
        request = testing.DummyRequest()
        request.matchdict['vocabid'] = 'federal-entities'
        request.matchdict['entityid'] = '200-35'
        response = entity_lookup(request)
        expected = {
            'id':'200-35',
            'name':'the Mildred and Claude Pepper Foundation',
            'parent':{
                'id':'200',
                'name':'Other Defense Civil Programs',
            }
        }
        self.assertEqual(response, expected)


    def test_entity_lookup_success_noparent(self):
        from .views import entity_lookup
        request = testing.DummyRequest()
        request.matchdict['vocabid'] = 'federal-entities'
        request.matchdict['entityid'] = '200'
        response = entity_lookup(request)
        expected = {
            'id':'200',
            'name':'Other Defense Civil Programs',
            'parent': None
        }
        self.assertEqual(response, expected)

    def test_entity_lookup_fail(self):
        from .views import entity_lookup
        request = testing.DummyRequest()
        request.matchdict['vocabid'] = 'federal-entity'
        request.matchdict['entityid'] = 'zzzzz'
        with self.assertRaises(HTTPNotFound):
            response = entity_lookup(request)


