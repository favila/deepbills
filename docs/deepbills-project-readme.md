Deepbills Project
=================

The Deepbills project takes the raw XML of Congressional bills (available at 
[FDsys][fdsys] and [Thomas][thomas]) and adds additional semantic information 
to them in inside the text.

You can download the continuously-updated data at 
[http://deepbills.cato.org/download][data-download].

Background
----------

Congress already produces machine-readable XML of almost every bill it 
proposes, but that XML is designed primarily for formatting a paper copy, not 
for extracting information. For example, it’s not currently possible to find 
every mention of an Agency, every legal reference, or even every spending 
authorization in a bill without having a human being read it.

We’ve done the hard work for you. Using a combination of hand-tagging and 
automated parsing, we take information-poor XML that looks like this (from 113 
H.R. 86):

    <subsection id="HEC8C7AD0C7D44C69A94F90F052E505A1">
        <enum>(d)</enum>
        <header>Institution of higher education defined</header>
        <text>In this section the term <quote>institution of higher education</quote> has the meaning given that term in section 101(a) of the Higher Education Act of 1965 (20 U.S.C. 1001(a)).</text>
    </subsection>
    <subsection id="HF6A1A9C99D6144B6AB33ECDCD55A05C6">
        <enum>(e)</enum>
        <header>Authorization of appropriations</header>
        <text>There is authorized to be appropriated to the Secretary for carrying out this section $3,700,000 for each of fiscal years 2012 and 2013.</text>
    </subsection>

And augment it until it looks like this:

    <subsection id="HEC8C7AD0C7D44C69A94F90F052E505A1" xmlns:cato="http://namespaces.cato.org/catoxml">
        <enum>(d)</enum>
        <header>Institution of higher education defined</header>
        <text>In this section the term <quote>institution of higher education</quote> has the meaning given that term in <cato:entity entity-type="law-citation"><cato:entity-ref entity-type="act" value="Higher Education Act of 1965/s:101/ss:a">section 101(a) of the Higher Education Act of 1965</cato:entity-ref> (<cato:entity-ref entity-type="uscode" value="usc/20/1001/a">20 U.S.C. 1001(a)</cato:entity-ref>)</cato:entity>.</text>
    </subsection>
    <subsection id="HF6A1A9C99D6144B6AB33ECDCD55A05C6"
    xmlns:cato="http://namespaces.cato.org/catoxml">
        <enum>(e)</enum>
        <header>Authorization of appropriations</header>
        <text><cato:entity entity-type="auth-auth-approp">There is authorized to be appropriated to the <cato:entity-ref entity-type="federal-body" entity-id="7000">Secretary</cato:entity-ref> <cato:property name="purpose">for carrying out <cato:entity-ref entity-type="act" value="Cybersecurity Education Enhancement Act of 2013/s:2" proposed="true">this section</cato:entity-ref></cato:property> <cato:funds-and-year amount="3700000" year="2012, 2013">$3,700,000 for each of fiscal years 2012 and 2013</cato:funds-and-year>.</cato:entity></text>
    </subsection>

Notice none of the text of the bill has changed; rather the information in the 
bill has been made explicit so that a computer can find and extract it.

What information is tagged?
---------------------------

Currently the following information is tagged:

* Legal citations
    * Public Laws (E.g., “P.L. 113-1”)
    * Popular names (E.g., “The Happiness Protection Act”)
    * US Code
    * Statutes at Large
* Budget Authorities (both Authorizations of Appropriations and Appropriations)
    * The source of funds
    * The purpose of the authorization
    * The dollar amount and years appropriated
* Agencies, bureaus, and subunits of the federal government.
* Congressional committees
* Federal elective officeholders (Congressmen)

Where possible, entities are identified with a commonly-used unique 
identifier, such as a [Bioguide ID][bioguide] for congressmen and an 
[SP800-87 code][nist-code] for agencies and bureaus.

How do you tag the bills?
-------------------------

All our bill augmentation is done using new XML elements in the 
`http://namespaces.cato.org/catoxml` namespace which we refer to informally as 
"CatoXML". We have [meticulously documented][catoxml] the elements and 
attributes in this namespace so that anyone can read *or* write documents that 
use them.

We have also created XML lookup tables for the lists of IDs we use for various 
entities. This is bundled with the [downloadable data][data-download] and its 
format is also [meticulously documented][catoxml].

You can read all about XML and CatoXML in [our XML guide][xmlguide].

What can I do with this data?
-----------------------------

All the underlying source XML for the bills (from GPO/FDsys or the Library of Congress) is public domain.

All the augmented bills and vocabulary lookup tables that you can [download from us in bulk][data-download] are also public domain.

The specification of the [CatoXML namespace][catoxml] itself is controlled by
the Deepbills project, although it has been designed to be extensible. You are
free to write CatoXML and to extend it in the ways indicated in the [CatoXML
documentation][catoxml]. However, we ask that you let us know what your
extensions are so we can document them.

How do I get started?
---------------------

1. [Download the bulk data][data-download]
2. [Read the spec][catoxml]
3. Use the data! Some ideas:
    * Transform the bill XML into deeply-interlinked data in some other format.
      For example, [wikisourceify][wikisourceify] uses this data to create 
      Wikitext for Wikisource with links to relevant Wikipedia articles right 
      in the bill text.
    * Extract the data and express it as [Legislative metadata RDF triples][cornell-rdf]
    * Using this data and other sources, create summary statistics about the 
      bills in Congress. What correlations are there between representatives 
      and the laws and agencies affected by the bills they sponsor and 
      cosponsor? Is it committee membership, seniority, party, state/region, 
      or something else? What about the spending they propose?
    * Build a Web site, app, or information service that interprets this data
      for the public. There is new information in this data that the public 
      would benefit from knowing. It’s up to you to figure out how to inform 
      them.

We’d love to learn about what you build. Please let us know in the
[Cato Government Transparency Data Google group][googlegroup].

We’ll be happy to help you, and we'd be delighted to learn how we can do things better.

[data-download]: http://deepbills.cato.org/download
[fdsys]: http://www.gpo.gov/fdsys/browse/collection.action?collectionCode=BILLS
[thomas]: http://thomas.loc.gov/home/thomas.php
[bioguide]: http://bioguide.congress.gov
[nist-code]: http://csrc.nist.gov/publications/nistpubs/800-87-Rev1/SP800-87_Rev1-April2008Final.pdf
[cornell-rdf]: http://blog.law.cornell.edu/metasausage/downloads-and-related-information/
[catoxml]: http://namespaces.cato.org/catoxml
[wikisourceify]: https://github.com/favila/wikisourceify
[xmlguide]: http://example.org
[googlegroup]: https://groups.google.com/forum/#!forum/cato-government-transparency-data