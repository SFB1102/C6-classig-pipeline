# -*- coding: utf-8 -*-
'''
Created on 23.10.2019

@author: Katrin Ortmann
'''

import os
import click
import importer, processor
from featurefinder import FeatureFinder
from corpus import Corpus
from ast import literal_eval

##############

importers = {"conlluplus" : importer.CoNLLUPlusImporter,
             "conll2000" : importer.CoNLL2000Importer}

processors = {"pronounlemmatizer" : processor.PronounLemmatizer, "bracketremover" : processor.BracketRemover,
              "ellipsisremover" : processor.EllipsisRemover}

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

    return files

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

def get_features(ctx, parameter, val):
    """
    Input: Filename of feature file with one feature per line.
    Output: List of features.
    """
    features = []

    if not os.path.isfile(val):
        print("WARNING:", val, "is not a feature file. Using default features instead.")

    else:
        feature_file = open(val, mode="r", encoding="utf-8")

        for line in feature_file:
            line = line.strip()
            #Skip empty lines
            if not line:
                continue
            #Skip comments
            elif line.startswith("#"):
                continue
            else:
                features.append(line)

        feature_file.close()
    
    return features
    
#########################################

def set_weights(ctx, parameter, val):
    """
    Input: Filename of weight file with one key-value pair per line.
    Output: Dictionary of feature : weight pairs.
    """
    weights = {}

    if not os.path.isfile(val):
        print("WARNING:", val, "is not a weight file. Using default weights instead.")

    else:
        weight_file = open(val, mode="r", encoding="utf-8")

        for line in weight_file:
            line = line.strip()
            #Skip empty lines
            if not line:
                continue
            #Skip comments
            elif line.startswith("#"):
                continue
            else:
                line = line.split(":")
                #Not well-formed
                if len(line) < 2:
                    print("WARNING: Cannot interpret line: {0}. Weight is skipped.".format(":".join(line)))
                    continue
                #Feature contains colon
                elif len(line) > 2:
                    feat = ":".join(line[:-1]).strip()
                    weight = line[-1].strip()
                else:
                    feat = line[0].strip()
                    weight = line[-1].strip()
                try:
                    weight = float(weight)
                    #Overwrite existing weights.
                    if feat in weights:
                        print("WARNING: Feature {0} already exists. New weight is {1}.".format(feat, weight))
                    weights[feat] = weight
                #Weight is not a float value.
                except ValueError:
                    print("WARNING: Cannot interpret weight {0}. Feature {1} is skipped.".format(weight, feat))                

        weight_file.close()

    return weights

#########################################

def read_list(value):
    if value:
        try: return literal_eval(value)
        except ValueError: return list()
    else:
        return list()

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

############################################

def set_output_mode(ctx, parameter, mode):

    if isinstance(mode, str) and mode.lower() == "true":
        return True
    else:
        return False

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
    print("### COAST (Conceptual Orality Analysis and Scoring Tool) ###", end="\n\n")

##############################

@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("f", nargs=-1, callback=get_input_files) #Input file or folder
@click.argument("out", nargs=1, callback=get_output_dir) #Output folder
@click.option("-i", "--importer", required=True, type=click.Choice(["conlluplus", "conll2000"], case_sensitive=False),
                                  help="Importer for input file format.", callback=add_component)
@click.option("-p", "--processors", help="Specify a list of processors in order of application. Processors must be surrounded by single quotes and the list by double quotes.", 
                                    callback=add_component)
@click.option("-f", "--features", default="./../config/features.config", 
                                  help="File specifying the list of features to analyze.", callback=get_features)
@click.option("-w", "--weights", default="./../config/weights.config", 
                                 help="File specifying the weights for calculating the orality score.", callback=set_weights)
@click.option("--reproduce-kajuk", default=False, 
                                   help="If True, reproduce the results of Ortmann & Dipper (2022).", callback=set_output_mode)
def analyze(f, out, **kwargs):
    """
    Analyze input files with respect to conceptual orality.
    """
    #Get input file(s)
    files = f
    if not files:
        return None
    
    #Get output directory
    if not out:
        return None
    
    #Settings for reproducing KaJuK paper
    if kwargs.get("reproduce_kajuk", False) == True:
        print("WARNING: Overwriting settings to reproduce results of Ortmann & Dipper (2022).")
        kwargs["processors"] = [processors.get("ellipsisremover")(), 
                                processors.get("bracketremover")(), 
                                processors.get("pronounlemmatizer")()]
        kwargs["features"] = ["mean_sent", "med_sent", "mean_word", "med_word",
                              "subord", "coordInit", "question", "exclam", "V:N",
                              "lexDens", "PRON1st", "DEM", "DEMshort", "PTC", "INTERJ"]
        kwargs["weights"] =   { "mean_word" : -0.819, 
                                "PRON1st" : 0.717, 
                                "V:N" : 0.528,
                                "DEMshort" : 0.365,
                                "subord" : -0.314, 
                                "INTERJ" : 0.276, 
                                "DEM" : 0.06, 
                                "PTC" : 0.104, 
                                "lexDens" : -0}
    
    finder = FeatureFinder(kwargs.get("features", []), kwargs.get("weights", {}))
    corpus = Corpus()
    results = dict()

    #For all files
    with click.progressbar(files, label="Analyzing texts:") as files:
        for file in files:
            
            #Skip non-existing files
            if not file_exists(file):
                continue

            doc = kwargs["importer"].import_file(file)
            
            for p in kwargs["processors"]:
                doc = p.process(doc)

            corpus.add_file(doc)

            finder.find_features(doc)

            doc = finder.compute_stats(doc)
            
            results[doc.filename] = doc.stats_table
        
        finder.output_stats(results, out, kwargs.get("reproduce_kajuk", False))


################################
if __name__ == '__main__':
    cli()