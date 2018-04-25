import re
import sys
import codecs
from pynlpl.formats import fql, folia

#This is the equalavent of foliamerge.py, but it takes one argument (Focus)

filename = sys.argv[1]

with codecs.open(filename, "r", "utf-8") as f:
    xml = f.read()

xml = re.sub(r"\s*<entity annotator=\"(Know-it-all|selim)\"[^<]*(<wref[^>]*>\s*)*\s*(<comment[^<]<\/comment>\s*)*\s*<\/entity>\s*", r"", xml)

filename = re.sub(r"^both_[^_]+_(.*)\.folia\.xml$", r"xmls/both_\g<1>.folia.xml", filename)

with codecs.open(filename, "w", "utf-8") as f:
    f.write(xml)

doc1_entity = []
doc2_entity = []

doc = folia.Document(file=filename)

for sentence in doc.sentences():

    for layer in sentence.select(folia.EntitiesLayer):

        for entity in layer.select(folia.Entity):

            if entity.annotator == "Doc1":
                doc1_entity.append(entity)

            elif entity.annotator == "Doc2":
                doc2_entity.append(entity)

    for word in sentence.words():

        if any(word in entity.wrefs() for entity in doc1_entity) and any(word in entity.wrefs() for entity in doc2_entity):
            for entity1 in doc1_entity:
                for entity2 in doc2_entity:
                    if (word in entity1.wrefs()) and (word in entity2.wrefs()) and (entity1.cls == entity2.cls):
                        word.add(folia.Entity, word, cls=entity1.cls, set=entity1.set, annotator="BothPart")

doc.save()
