# coding=utf-8
#
# Released under MIT License
#
# Copyright (c) 2022, Jinying Chen
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


""" preprocess test data """
import pandas as pd
import re
import sys
import os
from os import listdir
from os.path import isfile, join
from data_augmentation import *
from ehr_util import *
import time

random_seed = 2138
cpath = os.getcwd()
ehr_config = cpath + "/config/ehr_processing_config.txt"

augmentor = GeneralAugmentor(ehr_config)
ehr_util = ehrUtil(ehr_config)

# preprocessing EHR text
def preprocess(df):
    df['orig_text'] = df['text']

    for index, row in df.iterrows():
        sent, n = augmentor.transform(row.text)
        sent, changed = augmentor.concentrate(sent, max_len = 30, focus = "alzheimer")

        if n > 0 or changed:
            df.at[index, 'text'] = sent

    return df


def prepare_test_data(inputfile, outfile, preprocessing = True):
    test_df = pd.read_excel(inputfile, usecols = ["ReportText", "NewOverallID", "Clinical diagnosis"])
    test_df.rename({"ReportText":"segment", "NewOverallID": "patid", "Clinical diagnosis" : "plabel"}, axis='columns', inplace = True)
    test_df.fillna(method='ffill', inplace = True)
    test_df['plabel_orig'] = test_df['plabel']
    test_df['plabel'].loc[test_df['plabel'].str.contains('AD')] = "1"
    test_df['plabel'].loc[~test_df['plabel'].str.contains('AD')] = "0"
    test_df['id'] = test_df.groupby(['patid']).cumcount()+1
    test_df['label'] = 0
    test_df['drop'] = 0

    for index, row in test_df.iterrows():
        sent = row.segment
        if sent == "" or sent == None:
            test_df.at[index,'drop'] = 1
        else:
            seglabel1, seglabel2 = ehr_util.assign_segment_label(sent) 
            if re.search(r"(func_lines)|(attribute)|(endofnote)", seglabel1):
                test_df.at[index,'drop'] = 1
            else:
                if row['plabel'] == "AD":
                    if re.search(r"alzheimer", sent.lower()) or re.search(r"\bAD\b", sent):
                        ##print(f"warning-1: segment for further annotation (pid = {row.patid}, {row.label}): {sent}")
                        test_df.at[index,"label"] = 1

                sent, n = augmentor.replace_family_member(sent)
                test_df.at[index,'segment'] = sent


    test_df.drop(test_df[test_df['drop'] == 1].index, inplace = True)
    test_df = test_df[['id', 'label', 'segment', 'plabel', 'patid']]
    test_df.rename(columns={"segment": "text"}, errors="raise", inplace = True)
    test_df['plabel'] = test_df['plabel'].astype(int)
    
    test_df = test_df.reset_index(drop = True)
    test_df.index.names = ['sid']

    if preprocessing:
        test_df = preprocess(test_df)

    print(test_df.head(3))

    test_df.to_csv(outfile)


if '__main__' == __name__:
    if (len(sys.argv) < 4):
        print("This is the program that converts raw input file into input file for the NLP classifier.")
        print(sys.argv[0], "option inputfile outputfile")
        print(sys.argv[0], "option 1 - inputfile is a single .xlsx file")
        print("Examples: ")
        print(sys.argv[0], "1 NLP_Possible_Input_Formate_v2.xlsx test_data.csv")
        exit (1)

    opt=int(sys.argv[1])
    inputfile=sys.argv[2]
    outputfile=sys.argv[3]
    
    if opt == 1:
        start_time = time.time()
        prepare_test_data(inputfile = inputfile, outfile = outputfile)
        print("--- preprocessing time: %s seconds ---" % (time.time() - start_time))
