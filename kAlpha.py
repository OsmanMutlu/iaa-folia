from __future__ import print_function
from pynlpl.formats import fql, folia
import sys
import re
import codecs
import pandas
import numpy as np
from glob import glob

annot1 = "selim"
annot2 = "sumercan"
empty_tag = "empty"
all_kalpha_Event = []
all_kalpha_Part = []
all_kalpha_Org = []
all_kalpha_Target = []
all_tags_Event = []
all_tags_Part = []
all_tags_Org = []
all_tags_Target = []

# These are folders for annotators. They must end with "/" character. For example: python3 kAlpha.py xmls/selim/ xmls/sumercan/
ann1 = sys.argv[1]
ann2 = sys.argv[2]
#doc_length = 0

def sorted_nicely( l ):
    # Copied from this post
    # https://stackoverflow.com/questions/2669059/how-to-sort-alpha-numeric-set-in-python
    # Thank you Daniel
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key = alphanum_key)

def getData(entity, annot, sp, sent_len, df):

    wordList = []
    for wref in entity.wrefs():
        wordList.append(re.sub(r'.*(s\.\d+\.w\.\d+)$', r'\g<1>', wref.id))
    wordList = sorted_nicely(wordList)
    # Check if there is any space in entity. Divide them if there is.
    i = 0
    current_sent = int(re.search(r'^s\.(\d+)', wordList[0]).group(1))

    while i < len(wordList) - 1 and len(wordList) > 1:
        sent = int(re.search(r's\.(\d+)\.w\.\d+$', wordList[i]).group(1))
        next_sent = int(re.search(r's\.(\d+)\.w\.\d+$', wordList[i + 1]).group(1))
        word = int(re.search(r'(\d+)$', wordList[i]).group(1))
        next_word = int(re.search(r'(\d+)$', wordList[i + 1]).group(1))
        if word + 1 != next_word or (next_word == 1 and next_sent == sent + 1):
            first_word = int(re.search(r'(\d+)$', wordList[0]).group(1))
            first_sent = int(re.search(r's\.(\d+)\.w\.\d+$', wordList[0]).group(1))
            first_word += sp
            word += sp
            if first_sent == current_sent + 1:
                first_word += sent_len
            if sent == current_sent + 1:
                word += sent_len
            df = df.append({"entity": str(first_word) + ":" + str(word),
                            "annotator": annot, "focus": entity.set, "tag": entity.cls}, ignore_index=True)
            for j in range(0, i + 1):
                del wordList[0]
            i = 0
            if len(wordList) == 1:
                next_word += sp
                if next_sent == current_sent + 1:
                    next_word += sent_len
                df = df.append({"entity": str(next_word) + ":" + str(next_word),
                                "annotator": annot, "focus": entity.set, "tag": entity.cls}, ignore_index=True)
                del wordList[0]
        else:
            i = i + 1

    if len(wordList) > 0:
        first_word = int(re.search(r'(\d+)$', wordList[0]).group(1))
        first_sent = int(re.search(r's\.(\d+)\.w\.\d+$', wordList[0]).group(1))
        last_word = int(re.search(r'(\d+)$', wordList[-1]).group(1))
        last_sent = int(re.search(r's\.(\d+)\.w\.\d+$', wordList[-1]).group(1))
        first_word += sp
        last_word += sp
        if first_sent == current_sent + 1:
            first_word += sent_len
        if last_sent == current_sent + 1:
            last_word += sent_len
        df = df.append({"entity": str(first_word) + ":" + str(last_word),
                        "annotator": annot, "focus": entity.set, "tag": entity.cls}, ignore_index=True)

    return df

