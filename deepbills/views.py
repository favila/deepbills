# coding: utf-8
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.httpexceptions import HTTPTemporaryRedirect, HTTPSeeOther, HTTPBadRequest, HTTPNotFound, HTTPCreated, HTTPConflict, HTTPInternalServerError
from pyramid.url import route_url

import models.BaseXClient2 as BaseXClient

from xml.etree import cElementTree as ET

from codecs import BOM_UTF8

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


def sessionfactory():
    session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
    defaultbindings = {
        'DBua': 'deepbills'
    }
    session.execute('SET BINDINGS '+ BaseXClient.escapebindings(defaultbindings))
    return session

@view_config(route_name='bill_resource', renderer='string', request_method="GET")
def bill_resource(request):
    docid = request.matchdict['docid']
    qlatest = ("""
    declare variable $DB as xs:string := xs:string($DBua);
    let $latestrevision := db:open($DB, concat('docmetas/', $docid, '.xml'))/docmeta/revisions/revision[last()]
    return db:open($DB, $latestrevision/@doc)/*
    """, ['docid'])
    with sessionfactory() as session:
        with session.query(*qlatest) as qr:
            qr.bind('docid', docid)
            try:
                responsexml = qr.execute()
            except IOError:
                return HTTPBadRequest()
    return Response(BOM_UTF8+responsexml.encode('utf-8'), content_type="application/xml")

@view_config(route_name='bill_create', request_method="POST")
def create_bill_resource(request):
    qcreate = ("""
declare option db:chop "false";
declare variable $DB as xs:string := xs:string($DBua);
let $docmeta  := parse-xml($docmeta),
    $docid    := $docmeta/docmeta/@id,
    $docpath  := 'docs/' || $docid || '/1.xml',
    $metapath := 'docmetas/' || $docid || '.xml'
return if (db:open($DB, $metapath))
    then db:output($docid || " exists")
    else (
        db:add($DB, $doc, $docpath),
        db:add($DB, $docmeta, $metapath),
        db:output($docid || " created")
    )""",
    ('doc', 'docmeta'))
    with sessionfactory() as session:
        with session.query(*qcreate) as q:
            q.bind('doc', request.POST['doc'].value.decode('utf-8'))
            q.bind('docmeta', request.POST['docmeta'].value)
            msg = q.execute()
    docid, status = msg.split()
    if status == 'exists':
        return HTTPConflict(body=msg+"\n")
    elif status == 'created':
        newlocation = "/bills/{}".format(docid)
        return HTTPCreated(body=newlocation+"\n", headers=[('Location',newlocation)])
    else:
        return HTTPInternalServerError(body="unknown error\n")



@view_config(route_name='bill_resource', renderer='json', request_method="PUT")
def save_bill_resource(request):
    docid = request.matchdict['docid']
    response = {}
    newbill = {
        'commit-time': now_isoformat(),
        'comitter' : '/users/favila.xml',
        'description': 'Edited via AKN',
        'text': request.body.decode('utf-8'),
    }
    qupdate = ("""
        declare option db:chop "false";
        declare variable $DB as xs:string := xs:string($DBua);
        declare variable $docmeta := db:open($DB, concat('docmetas/', $docid, '.xml'))/docmeta;
        declare variable $newrev := fn:max($docmeta/revisions/revision/@id)+1;
        declare variable $newdocpath := concat('docs/', string($docid), '/', string($newrev), '.xml');
        declare variable $oldstatus := xs:string($docmeta/revisions/revision[
                @id = fn:max($docmeta/revisions/revision[@status!='']/@id)
            ]/@status);
        insert nodes 
            <revision id="{$newrev}" commit-time="{$commit-time}" 
                comitter="{$comitter}" 
                doc="{concat('/', $newdocpath)}"
                status="{$oldstatus}"
                >
                <description>{$description}</description>
            </revision>
        as last into $docmeta/revisions,
        db:add($DB, $text, $newdocpath)
    
    """, 'docid commit-time comitter description text'.split())

    if not newbill['description'] or not newbill['text']:
        request.response.status_code = 400
        response['error'] = 'Description and text are required'
        return response

    with sessionfactory() as session:
        try:
            with session.query(*qupdate) as q:
                q.bind('docid', docid)
                q.bind('commit-time', newbill['commit-time'])
                q.bind('comitter', newbill['comitter'])
                q.bind('description', newbill['description'])
                q.bind('text', newbill['text'])
                q.execute()
        except IOError, e:
            request.response.status_code = 500
            response['error'] = e.message
    return response


