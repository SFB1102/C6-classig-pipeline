# -*- coding: utf-8 -*-
'''
Created on 14.10.2019

@author: Katrin Ortmann
'''

import os, re, html
import xml.etree.ElementTree as ET
from collections import OrderedDict
from C6C.src.document import Doc, Sentence, Token, Tree
from C6C.src.utils import normalize_filename

############################

class Importer(object):

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    def import_file(self, file, metadir):
        pass

############################

class TCFDTAImporter(Importer):
    #TODO Complete importer with meta data

    namespaces = {"corpus" : "http://www.dspin.de/data/textcorpus",
                  "meta" : "http://www.dspin.de/data/metadata"}

    ##############################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ##############################

    def import_file(self, file, metadir):

        path, filename = os.path.split(file)
        filename, ext = os.path.splitext(filename)

        doc = Doc(filename)

        #Read tcf tree
        tree = ET.parse(file)
        root = tree.getroot()

        #Store tcf annotations in dictionary to speed up conversion
        tcf_dict = self.get_annotations_from_tcf(root.find(".//corpus:TextCorpus", self.namespaces))

        #Find text element
        textElem = root.find(".//corpus:TextCorpus", self.namespaces)

        #Find sentences element
        sentencesElem = textElem.find(".//corpus:sentences", self.namespaces)

        #Create sentence object for each sentence
        for sentElem in sentencesElem:

            sent = Sentence(**{"tcf_id" : sentElem.attrib["ID"]})

            #TODO Reconstruct original text

            #Get token ids for tokens in the sentence
            tok_ids = [tok_id for tok_id in sentElem.attrib["tokenIDs"].split()]

            #Get annotations for tokens from tcf file
            #(use dictionary here to speed up look-up)
            for tok_id in tok_ids:
                form = tcf_dict[tok_id]["token"]
                try:
                    pos = tcf_dict[tok_id]["pos"]
                except:
                    pos = "_"
                try:
                    lemma = tcf_dict[tok_id]["lemma"]
                except:
                    lemma = "_"
                try:
                    norm = tcf_dict[tok_id]["norm"]
                    norm_operation = tcf_dict[tok_id]["norm_operation"]
                    norm_reason = tcf_dict[tok_id]["norm_reason"]
                except:
                    norm = "_"
                    norm_operation = "_"
                    norm_reason = "_"

                token = Token(**{"FORM" : form, "XPOS" : pos, "LEMMA" : lemma, \
                                 "NORM" : norm, "NORM_OP" : norm_operation, "NORM_REASON" : norm_reason})

                sent.add_token(token)

            doc.add_sent(sent)

        return doc

    #################################

    def get_annotations_from_tcf(self, textElem):
        """
        Store all annotations (except sentences) from a given TCF file
        in a dictionary to speed up the conversion.
        Input: Text element of the TCF file.
        Output: Dictionary with token indices as keys and annotations as key value pairs
                { "w1" : { "token" : "Vier", "lemma" : "vier", "pos" : "CARD",
                           "norm" : "", "norm_operation" : "", "norm_reason" : ""},
                  ...
                }
                "norm", "norm_operation" and "norm_reason" keys may be missing for single tokens
        """
        tcf_dict = dict()

        for token in textElem.findall(".//corpus:token", self.namespaces):
            tcf_dict[token.attrib["ID"]] = {"token" : token.text}

        for pos in textElem.findall(".//corpus:POStags/corpus:tag", self.namespaces):
            tcf_dict[pos.attrib["tokenIDs"]]["pos"] = pos.text

        for lemma in textElem.findall(".//corpus:lemma", self.namespaces):
            tcf_dict[lemma.attrib["tokenIDs"]]["lemma"] = lemma.text

        for norm in textElem.findall(".//corpus:orthography/corpus:correction", self.namespaces):
            tcf_dict[norm.attrib["tokenIDs"]]["norm"] = norm.text
            if "operation" in norm.attrib:
                tcf_dict[norm.attrib["tokenIDs"]]["norm_operation"] = norm.attrib["operation"]
            else:
                tcf_dict[norm.attrib["tokenIDs"]]["norm_operation"] = "*"
            if "reason" in norm.attrib:
                tcf_dict[norm.attrib["tokenIDs"]]["norm_reason"] = norm.attrib["reason"]
            else:
                tcf_dict[norm.attrib["tokenIDs"]]["norm_reason"] = "*"

        return tcf_dict

############################

class XMLDTAImporter(Importer):

    namespaces = {"default" : "http://www.tei-c.org/ns/1.0"}
    filenr = 0

    ################################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ################################

    def read_metaheader(self, metaheader):
        """
        Read info from metaheader element into dictionary.
        Currently included are:
        - filename, DTA filename
        - author
        - title, subtitle
        - year, place
        - tokens, types, characters
        - URL
        - text class (DTA main), text class (DTA sub)
        - language code, language
        If info not available, value is NA.
        Input: Metaheader element from xml tree
        Output: Dictionary with meta info
        """
        metainfo = dict()

        #Author
        try:
            authornames = ""
            authors = metaheader.findall("./default:fileDesc/default:titleStmt/default:author", namespaces=self.namespaces)
            for author in authors:
                if authornames: authornames += ", "
                forename = author.find("./default:persName/default:forename", namespaces=self.namespaces)
                if forename != None: authornames += forename.text
                surname = author.find("./default:persName/default:surname", namespaces=self.namespaces)
                if surname != None: authornames += " " + surname.text
            metainfo["author"] = authornames.strip()
        except:
            metainfo["author"] = authornames.strip()
        if not metainfo["author"]: metainfo["author"] = "NA"

        #Title
        try:
            titleElem = metaheader.find("./default:fileDesc/default:titleStmt", namespaces=self.namespaces)
            if titleElem.findall("./default:title[@type='main']", namespaces=self.namespaces) != None:
                metainfo["title"] = titleElem.find("./default:title[@type='main']", namespaces=self.namespaces).text.strip()
                if titleElem.find("./default:title[@type='sub']", namespaces=self.namespaces) != None:
                    metainfo["subtitle"] = titleElem.find("./default:title[@type='sub']", namespaces=self.namespaces).text.strip()
                else:
                    metainfo["subtitle"] = "NA"
            else:
                metainfo["title"] = "NA"
                metainfo["subtitle"] = "NA"
        except:
            if not "title" in metainfo: metainfo["title"] = "NA"
            if not "subtitle" in metainfo: metainfo["subtitle"] = "NA"

        #Year
        try:
            metainfo["year"] = metaheader.find("./default:fileDesc/default:sourceDesc/default:biblFull/default:publicationStmt/default:date", namespaces=self.namespaces).text.strip()
        except:
            metainfo["year"] = "NA"

        #Place
        try:
            metainfo["place"] = metaheader.find("./default:fileDesc/default:sourceDesc/default:biblFull/default:publicationStmt/default:pubPlace", namespaces=self.namespaces).text.strip()
        except:
            metainfo["place"] = "NA"

        #Tokens
        try:
            metainfo["tokens"] = metaheader.find("./default:fileDesc/default:extent/default:measure[@type='tokens']", namespaces=self.namespaces).text.strip()
        except:
            metainfo["tokens"] = "NA"

        #Types
        try:
            metainfo["types"] = metaheader.find("./default:fileDesc/default:extent/default:measure[@type='types']", namespaces=self.namespaces).text.strip()
        except:
            metainfo["types"] = "NA"

        #Characters
        try:
            metainfo["characters"] = metaheader.find("./default:fileDesc/default:extent/default:measure[@type='characters']", namespaces=self.namespaces).text.strip()
        except:
            metainfo["characters"] = "NA"

        #URL
        try:
            metainfo["URL"] = metaheader.find("./default:fileDesc/default:publicationStmt/default:idno/default:idno[@type='URLWeb']", namespaces=self.namespaces).text.strip()
        except:
            metainfo["URL"] = "NA"

        #Text class
        try:
            textClassElem = metaheader.find("./default:profileDesc/default:textClass", namespaces=self.namespaces)
            for classCode in textClassElem:
                if "scheme" in classCode.attrib and classCode.attrib["scheme"].endswith("dtamain"):
                    metainfo["text class (DTA main)"] = classCode.text.strip()
                elif "scheme" in classCode.attrib and classCode.attrib["scheme"].endswith("dtasub"):
                    metainfo["text class (DTA sub)"] = classCode.text.strip()
            if not "text class (DTA main)" in metainfo:
                for classCode in textClassElem:
                    if "scheme" in classCode.attrib and classCode.attrib["scheme"].endswith("dwds1main"):
                        metainfo["text class (DTA main)"] = classCode.text.strip()
            if not "text class (DTA sub)" in metainfo:
                for classCode in textClassElem:
                    if "scheme" in classCode.attrib and classCode.attrib["scheme"].endswith("dwds1sub"):
                        metainfo["text class (DTA sub)"] = classCode.text.strip()
            if not "text class (DTA main)" in metainfo:
                metainfo["text class (DTA main)"] = "NA"
            if not "text class (DTA sub)" in metainfo:
                metainfo["text class (DTA sub)"] = "NA"

        except:
            metainfo["text class (DTA main)"] = "NA"
            metainfo["text class (DTA sub)"] = "NA"

        #Language
        try:
            langElem = metaheader.find("./default:profileDesc/default:langUsage/default:language", namespaces=self.namespaces)
            if "ident" in langElem.attrib:
                metainfo["language code"] = langElem.attrib["ident"].strip()
            else:
                metainfo["language code"] = "NA"
            metainfo["language"] = langElem.text.strip()
        except:
            metainfo["language code"] = "NA"
            metainfo["language"] = "NA"

        #Remove linebreaks from meta data
        for key in metainfo:
            metainfo[key] = re.sub(r"\n", " ", metainfo[key])

        #Generate new filename
        class_ = metainfo["text class (DTA sub)"]
        if class_ == "NA":
            class_ = metainfo["text class (DTA main)"]
        class_ = normalize_filename(class_)

        metainfo["filename"] = "{:04d}_{}_{}".format(self.filenr, \
                                                         class_, \
                                                         metainfo["year"])

        return metainfo

    ################################

    def output_metainfo(self, metainfo, metadir):
        """
        Append metainfo for a given file to a csv-file in metadir.
        Input: Dictionary with meta information, target directory
        """
        metacats = ["filename", "DTA filename", "author", "title", "subtitle", \
                     "year", "place", "tokens", "types", "characters", \
                     "URL", "text class (DTA main)", "text class (DTA sub)", \
                     "language code", "language"]

        metafile = open(os.path.join(metadir, "dta_meta_information.csv"), mode="a", encoding="utf-8")

        #Write header if
        if metafile.tell() == 0:
            print("\t".join(metacats), file=metafile)

        print("\t".join([metainfo[metacat] for metacat in metacats]), file=metafile)

        metafile.close()

    ################################

    def get_paragraphs(self, textElem):
        """
        Find all paragraphs and store the IDs of sentences appearing in them
        to facilitate parsing and look-up of paragraph IDs.
        Input: Text element
        Output: Dictionary with sentence IDs (s145, s235_3, ...) as keys
                and their corresponding paragraph ID (1..n) as value.
        """
        paragraphs = textElem.findall(".//default:p", namespaces=self.namespaces)
        pdict = dict()
        for i,paragraph in enumerate(paragraphs):
            pdict[str(i+1)] = set()
            for sentence in paragraph.findall(".//default:s", namespaces=self.namespaces):
                pdict[str(i+1)].add(sentence.attrib.get(r"{http://www.w3.org/XML/1998/namespace}id", None))
        reversedpdict = dict()
        for p, v in pdict.items():
            for s in v:
                if s != None:
                    reversedpdict[s] = p
        return reversedpdict

    ################################

    def get_divtypes(self, textElem):
        """
        Find all div elements with a specified type
        and store the IDs of sentences appearing in them
        to facilitate parsing and look-up of div types.
        Input: Text element
        Output: Dictionary with sentence IDs (s145, s235_3, ...) as keys
                and their corresponding div types as value.
        """
        #Check if type is specified and not a number
        div_types = textElem.findall(".//default:div[@type]", namespaces=self.namespaces)
        divdict = dict()
        for div in div_types:
            divdict[div.attrib.get("type", None)] = set()
            for sentence in div.findall(".//default:s", namespaces=self.namespaces):
                divdict[div.attrib.get("type", None)].add(sentence.attrib.get(r"{http://www.w3.org/XML/1998/namespace}id", None))
        reverseddivdict = dict()
        for k, v in divdict.items():
            if k == None: continue
            for s in v:
                if s != None:
                    if s in reverseddivdict:
                        reverseddivdict[s].add(k)
                    else:
                        reverseddivdict[s] = {k}
        return reverseddivdict

    ################################

    def get_headlines_etc(self, textElem):
        """
        Find all headers, titles, ... and store the IDs of sentences appearing in them
        to facilitate parsing and look-up of headers, titles, etc.
        Input: Text element
        Output: Dictionary with sentence IDs (s145, s235_3, ...) as keys
                and their corresponding headers, titles, etc. as value.
        """
        headerdict = dict()

        for tag,name in [("titlePart[@type='main']", "title"), \
                         ("titlePart[@type='sub']", "subtitle"), \
                         ("head", "head"), ("note", "note")]:
            elems = textElem.findall(".//default:"+tag, namespaces=self.namespaces)

            for elem in elems:
                headerdict[name] = set()
                for sentence in elem.findall(".//default:s", namespaces=self.namespaces):
                    headerdict[name].add(sentence.attrib.get(r"{http://www.w3.org/XML/1998/namespace}id", None))

        reverseddict = dict()
        for k, v in headerdict.items():
            for s in v:
                if s != None:
                    if s in reverseddict:
                        reverseddict[s].add(k)
                    else:
                        reverseddict[s] = {k}
        return reverseddict

    ################################

    def get_sentences(self, textElem):

        sentences = OrderedDict()

        #Get sentences
        for sentence in textElem.findall(".//default:s", namespaces=self.namespaces):

            #Sentence ID DTA
            sentID = sentence.attrib.get(r"{http://www.w3.org/XML/1998/namespace}id", None)

            #Parse ID
            if "_" in sentID:
                match = re.match(r"s(?P<hex>[\d\w]+)_(?P<part>\d+)", sentID)
                sentpart = int(match.group("part"))
            else:
                match = re.match(r"s(?P<hex>[\d\w]+)", sentID)
                sentpart = 1
            hexval = match.group("hex")

            #Join sentence parts
            if hexval in sentences:
                sentences[hexval].append((sentpart, sentence))
            else:
                sentences[hexval] = [(sentpart, sentence)]

        #Reorder sentence parts according to ID
        for s in sentences:
            sentences[s] = [sent for (sentpart,sent) in sorted(sentences[s])]

        return sentences

    ################################

    def get_words(self, sentenceElems):

        words = OrderedDict()

        for sentElem in sentenceElems:
            #Get words
            for word in sentElem.findall(".//default:w", namespaces=self.namespaces):

                #Word ID DTA
                wordID = word.attrib.get(r"{http://www.w3.org/XML/1998/namespace}id", None)

                #Parse ID
                if "_" in wordID:
                    match = re.match(r"w(?P<hex>[\d\w]+)_(?P<part>\d+)", wordID)
                    wordpart = int(match.group("part"))
                else:
                    match = re.match(r"w(?P<hex>[\d\w]+)", wordID)
                    wordpart = 0
                hexval = match.group("hex")

                if hexval in words:
                    words[hexval].append((wordpart, word))
                else:
                    words[hexval] = [(wordpart, word)]

        for w in words:
            words[w] = [word for (wordpart,word) in sorted(words[w])]

        return words

    ################################

    def import_file(self, file, metadir):

        self.filenr += 1

        path, filename = os.path.split(file)
        filename, ext = os.path.splitext(filename)

        #Read xml tree
        tree = ET.parse(file)
        root = tree.getroot()

        metaheader = root.find("default:teiHeader", namespaces=self.namespaces)
        textElem = root.find("default:text", namespaces=self.namespaces)

        #Read meta info
        metainfo = self.read_metaheader(metaheader)
        metainfo["DTA filename"] = filename+ext

        self.output_metainfo(metainfo, metadir)

        doc = Doc(**metainfo)

        #Look up which sentences appear in which paragraphs
        paragraphs = self.get_paragraphs(textElem)

        #Look up div types
        divtypes = self.get_divtypes(textElem)

        #Get headers, titles, etc.
        headers = self.get_headlines_etc(textElem)

        #Get sentences
        sentences = self.get_sentences(textElem)
        for _, sentence in sentences.items():

            sent = Sentence(**{"text" : ""})

            #For each sentence part
            for i, sentpart in enumerate(sentence):

                #Sentence ID DTA
                sentID = sentpart.attrib.get(r"{http://www.w3.org/XML/1998/namespace}id", None)
                if i == 0:
                    sent.__dict__["sent_id(DTA)"] = sentID
                else:
                    sent.__dict__["sent_id(DTA)"] += ", " + sentID

                #Get paragraph ID
                paragraph_id = paragraphs.get(sentID, None)
                if paragraph_id:
                    if "paragraph_id" in sent.__dict__ and not paragraph_id in sent.__dict__["paragraph_id"]:
                        sent.__dict__["paragraph_id"] += ", " + paragraph_id
                    elif not "paragraph_id" in sent.__dict__:
                        sent.__dict__["paragraph_id"] = paragraph_id

                #Get div type
                div_type = divtypes.get(sentID, None)
                if div_type:
                    if "div_type" in sent.__dict__:
                        for d in div_type:
                            if not d in sent.__dict__["div_type"]:
                                sent.__dict__["div_type"] += ", " + d
                    elif "div_type" in sent.__dict__:
                        sent.__dict__["div_type"] = ", ".join(div_type)

                #Get header, title, ...
                header_title_etc = headers.get(sentID, None)
                if header_title_etc:
                    if "text_section" in sent.__dict__:
                        for h in header_title_etc:
                            if not h in sent.__dict__["text_section"]:
                                sent.__dict__["text_section"] += ", " + h
                    else:
                        sent.__dict__["text_section"] = ", ".join(header_title_etc)

            words = self.get_words(sentence)

            for _, word in words.items():

                kwargs = {}

                #For each word part
                for i, wordpart in enumerate(word):

                    #DTA id
                    if "DTA:ID" in kwargs:
                        kwargs["DTA:ID"] += "," + wordpart.attrib.get(r"{http://www.w3.org/XML/1998/namespace}id")
                    else:
                        kwargs["DTA:ID"] = wordpart.attrib.get(r"{http://www.w3.org/XML/1998/namespace}id")

                    #Form
                    tokform = "".join(wordpart.itertext())
                    tokform = re.sub(r"\n", "<lb/>", tokform)
                    #Add final linebreak if deleted by ElementTree
                    if not tokform.endswith("<lb/>"):
                        #Part of word's tail
                        if wordpart.tail and wordpart.tail.endswith("\n"):
                            tokform += "<lb/>"
                        #Part of sentence tail
                        elif len(sentence) > 1 \
                         and any(wordpart == sentpart[-1] \
                                 and sentpart.tail \
                                 and sentpart.tail.endswith("\n") \
                                 for sentpart in sentence \
                                     if not sentpart == sentence[-1]):
                            tokform += "<lb/>"

                    tokform = re.sub(r"\s", "", tokform)

                    #First token part contains annotations
                    if i == 0:
                        kwargs["FORM"] = tokform

                        #XPOS
                        kwargs["XPOS"] = wordpart.attrib.get("pos", "_")

                        #Lemma
                        kwargs["LEMMA"] = wordpart.attrib.get("lemma", "_")

                        #Norm
                        kwargs["DTA:NORM"] = wordpart.attrib.get("norm", "_")

                        #Orig
                        kwargs["DTA:ORIG"] = wordpart.attrib.get("orig", "_")

                        #Reg
                        kwargs["DTA:REG"] = wordpart.attrib.get("reg", "_")

                    else:
                        #Form
                        kwargs["FORM"] += tokform

                    #Remove multiple adjacent linebreaks
                    while re.search(r"(<lb/>){2,}", kwargs["FORM"]):
                        kwargs["FORM"] = re.sub(r"(<lb/>){2,}", "<lb/>", kwargs["FORM"])

                #Reconstruct text
                if "join" in word[0].attrib and word[0].attrib["join"] in ("left", "both"):
                    sent.text += kwargs["FORM"]
                elif sent.text:
                    sent.text += " " + kwargs["FORM"]
                else:
                    sent.text += kwargs["FORM"]

                if not kwargs["FORM"].strip(): kwargs["FORM"] = "_"

                tok = Token(**kwargs)

                sent.add_token(tok)

            if sent.text.endswith("<lb/>"):
                print(filename, sent.__dict__["sent_id(DTA)"])
            doc.add_sent(sent)

        return doc

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

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

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
                if "-" in values["ID"]:
                    continue
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

