#!/usr/bin/env python
# -*- coding: utf-8 -*-


from __future__ import print_function, unicode_literals, division, absolute_import

#Osman
import re
import codecs
from pprint import pprint
import getopt
import sys
try:
    from pynlpl.formats import folia
except:
    print("ERROR: pynlpl not found, please obtain PyNLPL from the Python Package Manager ($ sudo easy_install pynlpl) or directly from github: $ git clone git://github.com/proycon/pynlpl.git",file=sys.stderr)
    sys.exit(2)

def usage():
    print("foliamerge",file=sys.stderr)
    print("  by Maarten van Gompel (proycon)",file=sys.stderr)
    print("  Radboud University Nijmegen",file=sys.stderr)
    print("  2017 - Licensed under GPLv3",file=sys.stderr)
    print("",file=sys.stderr)
    print("Merges annotations from two or more FoLiA documents. Structural elements are never added. Annotations can only be merged if their parent elements have IDs.",file=sys.stderr)
    print("",file=sys.stderr)
    print("Usage: foliamerge [options] file1 file2 file3 ... ",file=sys.stderr)
    print("",file=sys.stderr)
    print("Options:",file=sys.stderr)
    print("  -o [file]                    Output file",file=sys.stderr)
    print("  -s                           Substitute: use first input file as output as well",file=sys.stderr)
    print("  -a                           Annotations from file2 onwards are included as alternatives",file=sys.stderr)

def attach(parent, child):
    """Rather than copy children, we just abduct them from the other-doc parent"""
    child.doc = parent.doc
    child.parent = parent
    child.setparents()

def reID(doc, element, oldprefix, newprefix):
    if element.id:
        element.id = element.id.replace(oldprefix + '.', newprefix + '.')
    for child in element.data:
        if isinstance(child, folia.AbstractElement) and not isinstance(child, folia.AbstractStructureElement):
            reID(doc, child, oldprefix, newprefix)

def mergechildren(parent, outputdoc, asalternative):
    if hasattr(parent,'merged'): return 0
    merges = 0
    for e in parent:
        if isinstance(e, (folia.AbstractTokenAnnotation, folia.AbstractAnnotationLayer)) and parent.id and not hasattr(e, 'merged'):
            try:
                e.ANNOTATIONTYPE
            except:
                continue

            if (e.ANNOTATIONTYPE, e.set) in outputdoc.annotations:
                assert e.parent == parent
                try:
                    newparent = outputdoc[parent.id]
                except:
                    continue #parent does not exist, nothing to merge here
                if isinstance(newparent, (folia.Alternative, folia.AlternativeLayers)):
                    #we do not merge alternatives, each alternative has its own scope
                    continue
                #check if the annotation already exists
                #print("DEBUG: Adding annotation type " + e.__class__.__name__ + ", set " + e.set + ", under " + newparent.id, file=sys.stderr)
                if asalternative:
                    if isinstance(e, folia.AbstractTokenAnnotation):
                        #print("Adding Annotation type " + e.__class__.__name__ + ", set " + str(e.set) + " to " + newparent.id + " as alternative", file=sys.stderr)
                        alt = newparent.append(folia.Alternative, generate_id_in=newparent)
                        reID(newparent.doc, e, newparent.id, alt.id)
                        alt.append(e)
                        e.setdoc(outputdoc)
                        assert e.parent is alt
                        alt.merged = True
                        e.merged = True
                        merges += 1
                    elif isinstance(e, folia.AbstractAnnotationLayer):
                        #print("Adding Annotation type " + e.__class__.__name__ + ", set " + str(e.set) + " to " + newparent.id + " as alternative", file=sys.stderr)
                        alt = newparent.append(folia.AlternativeLayers, generate_id_in=newparent)
                        reID(newparent.doc, e, newparent.id, alt.id)
                        alt.append(e)
                        assert e.parent is alt
                        e.setdoc(outputdoc)
                        alt.merged = True
                        e.merged = True
                        merges += 1
                elif isinstance(e, folia.AbstractTokenAnnotation) and newparent.hasannotation(e.__class__, e.set):
                    #print("Annotation type " + e.__class__.__name__ + ", set " + e.set + ", under " + newparent.id + " , already exists... skipping", file=sys.stderr)
                    pass
                elif isinstance(e, folia.AbstractAnnotationLayer) and newparent.hasannotationlayer(e.__class__, e.set):
                    #print("Annotation type " + e.__class__.__name__ + ", set " + e.set + ", under " + newparent.id + " , already exists... skipping", file=sys.stderr)
                    pass
                else:
                    #print("Adding Annotation type " + e.__class__.__name__ + ", set " + str(e.set) + " to " + newparent.id, file=sys.stderr)
                    newparent.append(e)
                    assert e.parent is newparent
                    e.setdoc(outputdoc)
                    e.merged = True
                    merges += 1
        elif isinstance(e, folia.AbstractElement):
            merges += mergechildren(e, outputdoc, asalternative)
    return merges



