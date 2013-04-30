Cato XML Reference
==================

Last updated: 2013-04-30

This document describes CatoXML, which is a number of inline semantic metadata
extensions to “HouseXML” in the `http://namespaces.cato.org/catoxml` namespace.

“HouseXML” is an unofficial term for the XML schema of legislation drafted
by the United States Congress (House and Senate) and documented at 
[xml.house.gov][HouseXML].

These metadata extensions are collectively called “CatoXML”.

[HouseXML]: http://xml.house.gov

Definitions
-----------

Prefix `cato:` is bound to namespace `http://namespaces.cato.org/catoxml`

Attribute names are prefixed with `@`; e.g. `@foobar` for an attribute
named `foobar`.

A metadata element is an element that expresses metadata about a span
of text. CatoXML defines four metadata elements: `cato:entity`,
`cato:property`, `cato:funds-and-year`, and `cato:entity-ref`. Certain
HouseXML elements can also express metadata equivalent to CatoXML
elements.

`cato:entity` Element
---------------------

Used to contain text that creates an entity. Any child metadata
elements are properties of the immediate parent entity.

### Attributes of `cato:entity` ###

`@entity-type`: Required. States the type of the entity. Valid
values are:

  * `law-citation`: Parallel Law Citation: used to contain multiple law
   citations which are equivalent.
  * `auth-authorization`: Authorization
  * `auth-regulation`: Regulation
  * `auth-interpretation`: Desired interpretation of a passage by
   Congress.
  * `auth-auth-approp`: Authorizations of Appropriations (species of
   "Budget Authority")
  * `auth-approp`: Appropriations (species of "Budget Authority")

Note: the `auth-authorization`, `auth-regulation`, and `auth-interpretation`
types are currently unused, but these names are reserved for future use.

`cato:property` Element
-----------------------

Used to contain text which is constitutive of an entity but which is not
itself an entity or reference to an entity.

A `cato:property` element must be contained by a `cato:entity` element.

### Attributes of `cato:property` ###

1. `@name`: **Required.**  States the name of this property.  Property names
   are specific to a certain entity type.  Two property names are defined:
   * `funds-source`: used to contain the source of funds for an
     `auth-auth-approp` or `auth-approp` entity.
   * `purpose`: used to contain the purpose of an authority entity
     (`auth-auth-approp`, or `auth-approp`).

2. `@value`: States the machine-readable value of this property. If the
   property element contains text, then this attribute contains a
   normalized, machine-readable version of that text. If this
   attribute is omitted, then the value of this property is the text
   content of this element and it is not required to be
   machine-readble.

`cato:funds-and-year` Element
-----------------------------

Used to contain text that indicates the amount of funds made available
and the year during which those funds are made available by an
authority entity. An authority entity may have multiple
`cato:funds-and-year` elements.

This element exists as a shorthand for document markup to avoid the
need for id references and empty elements for one or another of its
property values. It expresses the same information as the following
set of `cato:entity` and `cato:property` elements:

    <entity entity-type="funds-and-year"><property name="amount"
    value="1000">$1000</property> in <property name="year"
    value="2011">2011</property></entity>

### Attributes of cato:funds-and-year ###

 1. `@amount`: Required. States the amount of money in US dollars that
    the authority proposes to be set aside. This attribute’s value is
    a positive integer or the special value `indefinite`, indicating
    that no specific amount was named.
 2. `@year`: Required. States the fiscal years during which the stated
    amount may be spent. This attribute’s value is a set of fiscal
    years expressed as one of the following:

    * A four-digit integer, indicating that the `@amount` is
      appropriated once to be spent during the indicated year.
    * A list of four digit integers separated by commas (e.g.
      `2012,2013,2014`) indicating that the `@amount` is appropriated
      again at the beginning of each listed fiscal year. This
      syntax is equivalent to using multiple `cato:funds-and-year`
      elements with a single fiscal year for each one.
    * A single four-digit year followed by a comma and two periods
      (e.g. `2013,..`) indicating that the `@amount` is appropriated
      at the beginning of the first indicated year and
      re-appropriated again at the beginning of each following year
      in perpetuity.
    * Two four-digit integers joined by two periods, e.g.
      (`2012..2014`), indicating that the `@amount` is appropriated
      once at the beginning of the fiscal year on the left-hand
      side and is available to be spent until the end of the fiscal
      year on the right-hand side. For example,
      `<cato:funds-and-year funds="100" year="2012..2014"/>`
      indicates that $100 is made available at the beginning of the
      2012 fiscal year and is available until the end of the 2014
      fiscal year.
    * A single four-digit integer followed by two dots (e.g.,
      `2013..`), indicating that the `@amount` is appropriated once
      and is available until it is expended.
    * Nothing, indicating that no fiscal year is discernible from the text.

