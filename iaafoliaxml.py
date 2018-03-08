#!/usr/bin/env python
#-*- coding:utf-8 -*-

from __future__ import print_function, unicode_literals, division, absolute_import

from pprint import pprint
import re
import argparse
import sys
import json
from itertools import chain
from collections import Counter, defaultdict
try:
    from pynlpl.formats import folia
except:
    print("ERROR: pynlpl not found, please obtain PyNLPL from the Python Package Manager ($ sudo pip install pynlpl) or directly from github: $ git clone git://github.com/proycon/pynlpl.git",file=sys.stderr)
    sys.exit(2)



def is_structural(correction):
    if correction.hasnew(True) and correction.hasoriginal(True):
        iterator = chain(correction.new(), correction.original())
    elif correction.hasnew(True):
        iterator = correction.new()
    elif correction.hasoriginal(True):
        iterator = correction.original()
    for annotation in iterator:
        if isinstance(annotation, folia.AbstractStructureElement):
            return True
    return False

def get_corrections(doc, Class, foliaset):
    """Get relevant corrections from document"""
    for correction in doc.select(folia.Correction):
        structural = is_structural(correction)

        #find targets, i.e. the original tokens this correction applies to
        targets = []
        if structural:
            #structural correction
            if correction.hasoriginal():
                for structure in correction.original():
                    if isinstance(structure, folia.AbstractStructureElement):
                        targets.append(structure)
            elif correction.hasoriginal(allowempty=True):
                #TODO: deal with insertions
                print("INSERTION found but not implemented yet",file=sys.stderr)
                pass
        elif issubclass(Class, folia.AbstractSpanAnnotation):
            #span annotation
            pass #defer until later
        else:
            #token annotation
            targets = [correction.ancestor(folia.AbstractStructureElement)]

        if correction.hasnew():
            annotations = []
            for annotation in correction.new():
                if isinstance(annotation, Class) and (Class in (folia.TextContent, folia.PhonContent) or foliaset is None or annotation.set == foliaset):
                    annotations.append(annotation)
                    if issubclass(Class, folia.AbstractSpanAnnotation):
                        targets += annotation.wrefs()
        elif correction.hasnew(allowempty=True) and structural:
            #TODO: deal with deletion
            print("DELETION found but not implemented yet",file=sys.stderr)
            pass

        yield annotations, targets, correction