@view_config(route_name='vocabulary_lookup', renderer='json', http_cache=3600)
def vocabulary_lookup(request):
    vocab = 'vocabularies/%s.xml' % request.matchdict['vocabid']
    if not request.query_string:
        with sessionfactory() as session:
            with session.query("declare variable $vocab as xs:string external; db:open($DB, $vocab)") as q:
                q.bind('vocab', vocab)
                responsexml = q.execute().encode('utf-8')
        return Response(responsexml, content_type="application/xml; charset=utf-8")


    query = request.GET.get('q')
    xquery = ("""
        import module namespace functx = "http://www.functx.com";
        declare variable $DB as xs:string := xs:string($DBua);
        declare variable $vocab as xs:string external;
        declare variable $query as xs:string external;
        declare function local:extract-entity-name-id-attr($entity as element()*) as node()* {
            if ($entity) then 
                (attribute {"id"} { $entity/@id },
                attribute {"name"} {
                    ($entity/name[@current="true" or position()=1]
                    | $entity/abbr[1])[1]
                })
            else ()
        };
        <results vocabulary="{$vocab}" query="{$query}">
        {
            for $entity in functx:distinct-nodes(
                db:open($DB, $vocab)/*/*[
                    */text() contains text {$query} using stemming using language "en" using fuzzy
                ]
            )
            let $parentid := xs:string($entity/@parent-id)
            return <e>{local:extract-entity-name-id-attr($entity)}
                   <parent>{local:extract-entity-name-id-attr($entity/../*[@id eq $parentid])}</parent>
                </e>
        }
        </results>
    """, [])

    with sessionfactory() as session:
        with session.query(*xquery) as q:
            q.bind('vocab', vocab)
            q.bind('query', query)
            #ET.fromstring requires utf-8 string, not unicode
            element = q.execute().encode('utf-8')
            xresults = ET.fromstring(element)

    aresults = [xml_to_map(e) for e in xresults.iter('e')]

    return aresults


@view_config(route_name="entity_lookup", renderer="json", http_cache=3600)
def entity_lookup(request):
    vocab = 'vocabularies/%s.xml' % request.matchdict['vocabid']
    entityid = request.matchdict['entityid']
    xquery = ("""
        declare variable $DB as xs:string := xs:string($DBua);
        declare variable $vocab as xs:string external;
        declare variable $entityid as xs:string external;
        declare function local:extract-entity-name-id-attr($entity as element()*) as node()* {
            if ($entity) then 
                (attribute {"id"} { $entity/@id },
                attribute {"name"} {
                    ($entity/name[@current="true" or position()=1]
                    | $entity/abbr[1])[1]
                })
            else ()
        };
        let $DB := xs:string($DB)
        let $entity := db:open($DB, $vocab)/*/*[@id eq $entityid],
            $parentid := xs:string($entity/@parent-id)
        return 
            if ($entity) then 
                <e>{local:extract-entity-name-id-attr($entity)}
                   <parent>{local:extract-entity-name-id-attr($entity/../*[@id eq $parentid])}</parent>
                </e>
            else <e/>
        """,[])
    with sessionfactory() as session:
        with session.query(*xquery) as q:
            q.bind('vocab', vocab)
            q.bind('entityid', entityid)
            res = q.execute()
            xresults = ET.fromstring(res)
    response = xml_to_map(xresults)
    if not response:
        raise HTTPNotFound
    return response


def xml_to_map(root):
    mapping = {}
    for aname, aval in root.attrib.iteritems():
        mapping[aname] = aval
    for child in root:
        mapping[child.tag] = xml_to_map(child)
    if not mapping:
        return None
    return mapping


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
        with sessionfactory() as session:
            try:
                with session.query(response['query']) as qr:
                    for typecode, item in qr.iter():
                        response['result'].append(item)
            except IOError, e:
                response['error'] = e.message

    response['result'] = "\n".join(response['result'])
    return response

