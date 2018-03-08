#!/bin/bash

#doc1 = selim_docname.folia.xml and doc2 = sumercan_docname.folia.xml

doc1="$1"
doc2="$2"

python3 iaafoliaxml.py -t entity -s https://github.com/OsmanMutlu/rawtext/raw/master/protes4-Event.foliaset.xml $doc1 $doc2
python3 iaafoliaxml.py -t entity -s https://github.com/OsmanMutlu/rawtext/raw/master/protes4-Participant.foliaset.xml $doc1 $doc2
python3 iaafoliaxml.py -t entity -s https://github.com/OsmanMutlu/rawtext/raw/master/protes3-Organizer.foliaset.xml $doc1 $doc2
python3 iaafoliaxml.py -t entity -s https://github.com/OsmanMutlu/rawtext/raw/master/protes1-Targeted.foliaset.xml $doc1 $doc2

BOTH_EVENT=$(echo ${doc1} | sed 's/selim_/both_Event_/')
BOTH_PART=$(echo ${doc1} | sed 's/selim_/both_Participant_/')
BOTH_ORG=$(echo ${doc1} | sed 's/selim_/both_Organizer_/')
BOTH_TARGET=$(echo ${doc1} | sed 's/selim_/both_Targeted_/')

python3 foliatohtml.py /home/osman/work/iaa/xmls/$BOTH_EVENT
python3 foliatohtml.py /home/osman/work/iaa/xmls/$BOTH_PART
python3 foliatohtml.py /home/osman/work/iaa/xmls/$BOTH_ORG
python3 foliatohtml.py /home/osman/work/iaa/xmls/$BOTH_TARGET