def evaluate(docs, Class, foliaset, reference, do_corrections=False, do_confusionmatrix=False, verbose=False):
    assert all((isinstance(doc, folia.Document) for doc in docs))
    nr = len(docs)
    index = []
    for i, doc in enumerate(docs):
        index.append(defaultdict(list))
        if do_corrections:
            for annotations, targets, correction in get_corrections(doc, Class, foliaset):
                targetids = tuple(( target.id for target in targets)) #tuple of IDs; hashable
                for annotation in annotations:
                    index[i][targetids].append( (annotation, correction) )
                    if verbose:
                        value = str(annotation) if isinstance(annotation, (folia.TextContent, folia.PhonContent)) else str(annotation.cls)
                        print("DOC #" + str(i+1) + " - Found annotation (" + value + ") on " + ", ".join(targetids) + " (in correction " + str(correction.id) + ", " + str(correction.cls) + ")",file=sys.stderr)
        else:
            for annotation in doc.select(Class, foliaset):
                if isinstance(annotation, folia.AbstractSpanAnnotation):
                    targets = annotation.wrefs() #TODO: distinguish span roles?
                else:
                    targets = [annotation.ancestor(folia.AbstractStructure)]
                targetids = tuple(( target.id for target in targets)) #tuple of IDs; hashable
                index[i][targetids].append( annotation )
                if verbose:
                    value = str(annotation) if isinstance(annotation, (folia.TextContent, folia.PhonContent)) else str(annotation.cls)
                    print("DOC #" + str(i+1) + " - Found annotation (" + value + ") on " + ", ".join(targetids),file=sys.stderr)

    #linking step: links annotations on the same targets
    links = []
    linkedtargets = []
    linkedtargetids = []
    for j in range(0,nr):
        for targetids in index[j].keys():
            linkchain = []
            if targetids not in linkedtargetids:
                linkedtargetids.append(targetids)
                assert isinstance(docs[j], folia.Document)
                linkedtargets.append([ docs[j][targetid] for targetid in targetids] )
                for i, doc in enumerate(docs):
                    if targetids in index[i]:
                        linkchain.append(index[i][targetids])
                    else:
                        linkchain.append(None)
                links.append(linkchain)

    #evaluation step

    #values can be class or text depending on annotation type
    valuelabel = 'text' if Class in (folia.TextContent, folia.PhonContent) else 'class'

    #truepos = matches
    #falsepos = wrong targets
    #falseneg = misses
    osman_targets = []
    evaluation = {
        'targets': {'truepos':0, 'falsepos': 0, 'falseneg':0, 'description': "A measure of detection, expresses whether the right targets (often words or spans of words) have been annotated, regardless of whether the annotation class/text/value is correct"},
        'osman_targets': [],
        valuelabel: {'truepos': 0, 'falsepos': 0, 'falseneg':0, 'description': "A measure of classification with regard to the text, expresses whether the text matches, i.e. the annotation is correct" if valuelabel == 'text' else "A measure of classification with regard to the annotation class, expresses whether the class matches, i.e. the annotation is correct"},
    }
    if do_confusionmatrix:
        evaluation['confusionmatrix'] = {}

    if do_corrections:
        evaluation.update({
            'correctionclass': {'truepos': 0, 'falsepos': 0, 'falseneg':0, 'description': "A measure expressing only if the correct correction class was assigned, irregardless of the correction itself!" },
            'correction': {'truepos': 0, 'falsepos': 0, 'falseneg':0, 'description': "A measure expressing if the correction is correction with both regard for correction class as well as actual annotation content (" + valuelabel + ")" }
        })
    #compute strong truepos
    for targets, linkchain in zip(linkedtargets, links):
        #targets example: [<pynlpl.formats.folia.Word object at 0x7fa7dfcadfd0>, <pynlpl.formats.folia.Word object at 0x7fa7dfcc00b8>]
        #linkchain example: [[<pynlpl.formats.folia.Entity object at 0x7fa7dfcc0be0>], [<pynlpl.formats.folia.Entity object at 0x7fa7df7a9630>]]
        #                    ^-- outer index corresponds to doc seq
        #annotations are wrapped in (annotation, correction) tuples if do_corrections is true

        evaluator = LinkchainEvaluator()

        evaluator.evaluate(docs, linkchain, Class, reference, do_corrections)


        targets_label = " & ".join([ target.id for target in targets])

        #Osman
#        target_vals = [re.sub(r".*s\.(\d+)\.w\.(\d+)$", r"bothfolia.sentences()[\g<1>].words(\g<2>)", target.id) for target in targets]
        #Class Must be Added !!!!!!
        target_vals = {"match" : False, "values" : [(int(re.search(r"s\.(\d+)\.w\.(\d+)$", target.id).group(1))-1, int(re.search(r"s\.(\d+)\.w\.(\d+)$", target.id).group(2))-1) for target in targets]}
#        pprint(target_vals)
        if evaluator.target_misses:
            if reference and linkchain[0] is None:
                polarity = 'pos'
                polarity_label = "WRONG"
            else:
                polarity = 'neg'
                polarity_label = "MISSED"
            print("[TARGET " + polarity_label+"]\t@" + ",".join([str(x+1) for x in evaluator.target_misses]) + "\t" + targets_label)
            otherdoc = [str(x+1) for x in evaluator.target_misses][0]
            if otherdoc == "2":
                target_vals["doc"] = "1"
            else:
                target_vals["doc"] = "2"
            evaluation['targets']['false'+polarity] += 1
            evaluation[valuelabel]['false'+polarity] += 1

            if do_corrections:
                evaluation['correctionclass']['false'+polarity] += 1
                evaluation['correction']['false'+polarity] += 1
        else:
            evaluation['targets']['truepos']  += 1

            for value in evaluator.value_matches:
                print("[" + valuelabel.upper() + " MATCHES]\t" + targets_label + "\t" + value)

                #Osman
                target_vals["match"] = True

            for value, docset in evaluator.value_misses:
#Didn't take misses into account. Maybe later
                print("[" + valuelabel.upper() + " MISSED]\t@" + ",".join([str(x+1) for x in docset]) + "\t" + targets_label + "\t" + value)
                print("MISSEEEEEEEEEES!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

            if do_corrections:
                for correctionclass in evaluator.correctionclass_matches:
                    print("[CORRECTION CLASS MATCHES]\t" + targets_label + "\t" + correctionclass)
                for correctionclass,docset in evaluator.correctionclass_misses:
                    print("[CORRECTION CLASS MISSED]\t@" + ",".join([str(x+1) for x in docset]) + "\t" +  targets_label + "\t" + correctionclass)
                for correctionclass, value in evaluator.correction_matches:
                    print("[CORRECTION MATCHES]\t" + targets_label + "\t" + correctionclass + "\t" + value)
                for (correctionclass, value), docset in evaluator.correction_misses:
                    print("[CORRECTION MISSED]\t@" + ",".join([str(x+1) for x in docset]) + "\t" + targets_label + "\t" + correctionclass + "\t" + value)

            evaluation[valuelabel]['truepos'] += len(evaluator.value_matches)
            evaluation[valuelabel]['falsepos'] += len(evaluator.value_misses)
            if do_corrections:
                evaluation['correctionclass']['truepos'] += len(evaluator.correctionclass_matches)
                evaluation['correctionclass']['falsepos']  += len(evaluator.correctionclass_misses)
                evaluation['correction']['truepos'] += len(evaluator.correction_matches)
                evaluation['correction']['falsepos']  += len(evaluator.correction_misses)

        if do_confusionmatrix:
            for refkey, counter in evaluator.confusionmatrix.items():
                if refkey not in evaluation['confusionmatrix']:
                    evaluation['confusionmatrix'][refkey] = {}
                evaluation['confusionmatrix'][refkey].update(counter)

        osman_targets.append(target_vals)

    evaluation['osman_targets'] = osman_targets

    try:
        evaluation[valuelabel]['precision'] = evaluation[valuelabel]['truepos'] / (evaluation[valuelabel]['truepos']  + evaluation[valuelabel]['falsepos'])
    except ZeroDivisionError:
        evaluation[valuelabel]['precision'] = 0
    try:
        evaluation[valuelabel]['recall'] = evaluation[valuelabel]['truepos'] / (evaluation[valuelabel]['truepos']  + evaluation[valuelabel]['falseneg'])
    except ZeroDivisionError:
        evaluation[valuelabel]['recall'] = 0
    try:
        evaluation[valuelabel]['f1score'] = 2 * ((evaluation[valuelabel]['precision'] * evaluation[valuelabel]['recall']) /  (evaluation[valuelabel]['precision'] + evaluation[valuelabel]['recall']))
    except ZeroDivisionError:
        evaluation[valuelabel]['f1score'] = 0

    try:
        evaluation['targets']['precision'] = evaluation['targets']['truepos'] / (evaluation['targets']['truepos']  + evaluation['targets']['falsepos'])
    except ZeroDivisionError:
        evaluation['targets']['precision'] = 0
    try:
        evaluation['targets']['recall'] = evaluation['targets']['truepos'] / (evaluation['targets']['truepos']  + evaluation['targets']['falseneg'])
    except ZeroDivisionError:
        evaluation['targets']['recall'] = 0
    try:
        evaluation['targets']['f1score'] = 2 * ((evaluation['targets']['precision'] * evaluation['targets']['recall']) /  (evaluation['targets']['precision'] + evaluation['targets']['recall']))
    except ZeroDivisionError:
        evaluation['targets']['f1score'] = 0

    if do_corrections:
        try:
            evaluation['correctionclass']['precision'] = evaluation['correctionclass']['truepos'] / (evaluation['correctionclass']['truepos']  + evaluation['correctionclass']['falsepos'])
        except ZeroDivisionError:
            evaluation['correctionclass']['precision'] = 0
        try:
            evaluation['correctionclass']['recall'] = evaluation['correctionclass']['truepos'] / (evaluation['correctionclass']['truepos']  + evaluation['correctionclass']['falseneg'])
        except ZeroDivisionError:
            evaluation['correctionclass']['recall'] = 0
        try:
            evaluation['correctionclass']['f1score'] = 2 * ((evaluation['correctionclass']['precision'] * evaluation['correctionclass']['recall']) /  (evaluation['correctionclass']['precision'] + evaluation['correctionclass']['recall']))
        except ZeroDivisionError:
            evaluation['correctionclass']['f1score'] = 0

        try:
            evaluation['correction']['precision'] = evaluation['correction']['truepos'] / (evaluation['correction']['truepos']  + evaluation['correction']['falsepos'])
        except ZeroDivisionError:
            evaluation['correction']['precision'] = 0
        try:
            evaluation['correction']['recall'] = evaluation['correction']['truepos'] / (evaluation['correction']['truepos']  + evaluation['correction']['falseneg'])
        except ZeroDivisionError:
            evaluation['correction']['recall'] = 0
        try:
            evaluation['correction']['f1score'] = 2 * ((evaluation['correction']['precision'] * evaluation['correction']['recall']) /  (evaluation['correction']['precision'] + evaluation['correction']['recall']))
        except ZeroDivisionError:
            evaluation['correction']['f1score'] = 0




    return evaluation


def iter_linkchain(linkchain, do_corrections):
    for i, annotations in enumerate(linkchain):
        if annotations is not None:
            if do_corrections:
                iterator = annotations
            else:
                iterator = [ (annotation, None) for annotation in annotations ]
            for annotation, correction in iterator:
                yield i, annotation, correction

class LinkchainEvaluator:
    def __init__(self):
        self.target_misses = set()

        self.value_matches = []
        self.value_misses = []

        self.correctionclass_matches = []
        self.correctionclass_misses = []

        self.correction_matches = []
        self.correction_misses = []

        self.confusionmatrix = {}

    def evaluate(self, docs, linkchain, Class, reference, do_corrections):
        assert all((isinstance(doc, folia.Document) for doc in docs))

        for i, annotations in enumerate(linkchain):
            if annotations is None:
                self.target_misses.add(i)

        values = defaultdict(set) #abstraction over annotation classes or text content (depending on annotation type)

        correctionclasses = defaultdict(set) #with corrections
        corrections = defaultdict(set)  #full corrections; values and correctionclasses
        refvalue = None
        for docnr, annotation, correction in iter_linkchain(linkchain, do_corrections):
            value = get_value(annotation, Class) #gets class or text depending on annotation type
            values[value].add(docnr)
            if do_corrections and correction:
                correctionclasses[correction.cls].add(docnr)
                corrections[(correction.cls, value)].add(docnr)
            if docnr == 0 and reference and refvalue is None:
                refvalue = value
                self.confusionmatrix[refvalue] = defaultdict(int)
            elif docnr > 0 and reference and refvalue is not None:
                self.confusionmatrix[refvalue][value] += 1



        alldocset = set(range(0,len(docs)))

        for value, docset in values.items():
            if len(docset) == len(docs):
                self.value_matches.append(value)
            else:
                self.value_misses.append( (value, alldocset - docset))

        if do_corrections:
            for correctionclass, docset in correctionclasses.items():
                if len(docset) == len(docs):
                    self.correctionclass_matches.append(correctionclass)
                else:
                    self.correctionclass_misses.append( (correctionclass, alldocset -docset))

            for correction, docset in corrections.items():
                if len(docset) == len(docs):
                    self.correction_matches.append(correction)
                else:
                    self.correction_misses.append( (correction, alldocset - docset))


def all_equal(collection):
    iterator = iter(collection)
    try:
        first = next(iterator)
    except StopIteration:
        return True
    return all(first == rest for rest in iterator)

def get_value(annotation, Class):
    if Class is folia.TextContent or Class is folia.PhonContent:
        return str(annotation)
    return annotation.cls

def main():
    parser = argparse.ArgumentParser(description="FoLiA Evaluator. This tool is used to evaluate annotation on two or more structurally equivalent FoLiA documents. It can provide a measure of inter-annotator agreement, or comparison of system output against a gold standard. It delivers a variery of metrics.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    #Evaluation is expressed as accuracy on the total number of annotation targets (often words) and comes in two flavours: weak and strong. Weak checks only if the same items were marked and can be used as a measure of detection; strong checks if the assigned classes are equal amongst annotators.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    #parser.add_argument('--storeconst',dest='settype',help="", action='store_const',const='somevalue')
    parser.add_argument('-t','--type', type=str,help="Annotation type to consider", action='store',default="",required=True)
    parser.add_argument('-s','--set', type=str,help="Set definition (required if there is ambiguity in the document)", action='store',required=False)
    parser.add_argument('-c','--corrections', help="Use corrections", action='store_true',default="",required=False)
    parser.add_argument('-q','--quiet',dest='verbose', help="Be quiet, do not output verbose information matches/mismatches", action='store_false',default=True,required=False)
    parser.add_argument('-M','--confusionmatrix', help="Output and output a confusion matrix", action='store_true',default="",required=False)
    parser.add_argument('--ref', help="Take first document to be the reference document, i.e. gold standard. If *not* specified all docuemnts are consider equal and metrics yield inter-annotator agreement", action='store_true')
    #parser.add_argument('-i','--number',dest="num", type=int,help="", action='store',default="",required=False)
    parser.add_argument('documents', nargs='+', help='FoLiA Documents')
    args = parser.parse_args()

    docs = []
    for i, docfile in enumerate(args.documents):
        if args.verbose:
            print("Loading DOC #" + str(i+1) + ": " + docfile,file=sys.stderr)
            if args.ref and i == 0:
                print("          ^--- This document acts as the reference documents, i.e. gold standard", file=sys.stderr)
        docs.append( folia.Document(file=docfile))

        #Osman
#        if i == 0:
#            temp = folia.Document(file=docfile)
#            temp.removeAllAnnotations()
#            bothfolia = temp

#Doc1 and doc2 begins with selim_docname and sumercan_docname respectively. These are our annotators
    bothfile = re.sub(r"^\w+_(.*)", r"both_\g<1>", args.documents[0])
    print(str(bothfile))
    bothfolia = folia.Document(file=bothfile)

    try:
        Type = folia.XML2CLASS[args.type]
    except KeyError:
        print("No such type: ", args.type,file=sys.stderr)

    foliaset = args.set
    if args.verbose:
        print("type=" + repr(Type),file=sys.stderr)
        print("set=" + repr(foliaset),file=sys.stderr)
        if args.ref:
            print("reference document provided (--ref)", file=sys.stderr)
        else:
            print("no reference document provided, all documents treated equal and computing inter-annotator agreement", file=sys.stderr)

    if args.ref:
        print("{")
        for i, doc in enumerate(docs[1:]):
            if i > 0: print(",")
            evaldocs = [docs[0], doc]
            evaluation = evaluate(evaldocs, Type, foliaset, True, args.corrections, args.confusionmatrix, args.verbose)
            print("\"" + doc.filename + "\": " + json.dumps(evaluation, indent=4))
        print("}")
    else:
        evaluation = evaluate(docs, Type, foliaset, False, args.corrections, args.confusionmatrix, args.verbose)
        print(json.dumps(evaluation, indent=4))

        #Osman
        wordc = 0
        for sentence in docs[0].sentences():
            for word in sentence.words():
                wordc = wordc + 1
        truean = evaluation['class']['truepos']
        falsean = evaluation['class']['falseneg'] + evaluation['class']['falsepos']
        cohen_kappa = ((truean/(truean+falsean))-((truean+falsean)/wordc))/(1-((falsean+truean)/wordc))
        print("Cohen's Kappa Score : " + str(cohen_kappa))

#Class Must be added!!!!!!!
        targets_doc2 = []
        targets_doc1 = []
        sentences = list(bothfolia.sentences())
        for target_vals2 in evaluation['osman_targets']:
            wordsList = []
            for value in target_vals2["values"]:
                wordsList.append(sentences[value[0]].words(value[1]))
#            print("words", wordsList)
            if target_vals2["match"]:
                wordsList[0].add(folia.Entity, *wordsList, cls="place", set=foliaset, annotator="Both")
            else:
                if target_vals2["doc"] == "1":
                    targets_doc1.append(target_vals2["values"])
#                    pprint(target_vals2["values"])
                else:
                    targets_doc2.append(target_vals2["values"])

        partial_match_count = 0
        partial_miss_count = 0
        for target_vals3 in targets_doc1:
#            target_vals3 = list(target_vals3.items())
#            pprint(target_vals3)
            if not targets_doc2:
                #annotate target_vals3
                wordsList_vals3 = []
                for value in target_vals3:
                    wordsList_vals3.append(sentences[value[0]].words(value[1]))
                wordsList_vals3[0].add(folia.Entity, *wordsList_vals3, cls="place", set=foliaset, annotator="Doc1")

                partial_miss_count = partial_miss_count + len(target_vals3) - 1

                continue

            same_lens = []
            for i,target_vals4 in enumerate(targets_doc2):

                same = list(set(target_vals3) & set(target_vals4))
#                print(same)
                if same:
                    same_lens.append(len(same))
                else:
                    same_lens.append(0)
#            pprint(targets_doc2)

# Maybe not only the longest but every same != 0 should be accounted (for 1 span in doc1 -> 2 spans in doc2 situtations)
            longest_len = sorted(same_lens)[-1]
            if longest_len != 0:
                partial_match_count = partial_match_count + longest_len
                ind = same_lens.index(longest_len)
                wordsList_same = []
                sameSet = set(target_vals3) & set(targets_doc2[ind])
                vals4_unique_list = list(set(target_vals3) - sameSet)
                # -1 because we already add one to falsean for every span annotation
                partial_miss_count = partial_miss_count + len(vals4_unique_list) - 1
                wordsList_doc1 = []
                vals3_unique_list = list(set(targets_doc2[ind]) - sameSet)
                partial_miss_count = partial_miss_count + len(vals3_unique_list) - 1
                wordsList_doc2 = []
                for value in list(sameSet):
                    wordsList_same.append(sentences[value[0]].words(value[1]))
                for value in vals4_unique_list:
                    wordsList_doc1.append(sentences[value[0]].words(value[1]))
                for value in vals3_unique_list:
                    wordsList_doc2.append(sentences[value[0]].words(value[1]))
                #annotate same and uniques
                if wordsList_same:
                    wordsList_same[0].add(folia.Entity, *wordsList_same, cls="place", set=foliaset, annotator="Both")
                if wordsList_doc1:
                    wordsList_doc1[0].add(folia.Entity, *wordsList_doc1, cls="place", set=foliaset, annotator="Doc1")
                if wordsList_doc2:
                    wordsList_doc2[0].add(folia.Entity, *wordsList_doc2, cls="place", set=foliaset, annotator="Doc2")
                #remove target_vals4
                del targets_doc2[ind]
            else:
                #annotate target_vals3
                wordsList_vals3 = []
                for value in target_vals3:
                    wordsList_vals3.append(sentences[value[0]].words(value[1]))
                wordsList_vals3[0].add(folia.Entity, *wordsList_vals3, cls="place", set=foliaset, annotator="Doc1")

        if targets_doc2:
            for target_vals4 in targets_doc2:

                wordsList_vals4 = []
                for value in target_vals4:
                    wordsList_vals4.append(sentences[value[0]].words(value[1]))
                wordsList_vals4[0].add(folia.Entity, *wordsList_vals4, cls="place", set=foliaset, annotator="Doc2")

                partial_miss_count = partial_miss_count + len(target_vals4) - 1

    bothfolia.save("/home/osman/work/iaa/xmls/both_" + foliaset[57:-13] + re.sub(r"^both_(.*)", r"_\g<1>", bothfile))

    truean = truean + partial_match_count
    falsean = falsean + partial_miss_count

    cohen_kappa = ((truean/(truean+falsean))-((truean+falsean)/wordc))/(1-((falsean+truean)/wordc))

    print("Cohen Kappa's Score for Partial Match is : " + str(cohen_kappa))

if __name__ == "__main__":
    main()
