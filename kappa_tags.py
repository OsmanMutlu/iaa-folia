import json
import codecs
from collections import Counter
import operator

cnt = Counter()
kappa = 0
kappa_miss = 0
kappa_part = 0
kappa_part_miss = 0

all_tags = {"Event_etype":0, "Event_etime":0, "Event_eptime":0, "Event_loc":0, "Event_fname":0, "Event_wtype":0,
            "Event_urban":0, "Event_rural":0, "Event_ses":0, "Event_doc_title":0, "Event_casual":0, "Event_ctype":0,
            "Event_casualof":0, "Event_coftype":0, "Event_civil":0, "Event_civiltype":0, "Event_place":0,
            "Event_motive":0, "Participant_type":0, "Participant_pname":0, "Participant_count":0, "Participant_ideology":0,
            "Participant_ethnicity":0, "Participant_religion":0, "Participant_caste":0, "Participant_sector":0,
            "Participant_partses":0, "Participant_emp":0, "Participant_sub":0, "Organizer_type":0, "Organizer_name":0,
            "Organizer_ideology":0, "Organizer_oethnicity":0, "Organizer_oreligion":0, "Organizer_osector":0,
            "Organizer_caste":0, "Organizer_count":0, "Organizer_orgses":0, "Targeted_type":0, "Targeted_name":0,
            "Targeted_ideology":0, "Targeted_ethnicity":0, "Targeted_religion":0, "Targeted_caste":0}

with codecs.open("kappa_tags.jl", "r", "utf-8") as f:
    for line in f:
        data = json.loads(line)
        cnt = cnt + Counter(data["tag_count"])
        annots = sum(Counter(data["tag_count"]).values())
        kappa = kappa + data["kappa"]*annots
        kappa_miss = kappa_miss + data["kappa_miss"]*annots
        kappa_part = kappa_part + data["kappa_part"]*annots
        kappa_part_miss = kappa_part_miss + data["kappa_part_miss"]*annots

all_sum = sum(cnt.values())

for key, value in cnt.items():
    all_tags[key] = value

all_tags = sorted(all_tags.items(), key=operator.itemgetter(1))

all_tags.reverse()
print("Sum of All Tags : " +str(all_sum))
print("Total Counts of Tags : " + str(all_tags))
print("Cohen Kappa Average Score (Without value misses) : " + str(kappa/all_sum))
print("Cohen Kappa Average Score (With value misses) : " + str(kappa_miss/all_sum))
print("Cohen Kappa Partial Average Score (Without value misses) : " + str(kappa_part/all_sum))
print("Cohen Kappa Partial Average Score (With value misses) : " + str(kappa_part_miss/all_sum))