`cato:entity-ref` Element
-------------------------

Used to contain text that refers to but does not create an entity.

### Attributes of `cato:entity-ref` ###

In addition to `@entity-type`, one and only one of the `entity-id`,
`entity-parent-id`, or `value` attributes are required.

1. `@entity-type`: Required. States the type of entity that the
   enclosed text references. Valid values are:

   * `federal-body`: Federal organizational unit citation, including
     Agencies and Bureaus. Uses the `@entity-id` or
     `@entity-parent-id` attribute.
   * `committee`: Congressional Committee citation. Uses the
     `@entity-id` attribute.
   * `person`: Federal elective officeholder citation. Uses the
     `@entity-id` attribute.
   * `act`: Popular name citation. Uses the `@value` attribute.
   * `uscode`: US Code section, chapter, or appendix citation. Uses
     the `@value` attribute.
   * `public-law`: Public law citation. Uses the `@value` attribute.
   * `statute-at-large`: Statutes at Large citation. Uses the `@value`
     attribute.

2. `entity-id`: States the id of the entity that the enclosed text references.
   Entity ids must be unique among all others with the same entity-type.
3. `entity-parent-id`: States the id of the parent entity of the entity that
   the enclosed text references. This attribute is used when the entity does
   not have an id or its id is not known but a parent entity is known.
4. `value`: Expresses the content of the text of the entity-ref (not of the
   entity) in a consistent, documented, machine-parsable format
   specific to its entity-type. Different `value` attribute values may
   refer to the same entity.
5. `proposed`: States whether the current entity reference is to an
   existing or a proposed entity. The value of this attribute is
   `true` or `false`. If this attribute is absent, then the value of
   this attribute is `false`. This attribute may be found on uscode
   or act entities.

### Notes on `entity-refs` ###

The `act`, `uscode`, `public-law`, and `statute-at-large` entity-types lack
an `@entity-id` or `@entity-parent-id` attribute because:

1. There is no universally-agreed-upon unique identifier for the entities they
   cite.
2. Different `@value` values may reference the same entity. This is unlike an 
   `@entity-id`, where every entity has exactly one id.

### Values for CatoXML `cato:entity-ref` value ###

All entity-ref value attributes use a series of slash-delimited
segments. For example, `usc/1/234` cites title 1, section 234 of the
U.S. Code. This is equivalent to "1 U.S.C. 234" in the common citation
format. The meaning and parsing of individual segments is determined
by the value of the first segment.

#### `uscode` ####

* **U.S.C. Section**. Segments are:
  1. Fixed string `usc`
  2. Title number
  3. Section number
  4. Further optional segments are subparts of Section, starting
     with subsection. For example `usc/1/2/a/i` cites title 1,
     section 2, subsection 3, paragraph a, subparagraph i. It is
     equivalent to "1 U.S.C. 2(a)(i)" in the common citation
     format. The last segment may indicate an inclusive range of
     document parts by using two citation values separated by
     double-periods, e.g. `usc/1/2/a..d` is equivalent to "1 U.S.C.
     2(a) through 1 U.S.C 2(d)".
  5. The final segment may contain the special value `note` or
     `etseq` to indicate that the citation is to a note to the
     current section (e.g. "1 U.S.C. 2 note") or a reference to
     this and the following sections (e.g. "1 U.S.C. 2 et seq.").
     If there is no special citation this segment is omitted.