class CoNLLUImporter(Importer):

    ###############################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ###############################

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

        #Open file
        conllfile = open(file, mode="r", encoding="utf-8")

        #column names
        columns = {"ID" : 0, "FORM" : 1, "LEMMA" : 2, "UPOS" : 3, "XPOS" : 4, \
                   "FEATS" : 5, "HEAD" : 6, "DEPREL" : 7, "DEPS" : 8, "MISC" : 9}

        #Create doc object
        doc = Doc(filename)

        tokens = list()
        metainfo = dict()

        punct_l= [".", ",", ":", ";", "!", "?", ")", "]"]
        punct_r= ["(", "["]

        for line in conllfile:

            if not line.strip() and tokens:
                if not "text" in metainfo:
                    metainfo["text"]= ""
                    for tok in tokens:
                        #first token
                        if not metainfo["text"]:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        #token is punctuation
                        elif tok.FORM in punct_l:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        elif tok.FORM in punct_r:
                            metainfo["text"] = metainfo["text"] + " " + tok.FORM
                        #other token
                        else:
                            if metainfo["text"][-1] in punct_r:
                                metainfo["text"] = metainfo["text"] + tok.FORM
                            else:
                                metainfo["text"] = metainfo["text"] + " " + tok.FORM
                sentence = Sentence(**metainfo)
                for tok in tokens:
                    sentence.add_token(tok)
                tokens.clear()
                metainfo.clear()
                doc.add_sent(sentence)

            #Token line
            elif line.strip():
                line = line.strip().split("\t")
                values = dict()
                for col in columns:
                    values[col] = line[columns.get(col)]
                #RIDGES Corpus
                if "RIDGES" in path:
                    values["UPOS"] = "_"
                    values["DEPS"] = "_"
                    values["MISC"] = "_"
                tok = Token(**values)
                tokens.append(tok)

        #If file does not end with empty line
        #save remaining last sentence
        if tokens:
                if not "text" in metainfo:
                    metainfo["text"]= ""
                    for tok in tokens:
                        #first token
                        if not metainfo["text"]:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        #token is punctuation
                        elif tok.FORM in punct_l:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        elif tok.FORM in punct_r:
                            metainfo["text"] = metainfo["text"] + " " + tok.FORM
                        #other token
                        else:
                            if metainfo["text"][-1] in punct_r:
                                metainfo["text"] = metainfo["text"] + tok.FORM
                            else:
                                metainfo["text"] = metainfo["text"] + " " + tok.FORM
                sentence = Sentence(**metainfo)
                for tok in tokens:
                    sentence.add_token(tok)
                tokens.clear()
                metainfo.clear()
                doc.add_sent(sentence)

        conllfile.close()

        return doc

############################

class TigerImporter(Importer):

    ###############################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ###############################

    def read_metadocs(self, metadocs, filename):
        """
        Read info from metadocuments into dictionary.
        Currently included are:
        - filename
        - author (name, gender)
        - sentence type (only in conllup doc, not in metafile)
        - folder (train/dev/test)
        - category of note (COLLECTION/OTHER)
        - note (type/heading of collection doc/description)
        If info not available, value is NA.
        Input: path of directory which includes all metadocuments, filename
        Output: Dictionary with meta info
        """

        #filename
        metainfo = dict()
        name= filename.split(".")[0]
        metainfo["filename"]= name

        #authors
        authors= open(metadocs + "\\authors.tsv", mode="r", encoding="utf-8")
        genders=["fem", "masc"]
        for line in authors:
            line= line.strip().split("\t")
            if name in line:
                for x in range(1, len(line)):
                    if line[x] not in genders:
                        if "author" not in metainfo:
                            metainfo["author"]= line[x]
                        else:
                            metainfo["author"]= metainfo["author"] + ", " + line[x]
                    else:
                        if "gender" not in metainfo:
                            metainfo["gender"]= line[x]
                        else:
                            metainfo["gender"]= metainfo["gender"] + ", " + line[x]
                break
        #if info not available
        if "author" not in metainfo:
            metainfo["author"]= "NA"
        if "gender" not in metainfo:
            metainfo["gender"]= "NA"
        authors.close()

        #sentence type
        types= dict()
        sentences= open(metadocs + "\\sentences.tsv", mode="r", encoding="utf-8")
        for line in sentences:
            line= line.strip().split("\t")
            types[line[1]]= line[2]
        metainfo["sent_types"]= types
        sentences.close()

        #folder
        train= open(metadocs + "\\documents_train.tsv", mode="r", encoding="utf-8")
        dev= open(metadocs + "\\documents_dev.tsv", mode="r", encoding="utf-8")
        test= open(metadocs + "\\documents_test.tsv", mode="r", encoding="utf-8")
        i= 0
        for line in train:
            if name == line.strip():
                metainfo["folder"]= "train"
                i= 1
                break
        if i==0:
            for line in dev:
                if name == line.strip():
                    metainfo["folder"]= "dev"
                    i= 1
                    break
        if i==0:
            for line in test:
                if name == line.strip():
                    metainfo["folder"]= "test"
                    i= 1
                    break
        if i==0:
            metainfo["folder"]= "NA"
        test.close()
        dev.close()
        train.close()

        #notes
        notes= open(metadocs + "\\documents_notes.tsv", mode="r", encoding="utf-8")
        for line in notes:
            line= line.strip().split("\t")
            if name in line:
                metainfo["category of note"]= line[1]
                metainfo["note"]= line[2]
        #if info not available
        if "category of note" not in metainfo:
            metainfo["category of note"]= "NA"
        if "note" not in metainfo:
            metainfo["note"]= "NA"
        notes.close()

        return metainfo

    ################################

    def output_metainfo(self, metainfo, metadir):
        """
        Append metainfo for a given file to a csv-file in metadir.
        Input: Dictionary with meta information, target directory
        """
        metacats = ["filename", "folder", "author", "gender", "category of note", "note"]

        metafile = open(os.path.join(metadir, "tiger_meta_information.csv"), mode="a", encoding="utf-8")

        #Write header if
        if metafile.tell() == 0:
            print("\t".join(metacats), file=metafile)

        print("\t".join([metainfo[metacat] for metacat in metacats]), file=metafile)

        metafile.close()

    ################################

    def import_file(self, file, metadir):

        path, filename = os.path.split(file)

        metadocs= file.split("\\conll09")[0] + "\\TIGER2.2.doc"
        metainfo= self.read_metadocs(metadocs, filename)
        self.output_metainfo(metainfo, metadir)

        #Open file
        conllfile = open(file, mode="r", encoding="utf-8-sig")


        columns = {"ID" : 0, "FORM" : 1, "LEMMA" : 2, "PLEMMA" : 3, "XPOS" : 4, \
                   "PPOS" : 5, "FEATS" : 6, "PFEAT" : 7, "HEAD" : 8, "PHEAD" : 9, \
                   "DEPREL" : 10, "PDEPREL" : 11, "FILLPRED" : 12, "PRED" : 13, "APREDs" : 14}

        #Create doc object
        doc = Doc(filename)

        tokens = list()
        types = metainfo["sent_types"]

        punct_l= [".", ",", ":", ";", "!", "?", ")", "]", "''", "/"]
        punct_r= ["(", "[", "`", "/"]

        for line in conllfile:

            #Empty line = end of sentence
            if not line.strip() and tokens:
                if not "text" in metainfo:
                    metainfo["text"]= ""
                    for tok in tokens:

                        #seperate sent_id(Tiger) and tok_id
                        tiger_id, tok_id = tok.ID.split("_")
                        tok.ID = tok_id
                        if not "sent_id(Tiger)" in metainfo:
                            metainfo["sent_id(Tiger)"]= tiger_id
                        #sentence type
                        if not "sent_type" in metainfo:
                            metainfo["sent_type"]= types[tiger_id]

                        #first token
                        if not metainfo["text"]:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        #token is punctuation
                        elif tok.FORM in punct_l:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        elif tok.FORM in punct_r:
                            metainfo["text"] = metainfo["text"] + " " + tok.FORM
                        #other token
                        else:
                            if metainfo["text"][-1] in punct_r:
                                metainfo["text"] = metainfo["text"] + tok.FORM
                            else:
                                metainfo["text"] = metainfo["text"] + " " + tok.FORM
                sentence = Sentence(**metainfo)
                for tok in tokens:
                    sentence.add_token(tok)
                tokens.clear()
                metainfo.clear()
                doc.add_sent(sentence)

            #Token line
            elif line.strip():
                line = line.strip().split("\t")
                values = dict()
                for col in columns:
                    values[col] = line[columns.get(col)]
                tok = Token(**values)
                tokens.append(tok)

        #If file does not end with empty line
        #save remaining last sentence
        if tokens:
                if not "text" in metainfo:
                    metainfo["text"]= ""
                    for tok in tokens:

                        #seperate sent_id(Tiger) and tok_id
                        tiger_id, tok_id = tok.ID.split("_")
                        tok.ID = tok_id
                        if not "sent_id(Tiger)" in metainfo:
                            metainfo["sent_id(Tiger)"]= tiger_id
                        #sentence type
                        if not "sent_type" in metainfo:
                            metainfo["sent_type"]= types[tiger_id]

                        #first token
                        if not metainfo["text"]:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        #token is punctuation
                        elif tok.FORM in punct_l:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        elif tok.FORM in punct_r:
                            metainfo["text"] = metainfo["text"] + " " + tok.FORM
                        #other token
                        else:
                            if metainfo["text"][-1] in punct_r:
                                metainfo["text"] = metainfo["text"] + tok.FORM
                            else:
                                metainfo["text"] = metainfo["text"] + " " + tok.FORM
                sentence = Sentence(**metainfo)
                for tok in tokens:
                    sentence.add_token(tok)
                tokens.clear()
                metainfo.clear()
                doc.add_sent(sentence)

        conllfile.close()

        return doc

############################

class DTATSVImporter(Importer):

    ###############################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ###############################

    def get_columns(self, file, simplify=True):

        line = ""
        metalines = []
        while not line.strip():
            line = file.__next__()
            if line.strip().startswith("#"):
                metalines.append(line.strip())
                line = ""
            else:
                break

        colnames = ["TSVID", "CHARS", "FORM", "XPOS", "POS", "LEMMA", "OrthCorr",
                    "OrthCorrOp", "OrthCorrReason", "Cite", "AntecDepLink", "AntecMovElem",
                    "AntecHeadLink", "AntecHead", "AntecHeadLemLink", "AntecHeadLem",
                    "SentBrcktLink", "SentBrckt", "SentBrcktType", "MovElemAntecLink",
                    "MovElemAntec", "MovElemCat", "MovElemPos", "RelCType",
                    "MovElemRole", "MovElemTyp", "AdvCVPos", "AdvCVHead"]
        if not any("relctype" in line for line in metalines):
            colnames.remove("RelCType")
        if not any("webanno.custom.Citation" in line for line in metalines):
            colnames.remove("Cite")
        columns = {colname : i for i, colname in enumerate(colnames)}

        return columns

    ###############################

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

        #Open file
        tsvfile = open(file, mode="r", encoding="utf-8")

        #Get columns
        columns = self.get_columns(tsvfile)
        if not columns:
            print("ERROR: Missing column information for {0}.".format(filename))
            return None

        #Create doc object
        doc = Doc(filename)

        tokens = list()
        metainfo = dict()

        for line in tsvfile:

            #Empty line = end of sentence
            if not line.strip() and tokens:

                #Get sent_id(TSV)
                metainfo["sent_id(TSV)"] = tokens[0].TSVID.split("-")[0]

                if not "Cite" in columns:
                    tok.Cite = "_"
                if not "RelCType" in columns:
                    tok.RelCType = "_"

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
                metainfo[line[0].strip().lower()] = "=".join(line[1:]).strip()

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
            #Get sent_id(TSV)
            metainfo["sent_id(TSV)"] = tokens[0].TSVID.split("-")[0]
            if not "text" in metainfo:
                metainfo["text"] = " ".join([tok.FORM for tok in tokens])
            sentence = Sentence(**metainfo)
            for tok in tokens:
                sentence.add_token(tok)
            tokens.clear()
            metainfo.clear()
            doc.add_sent(sentence)

        tsvfile.close()

        return doc

############################

class TuebaDzImporter(Importer):

    ###############################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ################################

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

        #TODO: metainfo?; docs in train/dev/test

        #Open file
        conllfile = open(file, mode="r", encoding="utf-8")


        columns = {"ID" : 0, "FORM" : 1, "LEMMA" : 2, "UPOS" : 3, "XPOS" : 4, \
                    "FEATS" : 5, "HEAD" : 6, "DEPREL" : 7, "DEPS" : 8, "MISC" : 9}
        annotations = ["TopoField", "Typo", "Morph", "NE", "WSD"]

        #Create doc object
        doc = Doc(filename)

        tokens = list()
        metainfo = dict()

        punct_l= [".", ",", ":", ";", "!", "?", ")", "]", "/", '"']
        punct_r= ["(", "[", "/"]

        for line in conllfile:

            #Empty line = end of sentence
            if not line.strip() and tokens:
                #text correction (punctuation marks)
                x = 0
                while x < len(metainfo["text"])-1:
                    if metainfo["text"][x] in punct_r and metainfo["text"][x+1]==" ":
                        metainfo["text"]= metainfo["text"][:x+1] + metainfo["text"][x+2:]
                    x += 1
                y = 1
                while y < len(metainfo["text"]):
                    if metainfo["text"][y] in punct_l and metainfo["text"][y-1]==" ":
                        if metainfo["text"][y] =='"' and y < len(metainfo["text"])-1:
                            if metainfo["text"][y+1] == " ":
                                metainfo["text"]= metainfo["text"][:y-1] + metainfo["text"][y:]
                        else:
                            metainfo["text"]= metainfo["text"][:y-1] + metainfo["text"][y:]
                    y += 1
                sentence = Sentence(**metainfo)
                for tok in tokens:
                    sentence.add_token(tok)
                tokens.clear()
                metainfo.clear()
                doc.add_sent(sentence)

            elif line.strip():
                #doc_id tueba
                if "# newdoc" in line:
                    line, doc_id = line.strip().split(" = ")
                    metainfo["doc_id(tueba)"] = doc_id
                #sent_id
                elif "# sent_id" in line:
                    line, sent_id = line.strip().split(" = ")
                    metainfo["sent_id(tueba)"] = sent_id
                #text
                elif "# text" in line:
                    line, sign, text = line.strip().partition(" = ")
                    metainfo["text"] = text
                #Token line
                else:
                    line = line.strip().split("\t")
                    values = dict()
                    for col in columns:
                        values[col] = line[columns.get(col)]
                    #splitting column MISC
                    if values["MISC"] == "_":
                        for anno in annotations:
                            values[anno] = "_"
                    else:
                        misc = dict()
                        for value in values["MISC"].split("|"):
                            try:
                                anno, val = value.split("=")
                                misc[anno] = val
                            #if "=" is missing
                            except:
                                for anno in annotations:
                                        if anno in value:
                                            none, val = value.split(anno)
                                            misc[anno] = val
                        for anno in annotations:
                            if anno in misc:
                                values[anno] = misc[anno]
                            else:
                                values[anno] = "_"
                        #SpaceAfter = MISC
                        if "SpaceAfter" in misc:
                            values["MISC"] = "SpaceAfter=" + misc["SpaceAfter"]
                        else:
                            values["MISC"] = "_"
                    tok = Token(**values)
                    tokens.append(tok)

        #If file does not end with empty line
        #save remaining last sentence
        if tokens:
                sentence = Sentence(**metainfo)
                for tok in tokens:
                    sentence.add_token(tok)
                tokens.clear()
                metainfo.clear()
                doc.add_sent(sentence)

        conllfile.close()

        return doc

############################

class ANNISGridSentenceImporter(Importer):

    ###############################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ###############################

    def read_metainfo(self, file):
        """
        Read info from document into dictionary.
        Included are:
        - Dokumentname
        - Auswahl
        - Edition
        - Ueberlieferungstraeger
        - Sprachstufe
        - Teilkorpus
        If info not available, value is NA.
        Input: gridfile
        Output: Dictionary with meta info
        """
        path, filename = os.path.split(file)
        gridfile = open(file, mode="r", encoding="utf-8")

        metainfo = dict()
        metacats = ["doc", "Auswahl", "Edition", "Ueberlieferungstraeger", "Sprachstufe", "Teilkorpus"]

        for line in gridfile:
            if len(metainfo) == 6:
                break

            elif "meta" in line:
                for cat in metacats:
                    if "meta::" + cat in line:
                        meta, val = line.strip().split("\t")
                        #if info not available, value is NA
                        if val in ["k.A.", "k. A."]:
                            val = "NA"

                        if cat == "doc":
                            metainfo["Dokumentname"] = val
                        else:
                            metainfo[cat] = val
        gridfile.close()

        return metainfo

    ################################

    def output_metainfo(self, metainfo, metadir):
        """
        Append metainfo for a given file to a csv-file in metadir.
        Input: Dictionary with meta information, target directory
        """
        metacats = ["Dokumentname", "Auswahl", "Edition", "Ueberlieferungstraeger", "Sprachstufe", "Teilkorpus"]

        metafile = open(os.path.join(metadir, "hipkon_meta_information.csv"), mode="a", encoding="utf-8")

        #Write header if
        if metafile.tell() == 0:
            print("\t".join(metacats), file=metafile)

        print("\t".join([metainfo[metacat] for metacat in metacats]), file=metafile)

        metafile.close()

    ################################

    def import_file(self, file, metadir):

        path, filename = os.path.split(file)

        metainfo= self.read_metainfo(file)
        self.output_metainfo(metainfo, metadir)

        #Open file
        gridfile = open(file, mode="r", encoding="utf-8")

        columns = {"ID" : 0, "FORM" : 1, "VERLINKUNG" : 2, "GF" : 3, "FOKUS" : 4, \
                   "SATZKLAMMER" : 5, "SATZSTATUS" : 6, "POS" : 7, "CAT" : 8, "CLEAN" : 9, \
                   "EDITION" : 10, "IS" : 11, "Kommentar" : 12, "Rekonstruktion" : 13, \
                   "Ergaenzung" : 14, "Sprache" : 15, "UEBERLIEFERUNGSTRAEGER" : 16, "WIEDERAUFNAHME" : 17}

        #Create doc object
        doc = Doc(filename)

        tokens = list()
        IDs = list()
        values_all = dict()

        punct_l= [".", ",", ":", ";", "!", "?"]

        for line in gridfile:

            if not line.strip() and values_all:

                #tokens
                values = dict()
                for id in IDs:
                    for col in columns:
                        if col in values_all:
                            values[col] = values_all[col][int(id)-1]
                        else:
                            values[col] = "_"
                    tok = Token(**values)
                    tokens.append(tok)
                IDs.clear()
                values_all.clear()

                #sentence
                if not "text" in metainfo:
                    metainfo["text"]= ""
                    for tok in tokens:
                        #first token
                        if not metainfo["text"]:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        #token is punctuation
                        elif tok.FORM in punct_l:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        #other token
                        else:
                            metainfo["text"] = metainfo["text"] + " " + tok.FORM
                sentence = Sentence(**metainfo)
                for tok in tokens:
                    sentence.add_token(tok)
                tokens.clear()
                metainfo.clear()
                doc.add_sent(sentence)

            #Category line
            elif line.strip():

                #ID+FORM
                if "tok" in line.strip().split():
                    #sent_id(grid)
                    sent_id = line.strip().split()[0]
                    metainfo["sent_id(grid)"] = sent_id[:-1]

                    sent = line.strip().split()[2:]
                    for x in range(0, len(sent)):
                        IDs.append(str(x+1))
                    values_all["ID"] = IDs
                    values_all["FORM"] = sent


                #other categories
                elif "meta" not in line:
                    cat, line = line.strip().split("\t")
                    line = line.strip().split("]")[:-1]
                    vals_all = dict() #key:ID, value:SUBJ etc
                    vals = list()

                    #Kommentar as sentence attribute if possible
                    if cat in ["Kommentar", "KOMMENTAR"]:
                        cat = "Kommentar"
                        for val in line:
                            val, ids = val.strip().split("[")
                            start, end = ids.split("-")
                            start_nr = int(start)
                            end_nr = int(end)
                            #refering to whole sentence?
                            if start_nr == 1 and end_nr >= len(IDs):
                                metainfo[cat] = val
                            else:
                                for id in range(start_nr, end_nr + 1):
                                    vals_all[str(id)] = val

                    else:
                        for val in line:
                            val, ids = val.strip().split("[")
                            start, end = ids.split("-")
                            start_nr = int(start)
                            end_nr = int(end)
                            for id in range(start_nr, end_nr + 1):
                                vals_all[str(id)] = val

                    for id in IDs:
                        if id in vals_all:
                            vals.append(vals_all[id])
                        else:
                            vals.append("_")
                    values_all[cat] = vals

                    vals_all.clear()

        #If file does not end with empty line
        #save remaining last sentence
        if values_all:

                #tokens
                values = dict()
                for id in IDs:
                    for col in columns:
                        if col in values_all:
                            values[col] = values_all[col][int(id)-1]
                        else:
                            values[col] = "_"
                    tok = Token(**values)
                    tokens.append(tok)
                IDs.clear()
                values_all.clear()

                #sentence
                if not "text" in metainfo:
                    metainfo["text"]= ""
                    for tok in tokens:
                        #first token
                        if not metainfo["text"]:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        #token is punctuation
                        elif tok.FORM in punct_l:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        #other token
                        else:
                            metainfo["text"] = metainfo["text"] + " " + tok.FORM
                sentence = Sentence(**metainfo)
                for tok in tokens:
                    sentence.add_token(tok)
                tokens.clear()
                metainfo.clear()
                doc.add_sent(sentence)

        gridfile.close()

        return doc

############################

