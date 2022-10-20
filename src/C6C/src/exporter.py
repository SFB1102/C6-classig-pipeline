# -*- coding: utf-8 -*-
'''
Created on 14.10.2019

@author: Katrin Ortmann
'''

import os

############################

class Exporter(object):

    def __init__(self):
        pass

    def export(self, doc, outdir):
        pass

############################

class CoNLLUPlusExporter(Exporter):

    COLUMNS = {"ID" : 0, "FORM" : 1, "LEMMA" : 2, "UPOS" : 3, "XPOS" : 4, \
               "FEATS" : 5, "HEAD" : 6, "DEPREL" : 7, "DEPS" : 8, "MISC" : 9}
    META = ["doc_id(tueba)", "sent_id", "sent_id(DTA)", "sent_id(Tiger)", "sent_id(TSV)", "sent_id(tueba)", "sent_id(grid)",
            "filename", "paragraph_id", "text_section", "div_type", "sent_type", "Kommentar", "PTBstring", "PTBstring_simple",
            "TopFString", "text"]

    ##########################

    def __init__(self):
        pass

    ##########################

    def create_outfile(self, filename, outdir):
        try:
            filename, _ = os.path.splitext(filename)
            filename = filename+".conllup"
            outfile = open(os.path.join(outdir, filename), mode="w", encoding="utf-8")
            return outfile
        except:
            print("ERROR: Cannot open file {0}.".format(filename))
            return None

    #########################

    def set_colums(self, doc):
        #TODO
        self.COLUMNS = {"ID" : 0, "FORM" : 1, "LEMMA" : 2, "UPOS" : 3, "XPOS" : 4, \
                        "FEATS" : 5, "HEAD" : 6, "DEPREL" : 7, "DEPS" : 8, "MISC" : 9}

        additional_annos = set()
        for sent in doc.sentences:
            for tok in sent.tokens:
                for anno,val in tok.__dict__.items():
                    if not anno in self.COLUMNS and not val in (None, "_"):
                        additional_annos.add(anno)
        if additional_annos:
            for i, anno in enumerate(sorted(additional_annos)):
                self.COLUMNS[anno] = i+len(self.COLUMNS)+1

    #########################

    def set_meta(self, doc):
        pass

    #########################

    def export(self, doc, outdir):

        #Open outfile
        outfile = self.create_outfile(doc.filename, outdir)
        if not outfile: return

        #Add necessary columns for this doc
        self.set_colums(doc)

        #Print header
        header = "# global.columns = " + " ".join([key for key,val in sorted(self.COLUMNS.items(), key=lambda l: l[1])])
        print(header, file=outfile)

        for sent in doc.sentences:

            #Print sentence meta info
            for metainfo in self.META: 
                #, _ in sorted(self.META.items(), key=lambda l: l[1]):
                val = sent.__dict__.get(metainfo, None)
                if val: print("# {0} = {1}".format(metainfo, val), file=outfile)

            #Print words
            for word in sent.tokens:
                print("\t".join([str(word.__dict__.get(col, "_")) \
                                 for col, _ in sorted(self.COLUMNS.items(), key=lambda l: l[1])]), \
                      file=outfile)

            if not sent is doc.sentences[-1]:
                print(file=outfile)

        outfile.close()

############################

class CoNLLUExporter(Exporter):

    COLUMNS = {"ID" : 0, "FORM" : 1, "LEMMA" : 2, "UPOS" : 3, "XPOS" : 4, \
               "FEATS" : 5, "HEAD" : 6, "DEPREL" : 7, "DEPS" : 8, "MISC" : 9}
    META = {"doc_id(tueba)" : 0, "sent_id" : 1, "sent_id(DTA)" : 2, "sent_id(Tiger)" : 2, "sent_id(TSV)" : 2, "sent_id(tueba)" : 2, "sent_id(grid)" : 3, \
            "paragraph_id" : 4, "text_section": 5, "div_type" : 6, "sent_type" : 7, "Kommentar" : 8, "text" : 9}

    ##########################

    def __init__(self):
        pass

    ##########################

    def create_outfile(self, filename, outdir):
        try:
            filename, _ = os.path.splitext(filename)
            filename = filename+".conllu"
            outfile = open(os.path.join(outdir, filename), mode="w", encoding="utf-8")
            return outfile
        except:
            print("ERROR: Cannot open file {0}.".format(filename))
            return None

    #########################

    def set_meta(self, doc):
        pass

    #########################

    def export(self, doc, outdir):

        #Open outfile
        outfile = self.create_outfile(doc.filename, outdir)
        if not outfile: return

        #Print header
        header = "# global.columns = " + " ".join([key for key,val in sorted(self.COLUMNS.items(), key=lambda l: l[1])])
        print(header, file=outfile)

        for sent in doc.sentences:

            #Print sentence meta info
            for metainfo, _ in sorted(self.META.items(), key=lambda l: l[1]):
                val = sent.__dict__.get(metainfo, None)
                if val: print("# {0} = {1}".format(metainfo, val), file=outfile)

            #Print words
            for word in sent.tokens:

                print("\t".join([str(word.__dict__.get(col, "_")) \
                                 for col, _ in sorted(self.COLUMNS.items(), key=lambda l: l[1])]), \
                      file=outfile)

            if not sent is doc.sentences[-1]:
                print(file=outfile)

        outfile.close()

