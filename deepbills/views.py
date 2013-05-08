# coding: utf-8
from pyramid.view import view_config, view_defaults
from pyramid.response import Response
from pyramid import security
from pyramid.httpexceptions import (HTTPTemporaryRedirect, 
    HTTPSeeOther, HTTPBadRequest, HTTPNotFound, HTTPCreated, 
    HTTPConflict, HTTPInternalServerError, HTTPForbidden, HTTPUnauthorized)
from pyramid.url import route_url

from models import deepbills as db

from xml.etree import cElementTree as ET

import datetime

ZERO = datetime.timedelta(0)


class UTC(datetime.tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

UTC = UTC()


def now():
    """Return datetime object in UTC without microseconds"""
    return datetime.datetime.utcnow().replace(microsecond=0, tzinfo=UTC)


def now_isoformat():
    """Return current UTC time as an iso-formatted string"""
    return now().isoformat()


def xml_to_map(root):
    mapping = {}
    for aname, aval in root.attrib.iteritems():
        mapping[aname] = aval
    for child in root:
        mapping[child.tag] = xml_to_map(child)
    if not mapping:
        return None
    return mapping


@view_config(context=HTTPForbidden)
def auth_basic_challenge(request):
    """View to issue a challenge for auth-basic credentials when none are provided"""
    response = HTTPUnauthorized()
    response.headers.update(security.forget(request))
    return response


@view_defaults(context=db.Vocabulary, http_cache=3600)
class Lookup(object):
    "Vocabulary lookups"
    def __init__(self, context, request):
        self.request = request
        self.context = context
        # self.vocabid = request.matchdict['vocabid']
        # self.vocab = deepbills.Vocabulary(request.basex, self.vocabid)

    @view_config(renderer='string')
    def all(self):
        vocabxml = self.context.body()
        self.request.response.content_type = 'application/xml'
        return vocabxml

    @view_config(context=db.VocabularyEntry, renderer="json")
    def one(self):
        response = self.context.asmap()
        return response

    @view_config(request_param='q', renderer='json')
    def search(self):
        searchterm = self.request.GET.get('q')
        return self.context.search(searchterm)


@view_config(route_name='bill_types', renderer="templates/bill_types.pt", http_cache=3600)
def bill_types(request):
    response = {
        'page_title': 'Dashboard',
        'site_name': 'DeepBills',
        'bill_types': db.BillList.billtypes,
    }
    return response


@view_config(context=db.BillList, renderer="templates/dashboard.pt", http_cache=3600)
def dashboard(context, request):
    response = {
        'page_title': 'Dashboard',
        'site_name':  'DeepBills',
        'rows':        context(),
        'bill_type':   context.billtype
    }
    if response['bill_type']:
        response['page_title'] += ': ' + response['bill_type']
    return response


@view_config(route_name='query', renderer='templates/query.pt')
def query(request):
    response = {
        'page_title': 'Query',
        'site_name': 'DeepBills',
        'query':'',
        'result':[],
        'error':'',
    }
    response['query'] = request.GET.get('query', '')
    
    if response['query']:
        try:
            with request.basex.query(response['query']) as qr:
                for typecode, item in qr.iter():
                    response['result'].append(item)
        except IOError, e:
            response['error'] = e.message

    response['result'] = "\n".join(response['result'])
    return response


@view_defaults(context=db.Bill)
class Bill(object):
    def __init__(self, context, request):
        self.request = request
        self.context = context

    @view_config(renderer='string', request_method="GET")
    def get(self):
        lock = int(self.request.GET.get('lock', '0'))
        if lock:
            locked, status = db.Lock(self.request.basex, self.context.docid).acquire()
            if not locked:
                raise HTTPConflict(
                    content_type='text/plain',
                    body="Failed to acquire lock on {id}: currently held by"
                         "{userid} since {time}\n".format(status))

        response = Response(self.context.doc(), content_type="application/xml")

    @view_config(permission='revise', request_method="POST", renderer='json')
    def put(self):
        "A save from the editor"
        response = {}
        # to save, must: have permission to save given bill's current status
        #   AND have a lock on the bill                        
        if self.context.rev_asmap()['status'] == 'complete' and not security.has_permission('complete', self.context, self.request):
            raise HTTPForbidden(
                content_type="text/plain", 
                body="You may not save a new revision of a completed bill\n")
        db.Locks(self.request.basex).reap()
        locked, status = db.Lock(self.request.basex, self.context.docid).acquire()
        if not locked:
            raise HTTPConflict(
                content_type='text/plain',
                body="Failed to acquire lock on {id}: currently held by"
                     "{userid} since {time}\n".format(status))

        newbill = {
            'time':        now_isoformat(),
            'comitter' :   security.authenticated_userid(request),
            'description': 'Edited via AKN',
            'text':        request.body.decode('utf-8'),
        }

        if not newbill['description'] or not newbill['text']:
            self.request.response.status_code = 400
            response['error'] = 'Description and text are required'
            return response

        self.context.save(newbill['committer'], newbill['time'], **newbill)

        if self.request.GET.get('release'):
            db.Lock('release')

        return response


    @view_config(context=db.Bills, request_method="POST")
    def create(self):
        docmeta = self.request.POST['docmeta'].value
        doc = self.request.POST['doc'].value.decode('utf-8')
        docid, status = context.create(docmeta, doc)
        if status == 'exists':
            return HTTPConflict(body="{} {}\n".format(docid, status))
        elif status == 'created':
            newlocation = "/bills/{}".format(docid)
            return HTTPCreated(body=newlocation+"\n", location=newlocation)
        else:
            return HTTPInternalServerError(body="unknown error\n")

    @view_config(name="view", renderer="templates/bill_view.pt", permission="view")
    def view(self):
        response = {
            'page_title': 'View Bill {}'.format(self.context.docid),
            'site_name': 'DeepBills',
            'bill' : dict(name='name', revision="1", metadata={'status':'','commit-time':'', 'committer':'','description':''}, text="<root></root>"),
            'error': '',
        }
        
        revdata = self.context.rev_asmap()
        response['bill']['name'] = self.context.docid
        response['bill']['revision'] = revdata['id']
        response['bill']['metadata'].update(revdata)
        del response['bill']['metadata']['id']
        response['bill']['text'] = self.context.doc()

        return response


    def edit_form_response(self):
        docid = self.context.docid
        rev = self.context.rev_asmap()
        response = {
            'page_title': 'Edit Bill {}'.format(docid),
            'site_name': 'DeepBills',
            'bill' : {
                'name':  docid,
                'description': '',
                'text': '',
                'revision': rev['id'],
                'status': rev['status'],
            },
            'error': '',
            'statuses' : ['new', 'auto-markup', 'in-progress', 'needs-review', 'complete'],
        }
        return response


    @view_config(name='edit', permission='revise', renderer="templates/bill_edit.pt", request_method="GET")
    def edit_form(self):
        response = self.edit_form_response()
        if has_permission('complete', self.context, self.request):
            response['bill']['text'] = self.context.doc()
        return response


    @view_config(name="edit", permission='revise', renderer="templates/bill_edit.pt", request_method="POST")
    def edit(self):
        "A save from the Edit Raw screen"
        response = self.edit_form_response()
        newbill = {
            'commit-time': now_isoformat(),
            'comitter':    security.authenticated_userid(self.request),
            'description': self.request.POST.get('description', '').strip(),
            'text':        self.request.POST.get('text', '').strip(),
            'status':      self.request.POST.get('status', '').strip(),
        }

        iscommitter = security.has_permission('committer', self.context, self.request)

        if not iscommitter and (newbill['description'] or newbill['status'] == 'completed'):
            newbill['text'] = ''
            response['error'] = "Error: only an administrator may complete a bill or edit its xml directly."
            self.request.response.status_code = 403 # forbidden -- but show form

        response['bill']['status'] = newbill['status']
        response['bill']['description'] = newbill['description']
        response['bill']['text'] = newbill['text']

        if not newbill['text'] or not newbill['status']:
            response['error'] = 'Text and status are required'
            return response

        action = self.request.POST.get('action')
        nextlocation = location="/bills/{}/view".format(docid)
        if action == 'Save and Edit Next':
            newbillid = self.context.next()
            if newbillid:
                nextlocation = '/Editor/Index.html?doc={}'.format(newbillid)
        elif action == 'Save and Return':
            dashboard = db.Dashboard(self.request.basex, self.context.asmap()['bill']['type'])
            nextlocation = self.request.resource_url(dashboard)
        return HTTPSeeOther(nextlocation)


@view_defaults(context=db.Locks, renderer='json')
class Locks(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(request_method='GET')
    def list(self):
        return self.context.asmap()


@view_config(route_name="download")
def download(request):
    from dateutil.parser import parse
    import time
    from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
    from cStringIO import StringIO
    from itertools import izip

    def parsetime(timestr):
        filemod = parse(timestr)
        if filemod.tzinfo is None:
            filemod = filemod.replace(tzinfo=UTC)
        return filemod

    README = """CatoXML-enhanced Federal Bills
==============================

(Last update in package was on {lastmod})

This package contains:

* `bills` directory: the latest versions of all bill xml files which
   have had CatoXML inline metadata elements added to them.

* `vocabularies` directory: the latest versions of all entity lookup
  tables (in xml) used by CatoXML.

More information on the CatoXML namespace and how to interpret CatoXML
metadata is available at http://namespaces.cato.org/catoxml

"""
    xquery = """
    declare namespace xs = "http://www.w3.org/2001/XMLSchema";
    (
    for $meta in db:open('deepbills','docmetas/')/docmeta
    let $latestrevid := max($meta/revisions/revision/@id)
    let $latestrev := $meta/revisions/revision[@id = $latestrevid]
    where $latestrevid > 1
    return ('bills/'||$meta/@id||'.xml', string($latestrev/@commit-time), db:open('deepbills', $latestrev/@doc)/*)
    ,
    for $doc in db:open('deepbills', 'vocabularies/')[/entities]
    let $filename := substring-after(document-uri($doc), '/')
    let $updated := $doc/entities/@updated
    where $filename != 'vocabularies/federal-entities.xml'
    return ($filename, string($updated), $doc)
    ,
    let $schemauri := 'schemas/vocabulary.xsd'
    for $doc in db:open('deepbills', $schemauri)
    let $lastmod := $doc/xs:schema/xs:annotation/xs:appinfo/modified
    return ($schemauri, string($lastmod), $doc)
    )"""

    filedates = set()
    zfp = StringIO()
    with request.basex.query(xquery, []) as q, ZipFile(zfp, 'w', ZIP_DEFLATED) as zf:
        for (_, filename), (_, isotime), (_, xml) in izip(*[iter(q.iter())]*3):
            filemod = parsetime(isotime)
            filedates.add(filemod)
            zinfo = ZipInfo(filename, filemod.timetuple())
            zf.writestr(zinfo, xml.encode('utf-8'), ZIP_DEFLATED)

        lastmod = max(filedates)
        readme_zinfo = ZipInfo('README.txt', lastmod.timetuple())
        zf.writestr(readme_zinfo, README.format(lastmod=lastmod.isoformat()))

    zfplen = zfp.tell()
    zfp.seek(0)

    return Response(
        body_file=zfp, content_length=zfplen,
        content_type="application/zip",
        content_disposition='attachment; filename="catobills_113-{:.0f}.zip"'.format(time.mktime(lastmod.timetuple())),
        last_modified = lastmod
    )