class WebAnnoTopFImporter(Importer):

    ###############################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ###############################

    def get_columns(self, file):

        morph = False
        xpos = False
        pos = False
        lemma = False
        chunk = False
        topf = False
        dep = False

        #Skip header
        line = ""
        while not line.strip():
            line = file.__next__()
            if line.strip().startswith("#"):
                if "MorphologicalFeatures" in line:
                    morph = True
                elif "Lemma" in line:
                    lemma = True
                elif "POS|PosValue|coarseValue" in line:
                    xpos = True
                    pos = True
                elif "POS|PosValue" in line:
                    xpos = True
                elif "Chunk" in line:
                    chunk = True
                elif "TopologicalField" in line:
                    topf = True
                elif "Dependency" in line:
                    dep = True
                line = ""
            else:
                break

        colnames = ["TSVID", "CharOffset", "FORM"]
        if morph:
            colnames += ["animacy", "aspect", "case", "definiteness", "degree", "gender",
                         "mood", "negative", "numType", "number", "person", "possessive",
                         "pronType", "reflex", "tense", "transitivity", "FEATS", "verbForm", "voice"]
        if xpos: colnames += ["XPOS"]
        if pos: colnames += ["POS"]
        if lemma: colnames += ["LEMMA"]
        if chunk: colnames += ["CHUNK"]
        if topf: colnames += ["TopF"]
        if dep: colnames += ["DEPREL", "DepFlavor", "HEAD"]
        columns = {colname : i for i, colname in enumerate(colnames)}

        return columns

    ###############################

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

        #Open file
        tsvfile = open(file, mode="r", encoding="utf-8")

        #Get columns
        columns = self.get_columns(tsvfile)
        if not columns:
            print("ERROR: Missing column information for {0}.".format(filename))
            return None

        #Create doc object
        doc = Doc(filename)

        tokens = list()
        metainfo = dict()

        for line in tsvfile:

            #Empty line = end of sentence
            if not line.strip() and tokens:

                #Get sent_id(TSV)
                metainfo["sent_id(TSV)"] = tokens[0].TSVID.split("-")[0]

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
                metainfo[line[0].strip().lower()] = "=".join(line[1:]).strip()

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
            #Get sent_id(TSV)
            metainfo["sent_id(TSV)"] = tokens[0].TSVID.split("-")[0]
            if not "text" in metainfo:
                metainfo["text"] = " ".join([tok.FORM for tok in tokens])
            sentence = Sentence(**metainfo)
            for tok in tokens:
                sentence.add_token(tok)
            tokens.clear()
            metainfo.clear()
            doc.add_sent(sentence)

        tsvfile.close()

        return doc

#############################

class WebAnnoTSVImporter(Importer):

    ###############################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val
        self.columns = ["TSVID", "CharOffset", "FORM", "POS", "LEMMA"]

    ###############################

    def get_columns(self, file):

        colnames = ["TSVID", "CharOffset", "FORM", "XPOS", "LEMMA"]

        #Skip header
        line = ""
        while not line.strip():
            line = file.__next__()
            if line.strip().startswith("#"):
                if "|" in line and not (line.strip().endswith("PosValue") or line.strip().endswith("Lemma|value")):
                    colnames.append(line.split("|")[-1])
                line = ""
            else:
                break

        columns = {colname : i for i, colname in enumerate(colnames)}

        return columns

    ###############################

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

        #Open file
        tsvfile = open(file, mode="r", encoding="utf-8")

        #Get columns
        columns = self.get_columns(tsvfile)
        if not columns:
            print("ERROR: Missing column information for {0}.".format(filename))
            return None

        #Create doc object
        doc = Doc(filename)

        tokens = list()
        metainfo = dict()

        for line in tsvfile:

            #Empty line = end of sentence
            if not line.strip() and tokens:

                #Get sent_id(TSV)
                metainfo["sent_id(TSV)"] = tokens[0].TSVID.split("-")[0]

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
                metainfo[line[0].strip().lower()] = "=".join(line[1:]).strip()

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
            #Get sent_id(TSV)
            metainfo["sent_id(TSV)"] = tokens[0].TSVID.split("-")[0]
            if not "text" in metainfo:
                metainfo["text"] = " ".join([tok.FORM for tok in tokens])
            sentence = Sentence(**metainfo)
            for tok in tokens:
                sentence.add_token(tok)
            tokens.clear()
            metainfo.clear()
            doc.add_sent(sentence)

        tsvfile.close()

        return doc

#############################

class CoraXMLReMImporter(Importer):

    ################################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ################################

    def read_metaheader(self, metaheader):
        """
        Read info from metaheader element into dictionary.
        If info not available, value is NA.
        Input: Metaheader element from xml tree
        Output: Dictionary with meta info
        """
        metainfo = dict()
        metacats = ["text", "abbr_ddd", "abbr_mwb", "topic", "text-type", "genre", "reference", "reference-secondary", "library", "library-shelfmark", \
                    "online", "medium", "extent", "extract", "language", "language-type", "language-region", "language-area", "place", "time", \
                    "notes-manuscript", "date", "text-place", "text-author", "text-language", "text-source", "edition", "notes-transcription", "notes-annotation"]

        for metacat in metacats:
            text = metaheader.find(metacat).text
            if text:
                if text != "-" and text!="_":
                    if "\t" in text:
                        text = text.replace("\t", " ")
                        metainfo[metacat] = text
                    else:
                        metainfo[metacat] = text
                else:
                    metainfo[metacat] = "NA"
            else:
                metainfo[metacat] = "NA"

        return metainfo

    ################################

    def output_metainfo(self, metainfo, metadir):
        """
        Append metainfo for a given file to a csv-file in metadir.
        Input: Dictionary with meta information, target directory
        """
        metacats = ["filename", "text", "abbr_ddd", "abbr_mwb", "topic", "text-type", "genre", "reference", "reference-secondary", \
                    "library", "library-shelfmark", "online", "medium", "extent", "extract", "language", "language-type", "language-region", "language-area", \
                    "place", "time", "notes-manuscript", "date", "text-place", "text-author", "text-language", "text-source", "edition", "notes-transcription", "notes-annotation"]

        metafile = open(os.path.join(metadir, "ReM_meta_information.csv"), mode="a", encoding="utf-8")

        #Write header if
        if metafile.tell() == 0:
            print("\t".join(metacats), file=metafile)

        print("\t".join([metainfo[metacat] for metacat in metacats]), file=metafile)

        metafile.close()

    ################################

    def get_locs(self, root):
        """
        Input: Root (text element)
        Output: Dictionary with tok_dipl IDs (t10_d1, ...) as keys
                and their corresponding loc ID (2a,11, ...) as value.
        """
        #list of all tok_dipl IDs
        tok_dipls = list()
        for tok_dipl in root.findall("./token/tok_dipl"):
            dipl_id = tok_dipl.attrib["id"]
            tok_dipls.append(dipl_id)

        #dictionary with locs
        lines = root.findall("./layoutinfo/line")
        range = list()
        locs = dict()
        for line in lines:
            if tok_dipls:
                try:
                    range_start, range_end = line.attrib["range"].split("..")
                except:
                    #only one tok_dipl for this loc
                    range_end = line.attrib["range"]
                #range = list of dipl_ids with same loc
                for tok_dipl in tok_dipls:
                    if tok_dipl != range_end:
                        range.append(tok_dipl)
                    else:
                        range.append(tok_dipl)
                        break
                loc = line.attrib["loc"]
                for id in range:
                    locs[id] = loc
                    tok_dipls.remove(id)
                range.clear()

        return locs

    ################################

    def get_shifttags(self, root):
        """
        Input: Root (text element)
        Output: Dictionary with tok_anno IDs (t23_m1, ...) as keys
                and their corresponding shifttags ("quote", "paren", "quote, paren" ...) as value.
        """
        #list of all tok_anno IDs
        tok_annos = list()
        for tok_anno in root.findall("./token/tok_anno"):
            anno_id = tok_anno.attrib["id"]
            tok_annos.append(anno_id)

        #dictionary with shifttags
        range = list()
        shifttags = dict()
        for tag in root.findall("./shifttags/"):
            if tok_annos:
                try:
                    range_start, range_end = tag.attrib["range"].split("..")
                except:
                    range_start = tag.attrib["range"]
                    range_end = tag.attrib["range"]
                #range = list of anno_ids with same shifttag
                n = 0
                for tok_anno in tok_annos:
                    if n!= 0:
                        range.append(tok_anno)
                        if tok_anno == range_end:
                            break
                    elif (tok_anno == range_start) & (tok_anno == range_end):
                        range.append(tok_anno)
                        break
                    elif tok_anno == range_start:
                        range.append(tok_anno)
                        n+= 1
                tag_name = tag.tag
                for id in range:
                    if id in shifttags:
                        shifttags[id] = shifttags[id] + ", " + tag_name
                    else:
                        shifttags[id] = tag_name
                range.clear()

        return shifttags

    ################################

    def get_sentences(self, root):
        """
        Input: Root (text element)
        Output: Dictionary with sent_IDs (1, 2, ...) as keys
                and a list of token_IDs ([t11, t12, ...], ...)
                of which the sentence exists as value.
        """
        sentences = dict()
        n= 1 #sent_id
        for token in root.findall("token"):
            tok_id = token.attrib["id"]
            if n in sentences:
                sentences[n].append(tok_id)
            else:
                sentences[n] = [tok_id]

            for tok_anno in token.findall("tok_anno"):
                try:
                    punc= tok_anno.find("punc")
                    if punc.attrib["tag"] in ["DE", "IE", "EE", "QE"]:
                        #end of sentence
                        n+= 1

                    elif punc.attrib["tag"]=="$E":
                        sentences[n-1].append(tok_id)
                        del sentences[n]
                except:
                    pass

        return sentences

    ################################

    def import_file(self, file, metadir):

        path, filename = os.path.split(file)

        #Read xml tree
        tree = ET.parse(file)
        root = tree.getroot()
        metaheader = root.find("header")

        #read metainfo
        metainfo = self.read_metaheader(metaheader)
        metainfo["filename"] = os.path.splitext(filename)[0]
        self.output_metainfo(metainfo, metadir)

        #create doc-object
        doc = Doc(filename)

        #Look up which loc belongs to which tok_dipl
        locs = self.get_locs(root)

        #Look up wich shifttags belong to which tok_anno
        shifttags = self.get_shifttags(root)

        #Get sentences
        sentences = self.get_sentences(root)


        for sentence in sentences:

            sent = Sentence(**{"text" : ""})

            #token
            n = 1
            for token_id in sentences[sentence]:

                kwargs = {}
                columns= ["ID", "LOC", "FORM", "DIPL", "TOKEN", "ANNO_TRANS", "DIPL_TRANS", "ANNO_ASCII", "NORM", "TOKEN_TYPE", "LEMMA", "LEMMA_GEN", "LEMMA_IDMWB", \
                        "POS", "POS_GEN", "INFL", "INFLCLASS", "INFLCLASS_GEN", "PUNC", "TOK_ID", "ANNO_ID", "DIPL_ID", "SHIFTTAG"]
                annos= {"NORM" : "norm", "TOKEN_TYPE" : "token_type", "LEMMA" : "lemma", "LEMMA_GEN" : "lemma_gen", "LEMMA_IDMWB" :"lemma_idmwb", \
                        "POS" : "pos", "POS_GEN" : "pos_gen", "INFL" :"infl", "INFLCLASS" :"inflClass", "INFLCLASS_GEN" :"inflClass_gen", "PUNC" : "punc"}

                #TOKEN-FORM+ID
                token = root.find("./token[@id='{0}']".format(token_id))
                kwargs["TOKEN"] = token.attrib["trans"]
                kwargs["TOK_ID"] = token_id

                #several annos
                if len(token.findall("tok_anno")) > 1:

                    #ID
                    kwargs["ID"] = str(n) + "-" + str(n+len(token.findall("tok_anno"))-1)

                    #DIPL-FORM+TRANS+ID
                    tok_dipls = token.findall("tok_dipl")
                    for tok_dipl in tok_dipls:
                        if "DIPL" in kwargs:
                            kwargs["DIPL"] += " " + tok_dipl.attrib["utf"]
                            kwargs["DIPL_ID"] += "," + tok_dipl.attrib["id"]
                        else:
                            kwargs["DIPL"] = tok_dipl.attrib["utf"]
                            kwargs["DIPL_ID"] = tok_dipl.attrib["id"]
                            kwargs["DIPL_TRANS"] = "_"
                            #LOC
                            kwargs["LOC"] = locs.get(kwargs["DIPL_ID"], "_")

                    #ANNO-FORM+TRANS+ID
                    tok_annos = token.findall("tok_anno")
                    for tok_anno in tok_annos:
                        if "FORM" in kwargs:
                            kwargs["FORM"] += " " + tok_anno.attrib["utf"]
                            kwargs["ANNO_ID"] += "," + tok_anno.attrib["id"]
                        else:
                            kwargs["FORM"] = tok_anno.attrib["utf"]
                            kwargs["ANNO_ID"] = tok_anno.attrib["id"]
                            kwargs["ANNO_TRANS"] = "_"
                            kwargs["ANNO_ASCII"] = "_"

                    #ANNOTATIONS
                    for anno in annos:
                        kwargs[anno] = "_"

                    #SHIFTTAG
                    kwargs["SHIFTTAG"] = "_"

                    tok = Token(**kwargs)
                    sent.add_token(tok)

                    #individual tok_annos
                    i = 0
                    for tok_anno in tok_annos:
                        kwargs = {}
                        kwargs["TOKEN"] = token.attrib["trans"]
                        kwargs["TOK_ID"] = token_id

                        #ID
                        kwargs["ID"] = str(n)

                        #DIPL-FORM+TRANS+ID
                        if len(tok_dipls) > i:
                            kwargs["DIPL"] = tok_dipls[i].attrib["utf"]
                            kwargs["DIPL_TRANS"] = tok_dipls[i].attrib["trans"]
                            kwargs["DIPL_ID"] = tok_dipls[i].attrib["id"]
                            #Reconstruct text
                            if sent.text:
                                sent.text += " " + kwargs["DIPL"]
                            else:
                                sent.text += kwargs["DIPL"]
                            i+= 1
                        else:
                            kwargs["DIPL"] = "_"
                            kwargs["DIPL_TRANS"] = "_"
                            kwargs["DIPL_ID"] = "_"

                        #LOC
                        kwargs["LOC"] = locs.get(kwargs["DIPL_ID"], "_")

                        #ANNO-FORM+TRANS+ASCII+ID
                        kwargs["FORM"] = tok_anno.attrib["utf"]
                        kwargs["ANNO_TRANS"] = tok_anno.attrib["trans"]
                        kwargs["ANNO_ASCII"] = tok_anno.attrib["ascii"]
                        kwargs["ANNO_ID"] = tok_anno.attrib["id"]

                        #ANNOTATIONS
                        for anno in annos:
                            try:
                                kwargs[anno] = tok_anno.find(annos[anno]).attrib["tag"]
                                if kwargs[anno]=="--":
                                    kwargs[anno] = "_"
                            except:
                                kwargs[anno] = "_"

                        #SHIFTTAG
                        kwargs["SHIFTTAG"] = shifttags.get(kwargs["ANNO_ID"], "_")

                        #more dipls than annos: put rest of the dipls to the last anno
                        if len(tok_dipls) > len(tok_annos) and len(tok_annos) == i:
                            for x in range(i, len(tok_dipls)):
                                kwargs["DIPL"] += " " + tok_dipls[x].attrib["utf"]
                                kwargs["DIPL_TRANS"] += " " + tok_dipls[x].attrib["trans"]
                                kwargs["DIPL_ID"] += " " + tok_dipls[x].attrib["id"]
                                #Reconstruct text
                                sent.text += " " + kwargs["DIPL"]

                        tok = Token(**kwargs)
                        sent.add_token(tok)
                        n += 1

                #one anno
                else:

                    #ID
                    kwargs["ID"] = str(n)

                    #DIPL-FORM+TRANS+ID
                    tok_dipls = token.findall("tok_dipl")
                    for tok_dipl in tok_dipls:
                        if "DIPL" in kwargs:
                            kwargs["DIPL"] += " " + tok_dipl.attrib["utf"]
                            kwargs["DIPL_TRANS"] += " " + tok_dipl.attrib["trans"]
                            kwargs["DIPL_ID"] += "," + tok_dipl.attrib["id"]
                        else:
                            kwargs["DIPL"] = tok_dipl.attrib["utf"]
                            kwargs["DIPL_TRANS"] = tok_dipl.attrib["trans"]
                            kwargs["DIPL_ID"] = tok_dipl.attrib["id"]
                            #LOC
                            kwargs["LOC"] = locs.get(kwargs["DIPL_ID"], "_")

                    #ANNO-FORM+TRANS+ASCII+ID
                    tok_anno = token.find("tok_anno")
                    kwargs["FORM"] = tok_anno.attrib["utf"]
                    kwargs["ANNO_TRANS"] = tok_anno.attrib["trans"]
                    kwargs["ANNO_ASCII"] = tok_anno.attrib["ascii"]
                    kwargs["ANNO_ID"] = tok_anno.attrib["id"]

                    #ANNOTATIONS
                    for anno in annos:
                        try:
                            kwargs[anno] = tok_anno.find(annos[anno]).attrib["tag"]
                            if kwargs[anno]=="--":
                                kwargs[anno] = "_"
                        except:
                            kwargs[anno] = "_"

                    #SHIFTTAG
                    kwargs["SHIFTTAG"] = shifttags.get(kwargs["ANNO_ID"], "_")

                    #Reconstruct text
                    if sent.text:
                        sent.text += " " + kwargs["DIPL"]
                    else:
                        sent.text += kwargs["DIPL"]

                    tok = Token(**kwargs)
                    sent.add_token(tok)
                    n += 1

            doc.add_sent(sent)

        return doc

############################

class TUEBADSConllImporter(Importer):


    ###############################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ###############################

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

        #Open file
        conllfile = open(file, mode="r", encoding="utf-8")

        #Get columns
        columns = {"ID" : 0, "FORM" : 1, "XPOS" : 2, "POS:HD" : 3, "SYNTAX" : 4}

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