############################

class DTATSVExporter(Exporter):

    COLUMNS = ["TSVID", "CHARS", "FORM", "XPOS", "POS", "LEMMA", "OrthCorr",
                        "OrthCorrOp", "OrthCorrReason", "Cite", "AntecDepLink", "AntecMovElem",
                        "AntecHeadLink", "AntecHead", "AntecHeadLemLink", "AntecHeadLem",
                        "SentBrcktLink", "SentBrckt", "SentBrcktType", "MovElemAntecLink",
                        "MovElemAntec", "MovElemCat", "MovElemPos", "RelCType",
                        "MovElemRole", "MovElemTyp", "AdvCVPos", "AdvCVHead"]

    ##########################

    def __init__(self):
        pass

    ##########################

    def create_outfile(self, filename, outdir):
        try:
            filename, _ = os.path.splitext(filename)
            filename = filename+".tsv"
            outfile = open(os.path.join(outdir, filename), mode="w", encoding="utf-8")
            return outfile
        except:
            print("ERROR: Cannot open file {0}.".format(filename))
            return None

    #########################

    def set_colums(self, doc):
        pass

    #########################

    def set_meta(self, doc):
        pass

    #########################

    def export(self, doc, outdir):

        #Open outfile
        outfile = self.create_outfile(doc.filename, outdir)
        if not outfile: return

        #Print header
        header = """#FORMAT=WebAnno TSV 3.2
#T_SP=de.tudarmstadt.ukp.dkpro.core.api.lexmorph.type.pos.POS|PosValue|coarseValue
#T_SP=de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Lemma|value
#T_SP=de.tudarmstadt.ukp.dkpro.core.api.transform.type.SofaChangeAnnotation|operation|reason|value
#T_SP=webanno.custom.Citation|
#T_SP=webanno.custom.Antezedens|ROLE_webanno.custom.Antezedens:dependent_webanno.custom.AntezedensDependentLink|webanno.custom.Extraposition|ROLE_webanno.custom.Antezedens:head_webanno.custom.AntezedensHeadLink|de.tudarmstadt.ukp.dkpro.core.api.lexmorph.type.pos.POS|ROLE_webanno.custom.Antezedens:headLemma_webanno.custom.AntezedensHeadLemmaLink|de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Lemma
#T_SP=webanno.custom.Bracket|ROLE_webanno.custom.Bracket:bracket_webanno.custom.BracketBracketLink|webanno.custom.Bracket|typ
#T_SP=webanno.custom.Extraposition|ROLE_webanno.custom.Extraposition:antecedent_webanno.custom.ExtrapositionAntecedentLink|webanno.custom.Antezedens|category|position|relctype|role|typ|ROLE_webanno.custom.Extraposition:verb_webanno.custom.ExtrapositionVerbLink|de.tudarmstadt.ukp.dkpro.core.api.lexmorph.type.pos.POS"""
        print(header, end="\n\n\n", file=outfile)

        for sent in doc.sentences:

            #Print text
            print("#Text=" + sent.text, file=outfile)

            #Print words
            for word in sent.tokens:
                print("\t".join([str(word.__dict__.get(str(col), "_")) \
                                     for col in self.COLUMNS]), \
                      file=outfile)

            if not sent is doc.sentences[-1]:
                print(file=outfile)

        outfile.close()

############################

class HIPKONTSVExporter(Exporter):

    COLUMNS = ["TSVID", "CHARS", "FORM", "XPOS", "LEMMA", "TopF"]

    ##########################

    def __init__(self):
        pass

    ##########################

    def create_outfile(self, filename, outdir):
        try:
            filename, _ = os.path.splitext(filename)
            filename = filename+".tsv"
            outfile = open(os.path.join(outdir, filename), mode="w", encoding="utf-8")
            return outfile
        except:
            print("ERROR: Cannot open file {0}.".format(filename))
            return None

    #########################

    def set_colums(self, doc):
        pass

    #########################

    def set_meta(self, doc):
        pass

    #########################

    def export(self, doc, outdir):

        #Open outfile
        outfile = self.create_outfile(doc.filename, outdir)
        if not outfile: return

        #Print header
        header = """#FORMAT=WebAnno TSV 3.2
#T_SP=de.tudarmstadt.ukp.dkpro.core.api.lexmorph.type.pos.POS|PosValue
#T_SP=de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Lemma|value
#T_SP=webanno.custom.TopF|TopologicalField"""
        print(header, end="\n\n\n", file=outfile)

        for sent in doc.sentences:

            #Print text
            print("#Text=" + sent.text, file=outfile)

            #Print words
            for word in sent.tokens:
                print("\t".join([str(word.__dict__.get(str(col), "_")) \
                                     for col in self.COLUMNS]), \
                      file=outfile)

            if not sent is doc.sentences[-1]:
                print(file=outfile)

        outfile.close()

