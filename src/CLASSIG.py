# -*- coding: utf-8 -*-

'''
CLASSIG Pipeline
Computational Linguistic Analysis
of Syntactic Structures in German

@author: Katrin Ortmann
'''

import os
import argparse
import sys
from annotations import Span, MovElem
from evaluation import evaluate_file, overall_results, output_results, \
                       output_tables, get_data_stats, output_data_stats
from variant_corpus import create_variant_corpus
from orality import determine_orality, scaled_results_and_scores
from helper_functions import add_dict
from language_models import create_LM
from information_theory import add_surprisal, analyze_surprisal_results, \
                               analyze_dorm_results
from extrap import analyze_relcs

#############################

def read_config(config_file):
    """
    Read settings from the configuration file.

    Input: Filename of the config file.
    Output: Settings dictionary.
    """

    #############################

    def parse_config(key, val):
        """
        Parse key-value pairs from the config file.
        Checks if values are valid. If not prints error messages.

        Input: Key and value
        Output: Key and parsed value (or None, if invalid)
        """

        #Set selected list of action(s) in a sensible order
        if key == "action":
            possible_vals = ["annotate", "evaluate", "data_stats", "create_lm",
                             "variants", "surprisal", "dorm", "orality",
                             "analyze_relcs", "tables"]
            actions = []

            val = set([v.strip() for v in val.split(",")])
            if "all" in val:
                return key, possible_vals
            
            for v in possible_vals:
                if v in val:
                    actions.append(v)
            
            return key, actions

        #Set input, output and evaluation directories
        #Create, if necessary and possible
        elif key.endswith("_dir"):
            if os.path.isdir(val) or os.path.isfile(val):
                val = os.path.normpath(val)
                return key, val
            else:
                if key in ["out_dir", "eval_dir", "variant_dir"]:
                    val = os.path.normpath(val)
                    os.makedirs(val)
                    return key, val
                else:
                    print("Error: '{0} = {1}' is not a file/directory.".format(key, val))
                    return None, None

        #Set input and gold formats
        elif key.startswith("format"):
            input_formats = ["conllup", "conll2000"]
            if key in ["format_in", "format_gold"]:
                if val in input_formats:
                    return key, val
                else:
                    print("Error: '{0}' is not a legal input format.".format(val))

        #Set list of annotations in a sensible order
        #so that each annotation can build on the previous one, if applicable.
        elif key == "annotations":
            possible_annotations = ["topf", "brackets", "chunks", 
                                    "phrases", "extrap"]
            annotations = []

            val = set([v.strip() for v in val.split(",")])
            if "all" in val:
                return key, possible_annotations
            
            for a in possible_annotations:
                if a in val:
                    annotations.append(a)

            return key, annotations

        #Set list of model(s) to apply
        elif key == "models":
            available_models = ["news1", "news2", "hist", "mix", 
                                "topfpunct"]
            models = []

            val = set([v.strip().lower() for v in val.split(",")])
            if "all" in val:
                return key, available_models
            
            for m in available_models:
                if m in val:
                    models.append(m)

            return key, models
        
        #Set list of language model(s) to apply
        elif key == "lm_models":
            available_models = ["WORD", "FORM", "XPOS", "LEMMA"]
            models = []

            val = set([v.strip() for v in val.split(",")])
            if "all" in val:
                return key, available_models
            
            for m in available_models:
                if m in val:
                    models.append(m)

            return key, models

        #Get n-gram size >= 1 for language models
        elif key == "lm_models_n":
            try:
                n = int(val)
                if n < 1:
                    raise ValueError
            except ValueError:
                n = 2
                print("Error: '{0}' is not a valid n-gram size. Using bigrams.".format(val))
            return key, n
        
        #Set normalized form
        elif key == "norm":
            if val.strip() and val.strip().lower() != "none":
                return key, val.strip()    
            elif val.strip().lower() == "none":
                return key, "FORM"
            else:
                print("Normalization '{0}' is not available. Normalization will not be used.".format(val))
                return key, "FORM"

        #Set corpus name
        elif key == "corpus":
            return key, val

        #Unknown key
        else:
            print("WARNING: Unknown key '{0}' will be ignored.".format(key))
            return key, None

    #############################

    #Create empty configuration dictionary
    config = dict()
    
    #Open config file
    f = open(config_file, mode="r", encoding="utf-8")
    
    for line in f:
        line = line.strip()

        #Skip empty lines and comments
        if not line or line.startswith("#"):
            continue
        
        #Read keys and values from config
        line = line.split("=")
        key = line[0].strip()
        val = line[1].strip()
        
        #Parse config
        key, val = parse_config(key, val)

        #Skip illegal configs
        if key is None or val is None:
            continue

        #Output settings
        print("{0}: {1}".format(key, val))

        #Warn about duplicate keys
        if key in config:
            print("Warning: Duplicate config item '{0}' found: '{1}' updated to '{2}'.".format(key, config[key], val))

        #Set key-value pair
        config[key] = val

    #Return the settings dictionary
    return config