class CoraXMLAnselmImporter(Importer):

    ################################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ################################

    def read_metaheader(self, metaheader):
        """
        Read info from metaheader element into dictionary.
        If info not available, value is NA.
        Input: Metaheader element from xml tree
        Output: Dictionary with meta info
        """
        metainfo = dict()
        metatext = metaheader.text.split("\n")
        for metaline in metatext:
            metacat, info = metaline.strip().split(":", 1)
            if metacat not in ["Bemerkungen", "Kommentar"]:
                if info:
                    if "\t" in info.strip():
                        info = info.replace("\t", " ")
                    metainfo[metacat] = info.strip()
                else:
                    metainfo[metacat] = "NA"

        return metainfo

    ################################

    def output_metainfo(self, metainfo, metadir):
        """
        Append metainfo for a given file to a csv-file in metadir.
        Input: Dictionary with meta information, target directory
        """
        metacats = ["filename", "Sigle", "Aufbewahrungsort", "Signatur", "Druck", "Handschrift_Druck", "Prosa_Vers", \
                    "Datum", "Sprache", "Sprachtyp", "Sprachraum", "Token", "Kenn-Name", "URL_Faksimile"]

        metafile = open(os.path.join(metadir, "Anselm_meta_information.csv"), mode="a", encoding="utf-8")

        #Write header if
        if metafile.tell() == 0:
            print("\t".join(metacats), file=metafile)

        print("\t".join([metainfo[metacat] for metacat in metacats]), file=metafile)

        metafile.close()

    ################################

    def get_shifttags(self, root):
        """
        Input: Root (text element)
        Output: Dictionary with tok-IDs (t1, t2, ...) as keys
                and their corresponding shifttags ("fm", ...) as value.
        """
        #list of all tok-IDs
        tok_ids = list()
        for tok in root.findall("./token"):
            tok_id = tok.attrib["id"]
            tok_ids.append(tok_id)

        #dictionary with shifttags
        range = list()
        shifttags = dict()
        for tag in root.findall("./shifttags/"):
            if tok_ids:
                try:
                    range_start, range_end = tag.attrib["range"].split("..")
                except:
                    range_start = tag.attrib["range"]
                    range_end = tag.attrib["range"]
                #range = list of tok_ids with same shifttag
                n = 0
                for tok_id in tok_ids:
                    if n!= 0:
                        range.append(tok_id)
                        if tok_id == range_end:
                            break
                    elif (tok_id == range_start) & (tok_id == range_end):
                        range.append(tok_id)
                        break
                    elif tok_id == range_start:
                        range.append(tok_id)
                        n+= 1
                tag_name = tag.tag
                for id in range:
                    if id in shifttags:
                        shifttags[id] = shifttags[id] + ", " + tag_name
                    else:
                        shifttags[id] = tag_name
                range.clear()

        return shifttags

    ################################

    def get_sentences(self, root):
        """
        Input: Root (text element)
        Output: Dictionary with sent_IDs (1, 2, ...) as keys
                and a list of token_IDs ([t11, t12, ...], ...)
                of which the sentence exists as value.
        """

        sentences = dict()
        n= 1 #sent_id
        for token in root.findall("token"):
            tok_id = token.attrib["id"]
            if n in sentences:
                sentences[n].append(tok_id)
            else:
                sentences[n] = [tok_id]

            tok_annos = token.findall("tok_anno")
            if tok_annos:
                for tok_anno in tok_annos:
                    pos = tok_anno.find("pos")
                    if pos.attrib["tag"] == "$.":
                        n += 1

        return sentences

    ################################

    def import_file(self, file, metadir):

        path, filename = os.path.split(file)

        #Read xml tree
        tree = ET.parse(file)
        root = tree.getroot()
        metaheader = root.find("header")

        #read metainfo
        metainfo = self.read_metaheader(metaheader)
        metainfo["filename"] = os.path.splitext(filename)[0]
        self.output_metainfo(metainfo, metadir)

        #create doc-object
        doc = Doc(filename)

        #Look up wich shifttags belong to which tok_anno
        shifttags = self.get_shifttags(root)

        #Get sentences
        sentences = self.get_sentences(root)

        for sentence in sentences:

            sent = Sentence(**{"text" : ""})

            #token
            n = 1
            for token_id in sentences[sentence]:

                kwargs = {}
                columns= ["ID", "FORM", "DIPL", "TOKEN", "ANNO_TRANS", "DIPL_TRANS", "ANNO_ASCII", "NORM", "NORM_BROAD", "NORM_TYPE", \
                          "LEMMA", "POS", "MORPH", "TOKEN_TYPE", "TOK_ID", "ANNO_ID", "DIPL_ID", "SHIFTTAG"]
                annos= {"NORM" : "norm", "NORM_BROAD" : "norm_broad", "NORM_TYPE" : "norm_type", "LEMMA" : "lemma", "POS" : "pos", \
                        "MORPH" : "morph", "TOKEN_TYPE" : "token_type"}

                #TOKEN-FORM+ID
                token = root.find("./token[@id='{0}']".format(token_id))
                kwargs["TOKEN"] = token.attrib["trans"]
                kwargs["TOK_ID"] = token_id

                #SHIFTTAG
                kwargs["SHIFTTAG"] = shifttags.get(token_id, "_")

                #several annos
                if len(token.findall("tok_anno")) > 1:

                    #ID
                    kwargs["ID"] = str(n) + "-" + str(n+len(token.findall("tok_anno"))-1)

                    #DIPL-FORM+TRANS+ID
                    tok_dipls = token.findall("tok_dipl")
                    for tok_dipl in tok_dipls:
                        if "DIPL" in kwargs:
                            kwargs["DIPL"] += " " + tok_dipl.attrib["utf"]
                            kwargs["DIPL_ID"] += "," + tok_dipl.attrib["id"]
                        else:
                            kwargs["DIPL"] = tok_dipl.attrib["utf"]
                            kwargs["DIPL_ID"] = tok_dipl.attrib["id"]
                            kwargs["DIPL_TRANS"] = "_"

                    #ANNO-FORM+TRANS+ID
                    tok_annos = token.findall("tok_anno")
                    for tok_anno in tok_annos:
                        if "FORM" in kwargs:
                            kwargs["FORM"] += " " + tok_anno.attrib["utf"]
                            kwargs["ANNO_ID"] += "," + tok_anno.attrib["id"]
                        else:
                            kwargs["FORM"] = tok_anno.attrib["utf"]
                            kwargs["ANNO_ID"] = tok_anno.attrib["id"]
                            kwargs["ANNO_TRANS"] = "_"
                            kwargs["ANNO_ASCII"] = "_"

                    #ANNOTATIONS
                    for anno in annos:
                        kwargs[anno] = "_"

                    tok = Token(**kwargs)
                    sent.add_token(tok)

                    #individual tok_annos
                    i = 0
                    for tok_anno in tok_annos:
                        kwargs = {}
                        kwargs["TOKEN"] = token.attrib["trans"]
                        kwargs["TOK_ID"] = token_id

                        #SHIFTTAG
                        kwargs["SHIFTTAG"] = shifttags.get(token_id, "_")

                        #ID
                        kwargs["ID"] = str(n)

                        #DIPL-FORM+TRANS+ID
                        if len(tok_dipls) > i:
                            kwargs["DIPL"] = tok_dipls[i].attrib["utf"]
                            kwargs["DIPL_TRANS"] = tok_dipls[i].attrib["trans"]
                            kwargs["DIPL_ID"] = tok_dipls[i].attrib["id"]
                            #Reconstruct text
                            if sent.text:
                                sent.text += " " + kwargs["DIPL"]
                            else:
                                sent.text += kwargs["DIPL"]
                            i+= 1
                        else:
                            kwargs["DIPL"] = "_"
                            kwargs["DIPL_TRANS"] = "_"
                            kwargs["DIPL_ID"] = "_"

                        #ANNO-FORM+TRANS+ASCII+ID
                        kwargs["FORM"] = tok_anno.attrib["utf"]
                        kwargs["ANNO_TRANS"] = tok_anno.attrib["trans"]
                        kwargs["ANNO_ASCII"] = tok_anno.attrib["ascii"]
                        kwargs["ANNO_ID"] = tok_anno.attrib["id"]

                        #ANNOTATIONS
                        for anno in annos:
                            try:
                                kwargs[anno] = tok_anno.find(annos[anno]).attrib["tag"]
                                if kwargs[anno]=="--":
                                    kwargs[anno] = "_"
                            except:
                                kwargs[anno] = "_"

                        #more dipls than annos: put rest of the dipls to the last anno
                        if len(tok_dipls) > len(tok_annos) and len(tok_annos) == i:
                            for x in range(i, len(tok_dipls)):
                                kwargs["DIPL"] += " " + tok_dipls[x].attrib["utf"]
                                kwargs["DIPL_TRANS"] += " " + tok_dipls[x].attrib["trans"]
                                kwargs["DIPL_ID"] += " " + tok_dipls[x].attrib["id"]
                                #Reconstruct text
                                sent.text += " " + kwargs["DIPL"]

                        tok = Token(**kwargs)
                        sent.add_token(tok)
                        n += 1

                #one or no anno
                else:

                    #ID
                    kwargs["ID"] = str(n)

                    #DIPL-FORM+TRANS+ID
                    tok_dipls = token.findall("tok_dipl")
                    for tok_dipl in tok_dipls:
                        if "DIPL" in kwargs:
                            kwargs["DIPL"] += " " + tok_dipl.attrib["utf"]
                            kwargs["DIPL_TRANS"] += " " + tok_dipl.attrib["trans"]
                            kwargs["DIPL_ID"] += "," + tok_dipl.attrib["id"]
                        else:
                            kwargs["DIPL"] = tok_dipl.attrib["utf"]
                            kwargs["DIPL_TRANS"] = tok_dipl.attrib["trans"]
                            kwargs["DIPL_ID"] = tok_dipl.attrib["id"]

                    #ANNO-FORM+TRANS+ASCII+ID
                    try:
                        tok_anno = token.find("tok_anno")
                        kwargs["FORM"] = tok_anno.attrib["utf"]
                        kwargs["ANNO_TRANS"] = tok_anno.attrib["trans"]
                        kwargs["ANNO_ASCII"] = tok_anno.attrib["ascii"]
                        kwargs["ANNO_ID"] = tok_anno.attrib["id"]
                    except:
                        kwargs["FORM"] = "_"
                        kwargs["ANNO_TRANS"] = "_"
                        kwargs["ANNO_ASCII"] = "_"
                        kwargs["ANNO_ID"] = "_"

                    #ANNOTATIONS
                    for anno in annos:
                        try:
                            kwargs[anno] = tok_anno.find(annos[anno]).attrib["tag"]
                            if kwargs[anno]=="--":
                                kwargs[anno] = "_"
                        except:
                            kwargs[anno] = "_"

                    #Reconstruct text
                    if sent.text:
                        sent.text += " " + kwargs["DIPL"]
                    else:
                        sent.text += kwargs["DIPL"]

                    tok = Token(**kwargs)
                    sent.add_token(tok)
                    n += 1

            doc.add_sent(sent)

        return doc

############################

class CoraXMLReFBoImporter(Importer):

    ################################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ################################

    def read_metaheader(self, root):
        """
        Read info from metaheader element into dictionary.
        If info not available, value is NA.
        Input: Metaheader element from xml tree
        Output: Dictionary with meta info
        """
        metainfo = dict()
        coraheader = root.find("cora-header")
        name = coraheader.attrib["name"]
        if "\t" in name:
            name = name.replace("\t", " ")
        metainfo["name"] = name

        metaheader = root.find("header")
        metatext = metaheader.text.split("\n")
        for metaline in metatext:
            metacat, info = metaline.strip().split(":", 1)
            if info.strip() != "-":
                if "\t" in info.strip():
                    info = info.replace("\t", " ")
                metainfo[metacat] = info.strip()
            else:
                metainfo[metacat] = "NA"

        return metainfo

    ################################

    def output_metainfo(self, metainfo, metadir):
        """
        Append metainfo for a given file to a csv-file in metadir.
        Input: Dictionary with meta information, target directory
        """
        metacats = ["filename", "language-area", "language-region", "language-type", "genre", "medium", "time", "reference", "corpus-sigle", \
                    "text", "text-author", "text-type", "assignment_quality", "hoffmann_wetter_nr", "library", "library-shelfmark", "date", \
                    "text-place", "printer", "edition", "literature", "size", "language", "notes-transcription", "abbr_ddd", "extent", "extent-size"]

        metafile = open(os.path.join(metadir, "ReF.BO_meta_information.csv"), mode="a", encoding="utf-8")

        #Write header if
        if metafile.tell() == 0:
            print("\t".join(metacats), file=metafile)

        print("\t".join([metainfo[metacat] for metacat in metacats]), file=metafile)

        metafile.close()

    ################################

    def get_shifttags(self, root):
        """
        Input: Root (text element)
        Output: Dictionary with tok-IDs (t1, t2, ...) as keys
                and their corresponding shifttags ("lat", ...) as value.
        """
        #list of all tok-IDs
        tok_ids = list()
        for tok in root.findall("./token"):
            tok_id = tok.attrib["id"]
            tok_ids.append(tok_id)

        #dictionary with shifttags
        range = list()
        shifttags = dict()
        for tag in root.findall("./shifttags/"):
            if tok_ids:
                try:
                    range_start, range_end = tag.attrib["range"].split("..")
                except:
                    range_start = tag.attrib["range"]
                    range_end = tag.attrib["range"]
                #range = list of tok_ids with same shifttag
                n = 0
                for tok_id in tok_ids:
                    if n!= 0:
                        range.append(tok_id)
                        if tok_id == range_end:
                            break
                    elif (tok_id == range_start) & (tok_id == range_end):
                        range.append(tok_id)
                        break
                    elif tok_id == range_start:
                        range.append(tok_id)
                        n+= 1
                tag_name = tag.tag
                for id in range:
                    if id in shifttags:
                        shifttags[id] = shifttags[id] + ", " + tag_name
                    else:
                        shifttags[id] = tag_name
                range.clear()

        return shifttags

    ################################

    def get_sentences(self, root):
        """
        Input: Root (text element)
        Output: Dictionary with sent_IDs (1, 2, ...) as keys
                and a list of token_IDs ([t11, t12, ...], ...)
                of which the sentence exists as value.
        """

        sentences = dict()
        n= 1 #sent_id
        for token in root.findall("token"):
            tok_id = token.attrib["id"]
            if n in sentences:
                sentences[n].append(tok_id)
            else:
                sentences[n] = [tok_id]

            tok_annos = token.findall("tok_anno")
            if tok_annos:
                for tok_anno in tok_annos:
                    try:
                        bound = tok_anno.find("boundary")
                        if "(.)" in bound.attrib["tag"]:
                            n += 1
                    except:
                        try:
                            punc = tok_anno.find("punc")
                            if "(.)" in punc.attrib["tag"]:
                                n += 1
                        except:
                            continue

        if n < 10:
            sentences = dict()
            n= 1 #sent_id
            for token in root.findall("token"):
                tok_id = token.attrib["id"]
                if n in sentences:
                    sentences[n].append(tok_id)
                else:
                    sentences[n] = [tok_id]

                tok_annos = token.findall("tok_anno")
                if tok_annos:
                    for tok_anno in tok_annos:
                        pos = tok_anno.find("pos")
                        if pos != None and pos.attrib["tag"] == "$_":
                            n += 1

        return sentences

    ################################

    def import_file(self, file, metadir):

        path, filename = os.path.split(file)

        #Read xml tree
        tree = ET.parse(file)
        root = tree.getroot()

        #read metainfo
        metainfo = self.read_metaheader(root)
        metainfo["filename"] = os.path.splitext(filename)[0]
        self.output_metainfo(metainfo, metadir)

        #create doc-object
        doc = Doc(filename)

        #Look up wich shifttags belong to which tok_anno
        shifttags = self.get_shifttags(root)

        #Get sentences
        sentences = self.get_sentences(root)

        for sentence in sentences:

            sent = Sentence(**{"text" : ""})

            #token
            n = 1
            for token_id in sentences[sentence]:

                kwargs = {}
                columns= ["ID", "FORM", "DIPL", "TOKEN", "ANNO_TRANS", "DIPL_TRANS", "ANNO_ASCII", "POS", "LEMMA", "POS_LEMMA", "LEMMA_URL", "LEMMA_ID", \
                         "MORPH", "ANNO_TYPE", "TOKEN_TYPE", "LEMMA_VERIFIED", "BOUNDARY", "PUNC", "TOK_ID", "ANNO_ID", "DIPL_ID", "SHIFTTAG"]
                annos= {"POS" : "pos", "POS_LEMMA" : "posLemma", "LEMMA_URL" : "lemmaURL", "LEMMA_ID" : "lemmaId", "LEMMA" : "lemma", \
                        "MORPH" : "morph", "ANNO_TYPE" : "annoType", "TOKEN_TYPE" : "token_type", "CORA_FLAG" : "cora-flag", "BOUNDARY" : "boundary", "PUNC" : "punc"}

                #TOKEN-FORM+ID
                token = root.find("./token[@id='{0}']".format(token_id))
                kwargs["TOKEN"] = token.attrib["trans"]
                kwargs["TOK_ID"] = token_id

                #SHIFTTAG
                kwargs["SHIFTTAG"] = shifttags.get(token_id, "_")

                #several annos
                if len(token.findall("tok_anno")) > 1:

                    #ID
                    kwargs["ID"] = str(n) + "-" + str(n+len(token.findall("tok_anno"))-1)

                    #DIPL-FORM+TRANS+ID
                    tok_dipls = token.findall("tok_dipl")
                    for tok_dipl in tok_dipls:
                        if "DIPL" in kwargs:
                            kwargs["DIPL"] += " " + tok_dipl.attrib["utf"]
                            kwargs["DIPL_ID"] += "," + tok_dipl.attrib["id"]
                        else:
                            kwargs["DIPL"] = tok_dipl.attrib["utf"]
                            kwargs["DIPL_ID"] = tok_dipl.attrib["id"]
                            kwargs["DIPL_TRANS"] = "_"

                    #ANNO-FORM+TRANS+ID
                    tok_annos = token.findall("tok_anno")
                    for tok_anno in tok_annos:
                        if "FORM" in kwargs:
                            kwargs["FORM"] += " " + tok_anno.attrib["utf"]
                            kwargs["ANNO_ID"] += "," + tok_anno.attrib["id"]
                        else:
                            kwargs["FORM"] = tok_anno.attrib["utf"]
                            kwargs["ANNO_ID"] = tok_anno.attrib["id"]
                            kwargs["ANNO_TRANS"] = "_"
                            kwargs["ANNO_ASCII"] = "_"

                    #ANNOTATIONS
                    for anno in annos:
                        kwargs[anno] = "_"

                    tok = Token(**kwargs)
                    sent.add_token(tok)

                    #individual tok_annos
                    i = 0
                    for tok_anno in tok_annos:
                        kwargs = {}
                        kwargs["TOKEN"] = token.attrib["trans"]
                        kwargs["TOK_ID"] = token_id

                        #SHIFTTAG
                        kwargs["SHIFTTAG"] = shifttags.get(token_id, "_")

                        #ID
                        kwargs["ID"] = str(n)

                        #DIPL-FORM+TRANS+ID
                        if len(tok_dipls) > i:
                            kwargs["DIPL"] = tok_dipls[i].attrib["utf"]
                            kwargs["DIPL_TRANS"] = tok_dipls[i].attrib["trans"]
                            kwargs["DIPL_ID"] = tok_dipls[i].attrib["id"]
                            #Reconstruct text
                            if sent.text:
                                sent.text += " " + kwargs["DIPL"]
                            else:
                                sent.text += kwargs["DIPL"]
                            i+= 1
                        else:
                            kwargs["DIPL"] = "_"
                            kwargs["DIPL_TRANS"] = "_"
                            kwargs["DIPL_ID"] = "_"

                        #ANNO-FORM+TRANS+ASCII+ID
                        kwargs["FORM"] = tok_anno.attrib["utf"]
                        kwargs["ANNO_TRANS"] = tok_anno.attrib["trans"]
                        kwargs["ANNO_ASCII"] = tok_anno.attrib["ascii"]
                        kwargs["ANNO_ID"] = tok_anno.attrib["id"]

                        #ANNOTATIONS
                        for anno in annos:
                            if anno == "CORA_FLAG":
                                try:
                                    coraflags = tok_anno.findall(annos[anno])
                                    if coraflags:
                                        for coraflag in coraflags:
                                            if coraflag.attrib["name"] == "lemma verified":
                                                kwargs["LEMMA_VERIFIED"] = "y"
                                            else:
                                                kwargs["LEMMA_VERIFIED"] = "n"
                                    else:
                                        kwargs["LEMMA_VERIFIED"] = "n"
                                except:
                                    kwargs["LEMMA_VERIFIED"] = "_"
                            else:
                                try:
                                    kwargs[anno] = tok_anno.find(annos[anno]).attrib["tag"]
                                    if anno == "LEMMA_URL":
                                        kwargs[anno] = kwargs[anno].split("'")[1]
                                    elif anno == "LEMMA_ID":
                                        kwargs[anno] = kwargs[anno].replace("[", "").replace("]", "")
                                    elif anno == "LEMMA":
                                        for lem_id in ["[GD00002]", "[GD01616]"]:
                                            if lem_id in kwargs[anno]:
                                                kwargs[anno] = kwargs[anno].replace(lem_id, "")
                                                kwargs["LEMMA_ID"] = lem_id.replace("[", "").replace("]", "")
                                    elif kwargs[anno]=="--":
                                        kwargs[anno] = "_"
                                except:
                                    kwargs[anno] = "_"

                        #more dipls than annos: put rest of the dipls to the last anno
                        if len(tok_dipls) > len(tok_annos) and len(tok_annos) == i:
                            for x in range(i, len(tok_dipls)):
                                kwargs["DIPL"] += " " + tok_dipls[x].attrib["utf"]
                                kwargs["DIPL_TRANS"] += " " + tok_dipls[x].attrib["trans"]
                                kwargs["DIPL_ID"] += " " + tok_dipls[x].attrib["id"]
                                #Reconstruct text
                                sent.text += " " + kwargs["DIPL"]

                        tok = Token(**kwargs)
                        sent.add_token(tok)
                        n += 1

                #one or no anno
                else:

                    #ID
                    kwargs["ID"] = str(n)

                    #DIPL-FORM+TRANS+ID
                    tok_dipls = token.findall("tok_dipl")
                    for tok_dipl in tok_dipls:
                        if "DIPL" in kwargs:
                            kwargs["DIPL"] += " " + tok_dipl.attrib["utf"]
                            kwargs["DIPL_TRANS"] += " " + tok_dipl.attrib["trans"]
                            kwargs["DIPL_ID"] += "," + tok_dipl.attrib["id"]
                        else:
                            kwargs["DIPL"] = tok_dipl.attrib["utf"]
                            kwargs["DIPL_TRANS"] = tok_dipl.attrib["trans"]
                            kwargs["DIPL_ID"] = tok_dipl.attrib["id"]

                    #ANNO-FORM+TRANS+ASCII+ID
                    try:
                        tok_anno = token.find("tok_anno")
                        kwargs["FORM"] = tok_anno.attrib["utf"]
                        kwargs["ANNO_TRANS"] = tok_anno.attrib["trans"]
                        kwargs["ANNO_ASCII"] = tok_anno.attrib["ascii"]
                        kwargs["ANNO_ID"] = tok_anno.attrib["id"]
                    except:
                        kwargs["FORM"] = "_"
                        kwargs["ANNO_TRANS"] = "_"
                        kwargs["ANNO_ASCII"] = "_"
                        kwargs["ANNO_ID"] = "_"

                    #ANNOTATIONS
                    for anno in annos:
                        if anno == "CORA_FLAG":
                            try:
                                coraflags = tok_anno.findall(annos[anno])
                                if coraflags:
                                    for coraflag in coraflags:
                                        if coraflag.attrib["name"] == "lemma verified":
                                            kwargs["LEMMA_VERIFIED"] = "y"
                                        else:
                                            kwargs["LEMMA_VERIFIED"] = "n"
                                else:
                                    kwargs["LEMMA_VERIFIED"] = "n"
                            except:
                                kwargs["LEMMA_VERIFIED"] = "_"
                        else:
                            try:
                                kwargs[anno] = tok_anno.find(annos[anno]).attrib["tag"]
                                if anno == "LEMMA_URL":
                                    kwargs[anno] = kwargs[anno].split("'")[1]
                                elif anno == "LEMMA_ID":
                                    kwargs[anno] = kwargs[anno].replace("[", "").replace("]", "")
                                elif anno == "LEMMA":
                                    for lem_id in ["[GD00002]", "[GD01616]"]:
                                        if lem_id in kwargs[anno]:
                                            kwargs[anno] = kwargs[anno].replace(lem_id, "")
                                            kwargs["LEMMA_ID"] = lem_id.replace("[", "").replace("]", "")
                                elif kwargs[anno]=="--":
                                    kwargs[anno] = "_"
                            except:
                                kwargs[anno] = "_"
                    #Reconstruct text
                    if sent.text:
                        sent.text += " " + kwargs["DIPL"]
                    else:
                        sent.text += kwargs["DIPL"]

                    tok = Token(**kwargs)
                    sent.add_token(tok)
                    n += 1

            doc.add_sent(sent)

        return doc

###########################

class TextImporter(Importer):

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    #######################

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

        #Open file
        textfile = open(file, mode="r", encoding="utf-8")

        #Create doc object
        doc = Doc(filename)

        tokens = []
        for line in textfile:
            if line.strip():
                tok = Token(**{"FORM" : line.strip()})
                tokens.append(tok)
            else:
                if tokens:
                    text = " ".join([tok.FORM for tok in tokens])
                    sentence = Sentence(**{"text" : text})
                    for tok in tokens:
                        sentence.add_token(tok)
                    tokens.clear()
                    doc.add_sent(sentence)

        if tokens:
            text = " ".join([tok.FORM for tok in tokens])
            sentence = Sentence(**{"text" : text})
            for tok in tokens:
                sentence.add_token(tok)
            tokens.clear()
            doc.add_sent(sentence)

        textfile.close()

        return doc