* **U.S.C. Chapter**. Segments are:
  1. Fixed string `usc-chapter`
  2. Title number
  3. Chapter number
  4. Subchapter number. If there is no subchapter citation this
     segment is omitted.
  5. The final segment may contain the special value `note` or
     `etseq`, as with U.S.C. Section citations.

* **U.S.C. Appendix**. A citation to an appendix of a title of the U.S.
  Code and optionally to a section, e.g. "1 U.S.C App. 234"
  1. Fixed string `usc-appendix`
  2. Title number
  3. Optionally a section number. Since section numbering is not
     always unambiguous in U.S.C. Appendixes, this segment may be
     absent. The common citation format would simply read "1
     U.S.C. App."
  4. The final segment may contain the special value `note` or
     `etseq`, as with U.S.C. Section citations.

#### `statute-at-large` ####

A reference to a page in a volume of the Statutes at Large. The normal
citation "90 Stat. 2541" would be expressed as `statute-at-large/90/2541`.
Segments are:

1. Fixed string "statute-at-large". (Note for compatibility with
   HouseXML "statute" is singular.)
2. Statutes at Large volume number.
3. Statutes at Large page number. The page number may be an inclusive
   range if two numbers are joined by a double-period, e.g.
   `2541..2543` indicates pages 2541 through 2543.

#### `act` ####

A reference to an act by its popular name. There is very little
uniformity among act citations so machine-parsable act citation values
utilize a system of prefixes to indicate segment types. The normal
citation "1861(s)(2) of the Social Security Act" would be expressed as
Social Security `Act/s:1861/ss:s/p:2`. Segments are:

1. A popular name for an act taken verbatim from the Office of the
   Law Revision Council’s table of popular names, or from the text
   contained by an HouseXML act-name element in the current document
   that names the current document, or the compact FDsys name of the
   bill with its version suffix (e.g., "113hconres2ih"). The latter
   two values are only used if the reference is to the current bill.
   A single act may have multiple popular names, and no attempt is
   made to establish one unique canonical popular name per act. The
   act name may contain any character except `/` (forward slash).
2. Further optional segments are citations reflecting the parts of
   the document explicitly mentioned by the text of the citation:

   * Segments must be listed in order from broadest document part
     to narrowest document part. (N.B., document part hierarchy
     may vary from act to act.)
   * Segment citations consist of a prefix to indicate the segment
     type, a colon, and a value to indicate the letter or number
     of that segment citation. For example, `t:I` cites "title
     one".
   * The following prefixes are defined:

     * division `d`
     * title `t`
     * subtitle `st`
     * part `pt`
     * subpart `spt`
     * chapter `ch`
     * subchapter `sch`
     * section `s`
     * subsection `ss`
     * paragraph `p`
     * subparagraph `sp`
     * clause `cl`
     * subclause `scl`
     * item `i`
     * subitem `si`

   * The last segment citation value may use a double-period to
     indicate a range. For example, `t:I..V` indicates title 1
     through title 5. Only the last segment citation value may use
     a range because the citation would be ambiguous otherwise.
     For example, `Social Security Act/t:I..V/s:6` is ambiguous, as
     it is not clear which section six is indicated.

3. The final segment may contain the special value `note` or `etseq`,
   as with U.S.C. Section citations.

#### `public-law` ####

A reference to a Public Law. The normal citation "P.L. 111-12" would
be expressed as `public-law/111/12`. Segments are:

1. Fixed string `public-law`
2. Congress number
3. Law number
4. Following the third segment, a public law citation value may use
   part-prefixed segments exactly as described in number 2 in the "acts"
   section above. For example, `public-law/111/12/t:I` indicates "title I of
   P. L. 111-12".

Mapping HouseXML metadata elements to CatoXML metadata elements
---------------------------------------------------------------

Certain elements in HouseXML can express the same information as a
CatoXML element. If a HouseXML element is present in a document and
would express the same information as a CatoXML element, no CatoXML
element is added. This section defines rules for determining the
semantically equivalent CatoXML for a HouseXML element.