#############################

def initialize_annotations(doc, annotation):
    """
    Initialize annotations from text input for further use.

    For a given document, transform the BIO annotations 
    from the correct column into Span objects.

    Input: Doc object and name of the annotation
    Output: Doc object with initialized Span objects
    """
    
    #Initialize standard spans
    if annotation in ["chunks", "phrases", "topf"]:

        if annotation == "chunks": annoname = "CHUNK"
        elif annotation == "phrases": annoname = "PHRASE"
        elif annotation == "topf": annoname = "TOPF"

        for sent in doc.sentences:
            sent.__dict__[annotation] = Span.span_from_BIO_annotation(sent, annoname)

    #Initialize sentence brackets
    elif annotation == "brackets":
        import brackets
        doc = brackets.annotate(doc)
        for sent in doc.sentences:
            sent.__dict__[annotation] = Span.span_from_BIO_annotation(sent, "SentBrckt")

    #Initialize moving elements and their antecedents
    elif annotation == "extrap":
        for sent in doc.sentences:
            if not sent.__dict__.get("MovElems", []):
                sent.MovElems = MovElem.span_from_BIO_annotation(sent, "MovElem")
    
    return doc

#############################

def import_data(data_type, **kwargs):
    """
    Import the given data as iterator.

    Selects the correct importer and loads the files
    into Doc objects. Also initializes all span annotations.

    Input: Type of data ('gold', 'out', 'in', 'variants', 
           'train', 'surprisal', 'surprisal_variants') 
           and kwargs dict
    Output: Yields one Doc object at a time
    """

    #Gold data is taken from gold dir
    if data_type == "gold":
        format = kwargs.get("format_gold", None)
        directory = kwargs.get("gold_dir", "")

    #Eval data comes from the out dir
    elif data_type == "out":
        format = "conllup"
        directory = kwargs.get("out_dir", "")
        if directory:
            directory = os.path.join(directory, kwargs.get("annotation"), 
                                     kwargs.get("model"))
    
    #Input data comes from input dir
    elif data_type == "in":
        format = kwargs.get("format_in", None)
        directory = kwargs.get("in_dir", "")

    #Variant data from variant dir
    elif data_type == "variants":
        format = "conllup"
        directory = kwargs.get("variant_dir", "")

    #Train data is taken from train dir
    elif data_type == "train":
        format = kwargs.get("format_gold", None)
        directory = kwargs.get("train_dir", "")

    #Surprisal data for orig and variants
    elif data_type.startswith("surprisal"):
        format = "conllup"
        if "variant" in data_type:
            directory = os.path.join(kwargs.get("out_dir", ""),
                                     "surprisal_variants")
        else:
            directory = os.path.join(kwargs.get("out_dir", ""), 
                                     "surprisal")

    #Get files from the correct directory
    if not os.path.isdir(directory):
        if not os.path.isfile(directory):
            print("Error: '{0}' is not a file/directory. Data cannot be imported.".format(directory))
            return None
        else:
            files = [directory]
    else:
        files = [os.path.join(directory, f) for f in os.listdir(directory) 
                 if os.path.isfile(os.path.join(directory, f))]
        if not files:
            for folder in os.listdir(directory):
                if os.path.isdir(os.path.join(directory, folder)):
                    files += [os.path.join(directory, folder, f) 
                              for f in os.listdir(os.path.join(directory, folder))]
    
    #Initialize the correct importer for the file format
    if format == "conllup":
        from C6C.src.importer import CoNLLUPlusImporter
        myImporter = CoNLLUPlusImporter()

    elif format == "conllu":
        from C6C.src.importer import CoNLLUImporter
        myImporter = CoNLLUImporter()
        
    elif format == "conll2000":
        from C6C.src.importer import CoNLL2000Importer
        myImporter = CoNLL2000Importer()
        #Change columns for different CoNLL2000 uses
        if "chunks" in kwargs.get("annotations", []):
            myImporter.COLUMNS = {"FORM" : 0, "XPOS" : 1, "CHUNK" : 2} 
        elif "phrase" in kwargs.get("annotations", []):
            myImporter.COLUMNS = {"FORM" : 0, "XPOS" : 1, "PHRASE" : 2}

    else:
        print("Error: Import for format '{0}' not supported.".format(format))
        return []

    if not files:
        return None

    #Read each file into a doc object
    for f in files:
        doc = myImporter.import_file(f)
        
        #Initialize the annotations
        for annotation in kwargs.get("annotations", []):
            doc = initialize_annotations(doc, annotation)
        
        #Yield one Doc object at a time
        yield doc