#####################################

class TigerXMLImporter(Importer):

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    #######################

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

        #Read xml tree
        tree = ET.parse(file)
        root = tree.getroot()

        doc = Doc(filename)

        for s_elem in root:
            #Get graph element
            graph = s_elem.find("graph")
            rootID = graph.attrib["root"]
            discontinuous = graph.attrib.get("discontinuous", False)
            if discontinuous: discontinuous = True

            #Get terminals and nonterminals
            terminals = graph.find("terminals")
            nonterminals = graph.find("nonterminals")

            tokens = []

            for terminal in sorted(terminals, key=lambda t : int(t.attrib["id"].split("_")[-1])):

                #Get annotations
                pos = terminal.attrib["pos"]
                if pos == "--": pos = "_"
                lemma = terminal.attrib["lemma"]
                if lemma == "--": lemma = "_"
                feats = ""
                for feat in ("number", "degree", "case", "gender", "person", "mood", "tense"):
                    if terminal.attrib[feat] != "--":
                        if feats:
                            feats += "|"+feat+"="+terminal.attrib[feat]
                        else:
                            feats = feat+"="+terminal.attrib[feat]
                if not feats: feats = "_"

                #Create token
                token = Token(**{"FORM" : terminal.attrib["word"],
                                 "LEMMA" : lemma, "XPOS" : pos,
                                 "FEATS" : feats,
                                 "TigerID" : terminal.attrib["id"]})
                tokens.append(token)

            #Create sentence
            sentence = Sentence(tokens, **{"sent_id(Tiger)" : s_elem.attrib["id"]})

            #If there are no non-terminals
            if not len(nonterminals):
                tree = None

            #Otherwise read syntax tree
            else:
                root_node = nonterminals.find("nt[@id='"+rootID+"']")
                tree = Tree(rootID, root_node.attrib["cat"], "--")

                ###########################

                def read_tree(node, tree):
                    for edge in node.findall("edge"):
                        edgeID = edge.attrib["idref"]

                        #Non-terminal
                        if len(edgeID.split("_")[1]) == 3 and int(edgeID.split("_")[1][0]) >= 5:
                            nonterminal_node = nonterminals.find("nt[@id='"+edgeID+"']")
                            nonterminal_child = Tree(edgeID, nonterminal_node.attrib["cat"], edge.attrib["label"])
                            read_tree(nonterminal_node, nonterminal_child)
                            tree.add_child(nonterminal_child)

                        #Terminal
                        else:
                            terminal_child = Tree(edgeID, "Tok", edge.attrib["label"],
                                                **{"token" : [tok for tok in sentence.tokens if tok.TigerID == edgeID][0]})
                            tree.add_child(terminal_child)

                ############################

                read_tree(root_node, tree)

            sentence.tree = tree
            sentence.discontinuous_tree = discontinuous

            if not "text" in sentence.__dict__:
                sentence.text = " ".join([tok.FORM for tok in sentence.tokens])
            doc.add_sent(sentence)

        return doc

###################################

class XMLKaJuKImporter(Importer):

    namespaces = {"default" : "http://www.tei-c.org/ns/1.0"}

    ################################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ################################

    def read_metadocs(self, root):
        """
        Read info from meta document into dictionary.
        Currently included are:
        - filename, file_id
        - style
        - author, editor
        - title
        - tokens
        - publisher, place, year
        - series
        - language
        If info not available, value is NA.
        Input: Root from meta document
        Output: Dictionary with meta info
        """
        metainfo = dict()
        header = root.find("./default:teiHeader", namespaces=self.namespaces)

        # style
        try:
            metainfo["style"] = header.attrib["style"]
        except:
            metainfo["style"] = "NA"

        # author
        try:
            authornames = ""
            authors = header.findall("./default:fileDesc/default:titleStmt/default:author", namespaces=self.namespaces)
            for author in authors:
                if authornames: authornames += ", "
                try:
                    forename = author.find("./default:persName/default:forename", namespaces=self.namespaces)
                except:
                    forename = author.find("./default:forename", namespaces=self.namespaces)
                if forename.text != "NA": authornames += forename.text
                try:
                    surname = author.find("./default:persName/default:surname", namespaces=self.namespaces)
                except:
                    surname = author.find("./default:surname", namespaces=self.namespaces)
                if surname != "NA": authornames += " " + surname.text
            metainfo["author"] = authornames.strip()
        except:
            metainfo["author"] = authornames.strip()
        if not metainfo["author"]: metainfo["author"] = "NA"

        # editor
        try:
            editornames = ""
            editors = header.findall("./default:fileDesc/default:titleStmt/default:editor", namespaces=self.namespaces)
            for editor in editors:
                if editornames: editornames += ", "
                forename = editor.find("./default:persName/default:forename", namespaces=self.namespaces)
                if forename == None: forename = editor.find("./default:forename", namespaces=self.namespaces)
                if forename.text != "NA": editornames += forename.text
                surname = editor.find("./default:persName/default:surname", namespaces=self.namespaces)
                if surname == None: surname = editor.find("./default:surname", namespaces=self.namespaces)
                if surname != "NA": editornames += " " + surname.text
            metainfo["editor"] = editornames.strip()
        except:
            metainfo["editor"] = editornames.strip()
        if not metainfo["editor"]: metainfo["editor"] = "NA"

        # title
        try:
            title = header.find("./default:fileDesc/default:titleStmt/default:title", namespaces=self.namespaces)
            title_list = title.text.split()
            metainfo["title"] = " ".join(title_list)
        except:
            metainfo["title"] = "NA"

        # tokens
        try:
            metainfo["tokens"] = header.find("./default:fileDesc/default:extent[@type='Tokens']", namespaces=self.namespaces).text.strip()
        except:
            metainfo["tokens"] = "NA"

        # publisher
        try:
            metainfo["publisher"] = header.find("./default:fileDesc/default:publicationStmt/default:publisher", namespaces=self.namespaces).text.strip()
        except:
            metainfo["publisher"] = "NA"

        # place
        try:
            metainfo["place"] = header.find("./default:fileDesc/default:publicationStmt/default:pubPlace", namespaces=self.namespaces).text.strip()
        except:
            metainfo["place"] = "NA"

        # year
        try:
            metainfo["year"] = header.find("./default:fileDesc/default:publicationStmt/default:date", namespaces=self.namespaces).text.strip()
        except:
            metainfo["year"] = "NA"

        # series
        try:
            series = ""
            series_title = header.find("./default:fileDesc/default:seriesStmt/default:title", namespaces=self.namespaces).text.strip()
            series_vol = header.find("./default:fileDesc/default:seriesStmt/default:biblScope[@unit='vol']", namespaces=self.namespaces).text.strip()
            if series_title != "NA":
                title_list = series_title.split()
                series += " ".join(title_list)
            if series_vol != "NA": series += " (vol. " + series_vol + ")"
            metainfo["series"] = series.strip()
        except:
            metainfo["series"] = "NA"
        if not metainfo["series"]: metainfo["series"] = "NA"

        # language
        try:
            langElem = header.find("./default:profileDesc/default:langUsage/default:language", namespaces=self.namespaces)
            if "ident" in langElem.attrib:
                metainfo["language code"] = langElem.attrib["ident"].strip()
            else:
                metainfo["language code"] = "NA"
            metainfo["language"] = langElem.text.strip()
        except:
            metainfo["language code"] = "NA"
            metainfo["language"] = "NA"

        return metainfo

    ################################

    def output_metainfo(self, metainfo, metadir):
        """
        Append metainfo for a given file to a csv-file in metadir.
        Input: Dictionary with meta information, target directory
        """
        metacats = ["filename", "file_id", "style", "author", "editor", "title", "tokens", \
                    "publisher", "place", "year", "series", "language code", "language"]

        metafile = open(os.path.join(metadir, "KaJuK_meta_information.csv"), mode="a", encoding="utf-8")

        #Write header if
        if metafile.tell() == 0:
            print("\t".join(metacats), file=metafile)

        print("\t".join([metainfo[metacat] for metacat in metacats]), file=metafile)

        metafile.close()

    ################################

    def get_lines(self, root):
        """
        Input: root
        Output: dictionaries with lb numbers as keys (integers) and
                corresponding page/line numbers as values (strings)
        """
        page_numbers = dict()
        line_numbers = dict()
        lb_nr = 1
        for child in root:
            if child.tag == "pb":
                page_nr = child.attrib["n"]
            elif child.tag == "line":
                line_nr = child.attrib["n"]
            elif child.tag == "lb":
                page_numbers[lb_nr] = page_nr
                line_numbers[lb_nr] = line_nr
                lb_nr += 1

        return page_numbers, line_numbers

    ################################

    def get_annotations(self, child, tokeninfo):
        """
        Input: child node, dictionary tokeninfo
        Output: dictionary tokeninfo with annotations of the child
        """

        for attrib in child.attrib:
            if attrib == "ID":
                tokeninfo["Ident"] = child.attrib[attrib]
            else:
                tokeninfo[attrib] = child.attrib[attrib]
        return tokeninfo

    ################################

    def get_tokens(self, lb, lb_info_sup, sent_parts, second_annos, page_numbers, line_numbers, lb_nr, tok_ID, sent, count):
        """
        Creates Token-Objects for inferior lbs
        Input:  lb node, dictionary with lb info of the superior lb, list with sentence parts,
                dictionary for second annotations, dictionary with line_numbers, number of current lb,
                ID of current token, sentence object, counter for inferior lbs
        Output: updated list sent_parts, updated dictionary second_annos,
                updated token ID, updated sentence object
        """

        columns= ["Ebene1", "Ebene2", "Ebene3", "Ebene4", "Ident", "real", "type", \
                    "IR", "norm", "ADDtype", "ADDIR", "dir", "change", "viol"]
        lb_attributes = ["lb_n", "lb_type", "lb_IR", "lb_EB", "lb_ADDIR"]
        punct = [",", ";", ":", "/", "–", "-"]
        punc = ""

        kwargs = dict()
        lb_info = dict()
        tokeninfo = dict()

        #lb attributes
        for attribute in lb_attributes:
            attrib = attribute.split("_")[1]
            if attrib in lb.attrib:
                lb_info[attribute] = lb.attrib[attrib]
            else:
                lb_info[attribute] = "_"

        #sent parts of this (inferior) lb
        text = ET.tostringlist(lb, encoding="Unicode", method="text")
        #check if last text element belongs to superior lb
        if "\n\t\n" in text[-1] or "\n\n" in text[-1]:
            text.remove(text[-1])
        sent_parts_inf = [elem.strip() for elem in text if elem.strip()]

        text_elem = sent_parts[0]
        text_elem_inf = sent_parts_inf[0]
        #check if textelement belongs to lb_info or lb_info_sup
        if text_elem != text_elem_inf:
            if text_elem[0] == "]":
                text_elem = text_elem[1:]
            elif text_elem[-1] == "[":
                text_elem = text_elem[:-1]
            tokens = text_elem.split()
            if tokens:
                for tok in tokens:
                    toks = []
                    if tok not in punct:
                        #extract punctuation
                        if tok[-1] in punct:
                            punc = tok[-1]
                            tok = tok[:-1]
                        #extract quotation marks
                        if tok[0] == '"':
                            toks.append(tok[0])
                        toks.append(tok)
                        if tok[-1] == '"':
                            toks.append(tok[-1])
                        if punc in punct:
                            toks.append(punc)
                            punc = ""
                    else:
                        toks.append(tok)
                    for tok in toks:
                        for col in columns:
                            kwargs[col] = "_"
                        #ID
                        kwargs["ID"] = str(tok_ID)
                        tok_ID += 1
                        #FORM
                        kwargs["FORM"] = tok
                        #page+line number
                        kwargs["page"] = page_numbers[lb_nr]
                        kwargs["line"] = line_numbers[lb_nr]
                        #lb_...
                        for attribute in lb_attributes:
                            kwargs[attribute] = lb_info[attribute]
                        token = Token(**kwargs)
                        sent.add_token(token)
                    toks.clear()
            text_elem = sent_parts.pop(0)

        for child in lb:

            # lb in lb?
            if child.tag == "lb":
                count += 1
                sent_parts_inf, second_annos, tok_ID, sent = self.get_tokens(child, lb_info, sent_parts_inf, second_annos, page_numbers, line_numbers, lb_nr, tok_ID, sent, count)
                count -= 1
                if sent_parts_inf:
                    for part in sent_parts:
                        if part == sent_parts_inf[0]:
                            sent_parts = sent_parts[sent_parts.index(part):]
                            break
                continue

            #Ebene1
            tokeninfo["Ebene1"] = "lb_" + str(count)
            #Ebene2
            tokeninfo["Ebene2"] = child.tag
            tokeninfo = self.get_annotations(child, tokeninfo)
            if child.text:
                tokeninfo["text"] = child.text.strip()
            #Ebene3
            else:
                for granchild in child:
                    tokeninfo["Ebene3"] = granchild.tag
                    tokeninfo = self.get_annotations(granchild, tokeninfo)
                    if granchild.text:
                        tokeninfo["text"] = granchild.text.strip()
                    #Ebene4
                    else:
                        for grangranchild in granchild:
                            tokeninfo["Ebene4"] = grangranchild.tag
                            tokeninfo = self.get_annotations(grangranchild, tokeninfo)
                            tokeninfo["text"] = grangranchild.text.strip()

            text_elem = sent_parts.pop(0)
            text_elem_inf = sent_parts_inf.pop(0)

            #textelement without tag inbetween?
            if tokeninfo["text"] != text_elem and "hier Zweitannotation" not in text_elem:
                if text_elem[0] == "]":
                    text_elem = text_elem[1:]
                elif text_elem[-1] == "[":
                    text_elem = text_elem[:-1]
                tokens = text_elem.split()
                if tokens:
                    for tok in tokens:
                        toks = []
                        if tok not in punct:
                            #extract punctuation
                            if tok[-1] in punct:
                                punc = tok[-1]
                                tok = tok[:-1]
                            #extract quotation marks
                            if tok[0] == '"':
                                toks.append(tok[0])
                            toks.append(tok)
                            if tok[-1] == '"':
                                toks.append(tok[-1])
                            if punc in punct:
                                toks.append(punc)
                                punc = ""
                        else:
                            toks.append(tok)
                        for tok in toks:
                            for col in columns:
                                kwargs[col] = "_"
                            #ID
                            kwargs["ID"] = str(tok_ID)
                            tok_ID += 1
                            #FORM
                            kwargs["FORM"] = tok
                            #Ebene1
                            if tok not in punct:
                                kwargs["Ebene1"] = "lb_" + str(count)
                            #page+line number
                            kwargs["page"] = page_numbers[lb_nr]
                            kwargs["line"] = line_numbers[lb_nr]
                            #lb_...
                            for attribute in lb_attributes:
                                kwargs[attribute] = lb_info[attribute]
                            token = Token(**kwargs)
                            sent.add_token(token)
                        toks.clear()
                text_elem_inf = sent_parts_inf.pop(0)
                text_elem = sent_parts.pop(0)

            #second annotation?
            if "hier Zweitannotation" in text_elem:
                i = int(text_elem[-1])
                second_annos[i]["ID"] = tok_ID
                for col in columns:
                    if col in tokeninfo and "lb" not in tokeninfo[col]:
                        second_annos[i][col] = tokeninfo[col]
            else:
                tokens = text_elem.split()
                for tok in tokens:
                    toks = []
                    if tok not in punct:
                        #extract punctuation
                        if tok[-1] in punct:
                            punc = tok[-1]
                            tok = tok[:-1]
                        #extract quotation marks
                        if tok[0] == '"':
                            toks.append(tok[0])
                        toks.append(tok)
                        if tok[-1] == '"':
                            toks.append(tok[-1])
                        if punc in punct:
                            toks.append(punc)
                            punc = ""
                    else:
                        toks.append(tok)
                    for tok in toks:
                        #ID
                        kwargs["ID"] = str(tok_ID)
                        tok_ID += 1
                        #FORM
                        kwargs["FORM"] = tok
                        #page+line number
                        kwargs["page"] = page_numbers[lb_nr]
                        kwargs["line"] = line_numbers[lb_nr]
                        #lb_...
                        for attribute in lb_attributes:
                            kwargs[attribute] = lb_info[attribute]
                        #rest of columns
                        for col in columns:
                            if tok not in punct and tok != '"' and col in tokeninfo:
                                kwargs[col] = tokeninfo[col]
                            else:
                                kwargs[col] = "_"
                        token = Token(**kwargs)
                        sent.add_token(token)
                    toks.clear()
            tokeninfo.clear()

        #save remaining textelement without tag
        if sent_parts_inf:
            text_elem = sent_parts.pop(0)
            if text_elem[0] == "]":
                text_elem = text_elem[1:]
            elif text_elem[-1] == "[":
                text_elem = text_elem[:-1]
            tokens = text_elem.split()
            if tokens:
                for tok in tokens:
                    toks = []
                    if tok not in punct:
                        #extract punctuation
                        if tok[-1] in punct:
                            punc = tok[-1]
                            tok = tok[:-1]
                        #extract quotation marks
                        if tok[0] == '"':
                            toks.append(tok[0])
                        toks.append(tok)
                        if tok[-1] == '"':
                            toks.append(tok[-1])
                        if punc in punct:
                            toks.append(punc)
                            punc = ""
                    else:
                        toks.append(tok)
                    for tok in toks:
                        for col in columns:
                            kwargs[col] = "_"
                        #ID
                        kwargs["ID"] = str(tok_ID)
                        tok_ID += 1
                        #FORM
                        kwargs["FORM"] = tok
                        #Ebene1
                        if tok not in punct:
                            kwargs["Ebene1"] = "lb_" + str(count)
                        #page+line number
                        kwargs["page"] = page_numbers[lb_nr]
                        kwargs["line"] = line_numbers[lb_nr]
                        #lb_...
                        for attribute in lb_attributes:
                            kwargs[attribute] = lb_info[attribute]
                        token = Token(**kwargs)
                        sent.add_token(token)
                    toks.clear()

        return sent_parts, second_annos, tok_ID, sent

    ################################

    def import_file(self, file, metadir):

        path, filename = os.path.split(file)

        #Read xml tree
        with open(file, mode="r", encoding="utf-8") as encoded_file:
            decoded_string = html.unescape(encoded_file.read())
        root = ET.fromstring(decoded_string)

        #read metainfo
        filename = os.path.splitext(filename)[0]
        name = filename.lower()
        metadocs_folder = file.split("XML")[0] + "\\TEI-HEADERS\\document"
        metadocs = os.listdir(metadocs_folder)
        for doc in metadocs:
            if name in doc:
                doc_path = metadocs_folder + "\\" + doc
                break
        metadoc = ET.parse(doc_path)
        path, doc = os.path.split(doc_path)
        doc = os.path.splitext(doc)[0]
        metaroot = metadoc.getroot()
        metainfo = self.read_metadocs(metaroot)
        metainfo["filename"] = filename
        metainfo["file_id"] = doc
        self.output_metainfo(metainfo, metadir)

        #get corresponding page and line numbers for all lbs
        page_numbers, line_numbers = self.get_lines(root)

        #create doc-object
        doc = Doc(filename)

        #token
        kwargs = dict()
        columns= ["Ebene1", "Ebene2", "Ebene3", "Ident", "real", "type", \
                    "IR", "norm", "ADDtype", "ADDIR", "dir", "change", "viol"]
        lb_attributes = ["lb_n", "lb_type", "lb_IR", "lb_EB", "lb_ADDIR"]

        #punctuation
        punct_eos = [".", "?", "!"]
        punct = [",", ";", ":", "/", "–", "-"]
        punc = ""

        sent = Sentence(**{"text" : ""})
        lb_info = dict()
        tokeninfo = dict()
        second_annos = list()
        lb_nr = 0
        tok_ID = 1

        #for every lb: get token-infos
        for lb in root.findall("lb"):
            lb_nr += 1

            #lb attributes
            for attribute in lb_attributes:
                attrib = attribute.split("_")[1]
                if attrib in lb.attrib:
                    lb_info[attribute] = lb.attrib[attrib]
                else:
                    lb_info[attribute] = "_"

            #text elements
            text = ET.tostringlist(lb, encoding="Unicode", method="text")
            sent_parts = [elem.strip() for elem in text if elem.strip()]

            #second annotations?
            ind = 0
            for i in range(len(sent_parts)-2):
                if sent_parts[i] == "[" or sent_parts[i+2] == "]":
                    #text
                    second_anno = {"text": sent_parts[i+1]}
                    #place
                    if i == 0:
                        second_anno["place"] = "before"
                    elif i == len(sent_parts)-3 :
                        second_anno["place"] = "after"
                    elif sent_parts[i+1] == sent_parts[i+3]:
                        second_anno["place"] = "before"
                    elif sent_parts[i-1] == sent_parts[i+1]:
                        second_anno["place"] = "after"
                    elif sent_parts[i+1] in sent_parts[i+3]:
                        second_anno["place"] = "before"
                    elif sent_parts[i+1] in sent_parts[i-1]:
                        second_anno["place"] = "after"

                    if "place" in second_anno:
                        second_annos.append(second_anno)
                        sent_parts[i+1] += " hier Zweitannotation " + str(ind)
                        ind += 1

            for child in lb:

                # lb in lb?
                if child.tag == "lb":
                    count = 1
                    sent_parts, second_annos, tok_ID, sent = self.get_tokens(child, lb_info, sent_parts, second_annos, page_numbers, line_numbers, lb_nr, tok_ID, sent, count)
                    continue

                #Ebene1
                tokeninfo["Ebene1"] = child.tag
                tokeninfo = self.get_annotations(child, tokeninfo)
                if child.text:
                    tokeninfo["text"] = child.text.strip()
                #Ebene2
                else:
                    for granchild in child:
                        tokeninfo["Ebene2"] = granchild.tag
                        tokeninfo = self.get_annotations(granchild, tokeninfo)
                        if granchild.text:
                            tokeninfo["text"] = granchild.text.strip()
                        #Ebene3
                        else:
                            for grangranchild in granchild:
                                tokeninfo["Ebene3"] = grangranchild.tag
                                tokeninfo = self.get_annotations(grangranchild, tokeninfo)
                                tokeninfo["text"] = grangranchild.text.strip()

                #textelement without tag inbetween?
                text_elem = sent_parts.pop(0)
                if tokeninfo["text"] != text_elem:
                    if text_elem[0] == "]":
                        text_elem = text_elem[1:]
                    elif text_elem[-1] == "[":
                        text_elem = text_elem[:-1]
                    tokens = text_elem.split()
                    if tokens:
                        for tok in tokens:
                            toks = []
                            if tok not in punct:
                                #extract punctuation
                                if tok[-1] in punct:
                                    punc = tok[-1]
                                    tok = tok[:-1]
                                #extract quotation marks
                                if tok[0] == '"':
                                    toks.append(tok[0])
                                toks.append(tok)
                                if tok[-1] == '"':
                                    toks.append(tok[-1])
                                if punc in punct:
                                    toks.append(punc)
                                    punc = ""
                            else:
                                toks.append(tok)
                            for tok in toks:
                                for col in columns:
                                    kwargs[col] = "_"
                                #ID
                                kwargs["ID"] = str(tok_ID)
                                tok_ID += 1
                                #FORM
                                kwargs["FORM"] = tok
                                #page+line number
                                kwargs["page"] = page_numbers[lb_nr]
                                kwargs["line"] = line_numbers[lb_nr]
                                #lb_...
                                for attribute in lb_attributes:
                                    kwargs[attribute] = lb_info[attribute]
                                token = Token(**kwargs)
                                sent.add_token(token)
                            toks.clear()
                    text_elem = sent_parts.pop(0)

                #second annotation?
                if tokeninfo["text"] != text_elem:
                    i = int(text_elem[-1])
                    second_annos[i]["ID"] = tok_ID
                    for col in columns:
                        if col in tokeninfo:
                            second_annos[i][col] = tokeninfo[col]
                else:
                    tokens = text_elem.split()
                    for tok in tokens:
                        toks = []
                        if tok not in punct:
                            #extract punctuation
                            if tok[-1] in punct:
                                punc = tok[-1]
                                tok = tok[:-1]
                            #extract quotation marks
                            if tok[0] == '"':
                                toks.append(tok[0])
                            toks.append(tok)
                            if tok[-1] == '"':
                                toks.append(tok[-1])
                            if punc in punct:
                                toks.append(punc)
                                punc = ""
                        else:
                            toks.append(tok)
                        for tok in toks:
                            #ID
                            kwargs["ID"] = str(tok_ID)
                            tok_ID += 1
                            #FORM
                            kwargs["FORM"] = tok
                            #page+line number
                            kwargs["page"] = page_numbers[lb_nr]
                            kwargs["line"] = line_numbers[lb_nr]
                            #lb_...
                            for attribute in lb_attributes:
                                kwargs[attribute] = lb_info[attribute]
                            #rest of columns
                            for col in columns:
                                if tok not in punct and tok != '"' and col in tokeninfo:
                                    kwargs[col] = tokeninfo[col]
                                else:
                                    kwargs[col] = "_"
                            token = Token(**kwargs)
                            sent.add_token(token)
                        toks.clear()
                tokeninfo.clear()

            #save remaining textelement without tag
            if sent_parts:
                text_elem = sent_parts.pop(0)
                if text_elem[0] == "]":
                    text_elem = text_elem[1:]
                elif text_elem[-1] == "[":
                    text_elem = text_elem[:-1]
                tokens = text_elem.split()
                if tokens:
                    for tok in tokens:
                        toks = []
                        if tok not in punct:
                            #extract punctuation
                            if tok[-1] in punct:
                                punc = tok[-1]
                                tok = tok[:-1]
                            #extract quotation marks
                            if tok[0] == '"':
                                toks.append(tok[0])
                            toks.append(tok)
                            if tok[-1] == '"':
                                toks.append(tok[-1])
                            if punc in punct:
                                toks.append(punc)
                                punc = ""
                        else:
                            toks.append(tok)
                        for tok in toks:
                            for col in columns:
                                kwargs[col] = "_"
                            #ID
                            kwargs["ID"] = str(tok_ID)
                            tok_ID += 1
                            #FORM
                            kwargs["FORM"] = tok
                            #page+line number
                            kwargs["page"] = page_numbers[lb_nr]
                            kwargs["line"] = line_numbers[lb_nr]
                            #lb_...
                            for attribute in lb_attributes:
                                kwargs[attribute] = lb_info[attribute]
                            token = Token(**kwargs)
                            sent.add_token(token)
                        toks.clear()

            #add second annotations
            for anno in second_annos:
                if anno["text"][-1] in punct or anno["text"][-1] in punct_eos:
                    anno["text"] = anno["text"][:-1]
                text = anno["text"].strip().split()
                i = anno["ID"]
                if anno["place"] == "after":
                    for x in range(i-1, 0, -1):
                        if text:
                            tok = sent.tokens[x-1]
                            if tok.FORM == text[-1]:
                                text.pop()
                                for col in columns:
                                    if col in anno:
                                        if tok.__dict__[col] != "_":
                                            tok.__dict__[col] += " [" + anno[col] + "]"
                                        else:
                                            tok.__dict__[col] = " [" + anno[col] + "]"
                        else:
                            break
                elif anno["place"] == "before":
                    for x in range(i-1, len(sent.tokens)):
                        if text:
                            tok = sent.tokens[x]
                            if tok.FORM == text[0]:
                                text.pop(0)
                                for col in columns:
                                    if col in anno:
                                        if tok.__dict__[col] != "_":
                                            tok.__dict__[col] += " [" + anno[col] + "]"
                                        else:
                                            tok.__dict__[col] = " [" + anno[col] + "]"
                        else:
                            break
            second_annos.clear()

            #end of sentence?
            ellipses = list()
            for token in reversed(sent.tokens):
                if token.type != "E" and token.ADDtype != "E":
                    if token.FORM[-1] in punct_eos:
                        punc = token.FORM[-1]
                        token.FORM = token.FORM[:-1]
                        if not token.FORM:
                            sent.tokens.remove(token)
                        #ID
                        kwargs["ID"] = str(int(sent.tokens[-1].ID) + 1)
                        #FORM
                        kwargs["FORM"] = punc
                        #page+line number
                        kwargs["page"] = page_numbers[lb_nr]
                        kwargs["line"] = line_numbers[lb_nr]
                        #lb_...
                        for attribute in lb_attributes:
                            kwargs[attribute] = lb_info[attribute]
                        #rest of columns
                        for col in columns:
                            kwargs[col] = "_"
                        token = Token(**kwargs)
                        sent.add_token(token)

                        #reconstruct text
                        for tok in sent.tokens:
                            if tok.FORM in punct or tok.FORM in punct_eos:
                                if ellipses:
                                    sent.text += "]" + tok.FORM
                                    ellipses.clear()
                                else:
                                    sent.text += tok.FORM
                            elif tok.type == "E" or tok.ADDtype == "E":
                                if ellipses:
                                    sent.text += " " + tok.FORM
                                elif sent.text:
                                    sent.text += " [" + tok.FORM
                                    ellipses.append(tok.FORM)
                                else:
                                    sent.text += "[" + tok.FORM
                                    ellipses.append(tok.FORM)
                                if tok.FORM[0] == '"':
                                    tok.FORM = tok.FORM[1:]
                                if tok.FORM[-1] == '"':
                                    tok.FORM = tok.FORM[:-1]
                            elif tok.FORM != '"':
                                if ellipses:
                                    sent.text += "] " + tok.FORM
                                    ellipses.clear()
                                elif sent.text:
                                    sent.text += " " + tok.FORM
                                else:
                                    sent.text += tok.FORM
                                if tok.FORM[0] == '"':
                                    tok.FORM = tok.FORM[1:]
                                if tok.FORM[-1] == '"':
                                    tok.FORM = tok.FORM[:-1]
                        doc.add_sent(sent)
                        sent = Sentence(**{"text" : ""})
                        tok_ID = 1
                        break

                    else:
                        break

        #save remaining last sentence
        if sent.tokens:
            #reconstruct text
            for tok in sent.tokens:
                if tok.FORM in punct or tok.FORM in punct_eos:
                    if ellipses:
                        sent.text += "]" + tok.FORM
                        ellipses.clear()
                    else:
                        sent.text += tok.FORM
                elif tok.type == "E" or tok.ADDtype == "E":
                    if ellipses:
                        sent.text += " " + tok.FORM
                    else:
                        sent.text += " [" + tok.FORM
                        ellipses.append(tok.FORM)
                    if tok.FORM[0] == '"':
                        tok.FORM = tok.FORM[1:]
                    if tok.FORM[-1] == '"':
                        tok.FORM = tok.FORM[:-1]
                elif tok.FORM != '"':
                    if ellipses:
                        sent.text += "] " + tok.FORM
                        ellipses.clear()
                    elif sent.text:
                        sent.text += " " + tok.FORM
                    else:
                        sent.text += tok.FORM
                    if tok.FORM[0] == '"':
                        tok.FORM = tok.FORM[1:]
                    if tok.FORM[-1] == '"':
                        tok.FORM = tok.FORM[:-1]

            doc.add_sent(sent)

        return doc

