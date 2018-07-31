#!/bin/bash

#doc1 = selim_docname.folia.xml and doc2 = sumercan_docname.folia.xml

doc1="$1"
doc2="$2"

BOTH=$(echo ${doc1} | sed 's/batch\/selim_/both_/')
cp $doc1 $BOTH

python3 iaafoliaxml.py -t entity -s https://github.com/OsmanMutlu/rawtext/raw/master/protes8-Event.foliaset.xml $doc1 $doc2
python3 iaafoliaxml.py -t entity -s https://github.com/OsmanMutlu/rawtext/raw/master/protes5-Participant.foliaset.xml $doc1 $doc2
python3 iaafoliaxml.py -t entity -s https://github.com/OsmanMutlu/rawtext/raw/master/protes4-Organizer.foliaset.xml $doc1 $doc2
python3 iaafoliaxml.py -t entity -s https://github.com/OsmanMutlu/rawtext/raw/master/protes1-Target.foliaset.xml $doc1 $doc2

BOTH_EVENT=$(echo ${doc1} | sed 's/batch\/selim_/both_Event_/')
BOTH_PART=$(echo ${doc1} | sed 's/batch\/selim_/both_Participant_/')
BOTH_ORG=$(echo ${doc1} | sed 's/batch\/selim_/both_Organizer_/')
BOTH_TARGET=$(echo ${doc1} | sed 's/batch\/selim_/both_Targeted_/')

rm $BOTH
mv $BOTH_EVENT xmls/$BOTH_EVENT

python3 foliatohtml.py xmls/$BOTH_EVENT

mv xmls/$BOTH_EVENT $BOTH_EVENT

if [ ! -f $BOTH_ORG ]
    then
    if [ ! -f $BOTH_TARGET ] && [ ! -f $BOTH_EVENT ] && [ ! -f $BOTH_PART ]
    then
    :
    elif [ ! -f $BOTH_TARGET ] && [ ! -f $BOTH_PART ]
    then
        python3 cleanannot.py $BOTH_EVENT
    elif [ ! -f $BOTH_TARGET ] && [ ! -f $BOTH_EVENT ]
    then
        python3 cleanannot.py $BOTH_PART
    :
    elif [ ! -f $BOTH_PART ] && [ ! -f $BOTH_EVENT ]
    then
        python3 cleanannot.py $BOTH_TARGET
    :
    elif [ ! -f $BOTH_TARGET ]
    then
        python3 foliamerge.py -a $BOTH_EVENT $BOTH_PART
    elif [ ! -f $BOTH_PART ]
    then
        python3 foliamerge.py -a $BOTH_EVENT $BOTH_TARGET
    elif [ ! -f $BOTH_EVENT ]
    then
        python3 foliamerge.py -a $BOTH_PART $BOTH_TARGET
    else
        python3 foliamerge.py -a $BOTH_EVENT $BOTH_PART $BOTH_TARGET
    fi
elif [ ! -f $BOTH_TARGET ]
    then
    if [ ! -f $BOTH_EVENT ] && [ ! -f $BOTH_PART ]
    then
        python3 cleanannot.py $BOTH_ORG
    elif [ ! -f $BOTH_PART ]
    then
        python3 foliamerge.py -a $BOTH_EVENT $BOTH_ORG
    elif [ ! -f $BOTH_EVENT ]
    then
        python3 foliamerge.py -a $BOTH_PART $BOTH_ORG
    else
        python3 foliamerge.py -a $BOTH_EVENT $BOTH_PART $BOTH_ORG
    fi
elif [ ! -f $BOTH_PART ]
    then
    if [ ! -f $BOTH_EVENT ]
    then
        python3 foliamerge.py -a $BOTH_ORG $BOTH_TARGET
    else
        python3 foliamerge.py -a $BOTH_EVENT $BOTH_ORG $BOTH_TARGET
    fi
elif [ ! -f $BOTH_EVENT ]
    then
    python3 foliamerge.py -a $BOTH_PART $BOTH_ORG $BOTH_TARGET
else
    python3 foliamerge.py -a $BOTH_EVENT $BOTH_PART $BOTH_ORG $BOTH_TARGET
fi


#cp /home/osman/work/iaa-folia/xmls/$BOTH_EVENT /home/osman/work/iaa-folia/xmls/$BOTH

mv $BOTH_EVENT xmls/$BOTH_EVENT
mv $BOTH_PART xmls/$BOTH_PART
mv $BOTH_ORG xmls/$BOTH_ORG
mv $BOTH_TARGET xmls/$BOTH_TARGET

python3 foliatohtml.py xmls/$BOTH_PART
python3 foliatohtml.py xmls/$BOTH_ORG
python3 foliatohtml.py xmls/$BOTH_TARGET

rm xmls/$BOTH_EVENT
rm xmls/$BOTH_PART
rm xmls/$BOTH_ORG
rm xmls/$BOTH_TARGET
