# coding=utf-8
# 
# Released under MIT License
# 
# Copyright (c) 2022, Jinying Chen
#
# contributors: (to add)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


""" EHR notes preprocessing """

import pandas as pd
import re
import sys
import os
from os import listdir
from os.path import isfile, join

ehr_config = "./ehr_processing_config.txt"

class ehrUtil():
    """ This is the class that processes the text for a patient note
    """

    def __init__(
        self,
        config_file = None
    ):
        """ information related to processing EHR notes, passed by a configuration file
        """
        self.config = self._load_config (config_file)
        self.key_sections = self.config["key_sections"]
        self.min_section_name_len = self.config["min_sec_name_length"] 
        self.key_sections_sn = [section_name.upper() for section_name in self.key_sections if len(section_name) < self.min_section_name_len ]
        self.key_sections_uc = [section_name.upper() for section_name in self.key_sections]


    def _load_config (self, config_file):
        config_dict = {}

        with open(config_file, "r") as f :
            for line in f.readlines():
                if re.search(r"^#", line) or re.search(r"^ *$", line):
                    continue
                else:
                    key, value = line.split(":")
                    if key == "key_sections":
                        val = [ re.search(r"^ *(.*[a-zA-Z]) *$", v).group(1) for v in value.split(",")]
                        config_dict[key] = val
                    elif re.search(r"length", key):
                        val = int(value)
                        config_dict[key] = val

        return config_dict
    
    def extract_title (self):
        try:
            title, = re.search(r"STANDARD +TITLE: (.*)\n", self.note).groups(1)
            title = re.sub(r" +", " ", title)
            title = re.sub(r"(^ +)|( +$)", "", title)
        except:
            title = None
        return title


    def _group_segment_labels (self, seglabel):
        newlabel = seglabel
        if re.search(r"FAMILY", seglabel):
            if re.search(r"(HISTORY)|(HX)", seglabel):
                newlabel = "FAMILY HISTORY"
            elif re.search(r"EDUCATION", seglabel):
                newlabel = "FAMILY EDU"
        elif re.search(r"(ASSESS)|(IMPRESSION)|(ASESSMENT)", seglabel):
            newlabel = "ASSESSMENT/IMPRESSION"
        elif re.search(r"CHIEF COMPLAIN", seglabel):
            newlabel = "CHIEF COMPLAIN"
        elif re.search(r"MEDIC((INE)|(ATION))", seglabel):
            newlabel = "MEDICINE"
        elif re.search(r"ACTIVE PROBLEM", seglabel):
            newlabel = "ACTIVE PROBLEM"
        elif re.search(r"DIAGNOS[EI]S", seglabel):
            newlabel = "DIAGNOSES"
        elif re.search(r"(HISTORY)|(PMH)", seglabel):
            newlabel = "PMH"
        elif re.search(r"PLAN", seglabel):
            newlabel = "TREATMENT PLAN"
        elif re.search(r"ALLERG", seglabel):
            newlabel = "ALLERGIES"
        elif re.search(r"HPI", seglabel):
            newlabel = "HPI"


        return newlabel
    
    def _classify_content (self, segment):
        segtype = "content"
        if re.search(r"(\-{3})|(\*{2})|(={2})", segment):
            segtype = "func_lines"
        elif re.search(r"\[[ xX]+\]", segment):
            segtype = "check_list"
        elif re.search(r"medication.* if applies:", segment):
            segtype = "medication_list"
        elif not re.search(r"[a-zA-Z]{3}", segment):
            segtype = "func_lines"

        return segtype


    def assign_segment_label (self, segment, pre_seglabel = "BEGIN" ):
        segtype = None
        segtype2 = None

        if re.search("TITLE:", segment):
            segtype = "attribute"
            segtype2 = "title"

        elif re.search("(DATE OF [A-Z]+:)|([A-Z]+ +DATE:)|(DATE +[A-Z]+:)", segment.upper()):
            segtype = "attribute"
            segtype2 = "date"

        elif re.search("AUTHOR:", segment):
            segtype = "attribute"
            segtype2 = "author"

        elif re.search("STATUS:", segment):
            segtype = "attribute"
            segtype2 = "note_status"

        elif re.search("\/es\/", segment) or (not re.search("\-\-\- Original Document ", segment) and pre_seglabel == "endofnote"):
            segtype = "endofnote"
            segtype2 = segtype

        elif re.search("^ *[A-Z \/&]+:", segment):
            findSection = True
            segtype2 = re.search("^ *([A-Z \/&]+):", segment).group(1)
            segtype2 = re.sub(r" +", " ", segtype2)
            segtype2 = re.sub(r"((^ +)|( +$))", "", segtype2)
            if len(segtype2) < self.min_section_name_len and not segtype2 in self.key_sections_sn:
                segtype2 = self._classify_content (segment)
                findSection = False

            segtype = self._group_segment_labels(segtype2)

            if findSection and re.search(r"^ *[A-Z \/&]+: *$", segment):
                segtype += ":"

        elif re.search("^ *[A-Za-z \/&]+:", segment):
            findSection = True
            segtype2 = re.search("^ *([A-Za-z \/&]+):", segment).group(1)
            segtype2 = re.sub(r" +", " ", segtype2).upper()
            if not segtype2 in self.key_sections_uc:
                segtype2 = self._classify_content (segment)
                findSection = False

            segtype = self._group_segment_labels(segtype2)

            if findSection and re.search(r"^ *[A-Za-z \/&]+: *$", segment):
                segtype += ":"

        else:
            segtype = self._classify_content(segment)
            segtype2 = segtype
            if segtype in ["content", "check_list"] and pre_seglabel[-1] == ":":
                ##print(f"warning-1: inherit segment label: {segtype} -> {pre_seglabel}")
                segtype = pre_seglabel

        return segtype, segtype2


    def segment_note (self, note, noteid):
        lineid = 1
        pre_seglabel = "BEGIN"

        note_dict = {}
        note_dict["segid"] = []
        note_dict["segment"] = []
        note_dict["seglabel"] = []
        ##note_dict["seglabel2"] = []

        for line in note.split("\n"):
            print(f"{lineid}: {line}")
            seglabel, seglabel2 = self.assign_segment_label(line, pre_seglabel)
            if seglabel != None:
                seglabel_clean = re.sub(r":", "", seglabel)
                print(f"seg label: {seglabel_clean}")
            else:
                print(f"seg label: unknown")

            note_dict["segid"].append(lineid)
            note_dict["segment"].append(line)
            note_dict["seglabel"].append(seglabel)
            ##note_dict["seglabel2"].append(seglabel2)

            lineid += 1
            pre_seglabel = seglabel

        note_df = pd.DataFrame.from_dict(note_dict)
        note_df.insert(0, 'NoteID', noteid)
        
        return note_df
