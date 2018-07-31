from __future__ import print_function
from pynlpl.formats import fql, folia
import sys
import re
import codecs
import pandas
import numpy as np

annot1 = "selim"
annot2 = "sumercan"

Event_out = pandas.DataFrame()
Part_out = pandas.DataFrame()
Org_out = pandas.DataFrame()
Target_out = pandas.DataFrame()


doc1file = sys.argv[1]
doc2file = re.sub(r"^([^\/]*\/)\w+_(http.*)$",r"\g<1>sumercan_\g<2>",doc1file)

doc1 = folia.Document(file=doc1file)

doc2 = folia.Document(file=doc2file)

df = pandas.DataFrame()

for i,sentence in enumerate(doc1.sentences()):

    for layer in sentence.select(folia.EntitiesLayer):

        for entity in layer.select(folia.Entity):

            for wref in entity.wrefs():
                df = df.append({"word":re.sub(r'.*\.(p\.\d+\.s\.\d+\.w\.\d+)$',r'\g<1>',wref.id),"annotator":annot1,"focus":entity.set,"tag":entity.cls}, ignore_index=True)

for i,sentence in enumerate(doc2.sentences()):

    for layer in sentence.select(folia.EntitiesLayer):

        for entity in layer.select(folia.Entity):

            for wref in entity.wrefs():
                df = df.append({"word":re.sub(r'.*\.(p\.\d+\.s\.\d+\.w\.\d+)$',r'\g<1>',wref.id),"annotator":annot2,"focus":entity.set,"tag":entity.cls}, ignore_index=True)

df.drop_duplicates(inplace=True)

df = df.sort_values(by=["word"])

Event_df = df[df['focus'] == "https://github.com/OsmanMutlu/rawtext/raw/master/protes6-Event.foliaset.xml"]
Part_df = df[df['focus'] == "https://github.com/OsmanMutlu/rawtext/raw/master/protes4-Participant.foliaset.xml"]
Org_df = df[df['focus'] == "https://github.com/OsmanMutlu/rawtext/raw/master/protes3-Organizer.foliaset.xml"]
Target_df = df[df['focus'] == "https://github.com/OsmanMutlu/rawtext/raw/master/protes1-Target.foliaset.xml"]

def organize_data(in_df):

    out_df = pandas.DataFrame()
    words = in_df.word.unique()
    words = list(words)

    for word in words:

        tag1 = "empty"
        tag2 = "empty"
        firstdf = in_df.loc[(in_df['word'] == word) & (in_df['annotator'] == annot1)]
        seconddf = in_df.loc[(in_df['word'] == word) & (in_df['annotator'] == annot2)]

        if not len(firstdf) == 0:
            if len(firstdf) == 1:
                tag1 = firstdf.tag.iloc[0]
            else:
                tag1 = firstdf.tag.tolist()

        if not len(seconddf) == 0:
            if len(seconddf) == 1:
                tag2 = seconddf.tag.iloc[0]
            else:
                tag2 = seconddf.tag.tolist()

        if len(firstdf) > 1 and len(seconddf) > 1:
            same = set(tag1).intersection(set(tag2))
            diff1 = set(tag1) - set(tag2)
            diff2 = set(tag2) - set(tag1)

            for tag in list(same):
                out_df = out_df.append({annot1:tag,annot2:tag}, ignore_index=True)

            # OTHER METHOD !!!!!
            # if diff1 > diff2:
            #     for i,tag in enumerate(list(diff1)):
            #         if i < len(diff2):
            #             out_df = out_df.append({annot1:tag,annot2:list(diff2)[i]}, ignore_index=True)
            #         else:
            #             out_df = out_df.append({annot1:tag,annot2:"*"}, ignore_index=True)
            # else:
            #     for i,tag in enumerate(list(diff2)):
            #         if i < len(diff1):
            #             out_df = out_df.append({annot1:list(diff1)[i],annot2:tag}, ignore_index=True)
            #         else:
            #             out_df = out_df.append({annot1:"*",annot2:tag}, ignore_index=True)

            for tag in list(diff1):
                out_df = out_df.append({annot1:tag,annot2:"empty"}, ignore_index=True)
            for tag in list(diff2):
                out_df = out_df.append({annot1:"empty",annot2:tag}, ignore_index=True)

        elif len(firstdf) > 1 and len(seconddf) < 2:
            if any(tag2 == tag for tag in tag1):
                out_df = out_df.append({annot1:tag2,annot2:tag2}, ignore_index=True)
                tag1.remove(tag2)
            elif tag2 != "empty":
                out_df = out_df.append({annot1:"empty",annot2:tag2}, ignore_index=True)
            for tag in tag1:
                out_df = out_df.append({annot1:tag,annot2:"empty"}, ignore_index=True)

        elif len(firstdf) < 2 and len(seconddf) > 1:
            if any(tag1 == tag for tag in tag2):
                out_df = out_df.append({annot1:tag1,annot2:tag1}, ignore_index=True)
                tag2.remove(tag1)
            elif tag1 != "empty":
                out_df = out_df.append({annot1:tag1,annot2:"empty"}, ignore_index=True)
            for tag in tag2:
                out_df = out_df.append({annot1:"empty",annot2:tag}, ignore_index=True)

        else:
            out_df = out_df.append({annot1:tag1,annot2:tag2}, ignore_index=True)

    return out_df

#    if not len(seconddf) == 0:
#        firsttime = True
#        for index, row in seconddf.iterrows():
#            if firsttime:
#                tag2 = row.tag
#                firsttime = False
#            else:
#                tag2 = tag2 + "|" + row.tag

