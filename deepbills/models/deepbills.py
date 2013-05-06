# encoding: utf-8
"""Domain objects

Bills, users, vocabularies
"""

# we use xquery_escape for literal string inclusion in queries instead of using
# the query binding mechanism because of limitations in the BaseX query
# optimizer regarding database locking. See:
# http://docs.basex.org/wiki/Transaction_Management#Limitations

from BaseXClient2 import xquery_escape as xqe


class BaseXResource(object):
    "Base class for basex-backed resources"
    def __init__(self, db):
        "Requires a BasexClient2.Session object"
        self.db = db

class Doc(BaseXResource):
    "Interface to a document"
    def __init__(self, db, docid):
        super(Doc, self).__init__(db)
        self.docid = docid

    def body(self):
        query = """\
let $meta := doc('deepbills/docmetas/%s.xml'),
    $docname := $meta/docmeta/revisions/revision[last()]/@doc,
    $doc := exactly-one(db:open('deepbills', $docname))/*
return $doc""" % xqe(self.docid)
        with self.db.query(query) as q:
            try:
                responsexml = q.execute()
            except IOError, e:
                responsexml = None
        return responsexml

    def get_meta(self, docid):
        pass

    def update(self, name, doc, meta=None):
        pass


class Vocabulary(BaseXResource):
    def __init__(self, db, vocabid):
        super(Vocabulary, self).__init__(db)
        self.vocabid = vocabid

    def body(self):
        query = "doc('deepbills/vocabularies/%s.xml')" % xqe(self.vocabid)
        with self.db.query(query) as q:
            try:
                xml = q.execute()
            except IOError, e:
                xml = None
        return xml

    def search(self, searchterm):
        query = """\
import module namespace functx = "http://www.functx.com";
declare variable $vocab as xs:string := 'vocabularies/%s.xml';
declare variable $doc as document-node() := doc('deepbills/vocabularies/%s.xml');
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
        $doc/*/*[
            */text() contains text {$query} using stemming using language "en" using fuzzy
        ]
    )
    let $parentid := xs:string($entity/@parent-id)
    return <e>{local:extract-entity-name-id-attr($entity)}
           <parent>{local:extract-entity-name-id-attr($entity/../*[@id eq $parentid])}</parent>
        </e>
}
</results>""" % (xqe(self.vocabid), xqe(self.vocabid))
        with self.db.query(query) as q:
            q.bind('query', searchterm)
            try:
                xml = q.execute()
            except IOError, e:
                xml = None
        return xml

    def entity(self, entityid):
        query = """\
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
let $doc := doc('deepbills/vocabularies/%s.xml'),
    $entity := $doc/*/*[@id eq $entityid],
    $parentid := xs:string($entity/@parent-id)
return 
    if ($entity) then 
        <e>{local:extract-entity-name-id-attr($entity)}
           <parent>{local:extract-entity-name-id-attr($entity/../*[@id eq $parentid])}</parent>
        </e>
    else <e/>""" % xqe(self.vocabid)

        with self.db.query(query) as q:
            q.bind('entityid', entityid)
            try:
                xml = q.execute()
            except IOError:
                xml = None
        return xml
