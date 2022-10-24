# -*- coding: utf-8 -*-

import os
from helper_functions import add_dict

##############################

def read_ngrams_from_corpus(doc, col, n=2, 
                            padLeft="#S", padRight="#E", 
                            exclude_punct=True, corpus=None):
    """
    Read n-grams of size n from the input document.

    Given an input document, read all n-grams of size 1..n from the specified column.

    Per default, #S and #E serve as left and right padding elements.
    If n == 1, #S corresponds to the number of sentences.

    If punctuation should be excluded, all tokens with an XPOS tag starting with '$'
    are removed from the sentence beforehand and not included in the n-grams.

    Input:

    Output: Dictionary with n-grams for all sizes 1..n
            {1 : {(Tok1, ) : Freq,
                  (Tok2, ) : Freq, ...},
             ...
             n : {(Tok1, ..., Tok_n) : Freq,
                  ...}
            }
    """
    
    #Map strange POS tags to STTS tags
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

    # {1 : {(Tok1, ) : Freq,
    #       (Tok2, ) : Freq, ...},
    #  2 : {(Tok1, Tok2) : Freq,
    #       ...},
    #  ...
    # }
    ngrams = dict()
    for i in range(n):
        ngrams[i+1] = dict()

    #For each sentence
    for sent in doc.sentences:

        for i in range(n):
            #Create stack for previous elements
            prev_elems = []
            #Add left padding element(s)
            for _ in range(i):
                prev_elems.append(padLeft)

            #Get tokens (without punctuation)
            if exclude_punct:
                if corpus == "DTAscience":
                    tokens = [tok for tok in sent.tokens
                                if not tok.XPOS.startswith("$")
                                and tok.__dict__.get(col, "_").strip()
                                and (col == "DTA:NORM" or tok.__dict__.get(col, "_") != "_")]
                else:
                    tokens = [tok for tok in sent.tokens
                                if not tok.XPOS.startswith("$")
                                and tok.__dict__.get(col, "_").strip()
                                and tok.__dict__.get(col, "_") != "_"]
            else:
                tokens = sent.tokens
            if not tokens:
                continue
            
            #Count sentences
            if i == 0:
                if (padLeft, ) in ngrams[i+1]:
                    ngrams[i+1][(padLeft, )] += 1
                else:
                    ngrams[i+1][(padLeft, )] = 1

            #Collect ngrams
            for tok in tokens:
                value = tok.__dict__.get(col, "_").strip()
                if corpus == "DTAscience" and col == "DTA:NORM" and value == "_":
                    value = tok.__dict__.get("FORM", "_").strip()
                elif col == "XPOS":
                    value = POS_mapping.get(value, value)
                prev_elems.append(value)
                if tuple(prev_elems) in ngrams[i+1]:
                    ngrams[i+1][tuple(prev_elems)] += 1
                else:
                    ngrams[i+1][tuple(prev_elems)] = 1
                del prev_elems[0]
            
            #Pad right
            for _ in range(i):
                prev_elems.append(padRight)
                if tuple(prev_elems) in ngrams[i+1]:
                    ngrams[i+1][tuple(prev_elems)] += 1
                else:
                    ngrams[i+1][tuple(prev_elems)] = 1
                del prev_elems[0]

    return ngrams

###################################

def create_LM(docs, **config):
    """
    Create n-gram language model(s) from input documents.

    Given the input docs, a language model is created
    for each desired column (given as 'lm_models' in config dictionary) 
    and each size between 1 and n (given as 'lm_models_n' in config).

    The language models are stored in 'lm_dir' as tab-separated csv files with two columns.
    The first column contains the n-gram. For n > 1, tokens are separated by spaces.
    The second column contains the frequency.

    #S and #E are used as padding elements.
    #S in the unigram model corresponds to the number of training sentences.

    WORD models use the normalized word form (if available) or FORM (otherwise).

    Input: Iterator over training documents,
           config dictionary with the following keys:
           'lm_models': list of columns to use as LM basis, e.g., ['WORD', 'XPOS']
           'lm_models_n' : defaults to 2
           'corpus' : name of the corpus
    Output: The language models are directly written to files.
    """

    #Get the column names
    column_names = config.get("lm_models", ["WORD"])
    columns = [(c, c) if c != "WORD"
               else (c, config.get("norm"))
               for c in column_names]
    
    #Collect ngrams for each column and n
    ngrams = dict()
    for colname, col in columns:
        ngrams[colname] = dict()
    for doc in docs:
        for colname, col in columns:
            doc_ngrams = read_ngrams_from_corpus(doc, col, 
                                                 config.get("lm_models_n", 2), 
                                                 corpus=config.get("corpus"))
            ngrams[colname] = add_dict(ngrams[colname], doc_ngrams)

    #Print ngrams to files.
    #To make the filename more transparent,
    #use the actual column names (e.g. NORM_BROAD).
    for colname, col in columns:
        for n in range(config.get("lm_models_n", 2)):
            lm_file = open(os.path.join(config.get("lm_dir"), 
                                        str(n+1)+"-gram_"+col.replace(":", "-")+".csv"), 
                           mode="w", encoding="utf-8")
            for key,val in sorted(ngrams[colname][n+1].items()):
                print(" ".join(key), val, sep="\t", file=lm_file)
            lm_file.close()