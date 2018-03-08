from pynlpl.formats import fql, folia
import sys
import re
import codecs

docfile = sys.argv[1]
doc = folia.Document(file=docfile)
htmlfile = re.sub(r"^(\/home\/osman\/work\/iaa\/)xmls(\/.*)folia\.xml$", r"\g<1>htmls\g<2>html", docfile)

both_entity = []
doc1_entity = []
doc2_entity = []

html = '<html><body><p>'

for sentence in doc.sentences():

    for layer in sentence.select(folia.EntitiesLayer):

        for entity in layer.select(folia.Entity):

            if entity.annotator == "Both":
                both_entity.append(entity)

            elif entity.annotator == "Doc1":
                doc1_entity.append(entity)

            elif entity.annotator == "Doc2":
                doc2_entity.append(entity)

    for word in sentence.words():

        if any(word in entity.wrefs() for entity in both_entity):
            html = html + '<span style="background-color:green;" class="both">' + word.text() + '</span>' + ' '

        elif any(word in entity.wrefs() for entity in doc1_entity) and any(word in entity.wrefs() for entity in doc2_entity):
            print("Found one!")
            html = html + '<span style="background-color:green;" class="both">' + word.text() + '</span>' + ' '

        elif any(word in entity.wrefs() for entity in doc1_entity):
            html = html + '<span style="background-color:blue;" class="doc1">' + word.text() + '</span>' + ' '

        elif any(word in entity.wrefs() for entity in doc2_entity):
            html = html + '<span style="background-color:red;" class="doc2">' + word.text() + '</span>' + ' '

        else:
            html = html + '<span>' + word.text() + '</span>' + ' '

html = html + '</p></body></html>'

with codecs.open(htmlfile, "w", "utf-8") as f:
    f.write(html)