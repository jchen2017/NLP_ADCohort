# coding=utf-8
#
# Released under MIT License
#
# Copyright (c) 2022, Jinying Chen
#
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


""" extract cognitive test results """
import pandas as pd
import re
import sys
import os
from os import listdir
from os.path import isfile, join
from test_extraction_util import *
from ehr_util import *
import time

SEGMENT_NOTE = False
random_seed = 2138
cpath = os.getcwd()
ehr_config = cpath + "/config/ehr_processing_config.txt"
test_extract_config = cpath + "/config/test_extraction_config.txt"
  

test_to_extract = ["MMSE", "MoCA", "SLUMS", "MINICOG", "BNT"]
test_extractor = testExtractor(test_extract_config)
ehr_util = ehrUtil(ehr_config)


def extract_test_results(inputfile, outfile, preprocessing = True):
    test_df = pd.read_excel(inputfile, usecols = ["ReportText", "NoteID"])
    test_df.drop(test_df[test_df['NoteID'] == "END"].index, inplace = True)
    test_df.fillna(method='ffill', inplace = True)

    if SEGMENT_NOTE:
        note_df_ls = []
        for index, row in test_df.iterrows():
            noteid =  row.NoteID
            note = row.ReportText
            note_df = ehr_util.segment_note(note, noteid)
            note_df_ls.append(note_df)

        test_df = pd.concat(note_df_ls)
        test_df = test_df.reset_index(drop = True)

    else:
        test_df.rename({"ReportText":"segment"}, axis='columns', inplace = True)
        test_df['seglabel'] = "full_note"
        test_df['segid'] = 1

    for test_name in test_to_extract:
        test_df[test_name] = None
        

    test_df['drop'] = 0

    for index, row in test_df.iterrows():
        sent = row.segment
        seglabel = row.seglabel

        if sent == "" or sent == None:
            test_df.at[index,'drop'] = 1
        else:
            ##if re.search(r"(func_lines)|(attribute)|(endofnote)", seglabel):
            if re.search(r"(attribute)|(endofnote)", seglabel):
                test_df.at[index,'drop'] = 1
            else:
                for test_name in test_to_extract:
                    result_ls = []
                    for (result, date) in test_extractor.extract(test_name, test_df, index):
                        ##result_ls.append((result, date))
                        result_ls.append(result)

                    test_df.at[index, test_name] = f"{result_ls}"
                    if len(result_ls) > 1:
                        print(f"warning-1: multiple test results for note {row.NoteID} segment {row.segid}")

    test_df.drop(test_df[test_df['drop'] == 1].index, inplace = True)
    test_df = test_df[['NoteID', 'segid', 'segment'] + test_to_extract ]
    test_df = test_df.reset_index(drop = True)
    test_df.index.names = ['id']

    print(test_df.head(3))


    test_df.to_csv(outfile)


if '__main__' == __name__:
    if (len(sys.argv) < 4):
        print("This is the program that extracts cognitive test results from EHR notes")
        print(sys.argv[0], "option inputfile outputfile")
        print(sys.argv[0], "option 1 - inputfile is a single .xlsx file")
        print("Examples: ")
        print(sys.argv[0], "1 sample_for_cogtest.xlsx cognitive_test_results.csv")
        exit (1)

    opt=int(sys.argv[1])
    inputfile=sys.argv[2]
    outputfile=sys.argv[3]
    if re.search(r"input\/([^_]+)_Notes", inputfile):
        test = re.search(r"input\/([^_]+)_Notes", inputfile).group(1)
        test_to_extract = [test]
    elif re.search(r"input\/([^_]+)\+Sample", inputfile):
        test = re.search(r"input\/([^_]+)\+Sample", inputfile).group(1)
        test_to_extract = [test]

    if opt == 1:
        start_time = time.time()
        extract_test_results(inputfile = inputfile, outfile = outputfile)
        print("--- preprocessing time: %s seconds ---" % (time.time() - start_time))