def foliamerge(outputfile, *files, **kwargs):
    asalternative = 'asalternative' in kwargs and kwargs['asalternative']
    outputdoc = None
    merges = 0

    for i, filename in enumerate(files):
        #print("Processing " + filename, file=sys.stderr)
        inputdoc = folia.Document(file=filename)
        if i == 0:
             #print("(pivot document)",file=sys.stderr)
             outputdoc = inputdoc
        else:
            #print("(merging document)",file=sys.stderr)

            for annotationtype,set in inputdoc.annotations:
                if not outputdoc.declared(annotationtype,set):
                    outputdoc.declare( annotationtype, set)

            for e in inputdoc:
                merges += mergechildren(e, outputdoc, asalternative)
    if outputfile and merges > 0:
        outputdoc.save(outputfile)

    return outputdoc

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "o:sha", ["help"])
    except getopt.GetoptError as err:
        print(str(err),file=sys.stderr)
        usage()
        sys.exit(2)

    outputfile = None
    substitute = False
    asalternative = False

    for o, a in opts:
        if o == '-h' or o == '--help':
            usage()
            sys.exit(0)
        elif o == '-o':
            outputfile = a
        elif o == '-s':
            substitute = True
        elif o == '-a':
            asalternative = True
        else:
            raise Exception("No such option: " + o)

    if len(args) < 2:
        print("ERROR: At least two files need to be specified",file=sys.stderr)
        sys.exit(2)

    if substitute:
        outputfile = args[0]

    outputdoc = foliamerge(outputfile, *args, asalternative=asalternative)

    if not outputfile:
        #print(outputdoc.xmlstring())
        xml = outputdoc.xmlstring()

#Osman-
        counter = 1000
        allentities = re.findall(r'entity\.\d+"',xml)
        uniq_ents = []
        same_ents = []
        for ent in allentities:
            if ent not in uniq_ents:
                uniq_ents.append(ent)
            else:
                same_ents.append(ent)

        #print(uniq_ents)
        #print(same_ents)
        for ent in same_ents:
            replaced_ent = "entity." + str(counter) + '"'
            #print(ent + " to " + replaced_ent)
            xml = re.sub(ent, replaced_ent, xml, 1)
            counter = counter + 1

        xml = re.sub(r"<altlayer[^>]*>|<\/altlayers?>", r"", xml)
#        xml = re.sub(r"\s*<entity annotator=\"(Know-it-all|selim)\"[^<]*(<wref[^>]*>\s*)*\s*(<comment[^<]<\/comment>\s*)*\s*<\/entity>\s*", r"", xml)

#        filename = re.sub(r"^(.*)sumercan_(.*)\.folia\.xml$", r"\g<1>both_\g<2>.folia.xml", args[1])
        annot_2 = re.sub(r"^.*\/([^\/]*)\/[^\/]*$", r"\g<1>", args[1])
#        print(annot_2)
        filename = "../adjudication/" + args[0]
        print(filename)
        with codecs.open(filename, "w", "utf-8") as f:
            f.write(xml)

# This is the part where we add the both annotation to the doc
        doc1_entity = []
        doc2_entity = []
        tobedeleted = []

        doc = folia.Document(file=filename)
        doc.metadata["Done"] = "No"

        for sentence in doc.sentences():

            for layer in sentence.select(folia.EntitiesLayer):

                for entity in layer.select(folia.Entity):

                    if entity.annotator == annot_2:
                        doc2_entity.append(entity)

                    else:
                        doc1_entity.append(entity)

        for entity1 in doc1_entity:
            for entity2 in doc2_entity:
                sorted_doc1 = sorted([word.id for word in entity1.wrefs()])
                sorted_doc2 = sorted([word.id for word in entity2.wrefs()])
                entity1_comment = ""
                entity2_comment = ""
                if type(entity1[-1]) == folia.Comment:
                    entity1_comment = entity1[-1].value.lower()
                if type(entity2[-1]) == folia.Comment:
                    entity2_comment = entity2[-1].value.lower()

                if (sorted_doc1 == sorted_doc2) and (entity1.cls == entity2.cls) and (entity1.set == entity2.set) and (entity1_comment == entity2_comment):
                    if entity1_comment == "":
                        entity1.wrefs()[0].add(folia.Entity, *entity1.wrefs(), cls=entity1.cls, set=entity1.set, annotator="Both", annotatortype="auto")
                    else:
                        entity1.wrefs()[0].add(folia.Entity, *entity1.wrefs(), folia.Comment(doc, value=entity1[-1].value, annotator="Both", annotatortype="auto"), cls=entity1.cls, set=entity1.set, annotator="Both", annotatortype="auto")
                    # entity1.annotator = "Both"
                    # entity1.annotatortype = "auto"
                    # new_entity.children.push({'type':'comment', 'value':entity1_comment})
                    try:
                        entity1.parent.remove(entity1)
                        entity2.parent.remove(entity2)
                    except:
                        print("No Parent, Can't delete")
                        tobedeleted.append(entity1.id)
                        tobedeleted.append(entity2.id)

        doc.save()

        if tobedeleted:
            with codecs.open(filename, "r", "utf-8") as g:

                xml = g.read()
                for id in tobedeleted:
                    regex = '\s*<entity.*xml:id="' + re.escape(id) + '">(.|\s)*?<\/entity>'
                    re.sub(regex, r'', xml)

            with codecs.open(filename, "w", "utf-8") as h:
                h.write(xml)

#-Osman
"""
        if sys.version < '3':
            if isinstance(xml, unicode):
                print(xml.encode('utf-8'))
            else:
                print(xml)
        else:
            print(xml)
"""

if __name__ == "__main__":
    main()