####################

def initialize_exporter():
    """
    Initialize the CoNLLUPlusExporter.

    Output: Exporter object
    """
    from C6C.src.exporter import CoNLLUPlusExporter
    myExporter = CoNLLUPlusExporter()
    
    #Return the exporter object
    return myExporter
    
########################################
## Main program
########################################

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config',  help='Configuration File', required=True)
    
    args = parser.parse_args()
    
    #Read config file
    config = read_config(args.config)

    #Set working directory to dir of this python file
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    #Add chunker to path
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ncrfpp"))

    ###############################
    # ANNOTATION
    if "annotate" in config.get("action", []):
        print("Annotation of input data")

        #For each annotation model
        for model in config.get("models", []):
            print("Model:", model)
            
            #Initialize annotators with the given model
            annotators = []
            for annotation in config.get("annotations", []):
                if annotation in ["brackets", "topf"] \
                   and model in ["topfpunct", "topfnopunct", "news1"]:
                    #If sentence brackets should be annotated
                    #initialize bracket annotation and also
                    #topofields if they are not included in annotation list.
                    if annotation == "brackets":
                        import brackets
                        if not "topf" in config.get("annotations", []):
                            import topofields
                            annotators.append((annotation, topofields.initialize(model, **config)))
                        topf_annotator = [a[1] for a in annotators if a[0] == "topf"]
                        annotators.append(("brackets", topf_annotator))
                    else:
                        import topofields
                        annotators.append((annotation, topofields.initialize(model, **config)))
                #Initialize chunker
                elif annotation == "chunks" and model in ["hist", "news1", "news2", "mix"]:
                    import chunks
                    annotators.append((annotation, chunks.initialize(model, **config)))
                #Initialize phrase parser
                elif annotation == "phrases" and model in ["hist", "news1", "news2", "mix"]:
                    import phrases
                    annotators.append((annotation, phrases.initialize(model, **config)))
                #Initialize extraposition annotation
                elif annotation == "extrap" and model in ["hist", "news1", "news2", "mix"]:
                    import extrap
                    annotators.append((annotation, extrap.initialize(model, **config)))
                
            #Import input data as iterator
            docs = import_data("in", **config)

            #Initialize exporter
            myExporter = initialize_exporter()
            #Stop program here, if data won't be exported anyway
            if myExporter is None:
                sys.exit(1)
            
            #Annotate each doc
            for doc in docs:
                print(doc.filename)
                
                #Go through annotations in a sensible order 
                #so that each annotation can build on the previous one
                #if applicable, i.e.:
                #topf, brackets, chunks, phrases, extrap
                for annotation, annotator in annotators:
                    if annotator is None:
                        continue
                        
                    #For sentence brackets
                    if annotation == "brackets":
                        #Take existing topofield annotation
                        if "topf" in config.get("annotations", []):
                            doc = brackets.annotate(doc, **config)
                        #Or create it first if topofields are not annotated
                        else:
                            doc = annotator.annotate(doc, **config)
                            doc = brackets.annotate(doc, **config)
                    
                    #Create other annotations
                    else:
                        doc = annotator.annotate(doc, **config)

                    #Determine output dir based on selected annotation and models
                    directory = config.get("out_dir", "")
                    if not os.path.isdir(directory):
                        print("Error: '{0}' is not a directory. Annotations cannot be exported.".format(directory))
                        sys.exit(1)
                    directory = os.path.join(directory, annotation, 
                                             model)
                    if not os.path.isdir(directory):
                        os.makedirs(directory)
                    
                    #Export annotations
                    myExporter.export(doc, directory)

    ###############################
    # EVALUATION
    if "evaluate" in config.get("action", []):
        print("Evaluation of annotations")

        #Evaluate each annotation
        for annotation in config.get("annotations", []):
            config["annotation"] = annotation
            print("Annotation:", annotation)

            #With each model that is available for a given annotation
            for model in config.get("models", []):

                if annotation in ["brackets", "topf"] \
                    and not model in ["topfpunct", "topfnopunct", "news1"]:
                    continue
                elif annotation in ["chunks", "phrases", "extrap"] \
                    and not model in ["hist", "news1", "news2", "mix"]:
                    continue

                print("Model:", model)
                config["model"] = model

                #Import gold data
                gold_data = import_data("gold", **config)
        
                #Import eval data
                eval_data = import_data("out", **config)

                if not gold_data or not eval_data:
                    continue

                #Create empty evaluation dict
                eval_dict = {"overall" : {}, "per_file" : {}}

                #Compare gold and eval data
                for golddoc, evaldoc in zip(gold_data, eval_data): 
                    
                    #Files must share the same filename to be compared
                    if golddoc.filename != evaldoc.filename:
                        print("Error: Files {0} and {1} do not match".format(golddoc.filename, evaldoc.filename))
                        continue

                    #Add results to the per-file evaluation dict
                    eval_dict["per_file"][golddoc.filename] = evaluate_file(golddoc, evaldoc, **config)

                #If the evaluation was skipped because of missing
                #input files, this is only recognized here...
                if eval_dict == {"overall" : {}, "per_file" : {}}:
                    continue

                #Calculate overall results
                eval_dict = overall_results(eval_dict, annotation)
                
                #Output the results
                output_results(eval_dict, **config)

    ###############################
    # Data Stats
    if "data_stats" in config.get("action"):
        
        data_stats = dict()

        #Import gold data as iterator
        docs = import_data("gold", **config)

        #Get statistics for each doc
        for doc in docs:
            add_dict(data_stats, get_data_stats(doc, **config))

        #Output the statistics
        output_data_stats(data_stats, **config)

    ###############################
    # Variant corpus
    if "variants" in config.get("action"):

        #Import gold data as iterator
        docs = import_data("gold", **config)

        #Initialize exporter
        myExporter = initialize_exporter()
        #Stop program here, if data won't be exported anyway
        if myExporter is None:
            sys.exit(1)

        #Determine output dir
        directory = config.get("variant_dir", "")
        if not os.path.isdir(directory):
            os.makedirs(directory)

        #Create variant
        for doc in docs:
            variant_doc = create_variant_corpus(doc, 
                                                config.get("variant_labels", ["RELC"]), 
                                                distance_file=None)
            
            #Export variant doc
            myExporter.export(variant_doc, directory)

    ###############################
    # Create language model
    if "create_lm" in config.get("action"):

        #Import train data as iterator
        docs = import_data("train", **config)

        #Create language model(s)
        create_LM(docs, **config)

    ###############################
    # Surprisal
    if "surprisal" in config.get("action"):

        #Import gold data as iterator
        docs = import_data("gold", **config)
        if config.get("variant_dir"):
            variant_docs = import_data("variants", **config)
        else:
            variant_docs = None

        #Initialize exporter
        myExporter = initialize_exporter()
        #Stop program here, if data won't be exported anyway
        if myExporter is None:
            sys.exit(1)

        #Determine output dirs for orig and variant surprisal
        directory = os.path.join(config.get("out_dir", ""),
                                 "surprisal")
        if not os.path.isdir(directory):
            os.makedirs(directory)
        if variant_docs != None:
            variant_directory = os.path.join(config.get("out_dir", ""),
                                             "surprisal_variants")
            if not os.path.isdir(variant_directory):
                os.makedirs(variant_directory)

        #Create eval output dir
        if not os.path.isdir(os.path.join(config.get("eval_dir", ""),
                                          "surprisal")):
            os.makedirs(os.path.join(config.get("eval_dir", ""),
                                     "surprisal"))

        #Check model availability
        available_models = os.listdir(config.get("lm_dir"))
        models = []
        for model_type in config.get("lm_models"):
            model = None
            #Use normalized forms if available
            if model_type == "WORD":
                norm_models = [m for m in available_models 
                               if m.startswith(str(config.get("lm_models_n"))) 
                                  and ("NORM" in m or "ANNO_ASCII" in m)]
                if norm_models:
                    model = norm_models[0]
                    model = model[model.index("_")+1:-4]
                else:
                    model = "FORM"
            if not model:
                model = [m for m in available_models 
                         if m.startswith(str(config.get("lm_models_n"))) 
                            and model_type in m]
                if model:
                    model = model[0]
                    model = model[model.index("_")+1:-4]
                else:
                    print("Error: Language model '{0}' with n = {1} not found.".format(config.get("lm_models"), 
                                                                                       config.get("lm_models_n")))
                    continue
            if model == "DTA-NORM":
                model = "DTA:NORM"
            models.append((model_type, model))
        
        #For each doc, calculate surprisal with given models
        for doc in docs:
            for model_type, model in models:
                add_surprisal(doc, config.get("lm_models_n"), 
                              model, model_type, **config)
            
            #Output RelC surprisal results
            analyze_surprisal_results(doc, **config)

            #Export doc with surprisal values
            myExporter.export(doc, directory)

        if variant_docs != None:
            #For each variant doc, calculate surprisal with given models
            for doc in variant_docs:
                for model_type, model in models:
                    add_surprisal(doc, config.get("lm_models_n"), 
                                  model, model_type, **config)
                
                #Export doc with surprisal values
                myExporter.export(doc, variant_directory)

    ###############################
    # DORM
    if "dorm" in config.get("action"):

        #Import orig and variant data with surprisal annotation
        orig_docs = import_data("surprisal", **config)
        variant_docs = import_data("surprisal_variants", **config)
        
        #Determine output dir
        directory = os.path.join(config.get("eval_dir", ""), "dorm")
        if not os.path.isdir(directory):
            os.makedirs(directory)
        
        #Set model that was used for constituency parsing
        if "news1" in config.get("models", []):
            config["model"] = "news1"
        else:
            config["model"] = "news2"
        
        #Calculate and compare DORM values
        for orig_doc, variant_doc in zip(orig_docs, variant_docs):
            analyze_dorm_results(orig_doc, variant_doc, **config)

    ###############################
    # Orality
    if "orality" in config.get("action"):
        
        #Import gold data as iterator
        docs = import_data("gold", **config)

        #Determine orality for each document
        determine_orality(docs, **config)

        #Scale feature values for the entire corpus
        #and output orality score
        scaled_results_and_scores(**config)

    ###############################
    # RelC extraposition
    if "analyze_relcs" in config.get("action"):

        #Import gold data as iterator
        docs = import_data("gold", **config)

        #Analyze the RelCs
        analyze_relcs(docs, **config)

    ###############################
    # Tables
    if "tables" in config.get("action"):
        output_tables(**config)