############################


class TextExporter(Exporter):

    ##########################

    def __init__(self):
        pass

    ##########################

    def create_outfile(self, filename, outdir):
        try:
            filename, _ = os.path.splitext(filename)
            filename = filename+".txt"
            outfile = open(os.path.join(outdir, filename), mode="w", encoding="utf-8")
            return outfile
        except:
            print("ERROR: Cannot open file {0}.".format(filename))
            return None

    #########################

    def export(self, doc, outdir):

        #Open outfile
        outfile = self.create_outfile(doc.filename, outdir)
        if not outfile: return

        for sent in doc.sentences:

            #Print sentence
            if sent.text:
                print(sent.text, file=outfile)
            else:
                print(" ".join(tok.FORM for tok in sent.tokens), file=outfile)

        outfile.close()

############################

class POSExporter(Exporter):

    ##########################

    def __init__(self):
        pass

    ##########################

    def create_outfile(self, filename, outdir):
        try:
            filename, _ = os.path.splitext(filename)
            filename = filename+".txt"
            outfile = open(os.path.join(outdir, filename), mode="w", encoding="utf-8")
            return outfile
        except:
            print("ERROR: Cannot open file {0}.".format(filename))
            return None

    #########################

    def export(self, doc, outdir):

        #Open outfile
        outfile = self.create_outfile(doc.filename, outdir)
        if not outfile: return

        for sent in doc.sentences:

            #for tok in sent:
            #    tok.XPOS = tok.XPOS.replace("$.", "PUNCT").replace("$,", "COMMA").replace("$(", "KLAMMER")
            #if len(sent.tokens) > 300:
            #    continue

            #Print POS
            if any(tok.__dict__.get("XPOS", "_") != "_" for tok in sent.tokens):
                print(" ".join(tok.XPOS for tok in sent.tokens), file=outfile)
            elif any(tok.__dict__.get("POS", "_") != "_" for tok in sent.tokens):
                print(" ".join(tok.POS for tok in sent.tokens), file=outfile)
            else:
                print("No POS information found.")
                break

        outfile.close()

############################

class CoNLL2000Exporter(Exporter):

    COLUMNS = {"FORM" : 0, "XPOS" : 1, "CHUNK" : 2}
    META = {"sent_id" : 0, "text" : 1}
    SEPARATOR = " "

    ##########################

    def __init__(self):
        pass

    ##########################

    def create_outfile(self, filename, outdir):
        try:
            filename, _ = os.path.splitext(filename)
            filename = filename+".conll"
            outfile = open(os.path.join(outdir, filename), mode="w", encoding="utf-8")
            return outfile
        except:
            print("ERROR: Cannot open file {0}.".format(filename))
            return None

    #########################

    def set_meta(self, doc):
        pass

    #########################

    def export(self, doc, outdir):

        #Open outfile
        outfile = self.create_outfile(doc.filename, outdir)
        if not outfile: return

        for sent in doc.sentences:

            #Print words
            for word in sent.tokens:

                print(self.SEPARATOR.join([str(word.__dict__.get(col, "_")) \
                                 for col, _ in sorted(self.COLUMNS.items(), key=lambda l: l[1])]), \
                      file=outfile)

            if not sent is doc.sentences[-1]:
                print(file=outfile)

        outfile.close()

############################

class PTBExporter(Exporter):

    def __init__(self):
        pass

    ##########################

    def create_outfile(self, filename, outdir):
        try:
            filename, _ = os.path.splitext(filename)
            filename = filename+".txt"
            outfile = open(os.path.join(outdir, filename), mode="w", encoding="utf-8")
            return outfile
        except:
            print("ERROR: Cannot open file {0}.".format(filename))
            return None

    #########################

    def export(self, doc, outdir):

        #Open outfile
        outfile = self.create_outfile(doc.filename, outdir)
        if not outfile: return

        for sent in doc.sentences:

            #Print trees
            tree = sent.__dict__.get("PTBstring", "")
            if tree:
                print(tree, file=outfile)
            else:
                print("WARNING: No tree for sentence", sent.sent_id, "in file", doc.filename)


        outfile.close()

############################