@view_config(route_name='dashboard', renderer="templates/dashboard.pt", http_cache=3600)
def dashboard(request):
    response = {
        'page_title': 'Dashboard',
        'site_name': 'DeepBills',
        'rows':'',
    }
    query = """
    declare namespace cato = "http://namespaces.cato.org/catoxml";
    declare variable $DB as xs:string := xs:string($DBua);
    for $docmeta in db:open($DB, 'docmetas')/docmeta
    let $id := $docmeta/@id, $i := xs:string($id), $bill := $docmeta/bill,
        $btype := xs:string($bill/@type), $bnum := xs:positiveInteger($bill/@number),
        $lastrevid := max($docmeta/revisions/revision/@id),
        $lastrev := $docmeta/revisions/revision[@id = $lastrevid],
        $doc := db:open($DB, $lastrev/@doc)[1],
        $annotations := count($doc/descendant::cato:entity[@entity-type eq "annotation"])
    order by $btype, $bnum 
    return <tr>
        <td class="bname">{$i}</td>
        <td class="bname number">{$btype}</td>
        <td class="bname number">{$bnum}</td>
        <td class="number revision">{$lastrevid}</td>
        <td class="annotation number">{if ($annotations) then ($annotations) else ()}</td>
        <td>{xs:string($lastrev/@status)}</td>
        <td class="number">{sum($doc/descendant::text() ! string-length(.))}</td>
        <td>{tokenize($lastrev/@commit-time, '[T+.]')[position()=(1,2)]}</td>
        <td><a href="/bills/{$i}/view">view</a></td>
        <td><a href="/bills/{$i}/edit">raw edit</a></td>
        <td><a target="_blank" href="/Editor/Index.html?doc={$i}">edit</a></td>
    </tr>"""
    with sessionfactory() as session:
        with session.query(query) as qr:
            response['rows'] = qr.execute()

    return response


@view_config(route_name="bill_view", renderer="templates/bill_view.pt")
def bill_view(request):
    docid = request.matchdict['docid']
    response = {
        'page_title': 'View Bill {}'.format(docid),
        'site_name': 'DeepBills',
        'bill' : dict(name='name', revision="1", metadata={'status':'','commit-time':'', 'committer':'','description':''}, text="<root></root>"),
        'error': '',
    }
    
    qrevision = ("""
        declare variable $DB as xs:string := xs:string($DBua);
        let $docuri := 'docmetas/' || $docid || '.xml'
        for $latestrevision in db:open($DB, $docuri)/docmeta/revisions/revision[last()]
        let $latestdoc := db:open($DB, $latestrevision/@doc)
        return
        (
            string($latestrevision/../../@id),
            string($latestrevision/@id),
            string($latestrevision/@commit-time),
            string($latestrevision/@comitter),
            string($latestrevision/description),
            string($latestrevision/@status),
            $latestdoc
        )
    """, ['docid'])
    with sessionfactory() as session:
        try:
            with session.query(*qrevision) as qr:
                qr.bind('docid', docid)
                qresponse = [v for t, v in qr.iter()]
                if not qresponse:
                    raise HTTPNotFound
                response['bill']['name'] = qresponse[0]
                response['bill']['revision'] = qresponse[1]
                response['bill']['metadata']['commit-time'] = qresponse[2]
                response['bill']['metadata']['committer'] = qresponse[3]
                response['bill']['metadata']['description'] = qresponse[4]
                response['bill']['metadata']['status'] = qresponse[5]
                response['bill']['text'] = qresponse[6]

        except IOError, e:
            response['error'] = e.message
    
    return response



