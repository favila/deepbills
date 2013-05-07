module namespace m = "http://deepbills.dancingmammoth.com/modules/helpers";
declare namespace cato = "http://namespaces.cato.org/catoxml";


declare function m:index-text($text as element(), $meta as element(docmeta))
as element(text) {
  <text
    node-id="{db:node-id($text)}"
    node-pre="{db:node-pre($text)}"
    document-name="{$meta/@id}"
    document-uri="deepbills{$meta/revision/@doc}"
    rev="{$meta/revision/@id}"
    status="{$meta/revision/@status}">{
      normalize-space($text) ! lower-case(.) ! hash:md5(.)
    }</text>
};

declare function m:billnames()
as xs:string* {
  db:open('deepbills','docmetas/')/docmeta/@id ! xs:string(.)
};

declare function m:open-bill($doc as item())
as node()+ {
  m:open-bill($doc, -1)
};

declare function m:open-bill($doc as item(), $revno as xs:integer)
as node()+ {
  let $meta := typeswitch($doc) 
        case element(docmeta) return $doc
        case document-node(element(docmeta)) return $doc/docmeta
        default return db:open('deepbills','docmetas/'||$doc||'.xml')/*,
      $revs := $meta/revisions,
      $maxrev := max($revs/revision/@id ! xs:positiveInteger(.)),
      $revno := if ($revno < 0) then $maxrev+1+$revno else $revno,
      $rev  := $revs/revision[@id = $revno],
      $bill := db:open('deepbills', xs:string($rev/@doc)),
      $metadata := copy $c := $meta
        modify (replace node $c/revisions with $c/revisions/revision[@id=$revno])
        return $c
  return ($metadata, $bill)
};

declare function m:scratch-doc-uri()
as xs:string {
  'scratch/metadata-candidates/'
};
declare function m:scratch-doc-uri($docname as item()?)
as xs:string {
   m:scratch-doc-uri()||(if ($docname) then $docname||'.xml' else '')
};

declare updating function m:delete-new-doc-copies() {
  db:delete('deepbills', m:scratch-doc-uri())
};

declare updating function m:clear-similars-index() {
  (
    try { db:drop('similars') } catch * {()},
    db:create('similars', <root/>, 'text.xml'),
    m:delete-new-doc-copies()
  )
};

declare updating function m:copy-new-docs() {
  (# db:chop false() #) {
    for $fullmeta in db:open('deepbills','docmetas/')/docmeta
    let $doc := m:open-bill($fullmeta), $meta := $doc[1], $bill := $doc[2],
      $scratchfile := m:scratch-doc-uri($meta/@id)
    where $meta/revision/@status = 'new'
    return db:add('deepbills', document {$bill/*}, $scratchfile)
  }
};


declare updating function m:index-docs() {
  (# db:chop true() #) {
    (
      let $sims := db:open('similars','text.xml')/*
      return insert nodes (
        for $fullmeta in db:open('deepbills', 'docmetas/')/docmeta
        let $doc := m:open-bill($fullmeta),
          $status := xs:string($doc[1]/revision/@status),
          $meta := if ($status='new')
            (: rewrite the meta path :)
            then copy $cpy_meta := $doc[1]
              modify (
                replace value of node $cpy_meta/revision/@doc with '/'||m:scratch-doc-uri($cpy_meta/@id)
              ) return $cpy_meta
            else $doc[1],
          $bill := if ($status='new')
            (: open the doc *copy* instead of the doc! 
              This is so @node-id values are correct later in m:index-text() :)
            then db:open('deepbills', m:scratch-doc-uri($doc[1]/@id))
            else $doc[2]
        for $text in $bill/descendant::text
        where $meta/revision/@status = 'new'
          or ($meta/revision/@status = 'complete' and $text[descendant::cato:*])
        return m:index-text($text, $meta)
      ) into $sims, db:optimize('similars')
    )
  }
};

declare function m:similar-pairs()
as element(pair)* {
  let $doc := db:open('similars','text.xml'),
    $uniq-texts := index:texts($doc)
  for $uniq-text in $uniq-texts[@count = 2]
  let $pairs := db:text($doc, $uniq-text)/..
  where $pairs/@status = 'new' and $pairs/@status = 'complete'
  return element pair {$pairs}
};

declare function m:new-revision-element($docmetaORid as item(), $newrev as element()) {
  let $docmeta := 
    typeswitch ($docmetaORid)
      case xs:string return db:open('deepbills','docmetas/'||$docmetaORid||'.xml')/*
      case document-node(element(docmeta)) return $docmetaORid/*
      case element(docmeta) return $docmetaORid
      default return $docmetaORid,
    $revs := $docmeta/revisions/revision,
    $lastrev := $revs[@id = max($revs/@id)]
  return element revision {
    attribute id { $lastrev/@id + 1 },
    attribute commit-time { fn:current-dateTime() },
    $newrev/@status, $newrev/@committer, $newrev/@doc,
    element description { $newrev/@description }
  }
};


declare updating function m:create-auto-markup-docs($pairs as element(pair)*) {
  (# db:chop false() #) {
    for $pairgroup in $pairs
    let $newtextentry := $pairgroup[1]/text[@status="new"],
      $newdocname := xs:string($newtextentry/@document-name),
      $candidatedoc := fn:substring-after($newtextentry/@document-uri, '/'),
      $updateddoc := 'docs/' || $newdocname || '/' || ($newtextentry/@rev+1) ||'.xml',
      $newdocmeta := db:open('deepbills', 'docmetas/'||$newdocname||'.xml'),
      $newrevisionelem := m:new-revision-element($newdocmeta, <r
        status="auto-markup" committer="/users/scraper.xml" doc="/{$updateddoc}"
        description="Markup copied from completed documents" />)
    group by $newdocname
    return (
      for $pair in $pairgroup
      let $completednode := db:open-pre('deepbills', $pair/text[@status="complete"]/@node-pre),
        $newnode := db:open-pre('deepbills', $pair/text[@status="new"]/@node-pre)
      return (
        delete nodes $newnode/node(),
        insert nodes $completednode/node() into $newnode
      ),
      (: [1] is because we're grouping here (pairs grouped by
        their common "new" doc), but must only do these updates once per group :)
      insert node $newrevisionelem[1] as last into $newdocmeta/docmeta/revisions,
      db:rename('deepbills', $candidatedoc[1], $updateddoc[1])
    )
  }
};

declare updating function m:delete-unmodified-automarkup() {
  for $bn in m:billnames()
  let $d := m:open-bill($bn)
  let $meta := $d[1], $bill := $d[2]
  where $meta/revision/@status = 'auto-markup'
    and $meta/revision/@id = 2
  return (
    delete node doc('deepbills/docmetas/'||$meta/@id||'.xml')
      /docmeta/revisions/revision[@id=$meta/revision/@id],
    db:delete('deepbills', $meta/revision/@doc)
  )
};



(:
  # cleanup and initialization
  XQUERY import module namespace m = "http://deepbills.dancingmammoth.com/modules/helpers"; m:clear-similars-index()
  # lock against further updates so node-pre() works reliably
  OPEN deepbills
  # create copies of status='new' docs for possible modification
  XQUERY import module namespace m = "http://deepbills.dancingmammoth.com/modules/helpers"; m:copy-new-docs()
  # create similars/text.xml index of bill <text> elements
  XQUERY import module namespace m = "http://deepbills.dancingmammoth.com/modules/helpers"; m:index-docs()
  # actually modify the docs
  XQUERY import module namespace m = "http://deepbills.dancingmammoth.com/modules/helpers"; m:create-auto-markup-docs(m:similar-pairs())
  # we're done with node-pre values: close deepbills
  CLOSE 
  # cleanup
  XQUERY import module namespace m = "http://deepbills.dancingmammoth.com/modules/helpers"; m:delete-new-doc-copies()
  OPTIMIZE deepbills
:)



