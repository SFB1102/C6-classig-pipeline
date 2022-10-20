# -*- coding: utf-8 -*-
'''
Created on 14.10.2019

@author: Katrin Ortmann
'''

import os
from corpus import Doc, Sentence, Token

############################

class Importer(object):

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

############################

class CoNLLUPlusImporter(Importer):

    ###############################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ###############################
    
    def get_columns(self, file):
        columns = dict()

        line = ""
        while not line.strip():
            line = file.__next__()

        if line.strip().startswith("#"):
        
            #Document includes column info
            if "global.columns" in line:
                columns = {col : i for i, col in enumerate(line.strip().split("=")[-1].split())}

        return columns

    ###############################

    def import_file(self, file):
        
        _, filename = os.path.split(file)
    
        #Open file
        conllfile = open(file, mode="r", encoding="utf-8")
        
        #Get columns
        columns = self.get_columns(conllfile)
        if not columns:
            print("ERROR: Missing column information for {0}.".format(filename))
            return None

        #Create doc object
        doc = Doc(filename)

        tokens = list()
        metainfo = dict()

        for line in conllfile:

            #Empty line = end of sentence
            if not line.strip() and tokens:
                if not "text" in metainfo:
                    metainfo["text"] = " ".join([tok.FORM for tok in tokens])
                sentence = Sentence(**metainfo)
                for tok in tokens:
                    sentence.add_token(tok)
                tokens.clear()
                metainfo.clear()
                doc.add_sent(sentence)

            #Comment line = meta data
            elif line.strip().startswith("#"):
                line = line.lstrip("#").strip().split("=")
                metainfo[line[0].strip()] = "=".join(line[1:]).strip() 

            #Token line
            elif line.strip():
                line = line.strip().split("\t")
                values = dict()
                for col in columns:
                    try:
                        values[col] = line[columns.get(col, None)]
                    except IndexError:
                        values[col] = "_"
                tok = Token(**values)     
                tokens.append(tok)

        #If file does not end with empty line
        #save remaining last sentence
        if tokens:
            if not "text" in metainfo:
                metainfo["text"] = " ".join([tok.FORM for tok in tokens])
            sentence = Sentence(**metainfo)
            for tok in tokens:
                sentence.add_token(tok)
            tokens.clear()
            metainfo.clear()
            doc.add_sent(sentence)

        conllfile.close()

        return doc


############################

class CoNLL2000Importer(Importer):

    COLUMNS = {"FORM" : 0, "XPOS" : 1, "CHUNK" : 2}

    ###############################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ###############################

    def import_file(self, file):

        _, filename = os.path.split(file)

        #Open file
        conllfile = open(file, mode="r", encoding="utf-8")

        #Create doc object
        doc = Doc(filename)

        tokens = list()
        metainfo = dict()

        for line in conllfile:

            #Empty line = end of sentence
            if not line.strip() and tokens:
                if not "text" in metainfo:
                    metainfo["text"] = " ".join([tok.FORM for tok in tokens])
                sentence = Sentence(**metainfo)
                for tok in tokens:
                    sentence.add_token(tok)
                tokens.clear()
                metainfo.clear()
                doc.add_sent(sentence)

            #Skip comment lines
            elif line.strip().startswith("#"):
                continue

            #Token line
            elif line.strip():
                if "\t" in line.strip():
                    line = line.strip().split("\t")
                else:
                    line = line.strip().split(" ")
                values = dict()
                for col in self.COLUMNS:
                    try:
                        values[col] = line[self.COLUMNS.get(col, None)]
                    except IndexError:
                        values[col] = "_"
                tok = Token(**values)
                tokens.append(tok)

        #If file does not end with empty line
        #save remaining last sentence
        if tokens:
            if not "text" in metainfo:
                metainfo["text"] = " ".join([tok.FORM for tok in tokens])
            sentence = Sentence(**metainfo)
            for tok in tokens:
                sentence.add_token(tok)
            tokens.clear()
            metainfo.clear()
            doc.add_sent(sentence)

        conllfile.close()

        return doc

############################