###################################

class MercuriusTigerXMLImporter(Importer):

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    #######################

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

        #Read xml tree
        tree = ET.parse(file)
        root = tree.getroot()

        doc = Doc(filename)

        for s_elem in root.find("body"):
            #Get graph element
            graph = s_elem.find("graph")
            rootID = graph.attrib["root"]

            discontinuous = graph.attrib.get("discontinuous", False)
            if discontinuous: discontinuous = True

            #Get terminals and nonterminals
            terminals = graph.find("terminals")
            nonterminals = graph.find("nonterminals")

            tokens = []

            for terminal in sorted(terminals, key=lambda t : int(t.attrib["id"].split("_")[-1])):

                #Get annotations
                pos = terminal.attrib["pos"]
                if pos == "--": pos = "_"
                feats = terminal.attrib["morph"].replace("--", "_")

                #Create token
                token = Token(**{"FORM" : terminal.attrib["word"],
                                 "POS" : pos,
                                 "FEATS" : feats,
                                 "TigerID" : terminal.attrib["id"]})
                tokens.append(token)

            #Create sentence
            sentence = Sentence(tokens, **{"sent_id(Tiger)" : s_elem.attrib["id"]})

            #If there are no non-terminals
            if not len(nonterminals):
                tree = None

            #Otherwise read syntax tree
            else:
                root_node = nonterminals.find("nt[@id='"+rootID+"']")
                tree = Tree(rootID, root_node.attrib["cat"], "--")

                ###########################

                def read_tree(node, tree):
                    for edge in node.findall("edge"):
                        edgeID = edge.attrib["idref"]

                        #Non-terminal
                        if len(edgeID.split("_")[1]) == 3 and int(edgeID.split("_")[1][0]) >= 5:
                            nonterminal_node = nonterminals.find("nt[@id='"+edgeID+"']")
                            nonterminal_child = Tree(edgeID, nonterminal_node.attrib["cat"], edge.attrib["label"])
                            read_tree(nonterminal_node, nonterminal_child)
                            tree.add_child(nonterminal_child)

                        #Terminal
                        else:
                            terminal_child = Tree(edgeID, "Tok", edge.attrib["label"],
                                            **{"token" : [tok for tok in sentence.tokens if tok.TigerID == edgeID][0]})
                            tree.add_child(terminal_child)

                ############################

                read_tree(root_node, tree)

            sentence.tree = tree
            sentence.discontinuous_tree = discontinuous

            if not "text" in sentence.__dict__:
                sentence.text = " ".join([tok.FORM for tok in sentence.tokens])
            doc.add_sent(sentence)

        return doc

#####################################

class ReFUPImporter(Importer):

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    #######################

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

        #Read xml tree
        tree = ET.parse(file)
        root = tree.getroot()

        doc = Doc(filename)

        for s_elem in root.find("body"):
            #Get graph element
            graph = s_elem.find("graph")
            rootID = graph.attrib["root"]

            discontinuous = graph.attrib.get("discontinuous", False)
            if discontinuous: discontinuous = True

            #Get terminals and nonterminals
            terminals = graph.find("terminals")
            nonterminals = graph.find("nonterminals")

            tokens = []

            for terminal in sorted(terminals, key=lambda t : int(t.attrib["id"].split("_")[-1])):

                #Get annotations
                pos = terminal.attrib["pos"]
                if pos == "--": pos = "_"
                if "morph" in terminal.attrib:
                    feats = terminal.attrib["morph"].replace("--", "_")
                else:
                    feats = "_"

                #Create token
                token = Token(**{"FORM" : terminal.attrib["word"],
                                 "POS" : pos,
                                 "FEATS" : feats,
                                 "TigerID" : terminal.attrib["id"]})
                tokens.append(token)

            #Create sentence
            sentence = Sentence(tokens, **{"sent_id(Tiger)" : s_elem.attrib["id"]})

            #If there are no non-terminals
            if not len(nonterminals):
                tree = None

            #Otherwise read syntax tree
            else:
                root_node = nonterminals.find("nt[@id='"+rootID+"']")
                tree = Tree(rootID, root_node.attrib["cat"], "--")

                ###########################

                def read_tree(node, tree):
                    for edge in node.findall("edge"):
                        edgeID = edge.attrib["idref"]

                        #Non-terminal
                        if len(edgeID.split("_")[1]) == 3 and int(edgeID.split("_")[1][0]) >= 5:
                            nonterminal_node = nonterminals.find("nt[@id='"+edgeID+"']")
                            nonterminal_child = Tree(edgeID, nonterminal_node.attrib["cat"], edge.attrib["label"])
                            read_tree(nonterminal_node, nonterminal_child)
                            tree.add_child(nonterminal_child)

                        #Terminal
                        else:
                            terminal_child = Tree(edgeID, "Tok", edge.attrib["label"],
                                            **{"token" : [tok for tok in sentence.tokens if tok.TigerID == edgeID][0]})
                            tree.add_child(terminal_child)

                ############################

                read_tree(root_node, tree)

            sentence.tree = tree
            sentence.discontinuous_tree = discontinuous

            if not "text" in sentence.__dict__:
                sentence.text = " ".join([tok.FORM for tok in sentence.tokens])
            doc.add_sent(sentence)

        return doc

##########################

class XMLFnhdCImporter(Importer):

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ################################

    def read_metaheader(self, root):
        """
        Read info from metaheader into dictionary.
        Currently included are:
        - filename
        - textname, textnr
        - Angabe_nr
        - Autor, Text
        - Titel
        - Herausgeber
        - Erscheinungsort, Erscheinungsjahr
        - Umfang, aufgenommen
        - Sprachraum, Ort, Jahr
        - Textart
        - URL_text
        If info not available, value is NA.
        Input: Root (text element)
        Output: Dictionary with meta info
        """
        metainfo = dict()
        metaheader = root.find("bibliographie")
        basis = metaheader.find("Basis")

        #textname, textnr
        metainfo["textname"] = root.attrib["name"]
        metainfo["textnr"] = metaheader.attrib["textnr"]

        #Angabe_nr
        try:
            metainfo["Angabe_nr"] = metaheader.find("Angabe_nr").text
        except:
            metainfo["Angabe_nr"] = "NA"

        #Autor, Text
        try:
            metainfo["Autor"] = basis.find("./Kurztitel/Autor").text
        except:
            metainfo["Autor"] = "NA"
        try:
            metainfo["Text"] = basis.find("./Kurztitel/Text").text
        except:
            metainfo["Text"] = "NA"

        #Titel
        try:
            title = basis.find("Titel").text.replace("\n", "").replace("       ", "")
            metainfo["Titel"] = title
        except:
            metainfo["Titel"] = "NA"

        #Herausgeber
        try:
            metainfo["Herausgeber"] = basis.find("Hrsg").text
        except:
            metainfo["Herausgeber"] = "NA"

        #Erscheinungsort, -jahr
        ersch = basis.find("Ersch")
        try:
            metainfo["Erscheinungsort"] = ersch.find("Eort").text
        except:
            metainfo["Erscheinungsort"] = "NA"
        try:
            metainfo["Erscheinungsjahr"] = ersch.find("Ejahr").text
        except:
            metainfo["Erscheinungsjahr"] = "NA"

        #Umfang, aufgenommen
        try:
            metainfo["Umfang"] = ersch.find("Umfang").text
        except:
            metainfo["Umfang"] = "NA"
        try:
            metainfo["aufgenommen"] = basis.find("aufgenommen").text
        except:
            metainfo["aufgenommen"] = "NA"

        #Sprachraum, Ort, Jahr
        try:
            metainfo["Sprachraum"] = basis.find("./Landschaft/Sprachraum").text
        except:
            metainfo["Sprachraum"] = "NA"
        try:
            metainfo["Ort"] = basis.find("./Landschaft/Ort").text
        except:
            metainfo["Ort"] = "NA"
        try:
            metainfo["Jahr"] = basis.find("./Zeit/Jahr").text
        except:
            metainfo["Jahr"] = "NA"

        #Textart
        zusatz = metaheader.find("Zusatz")
        try:
            metainfo["Textart"] = zusatz.find("Textart").text
        except:
            metainfo["Textart"] = "NA"

        #URL_text
        try:
            metainfo["URL_text"] = metaheader.find("./Links/a[@typ='text']").attrib["href"]
        except:
            metainfo["URL_text"] = "NA"


        #Edit_Eingr (123)?, Edit_Anm (113)
        #Vorlage (137)?
        #Reihe, Band, Druck?

        return metainfo

    ################################

    def output_metainfo(self, metainfo, metadir):
        """
        Append metainfo for a given file to a csv-file in metadir.
        Input: Dictionary with meta information, target directory
        """
        metacats = ["filename", "textname", "textnr", "Angabe_nr", "Autor", "Text", "Titel", \
                    "Herausgeber", "Erscheinungsort", "Erscheinungsjahr", "Umfang", "aufgenommen", \
                    "Sprachraum", "Ort", "Jahr", "Textart", "URL_text"]

        metafile = open(os.path.join(metadir, "FnhdC_meta_information.csv"), mode="a", encoding="utf-8")

        #Write header if
        if metafile.tell() == 0:
            print("\t".join(metacats), file=metafile)

        print("\t".join([metainfo[metacat] for metacat in metacats]), file=metafile)

        metafile.close()

    ################################

    def get_wordforms(self, node, layouts, wordforms, id=0):
        """
        Find wordform-nodes and save corresponding layout-annotations ("eingriff"/"ueberschrift"/"emph"/"zitat"/"name").
        Input:  current annotation-node, list of layout-annotations corresponding to this node, list of all wordforms,
                index of the current child-node (0 = child-node is directly under the line-node)
        Output: updated list of all wordforms (each entry ist a list that contains a wordform-node
                and the corresponding layouts-list)
        """
        for child in node:
            if child.tag != "wortform":
                id += 1
                try:
                    layouts[id] = child.tag
                except:
                    layouts.append(child.tag)
                wordforms = self.get_wordforms(child, layouts, wordforms, id)
                id -= 1
            else:
                wordforms.append([child, layouts[:id+1]])

        return wordforms

    ################################

    def import_file(self, file, metadir):

        path, filename = os.path.split(file)

        #Read xml tree
        tree = ET.parse(file)
        root = tree.getroot()

        #read metainfo
        metainfo = self.read_metaheader(root)
        metainfo["filename"] = os.path.splitext(filename)[0]
        self.output_metainfo(metainfo, metadir)

        #create doc-object
        doc = Doc(filename)

        sent = Sentence(**{"text": ""})
        id = 1

        for page in root.findall("seite"):
            page_info = dict()
            for attrib in page.attrib:
                if attrib != "nr_text": page_info[attrib] = page.attrib[attrib]

            for line in page.findall("zeile"):
                line_info = dict()
                for attrib in line.attrib:
                    if attrib != "lf_seite": line_info[attrib] = line.attrib[attrib]

                for child in line:
                    layouts = []
                    wordforms = []

                    if child.tag != "wortform":
                        layouts.append(child.tag)
                        wordforms = self.get_wordforms(child, layouts, wordforms)
                    else:
                        wordforms.append([child, layouts])

                    #token
                    for word in wordforms:
                        kwargs = dict()
                        punct = dict()
                        sign = dict()
                        tok = word[0]
                        layouts = word[1]

                        #page
                        for info in page_info:
                            info_name = "Seite_" + info
                            kwargs[info_name] = page_info[info]
                        #line
                        for info in line_info:
                            info_name = "Zeile_" + info
                            kwargs[info_name] = line_info[info]
                        #layouts + name
                        layout_column = []
                        for layout in layouts:
                            if layout == "name":
                                kwargs["Anmerkungen"] = "Name"
                            elif layout == "emph":
                                layout_column.append("hervorgehoben")
                            else:
                                layout_column.append(layout)
                        if layout_column:
                            kwargs["Layout"] = ",".join(layout_column)
                        else:
                            kwargs["Layout"] = "_"
                        if not "Anmerkungen" in kwargs: kwargs["Anmerkungen"] = "_"

                        #get annotations
                        annos = tok.find("annotation")
                        for anno in annos.attrib:
                            #FORM
                            if anno == "gelesen":
                                kwargs["FORM"] = annos.attrib[anno]
                            #verb_form
                            elif anno == "form":
                                kwargs["verb_form"] = annos.attrib[anno]
                            #punctuation after token
                            elif anno == "zeichen":
                                #page
                                for info in page_info:
                                    info_name = "Seite_" + info
                                    punct[info_name] = page_info[info]
                                #line
                                for info in line_info:
                                    info_name = "Zeile_" + info
                                    punct[info_name] = line_info[info]
                                #layouts + name
                                punct["Anmerkungen"] = kwargs["Anmerkungen"]
                                punct["Layout"] = kwargs["Layout"]
                                #FORM
                                punct["FORM"] = annos.attrib[anno]
                            #punctuation before token
                            elif anno == "vorzeichen":
                                #page
                                for info in page_info:
                                    info_name = "Seite_" + info
                                    sign[info_name] = page_info[info]
                                #line
                                for info in line_info:
                                    info_name = "Zeile_" + info
                                    sign[info_name] = line_info[info]
                                #layouts + name
                                sign["Anmerkungen"] = kwargs["Anmerkungen"]
                                sign["Layout"] = kwargs["Layout"]
                                #ID
                                sign["ID"] = str(id)
                                id += 1
                                #FORM
                                sign["FORM"] = annos.attrib[anno]
                            #other annotations
                            elif anno != "praefix":
                                kwargs[anno] = annos.attrib[anno]
                        for anno in kwargs:
                            if kwargs[anno] == "???":
                                kwargs[anno] = "_"
                            elif kwargs[anno] == "(nichts weiter)":
                                kwargs[anno] = "None"
                        if "FORM" not in kwargs: kwargs["FORM"] = kwargs["gefunden"]

                        #ID
                        kwargs["ID"] = str(id)
                        id += 1

                        #morph
                        morphs = [morph.text for morph in tok.findall("morph")]
                        kwargs["morph"] = ",".join(morphs)

                        #punctuation before token
                        if sign:
                            sent.text += sign["FORM"]
                            token = Token(**sign)
                            sent.add_token(token)

                        if kwargs["FORM"] in ["(", "["]:
                            sent.text += kwargs["FORM"]
                        elif kwargs["FORM"] in [")", "]"]:
                            sent.text += sent.text.strip() + kwargs["FORM"] + " "
                        else:
                            sent.text += kwargs["FORM"] + " "
                        token = Token(**kwargs)
                        sent.add_token(token)

                        #punctuation after token
                        if punct:
                            punct["ID"] = str(id)
                            id += 1
                            sent.text = sent.text.strip() + punct["FORM"] + " "
                            token = Token(**punct)
                            sent.add_token(token)

                            #end of sentence?
                            if punct["FORM"] in [".", "?", "!"] and kwargs["typ"] != "zahl":
                                sent.text = sent.text.strip()
                                doc.add_sent(sent)
                                sent = Sentence(**{"text": ""})
                                id = 1

                            sign.clear()
                            punct.clear()
                            kwargs.clear()

                line_info.clear()
            page_info.clear()

        #save remaining last sentence
        if sent.tokens:
            sent.text = sent.text.strip()
            doc.add_sent(sent)

        return doc

