# -*- coding: utf-8 -*-
'''
Created on 14.10.2019

@author: Katrin Ortmann
'''

import os, re

############################

class Processor(object):

    def __init__(self):
        pass

############################


class DTAChopper(Processor):

    def __init__(self):
        pass

    #####################

    def chop(self, doc):

        s = 0
        while s < len(doc.sentences):
            if not any(tok.MovElemCat != "_" for tok in doc.sentences[s].tokens):
                del doc.sentences[s]
            else:
                s += 1

        pass

    #####################

    def reindex(self, doc):

        charoffset = 0

        for i, sent in enumerate(doc.sentences):
            for tok in sent.tokens:
                #Re-index sentences
                old_sentid = tok.TSVID.split("-")[0]
                new_sentid = str(i+1)
                tok.TSVID = new_sentid + "-" + tok.TSVID.split("-")[-1]

                #Re-index characters
                tokstart = charoffset
                tokend = charoffset + len(tok.FORM)
                tok.CHARS = str(tokstart) + "-" + str(tokend)
                charoffset += len(tok.FORM) + 1

                #Re-index annotations
                for annotation in tok.__dict__:
                    if annotation in ["TSVID", "CHARS", "FORM", "XPOS", "LEMMA", "OrthCorr",
                    "OrthCorrOp", "OrthCorrReason"]:
                        continue
                    tok.__dict__[annotation] = re.sub(old_sentid+r"(-\d+)", new_sentid + r"\1", tok.__dict__[annotation])

    #####################

    def process(self, doc):

        #Remove un-annotated sentences
        self.chop(doc)

        #Re-index sentences and chars
        self.reindex(doc)

        return doc

###########################

class TopFChopper(Processor):

    def __init__(self):
        pass

    #####################

    def chop(self, doc):

        s = 0
        while s < len(doc.sentences):
            if not any(not tok.TopF in ["_", "FRAG"] for tok in doc.sentences[s].tokens):
                del doc.sentences[s]
            else:
                s += 1
        pass

    #####################

    def process(self, doc):

        #Remove un-annotated sentences
        self.chop(doc)

        return doc

###########################

class DTASimplifier(Processor):

    #######################

    def __init__(self):
        self.mapping = {"ID" : "ID",
                        "FORM" : "FORM",
                        "XPOS" : "XPOS",
                        "LEMMA" : "LEMMA",
                        "OrthCorr" : "OrthCorr",
                        "Cite" : "Cite",
                        "AntecMovElem" : "Antec",
                        "AntecHead" : "AntecHead",
                        "SentBrcktType" : "SentBrckt",
                        "MovElemCat" : "MovElem",
                        "MovElemPos" : "MovElemPos",
                        "RelCType" : "RelCType",
                        "AdvCVPos" : "AdvCVPos",
                        "AdvCVHead" : "AdvCVHead"}

    #######################

    def process(self, doc):

        for sent in doc.sentences:
            for tok in sent.tokens:
                #print(tok.__dict__)
                #i = input()
                #Map annotation names and delete unneeded ones
                for annoname in list(tok.__dict__):

                    newname = self.mapping.get(annoname, None)
                    if newname:
                        tok.__dict__[newname] = tok.__dict__[annoname]
                    if newname != annoname:
                        del tok.__dict__[annoname]

                if tok.Antec != "_":
                    if not "|" in tok.Antec and "_" in tok.Antec:
                        tok.Antec = "_"
                    else:
                        tok.Antec = "|".join([re.sub(r"\[\d+\]", "", a).split("-")[-1] for a in tok.Antec.split("|")])

                if tok.AntecHead == "*":
                    tok.AntecHead = "_"
                elif tok.AntecHead != "_":
                    tok.AntecHead = "|".join([a.split("-")[-1] for a in tok.AntecHead.split("|") if not "*" in a])

                if tok.MovElemPos != "_":
                    tok.MovElemPos = "|".join([a for a in tok.MovElemPos.split("|") if not "*" in a])

                if tok.AdvCVPos == "*":
                    tok.AdvCVPos = "_"
                elif tok.AdvCVPos != "_":
                    if not "|" in tok.AdvCVPos and "_" in tok.AdvCVPos:
                        tok.AdvCVPos = "_"
                    else:
                        tok.AdvCVPos = "|".join([a for a in tok.AdvCVPos.split("|") if not "_" in a])
                if not tok.AdvCVPos:
                    tok.AdvCVPos = "_"

                if tok.AdvCVHead == "*":
                    tok.AdvCVHead = "_"
                elif tok.AdvCVHead != "_":
                    tok.AdvCVHead = "|".join([a.split("-")[-1] for a in tok.AdvCVHead.split("|") if not "*" in a])
                if not tok.AdvCVHead:
                    tok.AdvCVHead = "_"

                if "Cite" in tok.__dict__ and tok.Cite != "_":
                    tok.Cite = "|".join([a.replace("*", "cite") for a in tok.Cite.split("|")])
                #print(tok.__dict__)
                #i = input()
        return doc

############################

