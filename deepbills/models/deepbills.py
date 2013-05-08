# encoding: utf-8
"""Domain objects

Bills, users, vocabularies
"""

# we use xquery_escape for literal string inclusion in queries instead of using
# the query binding mechanism because of limitations in the BaseX query
# optimizer regarding database locking. See:
# http://docs.basex.org/wiki/Transaction_Management#Limitations

from BaseXClient2 import xquery_escape as xqe
from passlib.apps import custom_app_context as pwd_context
from xml.etree import cElementTree as ET
import copy

from pyramid.security import Everyone, Allow, Deny, ALL_PERMISSIONS, DENY_ALL


def located(obj, name, parent):
    "Return obj after adding name and parent location-aware traversal attributes"
    obj.__name__ = name
    obj.__parent__ = parent
    return obj

def xml_to_map(root, lists=()):
    """Return an ElementTree as a map

    Attributes and child element names become keys. Attributes will have scalar
    values. Child elements have map values or (if name is in +lists+) lists
    of the mapped contents of subelements. Elements with no attributes or
    child elements become strings of their text content.

    >>> xml_to_map(ET.fromstring("<foos><foo a='1'>fooa1</foo><foo b='2'/><bar/></foos>"), ['foos'])
    [{'a': '1'}, {'b': '2'}, '']

    Note that the 'foo' and 'bar' elements are no longer named and the text
    content of foo is gone.
    """
    if root.tag in lists:
        mapping = []
        for child in root:
            mapping.append(xml_to_map(child, lists))
    else:
        mapping = {}
        mapping.update(root.attrib)
        for child in root:
            mapping[child.tag] = xml_to_map(child, lists)
    if not mapping:
        return root.text or ''
    return mapping



class BaseXResource(object):
    "Base class for basex-backed resources"
    def __init__(self, db):
        "Requires a BasexClient2.Session object"
        self.db = db


class Bills(BaseXResource):
    """Produce space-efficient lists of bill items, optionally filtered by bill type"""
    __acl__ = [
        (Allow, ('group:editor', 'group:admin'), 'view'),
        (Allow, 'scraper', 'create'),
        DENY_ALL, # default
    ]

    billtypes = ['hr', 'hres', 'hconres', 'hjres', 's', 'sres', 'sconres', 'sjres']

    def __init__(self, db, billtype=None):
        super(Bills, self).__init__(db)
        self.billtype = billtype if billtype in self.billtypes else None

    def __getitem__(self, billtype):
        if self.billtype is not None or billtype not in self.billtypes:
            raise KeyError
        return located(Bills(self.db, billtype), billtype, self)

    def __call__(self):
        query = """\
declare namespace cato = "http://namespaces.cato.org/catoxml";
for $docmeta in db:open('deepbills', 'docmetas/')/docmeta
let $id := $docmeta/@id, $i := xs:string($id), $bill := $docmeta/bill,
    $btype := xs:string($bill/@type), $bnum := xs:positiveInteger($bill/@number),
    $lastrevid := max($docmeta/revisions/revision/@id),
    $lastrev := $docmeta/revisions/revision[@id = $lastrevid],
    $doc := db:open('deepbills', $lastrev/@doc)[1],
    $annotations := count($doc/descendant::cato:entity[@entity-type eq "annotation"])
where if ($btype_filter) then ($btype = $btype_filter) else (true())
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
        with self.db.query(query) as q:
            if self.billtype:
                q.bind('btype_filter', self.billtype, 'xs:string')
            else:
                q.bind('btype_filter', 'false()', 'xs:boolean')
            return q.execute()

    def create(self, docmeta, doc):
        """Create a new bill from docmeta and doc (both xml strings)"""
        qcreate = ("""\