#############################

class CoNLL2000Importer(Importer):

    COLUMNS = {"FORM" : 0, "XPOS" : 1, "CHUNK" : 2}

    ###############################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ###############################

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

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

class SDeWaCIteratorImporter(Importer):

    COLUMNS = {"Joined_ID" : 0, "FORM" : 1, "UNK1" : 2, "LEMMA" : 3, "UPOS" : 4,
               "XPOS" : 5, "UNK2" : 6, "FEATS" : 7, "UNK3" : 8, "HEAD" : 9, "UNK4" : 10,
               "DEPREL" : 11, "UNK5" : 12, "UNK6" : 13}

    ###############################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ###############################

    def yield_sentences(self, conllfile):

        tokens = list()
        metainfo = dict()

        punct_l= [".", ",", ":", ";", "!", "?", ")", "]"]
        punct_r= ["(", "["]

        sent_id = 1

        for line in conllfile:

            if not line.strip() and tokens:
                if not "text" in metainfo:
                    metainfo["text"]= ""
                    for tok in tokens:
                        #first token
                        if not metainfo["text"]:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        #token is punctuation
                        elif tok.FORM in punct_l:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        elif tok.FORM in punct_r:
                            metainfo["text"] = metainfo["text"] + " " + tok.FORM
                        #other token
                        else:
                            if metainfo["text"][-1] in punct_r:
                                metainfo["text"] = metainfo["text"] + tok.FORM
                            else:
                                metainfo["text"] = metainfo["text"] + " " + tok.FORM
                if not "sent_id(SDeWaC)" in metainfo:
                    metainfo["sent_id(SDeWaC)"] = tokens[0].Joined_ID.split("_")[0]
                if not "sent_id" in metainfo:
                    metainfo["sent_id"] = str(sent_id)
                    sent_id += 1
                sentence = Sentence(**metainfo)
                for tok in tokens:
                    sentence.add_token(tok)
                tokens.clear()
                metainfo.clear()
                yield sentence

            #Token line
            elif line.strip():
                line = line.strip().split("\t")
                values = dict()
                for col in self.COLUMNS:
                    values[col] = line[self.COLUMNS.get(col)]
                values["ID"] = values["Joined_ID"].split("_")[-1]
                tok = Token(**values)
                tokens.append(tok)

        #If file does not end with empty line
        #save remaining last sentence
        if tokens:
            if not "text" in metainfo:
                metainfo["text"]= ""
                for tok in tokens:
                    #first token
                    if not metainfo["text"]:
                        metainfo["text"] = metainfo["text"] + tok.FORM
                    #token is punctuation
                    elif tok.FORM in punct_l:
                        metainfo["text"] = metainfo["text"] + tok.FORM
                    elif tok.FORM in punct_r:
                        metainfo["text"] = metainfo["text"] + " " + tok.FORM
                    #other token
                    else:
                        if metainfo["text"][-1] in punct_r:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        else:
                            metainfo["text"] = metainfo["text"] + " " + tok.FORM
            sentence = Sentence(**metainfo)
            for tok in tokens:
                sentence.add_token(tok)
            tokens.clear()
            metainfo.clear()
            yield sentence

        conllfile.close()

    ###############################

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

        #Open file
        conllfile = open(file, mode="r", encoding="utf-8")

        #Create doc object
        doc = Doc(filename)

        doc.sentences = self.yield_sentences(conllfile)

        return doc

#######################

class GerManCCoNLLImporter(Importer):

    namespaces = {"default" : "http://www.tei-c.org/ns/1.0"}

    ################################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ################################

    def read_metaheader(self, root):
        """
        Read info from meta document into dictionary.
        Currently included are:
        - filename
        - style
        - title
        - author
        - number of words
        - place and year of publication
        - scope of bibliographic reference
        - source, reference
        - language, language code, language type
        If info not available, value is NA.
        Input: Root from meta document
        Output: Dictionary with meta info
        """
        metainfo = dict()
        header = root.find("./default:teiHeader", namespaces=self.namespaces)

        # style
        try:
            metainfo["style"] = header.attrib["style"]
        except:
            metainfo["style"] = "NA"

        # author
        try:
            authornames = ""
            authors = header.findall("./default:fileDesc/default:titleStmt/default:author", namespaces=self.namespaces)
            for author in authors:
                if authornames: authornames += ", "
                forename = author.find("./default:persName/default:forename", namespaces=self.namespaces)
                if forename.text != "NA":
                    forename_list = forename.text.split()
                    authornames +=  " ".join(forename_list)
                surname = author.find("./default:persName/default:surname", namespaces=self.namespaces)
                if surname.text != "NA":
                    surname_list = surname.text.split()
                    authornames +=  " " + " ".join(surname_list)
            metainfo["author"] = authornames.strip()
        except:
            metainfo["author"] = authornames.strip()
        if not metainfo["author"]: metainfo["author"] = "NA"

        # title
        try:
            title = header.find("./default:fileDesc/default:titleStmt/default:title", namespaces=self.namespaces)
            title_list = title.text.split()
            metainfo["title"] = " ".join(title_list)
        except:
            metainfo["title"] = "NA"

        # words
        try:
            metainfo["words"] = header.find("./default:fileDesc/default:extent[@type='Words']", namespaces=self.namespaces).text.strip()
        except:
            metainfo["words"] = "NA"

        # place
        try:
            metainfo["place"] = header.find("./default:fileDesc/default:publicationStmt/default:pubPlace", namespaces=self.namespaces).text.strip()
        except:
            metainfo["place"] = "NA"

        # year
        try:
            metainfo["year"] = header.find("./default:fileDesc/default:publicationStmt/default:date", namespaces=self.namespaces).text.strip()
        except:
            metainfo["year"] = "NA"

        # biblScope
        try:
            biblScope = header.find("./default:fileDesc/default:publicationStmt/default:biblScope", namespaces=self.namespaces)
            bibl_list = biblScope.text.split()
            metainfo["biblScope"] = " ".join(bibl_list)
        except:
            metainfo["biblScope"] = "NA"

        # source
        try:
            source = header.find("./default:fileDesc/default:sourceDesc/default:recordHist/default:source", namespaces=self.namespaces)
            metainfo["source"] = source.attrib["facs"].strip()
        except:
            metainfo["source"] = "NA"

        # reference
        try:
            ref = source.find("./default:ref", namespaces=self.namespaces)
            ref_list = ref.text.split()
            metainfo["reference"] = " ".join(ref_list)
        except:
            metainfo["reference"] = "NA"

        # language, language code
        try:
            langElem = header.find("./default:profileDesc/default:langUsage/default:language[@style='Language']", namespaces=self.namespaces)
            lang_list = langElem.text.split()
            metainfo["language"] = " ".join(lang_list)
            if "ident" in langElem.attrib:
                metainfo["language code"] = langElem.attrib["ident"].strip()
            else:
                metainfo["language code"] = "NA"
        except:
            metainfo["language code"] = "NA"
            metainfo["language"] = "NA"

        # language type
        try:
            langElem = header.find("./default:profileDesc/default:langUsage/default:language[@style='LanguageType']", namespaces=self.namespaces)
            metainfo["language type"] = langElem.text.strip()
        except:
            metainfo["language type"] = "NA"

        return metainfo

    ################################

    def output_metainfo(self, metainfo, metadir):
        """
        Append metainfo for a given file to a csv-file in metadir.
        Input: Dictionary with meta information, target directory
        """
        metacats = ["filename", "style", "author", "title", "words", "place", "year", \
                    "biblScope", "source", "reference", "language", "language code", "language type"]

        metafile = open(os.path.join(metadir, "GerManC_meta_information.csv"), mode="a", encoding="utf-8")

        #Write header if
        if metafile.tell() == 0:
            print("\t".join(metacats), file=metafile)

        for metacat in metacats:
            if metacat not in metainfo: metainfo[metacat] = "NA"

        print("\t".join([metainfo[metacat] for metacat in metacats]), file=metafile)

        metafile.close()

    ################################

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

        #Open file
        conllfile = open(file, mode="r", encoding="utf-8")

        #metafile
        metapath = path.split("CoNLL")[0] + "germanc-v1.0TEI-HEADERS/document/"
        metafile = metapath + filename.replace(".txt", ".xml")
        #files where metafilename is different
        if "Zuegellose" in filename:
            metafile = metafile.replace("Zuegellose", "Zugellose")
        elif "ChristenStat" in filename:
            metafile = metafile.replace("1685", "1686")
        elif "Biedermann" in filename:
            metafile = metafile.replace("1729", "1728")
        elif "JurisMilitaris" in filename:
            metafile = metafile.replace("1723", "1707")
        elif "Ruebezahl" in filename:
            metafile = metafile.replace("Ruebezahl", "Ruebezal")
        elif "Handwercke" in filename:
            metafile = metafile.replace("Handwercke", "Handwerck")
        elif "ArtzneyKunst" in filename:
            metafile = metafile.replace("1687", "1676")
        elif "SursumDeosum" in filename:
            metafile = metafile.replace("Deosum", "Deorsum")
        elif "Feuersbrunst" in filename:
            metafile = metafile.replace("Feuersbrunst", "Feuerbrunst")

        #Read xml tree
        try:
            tree = ET.parse(metafile)
            root = tree.getroot()
            #read metainfo
            metainfo = self.read_metaheader(root)
            metainfo["filename"] = os.path.splitext(filename)[0]
            self.output_metainfo(metainfo, metadir)

        except:
            try:
                filename_list = filename.split("_")
                name = filename_list[-1]
                metaname = name[0]
                for x in range(1, len(name)):
                    if name[x].isupper():
                        if "RedlicheMann" in filename or "AntonReiser" in filename: metaname += "_" + name[x]
                        else: metaname += "-" + name[x]
                    else:
                        metaname += name[x]
                filename_list[-1] = metaname
                metafilename = "_".join(filename_list)
                metafile = metapath + metafilename.replace(".txt", ".xml")
                tree = ET.parse(metafile)
                root = tree.getroot()
                #read metainfo
                metainfo = self.read_metaheader(root)
                metainfo["filename"] = os.path.splitext(filename)[0]
                self.output_metainfo(metainfo, metadir)
            except:
                #no metafile available
                metainfo = dict()
                metainfo["filename"] = os.path.splitext(filename)[0]
                self.output_metainfo(metainfo, metadir)

        #column names
        columns = {"ID" : 0, "FORM" : 1, "NORM" : 2, "POS" : 3, "LEMMA" : 4, \
                   "FEATS" : 5, "HEAD" : 6, "DEPREL" : 7, "DEPS" : 8, "MISC" : 9}

        #for files where columns HEAD, DEPREL are swapped
        columns_swapped = {"ID" : 0, "FORM" : 1, "NORM" : 2, "POS" : 3, "LEMMA" : 4, \
                            "FEATS" : 5, "HEAD" : 7, "DEPREL" : 6}

        #for files where columns FORM, HEAD, DEPREL are swapped
        files_swapped = ["Ratseburg", "Rosetum", "Bericht", "Musurgia", "AntiquitaetenSchatz", "Samuel", \
                            "Antiquitaeten", "Kreuzzuege", "Ursprung", "Reglement", "StaatsArchiv", "Banise", \
                            "Levante", "LebensBeschreibung", "HeldenGeschichte", "Teutsche", "Fabeln", \
                            "WerckSchul", "Mathematicus"]

        #POS-STTS-Mapping
        mapping = {"NA" : "NN", "PROAV" : "PAV", "PAVREL" : "PAV", "PWAVREL" : "PWAV", \
                    "PWREL" : "PWS", "SENT" : "$.", "$-" : "$.", "$'" : "$(", "$)" : "$(", "_" : "$("}

        #Create doc object
        doc = Doc(filename)

        tokens = list()
        metainfo = dict()

        punct_l= [".", ",", ":", ";", "!", "?", ")", "]", "'"]
        punct_r= ["(", "["]

        for line in conllfile:

            if not line.strip() and tokens:
                if not "text" in metainfo:
                    metainfo["text"]= ""
                    for tok in tokens:
                        #first token
                        if not metainfo["text"]:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        #token is punctuation
                        elif tok.FORM in punct_l:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        elif tok.FORM in punct_r:
                            metainfo["text"] = metainfo["text"] + " " + tok.FORM
                        #other token
                        else:
                            if metainfo["text"][-1] in punct_r:
                                metainfo["text"] = metainfo["text"] + tok.FORM
                            else:
                                metainfo["text"] = metainfo["text"] + " " + tok.FORM
                sentence = Sentence(**metainfo)
                for tok in tokens:
                    sentence.add_token(tok)
                tokens.clear()
                metainfo.clear()
                doc.add_sent(sentence)

            #Token line
            elif line.strip():
                line = line.strip().split("\t")
                values = dict()
                try:
                    for col in columns:
                        values[col] = line[columns.get(col)]
                    #swapped columns in NEWS-files
                    if "NEWS" in filename:
                        lemma = values["NORM"]
                        values["NORM"] = values["LEMMA"]
                        values["LEMMA"] = lemma
                    #POS-STTS-Mapping
                    if values["POS"] in mapping: values["XPOS"] = mapping[values["POS"]]
                    else: values["XPOS"] = values["POS"]

                    tok = Token(**values)
                    tokens.append(tok)

                except:
                    #uncompleted annotation line with word form ')'
                    if line[0] == ")":
                        sent = doc.sentences[-1]
                        id = int(sent.tokens[-1].ID) + 1
                        for x in range(len(line)):
                            if not line[x]: line[x] = "_"
                        newline = [str(id)] + line
                        for col in columns:
                            try:
                                values[col] = newline[columns.get(col)]
                            except:
                                values[col] = "_"
                        #POS-STTS-Mapping
                        if values["POS"] in mapping: values["XPOS"] = mapping[values["POS"]]
                        else: values["XPOS"] = values["POS"]

                        tok = Token(**values)
                        sent.add_token(tok)
                        sent.text += tok.FORM

                    #uncompleted annotation line
                    elif len(line) == 8:
                        for col in columns_swapped:
                            values[col] = line[columns_swapped.get(col)]
                        values["DEPS"] = "_"
                        values["MISC"] = "_"
                        for file in files_swapped:
                            if file in filename:
                                deprel = values["FORM"]
                                values["FORM"] = values["DEPREL"]
                                values["DEPREL"] = deprel
                                break
                        #POS-STTS-Mapping
                        if values["POS"] in mapping: values["XPOS"] = mapping[values["POS"]]
                        else: values["XPOS"] = values["POS"]

                        tok = Token(**values)
                        tokens.append(tok)

        #If file does not end with empty line
        #save remaining last sentence
        if tokens:
                if not "text" in metainfo:
                    metainfo["text"]= ""
                    for tok in tokens:
                        #first token
                        if not metainfo["text"]:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        #token is punctuation
                        elif tok.FORM in punct_l:
                            metainfo["text"] = metainfo["text"] + tok.FORM
                        elif tok.FORM in punct_r:
                            metainfo["text"] = metainfo["text"] + " " + tok.FORM
                        #other token
                        else:
                            if metainfo["text"][-1] in punct_r:
                                metainfo["text"] = metainfo["text"] + tok.FORM
                            else:
                                metainfo["text"] = metainfo["text"] + " " + tok.FORM
                sentence = Sentence(**metainfo)
                for tok in tokens:
                    sentence.add_token(tok)
                tokens.clear()
                metainfo.clear()
                doc.add_sent(sentence)

        conllfile.close()

        return doc

############################

class TuebaDZPTBImporter(Importer):

    def __init__(self, **kwargs):

        for key,val in kwargs.items():
            self.__dict__[key] = val

    #######################

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

        #Open file
        textfile = open(file, mode="r", encoding="utf-8")

        #Create doc object
        doc = Doc(filename)

        for line in textfile:
            if not line.strip():
                continue

            tree = Tree.from_PTB_string(line.strip())

            sentence = Sentence(**{"tree_object" : tree, "PTBstring": str(tree)})

            #Collect tokens from tree
            terminals = tree.terminals()
            tokens = [t.token for t in terminals]

            #Add toks to sentences
            for tok in tokens:
                sentence.add_token(tok)

            #Add sentence to doc
            doc.add_sent(sentence)

        textfile.close()

        return doc

###########################