class HIPKONtoSTTSMapper(Processor):

    def __init__(self):
        pass

    #####################

    def process(self, doc):

        filedir = "./../res"
        file = open(os.path.join(filedir, "HIPKON-STTS.txt"), mode="r", encoding="utf-8")

        #dictionary "HIPKON" : "STTS"
        tags = dict()
        for line in file:
            hipkon, stts = line.strip().split()
            tags[hipkon] = stts

        file.close()

        punct = [".", ":", "!", "?", ";"]
        comma = [",", "/"]
        other = ["(", ")", "[", "]", "-", '"', "'", "„"]
        #dictionary for used rules
        rules = dict()
        rules["$_"] = list()
        rules["ſ"] = list()

        for sent in doc.sentences:
            for tok in sent.tokens:

                if tok.POS != "_":
                    #punctuation
                    if tok.POS == "$_":
                        if tok.FORM in punct:
                            tok.__dict__["XPOS"] = "$."
                            if "$." not in rules["$_"]:
                                rules["$_"].append("$.")
                        elif tok.FORM in comma:
                            tok.__dict__["XPOS"] = "$,"
                            if "$," not in rules["$_"]:
                                rules["$_"].append("$,")
                        else:
                            tok.__dict__["XPOS"] = "$("
                            if "$(" not in rules["$_"]:
                                rules["$_"].append("$(")
                    #other
                    else:
                        try:
                            tok.__dict__["XPOS"] = tags[tok.POS]
                            rules[tok.POS] = tags[tok.POS]
                        except:
                            if tok.FORM in punct:
                                tok.__dict__["XPOS"] = "$."
                                if "$." not in rules["ſ"]:
                                    rules["ſ"].append("$.")
                            elif tok.FORM in comma:
                                tok.__dict__["XPOS"] = "$,"
                                if "$," not in rules["ſ"]:
                                    rules["ſ"].append("$,")
                            elif tok.FORM in other:
                                tok.__dict__["XPOS"] = "$("
                                if "$(" not in rules["ſ"]:
                                    rules["ſ"].append("$(")
                            else:
                                tok.__dict__["XPOS"] = "FEHLER"
                                print("FEHLER")
                else:
                    #punctuation?
                    if tok.FORM in punct:
                        tok.__dict__["XPOS"] = "$."
                    elif tok.FORM in comma:
                        tok.__dict__["XPOS"] = "$,"
                    elif tok.FORM in other:
                        tok.__dict__["XPOS"] = "$("

                    #missing tag
                    else:
                        info = dict()
                        info["Token"] = tok.FORM
                        info["Filename"] = doc.filename[:-4]
                        info["sent_id"] = sent.sent_id
                        info["tok_id"] = tok.ID

                        #output: list of token without tag
                        cats = ["Token", "Filename", "sent_id", "tok_id"]
                        missing_tags = open(os.path.join(filedir, "hipkon_missing_tags.csv"), mode="a", encoding="utf-8")
                        #Write header if
                        if missing_tags.tell() == 0:
                            print("\t".join(info), file=missing_tags)
                        print("\t".join([info[cat] for cat in cats]), file=missing_tags)
                        missing_tags.close()

        #output: list of rules which were used
        cats = ["POS", "STTS"]
        used_rules = open(os.path.join(filedir, "rules_" + doc.filename), mode="a", encoding="utf-8")
        #Write header if
        if used_rules.tell() == 0:
            print("\t".join(cats), file=used_rules)
        if rules["$_"]:
            print("$_" + "\t" + " ".join([rule for rule in rules["$_"]]), file=used_rules)
        if rules["ſ"]:
            print("ſ" + "\t" + " ".join([rule for rule in rules["ſ"]]), file=used_rules)
        for rule in tags:
            if rule in rules:
                print(rule + "\t" + rules[rule], file=used_rules)
        used_rules.close()

        return doc

############################

class addmissingSTTStoHIPKON(Processor):

    def __init__(self):
        pass

    #####################

    def process(self, doc):

        filedir = "./../res"
        missing_stts = open(os.path.join(filedir, "hipkon_missing_stts.csv"), mode="r", encoding="utf-8")

        for line in missing_stts:
            token, filename, sent_id, tok_id, stts = line.strip().split()
            if doc.filename[:-4] == filename:
                sent = doc.sentences[int(sent_id)-1]
                tok = sent.tokens[int(tok_id)-1]
                if tok.FORM == token:
                    tok.__dict__["XPOS"] = stts
                else:
                    print("FEHLER")

        missing_stts.close()

        return doc

###########################

class TopFSimplifier(Processor):

    def __init__(self):
        self.mapping = {"ID" : "ID",
                        "FORM" : "FORM",
                        "XPOS" : "XPOS",
                        "LEMMA" : "LEMMA",
                        "FEATS" : "FEATS",
                        "DEPREL" : "DEPREL",
                        "HEAD" : "HEAD",
                        "CHUNK" : "CHUNK",
                        "TopF" : "TopF"}

    #####################

    def process(self, doc):

        for sent in doc.sentences:
            for tok in sent.tokens:

                #Map annotation names and delete unneeded ones
                for annoname in list(tok.__dict__):

                    newname = self.mapping.get(annoname, None)
                    if newname:
                        tok.__dict__[newname] = tok.__dict__[annoname]
                    if newname != annoname:
                        del tok.__dict__[annoname]

                #Remove backslash escapes from FEAT
                if tok.__dict__.get("FEATS", None):
                    tok.FEATS = re.sub(r"\\", "", tok.FEATS)

                #Simplify TopF column
                TopF = ""
                annotations = tok.TopF.split("|")
                if len(annotations) == 1:
                    if annotations[0] == "_" or not "[" in annotations[0]:
                        pass
                    else:
                        tok.TopF = re.sub(r"\[\d+\]", "", annotations[0])
                else:
                    sorted_annotations = []
                    for a in annotations:
                        field = a.split("[")[0]
                        number = a.split("[")[-1].rstrip("]")
                        try:
                            number = int(number)
                        except:
                            number = 99999
                        sorted_annotations.append((field, number))
                    sorted_annotations.sort(key=lambda l: int(l[1]))
                    tok.TopF = "-".join([a for a,i in sorted_annotations])

                #Create Sentence Bracket Column
                tok.__dict__["SentBrckt"] = ""
                for anno in tok.TopF.split("-"):
                    if anno in ["LK", "RK"]:
                        if tok.SentBrckt:
                            tok.__dict__["SentBrckt"] += "-" + anno
                        else:
                            tok.__dict__["SentBrckt"] += anno
                if not tok.SentBrckt:
                    tok.__dict__["SentBrckt"] = "_"

                #Strip sentID from depHead
                if tok.__dict__.get("HEAD", None) and tok.HEAD != "_":
                    tok.HEAD = tok.HEAD.split("-")[-1]

        return doc

################################

class SATZKLAMMERtoTopF(Processor):

    ######################

    def __init__(self):
        self.mapping = {"LI" : "LK", "RE" : "RK", "_" : "_"}

    ######################

    def process(self, doc):

        topfID = 1
        for sent in doc.sentences:
            openbracket = ""

            for i,tok in enumerate(sent.tokens):
                if tok.SATZKLAMMER != "_":
                    if openbracket:
                        #Bracket continues
                        if openbracket.startswith(self.mapping.get(tok.SATZKLAMMER, "_")):
                            if not "[" in openbracket:
                                openbracket = openbracket + "[" + str(topfID) + "]"
                                sent.tokens[i-1].TopF = openbracket
                            tok.TopF = openbracket
                        #New bracket
                        else:
                            if "[" in openbracket: topfID += 1
                            openbracket = ""
                            openbracket = self.mapping.get(tok.SATZKLAMMER, "_")
                            tok.TopF = self.mapping.get(tok.SATZKLAMMER, "_")
                    #New bracket
                    else:
                        openbracket = self.mapping.get(tok.SATZKLAMMER, "_")
                        tok.TopF = self.mapping.get(tok.SATZKLAMMER, "_")
                #No bracket
                else:
                    #End previous bracket
                    if openbracket:
                        if "[" in openbracket: topfID += 1
                        openbracket = ""
                    tok.TopF = "_"
        return doc