<table border="1" cellpadding="2">
 <thead bgcolor="lightgrey">
  <tr><th>Entity type</th> <th>HouseXML</th> <th>CatoXML</th></tr>
 </thead>
 <tbody>
  <tr>
   <td>Committee</td>
   <td><code>&lt;committee-name committee-id="<b>CID</b>"></code></td>
   <td><code>&lt;cato:entity-ref entity-type="committee" entity-id="<b>CID</b>"></code></td>
  </tr>
  <tr>
   <td>Person</td>
   <td><code>&lt;sponsor name-id="<b>BIOID</b>"></code></td>
   <td><code>&lt;cato:entity-ref entity-id="<b>BIOID</b>"></code></td>
  </tr>
  <tr>
   <td>Person</td>
   <td><code>&lt;cosponsor name-id="<b>BIOID</b>"></code></td>
   <td><code>&lt;cato:entity-ref entity-id="<b>BIOID</b>"></code></td>
  </tr>
  <tr>
   <td>Act (Popular Name)</td>
   <td><code>&lt;act-name><b>Name of Act</b>&lt;/act-name></code></td>
   <td><code>&lt;cato:entity-ref entity-type="act" value="<b>Name of Act</b>">
    <b>Name of Act</b>&lt;/cato:entity-ref></code>
    <sup><a href="#note1" id="note1-ref">Note</a></sup></td>
  </tr>
  <tr>
   <td>U.S. Code Section</td>
   <td><code>&lt;external-xref legal-doc="uscode" parseable-cite="<b>Citation Value</b>"></code></td>
   <td><code>&lt;cato:entity-ref entity-type="usc" value="<b>Citation Value</b>"></code></td>
  </tr>
  <tr>
   <td>U.S. Code Chapter</td>
   <td><code>&lt;external-xref legal-doc="usc-chapter" parseable-cite="<b>Citation Value</b>"></code></td>
   <td><code>&lt;cato:entity-ref entity-type="uscode" value="<b>Citation Value</b>"></code></td>
  </tr>
  <tr>
   <td>U.S. Code Appendix</td>
   <td><code>&lt;external-xref legal-doc="usc-appendix" parseable-cite="<b>Citation Value</b>"></code></td>
   <td><code>&lt;cato:entity-ref entity-type="uscode" value="<b>Citation Value</b>"></code></td>
  </tr>
  <tr>
   <td>Public Law</td>
   <td><code>&lt;external-xref legal-doc="public-law" parseable-cite="<b>Citation Value</b>"></code></td>
   <td><code>&lt;cato:entity-ref entity-type="public-law" value="<b>Citation Value</b>"></code></td>
  </tr>
  <tr>
   <td>Statutes at Large</td>
   <td><code>&lt;external-xref legal-doc="statute-at-large" parseable-cite="<b>Citation Value</b>"></code></td>
   <td><code>&lt;cato:entity-ref entity-type="statute-at-large" value="<b>Citation Value</b>"></code></td>
  </tr>
 </tbody>
</table>