def organize_data(entities, tag):

    out_list = []
    start_point = 1
    if len(entities) == 0:
        out_list.append([1,doc_length,empty_tag])
        return out_list
    for entity in entities:
        # ESP = Entity Start Point , EEP = Entity End Point
        ESP = int(re.search(r'^(\d+):', entity).group(1))
        EEP = int(re.search(r':(\d+)$', entity).group(1))
        #print("(" + str(ESP) + "," + str(EEP) + ")")
        if ESP > start_point:
            out_list.append([start_point,ESP - 1,empty_tag])
        elif ESP < start_point:
            # Duplicates
            print("Duplicates")
            continue
        out_list.append([ESP,EEP,tag])
        start_point = EEP + 1

    last_point = out_list[-1][1]
    if last_point < doc_length:
        out_list.append([last_point + 1,doc_length,empty_tag])

    return out_list

def getUnion(a,b):
    return max(a[1],b[1]) - min(a[0],b[0]) + 1

def getIntersect(a,b):
    return min(a[1],b[1]) - max(a[0],b[0]) + 1

def getLength(a):
    return a[1] - a[0] + 1

def encapsulates(a,b):
    if getIntersect(a,b) == getLength(b):
        return True
    else:
        return False

def calculate_Kalpha(in_df):

    tags = in_df.tag.unique()

    kAlpha_tags = {}
    for tag in tags:

        firstdf = in_df.loc[(in_df['tag'] == tag) &
                            (in_df['annotator'] == annot1)]
        seconddf = in_df.loc[(in_df['tag'] == tag) &
                             (in_df['annotator'] == annot2)]

        #print("-----------------------------------------------------------")
        #print(tag)
        entities1 = firstdf.entity.tolist()
        entities1 = sorted_nicely(entities1)
        entities1 = organize_data(entities1, tag)
        #print(firstdf)
        entities2 = seconddf.entity.tolist()
        entities2 = sorted_nicely(entities2)
        entities2 = organize_data(entities2, tag)
        #print(seconddf)
        #print(entities1)
        #print(entities2)

        if entities1 == entities2:
            for g in entities1:
                if g[2] != empty_tag:
                    count += 1
            kAlpha_tags[tag] = {'kalpha':1.0,'weight':count}
            continue

        observed = 0
        count = 0
        empty_count = 0
        for g in entities1:
            for h in entities2:
                intersect = getIntersect(g,h)
                if intersect > 0:
                    if g[2] != empty_tag and h[2] != empty_tag:
                        observed += getUnion(g,h) - intersect
                        count += 1
                    elif g[2] != empty_tag and h[2] == empty_tag and encapsulates(h,g):
                        observed += 2*getLength(g)
                        count += 1
                    elif g[2] == empty_tag and h[2] != empty_tag and encapsulates(g,h):
                        observed += 2*getLength(h)
                        count += 1
                    elif g[2] == empty_tag and h[2] == empty_tag:
                        empty_count += 1

        observed = float(observed / count)

        entities1.extend(entities2)
        entities1 = [x for x in entities1 if x[2] == tag]

        expected = 0
        ecount = 0
        for g in entities1:
            for h in entities1:
                if g == h:
                    continue
                leng = getLength(g)
                lenh = getLength(h)
                expected += leng*leng + lenh*lenh
                ecount += leng + lenh

        if ecount == 0:
            print("Zero expected " + tag)
        else:
            expected = float(expected / ecount)


        if expected == 0:
            kAlpha_tags[tag] = {'kalpha':0.0,'weight':count}
            continue

        kalpha = 1.0 - observed / expected
        kAlpha_tags[tag] = {'kalpha':kalpha,'weight':count}
    print(kAlpha_tags)
    return kAlpha_tags