@view_config(route_name="bill_edit", renderer="templates/bill_edit.pt")
def bill_edit(request):
    docid = request.matchdict['docid']
    response = {
        'page_title': 'Edit Bill {}'.format(docid),
        'site_name': 'DeepBills',
        'bill' : {
            'name':docid,
            'description': '',
            'text': '',
            'revision': '',
            'status'   : '',
        },
        'error': '',
        'statuses' : ['new', 'auto-markup', 'in-progress', 'needs-review', 'complete'],
    }
        
    qget = ("""
    declare variable $DB as xs:string := xs:string($DBua);
    declare variable $latestrevision := db:open($DB, concat('docmetas/', $docid, '.xml'))/docmeta/revisions/revision[last()];
    (db:open($DB, $latestrevision/@doc), xs:string($latestrevision/@status), xs:string($latestrevision/@id))
    """, ['docid'])
    
    qupdate = ("""
        declare option db:chop "false";
        declare variable $DB as xs:string := xs:string($DBua);
        declare variable $docmeta := db:open($DB, concat('docmetas/', $docid, '.xml'))/docmeta;
        declare variable $newrev := fn:max($docmeta/revisions/revision/@id)+1;
        declare variable $newdocpath := concat('docs/', string($docid), '/', string($newrev), '.xml');
        insert nodes 
            <revision id="{$newrev}" commit-time="{$commit-time}"
            comitter="{$comitter}" doc="{concat('/', $newdocpath)}"
            status="{$status}">
                <description>{$description}</description>
            </revision>
        as last into $docmeta/revisions,
        db:add($DB, $text, $newdocpath)
    
    """, 'docid commit-time comitter status description text'.split())
    
    def addbilldata(docid, response):
        with sessionfactory() as session:
            try:
                with session.query(*qget) as qr:
                    qr.bind('docid', docid)
                    qresponse = [v for t, v in qr.iter()]
                    response['bill']['text'] = qresponse[0]
                    response['bill']['status'] = qresponse[1]
                    response['bill']['revision'] = qresponse[2]
            except IOError, e:
                response['error'] = e.message

    if request.method == 'GET':
        addbilldata(docid, response)
    elif request.method == 'POST':
        newbill = {
            'commit-time': now_isoformat(),
            'comitter': '/users/favila.xml',
            'description': request.POST.get('description', '').strip(),
            'text': request.POST.get('text', '').strip(),
            'status': request.POST.get('status', '').strip(),
        }
        print newbill
        response['bill']['status'] = newbill['status']
        response['bill']['description'] = newbill['description']
        response['bill']['text'] = newbill['text']

        if not newbill['text'] or not newbill['status']:
            addbilldata(docid, response)
            response['error'] = 'Text and status are required'
            return response

        with sessionfactory() as session:
            try:
                with session.query(*qupdate) as q:
                    q.bind('docid', docid)
                    q.bind('commit-time', newbill['commit-time'])
                    q.bind('comitter', newbill['comitter'])
                    q.bind('status', newbill['status'])
                    q.bind('description', newbill['description'])
                    q.bind('text', newbill['text'])
                    q.execute()
                    return HTTPSeeOther(location="/bills/{}/view".format(docid))
            except IOError, e:
                response['error'] = e.message

    return response


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
            filemod = filemod.replace(tzinfo=UTC())
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
    declare variable $DB as xs:string := xs:string($DBua);
    (
    for $meta in db:open($DB,'docmetas/')/docmeta
    let $latestrevid := max($meta/revisions/revision/@id)
    let $latestrev := $meta/revisions/revision[@id = $latestrevid]
    where $latestrevid > 1
    return ('bills/'||$meta/@id||'.xml', string($latestrev/@commit-time), db:open($DB, $latestrev/@doc)/*)
    ,
    for $doc in db:open($DB, 'vocabularies/')[/entities]
    let $filename := substring-after(document-uri($doc), '/')
    let $updated := $doc/entities/@updated
    where $filename != 'vocabularies/federal-entities.xml'
    return ($filename, string($updated), $doc)
    ,
    let $schemauri := 'schemas/vocabulary.xsd'
    for $doc in db:open($DB, $schemauri)
    let $lastmod := $doc/xs:schema/xs:annotation/xs:appinfo/modified
    return ($schemauri, string($lastmod), $doc)
    )"""

    filedates = set()
    with sessionfactory() as session:
        zfp = StringIO()
        with session.query(xquery, []) as q, ZipFile(zfp, 'w', ZIP_DEFLATED) as zf:
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

