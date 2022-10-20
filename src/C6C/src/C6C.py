# -*- coding: utf-8 -*-
'''
Created on 14.10.2019

@author: Katrin Ortmann
'''

import os
import sys
import click
import importer, exporter, processor
from ast import literal_eval

##############

importers = {"tcfdta" : importer.TCFDTAImporter, "xmldta" : importer.XMLDTAImporter, \
             "tiger" : importer.TigerImporter, "conlluplus" : importer.CoNLLUPlusImporter, \
             "conllu" : importer.CoNLLUImporter, "dtatsv" : importer.DTATSVImporter, \
             "tuebadz" : importer.TuebaDzImporter, "annisgrid" : importer.ANNISGridSentenceImporter, \
             "webannotopf" : importer.WebAnnoTopFImporter, "webannotsv" : importer.WebAnnoTSVImporter, \
             "coraxmlrem" : importer.CoraXMLReMImporter, "tuebadsconll" : importer.TUEBADSConllImporter, \
             "coraxmlanselm" : importer.CoraXMLAnselmImporter, "coraxmlrefbo" : importer.CoraXMLReFBoImporter, \
             "text" : importer.TextImporter, "tigerxml": importer.TigerXMLImporter, \
             "xmlkajuk" : importer.XMLKaJuKImporter, "xmlfnhdc" : importer.XMLFnhdCImporter,
             "conll2000" : importer.CoNLL2000Importer, "sdewac" : importer.SDeWaCIteratorImporter,
             "germanc" : importer.GerManCCoNLLImporter, "tuebatrees" : importer.TuebaDZPTBImporter,
             "ddbtigernegra" : importer.DDBTigerNegraImporter, "fuerstinnenexb" : importer.FuerstinnenEXBImporter,
             "refup" : importer.ReFUPImporter}
exporters = {"conlluplus" : exporter.CoNLLUPlusExporter, "conllu" : exporter.CoNLLUExporter, \
             "dtatsv" : exporter.DTATSVExporter, "hipkontsv" : exporter.HIPKONTSVExporter,
             "text" : exporter.TextExporter, "pos" : exporter.POSExporter,
             "conll2000" : exporter.CoNLL2000Exporter, "ptb": exporter.PTBExporter}
processors = {"dtachopper" : processor.DTAChopper, "dtasimplifier" : processor.DTASimplifier, \
              "hipkontostts" : processor.HIPKONtoSTTSMapper, "addmissingstts" : processor.addmissingSTTStoHIPKON, \
              "topfsimplifier" : processor.TopFSimplifier, "satzklammertotopf" : processor.SATZKLAMMERtoTopF,
              "tsvindexer" : processor.TSVIndexer, "hitstostts" : processor.HiTStoSTTSMapper,
              "tuebadstopf" : processor.TUEBADSTopFExtractor, "anselmtostts" : processor.ANSELMtoSTTSMapper,
              "refhitstostts" : processor.ReFHiTStoSTTSMapper, "topfchopper" : processor.TopFChopper,
              "conllindexer" : processor.CoNLLUPLUSIndexer, "mercuriustostts" : processor.MercuriusToSTTSMapper,
              "refuptostts" : processor.ReFUPToSTTSMapper, "fuerstinnentostts" : processor.FuerstinnentoSTTSMapper,
              "virgelmapper" : processor.VirgelMapper, "pronominaladverb" : processor.PronominalAdverbMapper,
              "refupcoding" : processor.ReFUPCoding, "bracketremover" : processor.BracketRemover}

##############################

class Pipeline(object):

    #################################

    def __init__(self, files, out, **kwargs):

        self.files = files
        self.out = out
        for key,val in kwargs.items():
            self.__dict__[key] = val

    #################################

    def convert(self, file):

        #Import file
        doc = self.importer.import_file(file, self.metadir)

        #Additional processing
        for p in self.processors:
            doc = p.process(doc)

        #Export file
        self.exporter.export(doc, self.out)

##############################

def read_list(value):
    if value:
        try: return literal_eval(value)
        except ValueError: return list()
    else:
        return list()

#########################################