declare option db:chop "false";
let $docmeta  := (# db:chop true #) { parse-xml($docmeta) },
    $docid    := $docmeta/docmeta/@id,
    $docpath  := 'docs/' || $docid || '/1.xml',
    $metapath := 'docmetas/' || $docid || '.xml'
return if (db:open('deepbills', $metapath))
    then db:output($docid || " exists")
    else (
        db:add('deepbills', $doc, $docpath),
        db:add('deepbills', $docmeta, $metapath),
        db:output($docid || " created")
    )""", ('doc', 'docmeta'))
        with self.db.query(*qcreate) as q:
            q.bind('doc', doc)
            q.bind('docmeta', docmeta)
            msg = q.execute()
        return msg.split()


class Bill(BaseXResource):
    __acl__ = [
        (Allow, Everyone, 'view'),
        (Allow, 'group:editor', 'revise'),
        (Allow, 'group:admin', ('revise', 'complete')),
        DENY_ALL, # default
    ]

    def __init__(self, db, docid):
        super(Bill, self).__init__(db)
        self.docid = docid
        self._meta = self.db.get_document('deepbills', 'docmetas/{}'.format(docid))
        self._et_meta = None   # cache of docmeta Element (parsed)
        self._revisions = None # Revision cache
        self._docs = {}        # keyed by revision number

    @property
    def meta(self):
        "Docmeta element as an Element (parsed self._meta text)"
        if self._et_meta is None:
            self._et_meta = ET.fromstring(self._meta)
        return self._et_meta

    def asmap(self):
        return xml_to_map(self.meta)

    def rev(self, rev=None):
        "Return revision Element for revision number (default latest revision)"
        if self._revisions is None:
            self._revisions = {int(r.get('id')):r for r in self.meta.find('revisions')}
            self._revisions[None] = self._revisions[max(self._revisions.keys())]
        return self._revisions[rev]

    def onlyrev(self, rev=None):
        "Return a docmeta Element with full revision history replaced by a single revision"
        rev = copy.deepcopy(self.rev(rev))
        meta = copy.deepcopy(self.meta)
        meta.find('revisions')
        meta.remove(meta.find('revisions'))
        meta.append(rev)
        return meta

    def onlyrev_asmap(self, rev=None):
        "Return self.onlyrev(rev) as a map instead of a docmeta Element"
        return xml_to_map(self.onlyrev(rev))

    def doc(self, rev=None):
        "Return full document for given revision (default last)"
        doc = self._docs.get(rev)
        if doc is not None:
            return doc

        revinfo = self.rev(rev)
        doc = self.db.get_document('deepbills', revinfo.get('doc'))

        self._docs[int(revinfo.get('id'))] = doc

        # If this is latest rev, cache it with None key
        if rev is None or (None not in self._docs and rev == max(self._revisions.keys())):
            self._docs[None] = doc

        return doc

    def save(self, committer, time, status=None, description=None, text=None):
        """Save a new revision of this document

        
        If +text+ is omitted, a new revision will be saved without changing the
        text.
        """
        query = """\
declare option db:chop 'false';
declare namespace cato = "http://namespaces.cato.org/catoxml";
let $metapath   := concat('docmetas/', $docid, '.xml'),
    $docmeta   := db:open('deepbills', $metapath)/docmeta,
    $lastrevid := xs:positiveInteger(fn:max($docmeta/revisions/revision/@id)),
    $newrevid  := $lastrevid + 1,
    $lastrev   := $docmeta/revisions/revision[@id = $lastrevid],
    $newstatus := if ($status) then $status else
                    if ($lastrev/@status = ('new', 'auto-markup'))
                    then 'in-progress' else xs:string($lastrev/@status),
    $size      := if ($text)
                    then sum($text/descendant::text() ! string-length(.))
                    else false(),
    $annotations := if ($text)
                    then count($text/descendant::cato:entity[@entity-type eq "annotation"])
                    else false(),
    $newdocpath := if ($text) then concat('docs/', $docid, '/', $newrevid, '.xml')
                    else false()
return (
    (# db:chop true #) {
        insert node 
            copy $r := $lastrev
            modify (
                replace value of node $r/@id with $newrevid,
                replace value of node $r/@committer with $committer,
                replace value of node $r/@commit-time with $commit-time,
                replace value of node $r/@status with $newstatus,
                if ($description)
                    then replace value of node $r/description with $description else (),
                if ($newdocpath)
                    then replace value of node $r/@doc with $newdocpath else ()
            ) return $r
            as last into $docmeta/revisions
    },
    (# db:chop false #) {
        if ($text)
            then db:add('deepbills', document { $text/* } , $newdocpath) else ()
    }
)"""
        with self.db.query(query) as q:
            q.bind('docid', self.docid, 'xs:string')
            q.bind('committer', committer, 'xs:string')
            q.bind('commit-time', time, 'xs:dateTime')
            if status is None:
                q.bind('status', 'false()', 'xs:boolean')
            else:
                q.bind('status', status, 'xs:string')
            if description is None:
                q.bind('description', 'false()', 'xs:boolean')
            else:
                q.bind('description', description, 'xs:string')
            if text is None:
                q.bind('text', 'false()', 'xs:boolean')
            else:
                q.bind('text', text, 'document-node()')
            q.execute()

        # clear any cached metadata if successful
        self._meta = self.db.get_document('deepbills', 'docmetas/{}'.format(docid))
        self._et_meta = None
        self._revisions = None
        self._docs = {}



class Users(BaseXResource):
    __acl__ = [
        (Allow, ('group:editor','group:admin'), 'view'),
        (Allow, 'group:admin', 'create'),
        DENY_ALL
    ]
    "Interface to all users"
    def __init__(self, db):
        super(Users, self).__init__(db)
        self._usermap_cache = None

    @property
    def _usermap(self):
        if self._usermap_cache is None:
            userlist = xml_to_map(ET.fromstring(db.get_document('users', 'users')), ['users'])
            for user in userlist:
                user['roles'] = user['roles'].strip().split()
            usermap = {u['id']:u for u in userlist}
            self._usermap_cache = usermap
        return self._usermap_cache

    def __call__(self):
        return self._usermap

    def __getitem__(self, userid):
        userdata = self._usermap[userid]
        user = User(self.db, userid, userdata)
        return located(user, userid, self)

    def create(self, userdata):
        "Create a new User from a dict with the user's fields"
        user = ET.Element('user')
        user.attrib.update(userdata)
        userxml = ET.tostring(user)
        query = """\
let $users := db:open('users', 'user.xml')/users
return insert node $newuser into $users"""
        with self.db.query(query) as q:
            q.bind('newuser', userxml, 'element()')
            q.execute()
        # new user added, so be sure to clear the cached userlist
        self._usermap_cache = None


class User(BaseXResource):
    "Interface to a user"
    def __init__(self, db, userid, userdata=None):
        super(User, self).__init__(db)
        self.userid = userid
        # users have *per-instance* ACLs!!
        self.__acl__ = [
            (Allow, self.userid, ('view', 'edit'))
            (Allow, 'group:admin', ('view', 'edit')),
            DENY_ALL
        ]
        if userdata is None:
            users = Users(self.db)
            userdata = users[userid]
        self._userdata = userdata

    def __getattr__(self, name):
        return self._userdata[name]

    def __setattr__(self, name, value):
        self._userdata[name] = value

    @property
    def principals(self):
        "Return a list of security principals for this user"
        principals = [self.userid]
        principals.extend(self.roles)
        return principals

    @staticmethod
    def user_with_pass(db, userid, passwd):
        """Return valid user or None"""
        try:
            user.User(db, userid)
        except KeyError:
            return None
        if not pwd_context.verify(passwd, user('password')):
            return None
        return user

    @staticmethod
    def authentication_check(userid, passwd, request):
        """Return None or a list of principal identifiers

        A callback for an authentication check, e.g. for BasicAuthAuthenticationPolicy()
        """
        user = User.user_with_pass(request.basex, userid, passwd)
        if user is not None:
            return user.principals
        return None


class Locks(BaseXResource):
    "Lists of currently-held locks"
    def __init__(self, db):
        super(Locks, self).__init__(db)
        self._locklist = None
        self.release_timedout()

    def __call__(self):
        if self._locklist is not None:
            return self._locklist

        query = """\
element locks {
for $lock in db:open('deepbills', 'docmetas/')/docmeta/lock
return copy $l := $lock
    modify(
        insert node $lock/../@id into $l,
        insert node $lock/../bill into $l
    )
    return $l
}"""
        with self.db.query(query) as q:
            self._locklist = ET.fromstring(q.execute())
        return self._locklist

    def __getitem__(self, docid):
        return located(Lock(self.db, docid), docid, self)

    def reap(self, timeout=900):
        """Release timed-out locks

        Timeout is in seconds since acquired.
        """
        query = """\
let $now := current-dateTime(),
    $timeout-duration := xs:dayTimeDuration("PT"||$timeout-seconds||"S")
for $lock in db:open('deepbills', 'docmetas/')/docmeta/lock
let $locktime := xs:dateTime($lock/@time)
where ($now - $locktime) > $timeout-duration
return delete node $lock"""
        with self.db.query(query) as q:
            q.execute()


class Lock(BaseXResource):
    "A document lock"
    def __init__(self, db, docid):
        super(Lock, self).__init__(db)
        self.docid = docid

    def acquire(self, userid, time):
        query = """\
let $docmeta := db:open('deepbills', 'docmetas/%s.xml')/docmeta
return if ($docmeta/lock[@userid=$userid])
    then (
        replace value of node $docmeta/lock/@time with $time,
        db:output(<acquire status="refreshed"/>)
    ) else
    if ($docmeta/lock)
    then (
        db:output(<acquire status="failed">{($docmeta/@lock, $docmeta/@time)}</acquire>)
    ) else (
        insert node <lock userid="{$userid}" time="{$time}"
        db:output(<acquire status="acquired"/>)
    )""" % xqe(self.docid)
        with self.db.query(query) as q:
            q.bind('userid', userid, 'xs:string')
            q.bind('time', time, 'xs:dateTime')
            result = xml_to_map(ET.fromstring(q.execute()))
        return result

    def release(self, userid=None):
        query = """\
let $docmeta := db:open('deepbills', 'docmetas/%s.xml')/docmeta
return if ($userid and $docmeta/lock[@userid=$userid])
    then (
        replace value of node $docmeta/lock/@time with $time,
        db:output(<acquire status="refreshed"/>)
    ) else
    if ($docmeta/lock)
    then (
        db:output(<acquire status="failed">{($docmeta/@lock, $docmeta/@time)}</acquire>)
    ) else (
        insert node <lock userid="{$userid}" time="{$time}"
        db:output(<acquire status="acquired"/>)
    )""" % xqe(self.docid)
        with self.db.query(query) as q:
            if userid is None:
                q.bind('userid', 'false()', 'xs:boolean')
            else:
                q.bind('userid', userid, 'xs:string')
            result = xml_to_map(ET.fromstring(q.execute()))
        return result



class Vocabularies(BaseXResource):
    def __getitem__(self, vocabid):
        return located(Vocabulary(self.db, vocabid), vocabid, self)


class Vocabulary(BaseXResource):
    def __init__(self, db, vocabid):
        super(Vocabulary, self).__init__(db)
        self.vocabid = vocabid
        # this will raise KeyError on failure:
        self.db.document_exists('deepbills', 'vocabularies/{}'.format(vocabid))


    def body(self):
        return self.db.get_document('deepbills', 'vocabularies/{}'.format(self.vocabid))

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
            except IOError:
                xml = None
        return [db.xml_to_map(e) for e in ET.fromstring(xml)]


    def entity(self, entityid):
        "Return a single vocabulary entry (an Entity) with entityid, or None if not found"
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

    def __getitem__(self, entityid):
        xml = self.entity(entityid)
        if xml is None:
            return KeyError(entityid)
        return located(VocabularyEntry(xml), entityid, self)

class VocabularyEntry(object):
    """A single entity of a Vocabulary lookup table."""
    def __init__(self, xmldata):
        self.xmldata = xmldata

    def asmap(self):
        return xml_to_map(ET.fromstring(self.xmldata))