###############################

class TSVIndexer(Processor):

    def __init__(self):
        pass

    def process(self, doc):

        charoffset = 0

        for i, sent in enumerate(doc.sentences):
            for j, tok in enumerate(sent.tokens):
                #Re-index sentences
                new_sentid = str(i+1)
                new_tokid = str(j+1)
                tok.TSVID = new_sentid + "-" + new_tokid

                #Re-index characters
                tokstart = charoffset
                tokend = charoffset + len(tok.FORM)
                tok.CHARS = str(tokstart) + "-" + str(tokend)
                charoffset += len(tok.FORM) + 1

            charoffset += 1

            #Add spaces to text, so WebAnno finds the tokens
            sent.text = " ".join([tok.FORM for tok in sent.tokens])

        return doc

#######################

class CoNLLUPLUSIndexer(Processor):

    def __init__(self):
        pass

    def process(self, doc):

        for i, sent in enumerate(doc.sentences):
            for j, tok in enumerate(sent.tokens):
                tok.ID = str(j + 1)
            sent.sent_id = str(i + 1)

        return doc

############################

class HiTStoSTTSMapper(Processor):

    def __init__(self):
        pass

    #####################

    def process(self, doc):

        file = open("./../res/HiTS_STTS_mapping.csv", mode="r", encoding="utf-8")

        #dictionary {"pos" : {"posLemma" : "STTS"}}
        tags = dict()
        for line in file:
            line = line.strip().split("\t")
            if line[0] in tags:
                tags[line[0]][line[1]] = line[4]
            else:
                tags[line[0]] = {line[1] : line[4]}

        file.close()

        punct = [":", "!", "?", ";"]
        comma = [",", "/", "//"]
        other = ["(", ")", "[", "]", "-", '"', "'", "„"]

        for sent in doc.sentences:
            for tok in sent.tokens:

                if "-" not in tok.ID:

                    #punctuation
                    if tok.POS == "$_":
                        #look up tok.FORM and punc-annotation
                        if tok.FORM in [".", "·"]:
                            if tok.PUNC == "$E":
                                tok.__dict__["XPOS"] = "$."
                            else:
                                tok.__dict__["XPOS"] = "$,"
                        elif tok.FORM in punct:
                            tok.__dict__["XPOS"] = "$."
                        elif tok.FORM in comma:
                            tok.__dict__["XPOS"] = "$,"
                        elif tok.FORM in other:
                            tok.__dict__["XPOS"] = "$("

                    #other
                    elif tok.POS == "_":
                        if tok.POS_GEN == "_":
                            tok.__dict__["XPOS"] = tags["--"]["--"]
                        else:
                            tok.__dict__["XPOS"] = tags["--"][tok.POS_GEN]

                    else:
                        tok.__dict__["XPOS"] = tags[tok.POS][tok.POS_GEN]

        return doc

###################################

class TUEBADSTopFExtractor(Processor):

    def __init__(self):
        self.tuebatagset = ["LV", "VF", "LK", "C", "MF", "MFE",
                            "VC", "VCE", "NF", "KOORD", "PARORD", "FKOORD"]

    def process(self, doc):
        for sent in doc.sentences:

            open_fields = []

            #Move HD info from POS column to new col
            for tok in sent.tokens:
                head = tok.__dict__.get("POS:HD", "_")
                if head != "_" and not ":HD" in head:
                    head = "_"
                elif head != "_":
                    head = "HD"
                tok.__dict__["PHRASE:HEAD"] = head
                tok.__dict__["POS:HD"] = "_"

                #Read topological fields from syntax col
                syntax = tok.__dict__.get("SYNTAX", "_")

                #Add open fields to token annotation
                tok.__dict__["TopoField"] = ""
                for field in open_fields:
                    if field in self.tuebatagset:
                        if tok.TopoField: tok.TopoField += "-" + field
                        else: tok.TopoField = field

                #Analyze token's own syntax annotation
                if syntax:
                    syntax = syntax.replace("(", " (").replace(")", " )")#re.sub(r"\(", r" \(", syntax)
                    #syntax = re.sub(r"\)", r" \)", syntax)
                    syntax = syntax.split()
                    for node in syntax:
                        if node.strip() in ["*", "_"]:
                            continue
                        #End of node
                        elif node.strip() == ")":
                            open_fields = open_fields[:-1]
                        #New node
                        else:
                            node = node.strip().replace("(", "").replace("*", "")
                            if ":" in node:
                                node = node.split(":")[0]
                            open_fields.append(node)
                            if node in self.tuebatagset:
                                if tok.TopoField:
                                    tok.TopoField += "-" + node
                                else:
                                    tok.TopoField = node

                if not tok.TopoField: tok.TopoField = "_"

        return doc

#############################

def map_tueba_tagset(orig_folder, target_folder):
    from importer import CoNLLUPlusImporter
    from exporter import CoNLLUPlusExporter

    for of in [os.path.join(orig_folder, f) for f in os.listdir(orig_folder)]:
        doc = CoNLLUPlusImporter().import_file(of)
        doc = TUEBATopFSimplifier().process(doc)
        CoNLLUPlusExporter().export(doc, target_folder)

############################

def convert_tuebads(indir, outdir):
    from importer import TUEBADSConllImporter
    from exporter import CoNLLUPlusExporter

    for conllfile in [os.path.join(indir, f) for f in os.listdir(indir)]:
        doc = TUEBADSConllImporter().import_file(conllfile)
        doc = TUEBADSTopFExtractor().process(doc)
        CoNLLUPlusExporter().export(doc, outdir)

############################

