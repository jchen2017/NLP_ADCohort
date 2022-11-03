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


""" utility funcs to extract test results and dates"""

import pandas as pd
import re
import numpy as np
import datefinder
#from nltk.tokenize import word_tokenize, sent_tokenize
#from nltk.stem.snowball import EnglishStemmer
from trie import Trie


# Augmentation using general domain data
def trie_regex_from_words(words):
    trie = Trie()
    for word in words:
        trie.add(word)

    regex_pattern=trie.pattern()
    return re.compile(r"\b" + regex_pattern + r"\b", re.IGNORECASE)


class testExtractor():
    """ This is the class that extract the test results/dates from EHR notes
    """

    def __init__(
        self,
        config_file = None
    ):
        """ information related to processing EHR notes, passed by a configuration file
        """
        self.config = self._load_config(config_file)
        self.w_size = 3
        if "win_size" in self.config:
            self.w_size = self.config["win_size"]


    def _load_config(self, config_file):
        config_dict = {}

        with open(config_file, "r") as f :
            for line in f.readlines():
                if re.search(r"^#", line) or re.search(r"^ *$", line):
                    continue
                
                if re.search(r"window_size", line):
                    config_dict["win_size"] = int(re.search(r"window_size: *(\d+)", line).group(1))
                
                else:
                    key, value = line.split(":")
                    val = [ re.search(r"^ *(.*[a-zA-Zé]) *$", v).group(1).lower() for v in value.split(",")]
                    config_dict[key] = trie_regex_from_words(val)
                
            print(config_dict)

        return config_dict


    def _find_dates(self, sent):
        date = "N/A"
        if re.search(r"\b((today)|(this +am))\b", sent):
            date = "encounter_date"
        elif re.search(r"\b(\d{1,2}\/((19)|(20))[0-9]{2})\b", sent):
            date = re.search(r"\b(\d+\/\d+)\b", sent).group(1)
        return date


    def extract(self, test, df, index):
        try:
            regex_test = self.config[test]
        except:
            print("warning-1: %s cannot be handled by the extractor"%(test))
            exit(1)

        sent = df.at[index,'segment']
        test_results = []
        for m in re.finditer(regex_test, sent):
            ##print(m.start(), m.end())
            t = sent[m.start():m.end()]
            left_context = sent[:m.start()]
            right_context = sent[m.end():]
            left_win = " ".join(left_context.split()[-self.w_size:])
            right_win = " ".join(right_context.split()[0:self.w_size])
            print("find %s in :  %s  %s  %s "%(t, left_context, t, right_context))
            
            if test in ["MMSE", "MoCA"]:
                # extract results
                try:
                    result = re.search("((\d+/\d+)|( \d+ ))", right_win).group(1)
                except:
                    try:
                        result = re.search("((\d+/\d+)|( \d+)) +on +$", left_win).group(1)
                    except:
                        result = "N/A"
                print("test result: %s"%(result))
            
                # extract date
                test_date = self._find_dates(right_win)
                if test_date == "N/A":
                    test_date = self._find_dates(left_win)

                print("test date: %s"%(test_date))
                test_results.append((result, test_date))

        return (test_results)

