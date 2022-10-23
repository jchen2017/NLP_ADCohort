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


""" data utility funcs """

import pandas as pd
import re
import pickle
import random
import sys
import os
import numpy as np
from os import listdir
from os.path import isfile, join
from nltk.corpus import wordnet, stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem.snowball import EnglishStemmer
from trie import Trie


# Augmentation using general domain data
def trie_regex_from_words(words):
    trie = Trie()
    for word in words:
        trie.add(word)

    regex_pattern=trie.pattern()
    return re.compile(r"\b" + regex_pattern + r"\b", re.IGNORECASE)


class GeneralAugmentor():
    """ This is the class that augment the text using general domain knowledge
    """

    def __init__(
        self,
        config_file = None
    ):
        """ information related to processing EHR notes, passed by a configuration file
        """
        self.config = self._load_config (config_file)
        self.stopwords = set(stopwords.words('english'))
        self.stopwords.update(["alzheimer", "ad", "sob", "x"])

        self.stemmer = EnglishStemmer()
        self.regex_family_fh = trie_regex_from_words(self.config['family_members_fh'])
        self.regex_family_oth = trie_regex_from_words(self.config['family_members_oth'])

    def _load_config(self, config_file):
        config_dict = {}

        with open(config_file, "r") as f :
            for line in f.readlines():
                if re.search(r"^#", line) or re.search(r"^ *$", line):
                    continue
                else:
                    key, value = line.split(":")
                    if re.search(r"family_members", key):
                        val = [ re.search(r"^ *(.*[a-zA-Zé]) *$", v).group(1) for v in value.split(",")]
                        config_dict[key] = val

        return config_dict


    def concentrate(self, sent, max_len = 100, focus = ""):
        token_ls = word_tokenize(sent)
        new_sent = sent
        shortened = False
        if len(token_ls) > max_len:
            sent_ls = sent_tokenize(sent)
            for sent in sent_ls:
                if focus in sent:
                    new_sent = sent
                    shortened = True
                    break

        return new_sent, shortened


    def transform(self, sent):
        token_ls = word_tokenize(sent)
        
        new_token_ls = []
        num_replaced = 0

        for w in token_ls:
            changed = False
            if w == "AD":
                w = "Alzheimer"

            elif re.search("^AD\-related", w):
                w = re.sub(r"^AD-", "Alzheimer ", w)
                changed = True

            elif len(w) > 2 or re.search(r"[a-z]", w):
                w = w.lower()
                changed = True
                
                if re.search(r"(alzheimer)|(alheimer)", w):
                    w = "Alzheimer"
                                        
            new_token_ls.append(w)

            if changed:
                num_replaced += 1


        new_sent = sent

        if num_replaced > 0:
            new_sent = " ".join(new_token_ls)
            ##print(f"warning-1.1 (transform): converted {sent} => {new_sent}")

        else:
            pass
            ##print(f"warning-1.2 (transform): failed to convert {sent}")

        return new_sent, num_replaced


    def replace_family_member(self, sent):
        token_ls = word_tokenize(sent)
        num_replaced = 0

        new_token_ls = []
        for w in token_ls:
            if self.regex_family_fh.search(w) or self.regex_family_fh.search(self.stemmer.stem(w)):
                new_token_ls.append("family member")
                num_replaced += 1

            elif self.regex_family_oth.search(w) or self.regex_family_oth.search(self.stemmer.stem(w)):
                new_token_ls.append("family member " + w)
                num_replaced += 1

            else:
                new_token_ls.append(w)
            
        new_sent = sent
        if num_replaced > 0:
            new_sent = " ".join(new_token_ls)
            ##print(f"warning-2.1 (family): converted {sent} => {new_sent}")

        else:
            pass
            ##print(f"warning-2.2 (family): failed to convert {sent}")

        return new_sent, num_replaced

