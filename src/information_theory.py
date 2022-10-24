# -*- coding: utf-8 -*-

import os
import math
import statistics
from extrap import RelCFinder
from C6C.src.processor import SimplePTBInitializer


##########################

def load_lm_file(n, col, model_dir):
    """
    Load language model.

    Open the language model file for n-grams of size n
    based on annotation column col and read it into a dictionary.
    N-grams are stored as keys (tuples) and frequencies as values.

    Input: N-gram size, column name, model directory (string).
    Output: Dictionary {(tok1, ..., tok_n) : freq, ...} or None.
    """
    if str(n)+"-gram_"+col.replace(":", "-")+".csv" in os.listdir(model_dir):           
        obj = dict()
        with open(os.path.join(model_dir, str(n)+"-gram_"+col.replace(":", "-")+".csv"), 
                  mode="r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    key_vals = line.strip().split("\t")
                    if len(key_vals) < 2:
                        continue
                    key = tuple(key_vals[0].split())
                    val = int(key_vals[1])
                    obj[key] = val
            return obj
    else:
        return None

##########################

def surprisal(probability):
    """
    Input: p(u1|context)
    Output: surprisal(u1|context)
    """
    if probability == 0:
        return None
    elif probability == 1:
        return 0
    else:
        return -math.log(probability, 2)

##########################

def ELE_probability(unit, context, freqdict, freqdict_n_minus_one, V, lambda_=0.5):
    """
    Returns p(u|context) with

                          c(u1, ..., un) + lambda_
    p(un|u1, ..., un-1) = -------------------------------
                          c(u1, ..., un-1) + lambda_ * V

    with V = number of unigram types

    Input
    - unit : string
    - context : tuple of context strings ("tok1", "tok2", ...) or ("", ) for unigrams
    - freqdict : LM dictionary with ngram-tuples as keys and frequencies as values
    - freqdict_n_minus_one : LM dictionary with n-1-grams
    - V : number of unigram types
    - lambda : smoothing parameter (default: 0.5; Jeffrey's 1946)
    """
    if context == ("",):
        count_ngram = freqdict.get((unit,), 0)
    else:
        count_ngram = freqdict.get(tuple([c for c in context]+[unit]), 0)
    count_context = freqdict_n_minus_one.get(context, 0)
    numerator = count_ngram + lambda_
    denominator = count_context + lambda_ * V
    return numerator / denominator

#################################

def dorm(surprisal_values):
    """
    Calculate DORM (sample variance of rolling means).

    Input: List of surprisal values
    Output: DORM value
    """
    rolling_means = [statistics.mean((surprisal_values[i], 
                                      surprisal_values[i+1]))
                     for i in range(len(surprisal_values)-1)]
    try:
        DORM = statistics.variance(rolling_means)
    except:
        print("No DORM for", rolling_means)
        DORM = None
    return DORM
    
################################

def add_surprisal(doc, ngram=2, col="FORM", colname="WORD", **config):
    """
    Annotate document with surprisal values.

    For a given document and language model, calculate surprisal values.
    Values are stored as token attributes 'UnigramSurpr' and 'BigramSurpr' 
    followed by the column name.

    Currently, the function always calculates (only) unigram and bigram surprisal.

    Input: Document object,
           maximum n-gram size (always 2),
           column name in the document,
           model name,
           config dictionary with keys 'lm_dir' and 'corpus'.
    Output: Annotated document object.
    """
    #Currently, only unigrams and bigrams are supported
    ngram = 2

    POS_mapping = {"*" : "XY",
                   "PROAV" : "PAV",
                   "PROP" : "PAV",
                   "_" : "XY",
                   "FM.da" : "FM",
                   "FM.el" : "FM",
                   "FM.en" : "FM",
                   "FM.es" : "FM",
                   "FM.fr" : "FM",
                   "FM.it" : "FM",
                   "FM.la" : "FM",
                   "FM.nl" : "FM",
                   "FM.sv" : "FM",
                   "FM.xy" : "FM",
                   "acc|sg|masc" : "XY",
                   "dat|sg|fem" : "XY",
                   "dat|sg|masc" : "XY",
                   "nom|sg|*" : "XY",
                   "nom|sg|masc" : "XY",
                   "nom|sg|masc|pos" : "XY",
                   "nom|sg|neut" : "XY",
                   "pos" : "XY",
                   "sg|3|pres|ind" : "XY",
                   "NNE" : "NE",
                   "BS" : "XY"}
        
    padLeft = "#S"
    unigram_context = ("", )

    #Load language models
    lms = {0 : dict()}
    for n in range(ngram):
        lms[n+1] = load_lm_file(n+1, col, os.path.join(config.get("lm_dir")))

    #Get vocabulary size (=number of unigram types)
    V = dict()
    V = len(lms[1])-1 #minus padding element

    #Get LM size (=number of unigram tokens)
    lms[0] = {("", ) : sum(lms[1].values())-lms[1].get(padLeft, 0)}
    
    for sent in doc.sentences:
        words = [tok for tok in sent.tokens if not tok.XPOS.startswith("$")]

        for i, w in enumerate(words):
            
            #Get unit
            unit = w.__dict__.get(col, "_")
            if config.get("corpus") == "DTAscience" and col == "DTA:NORM" and unit == "_":
                unit = w.__dict__.get("FORM", "_")
            elif col == "XPOS":
                unit = POS_mapping.get(unit, unit)
            #Get context
            if i == 0:
                context = ("#S", )
            else:
                context = words[i-1].__dict__.get(col, "_")
                if config.get("corpus") == "DTAscience" and col == "DTA:NORM" and context == "_":
                    context = words[i-1].__dict__.get("FORM", "_")
                elif col == "XPOS":
                    context = POS_mapping.get(context, context)
                context = (context, )
            
            #Calculate probability
            unigram_prob = ELE_probability(unit, unigram_context, lms[1], lms[0], V)
            bigram_prob = ELE_probability(unit, context, lms[2], lms[1], V)

            #Calculate surprisal
            w.__dict__["UnigramSurpr"+colname] = surprisal(unigram_prob)
            w.__dict__["BigramSurpr"+colname] = surprisal(bigram_prob)

    return doc

################################

def analyze_surprisal_results(doc, **config):
    """
    Analyze surprisal values of relative clauses.

    For each insitu/extrap relative clause in the input data,
    gets position, length, and mean surprisal.
    The results are printed to an output file:

    Corpus, File, Sentence, RelCID, Position, Length, CumSurpr, MeanSurpr

    Input: Doc object (with surprisal annotation)
           and config dictionary with 'eval_dir', 'corpus', and 'lm_models'.
    """

    #Open or create overall result files
    if os.path.isfile(os.path.join(config.get("eval_dir"), "surprisal", "relc_results.csv")):
        overall_results = open(os.path.join(config.get("eval_dir"), "surprisal", "relc_results.csv"), 
                            mode="a", encoding="utf-8")
    else:
        overall_results = open(os.path.join(config.get("eval_dir"), "surprisal", "relc_results.csv"), 
                            mode="w", encoding="utf-8")
        
        #Print header
        print("Corpus", "Filename", "Sentence", "RelC_ID", "Position", "Length", 
              "MeanUniSurprXPOS", "MeanBiSurprXPOS",
              "MeanUniSurprWORD", "MeanBiSurprWORD",
            sep="\t", file=overall_results)
    
    for sent in doc.sentences:
        #For each RelC
        for relc in RelCFinder.get_relcs(sent.MovElems):
            
            #Skip ambiguous RelCs
            if not relc.get_position() in ["extrap", "insitu"]:
                continue

            #Get Length (only count tokens with surprisal annotation)
            length = len([t for t in relc.get_tokens()
                          if "UnigramSurpr"+config.get("lm_models")[0] in t.__dict__ 
                          and t.__dict__["UnigramSurpr"+config.get("lm_models")[0]] != "_"])

            #Collect all surprisal values in RelC
            surprisals = dict()
            for col in config.get("lm_models", []):
                unigram_surprisals = [float(t.__dict__.get("UnigramSurpr"+col))
                                        for t in relc.get_tokens()
                                        if not t.__dict__.get("UnigramSurpr"+col) in ["_", None, "NA"]]
                bigram_surprisals = [float(t.__dict__.get("BigramSurpr"+col))
                                        for t in relc.get_tokens()
                                        if not t.__dict__.get("BigramSurpr"+col) in ["_", None, "NA"]] 

                #Calculate mean surprisal
                surprisals["MeanUniSurpr"+col] = statistics.mean(unigram_surprisals)
                surprisals["MeanBiSurpr"+col] = statistics.mean(bigram_surprisals)
                
            #Store results: Corpus, File, Sentence, RelCID, Position, Length, CumSurpr, MeanSurpr
            print(config.get("corpus"), doc.filename.rstrip(".conllup"), sent.sent_id, 
                  relc.get_ID(), relc.get_position(), length, 
                  "\t".join([str(surprisals[v]) if v in surprisals
                                else "NA"
                                for v in ("MeanUniSurprXPOS", "MeanBiSurprXPOS",
                                          "MeanUniSurprWORD", "MeanBiSurprWORD")]),
                  sep="\t", file=overall_results)

    overall_results.close()

################################

def analyze_dorm_results(orig_doc, variant_doc, **config):
    """
    DORM analysis of relative clauses.

    For each original and variant sentence, calculates
    DORMorig, DORMvariant, and DORMdiff.
    Calculations are performed for word and POS bigram surprisal
    and stored in two output files for token-based and constituent-based analysis:

    Corpus, File, Sentence, DORMorig, DORMvariant, DORMdiff

    Input: Original and variant doc object,
           config dictionary with 'eval_dir', 'corpus', 'model', 
           'norm', and 'lm_models'.
    """

    #Open or create overall result file for token-based analysis
    if os.path.isfile(os.path.join(config.get("eval_dir"), "dorm", "dorm_results_tokens.csv")):
        overall_results_toks = open(os.path.join(config.get("eval_dir"), 
                                                 "dorm", "dorm_results_tokens.csv"), 
                                    mode="a", encoding="utf-8")
    else:
        overall_results_toks = open(os.path.join(config.get("eval_dir"), 
                                                 "dorm", "dorm_results_tokens.csv"), 
                                    mode="w", encoding="utf-8")
        
        #Print header
        print("Corpus", "Filename", "Sentence", 
              "DORMorigXPOS", "DORMvariantXPOS", "DORMdiffXPOS",
              "DORMorigWORD", "DORMvariantWORD", "DORMdiffWORD",
              sep="\t", file=overall_results_toks)
    
    #Open or create overall result file for constituent based analysis
    if os.path.isfile(os.path.join(config.get("eval_dir"), "dorm", "dorm_results_constituents.csv")):
        overall_results_const = open(os.path.join(config.get("eval_dir"), 
                                                 "dorm", "dorm_results_constituents.csv"), 
                                     mode="a", encoding="utf-8")
    else:
        overall_results_const = open(os.path.join(config.get("eval_dir"), 
                                                 "dorm", "dorm_results_constituents.csv"), 
                                     mode="w", encoding="utf-8")
        
        #Print header
        print("Corpus", "Filename", "Sentence", 
              "DORMorigXPOS", "DORMvariantXPOS", "DORMdiffXPOS",
              "DORMorigWORD", "DORMvariantWORD", "DORMdiffWORD",
              sep="\t", file=overall_results_const)

    #For each sentence pair (orig and variant)
    for orig_sent, variant_sent in zip(orig_doc.sentences, variant_doc.sentences):

        #Skip unchanged sentences
        if [(tok.ID, tok.FORM) for tok in orig_sent.tokens] \
            == [(tok.ID, tok.FORM) for tok in variant_sent.tokens]:
            continue

        #Initialize tree for constituent identification
        orig_sent = SimplePTBInitializer().process_sentence(orig_sent, 
                                                            "tree", 
                                                            "PTBstring", 
                                                            config.get("norm", "FORM"))

        if orig_sent.tree is None:
            print("WARNING: No parse tree found. Skipping DORM for constituents.")
        
        else:
            #Get constituents in original sentence
            orig_constituents = []

            #For each token in the tree
            for tok in orig_sent.tree.terminals():
                #Skip punctuation
                if tok.__dict__.get("token", {}).__dict__.get("XPOS", "$").startswith("$"):
                    continue
                else:
                    #Get corresponding token in the sentence
                    token = [t for t in orig_sent.tokens 
                            if t.ID == tok.token.ID][0]

                    #Get parent node
                    parent_node = tok.get_parent()
                    
                    #Select the correct node as constituent
                    #Tueba-style trees
                    if config.get("model") == "news1":
                        while parent_node.get_parent() != None \
                            and not parent_node.get_parent().cat() in ["LV", "VF", "LK", 
                                                                    "C", "MF", "VC", 
                                                                    "MFE", "VCE", "NF", "KOORD"]:
                            parent_node = parent_node.get_parent()
                        if parent_node.get_parent() != None \
                            and parent_node.get_parent().cat() in ["LK", "C", "VC", "VCE"]:
                            parent_node = parent_node.get_parent()
                        if parent_node.cat() == "VROOT":
                            parent_node = tok.get_parent()
                        
                        #Add complete RelCs as constituents
                        if "B-RELC" in token.MovElem and not "I-RELC" in token.MovElem:
                            orig_constituents.append([token])
                        elif "I-RELC" in token.MovElem:
                            orig_constituents[-1].append(token)
                        elif parent_node.cat() in ["LK", "C", "VC", "VCE"] \
                            or parent_node.get_parent() != None \
                                and parent_node.get_parent().cat() in ["LV", "VF", "MF", 
                                                                    "MFE", "NF"]:
                            if not orig_constituents or tok == parent_node.terminals()[0]:
                                orig_constituents.append([token])
                            else:
                                orig_constituents[-1].append(token)
                        else:
                            orig_constituents.append([token])

                    #Tiger-style trees
                    else:
                        while parent_node.get_parent() != None \
                            and parent_node.get_parent().cat().lstrip("C") in ["NP", "PP", "PN", 
                                                                            "NM", "AP", "AVP", 
                                                                            "AA", "VZ"]:
                            parent_node = parent_node.get_parent()

                        #Add complete RelCs as constituents
                        if "B-RELC" in token.MovElem and not "I-RELC" in token.MovElem:
                            orig_constituents.append([token])
                        elif "I-RELC" in token.MovElem:
                            orig_constituents[-1].append(token)
                        elif parent_node.cat().lstrip("C") in ["NP", "PP", "PN", "NM",
                                                            "AP", "AVP", "AA", "VZ"]:
                            if not orig_constituents or tok == parent_node.terminals()[0]:
                                orig_constituents.append([token])
                            else:
                                orig_constituents[-1].append(token)
                        else:
                            orig_constituents.append([token])

            #Get constituents for the variant sentence
            variant_constituents = []
            for tok in variant_sent.tokens:
                if tok.XPOS.startswith("$"):
                    continue
                const = [c for c in orig_constituents 
                        if any(t.ID == tok.ORIG_ID for t in c)][0]
                if not variant_constituents or const[0].ID == tok.ORIG_ID:
                    variant_constituents.append([tok])
                else:
                    variant_constituents[-1].append(tok)

            #Calculate results on constituent basis
            dorms_const = dict()
            for col in config.get("lm_models", []):

                #Calculate DORM of original sentence
                bigram_surprisals = []
                for c in orig_constituents:
                    bigram_surprisals.append(statistics.mean([float(t.__dict__.get("BigramSurpr"+col))
                                                for t in c
                                                if not t.__dict__.get("BigramSurpr"+col) in ["_", "NA", None]])) 
                dorms_const["DORMorig"+col] = dorm(bigram_surprisals)

                #Calculate DORM of variant sentence
                bigram_surprisals = []
                for c in variant_constituents:
                    bigram_surprisals.append(statistics.mean([float(t.__dict__.get("BigramSurpr"+col))
                                                for t in c
                                                if not t.__dict__.get("BigramSurpr"+col) in ["_", "NA", None]]))
                dorms_const["DORMvariant"+col] = dorm(bigram_surprisals)
                if dorms_const["DORMorig"+col] is None or dorms_const["DORMvariant"+col] is None:
                    dorms_const["DORMdiff"+col] = None
                else:
                    dorms_const["DORMdiff"+col] = dorms_const["DORMorig"+col] - dorms_const["DORMvariant"+col]

            #Store result: Corpus, File, Sentence, DORMorig, DORMvariant, DORMdiff
            if None in dorms_const.values():
                continue
            print(config.get("corpus"), orig_doc.filename, orig_sent.sent_id, 
                    "\t".join([str(dorms_const[v]) if v in dorms_const
                                else "NA"
                                for v in ("DORMorigXPOS", "DORMvariantXPOS", "DORMdiffXPOS",
                                        "DORMorigWORD", "DORMvariantWORD", "DORMdiffWORD")]),
                    sep="\t", file=overall_results_const)

        #Calculate results on token basis
        dorms_tok = dict()
        for col in config.get("lm_models", []):

            #Calculate DORM of original sentence
            bigram_surprisals = [float(t.__dict__.get("BigramSurpr"+col))
                                    for t in orig_sent.tokens
                                    if not t.__dict__.get("BigramSurpr"+col) in ["_", "NA", None]] 
            dorms_tok["DORMorig"+col] = dorm(bigram_surprisals)

            #Calculate DORM of variant sentence
            bigram_surprisals = [float(t.__dict__.get("BigramSurpr"+col))
                                    for t in variant_sent.tokens
                                    if not t.__dict__.get("BigramSurpr"+col) in ["_", "NA", None]] 
            dorms_tok["DORMvariant"+col] = dorm(bigram_surprisals)
        
            dorms_tok["DORMdiff"+col] = dorms_tok["DORMorig"+col] - dorms_tok["DORMvariant"+col]

        #Store result: Corpus, File, Sentence, DORMorig, DORMvariant, DORMdiff
        print(config.get("corpus"), orig_doc.filename, orig_sent.sent_id, 
                "\t".join([str(dorms_tok[v]) if v in dorms_tok
                            else "NA"
                            for v in ("DORMorigXPOS", "DORMvariantXPOS", "DORMdiffXPOS",
                                      "DORMorigWORD", "DORMvariantWORD", "DORMdiffWORD")]),
                sep="\t", file=overall_results_toks)

    overall_results_toks.close()
    overall_results_const.close()

################################