for doc in glob(ann1 + "http*"):

    Event_out = pandas.DataFrame()
    Part_out = pandas.DataFrame()
    Org_out = pandas.DataFrame()
    Target_out = pandas.DataFrame()
    all_df = pandas.DataFrame()

    doc1 = folia.Document(file=doc)

    doc2file = re.sub(r"^.*\/(http.*)$",
                      ann2 + r"\g<1>", doc)

    doc2 = folia.Document(file=doc2file)

    # These 3 for loops are for making sure that the sentence lengths in both documents are equal
    sentence_lengths1 = []
    sentence_lengths2 = []
    sentence_lengths = []
    for i, sentence in enumerate(doc1.sentences()):
        sentence_lengths1.append(len(sentence))

    for i, sentence in enumerate(doc2.sentences()):
        sentence_lengths2.append(len(sentence))

    for i in range(len(sentence_lengths1)):
        sentence_lengths.append(max(sentence_lengths1[i],sentence_lengths2[i]))

    start_point = 0
    for i, sentence in enumerate(doc1.sentences()):

        for layer in sentence.select(folia.EntitiesLayer):

            for entity in layer.select(folia.Entity):

                all_df = getData(entity, annot1, start_point, sentence_lengths[i], all_df)


        #print("Current Sentence : " + str(i) + " , Sentence Length : " + str(sentence_lengths[i]))
        start_point = start_point + sentence_lengths[i]

    #print("-------------------------------------------------------------")

    start_point = 0
    for i, sentence in enumerate(doc2.sentences()):

        for layer in sentence.select(folia.EntitiesLayer):

            for entity in layer.select(folia.Entity):

                all_df = getData(entity, annot2, start_point, sentence_lengths[i], all_df)

        #print("Current Sentence : " + str(i) + " , Sentence Length : " + str(sentence_lengths[i]))
        start_point = start_point + sentence_lengths[i]

    all_df.drop_duplicates(inplace=True)

    all_df = all_df.sort_values(by=["entity"])

    Event_df = all_df[all_df['focus'] ==
                  "https://github.com/OsmanMutlu/rawtext/raw/master/protes6-Event.foliaset.xml"]
    Part_df = all_df[all_df['focus'] ==
                 "https://github.com/OsmanMutlu/rawtext/raw/master/protes4-Participant.foliaset.xml"]
    Org_df = all_df[all_df['focus'] ==
                "https://github.com/OsmanMutlu/rawtext/raw/master/protes3-Organizer.foliaset.xml"]
    Target_df = all_df[all_df['focus'] ==
                   "https://github.com/OsmanMutlu/rawtext/raw/master/protes1-Target.foliaset.xml"]
    #print(all_df[all_df.annotator == annot1])
    #print(all_df[all_df.annotator == annot2])

    doc_length = sum(sentence_lengths)

    #print(Event_df.sort_values(by=["annotator"]))

    all_kalpha_Event.append(calculate_Kalpha(Event_df))
    all_kalpha_Part.append(calculate_Kalpha(Part_df))
    all_kalpha_Org.append(calculate_Kalpha(Org_df))
    all_kalpha_Target.append(calculate_Kalpha(Target_df))
    all_tags_Event.extend(Event_df.tag.unique())
    all_tags_Part.extend(Part_df.tag.unique())
    all_tags_Org.extend(Org_df.tag.unique())
    all_tags_Target.extend(Target_df.tag.unique())

def all_docs(kalpha_list,tags):
    result = {}
    for tag in list(set(tags)):
        result[tag] = {}
        result[tag]['count'] = 0
        result[tag]['kalpha'] = 0.0
    for kalpha in kalpha_list:
        for tag in kalpha.keys():
            result[tag]['count'] += kalpha[tag]['weight']
            result[tag]['kalpha'] += kalpha[tag]['kalpha']*kalpha[tag]['weight']
    for tag in result.keys():
        if result[tag]['count'] != 0:
            result[tag]['kalpha'] = result[tag]['kalpha'] / result[tag]['count']
    return result

print(all_docs(all_kalpha_Event,all_tags_Event))
print(all_docs(all_kalpha_Part,all_tags_Part))
print(all_docs(all_kalpha_Org,all_tags_Org))
print(all_docs(all_kalpha_Target,all_tags_Target))
# place_pub and doc_title should be 1, but they are 0
# make certain this works ( do it manually)
