# coding: utf-8
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.httpexceptions import HTTPTemporaryRedirect, HTTPSeeOther, HTTPBadRequest
from pyramid.url import route_url

import datetime

import models.BaseXClient2 as BaseXClient

def sessionfactory():
    session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
    defaultbindings = {
        'DB': 'deepbills'
    }
    session.execute('SET BINDINGS '+ BaseXClient.escapebindings(defaultbindings))
    return session

@view_config(route_name='bill_resource', renderer='string', request_method="GET")
def bill_resource(request):
    docid = request.matchdict['docid']
    qlatest = ("""
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
    return Response(responsexml, content_type="application/xml")

@view_config(route_name='bill_resource', renderer='json', request_method="PUT")
def save_bill_resource(request):
    docid = request.matchdict['docid']
    response = {}
    newbill = {
        'commit-time': datetime.datetime.now().isoformat(),
        'comitter' : '/users/favila.xml',
        'description': 'Edited via AKN',
        'text': request.body.decode('utf-8'),
    }
    qupdate = ("""
        declare variable $docmeta := db:open($DB, concat('docmetas/', $docid, '.xml'))/docmeta;
        declare variable $newrev := fn:max($docmeta/revisions/revision/@id)+1;
        declare variable $newdocpath := concat('docs/', string($docid), '/', string($newrev), '.xml');
        insert nodes 
            <revision id="{$newrev}" commit-time="{$commit-time}" comitter="{$comitter}" doc="{concat('/', $newdocpath)}">
                <description>{$description}</description>
            </revision>
        as last into $docmeta/revisions,
        db:add($DB, $text, $newdocpath)
    
    """, 'docid commit-time comitter description text'.split())

    if not newbill['description'] or not newbill['text']:
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
            response['error'] = e.message
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
    for $id in db:open($DB, 'docmetas')/docmeta/@id[matches(., '^[0-9]+hr[0-9]')]
    let $i := xs:string($id)
    return <tr>
        <td>{$i}</td>
        <td><a href="/bills/{$i}/activity">activity</a></td>
        <td><a href="/bills/{$i}/view">view</a></td>
        <td><a href="/bills/{$i}/edit">edit</a></td>
        <td><a href="/static/Editor/Index.html?doc={$i}">edit (AKN)</a></td>
        <td><a href="/bills/{$i}/compare">compare</a></td>
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
        'bill' : dict(name='name', revision="1", metadata={'commit-time':'', 'committer':'','description':''}, text="<root></root>"),
        'error': '',
    }
    
    qrevision = ("""
        declare variable $latestrevision := db:open($DB, concat('docmetas/', $docid, '.xml'))/docmeta/revisions/revision[last()];
        declare variable $latestdoc := db:open($DB, $latestrevision/@doc);
        (
            string($latestrevision/../../@id),
            string($latestrevision/@id),
            string($latestrevision/@commit-time),
            string($latestrevision/@comitter),
            string($latestrevision/description),
            $latestdoc
        )
    """, ['docid'])
    with sessionfactory() as session:
        try:
            with session.query(*qrevision) as qr:
                qr.bind('docid', docid)
                qresponse = [v for t,v in qr.iter()]
                response['bill']['name'] = qresponse[0]
                response['bill']['revision'] = qresponse[1]
                response['bill']['metadata']['commit-time'] = qresponse[2]
                response['bill']['metadata']['committer'] = qresponse[3]
                response['bill']['metadata']['description'] = qresponse[4]
                response['bill']['text'] = qresponse[5]
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
        },
        'error': '',
    }
    
    
    
    qget = ("""
    declare variable $latestrevision := db:open($DB, concat('docmetas/', $docid, '.xml'))/docmeta/revisions/revision[last()];
    db:open($DB, $latestrevision/@doc)
    """, ['docid'])
    
    qupdate = ("""
        declare variable $docmeta := db:open($DB, concat('docmetas/', $docid, '.xml'))/docmeta;
        declare variable $newrev := fn:max($docmeta/revisions/revision/@id)+1;
        declare variable $newdocpath := concat('docs/', string($docid), '/', string($newrev), '.xml');
        insert nodes 
            <revision id="{$newrev}" commit-time="{$commit-time}" comitter="{$comitter}" doc="{concat('/', $newdocpath)}">
                <description>{$description}</description>
            </revision>
        as last into $docmeta/revisions,
        db:add($DB, $text, $newdocpath)
    
    """, 'docid commit-time comitter description text'.split())
    
    if request.method=='GET':
        with sessionfactory() as session:
            try:
                with session.query(*qget) as qr:
                    qr.bind('docid', docid)
                    qresponse = [v for t,v in qr.iter()]
                    response['bill']['text'] = qresponse[0]
            except IOError, e:
                response['error'] = e.message
            
    elif request.method=='POST':
        newbill = {
            'commit-time': datetime.datetime.now().isoformat(),
            'comitter' : '/users/favila.xml',
            'description': request.POST.get('description', '').strip(),
            'text': request.POST.get('text', '').strip(),
        }
        response['bill']['description'] = newbill['description']
        response['bill']['text'] = newbill['text']
        
        if not newbill['description'] or not newbill['text']:
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
                    return HTTPSeeOther(location="/bills/{}/view".format(docid))
            except IOError, e:
                response['error'] = e.message
    
    return response