<strong id="note1">[Note:](#note1-ref)</strong>`act-name`'s  `@parseable-cite`
is ignored because the vocabulary is unpublished. If it is ever released, its
value may be used in a `cato:entity-ref` `@entity-id` attribute.

Entity Lookup Tables
--------------------

Entity lookup tables are references for entities indexed by entity-id.
They have the following structure shared by all entity types:

1. `entities` root element.

   * `entities` has an required `@type` attribute expressing the
     entity type of all child elements. The value of this
     attribute matches the `@entity-type` attribute used on
     `cato:entity` and `cato:entity-ref` attributes.
   * `entities` has a required `@updated` attribute indicating the
     date and time the entity lookup table was last updated in
     iso8601 format, e.g. `2012-12-30T13:30:02`.
   * entites has an optional attribute `@version` whose value is
     entity-type specific. This attribute is used to fix a lookup
     table to a specific point in time relevant to a specific set
     of documents. For example, the list of agencies and bureaus
     (federal-body) may vary from year to year as some are added,
     others removed, and bureaus are restructured into different
     agencies. However, these older lists are still relevant, as
     legislation and other documents from those time periods will
     still need to identify them. Thus a `@version` attribute may be
     included with (for example) a fiscal year or congress number
     to indicate that it lists the state of the world of
     federal-bodies during that period. This is different from a
     lookup table with a newer `@updated` value: in this case the
     older document should merely be discarded. In other words, a
     lookup table is “updated” when it is corrected or added to,
     but “versioned” when the world changes in a
     backwards-incompatible way but the older lookup table needs
     to be kept for older documents.
   * entity-types may define further entity-type-specific
     attributes on this element.

2. `entity` child elements of `entities` contain information regarding a
   particular entity. They have a basic structure shared by all
   entity types which may be extended by particular entity types.
   * entity elements have a required `@id` attribute which indicates
     the id of the entity.
   * entity elements may have a `@parent-id` attribute which refers
     to another entity in the table as its parent. The precise
     semantic meaning of this "parent" relationship varies by
     entity-type. Some entity types do not have parent-child
     relationships among entities.
   * entity elements may have one or more `name` or `abbr` elements to
     indicate names and abbreviations for the entity. The value of
     this element is contained as text.
   * `name` and `abbr` elements have an optional `@role` attribute to
     indicate the role of the name. Predefined values are:
     * `official` for official names and abbreviations.
     * `historical` for older names and abbreviations no longer
       in common use.
     * Entity types may define and use other
       entity-type-specific values.
   * **Name and abbr sorting order.** The order of preference for an
     entity’s names and abbreviations is determined in this way:

     1. Names and abbreviations with a `@role` attribute with
        value `official` rank first. If there are multiple such
        names or abbreviations, they are ranked in document
        order.
     2. All other names and abbreviations are ranked below the
        official ones in document order.

### Entity-Type specific extensions ###

Certain entity types make use of the various extension points provided
by the lookup table format and described in the previous section. These
entity-type specific extensions are documented below.

#### Committees ("committee" entities) ####

These committee and subcommittee id values are consistent with those
found in the `@committee-id` attribute of the `committee-name` element of
[House XML][HouseXML].

Subcommittees indicate their parent Committee with the `@parent-id`
attribute.

#### People ("person" entities) ####

Person `@id` values are [Bioguide ids](http://bioguide.congress.gov).

The `@version` attribute on the `entity` element indicates a congressional
session. The lookup table is expected to contain a comprehensive list
of every congressman who served during that session of congress.

The `entity` element may have the following additional attributes:

* `@govtrackid` to indicate a govtrack id
* `@title`: `Rep.` to indicate a representative, `Sen.` to indicate a
   senator, `Del.` to indicate a delegate.
* `@state` and a two-leter postal state to indicate the state of the
  seat the congressman occupies.
* `@district` to indicate the district number of the seat the
   Representative occupies.

The `name` element includes a full name of the senator, with title,
party, and state. E.g.: `Rep. Gary Ackerman (D, NY-5)`.

The `name` element may have the following optional attributes:

* `@firstname` to indicate the first name of the congressman.
* `@lastname` to indicate the last name of the congressman.

#### Agencies and Bureaus (“federal-body” entities) ####

The `@entity` element may have the following additional attributes:

* `@omb-agency` a crosswalk to the three-digit Office of Management
  and Budget (OMB) agency code
* `@omb-bureau` a crosswalk to the two-digit OMB bureau code
* `@treasury-code` a crosswalk to the two-digit Treasury Account
  Symbol (TAS) code.

Additionally, the `@role` attribute of the `name` element may have the value
`leadership`, which indicates that the name is the position of the senior
director of the named federal body. This role is included because bills often
direct an agency to do something using language that names the highest
position in that agency. For example, "The Happiness Czar shall expend $5
million in fiscal year 2013 to promote happiness abroad". Here, "Happiness
Czar" would be a `<name role="leadership">` entry for the fictional "Bureau
of Happiness".
