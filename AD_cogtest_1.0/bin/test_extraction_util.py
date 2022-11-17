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
#import datefinder
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


    def _extract_results_generic(self, right_context, left_context):
        left_win_ls = left_context.split()[-self.w_size:]
        left_win = " ".join(left_win_ls)
        right_win_ls = right_context.split()[0:self.w_size]
        right_win = " ".join(right_win_ls)

        # extract result
        result = None
        for tok in right_win_ls:
            if re.search(r"^\d+$", tok):
                result = re.search("^(\d+)$", tok).group(1)
            elif re.search(r"(^|[^\/0-9])\d+/\d{2}([^\/0-9]|$)", tok):
                result = re.search(r"(\d+/\d{2})", tok).group(1)
                
            if result != None:
                break

        if result == None:
            try:
                result = re.search("(([^\/0-9]\d+/\d{2}[^\/])|( \d+ )) *on( |$)", left_win).group(1)
                result = result[1:-1]
            except:
                pass

        return result

    def _extract_bvrt(self, right_context, left_context):
        right_context_lc = right_context.lower()
        right_win_ls = right_context.split()[0:self.w_size]
        right_win = " ".join(right_win_ls)

        result = None

        if re.search(r"^[^\d]*\d+\/10", right_context_lc):
            result = re.search(r"^[^\d]*(\d+\/10)", right_context_lc).group(1)
        elif re.search(r"^[^\d]*((average)|(borderline impair[a-z]+)) +range", right_context_lc):
            result = re.search(r"^[^\d]*((average)|(borderline impair[a-z]+))", right_context_lc).group(1)
        elif re.search(r"^[^\d]*raw=10[^\d]*((average)|(borderline impair[a-z]+))", right_context_lc):
            result = re.search(r"^[^\d]*raw=10[^\d]*((average)|(borderline impair[a-z]+))", right_context_lc).group(1)
        elif re.search(r"^[^\d]*\d\b", right_win):
            result = re.search(r"^[^\d]*(\d)\b", right_win).group(1)


        if result == None:
            left_context = re.sub(r"on( the)?$", "", left_context)
            left_win_ls = left_context.split()[-self.w_size:]
            left_win = " ".join(left_win_ls)

            try:
                result = re.search("((average)|(borderline impair[a-z]+))[^\d]*", left_win.lower()).group(1)
            except:
                pass


        return result


    def _extract_bnt(self, right_context):
        right_context_lc = right_context.lower()

        result = None

        if re.search(r"^[^\d]*\d+[a-z]{2} +percentile", right_context_lc):
            r1 = re.search(r"[^\d]*(\d+[a-z]{2})", right_context_lc).group(1)
            result = "%s percentile"%(r1)
        elif re.search(r"^[^\d]*\d+\/\d{2}", right_context_lc):
            r1 = re.search(r"^[^\d]*(\d+\/\d{2})", right_context_lc).group(1)
            result = "%s"%(r1)
        elif re.search(r"^[^\d]*\d{1,2}\b", right_context_lc):
            r1 = re.search(r"^[^\d]*(\d{1,2})", right_context_lc).group(1)
            result = "%s"%(r1)
        
        return result


    def _extract_mini_cog(self, right_context, left_context):
        right_context_lc = right_context.lower()

        result = None

        if re.search(r"[^\d]+ accomplished [^\d]+ \d\/5", right_context):
            result = re.search(r"[^\d]+ (\d\/5)", right_context).group(1)
        elif re.search(r"score[^\d]+\d out of *\d", right_context):
            r1, r2 = re.search(r"score[^\d]+(\d) out of *(\d)", right_context).groups()
            result = "%s/%s"%(r1,r2)
        elif re.search(r"^[^\d]*clock: *\d *recall: *\d( |^)", right_context_lc):
            r1, r2 = re.search(r"clock: *(\d) *recall: *(\d)", right_context_lc).groups()
            result = "clock=%s,recall=%s"%(r1,r2)
        elif re.search(r"^[^\d]*recall[^\d]*: *\d\/\d[^\d]*clock[^\d]*: *\d\/\d( |^)", right_context_lc):
            r1, r2 = re.search(r"recall[^\d]*: *(\d\/\d)[^\d]*clock[^\d]*: *(\d\/\d)", right_context_lc).groups()
            result = "clock=%s,recall=%s"%(r2,r1)
        elif re.search(r"registration +(\d)\/3, *recall +(\d)\/3", right_context_lc):
            r1, r2 = re.search(r"registration +(\d\/3), *recall +(\d\/3)", right_context_lc).groups()
            result = "registration=%s,recall=%s"%(r1,r2)
        elif re.search(r"(\d)\/3 +for +registration, *(\d)\/3 +for +recall", right_context_lc):
            r1, r2 = re.search(r"(\d\/3) +for +registration, *(\d\/3) +for +recall", right_context_lc).groups()
            result = "registration=%s,recall=%s"%(r1,r2)
        else:
            right_win_ls = right_context.split()[0:self.w_size]
            for tok in right_win_ls:
                if re.search(r"[^\d]*\d\/\d[^\d]*", tok):
                    result = re.search("(\d\/\d)", tok).group(1)
                    break

        if result == None:
            try:
                result = re.search("([0-5]) *on( |$)", left_context).group(1)
            except:
                pass


        return result

                
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
            print("find %s in :  %s  %s  %s "%(t, left_context, t, right_context))

            right_context = re.sub(r"^[^\w]+", "", right_context)
            right_context = re.sub(r"(( - )|(\. [A-Z])).*$", "", right_context)
            lef_context = re.sub(r"[ \(]+$", "", left_context)
            
            if test in ["MMSE", "MoCA", "SLUMS"]:
                result = self._extract_results_generic(right_context, left_context)
                                
                # extract date (not implemented)
                #test_date = self._find_dates(right_win)
                #if test_date == "N/A":
                #    test_date = self._find_dates(left_win)
 
            elif test == "MINICOG":
                result = self._extract_mini_cog(right_context, left_context)
  
            elif test == "BNT":
                result = self._extract_bnt(right_context)

            elif test == "BENTON":
                result = self._extract_bvrt(right_context, left_context)


            test_date = "N/A"
        
            if result != None:
                print("test result: %s"%(result))
                #print("test date: %s"%(test_date))
                test_results.append((result, test_date))
            else:
                print("warning-2: failed to find value for %s"%(t))
    

        if test_results == []:
            test_results.append(("N/A", "N/A"))
            #test_results.append("N/A")
        return (test_results)