def get_input_files(ctx, parameter, vals):
    """
    Input: Folder as string
    Output: List of filenames (including paths)
    """
    files = []
    for v in vals:
        v = os.path.normpath(v)

        #File
        if os.path.isfile(v):
            files.append(v)

        #Folder
        elif os.path.isdir(v):
            for f in os.listdir(v):
                f = os.path.join(v, f)

                #File
                if os.path.isfile(f):
                    files.append(f)

                #Folder
                elif os.path.isdir(f):
                    files.extend(get_input_files(ctx, parameter, [f]))

        #Neither file nor folder
        else:
            print("ERROR: %s is not a file or directory." % (v))

    return sorted(files)

#########################################

def get_output_dir(ctx, parameter, out):
    #Get output directory
    outdir = os.path.normpath(out)

    #Illegal outdir
    if os.path.exists(outdir) and not os.path.isdir(outdir):
        print("ERROR: %s is not a directory." % (outdir))
        return None

    #If outdir does not exist, create it.
    elif not os.path.isdir(outdir):
        os.makedirs(outdir)

    return outdir

#########################################

def add_component(ctx, parameter, value):

    if parameter.name == "importer":
        name = value.lower()
        imp = importers.get(name, None)()
        if not imp:
            print("ERROR: %s is not a valid importer." % (value))
            raise ValueError
        ctx.params[parameter.name] = imp
        return imp

    elif parameter.name == "exporter":
        name = value.lower()
        exp = exporters.get(name, None)()
        if not exp:
            print("ERROR: %s is not a valid exporter." % (value))
            raise ValueError
        ctx.params[parameter.name] = exp
        return exp

    elif parameter.name == "processors":
        if value:
            prcs = list()
            processorlist = read_list(value)
            for p in processorlist:
                if processors.get(p.lower(), None):
                    prcs.append(processors.get(p.lower(), None)())
                else:
                    print("WARNING: %s is not a valid processor." % (value))
            return prcs
        else:
            return list()
    else:
        return value

#########################################

def file_exists(file):
    try:
        if not os.path.isfile(file):
            raise FileNotFoundError

    #If file does not exist, skip it.
    except FileNotFoundError:
        print("ERROR: File %s not found." % (file))
        return False

    return True

#########################################

@click.group()
def cli():
    print("### C6C ###", end="\n\n")

##############################

@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("f", nargs=-1, callback=get_input_files) #Input file or folder
@click.argument("out", nargs=1, callback=get_output_dir) #Output file or folder
@click.option("-m", "--metadir", default="./../meta/", help="Directory where meta information should be stored.", callback=get_output_dir)
@click.option("-i", "--importer", required=True, type=click.Choice(["tcfDTA", "xmlDTA", "tiger", "conlluplus", "conllu", "DTAtsv",
                                                                    "tuebadz", "annisgrid", "webannotopf", "webannotsv", "coraxmlrem",
                                                                    "tuebadsconll", "coraxmlanselm", "coraxmlrefbo", "text", "tigerxml",
                                                                    "xmlkajuk", "xmlfnhdc", "conll2000", "sdewac", "germanc", "tuebatrees",
                                                                    "ddbtigernegra", "fuerstinnenexb", "refup"], \
              case_sensitive=False), help="Importer for input file format.", callback=add_component)
@click.option("-e", "--exporter", required=True, type=click.Choice(["conlluplus", "conllu", "DTAtsv", "HIPKONtsv", "text", "pos", "conll2000", "ptb"], case_sensitive=False), \
              help="Exporter for desired output format.", callback=add_component)
@click.option("-p", "--processors", help="Specify list of processors in order of application.", callback=add_component)
def convert(f, out, **kwargs):
    """
    Convert input file(s) to a specified output format.
    """
    #Get input file(s)
    files = f
    if not files:
        return None

    #Get output directory
    if not out:
        return None

    #Create Pipeline
    pipeline = Pipeline(files, out, **kwargs)

    #For all files
    with click.progressbar(files, label="Converting texts:") as files:
        for file in files:

            #Skip non-existing files
            if not file_exists(file):
                continue

            pipeline.convert(file)

################################
if __name__ == '__main__':
    cli()