def calculate_Kalpha(in_df):
    tags1 = set(in_df[annot1].unique())
    tags2 = set(in_df[annot2].unique())
    tags = list(tags2.union(tags1))
    matrice = [x[:] for x in [[0] * len(tags)] * len(tags)]
    tags = sorted(tags)
#    dict = {}
#    for i,tag in enumerate(tags):
#        dict[tag] = i

    for i,tag1 in enumerate(tags):
        for j,tag2 in enumerate(tags):
            matches = in_df.loc[(in_df[annot1] == tag1) & (in_df[annot2] == tag2)]
            matrice[i][j] += len(matches)
            matrice[j][i] += len(matches)

    n = 2 * len(in_df)
    sumoftags = sum([sum(matrice[x])*(sum(matrice[x])-1) for x in range(len(matrice))])
    Kalpha = ((n-1)*sum([matrice[x][x] for x in range(len(matrice))]) - sumoftags) / (n*(n-1) - sumoftags)

    return Kalpha

#file = re.sub(r"^.*_(http.*)\.folia\.xml$",r"\g<1>.tsv",doc1file)



print(calculate_Kalpha(organize_data(Event_df)))
print(calculate_Kalpha(organize_data(Part_df)))
print(calculate_Kalpha(organize_data(Org_df)))
#print(calculate_Kalpha(organize_data(Target_df)))

#Event_out.to_csv("score/Event_" + file, sep="\t")
#Part_out.to_csv("score/Part_" + file, sep="\t")
#Org_out.to_csv("score/Org_" + file, sep="\t")
#Target_out.to_csv("score/Target_" + file, sep="\t")

#If there are more than one tag in word seperate them (One tag per row)

#Create a 2d array out of words. Initialize it with "empty"s. Loop over rows and add tag to appropriate place (example : First row Annot1:place, annot2:type add 1 to array["place"]["type"],
#and 1 to vice-versa) (If they are both same like motive then add 2 to array["motive"]["motive"])

#! /usr/bin/env python
# -*- coding: utf-8
'''
Python implementation of Krippendorff's alpha -- inter-rater reliability

(c)2011-17 Thomas Grill (http://grrrr.org)

Python version >= 2.4 required
'''

def nominal_metric(a, b):
    return a != b


def interval_metric(a, b):
    return (a-b)**2


def ratio_metric(a, b):
    return ((a-b)/(a+b))**2


def krippendorff_alpha(data, metric=interval_metric, force_vecmath=False, convert_items=float, missing_items=None):
    '''
    Calculate Krippendorff's alpha (inter-rater reliability):

    data is in the format
    [
        {unit1:value, unit2:value, ...},  # coder 1
        {unit1:value, unit3:value, ...},   # coder 2
        ...                            # more coders
    ]
    or
    it is a sequence of (masked) sequences (list, numpy.array, numpy.ma.array, e.g.) with rows corresponding to coders and columns to items

    metric: function calculating the pairwise distance
    force_vecmath: force vector math for custom metrics (numpy required)
    convert_items: function for the type conversion of items (default: float)
    missing_items: indicator for missing items (default: None)
    '''

    # number of coders
    m = len(data)

    # set of constants identifying missing values
    if missing_items is None:
        maskitems = []
    else:
        maskitems = list(missing_items)
    if np is not None:
        maskitems.append(np.ma.masked_singleton)

    # convert input data to a dict of items
    units = {}
    for d in data:
        try:
            # try if d behaves as a dict
            diter = d.items()
        except AttributeError:
            # sequence assumed for d
            diter = enumerate(d)

        for it, g in diter:
            if g not in maskitems:
                try:
                    its = units[it]
                except KeyError:
                    its = []
                    units[it] = its
                its.append(convert_items(g))


    units = dict((it, d) for it, d in units.items() if len(d) > 1)  # units with pairable values
    n = sum(len(pv) for pv in units.values())  # number of pairable values

    if n == 0:
        raise ValueError("No items to compare.")

    np_metric = (np is not None) and ((metric in (interval_metric, nominal_metric, ratio_metric)) or force_vecmath)

    Do = 0.
    for grades in units.values():
        if np_metric:
            gr = np.asarray(grades)
            Du = sum(np.sum(metric(gr, gri)) for gri in gr)
        else:
            Du = sum(metric(gi, gj) for gi in grades for gj in grades)
        Do += Du/float(len(grades)-1)
    Do /= float(n)

    if Do == 0:
        return 1.

    De = 0.
    for g1 in units.values():
        if np_metric:
            d1 = np.asarray(g1)
            for g2 in units.values():
                De += sum(np.sum(metric(d1, gj)) for gj in g2)
        else:
            for g2 in units.values():
                De += sum(metric(gi, gj) for gi in g1 for gj in g2)
    De /= float(n*(n-1))

    return 1.-Do/De if (Do and De) else 1.

def show_Kalpha(in_df):
    organizeddf = organize_data(in_df)
    array = organizeddf.values.tolist()
    array = [*zip(*array)]
    tags = list(set(organizeddf[annot1].unique()).union(set(organizeddf[annot2].unique())))
    dict2 = {}
    for i,tag in enumerate(tags):
        dict2[tag] = i
        array2 = array
    for i in range(len(array)):
        array2[i] = list(array[i])
    for i in range(len(array2)):
        for j in range(len(array2[i])):
            #if array2[i][j] != '*':
            array2[i][j] = dict2[array2[i][j]]
    missing = '*'
    print(array2)
    print(krippendorff_alpha(array2, nominal_metric))

show_Kalpha(Event_df)
show_Kalpha(Part_df)
show_Kalpha(Org_df)