class DDBTigerNegraImporter(Importer):

    namespaces = {"default" : "http://www.tei-c.org/ns/1.0"}

    ################################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ################################

    def read_metaheader(self, root):
        """
        Read info from meta document into dictionary.
        Currently included are:
        - filename
        - style
        - title
        - author
        - number of tokens
        - publisher, place and year of publication
        - scope of bibliographic reference
        - original year/place/title
        - source, reference
        - language, language code, language type, language area
        If info not available, value is NA.
        Input: Root from meta document
        Output: Dictionary with meta info
        """
        metainfo = dict()
        header = root.find("./default:teiHeader", namespaces=self.namespaces)

        # style
        try:
            metainfo["style"] = header.attrib["style"]
        except:
            metainfo["style"] = "NA"

        # author
        try:
            authornames = ""
            authors = header.findall("./default:fileDesc/default:titleStmt/default:author", namespaces=self.namespaces)
            for author in authors:
                if authornames: authornames += ", "
                forename = author.find("./default:persName/default:forename", namespaces=self.namespaces)
                if forename == None: forename = author.find("./default:forename", namespaces=self.namespaces)
                if forename.text != "NA":
                    forename_list = forename.text.split()
                    authornames +=  " ".join(forename_list)
                surname = author.find("./default:persName/default:surname", namespaces=self.namespaces)
                if surname == None: surname = author.find("./default:surname", namespaces=self.namespaces)
                if surname.text != "NA":
                    surname_list = surname.text.split()
                    authornames +=  " " + " ".join(surname_list)
            metainfo["author"] = authornames.strip()
        except:
            metainfo["author"] = authornames.strip()
        if not metainfo["author"]: metainfo["author"] = "NA"

        # title
        try:
            title = header.find("./default:fileDesc/default:titleStmt/default:title", namespaces=self.namespaces)
            title_list = title.text.split()
            metainfo["title"] = " ".join(title_list)
        except:
            metainfo["title"] = "NA"

        # tokens
        try:
            metainfo["tokens"] = header.find("./default:fileDesc/default:extent[@type='Tokens']", namespaces=self.namespaces).text.strip()
        except:
            metainfo["tokens"] = "NA"

        # publisher
        try:
            metainfo["publisher"] = header.find("./default:fileDesc/default:publicationStmt/default:publisher", namespaces=self.namespaces).text.strip()
        except:
            metainfo["publisher"] = "NA"

        # place
        try:
            metainfo["place of publication"] = header.find("./default:fileDesc/default:publicationStmt/default:pubPlace", namespaces=self.namespaces).text.strip()
        except:
            metainfo["place of publication"] = "NA"

        # year
        try:
            metainfo["year of publication"] = header.find("./default:fileDesc/default:publicationStmt/default:date", namespaces=self.namespaces).text.strip()
        except:
            metainfo["year of publication"] = "NA"

        # biblScope
        try:
            biblScope = header.find("./default:fileDesc/default:publicationStmt/default:biblScope", namespaces=self.namespaces)
            bibl_list = biblScope.text.split()
            metainfo["biblScope"] = " ".join(bibl_list)
        except:
            metainfo["biblScope"] = "NA"

        # original year
        try:
            origYear = header.find("./default:fileDesc/default:sourceDesc/default:msDesc/default:history/default:origin/default:origDate", namespaces=self.namespaces)
            not_after = origYear.attrib["notAfter-custom"]
            not_before = origYear.attrib["notBefore-custom"]
            if not_after != "NA" and not_before != "NA":
                if int(not_after) > int(not_before):
                    scopeYear = not_before + "-" + not_after
                else:
                    scopeYear = not_after + "-" + not_before
            if origYear.text.strip() != "NA":
                metainfo["original year"] = origYear.text.strip() + " (" + scopeYear + ")"
            else:
                metainfo["original year"] = scopeYear
        except:
            metainfo["original year"] = "NA"

        # original place
        try:
            metainfo["original place"] = header.find("./default:fileDesc/default:sourceDesc/default:msDesc/default:history/default:origin/default:origPlace", namespaces=self.namespaces).text.strip()
        except:
            metainfo["original place"] = "NA"

        # original title
        try:
            metainfo["original title"] = header.find("./default:fileDesc/default:sourceDesc/default:msDesc/default:history/default:origin/default:title", namespaces=self.namespaces).text.strip()
        except:
            metainfo["original title"] = "NA"

        # source
        try:
            source = header.find("./default:fileDesc/default:sourceDesc/default:recordHist/default:source", namespaces=self.namespaces)
            metainfo["source"] = source.attrib["facs"].strip()
        except:
            metainfo["source"] = "NA"

        # reference
        try:
            ref = source.find("./default:ref", namespaces=self.namespaces)
            ref_list = ref.text.split()
            metainfo["reference"] = " ".join(ref_list)
        except:
            metainfo["reference"] = "NA"

        # language, language code
        try:
            langElem = header.find("./default:profileDesc/default:langUsage/default:language[@style='Language']", namespaces=self.namespaces)
            lang_list = langElem.text.split()
            metainfo["language"] = " ".join(lang_list)
            if "ident" in langElem.attrib:
                metainfo["language code"] = langElem.attrib["ident"].strip()
            else:
                metainfo["language code"] = "NA"
        except:
            metainfo["language code"] = "NA"
            metainfo["language"] = "NA"

        # language type
        try:
            langElem = header.find("./default:profileDesc/default:langUsage/default:language[@style='LanguageType']", namespaces=self.namespaces)
            metainfo["language type"] = langElem.text.strip()
        except:
            metainfo["language type"] = "NA"

        # language area
        try:
            langElem = header.find("./default:profileDesc/default:langUsage/default:language[@style='LanguageArea']", namespaces=self.namespaces)
            metainfo["language area"] = langElem.text.strip()
        except:
            metainfo["language area"] = "NA"

        return metainfo

    ################################

    def output_metainfo(self, metainfo, metadir):
        """
        Append metainfo for a given file to a csv-file in metadir.
        Input: Dictionary with meta information, target directory
        """
        metacats = ["filename", "style", "author", "title", "tokens", "publisher", "place of publication", \
                    "year of publication", "biblScope", "original year", "original place", "original title", \
                    "source", "reference", "language", "language code", "language type", "language area"]

        metafile = open(os.path.join(metadir, "DDB_meta_information.csv"), mode="a", encoding="utf-8")

        #Write header if
        if metafile.tell() == 0:
            print("\t".join(metacats), file=metafile)

        for metacat in metacats:
            if metacat not in metainfo: metainfo[metacat] = "NA"

        print("\t".join([metainfo[metacat] for metacat in metacats]), file=metafile)

        metafile.close()

    #######################

    def import_file(self, file, metadir):

        path, filename = os.path.split(file)
        filename = filename.replace("_context", "")

        #metafile
        metapath = path.split("DDB")[0] + "DDB/deutsche-diachrone-baumbank/deutsche-diachrone-baumbank-v1.0TEI-HEADERS/document/"
        metafile = metapath + filename.replace(".S", "")
        metatree = ET.parse(metafile)
        metaroot = metatree.getroot()

        #read metainfo
        metainfo = self.read_metaheader(metaroot)
        metainfo["filename"] = os.path.splitext(filename)[0]
        self.output_metainfo(metainfo, metadir)

        #Read xml tree
        tree = ET.parse(file)
        root = tree.getroot()

        doc = Doc(filename)

        #documents in Negra-format
        if "Hench" in filename:

            for s_elem in root.find("body"):
                #Get graph element
                graph = s_elem.find("graph")
                rootID = graph.attrib["root"]

                discontinuous = graph.attrib.get("discontinuous", False)
                if discontinuous: discontinuous = True

                #Get terminals and nonterminals
                terminals = graph.find("terminals")
                nonterminals = graph.find("nonterminals")

                tokens = []

                for terminal in sorted(terminals, key=lambda t : int(t.attrib["id"].split("_")[-1])):

                    #Get annotations
                    pos = terminal.attrib["pos"]
                    if pos == "--": pos = "_"
                    feats = terminal.attrib["morph"]
                    if feats == "--": feats = "_"

                    #Create token
                    token = Token(**{"FORM" : terminal.attrib["word"],
                                     "POS" : pos,
                                     "XPOS" : pos,
                                     "FEATS" : feats,
                                     "TigerID" : terminal.attrib["id"]})

                    #XPOS tag
                    xpos_tags = {"#": "$(", ",": "$,", ":": "$.", ";": "$.", ".": "$.", "enti": "KON", "auuar": "ADV"}
                    if token.XPOS == "_":
                        if "*" in token.FORM: token.XPOS = "$("
                        else: token.XPOS = xpos_tags.get(token.FORM, "_")
                    tokens.append(token)

                #Create sentence
                sentence = Sentence(tokens, **{"sent_id(Tiger)" : s_elem.attrib["id"]})

                #If there are no non-terminals
                if not len(nonterminals):
                    tree = None

                #Otherwise read syntax tree
                else:
                    root_node = nonterminals.find("nt[@id='"+rootID+"']")
                    tree = Tree(rootID, root_node.attrib["cat"], "--")

                    ###########################

                    def read_tree(node, tree):
                        for edge in node.findall("edge"):
                            edgeID = edge.attrib["idref"]

                            #Non-terminal
                            if len(edgeID.split("_")[1]) == 3 and int(edgeID.split("_")[1][0]) >= 5:
                                nonterminal_node = nonterminals.find("nt[@id='"+edgeID+"']")
                                nonterminal_child = Tree(edgeID, nonterminal_node.attrib["cat"], edge.attrib["label"])
                                read_tree(nonterminal_node, nonterminal_child)
                                tree.add_child(nonterminal_child)

                            #Terminal
                            else:
                                terminal_child = Tree(edgeID, "Tok", edge.attrib["label"],
                                                **{"token" : [tok for tok in sentence.tokens if tok.TigerID == edgeID][0]})
                                tree.add_child(terminal_child)

                    ############################

                    read_tree(root_node, tree)

                sentence.tree = tree
                sentence.__dict__["PTBstring"]= tree.to_string()
                sentence.discontinuous_tree = discontinuous

                if not "text" in sentence.__dict__:
                    sentence.text = " ".join([tok.FORM for tok in sentence.tokens])
                doc.add_sent(sentence)

        #documents in other format
        else:
            columns = ["POS", "CAT", "TENSE", "CONTEXT", "ASPECT", "VOICE"]

            #dictionary with IDs as keys and corresponding annotation-dictionaries as values
            tokens = dict()
            body = root.find("basic-body")
            for tier in body.findall("tier"):

                #get annotations
                cat = tier.attrib["category"]
                for event in tier.findall("event"):
                    start = event.attrib["start"]
                    end = event.attrib["end"]
                    included_end = "T" + str(int(end[1:])-1)
                    anno = event.text
                    #save annotations in dictionary
                    if start not in tokens: tokens[start] = {cat : anno}
                    else:
                        if cat == "cat": anno += "[" + start + "-" + included_end + "]"
                        for id in range(int(start[1:]), int(end[1:])):
                            tokens["T" + str(id)][cat] = anno

            sent = Sentence(**{"text": ""})
            id = 1

            #create tokens
            kwargs = dict()
            for tok_id in tokens:
                if tokens[tok_id]["tok"]:
                    kwargs["ID"] = str(id)
                    kwargs["TimelineID"] = tok_id
                    kwargs["FORM"] = tokens[tok_id]["tok"]
                    kwargs["FEATS"] = tokens[tok_id].get("morph", "_")
                    if kwargs["FEATS"] == "--": kwargs["FEATS"] = "_"
                    for col in columns:
                        kwargs[col] = tokens[tok_id].get(col.lower(), "_")
                        if kwargs[col] == "--": kwargs[col] = "_"
                    token = Token(**kwargs)
                    sent.add_token(token)
                    kwargs.clear()
                    id += 1

                    #XPOS tags
                    if token.POS == "_":
                        if token.FORM in [",", "/"]: token.XPOS = "$,"
                        elif token.FORM in [".", ":"]: token.XPOS = "$."
                        elif token.FORM == "lebent": token.XPOS = "VVFIN"
                    elif token.POS == "FM":
                        if token.FORM in [",", "/"]: token.XPOS = "$,"
                        elif token.FORM in [".", ":"]: token.XPOS = "$."
                        elif token.FORM in ["-"]: token.XPOS = "$("
                        else: token.XPOS = token.POS
                    else:
                        token.XPOS = token.POS

                    #create text
                    if token.FORM not in [".", ":", ",", ";"]: sent.text += " " + token.FORM
                    else: sent.text += token.FORM

                    #end of sentence?
                    if token.XPOS == "$.":
                        sent.text = sent.text.strip()
                        doc.add_sent(sent)
                        sent = Sentence(**{"text": ""})
                        id = 1

            #save remaining last sentence
            if sent.tokens:
                sent.text = sent.text.strip()
                doc.add_sent(sent)

        return doc

############################

class FuerstinnenEXBImporter(Importer):

    namespaces = {"default" : "http://www.tei-c.org/ns/1.0"}

    ################################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ################################

    def read_metaheader(self, root):

        """
        Read info from meta document into dictionary.
        Currently included are:
        - filename
        - style
        - author
        - addressee
        - number of tokens
        - place, date
        - scope of bibliographic reference
        - manuscript name
        - language, language code, language type, language area
        - comment (from exb-file)
        If info not available, value is NA.
        Input: Root from meta document
        Output: Dictionary with meta info
        """
        metainfo = dict()
        header = root.find("./default:teiHeader", namespaces=self.namespaces)

        # style
        try:
            metainfo["style"] = header.attrib["style"]
        except:
            metainfo["style"] = "NA"

        # author
        try:
            authornames = ""
            authors = header.findall("./default:fileDesc/default:titleStmt/default:author", namespaces=self.namespaces)
            for author in authors:
                if authornames: authornames += ", "
                forename = author.find("./default:persName/default:forename", namespaces=self.namespaces)
                if forename.text != "NA":
                    forename_list = forename.text.split()
                    authornames +=  " ".join(forename_list)
                surname = author.find("./default:persName/default:surname", namespaces=self.namespaces)
                if surname.text != "NA":
                    surname_list = surname.text.split()
                    authornames +=  " " + " ".join(surname_list)
            metainfo["author"] = authornames.strip()
        except:
            metainfo["author"] = authornames.strip()
        if not metainfo["author"]: metainfo["author"] = "NA"

        # tokens
        try:
            metainfo["tokens"] = header.find("./default:fileDesc/default:extent[@type='Tokens']", namespaces=self.namespaces).text.strip()
        except:
            metainfo["tokens"] = "NA"

        # place
        try:
            metainfo["place"] = header.find("./default:fileDesc/default:publicationStmt/default:pubPlace", namespaces=self.namespaces).text.strip()
        except:
            metainfo["place"] = "NA"

        # date
        try:
            metainfo["date"] = header.find("./default:fileDesc/default:publicationStmt/default:date", namespaces=self.namespaces).text.strip()
        except:
            metainfo["date"] = "NA"

        # biblScope
        try:
            biblScope = header.find("./default:fileDesc/default:publicationStmt/default:biblScope", namespaces=self.namespaces)
            bibl_list = biblScope.text.split()
            unit = biblScope.attrib["unit"]
            metainfo["biblScope"] = unit + " " + " ".join(bibl_list)
        except:
            metainfo["biblScope"] = "NA"

        # manuscript name
        try:
            msName = header.find("./default:fileDesc/default:sourceDesc/default:msDesc/default:msIdentifier/default:msName", namespaces=self.namespaces)
            msName_list = msName.text.split()
            metainfo["manuscript name"] = " ".join(msName_list)
        except:
            metainfo["manuscript name"] = "NA"

        # language, language code
        try:
            langElem = header.find("./default:profileDesc/default:langUsage/default:language[@style='Language']", namespaces=self.namespaces)
            lang_list = langElem.text.split()
            metainfo["language"] = " ".join(lang_list)
            if "ident" in langElem.attrib:
                metainfo["language code"] = langElem.attrib["ident"].strip()
            else:
                metainfo["language code"] = "NA"
        except:
            metainfo["language code"] = "NA"
            metainfo["language"] = "NA"

        # language type
        try:
            langElem = header.find("./default:profileDesc/default:langUsage/default:language[@style='LanguageType']", namespaces=self.namespaces)
            metainfo["language type"] = langElem.text.strip()
        except:
            metainfo["language type"] = "NA"

        # language area
        try:
            langElem = header.find("./default:profileDesc/default:langUsage/default:language[@style='LanguageArea']", namespaces=self.namespaces)
            metainfo["language area"] = langElem.text.strip()
        except:
            metainfo["language area"] = "NA"

        return metainfo

    ################################

    def output_metainfo(self, metainfo, metadir):
        """
        Append metainfo for a given file to a csv-file in metadir.
        Input: Dictionary with meta information, target directory
        """
        metacats = ["filename", "style", "author", "addressee", "tokens", "place", "date", "biblScope", \
                    "manuscript name", "language", "language code", "language type", "language area", "comment"]

        metafile = open(os.path.join(metadir, "Fuerstinnenkorrespondenz_meta_information.csv"), mode="a", encoding="utf-8")

        #Write header if
        if metafile.tell() == 0:
            print("\t".join(metacats), file=metafile)

        for metacat in metacats:
            if metacat not in metainfo or metainfo[metacat] == "unknown": metainfo[metacat] = "NA"

        print("\t".join([metainfo[metacat] for metacat in metacats]), file=metafile)

        metafile.close()

    ################################

    def import_file(self, file, metadir):

        path, filename = os.path.split(file)

        #Read xml tree
        tree = ET.parse(file)
        root = tree.getroot()

        #metafile
        metapath = path.split("Fuerstinnen_1.1 exb")[0] + "/fuerstinnenkorrespondenz-v1.1TEI-HEADERS/document/"
        metafile = metapath + filename.replace("exb", "xml")
        metatree = ET.parse(metafile)
        metaroot = metatree.getroot()

        #read metainfo
        metainfo = self.read_metaheader(metaroot)
        metainfo["filename"] = os.path.splitext(filename)[0]
        #author, addressee, comment
        try:
            speaker = root.find("./head/speakertable/speaker")
            metainfo["comment"] = speaker.find("./comment").text.strip()
            metainfo["author"] = speaker.find("./ud-speaker-information/ud-information[@attribute-name='pers1']").text.strip()
            metainfo["addressee"] = speaker.find("./ud-speaker-information/ud-information[@attribute-name='pers2']").text.strip()
        except:
            metainfo["comment"] = "NA"
            metainfo["addressee"] = "NA"
        self.output_metainfo(metainfo, metadir)

        doc = Doc(filename)

        columns = []

        #dictionary with timeline-IDs as keys and corresponding annotation-dictionaries as values
        tokens = dict()
        body = root.find("basic-body")

        #timeline-IDs
        timelines = body.find("common-timeline")
        for timeline in timelines:
            tokens[timeline.attrib["id"]] = dict()

        #text+annotations
        for tier in body.findall("tier"):
            cat = tier.attrib["category"]
            if cat not in columns: columns.append(cat)
            for event in tier.findall("event"):
                start = event.attrib["start"]
                end = event.attrib["end"]
                anno = event.text
                #save annotations in dictionary
                started = 0
                for timeline in tokens:
                    if timeline == end:
                        break
                    elif started == 1:
                        tokens[timeline][cat] = anno
                    elif timeline == start:
                        tokens[timeline][cat] = anno
                        started = 1

        sent = Sentence(**{"text": ""})
        id = 1

        #create tokens
        kwargs = dict()
        id = 1
        for timeline in tokens:
            if "text" in tokens[timeline]:
                kwargs["ID"] = str(id)
                kwargs["TimelineID"] = timeline
                kwargs["FORM"] = tokens[timeline]["text"]
                kwargs["FEATS"] = tokens[timeline].get("morph", "_")
                for col in columns:
                    if col not in ["text", "morph"]: kwargs[col.upper()] = tokens[timeline].get(col, "_")
                token = Token(**kwargs)
                sent.add_token(token)
                kwargs.clear()
                id += 1

                #create text
                if token.FORM not in [".", ":", ",", ";"]: sent.text += " " + token.FORM
                else: sent.text += token.FORM

                #end of sentence?
                if token.POS == "$.":
                    sent.text = sent.text.strip()
                    doc.add_sent(sent)
                    sent = Sentence(**{"text": ""})
                    id = 1

        #save remaining last sentence
        if sent.tokens:
            sent.text = sent.text.strip()
            doc.add_sent(sent)

        return doc

############################

class WebAnnoTSVExtrapImporter(Importer):

    ###############################

    def __init__(self, **kwargs):
        for key,val in kwargs.items():
            self.__dict__[key] = val

    ###############################

    def get_columns(self, file):

        colnames = ["TSVID", "CharOffset", "FORM"]

        #Read columns from header
        line = ""
        while not line.strip():
            line = file.__next__()
            if line.strip().startswith("#"):
                
                if "MorphologicalFeatures|" in line:
                    colnames += ["animacy", "aspect", "case", "definiteness", "degree", "gender",
                                 "mood", "negative", "numType", "number", "person", "possessive",
                                 "pronType", "reflex", "tense", "transitivity", "FEATS", "verbForm", "voice"]
                elif "Lemma|value" in line:
                    colnames += ["LEMMA"]
                elif "POS|PosValue|coarseValue" in line:
                    colnames += ["XPOS"]
                    colnames += ["POS"]
                elif "POS|PosValue" in line:
                    colnames += ["XPOS"]
                elif "Chunk|" in line:
                    colnames += ["CHUNK"]
                elif "TopF|TopologicalField" in line:
                    colnames += ["TopF"]
                elif "Dependency|" in line:
                    colnames += ["DEPREL", "DepFlavor", "HEAD"]
                elif "SofaChangeAnnotation|" in line:
                    colnames += ["OrthCorrOp", "OrthCorrReason", "OrthCorr"]
                elif "Bracket|" in line:
                    colnames += ["SentBrcktLink", "SentBrckt", "SentBrcktType"]
                elif "T_SP=webanno.custom.Antezedens|" in line:
                    colnames += ["AntecDepLink", "AntecMovElem", "AntecHeadLink", 
                                 "AntecHead", "AntecHeadLemLink", "AntecHeadLem"]
                elif "T_SP=webanno.custom.Extraposition|" in line:
                    colnames += ["MovElemAntecLink", "MovElemAntec", "MovElemCat", 
                                 "MovElemPos", "RelCType", "MovElemRole", 
                                 "MovElemTyp", "AdvCVPos", "AdvCVHead"]
                elif "Citation|" in line:
                    colnames += ["Cite"]
                line = ""
            else:
                break

        columns = {colname : i for i, colname in enumerate(colnames)}

        return columns

    ###############################

    def import_file(self, file, metadir=None):

        path, filename = os.path.split(file)

        #Open file
        tsvfile = open(file, mode="r", encoding="utf-8")

        #Get columns
        columns = self.get_columns(tsvfile)
        if not columns:
            print("ERROR: Missing column information for {0}.".format(filename))
            return None

        #Create doc object
        doc = Doc(filename)

        tokens = list()
        metainfo = dict()

        for line in tsvfile:

            #Empty line = end of sentence
            if not line.strip() and tokens:

                #Get sent_id(TSV)
                metainfo["sent_id(TSV)"] = tokens[0].TSVID.split("-")[0]

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
                metainfo[line[0].strip().lower()] = "=".join(line[1:]).strip()

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
            #Get sent_id(TSV)
            metainfo["sent_id(TSV)"] = tokens[0].TSVID.split("-")[0]
            if not "text" in metainfo:
                metainfo["text"] = " ".join([tok.FORM for tok in tokens])
            sentence = Sentence(**metainfo)
            for tok in tokens:
                sentence.add_token(tok)
            tokens.clear()
            metainfo.clear()
            doc.add_sent(sentence)

        tsvfile.close()

        return doc

#############################