# -*- coding: utf-8 -*-
'''
Created on 14.10.2019

@author: Katrin Ortmann
'''

import re

############################

class Processor(object):

    def __init__(self):
        pass

############################

class PronounLemmatizer(Processor):

    def __init__(self):
        pass

    #####################

    def process(self, doc):

        for sent in doc.sentences:
            for tok in sent.tokens:
                if tok.__dict__.get("LEMMA", "_") in ["_", ""]:
                    if tok.XPOS == "PPER":
                        #ich, mich, mir, mier, mihr
                        if re.match(r"(m?ich|mie?h?r)", tok.FORM, re.IGNORECASE) != None:
                            tok.LEMMA = "ich"
                        #wir, wier, wihr, wiehr, uns, unß, unSchaft-s
                        elif re.match(r"(wie?h?r|un[sßſ]+)", tok.FORM, re.IGNORECASE) != None:
                            tok.LEMMA = "wir"
                        else:
                            tok.LEMMA = "_"
                    elif tok.XPOS == "PDS":
                        #dieser, diese, dies, diesen, dieses (mit s/ß/Schaft-s, mit/ohne ie)
                        if re.match(r"die?[sßſ]+(e|er|en|es)?", tok.FORM, re.IGNORECASE) != None:
                            tok.LEMMA = "diese"
                        #die, der, das, den, dem, dessen, denen, derer, deren, dero
                        elif re.match(r"(der|die|das|den|dem|de[sßſ]+en|denen|dere[nr]|dero)", tok.FORM, re.IGNORECASE) != None:
                            tok.LEMMA = "die"
                        else:
                            tok.LEMMA = "_"
                    else:
                        tok.LEMMA = "_"
                        
        return doc

##########################

class BracketRemover(Processor):

    def __init__(self):
        pass

    #####################

    def process(self, doc):

        brackets = ["(", ")", "{", "}", "[", "]", "<", ">"]

        for sent in doc.sentences:
            for tok in sent.tokens:

                if any(c.isalnum() for c in tok.FORM) and any(b in tok.FORM for b in brackets):
                    for b in brackets:
                        if b in tok.FORM:
                            tok.FORM = tok.FORM.replace(b, "")                   

        return doc

############################

class EllipsisRemover(Processor):

    def __init__(self):
        pass

    #####################

    def process(self, doc):

        for sent in doc.sentences:
            sent.tokens = [tok for tok in sent.tokens if not tok.__dict__.get("type", "_") == "E"]

        return doc

##############################