def find_ANNIS_matches(grid_file, conll_folder, outdir):

    from importer import CoNLLUPlusImporter
    from exporter import DTATSVExporter, CoNLLUPlusExporter
    from document import Doc

    #Import grid file
    grid = open(grid_file, mode="r", encoding="utf-8").readlines()

    matches = dict()
    n = 0
    for line in grid:
        if not line.strip() or line.strip() == "finished":
            if not n+1 in matches:
                n += 1
        else:
            line = line.split("\t")
            if not n in matches:
                matches[n] = {line[1] : line[2].strip()}
            else:
                matches[n][line[1]] = line[2].strip()

    #For each annis match import coresponding conll file
    conll = None
    doc = None
    for _, match in sorted(matches.items()):
        filename = match["meta::annis:doc"]
        #If match is from same file as previous one
        if conll and conll.filename.startswith(filename):
            #Continue with same conll and output doc
            pass
        #Match from a new file
        else:
            #Export previous doc
            if doc:
                TSVIndexer().process(doc)
                if not os.path.isdir(os.path.join(outdir, "tsv")):
                    os.makedirs(os.path.join(outdir, "tsv"))
                if not os.path.isdir(os.path.join(outdir, "conllup")):
                    os.makedirs(os.path.join(outdir, "conllup"))
                DTATSVExporter().export(doc, os.path.join(outdir, "tsv"))
                CoNLLUPlusExporter().export(doc, os.path.join(outdir, "conllup"))
            #Import conll
            conll = CoNLLUPlusImporter().import_file(os.path.join(conll_folder, filename+".conllup"))
            #Create output doc
            doc = Doc(filename)

        #Get matched token sequence
        tok_annos = [re.sub(r"\[\d+-\d+\]$", "", t) for t in match["tok_anno"].split()]
        middle_tok = tok_annos[(len(tok_annos)-1)//2]
        if (len(tok_annos)-1)//2-5 >= 0:
            prev_5_toks = tok_annos[(len(tok_annos)-1)//2-5:(len(tok_annos)-1)//2]
        else:
            prev_5_toks = tok_annos[:(len(tok_annos)-1)//2]
        prev_5_toks.reverse()
        try:
            next_5_toks = tok_annos[(len(tok_annos)-1)//2+1:(len(tok_annos)-1)//2+6]
        except IndexError:
            try:
                next_5_toks = tok_annos[(len(tok_annos)-1)//2+1:]
            except IndexError:
                next_5_toks = []


        #Search for token sequence in conll
        for sent in conll.sentences:
            hits = [t for t in sent.tokens if t.ANNO_ASCII == middle_tok]

            #Every time the search word appears in a sentence
            for hit in hits:

                contains_previous_toks = True
                contains_following_toks = True

                #Check previous tokens
                prev_forms = [t.ANNO_ASCII for t in sent.tokens[:sent.tokens.index(hit)]]
                prev_forms.reverse()

                if not prev_forms or not prev_5_toks:
                    contains_previous_toks = False
                else:
                    for prev_tok,prev_form in zip(prev_5_toks, prev_forms):
                        if prev_tok != prev_form:
                            contains_previous_toks = False
                            break

                #Check following tokens
                if len(sent.tokens) > sent.tokens.index(hit)+1:
                    next_forms = [t.ANNO_ASCII for t in sent.tokens[sent.tokens.index(hit)+1:]]
                else:
                    next_forms = []

                if not next_forms or not next_5_toks:
                    contains_following_toks = False
                else:
                    for next_tok,next_form in zip(next_5_toks, next_forms):
                        if next_tok != next_form:
                            contains_following_toks = False
                            break

                #Add sentence(s) to doc
                if contains_previous_toks or contains_following_toks:
                    if not sent in doc.sentences:
                        doc.sentences.append(sent)
                        for tok in doc.sentences[-1].tokens:
                            tok.XPOS = tok.POS
                    break

    if doc:
        TSVIndexer().process(doc)
        if not os.path.isdir(os.path.join(outdir, "tsv")):
            os.makedirs(os.path.join(outdir, "tsv"))
        if not os.path.isdir(os.path.join(outdir, "conllup")):
            os.makedirs(os.path.join(outdir, "conllup"))
        DTATSVExporter().export(doc, os.path.join(outdir, "tsv"))
        CoNLLUPlusExporter().export(doc, os.path.join(outdir, "conllup"))

############################

class ANSELMtoSTTSMapper(Processor):

    def __init__(self):
        pass

    #####################

    def process(self, doc):

        file = open("./../res/Anselm_pos_tags.csv", mode="r", encoding="utf-8")

        #dictionary {"Anselm" : "STTS"}
        tags = dict()
        for line in file:
            anselm, stts = line.strip().split("\t")
            tags[anselm] = stts
        tags["_"] = "_"
        file.close()

        for sent in doc.sentences:
            for tok in sent.tokens:
                tok.__dict__["XPOS"] = tags[tok.POS]

        return doc

############################

class ReFHiTStoSTTSMapper(Processor):

    def __init__(self):
        pass

    #####################

    def process(self, doc):

        file = open("./../res/ReF_HiTS-STTS_mapping.csv", mode="r", encoding="utf-8")

        #dictionary {"pos" : {"posLemma" : "STTS"}}
        tags = dict()
        for line in file:
            line = line.strip().split("\t")
            if line[0] in tags:
                tags[line[0]][line[1]] = line[2]
            else:
                tags[line[0]] = {line[1] : line[2]}
        tags["_"] = {"_" : "_"}
        file.close()

        punct = [":", "!", "?", ";"]
        comma = [","]

        for sent in doc.sentences:
            for i, tok in enumerate(sent.tokens):

                if "-" not in tok.ID:

                    del tok.__dict__["XPOS"]

                    #punctuation
                    if tok.POS == "$_":
                        #look up tok.FORM and boundary-tag
                        if tok.FORM in [".", "·", "/"]:
                            if "." in tok.__dict__.get("BOUNDARY", ""):
                                tok.__dict__["XPOS"] = "$."
                            elif "," in tok.__dict__.get("BOUNDARY", ""):
                                tok.__dict__["XPOS"] = "$,"
                            else:
                                for punc in punct:
                                    if punc in tok.__dict__.get("BOUNDARY", ""):
                                        tok.__dict__["XPOS"] = "$."
                        elif tok.FORM in punct:
                            tok.__dict__["XPOS"] = "$."
                        elif tok.FORM in comma:
                            tok.__dict__["XPOS"] = "$,"

                        if "XPOS" not in tok.__dict__:
                            if i == len(sent.tokens)-1:
                                tok.__dict__["XPOS"] = "$."
                            else:
                                tok.__dict__["XPOS"] = "$,"

                    #other
                    elif tok.POS == "DRELS":
                        tok_id = int(tok.ID)
                        for token in sent.tokens:
                            if token.ID == str(tok_id + 1):
                                if tags[token.POS][token.POS_LEMMA] in ["ADJA", "NN"]:
                                    tok.__dict__["XPOS"] = "PRELAT"
                                else:
                                    tok.__dict__["XPOS"] = "PRELS"

                    elif tok.POS == "PW":
                        tok_id = int(tok.ID)
                        for token in sent.tokens:
                            if token.ID == str(tok_id + 1):
                                if tags[token.POS][token.POS_LEMMA] in ["ADJA", "NN"]:
                                    tok.__dict__["XPOS"] = "PWAT"
                                else:
                                    tok.__dict__["XPOS"] = "PWS"

                    else:
                        tok.__dict__["XPOS"] = tags[tok.POS][tok.POS_LEMMA]

        return doc

############################

class MercuriusToSTTSMapper(Processor):

    def __init__(self):
        pass

    #####################

    def process(self, doc):

        filedir = "./../res"
        file = open(os.path.join(filedir, "mercurius_STTS.csv"), mode="r", encoding="utf-8")

        #dictionary "Mercurius" : "STTS"
        tags = dict()
        for line in file:
            mercurius, stts, comments = line.strip().split("\t")
            tags[mercurius] = stts

        file.close()

        for sent in doc.sentences:
            for i, tok in enumerate(sent.tokens):

                if tok.POS != "_":
                    stts = tags.get(tok.POS, None)

                    if stts:

                        #Virgel
                        if stts == "$(" and tok.FORM == "/":
                            tok.XPOS = "$,"

                        #For compounds
                        elif stts == "#" and tok.POS == "KOMPE":

                            #Get STTS of next token
                            if i < len(sent.tokens)-1:
                                j = i
                                nextstts = None
                                while j < len(sent.tokens)-1 and (nextstts is None or nextstts == "#"):
                                    nexttok = sent.tokens[j+1]
                                    nextstts = tags.get(nexttok.POS, None)
                                    j += 1

                                if not nextstts or nextstts == "#":
                                    print("POS", nextstts, "of token", tok.ID, "in sentence", sent.sent_id, "after KOMPE is not in mapping.")
                                    tok.XPOS = "NN"

                                #And assign it to all compound parts
                                else:
                                    tok.XPOS = nextstts

                            else:
                                print("KOMPE is last token in sentence.")
                                tok.XPOS = "NN"
                        else:
                            tok.XPOS = stts

                    else:
                        print("Not in mapping:", tok.POS)

                else:
                    print("Token", tok.ID, tok.FORM, "in sentence", sent.sent_id, "in doc", doc.filename, "not annotated")
                    tok.XPOS = "XY"

        return doc

############################

class ReFUPToSTTSMapper(Processor):

    def __init__(self):
        pass

    #####################

    def process(self, doc):

        filedir = "./../res"
        file = open(os.path.join(filedir, "ReF-UP-STTS.csv"), mode="r", encoding="utf-8")

        #dictionary "ReF.UP" : "STTS"
        tags = dict()
        for line in file:
            if "POS" in line and "STTS" in line:
                continue
            refup = line.strip().split("\t")[0]
            stts = line.strip().split("\t")[1]
            tags[refup] = stts

        file.close()

        for sent in doc.sentences:
            for t, tok in enumerate(sent.tokens):

                if tok.POS != "_":
                    stts = tags.get(tok.POS, None)

                    if stts:
                        if stts.startswith("$") and tok.POS in ["$MK", "$MSBI", "$QL", "$QR"] \
                           and t > 0 and sent.tokens[t-1].XPOS.startswith("$"):
                            sent.tokens[t-1].XPOS = stts

                        tok.XPOS = stts

                    else:
                        print("Not in mapping:", tok.POS)

                else:
                    print("Token", tok.ID, tok.FORM, "in sentence", sent.sent_id, "in doc", doc.filename, "not annotated")
                    tok.XPOS = "XY"

        return doc

############################

class FuerstinnentoSTTSMapper(Processor):

    def __init__(self):
        pass

    #####################

    def process(self, doc):

        file = open("./../res/Fuerstinnen_STTS.csv", mode="r", encoding="utf-8")

        #dictionary {"POS" : "STTS"}
        tags = dict()
        for line in file:
            pos, stts = line.strip().split("\t")
            tags[pos] = stts
        file.close()

        for sent in doc.sentences:
            for tok in sent.tokens:

                if tok.__dict__["POS"] == "_":
                    if tok.__dict__["LEMMA"] == "_":
                        tok.__dict__["XPOS"] = "XY"
                        tok.__dict__["LEMMA"] = "#"
                    else:
                        tok.__dict__["XPOS"] = "XY"

                else:
                    tok.__dict__["XPOS"] = tags[tok.POS]

        return doc

############################

class VirgelMapper(Processor):

    def __init__(self):
        pass

    #####################

    def process(self, doc):

        for sent in doc.sentences:
            for tok in sent.tokens:

                if tok.__dict__["FORM"] == "/":
                    tok.__dict__["XPOS"] = "$("

        return doc

############################

class PronominalAdverbMapper(Processor):

    def __init__(self):
        pass

    #####################

    def process(self, doc):

        for sent in doc.sentences:
            for tok in sent.tokens:

                if tok.__dict__["XPOS"] in ["PROAV", "PROP"]:
                    tok.__dict__["XPOS"] = "PAV"

        return doc

############################

class ReFUPCoding(Processor):

    def __init__(self):
        pass

    #####################

    def process(self, doc):

        for sent in doc.sentences:
            for tok in sent.tokens:

                if "Ã" in tok.__dict__["FORM"]:
                    #print(tok.__dict__["FORM"])
                    tok.__dict__["FORM"] = tok.__dict__["FORM"].replace("Ã", "ß")

            sent.text = " ".join([tok.FORM for tok in sent.tokens])

        return doc

############################

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
                        if b in tok.FORM: tok.FORM = tok.FORM.replace(b, "")

        return doc

########################

class TSVtoBIOProcessor(Processor):

    def __init__(self):
        pass

    ##################

    def process(self, doc, annotation, empty_annotation="O"):

        for sent in doc.sentences:
            sent = self.process_sentence(sent, annotation, empty_annotation)

        return doc

    ##################

    def process_sentence(self, sentence, annotation, empty_annotation="O"):

        #Special handling of extrap/antec annotation
        if annotation == "Extrap/Antec":
            sentence = self.process_extrap_antec(sentence)
            return sentence
        
        #Special handling of extrap/antec annotation
        elif annotation == "Citation":
            sentence = self.process_citation(sentence)
            return sentence

        anno_stack = []

        #For each token
        for tok in sentence.tokens:

            #Token not annotated
            if tok.__dict__.get(annotation, "_") == "_":
                #Reset phrase stack
                tok.__dict__[annotation] = empty_annotation
                anno_stack = []
                continue
                                
            #Token is annotated
            annos = tok.__dict__.get(annotation, "_").split("|")
            bio_annotation = []

            #Cut stack to same level as current annos
            if len(anno_stack) > len(annos):
                anno_stack = anno_stack[:len(annos)]

            for i in range(len(annos)):
                #There are previous annotations
                if anno_stack:
                    #This is on the same level as previous annotations
                    if i < len(anno_stack):
                        #The annotation continues
                        if annos[i] == anno_stack[i]:
                            bio_annotation.append("I-"+annos[i].split("[")[0])
                        #The previous annotation ends and a new one begins
                        else:
                            anno_stack = anno_stack[:i]
                            anno_stack.append(annos[i])
                            bio_annotation.append("B-"+annos[i].split("[")[0])
                    #New level annotation
                    else:
                        anno_stack.append(annos[i])
                        bio_annotation.append("B-"+annos[i].split("[")[0])
                #No previous annotations
                else:
                    anno_stack.append(annos[i])
                    bio_annotation.append("B-"+annos[i].split("[")[0])

            tok.__dict__[annotation] = "|".join(bio_annotation)

        return sentence    

    #######################

    def process_citation(self, sentence):
        citeStack = ""

        for tok in sentence.tokens:
            if tok.__dict__.get("Cite", "_") == "_":
                tok.Cite = "_"
                citeStack = ""
            else:
                if citeStack:
                    if tok.Cite == citeStack:
                        tok.Cite = "I-Citation"
                    else:
                        citeStack = tok.Cite
                        tok.Cite = "B-Citation"
                else:
                    citeStack = tok.Cite
                    tok.Cite = "B-Citation"
        
        return sentence
                    
    #######################

    def process_extrap_antec(self, sentence):

        movElemStack = []
        antecStack = []

        ID = 1

        #For each token
        for tok in sentence.tokens:

            #Token not a MovElem
            if tok.__dict__.get("MovElemCat", "_") == "_" :
                #Reset movElem stack
                movElemStack = []

            #Token is a MovElem
            else:
                annos = tok.__dict__.get("MovElemCat", "_").split("|")
                positions = tok.__dict__.get("MovElemPos", "_").split("|")
                vpos = tok.__dict__.get("AdvCVPos", "_").split("|")
                movElem_annotation = []

                #Cut stack to anno length
                if len(movElemStack) > len(annos):
                    movElemStack = movElemStack[:len(annos)]

                for i in range(len(annos)):
                        
                    #There already are annos
                    if movElemStack:
                        #Same level anno
                        if i < len(movElemStack):
                            #Continued MovElem
                            if movElemStack[i] == annos[i]:
                                if annos[i].split("[")[0] == "ADVC" and tok.__dict__.get("AdvCVHead", "_") == "head":
                                    movElem_annotation.append("I-"+annos[i].split("[")[0]+"-Head")
                                else:
                                    movElem_annotation.append("I-"+annos[i].split("[")[0])

                            #End of previous elem and start of new one
                            else:
                                movElemStack = movElemStack[:i]
                                movElemStack.append(annos[i])
                                if annos[i].split("[")[0] == "ADVC":
                                    if "[" in annos[i] \
                                       and any("["+annos[i].split("[")[1] in antec.__dict__.get("AntecMovElem", "_") for antec in sentence.tokens):
                                        movElem_annotation.append("B-"+annos[i].split("[")[0]+"-"+vpos[i].split("[")[0]+"-"+str(ID))
                                        ID += 1
                                    else:
                                        movElem_annotation.append("B-"+annos[i].split("[")[0]+"-"+vpos[i].split("[")[0])
                                elif annos[i].split("[")[0] in ["RELC", "CMPP"] \
                                    or ("[" in annos[i] and 
                                        any("["+annos[i].split("[")[1] in antec.__dict__.get("AntecMovElem", "_") for antec in sentence.tokens)):
                                    movElem_annotation.append("B-"+annos[i].split("[")[0]+"-"+positions[i].split("[")[0]+"-"+str(ID))
                                    ID += 1
                                else:
                                    movElem_annotation.append("B-"+annos[i].split("[")[0]+"-"+positions[i].split("[")[0])
                        #New level MovElem
                        else:
                            movElemStack.append(annos[i])
                            if annos[i].split("[")[0] == "ADVC":
                                if "[" in annos[i] \
                                   and any("["+annos[i].split("[")[1] in antec.__dict__.get("AntecMovElem", "_") for antec in sentence.tokens):
                                    movElem_annotation.append("B-"+annos[i].split("[")[0]+"-"+vpos[i].split("[")[0]+"-"+str(ID))
                                    ID += 1
                                else:
                                    movElem_annotation.append("B-"+annos[i].split("[")[0]+"-"+vpos[i].split("[")[0])
                            elif annos[i].split("[")[0] in ["RELC", "CMPP"] \
                                or ("[" in annos[i] and 
                                    any("["+annos[i].split("[")[1] in antec.__dict__.get("AntecMovElem", "_") for antec in sentence.tokens)):
                                movElem_annotation.append("B-"+annos[i].split("[")[0]+"-"+positions[i].split("[")[0]+"-"+str(ID))
                                ID += 1
                            else:
                                movElem_annotation.append("B-"+annos[i].split("[")[0]+"-"+positions[i].split("[")[0])
                    #Start of MovElem
                    else:
                        movElemStack.append(annos[i])
                        if annos[i].split("[")[0] == "ADVC":
                            if "[" in annos[i] \
                               and any("["+annos[i].split("[")[1] in antec.__dict__.get("AntecMovElem", "_") for antec in sentence.tokens):
                                movElem_annotation.append("B-"+annos[i].split("[")[0]+"-"+vpos[i].split("[")[0]+"-"+str(ID))
                                ID += 1
                            else:
                                movElem_annotation.append("B-"+annos[i].split("[")[0]+"-"+vpos[i].split("[")[0])
                        elif annos[i].split("[")[0] in ["RELC", "CMPP"] \
                            or ("[" in annos[i] and 
                                any("["+annos[i].split("[")[1] in antec.__dict__.get("AntecMovElem", "_") for antec in sentence.tokens)):
                            movElem_annotation.append("B-"+annos[i].split("[")[0]+"-"+positions[i].split("[")[0]+"-"+str(ID))
                            ID += 1
                        else:
                            movElem_annotation.append("B-"+annos[i].split("[")[0]+"-"+positions[i].split("[")[0])

                tok.MovElem = "|".join(movElem_annotation)

            #Token not an Antec
            if tok.__dict__.get("AntecMovElem", "_") == "_":
                #Reset Antec stack
                antecStack = []

            #Token is an Antec
            else:
                if "|" in tok.__dict__.get("AntecMovElem", "_"):
                    antec_annos = tok.__dict__.get("AntecMovElem", "_").split("|")
                else:
                    antec_annos = tok.__dict__.get("AntecMovElem", "_").split(";")
                antec_annotation = []

                #Cut stackt to anno length
                if len(antecStack) > len(antec_annos):
                    antecStack = antecStack[:len(antec_annos)]

                for i in range(len(antec_annos)):
                    #There already are antecs
                    if antecStack:
                        #Same level antec
                        if i < len(antecStack):
                            #Continued antec
                            if antecStack[i] == antec_annos[i]:
                                if tok.__dict__.get("AntecHead", "_") == "head":
                                    antec_annotation.append("I-Antec-Head")
                                else:
                                    antec_annotation.append("I-Antec")
                            #End of previous antec and start of new one
                            else:
                                antecStack = antecStack[:i]
                                antecStack.append(antec_annos[i])
                                if tok.__dict__.get("AntecHead", "_") == "head":
                                    antec_annotation.append("B-Antec-Head")
                                else:
                                    antec_annotation.append("B-Antec")
                        #New level antec
                        else:
                            antecStack.append(antec_annos[i])
                            if tok.__dict__.get("AntecHead", "_") == "head":
                                antec_annotation.append("B-Antec-Head")
                            else:
                                antec_annotation.append("B-Antec")
                    #Start of antec
                    else:
                        antecStack.append(antec_annos[i])
                        if tok.__dict__.get("AntecHead", "_") == "head":
                            antec_annotation.append("B-Antec-Head")
                        else:
                            antec_annotation.append("B-Antec")

                tok.Antec = "|".join(antec_annotation)

        #Link Antecs to their MovElem(s)
        for tok in sentence.tokens:

            if tok.__dict__.get("Antec", "_") == "_" or tok.__dict__.get("AntecMovElem", "_") == "_":
                continue

            #Token is antec
            if "|" in tok.AntecMovElem:
                links = tok.AntecMovElem.split("|")
            else:
                links = tok.AntecMovElem.split(";")
            for l in range(len(links)):
                link = links[l]
                TSV_ID = link.split("[")[0]
                try:
                    MovElemID = "["+link.split("[")[1]
                except IndexError:
                    print(sentence.sent_id, tok.ID, link)
                    input()
                #print(sentence.sent_id, tok.ID, link, TSV_ID)
                #linkID = "_"
                for linktok in sentence.tokens:
                    if linktok.TSVID != TSV_ID: continue

                    #Token with correct ID
                    movElems = linktok.__dict__.get("MovElemCat", "_").split("|")
                    linkID = "_"
                    for me in movElems:
                        if me.endswith(MovElemID):
                            movElemBIO = linktok.MovElem.split("|")[movElems.index(me)]
                            try:
                                linkID = str(int(movElemBIO.split("-")[-1]))
                            except ValueError:
                                linkID = "_"
                    
                if linkID != "_":
                    links[l] = linkID
                else:
                    print("no linkID for", sentence.sent_id, tok.ID, link)
                    input()
                    links[l] = "_"

            antecAnnos = tok.Antec.split("|")
            for i in range(len(links)):
                if antecAnnos[i].startswith("I-"):
                    continue
                antecAnnos[i] = antecAnnos[i].replace("Antec", "Antec-"+links[i])
            tok.Antec = "|".join(antecAnnos)

        return sentence

##############################

class SimplePTBInitializer(Processor):

    CHAR_MAPPING = {
            "(" : "LBR",
            ")" : "RBR",
            "ō" : "o",
            "ā" : "a",
            "ī́" : "i",
            "č" : "c",
            "ꝙ́" : "q",
            "ꝛ" : "r",
            "ď" : "d",
            "ꝰ" : "9",
            "q́" : "q"
        }

    #################

    def __init__(self):
        pass

    #####################

    def process_sentence(self, sent, treename, stringname, form="FORM"):
        from C6C.src.document import Tree
        
        if not stringname in sent.__dict__:
            sent.__dict__[stringname] = ""
            sent.__dict__[treename] = None
            return sent

        if not treename in sent.__dict__:
            sent.__dict__[treename] = Tree.from_PTB_string(sent.__dict__[stringname])

        if sent.__dict__[treename] == None:
            return sent
        c = 0
        for terminal in sent.__dict__[treename].terminals():
            if not "token" in terminal.__dict__:
                print(sent.sent_id, sent.__dict__[treename])
                sent.__dict__[treename] = None
                continue
            
            terminal_mapped_form = terminal.token.__dict__["FORM"]
            for char, repl in self.CHAR_MAPPING.items():
                terminal_mapped_form = terminal_mapped_form.replace(char, repl)
            token_mapped_form = sent.tokens[c].__dict__[form]
            for char, repl in self.CHAR_MAPPING.items():
                token_mapped_form = token_mapped_form.replace(char, repl)
            while c < len(sent.tokens) \
                and terminal_mapped_form != token_mapped_form:
                c += 1
                if c < len(sent.tokens):
                    token_mapped_form = sent.tokens[c].__dict__[form]
                    for char, repl in self.CHAR_MAPPING.items():
                        token_mapped_form = token_mapped_form.replace(char, repl)
            if c < len(sent.tokens):
                terminal.token = sent.tokens[c]
                terminal.ID = terminal.token.ID
                c += 1
            else:
                print("No matching conlltok for terminal", terminal.token, "in sent", sent.sent_id)
                #input("Press any key to continue.")
        
        for conlltok in sent.tokens:
            conlltok.XPOS = conlltok.XPOS.replace("PROAV", "PAV").replace("PROP", "PAV")
       
        return sent

    ####################

    def process(self, doc, treename, stringname):
        for sent in doc.sentences:
            sent = self.process_sentence(sent, treename, stringname)
        return doc

##########################

class GermanCtoSTTSMapper(Processor):

    def __init__(self):
        pass

    def process(self, doc):

        for sent in doc.sentences:
            for tok in sent.tokens:
                if tok.POS == "PTKREL":
                    tok.XPOS = "ADV"
                elif tok.POS == "PWAVREL":
                    tok.XPOS = "PWAV"
                elif tok.POS == "PWREL":
                    tok.XPOS = "PRELS"
                elif tok.POS == "PAVREL":
                    tok.XPOS = "PAV"
                elif tok.POS == "NA":
                    tok.XPOS = "NN"

        return doc

###############################

class DependencyProcessor(Processor):

    def __init__(self):
        pass

    #####################

    def process_sentence(self, sent):

        #Add root(s) to sentence
        #And inform every tok about its head-token
        sent.roots = []
        for tok in sent.tokens:
            if tok.HEAD == "0":
                sent.roots.append(tok)
                tok.head_tok = "ROOT"
            elif tok.HEAD != "_":
                try:
                    tok.head_tok = [t for t in sent.tokens if t.ID == tok.HEAD][0]
                except:
                    tok.head_tok = None
            else:
                tok.head_tok = None

        #Then inform every tok about its children
        for tok in sent.tokens:
            tok.dep_toks = [t for t in sent.tokens if t.head_tok == tok]          

        return sent

    #####################

    def process(self, doc):

        for sent in doc.sentences:
            sent = self.process_sentence(sent)
        
        return doc

######################################

class TuebaTreeSimplifier(Processor):

    def __init__(self):
        pass

    #####################

    def process_sentence(self, sent):

        ############################

        def map_label(node):

            if node.cat() == "SIMPX" and node.label() == "OS":
                node.simple_cat = "SIMPX:OS"
            elif node.label() == "KONJ":
                node.simple_cat = node.cat().split("=")[0] + ":KONJ"
            elif node.label() == "HD" and node.get_parent() and node.get_parent().cat().startswith("PX"):
                node.simple_cat = node.cat().split("=")[0] + ":HD"
            elif node.label() == "HD" and node.get_parent() and node.get_parent().cat().split("=")[0] == node.cat().split("=")[0]:
                i = node.get_parent().children.index(node)
                node.get_parent().remove_child(node)
                for c, child in enumerate(node.nodes()):
                    node.get_parent().insert_child(i+c, child)
                map_label(node.get_parent().children[i])
                return
            elif node.cat().startswith("NX") and node.label() == "APP" and node.get_parent() and node.get_parent().cat() == "NX":
                node.simple_cat = "NX:APP"
            else:
                node.simple_cat = node.cat().split("=")[0]
            
            c = 0
            while c < len(list(node.nodes())):
                child = list(node.nodes())[c]
                map_label(child)
                c += 1

        ###########################
            
        if sent.tree:
            map_label(sent.tree)
            sent.PTBstring_simple = sent.tree.to_string(include_gf=False)

        return sent

    ###########################

    def process(self, doc):

        for sent in doc.sentences:
            sent = self.process_sentence(sent)

        return doc

####################################

class TigerTreeSimplifier(Processor):

    def __init__(self):
        pass

    #####################

    def process_sentence(self, sent):

        ############################

        def map_label(node):

            if node.cat() == "S" and node.label() in ["RC", "OC"]:
                node.simple_cat = "S:"+node.label()
            
            elif node.is_terminal() and node.get_parent() and node.get_parent().cat().startswith("S"):
                if node.token.XPOS in ["PRELS", "PDS", "PIS", "PPER", "PPOSS", "PRELS", "PRF", "PWS", "NN", "NE", "CARD"]:
                    t = Tree(node.ID, "NP", node.label(), nodes=[], parent=node.get_parent())
                    t.simple_cat = "NP"
                    node.parent().children[node.parent().children.index(node)] = t
                    t.add_child(node)
                elif node.token.XPOS in ["ADV", "PTKNEG"]:
                    t = Tree(node.ID, "AVP", node.label(), nodes=[], parent=node.get_parent())
                    t.simple_cat = "AVP"
                    node.get_parent().children[node.get_parent().children.index(node)] = t
                    t.add_child(node)
                elif node.token.XPOS.startswith("ADJ"):
                    t = Tree(node.ID, "AP", node.label(), nodes=[], parent=node.get_parent())
                    t.simple_cat = "AP"
                    node.get_parent().children[node.get_parent().children.index(node)] = t
                    t.add_child(node)
                elif node.token.XPOS in ["PROP", "PROAV", "PAV"]:
                    node.token.XPOS = "PAV"
                    t = Tree(node.ID, "PP", node.label(), nodes=[], parent=node.get_parent())
                    t.simple_cat = "PP"
                    node.get_parent().children[node.get_parent().children.index(node)] = t
                    t.add_child(node)
                elif node.token.XPOS.startswith("V"):
                    t = Tree(node.ID, "VP", node.label(), nodes=[], parent=node.get_parent())                    
                    t.simple_cat = "VP"
                    node.get_parent().children[node.get_parent().children.index(node)] = t
                    t.add_child(node)
                elif node.token.XPOS == "PTKVZ":
                    t = Tree(node.ID, "SVP", node.label(), nodes=[], parent=node.get_parent())                    
                    t.simple_cat = "SVP"
                    node.get_parent().children[node.get_parent().children.index(node)] = t
                    t.add_child(node)
                else:
                    node.simple_cat = node.cat()
            
            else:
                node.simple_cat = node.cat()
            
            c = 0
            while c < len(list(node.nodes())):
                child = list(node.nodes())[c]
                map_label(child)
                c += 1

        ###########################

        if sent.tree:
            map_label(sent.tree)
            sent.PTBstring_simple = sent.tree.to_simplified_string()

        return sent
    
    ###########################

    def process(self, doc):

        for sent in doc.sentences:
            sent = self.process_sentence(sent)

        return doc

############################
