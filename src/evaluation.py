# -*- coding: utf-8 -*-

import os
from copy import deepcopy
from annotations import Span, MovElem
from FairEval import compare_spans, precision, recall, fscore, overlap_type
from helper_functions import add_dict

#Define labels for evaluation
LABELS = {"chunks" : ["NC", "PC", "AC", "ADVC", "sNC", "sPC"],
          "topf" : ["KOORD", "LV", "VF", "LK", "MF", "RK", "NF"],
          "phrases" : ["NP", "PP", "AP", "ADVP"],
          "brackets" : ["LK", "RK"],
          "extrap" : ["NP-insitu", "NP-extrap", "PP-insitu", "PP-extrap", 
                      "AP-insitu", "AP-extrap", "ADVP-insitu", "ADVP-extrap", 
                      "RELC-insitu", "RELC-ambig", "RELC-extrap"]
         }

######################################

def evaluate_antecedents(goldsent, evalsent):
    """
    Evaluate the accuracy of RelC antecedents.
    
    For the antecedents, instead of the standard span evaluation,
    a separate evaluation is carried out because:
    - antecedents all have the same label, so they don't have LE or LBE errors
    - also, they must always be evaluated with respect to their moving element
      (if the moving element is missing, the antecedent will also be missing;
       if they are linked to the wrong element, they are incorrect anyway)
    - their right boundary is much more important than the span itself
      (a fuzzy match with correct right boundary is enough for determining the
       original position of MovElems and the distance between both)
    - the accuracy likely depends on the distance to the moving element,
    - their head(s) need to be evaluated, too
      (but the head can only be correct if the antecedent is linked to the 
       correct moving element and located in the correct place).

    For each distance (in words, without punctuation) and overall, 
    the output dictionary will contain the following information:

    Correct: antecedents with correct boundaries
             that are linked to the correct moving element
    BES, BEL, BEO: boundary errors of the respective type
                   that are linked to the correct moving element
    BE: any of BES, BEL, BEO
    BEright: any of BES, BEL, BEO for which the
             right boundary is correct (ignoring punctuation)
    IL: antecedents of the correct moving element
        but in an incorrect location (no overlap with correct antecedent)
    FP: antecedents only in the system annotation 
    FN: missing antecedent in the system annotation
    TP_Head_Correct/Right/All: correctly recognized head token 
                               for correct/correct-right-boundary/all moving elements
    FP_Head_Correct/Right/All: head token for correct/correct-right-boundary/all moving elements 
                               that does not exist in the target annotation
    FN_Head_Correct/Right/All: head token for correct/correct-right-boundary/all moving elements 
                               that is missing in the system annotation
    
    The structure of the result dictionary is as follows:

    { 1 : {"Correct" : freq, "IL" : freq, 
            "FP" : freq, "FN" : freq,
            "BES" : freq, "BEL" : freq, "BEO" : freq, 
            "BE" : freq, "BEright" : freq,
            "Head" : {"TP_Correct" : freq, "TP_Right" : freq, "TP_All": freq,
                      "FP_Correct" : freq, "FP_Right" : freq, "FP_All": freq,
                      "FN_Correct" : freq, "FN_Right" : freq, "FN_All": freq}
      2 : ...,
      ...
      "overall" : ...
    }
        
    Only antecedents of relative clauses are evaluated.

    Input: Sentence with target annotation and sentence with system annotation 
    Output: Evaluation dictionary
    """

    #Collect antecedents
    g_antecs = [a for a in goldsent.antecedents 
                if a.get_MovElem() != None 
                   and a.get_MovElem().get_label() == "RELC"
                   and not all(h.XPOS.startswith("V") for h in a.get_headToks())]
    e_antecs = [e for e in evalsent.antecedents 
                if e.get_MovElem() != None 
                   and e.get_MovElem().get_label() == "RELC"]

    #Get distances for gold and system antecedents
    distances = {a.get_distance(goldsent) 
                 for a in g_antecs}.union({a.get_distance(evalsent) 
                                           for a in e_antecs})

    #Prepare evaluation dict
    eval_dict = {}
    for d in distances:
        if d == None:
            continue
        eval_dict[d] = {"Correct" : 0, "BES" : 0, "BEL" : 0, "BEO" : 0, 
                        "BE" : 0, "FP" : 0, "IL" : 0, 
                        "FN" : 0, "BEright" : 0,
                        "TP_Head_Correct" : 0, "FP_Head_Correct": 0, "FN_Head_Correct" : 0,
                        "TP_Head_Right" : 0, "FP_Head_Right": 0, "FN_Head_Right" : 0,
                        "TP_Head_All" : 0, "FP_Head_All": 0, "FN_Head_All" : 0}

    #Match TPs: count antecedents with correct boundaries
    #that are linked to the correct moving element
    matched = []
    for ga in g_antecs: 
        ea_matches = [ea for ea in e_antecs
                      if overlap_type((ga.get_start_index(ignore_punct=True), 
                                       ga.get_end_index(ignore_punct=True)),
                                      (ea.get_start_index(ignore_punct=True), 
                                       ea.get_end_index(ignore_punct=True))) == "TP"
                        and overlap_type((ga.get_MovElem().get_start_index(ignore_punct=True), 
                                          ga.get_MovElem().get_start_index(ignore_punct=True)), 
                                         (ea.get_MovElem().get_start_index(ignore_punct=True), 
                                          ea.get_MovElem().get_start_index(ignore_punct=True))) != False]
        if ea_matches:
            eval_dict[ga.get_distance(goldsent)]["Correct"] += 1
            #Evaluate heads
            ga_head_tok_ids = {t.ID for t in ga.get_headToks()}
            ea_head_tok_ids = {t.ID for t in ea_matches[0].get_headToks()}
            eval_dict[ga.get_distance(goldsent)]["TP_Head_Correct"] += len(ga_head_tok_ids.intersection(ea_head_tok_ids))
            eval_dict[ga.get_distance(goldsent)]["FP_Head_Correct"] += len(ea_head_tok_ids.difference(ga_head_tok_ids))
            eval_dict[ga.get_distance(goldsent)]["FN_Head_Correct"] += len(ga_head_tok_ids.difference(ea_head_tok_ids))
            eval_dict[ga.get_distance(goldsent)]["TP_Head_Right"] += len(ga_head_tok_ids.intersection(ea_head_tok_ids))
            eval_dict[ga.get_distance(goldsent)]["FP_Head_Right"] += len(ea_head_tok_ids.difference(ga_head_tok_ids))
            eval_dict[ga.get_distance(goldsent)]["FN_Head_Right"] += len(ga_head_tok_ids.difference(ea_head_tok_ids))
            eval_dict[ga.get_distance(goldsent)]["TP_Head_All"] += len(ga_head_tok_ids.intersection(ea_head_tok_ids))
            eval_dict[ga.get_distance(goldsent)]["FP_Head_All"] += len(ea_head_tok_ids.difference(ga_head_tok_ids))
            eval_dict[ga.get_distance(goldsent)]["FN_Head_All"] += len(ga_head_tok_ids.difference(ea_head_tok_ids))
            e_antecs.remove(ea_matches[0])
            matched.append(ga)
    for m in matched:
        g_antecs.remove(m)

    #Match BES, BEL, BEO: boundary errors of the respective type
    #that are linked to the correct moving element
    matched = []
    for ga in g_antecs: 
        ea_matches = [ea for ea in e_antecs
                      if overlap_type((ga.get_start_index(ignore_punct=True), 
                                       ga.get_end_index(ignore_punct=True)),
                                      (ea.get_start_index(ignore_punct=True), 
                                       ea.get_end_index(ignore_punct=True))) in ["BES", "BEL", "BEO"]
                        and overlap_type((ga.get_MovElem().get_start_index(ignore_punct=True), 
                                          ga.get_MovElem().get_start_index(ignore_punct=True)), 
                                         (ea.get_MovElem().get_start_index(ignore_punct=True), 
                                          ea.get_MovElem().get_start_index(ignore_punct=True))) != False]
        if ea_matches:
            ot = overlap_type((ga.get_start_index(ignore_punct=True), 
                               ga.get_end_index(ignore_punct=True)),
                              (ea_matches[0].get_start_index(ignore_punct=True), 
                               ea_matches[0].get_end_index(ignore_punct=True)))
            eval_dict[ga.get_distance(goldsent)][ot] += 1

            #Evaluate heads
            ga_head_tok_ids = {t.ID for t in ga.get_headToks()}
            ea_head_tok_ids = {t.ID for t in ea_matches[0].get_headToks()}

            #Check if right boundary is identical
            if ga.get_end_index(ignore_punct=True) == ea_matches[0].get_end_index(ignore_punct=True):
                eval_dict[ga.get_distance(goldsent)]["BEright"] += 1
                eval_dict[ga.get_distance(goldsent)]["TP_Head_Right"] += len(ga_head_tok_ids.intersection(ea_head_tok_ids))
                eval_dict[ga.get_distance(goldsent)]["FP_Head_Right"] += len(ea_head_tok_ids.difference(ga_head_tok_ids))
                eval_dict[ga.get_distance(goldsent)]["FN_Head_Right"] += len(ga_head_tok_ids.difference(ea_head_tok_ids))

            eval_dict[ga.get_distance(goldsent)]["TP_Head_All"] += len(ga_head_tok_ids.intersection(ea_head_tok_ids))
            eval_dict[ga.get_distance(goldsent)]["FP_Head_All"] += len(ea_head_tok_ids.difference(ga_head_tok_ids))
            eval_dict[ga.get_distance(goldsent)]["FN_Head_All"] += len(ga_head_tok_ids.difference(ea_head_tok_ids))

            e_antecs.remove(ea_matches[0])
            matched.append(ga)
    for m in matched:
        g_antecs.remove(m)

    #Sum up fuzzy matches
    for d in distances:
        eval_dict[d]["BE"] += eval_dict[d]["BES"] + eval_dict[d]["BEL"] + eval_dict[d]["BEO"]

    #Match ILs: antecedents of the correct moving element
    #but in an incorrect location (no overlap with correct antecedent)
    matched = []
    for ga in g_antecs: 
        ea_matches = [ea for ea in e_antecs
                      if overlap_type((ga.get_start_index(ignore_punct=True), 
                                       ga.get_end_index(ignore_punct=True)),
                                      (ea.get_start_index(ignore_punct=True), 
                                       ea.get_end_index(ignore_punct=True))) == False
                      and overlap_type((ga.get_MovElem().get_start_index(ignore_punct=True), 
                                        ga.get_MovElem().get_start_index(ignore_punct=True)), 
                                       (ea.get_MovElem().get_start_index(ignore_punct=True), 
                                        ea.get_MovElem().get_start_index(ignore_punct=True))) != False]
        if ea_matches:
            eval_dict[ga.get_distance(goldsent)]["IL"] += 1
            #Evaluate heads
            ga_head_tok_ids = {t.ID for t in ga.get_headToks()}
            ea_head_tok_ids = {t.ID for t in ea_matches[0].get_headToks()}
            eval_dict[ga.get_distance(goldsent)]["TP_Head_All"] += len(ga_head_tok_ids.intersection(ea_head_tok_ids))
            eval_dict[ga.get_distance(goldsent)]["FP_Head_All"] += len(ea_head_tok_ids.difference(ga_head_tok_ids))
            eval_dict[ga.get_distance(goldsent)]["FN_Head_All"] += len(ga_head_tok_ids.difference(ea_head_tok_ids))
            e_antecs.remove(ea_matches[0])
            matched.append(ga)
    for m in matched:
        g_antecs.remove(m)
    
    #Remaining antecedents in gold annotation are FN
    for ga in g_antecs:
        #Evaluate heads
        ga_head_tok_ids = {t.ID for t in ga.get_headToks()}
        eval_dict[ga.get_distance(goldsent)]["FN_Head_All"] += len(ga_head_tok_ids)
        eval_dict[ga.get_distance(goldsent)]["FN"] += 1
    
    #Remaining antecedents in system annotation are FP
    for ea in e_antecs:
        #Evaluate heads
        ea_head_tok_ids = {t.ID for t in ea.get_headToks()}
        eval_dict[ea.get_distance(evalsent)]["FP_Head_All"] += len(ea_head_tok_ids)
        eval_dict[ea.get_distance(evalsent)]["FP"] += 1

    #Sum up result across distances
    eval_dict["overall"] = dict()
    for d in distances:
        add_dict(eval_dict["overall"], eval_dict[d])

    #If there are no antecedents, return zero dict
    if not eval_dict["overall"]:
        eval_dict["overall"] = {"Correct" : 0, "BES" : 0, "BEL" : 0, "BEO" : 0, 
                                "BE" : 0, "FP" : 0, "IL" : 0, 
                                "FN" : 0, "BEright" : 0, 
                                "TP_Head_Correct" : 0, "FP_Head_Correct": 0, "FN_Head_Correct" : 0,
                                "TP_Head_Right" : 0, "FP_Head_Right": 0, "FN_Head_Right" : 0,
                                "TP_Head_All" : 0, "FP_Head_All": 0, "FN_Head_All" : 0}

    return eval_dict

######################################

def evaluate_MovElems(goldsent, evalsent, labels):
    """
    Evaluate the accuracy of moving elements.

    First, the standard span evaluation is performed
    with a concatenation 'label-position' as span label,
    e.g., 'NP-insitu', 'RELC-extrap'.

    In addition to the standard span evaluation there is:
    - a separate evaluation for relative clauses (independent of position)

    So, the standard evaluation dictionary

    {"overall" : {"traditional" : {"TP" : freq, "FP" : freq, "FN" : freq,
                                   "Prec" : val, "Rec" : val, "F1" : val},
                  "fair" : {"TP" : freq, "FP" : freq, "FN" : freq, 
                            "BE" : freq, "BEO" : freq, "BES" : freq, "BEL" : freq, 
                            "LE" : freq, "LBE" : freq,
                            "Prec" : val, "Rec" : val, "F1" : val},
                 },
     "per_label" : {"traditional" : {Lab1 : {"TP" : freq, ...},
                                     Lab2 : ...
                                    },
                    "fair" : {Lab1 : {"TP" : freq, ...},
                              Lab2 : ...}
                   },
     "conf" : {target_lab1 : {system_lab1 : freq,
                              system_lab2 : freq,
                              ...},
               target_lab2 : ...}
    }

    is complemented with an evaluation specific to moving elements:

    {"MovElem" : {"RELC" : {"traditional" : {"TP" : freq, ...},
                            "fair" : {"TP" : freq, ...}
                 }
    }

    Input:
    - Gold sentence with target annotation
    - Evaluation sentence with system annotation
    - List of labels to evaluate

    Output: Evaluation dictionary
    """

    ###################

    def get_MovElem_spans(s, 
                          exclude_non_attributive_relcs=False, 
                          exclude_unknown_position=False):
        """
        Recursively get span tuples (well, actually lists).

        The output spans have the following form:
        [label-position, startIndex, endIndex, {includedTokIDs}]

        Start and end index are determined without punctuation.
        Punctuation is also excluded from the token set.

        Only spans whose label is in the label list are
        included in the output. If desired, non-attributive RelCs
        and MovElems with unknown position can be excluded.

        Input: Span object, 
               whether to exclude non-attributive RelCs (default: False),
               whether to exclude MovElems with position 'unknown' (default: False).
        Output: List of span lists
        """
        spans = []

        #Token element: stop recursion
        if not isinstance(s, MovElem):
            return spans
        
        #Span with relevant label
        if s.get_label() in [l.split("-")[0] for l in labels]:

            if exclude_unknown_position and "unknown" in s.get_position():
                pass

            elif exclude_non_attributive_relcs \
                and s.get_label() == "RELC" \
                and (s.get_antecedent() == None \
                     or all(h.XPOS.startswith("V") 
                            for h in s.get_antecedent().get_headToks())):
                pass

            else:
                #Concatenate label and position
                label = s.get_label() + "-" + s.get_position()

                #Get start and end without punctuation
                start = s.get_start_index(ignore_punct=True)
                end = s.get_end_index(ignore_punct=True)

                #Add span tuple (well, actually list)
                if type(start) == int and type(end) == int:
                    spans.append([label, start, end,
                                {int(t.ID)-1 for t in s.get_tokens() 
                                if t.XPOS[0] != "$"}])
        
        #Recursively repeat for each element in the span
        for e in s.get_elements():
            spans.extend(get_MovElem_spans(e, 
                                           exclude_non_attributive_relcs, 
                                           exclude_unknown_position))

        return spans

    ###################

    #Get target and system annotations
    all_goldspans, movElem_goldspans, evalspans = [], [], []
    for s in goldsent.__dict__.get("MovElems", []):
        all_goldspans.extend(get_MovElem_spans(s))
        movElem_goldspans.extend(get_MovElem_spans(s, 
                                                   exclude_non_attributive_relcs=True, 
                                                   exclude_unknown_position=True))
    for s in evalsent.__dict__.get("MovElems", []):
        evalspans.extend(get_MovElem_spans(s))
    
    #Perform MovElem evaluation with FairEval
    #(Create a copy of the spans for further use, 
    #because FairEval removes spans from the lists.)
    eval_dict = compare_spans(deepcopy(movElem_goldspans), deepcopy(evalspans))
        
    #Evaluate RelCs separately (ignoring position for the moment)
    gold_relcs = [[g[0].split("-")[0]]+g[1:] for g in all_goldspans 
                  if g[0].startswith("RELC")]
    eval_relcs = [[e[0].split("-")[0]]+e[1:] for e in evalspans 
                  if e[0].startswith("RELC")]

    eval_dict_relc = compare_spans(deepcopy(gold_relcs), deepcopy(eval_relcs))
    add_dict(eval_dict, {"MovElem" : {"RELC" : eval_dict_relc["overall"]}})

    return eval_dict

######################################

def evaluate_spans(goldsent, evalsent, annotation, labels):
    """
    Compare system with target span annotations.

    For evaluation, the list of span objects is expected to be
    stored as sentence attribute with the annotation name.
    Only spans whose label is included in the label list
    are evaluated.

    The function collects the spans from both sentences
    and applies the traditional and FairEval evaluation methods.
    The output dictionary has the following structure:

    {"overall" : {"traditional" : {"TP" : freq, "FP" : freq, "FN" : freq},
                  "fair" : {"TP" : freq, "FP" : freq, "FN" : freq, 
                            "BE" : freq, "BEO" : freq, "BES" : freq, "BEL" : freq, 
                            "LE" : freq, "LBE" : freq},
                 },
     "per_label" : {"traditional" : {Lab1 : {"TP" : freq, ...},
                                     Lab2 : ...
                                    },
                    "fair" : {Lab1 : {"TP" : freq, ...},
                              Lab2 : ...}
                   },
     "conf" : {target_lab1 : {system_lab1 : freq,
                              system_lab2 : freq,
                              ...},
               target_lab2 : ...}
    }

    Input:
    - Gold sentence with target annotation
    - Evaluation sentence with system annotation
    - Annotation name (e.g., 'chunks')
    - List of labels to evaluate

    Output: Evaluation dictionary
    """

    ###################

    def get_spans(s):
        """
        Recursively get span tuples (well, actually lists).

        The output spans have the following form:
        [label, startIndex, endIndex, {includedTokIDs}]

        Start and end index are determined without punctuation.
        Punctuation is also excluded from the token set.

        Only spans whose label is in the label list are
        included in the output.

        Input: Span object
        Output: List of span lists
        """
        spans = []

        #Token element: stop recursion
        if type(s) != Span:
            return spans

        #Span with relevant label
        if s.get_label() in labels:

            #Get start and end without punctuation
            start = s.get_start_index(ignore_punct=True)
            end = s.get_end_index(ignore_punct=True)

            #Add span tuple (well, actually list)
            if type(start) == int and type(end) == int:
                spans.append([s.get_label(), start, end,
                            {int(t.ID)-1 for t in s.get_tokens() 
                             if t.XPOS[0] != "$"}])

        #Recursively repeat for each element in the span
        for e in s.get_elements():
            spans.extend(get_spans(e))

        return spans
    
     ###################

    #Get target and system annotations
    goldspans, evalspans = [], []
    for s in goldsent.__dict__.get(annotation, []):
        goldspans.extend(get_spans(s))
    for s in evalsent.__dict__.get(annotation, []):
        evalspans.extend(get_spans(s))

    #Perform evaluation with FairEval
    eval_dict = compare_spans(goldspans, evalspans)

    #Return evaluation dictionary
    return eval_dict

######################################

def calculate_metrics_antecedent(evaldict):
    """
    Calculate precision, recall, F1 score,
    and accuracy values for antecedents.

    Values are added to the dictionary 
    as 'Prec', 'Rec', 'F1', 'F1right'.

    Also calculates traditional precision, recall, and F1 values
    for head token(s) of correct/correct-right-boundary/all antecedents.

    Input: Dictionary with error counts.
    Output: Dictionary including results.
    """
    #Initialize dictionary with error categories for evaluation
    fair_eval_dict = {}
    fair_eval_dict["BE"] = evaldict["BE"]
    fair_eval_dict["TP"] = evaldict["Correct"]
    fair_eval_dict["FP"] = evaldict["FP"] + 0.5 * evaldict["IL"]
    fair_eval_dict["FN"] = evaldict["FN"] + 0.5 * evaldict["IL"]

    #Calculate results
    evaldict["Prec"] = precision(fair_eval_dict, "fair")
    evaldict["Rec"] = recall(fair_eval_dict, "fair")
    evaldict["F1"] = fscore(evaldict)

    #Calculate F1 with right-aligned as TP
    fair_eval_dict["BEright"] = evaldict["BEright"]
    fair_eval_dict["BE"] = evaldict["BE"] - evaldict["BEright"]
    prec_right = precision(fair_eval_dict, "weighted", 
                           {"TP" : {"TP" : 1},
                            "FP" : {"FP" : 1},
                            "FN" : {"FN" : 1},
                            "BEright" : {"TP" : 1},
                            "BE" : {"FP" : 0.5, "FN" : 0.5}}
                           )
    rec_right = recall(fair_eval_dict, "weighted", 
                        {"TP" : {"TP" : 1},
                        "FP" : {"FP" : 1},
                        "FN" : {"FN" : 1},
                        "BEright" : {"TP" : 1},
                        "BE" : {"FP" : 0.5, "FN" : 0.5}}
                      )
    evaldict["F1right"] = fscore({"Prec" : prec_right, "Rec" : rec_right})
    
    #Initialize dictionary with error categories 
    #for traditional evaluation of antecedent head(s)
    for group in ("Correct", "Right", "All"):
        head_eval_dict = {}
        head_eval_dict["TP"] = evaldict["TP_Head_"+group]
        head_eval_dict["FP"] = evaldict["FP_Head_"+group]
        head_eval_dict["FN"] = evaldict["FN_Head_"+group]

        #Evaluate antecedent head(s)
        evaldict["Head_"+group+"_Prec"] = precision(head_eval_dict)
        evaldict["Head_"+group+"_Rec"] = recall(head_eval_dict)
        evaldict["Head_"+group+"_F1"] = fscore({"Prec" : evaldict["Head_"+group+"_Prec"],
                                                "Rec" : evaldict["Head_"+group+"_Rec"]})

    return evaldict

######################################

def calculate_metrics(evaldict, version):
    """
    Calculate precision, recall and F1 score
    with the given evaluation method.

    Values are added to the dictionary 
    as 'Prec', 'Rec', and 'F1'.

    Input: Dictionary with error counts
           and evaluation method ('traditional' or 'fair').
    Output: Dictionary including results.
    """
    #Add precision, recall and f1 values
    evaldict["Prec"] = precision(evaldict, version)
    evaldict["Rec"] = recall(evaldict, version)
    evaldict["F1"] = fscore(evaldict)

    return evaldict

######################################

def evaluate_file(golddoc, evaldoc, **kwargs):
    """
    Compare gold and system annotations to calculate evaluation results.

    If the annotation is one of 'brackets', 'topf', 'chunks', 'phrases', or 'ner',
    applies the traditional and FairEval algorithms and outputs an evaluation
    dictionary with the following structure:

    {"overall" : {"traditional" : {"TP" : freq, "FP" : freq, "FN" : freq,
                                   "Prec" : val, "Rec" : val, "F1" : val},
                  "fair" : {"TP" : freq, "FP" : freq, "FN" : freq, 
                            "BE" : freq, "BEO" : freq, "BES" : freq, "BEL" : freq, 
                            "LE" : freq, "LBE" : freq,
                            "Prec" : val, "Rec" : val, "F1" : val},
                 },
     "per_label" : {"traditional" : {Lab1 : {"TP" : freq, ...},
                                     Lab2 : ...
                                    },
                    "fair" : {Lab1 : {"TP" : freq, ...},
                              Lab2 : ...}
                   },
     "conf" : {target_lab1 : {system_lab1 : freq,
                              system_lab2 : freq,
                              ...},
               target_lab2 : ...}
    }

    If the annotation is 'extrap', evaluates the moving elements
    and also their antecedents.

    For the antecedents, instead of the standard span evaluation,
    a separate evaluation is performed because:
    - antecedents all have the same label, so they don't have LE or LBE errors
    - also, they must always be evaluated with respect to their moving element
      (if the moving element is missing, the antecedent will also be missing;
       if they are linked to the wrong element, they are incorrect anyway)
    - their right boundary is much more important than the span itself
      (a fuzzy match with correct right boundary is enough for determining the
       original position of MovElems and the distance between both)
    - the accuracy likely depends on the distance to the moving element
    - their head(s) have to be evaluated, too, but can only be correct
      for correct/fuzzy-match antecedents.

    The output dictionary from above is thus complemented 
    with the following key-value pairs:

    {"Antec" :  { 1 : {"Correct" : freq, "IL" : freq, 
                       "FP" : freq, "FN" : freq,
                       "BES" : freq, "BEL" : freq, "BEO" : freq, 
                       "BE" : freq, "BEright" : 0,
                       "TP_Head" : freq, "FP_Head" : freq, "FN_Head" : freq,
                       "Prec" : val, "Rec" : val, "F1" : val, "F1right" : val,
                       "Head_Correct_Prec" : val, "Head_Correct_Rec" : val, "Head_Correct_F1" : val,
                       "Head_Right_Prec" : val, "Head_Right_Rec" : val, "Head_Right_F1" : val,
                       "Head_All_Prec" : val, "Head_All_Rec" : val, "Head_All_F1" : val}
                  2 : ...,
                  ...
                  "overall" : ...}
                }
    }

    Input:
    - Doc object with gold annotations (golddoc)
    - Doc with system annotations (evaldoc)
    - Additional key-word arguments ('annotation', 'corpus')
    Output: Evaluation dictionary with overall and per-label
            results according to different evaluation methods
            plus confusion matrix.
    """
    ######################

    print(golddoc.filename)

    annotation = kwargs.get("annotation", "")

    #For some corpora, only RelC MovElems are annotated
    if annotation == "extrap" \
        and kwargs.get("corpus", "") in ["Tiger"]:#, "TuebaDS"]:
        LABELS["extrap"] = ["RELC-insitu", "RELC-ambig", "RELC-extrap"]
    labels = LABELS.get(annotation, [])

    #Create empty eval dict for doc
    eval_dict = {"overall" : {"traditional" : {"TP" : 0, "FP" : 0, "FN" : 0},
                              "fair" : {"TP" : 0, "FP" : 0, "FN" : 0, "LE" : 0, "BE" : 0, 
                                        "BEO" : 0, "BES" : 0, "BEL" : 0, "LBE" : 0}},
                 "per_label" : {"traditional" : {},
                                "fair" : {}},
                 "conf" : {}}
    
    #For each sentence pair
    for goldsent, evalsent in zip(golddoc.sentences, evaldoc.sentences):

        #Get result dict for sentence
        sent_counts = evaluate_spans(goldsent, evalsent, annotation, labels)

        #For moving elements, get additional results
        if annotation == "extrap":
            eval_movElem = evaluate_MovElems(goldsent, evalsent, labels)
            eval_antec = {"Antec" : evaluate_antecedents(goldsent, evalsent)}
            add_dict(sent_counts, eval_movElem)
            add_dict(sent_counts, eval_antec)

        #Add results to eval dict
        add_dict(eval_dict, sent_counts)

    #Calculate overall results for traditional and fair evaluation
    for version in ["traditional", "fair"]:
        calculate_metrics(eval_dict["overall"][version], version)
        #Also for RelCs
        if annotation == "extrap":
            calculate_metrics(eval_dict["MovElem"]["RELC"][version], version)
        #And per label
        for label in eval_dict["per_label"][version]:
            calculate_metrics(eval_dict["per_label"][version][label], version)
    
    #Calculate overall results for antecedents
    if annotation == "extrap":
        for key in eval_dict["Antec"]:
            calculate_metrics_antecedent(eval_dict["Antec"][key])
    
    return eval_dict

###########################

def overall_results(eval_dict, annotation):
    """
    Take evaluation results for different corpus files
    and calculate overall results (across documents).

    The function takes a dictionary with evaluation
    results for one or more files and adds up frequencies.
    Then, the overall frequencies are used to calculate
    different evaluation metrics (depending on the annotation).

    The input dictionary, e.g., looks as follows:

    {"per_file" : {filename1 : {"overall" : ...,
                                "per_label" : ...,
                                "conf" : ...},
                   filename2 : ...}
    }

    The output dictionary contains an additional key 'overall':
    {"overall" : {"overall" : ...,
                  "per_label" : ...,
                  "conf" : ...}
    }

    Input: Evaluation dictionary, annotation name.
    Output: Evaluation dictionary.
    """
    
    #Add up results from all files
    eval_dict["overall"] = {}
    for f in eval_dict["per_file"]:
        add_dict(eval_dict["overall"], eval_dict["per_file"][f])
    
    #Calculate overall results for traditional and fair evaluation
    for version in ["traditional", "fair"]:
        calculate_metrics(eval_dict["overall"]["overall"][version], version)
        #Also for RelCs
        if annotation == "extrap":
            calculate_metrics(eval_dict["overall"]["MovElem"]["RELC"][version], version)
        #And per label
        for label in eval_dict["overall"]["per_label"][version]:
            calculate_metrics(eval_dict["overall"]["per_label"][version][label], version)

    #Calculate overall results for antecedents
    if annotation == "extrap":
        for key in eval_dict["overall"]["Antec"]:
            calculate_metrics_antecedent(eval_dict["overall"]["Antec"][key])
    
    return eval_dict

############################

def output_results(evaldict, **kwargs):
    """
    Print the evaluation results to a file.

    For each annotation, a separate folder is used/created.
    The output files are named after corpus and model.
    
    Each output file (if applicable) contains:
    - traditional and fair evaluation results per file and overall
    - traditional and fair evaluation results per label and overall
    - a confusion matrix

    For the evaluation of moving elements,
    1) the results as described above are saved in the 'extrap' folder
    2) additional results for antecedents are saved in the 'antec' folder
    3) additional results for relative clauses are saved in the 'relc' folder

    Input: Evaluation dictionary and additional key-word arguments
           (e.g., 'eval_dir', 'annotation', 'corpus', 'model')
    """

    #Output directory depending on the annotation
    outdir = os.path.join(kwargs.get("eval_dir"), 
                          kwargs.get("annotation"))
    #Create if necessary
    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    #Filename depending on corpus and model
    filename = kwargs.get("corpus") + "_" + kwargs.get("model") + ".csv"
    evalfile = open(os.path.join(outdir, filename), mode="w", encoding="utf-8")

    for version in ["traditional", "fair"]:
        if version == "traditional":
            columns = ["TP", "FP", "FN", "Prec", "Rec", "F1"]
        else:
            columns = ["TP", "FP", "LE", "BE", "BES", "BEL", "BEO", 
                       "LBE", "FN", "Prec", "Rec", "F1"]

        #Print header
        print("#", version.title(), "evaluation", file=evalfile)
        print(file=evalfile)
        print("## Per file", file=evalfile)
        print(file=evalfile)
        
        #Print filename and values for each file
        print("file", "\t".join(columns), sep="\t", file=evalfile)
        for file, results in evaldict["per_file"].items():
            print(os.path.splitext(file)[0], 
                  "\t".join([str(results["overall"][version][col]) 
                             for col in columns]), 
                  sep="\t", file=evalfile)
        
        #Print overall results
        print("overall", 
              "\t".join([str(evaldict["overall"]["overall"][version][col]) 
                         for col in columns]), 
              sep="\t", file=evalfile)

        #Print label and results per label
        print(file=evalfile)
        print("## Per label", file=evalfile)
        print(file=evalfile)
        print("label", "\t".join(columns), sep="\t", file=evalfile)
        
        for label in LABELS.get(kwargs.get("annotation"), []):
            print(label, 
                  "\t".join([str(evaldict["overall"]["per_label"][version][label][col]) 
                             for col in columns]), 
                  sep="\t", file=evalfile)

        print(file=evalfile)

    #Print confusion matrix
    print("# Confusion matrix", file=evalfile)
    print(file=evalfile)

    #Get list of all existing labels
    #These are used for columns and rows
    labels = {lab for lab in evaldict["overall"]["conf"]}
    labels = list(labels.union({syslab for lab in evaldict["overall"]["conf"] 
                                for syslab in evaldict["overall"]["conf"][lab]}))
    labels.sort()

    #Output matrix
    print(r"Target\System", "\t".join(labels), sep="\t", file=evalfile)
    for goldlab in labels:
        print(goldlab, 
              "\t".join([str(evaldict["overall"]["conf"][goldlab].get(syslab, 0)) 
                         for syslab in labels]), 
              sep="\t", file=evalfile)

    evalfile.close()

    #For evaluation of moving elements
    #create separate output for antecedents and RelCs
    if kwargs.get("annotation") == "extrap":
        
        #Output directory for antecedents
        outdir = os.path.join(kwargs.get("eval_dir"), 
                              "antec")
        #Create if necessary
        if not os.path.isdir(outdir):
            os.makedirs(outdir)

        #Open evaluation file in antec folder
        evalfile = open(os.path.join(outdir, filename), mode="w", encoding="utf-8")

        columns = ["Correct", "BE", "BES", "BEL", "BEO", 
                   "BEright", "IL", "FP", "FN",
                   "Prec", "Rec", "F1", "F1right"]
        
        #Print header
        print("# Per file", file=evalfile)
        print(file=evalfile)

        #Print filename and overall values for each file
        print("file", "\t".join(columns), sep="\t", file=evalfile)
        for file, results in evaldict["per_file"].items():
            print(os.path.splitext(file)[0], 
                  "\t".join([str(results["Antec"]["overall"][col]) 
                             for col in columns]), 
                  sep="\t", file=evalfile)
        
        #Print overall results
        print("overall", 
              "\t".join([str(evaldict["overall"]["Antec"]["overall"][col]) 
                         for col in columns]), 
              sep="\t", file=evalfile)

        #Print distance and results per distance
        print(file=evalfile)
        print("# Per distance", file=evalfile)
        print(file=evalfile)
        print("distance", "\t".join(columns), sep="\t", file=evalfile)

        #To sort by distance, use 999 for the "overall" result
        def sort_dist(d):
            if isinstance(d, (int, float)):
                return d
            else:
                return 999
        for d in sorted(evaldict["overall"]["Antec"],
                        key=lambda d : sort_dist(d)):
            print(d, 
                  "\t".join([str(evaldict["overall"]["Antec"][d][col]) 
                             for col in columns]), 
                  sep="\t", file=evalfile)

        #Print head evaluation
        columns_head = ["TP_Head_Correct", "FP_Head_Correct", "FN_Head_Correct",
                        "TP_Head_Right", "FP_Head_Right", "FN_Head_Right",
                        "TP_Head_All", "FP_Head_All", "FN_Head_All",
                        "Head_Correct_Prec", "Head_Correct_Rec", "Head_Correct_F1",
                        "Head_Right_Prec", "Head_Right_Rec", "Head_Right_F1",
                        "Head_All_Prec", "Head_All_Rec", "Head_All_F1"]

        #Print header
        print(file=evalfile)
        print("# Head", file=evalfile)
        print(file=evalfile)

        #Print filename and overall values for each file
        print("file", "\t".join(columns_head), sep="\t", file=evalfile)
        for file, results in evaldict["per_file"].items():
            print(os.path.splitext(file)[0], 
                  "\t".join([str(results["Antec"]["overall"][col]) 
                             for col in columns_head]), 
                  sep="\t", file=evalfile)
        
        #Print overall results
        print("overall", 
              "\t".join([str(evaldict["overall"]["Antec"]["overall"][col]) 
                         for col in columns_head]), 
              sep="\t", file=evalfile)

        evalfile.close()

        #Output directory for RelCs
        outdir = os.path.join(kwargs.get("eval_dir"), 
                              "relc")
        #Create if necessary
        if not os.path.isdir(outdir):
            os.makedirs(outdir)

        #Open evaluation file in relc folder
        evalfile = open(os.path.join(outdir, filename), mode="w", encoding="utf-8")

        for version in ["traditional", "fair"]:
            if version == "traditional":
                columns = ["TP", "FP", "FN", "Prec", "Rec", "F1"]
            else:
                columns = ["TP", "FP", "LE", "BE", "BES", "BEL", "BEO", 
                           "LBE", "FN", "Prec", "Rec", "F1"]

            #Print header
            print("#", version.title(), "evaluation", file=evalfile)
            print(file=evalfile)
            print("## Per file", file=evalfile)
            print(file=evalfile)
            
            #Print filename and values for each file
            print("file", "\t".join(columns), sep="\t", file=evalfile)
            for file, results in evaldict["per_file"].items():
                print(os.path.splitext(file)[0], 
                    "\t".join([str(results["MovElem"]["RELC"][version][col]) 
                                for col in columns]), 
                    sep="\t", file=evalfile)
            
            #Print overall results
            print("overall", 
                "\t".join([str(evaldict["overall"]["MovElem"]["RELC"][version][col]) 
                            for col in columns]), 
                sep="\t", file=evalfile)

            print(file=evalfile)

        evalfile.close()
        
############################

def read_table(file):
    """
    Read tables from files created by output_results.

    Headings (# ) and subheadings (## ) are used as keys
    (e.g., traditional vs. fair evaluation 
     or different types of annotations in stats file)
    and the table rows are stored as values in list format.
    
    Input: Filename
    Output: Table as dictionary
    """
    f = open(file, mode="r", encoding="utf-8")
    lines = f.readlines()
    f.close()

    section = ""
    subsection = ""
    table = {}
    for l in lines:
        
        if l.startswith("# "):
            section = l[2:].strip()
            table[section] = {}
        
        elif l.startswith("## "):
            subsection = l[3:].strip()
            table[section][subsection] = []
            
        elif not l.strip():
            continue
            
        else:
            if subsection in table[section]:
                table[section][subsection].append(l.strip().split("\t"))
            else:
                if isinstance(table[section], dict):
                    table[section] = []
                table[section].append(l.strip().split("\t"))

    return table

############################

def output_tables(**kwargs):
    """
    Arrange evaluation results and data stats into LaTeX tables
    and input tables for R.

    Input: Key-word arguments ('annotations', 'eval_dir')
    """
    
    #Add relative clauses to annotations
    annotations = kwargs.get("annotations", [])
    if "extrap" in annotations:
        annotations.append("relc")

    #For each annotation
    for annotation in annotations:
        print("Creating tables for", annotation)

        #Store tables in table folder
        outdir = os.path.join(kwargs.get("eval_dir", "eval"), "tables", annotation)
        if not os.path.isdir(outdir):
            os.makedirs(outdir)

        #Evaluation results are stored in annotation folders in eval_dir
        evaldir = os.path.join(kwargs.get("eval_dir", "eval"), annotation)
        if not os.path.isdir(evaldir):
            print("ERROR: Annotation", annotation, "not found.")
            continue
        resultfiles = [os.path.join(evaldir, f) for f in os.listdir(evaldir)]

        #Get corpora and their pretty names
        corpora = set([os.path.split(f)[-1].split("_")[0] for f in resultfiles])
        corpora = [c for c in [("TuebaDZ", "TüBa-D/Z"), ("Tiger", "Tiger"), 
                               ("TuebaDS", "Spoken"), ("Modern", "Modern"), 
                               ("Mercurius", "Mercurius"), ("ReF.UP", "ReF.UP"),
                               ("HIPKON", "HIPKON"), ("DTA", "DTA")] 
                  if c[0] in corpora]

        #Get models and their pretty names
        models = set([os.path.splitext(os.path.split(f)[-1])[0].split("_")[1] 
                     for f in resultfiles])
        models = [m for m in [("news1", "News1"), ("news2", "News2"), 
                              ("hist", "Hist"), ("mix", "Mix"), 
                              ("topfpunct", "Punct"), ("topfnopunct", "NoPunct")] 
                  if m[0] in models]
        #Move News1 model to final position for topofields and brackets
        if annotation in ["topf", "brackets"] and ("news1", "News1") in models:
            models.remove(("news1", "News1"))
            models.append(("news1", "News1"))

        #Tab 1a: overall Prec, Rec and F1
        #Line: corpus
        #Column: model, subcolumns: Prec, Rec, F1
        #Upper part: traditional; Lower part: FairEval
        tablefile = open(os.path.join(outdir, "tab_overall.tex"), mode="w", encoding="utf-8")
        print(r"\begin{table}[ht]", file=tablefile)
        print(r"\begin{tabular}{l" 
                + r"".join([r"".join(["c"]*3)]*len(models))+"}", 
                file=tablefile)
        print(r"\toprule", file=tablefile)
        print("", " & ".join([r"\multicolumn{3}{c}{\texttt{"+m[1]+"}}" for m in models]), 
              sep=" & ", end=r" \\"+"\n", file=tablefile)
        print("Corpus", " & ".join(["Prec", "Rec", "F1"]*len(models)), 
              sep=" & ", end=r" \\"+"\n", file=tablefile)
        print(r"\midrule", file=tablefile)
        
        #For each evaluation version
        for v in ["Traditional", "Fair"]:
            print(r"\multicolumn{%d}{l}{\textit{%s}}" % (len(models)*3+1, 
                  v.replace("Fair", "FairEval")), 
                  end=r" \\"+"\n", file=tablefile)
            #For each corpus
            for corpus, corpusname in corpora:
                res = []
                #For each model
                for model, _ in models:
                    try:
                        #Get precision, recall, and F1 from table
                        table = read_table(os.path.join(evaldir, corpus + "_" + model + ".csv"))
                        table = table[v + " evaluation"]["Per file"]
                        res.append([float(l[-3])*100 for l in table 
                                    if l[0] == "overall"][0])
                        res.append([float(l[-2])*100 for l in table 
                                    if l[0] == "overall"][0])
                        res.append([float(l[-1])*100 for l in table 
                                    if l[0] == "overall"][0])
                    #If model was not used for this corpus, output dash
                    except FileNotFoundError:
                        res.append(None)
                        res.append(None)
                        res.append(None)
                #Output corpus, Prec, Rec, and F1 for each model
                #Bold-face best values per corpus
                print(corpusname, 
                    " & ".join(["-"
                                if r == None
                                else r"\textbf{%s}" % "{:04.2f}".format(r) 
                                    if i in range(0, 30, 3) \
                                       and r == max([x for x in res[::3] 
                                                    if x != None])
                                    or i in range(1, 30, 3) \
                                       and r == max([x for x in res[1::3] 
                                                     if x != None])
                                    or i in range(2, 30, 3) \
                                       and r == max([x for x in res[2::3] 
                                                     if x != None])
                                    else "{:04.2f}".format(r) 
                                for i, r in enumerate(res)]), 
                    sep=" & ", end=r" \\"+"\n", file=tablefile)
        print(r"\bottomrule", file=tablefile)
        print(r"\end{tabular}", file=tablefile)
        print(r"""\caption{Overall precision, recall, and F\textsubscript{1}-scores 
                  (in percent) according to traditional and fair evaluation
                  for the different models on each data set. The highest scores
                  for each corpus are highlighted in bold.}""", 
              file=tablefile)
        print(r"\label{tab:%s_overall}" % annotation, file=tablefile)
        print(r"\end{table}", file=tablefile)
        tablefile.close()

        #Tab 1b: overall Prec, Rec and F1 (FairEval only)
        #Line: corpus
        #Column: model, subcolumns: Prec, Rec, F1
        tablefile = open(os.path.join(outdir, "tab_overall_FairEval.tex"), 
                         mode="w", encoding="utf-8")
        print(r"\begin{table}[ht]", file=tablefile)
        print(r"\begin{tabular}{l" 
                + r"".join([r"".join(["c"]*3)]*len(models))+"}", 
                file=tablefile)
        print(r"\toprule", file=tablefile)
        print("", " & ".join([r"\multicolumn{3}{c}{\texttt{"+m[1]+"}}" for m in models]), 
              sep=" & ", end=r" \\"+"\n", file=tablefile)
        print("Corpus", " & ".join(["Prec", "Rec", "F1"]*len(models)), 
              sep=" & ", end=r" \\"+"\n", file=tablefile)
        print(r"\midrule", file=tablefile)
        
        #For each corpus
        for corpus, corpusname in corpora:
            res = []
            #For each model
            for model, _ in models:
                try:
                    #Get precision, recall, and F1 from table
                    table = read_table(os.path.join(evaldir, corpus + "_" + model + ".csv"))
                    table = table["Fair evaluation"]["Per file"]
                    res.append([float(l[-3])*100 for l in table 
                                if l[0] == "overall"][0])
                    res.append([float(l[-2])*100 for l in table 
                                if l[0] == "overall"][0])
                    res.append([float(l[-1])*100 for l in table 
                                if l[0] == "overall"][0])
                #If model was not used for this corpus, output dash
                except FileNotFoundError:
                    res.append(None)
                    res.append(None)
                    res.append(None)
            #Output corpus, Prec, Rec, and F1 for each model
            #Bold-face best values per corpus
            print(corpusname, 
                " & ".join(["-"
                            if r == None
                            else r"\textbf{%s}" % "{:04.2f}".format(r) 
                                if i in range(0, 30, 3) \
                                   and r == max([x for x in res[::3] 
                                                 if x != None])
                                or i in range(1, 30, 3) \
                                   and r == max([x for x in res[1::3] 
                                                 if x != None])
                                or i in range(2, 30, 3) \
                                   and r == max([x for x in res[2::3] 
                                                 if x != None])
                                else "{:04.2f}".format(r) 
                            for i, r in enumerate(res)]), 
                sep=" & ", end=r" \\"+"\n", file=tablefile)
        print(r"\bottomrule", file=tablefile)
        print(r"\end{tabular}", file=tablefile)
        print(r"""\caption{Overall precision, recall, and F\textsubscript{1}-scores 
                  (in percent) according to \textit{FairEval}
                  for the different models on each data set. The highest scores
                  for each corpus are highlighted in bold.}""", 
              file=tablefile)
        print(r"\label{tab:%s_overall_FairEval}" % annotation, file=tablefile)
        print(r"\end{table}", file=tablefile)
        tablefile.close()

        #Tab 2a: F1 per label (for best model, FairEval only)
        #Line: corpus
        #Column: label
        #Special table for MovElem labels, skip here
        if annotation != "extrap":
            tablefile = open(os.path.join(outdir, "tab_F1_per_label_FairEval.tex"), 
                             mode="w", encoding="utf-8")
            print(r"\begin{table}[ht]", file=tablefile)
            print(r"\begin{tabular}{l" + "c"*len(LABELS.get(annotation, []))+"}", file=tablefile)
            print(r"\toprule", file=tablefile)
            print("Corpus", 
                  " & ".join([r"\texttt{"+lab+"}" 
                              for lab in LABELS.get(annotation, [])]), 
                  sep=" & ", end=r" \\"+"\n", file=tablefile)
            print(r"\midrule", file=tablefile)

            #For each corpus
            for corpus, corpusname in corpora:
                f1 = []
                best_model = models[0][0]
                best_f1 = 0
                #For each model
                for model, _ in models:
                    try:
                        #Read table and find model with best overall F1
                        table = read_table(os.path.join(evaldir, corpus + "_" + model + ".csv"))
                        table = table["Fair evaluation"]["Per file"]
                        f = [float(l[-1])*100 for l in table 
                                if l[0] == "overall"][0]
                        if f > best_f1:
                            best_model = model
                            best_f1 = f
                    #Model not used for this corpus
                    except FileNotFoundError:
                        continue
                #Then for each label
                for lab in LABELS.get(annotation, []):          
                    try:
                        #Take best model
                        table = read_table(os.path.join(evaldir, corpus + "_" + best_model + ".csv"))
                        table = table["Fair evaluation"]["Per label"]
                        f1.append([float(l[-1])*100 for l in table 
                                        if l[0] == lab][0])
                    except:
                        f1.append(0.00)
                #Output F1 for each label of best model for each corpus
                print(corpusname, 
                    " & ".join(["{:04.2f}".format(f)
                                for f in f1]), 
                    sep=" & ", end=r" \\"+"\n", file=tablefile)
            print(r"\bottomrule", file=tablefile)
            print(r"\end{tabular}", file=tablefile)
            print(r"""\caption{Overall F\textsubscript{1}-scores for each label (in percent) 
                               according to \extit{FairEval}
                               for the best performing model on each data set.}""", 
                file=tablefile)
            print(r"\label{tab:%s_F1_per_label_FairEval}" % annotation, file=tablefile)
            print(r"\end{table}", file=tablefile)
            tablefile.close()

        #Table for MovElem labels
        else:
            #Separate labels and positions
            labels = [lab.split("-")[0]
                      for lab in LABELS.get(annotation, [])]
            unique_labels = []
            [unique_labels.append(l) for l in labels
             if not l in unique_labels]
            positions = [lab.split("-")[1]
                         for lab in LABELS.get(annotation, [])]

            tablefile = open(os.path.join(outdir, "tab_F1_per_label_FairEval.tex"), 
                             mode="w", encoding="utf-8")
            print(r"\begin{table}[ht]", file=tablefile)
            print(r"\begin{tabular}{l" 
                    + r"".join([r"".join(["c"]*2)]*(len(labels)-1))
                    + r"".join(["c"]*3) + "}", 
                  file=tablefile)
            print(r"\toprule", file=tablefile)
            print("", 
                  " & ".join([r"\multicolumn{3}{c}{"+lab+"}" 
                              if lab == "RELC"
                              else r"\multicolumn{2}{c}{"+lab+"}" 
                              for lab in unique_labels]), 
                  sep=" & ", end=r" \\"+"\n", file=tablefile)
            print("Corpus", " & ".join(positions),
                  sep=" & ", end=r" \\"+"\n", file=tablefile)
            print(r"\midrule", file=tablefile)

            #For each corpus
            for corpus, corpusname in corpora:
                f1 = []
                best_model = models[0][0]
                best_f1 = 0
                #For each model
                for model, _ in models:
                    try:
                        #Read table and find model with best overall F1
                        table = read_table(os.path.join(evaldir, corpus + "_" + model + ".csv"))
                        table = table["Fair evaluation"]["Per file"]
                        f = [float(l[-1])*100 for l in table 
                                if l[0] == "overall"][0]
                        if f > best_f1:
                            best_model = model
                            best_f1 = f
                    #Model not used for this corpus
                    except FileNotFoundError:
                        continue
                #Then for each label
                for lab, pos in zip(labels, positions):          
                    try:
                        #Take best model
                        table = read_table(os.path.join(evaldir, corpus + "_" + best_model + ".csv"))
                        table = table["Fair evaluation"]["Per label"]
                        f1.append([float(l[-1])*100 for l in table 
                                        if l[0] == lab+"-"+pos][0])
                    except:
                        f1.append(0.00)
                #Output F1 for each label of best model for each corpus
                print(corpusname, 
                    " & ".join(["-"
                                if f == 0.00 and corpusname in ["Tiger"]
                                else "{:04.2f}".format(f)
                                for f in f1]), 
                    sep=" & ", end=r" \\"+"\n", file=tablefile)
            print(r"\bottomrule", file=tablefile)
            print(r"\end{tabular}", file=tablefile)
            print(r"""\caption{Overall F\textsubscript{1}-scores for each label (in percent) 
                               according to \textit{FairEval}
                               for the best performing model on each data set.}""", 
                file=tablefile)
            print(r"\label{tab:%s_F1_per_label_FairEval}" % annotation, file=tablefile)
            print(r"\end{table}", file=tablefile)
            tablefile.close()

        #LaTeX table and R table
        #Tab 3: Error types (for best model, only FairEval)
        #line: corpus
        #column: error type
        tablefile = open(os.path.join(outdir, "tab_error_types.tex"), 
                         mode="w", encoding="utf-8")
        rtable = open(os.path.join(outdir, "tab_error_types.csv"), 
                      mode="w", encoding="utf-8")
        print(r"\begin{table}[ht]", file=tablefile)
        if annotation == "relc":
            print(r"\begin{tabular}{l" + "c"*6+"}", file=tablefile)
        else:
            print(r"\begin{tabular}{l" + "c"*8+"}", file=tablefile)
        print(r"\toprule", file=tablefile)
        if annotation == "relc":
            print(r"""\multirow[c]{2}{*}{\textbf{Corpus}} 
                    & \multirow[c]{2}{*}{\texttt{FP}} 
                    & \multicolumn{4}{c}{\texttt{BE}} 
                    & \multirow[c]{2}{*}{\texttt{FN}}
                """, 
                end=r" \\"+"\n", file=tablefile)
            print(r""" & 
                    & BE\textsubscript{s} 
                    & BE\textsubscript{\textit{l}}
                    & BE\textsubscript{o} 
                    & BE\textsubscript{all} &""",
                end=r" \\"+"\n", file=tablefile)
        else:
            print(r"""\multirow[c]{2}{*}{\textbf{Corpus}} 
                    & \multirow[c]{2}{*}{\texttt{FP}} 
                    & \multirow[c]{2}{*}{\texttt{LE}} 
                    & \multicolumn{4}{c}{\texttt{BE}} 
                    & \multirow[c]{2}{*}{\texttt{LBE}} 
                    & \multirow[c]{2}{*}{\texttt{FN}}
                """, 
                end=r" \\"+"\n", file=tablefile)
            print(r""" & & 
                    & BE\textsubscript{s} 
                    & BE\textsubscript{\textit{l}}
                    & BE\textsubscript{o} 
                    & BE\textsubscript{all} & &""",
                end=r" \\"+"\n", file=tablefile)
        print(r"\midrule", file=tablefile)
        print("Corpus", "ErrorType", "Freq", "Perc", sep="\t", file=rtable)

        #For each corpus
        for corpus, corpusname in corpora:
            n = []
            best_model = models[0][0]
            best_f1 = 0
            #For each model
            for model, _ in models:
                try:
                    #Find model with best overall F-score
                    table = read_table(os.path.join(evaldir, corpus + "_" + model + ".csv"))
                    table = table["Fair evaluation"]["Per file"]
                    f = [float(l[-1])*100 for l in table 
                         if l[0] == "overall"][0]
                    if f > best_f1:
                        best_model = model
                        best_f1 = f
                except:
                    continue
            try:
                #Get results for best model
                table = read_table(os.path.join(evaldir, corpus + "_" + best_model + ".csv"))
                table = table["Fair evaluation"]["Per file"]
                n = [l[2:10] for l in table if l[0] == "overall"][0]
                #Swap BE and BE subtypes
                be = n[2]
                del n[2]
                n.insert(5, be)
                
                #Get number of errors (don't count BE twice)
                n_errors = sum([float(i) for i in n]) - float(n[5])
                if annotation == "relc":
                    del n[6]
                    del n[1]

                #Output R table
                if annotation == "relc":
                    errortypes = ["FP", "BEs", "BEl", "BEo", "BE", "FN"]
                else:
                    errortypes = ["FP", "LE", "BEs", "BEl", "BEo", "BE", "LBE", "FN"]
                for i, e in enumerate(errortypes):
                    if e == "BE":
                        continue
                    print(corpus, e, n[i], float(n[i])/n_errors*100, sep="\t", file=rtable)

                #Calculate proportion
                n = [float(i)/n_errors*100 for i in n]
            except:
                if annotation == "relc":
                    n = [0, 0, 0, 0, 0, 0]
                else:
                    n = [0, 0, 0, 0, 0, 0, 0, 0]
            print(corpusname, 
                  " & ".join(["{:04.2f}".format(i) for i in n]), 
                  sep=" & ", end=r" \\"+"\n", file=tablefile)
        print(r"\bottomrule", file=tablefile)
        print(r"\end{tabular}", file=tablefile)
        if annotation == "relc":
            print(r"""\caption{Proportion of the different error types: 
                false positives (\texttt{FP}), boundary errors (\texttt{BE}),
                and false negatives (\texttt{FN}). 
                Numbers are given in percent for the best model on each data set.}""", 
                file=tablefile)
        else:
            print(r"""\caption{Proportion of the different error types: 
                false positives (\texttt{FP}), labeling errors (\texttt{LE}), 
                boundary errors (\texttt{BE}), labeling-boundary errors (\texttt{LBE}), 
                and false negatives (\texttt{FN}). 
                Numbers are given in percent for the best model on each data set.}""", 
                file=tablefile)
        print(r"\label{tab:%s_error_types}" % annotation, file=tablefile)
        print(r"\end{table}", file=tablefile)
        tablefile.close()
        rtable.close()

        #Confmatrix
        tablefile = open(os.path.join(outdir, "confmatrix.csv"), mode="w", encoding="utf-8")
        print("Corpus", "Target", "System", "Freq", "Perc", sep="\t", file=tablefile)

        #For each corpus
        for corpus, corpusname in corpora:
            n = []
            best_model = models[0][0]
            best_f1 = 0
            #For each model
            for model, _ in models:
                try:
                    #Find model with best overall F-score
                    table = read_table(os.path.join(evaldir, corpus + "_" + model + ".csv"))
                    table = table["Fair evaluation"]["Per file"]
                    f = [float(l[-1])*100 for l in table 
                         if l[0] == "overall"][0]
                    if f > best_f1:
                        best_model = model
                        best_f1 = f
                except:
                    continue

            #Get confmatrix for best model
            table = read_table(os.path.join(evaldir, corpus + "_" + best_model + ".csv"))
            try:
                table = table["Confusion matrix"]
            except KeyError:
                continue
            for i in range(1, len(table)):
                target = table[i][0]
                n = sum([int(freq) for freq in table[i][1:] 
                            if freq.isnumeric()])
                for j in range(1, len(table[i])):
                    syslab = table[0][j]
                    try:
                        freq = int(table[i][j])
                    except ValueError:
                        freq = 0
                    try:
                        perc = freq/n
                    except ZeroDivisionError:
                        perc = 0
                    if target.endswith("unknown") or syslab.endswith("unknown"):
                        continue
                    print(corpusname, target, syslab, freq, perc, sep="\t", file=tablefile)
        tablefile.close()

        #Additional evaluations for antecedents and relative clauses
        if annotation == "extrap":
            
            #Antec
            evaldir = os.path.join(kwargs.get("eval_dir", "eval"), "antec")
            resultfiles = [os.path.join(evaldir, f) for f in os.listdir(evaldir)]
            outdir = os.path.join(kwargs.get("eval_dir", "eval"), "tables", "antec")
            if not os.path.isdir(outdir):
                os.makedirs(outdir)

            #Tab 1: Overall results (for each model)
            #line: corpus
            #column: error type
            tablefile = open(os.path.join(outdir, "tab_overall.tex"), 
                             mode="w", encoding="utf-8")
            print(r"\begin{table}[ht]", file=tablefile)
            print(r"\begin{tabular}{cl" + "c"*len(corpora)+"}", file=tablefile)
            print(r"\toprule", file=tablefile)
            print("Model & &", " & ".join([c[1] for c in corpora]), end=r" \\"+"\n", file=tablefile)
            print(r"\midrule", file=tablefile)

            res = []
            for model, _ in models:
                res.append([])
                for v in range(6):
                    res[-1].append([])

            #For each corpus
            for corpus, corpusname in corpora:
                #For each model
                for i, (model, _) in enumerate(models):
                    try:
                        #Get scores
                        table = read_table(os.path.join(evaldir, corpus + "_" + model + ".csv"))
                        table = table["Per file"]
                        vals = [float(l)*100 for c in table 
                                if c[0] == "overall" for l in c[-4:]]
                        for v, val in enumerate(vals):
                            res[i][v].append("{:04.2f}".format(val))
                    except FileNotFoundError:
                        for v in range(4):
                            res[i][v].append("-")

            #Bold-face max values
            for c in range(len(corpora)):
                for v in range(4):
                    max_v = max([float(res[m][v][c])
                             for m in range(len(models)) 
                             if res[m][v][c] != "-"])
                    for m in range(len(models)):
                        if res[m][v][c] != "-" and float(res[m][v][c]) == max_v:
                            res[m][v][c] = r"\textbf{"+res[m][v][c]+"}"

            for m, (_, modelname) in enumerate(models):
                for i, v in enumerate(["Prec", "Rec", r"F\textsubscript{1}", 
                                       r"F\textsubscript{1}\textsubscript{\textit{right}}"]):
                    if i == 0:
                        print(r"\multirow[c]{4}{*}{\texttt{"+modelname+"}}", 
                              v, " & ".join(res[m][i][c] for c in range(len(corpora))),
                              sep=" & ", end=r" \\"+"\n", file=tablefile)
                    else:
                        print("", v, " & ".join(res[m][i][c] for c in range(len(corpora))),
                              sep=" & ", end=r" \\"+"\n", file=tablefile)
              
            print(r"\bottomrule", file=tablefile)
            print(r"\end{tabular}", file=tablefile)
            print(r"""\caption{Overall precision, recall, F\textsubscript{1}-score, 
                  and F\textsubscript{1} with correct right boundary
                  (in percent) according to \textit{FairEval} for the different models on each data set. 
                  The highest scores for each corpus are highlighted in bold.}""", 
                file=tablefile)
            print(r"\label{tab:antec_overall}", file=tablefile)
            print(r"\end{table}", file=tablefile)
            tablefile.close()

            #LaTeX and R tables
            #Tab 2: Error types (for best model, only FairEval)
            #line: corpus
            #column: error type
            tablefile = open(os.path.join(outdir, "tab_error_types.tex"), 
                             mode="w", encoding="utf-8")
            rtable = open(os.path.join(outdir, "tab_error_types.csv"), 
                          mode="w", encoding="utf-8")
            print(r"\begin{table}[ht]", file=tablefile)
            print(r"\begin{tabular}{l" + "c"*8+"}", file=tablefile)
            print(r"\toprule", file=tablefile)
            print(r"""\multirow[c]{2}{*}{\textbf{Corpus}} 
                    & \multirow[c]{2}{*}{\texttt{FP}} 
                    & \multicolumn{5}{c}{\texttt{Fuzzy Match}} 
                    & \multirow[c]{2}{*}{\texttt{IL}} 
                    & \multirow[c]{2}{*}{\texttt{FN}}
                """, 
                end=r" \\"+"\n", file=tablefile)
            print(r""" &
                    & BE\textsubscript{s} 
                    & BE\textsubscript{\textit{l}}
                    & BE\textsubscript{o} 
                    & BE\textsubscript{right} 
                    & BE\textsubscript{all} & &""",
                end=r" \\"+"\n", file=tablefile)
            print(r"\midrule", file=tablefile)
            print("Corpus", "ErrorType", "Freq", "Perc", sep="\t", file=rtable)

            #For each corpus
            for corpus, corpusname in corpora:
                n = []
                best_model = models[0][0]
                best_f1 = 0
                #For each model
                for model, _ in models:
                    try:
                        #Find model with best overall F1right-score
                        table = read_table(os.path.join(evaldir, corpus + "_" + model + ".csv"))
                        table = table["Per file"]
                        f = [float(l[25])*100 for l in table 
                            if l[0] == "overall"][0]
                        if f > best_f1:
                            best_model = model
                            best_f1 = f
                    except:
                        continue
                try:
                    #Get results for best model
                    table = read_table(os.path.join(evaldir, corpus + "_" + best_model + ".csv"))
                    table = table["Per file"]
                    n = [[l[8]] + l[3:7] + [l[2]] + [l[7]] + [l[9]] for l in table 
                         if l[0] == "overall"][0]

                    #Count errors (but don't count any boundary errors twice)
                    n_errors = sum([float(i) for i in n]) - float(n[4]) - float(n[5])

                    errortypes = ["FP", "BEs", "BEl", "BEo", "BEright", "BE", "IL", "FN"]
                    for i, e in enumerate(errortypes):
                        if e in ["BEs", "BEl", "BEo"]:
                            continue
                        elif e == "BE":
                            print(corpus, e, 
                                  float(n[i])-float(n[i-1]), 
                                  (float(n[i])-float(n[i-1]))/n_errors*100, 
                                  sep="\t", file=rtable)
                        else:
                            print(corpus, e, n[i], float(n[i])/n_errors*100, sep="\t", file=rtable)
                    
                    #Calculate proportion
                    n = [float(i)/n_errors*100 for i in n]
                except:
                    n = [0, 0, 0, 0, 0, 0, 0, 0]
                print(corpusname, 
                    " & ".join(["{:04.2f}".format(i) for i in n]), 
                    sep=" & ", end=r" \\"+"\n", file=tablefile)
            print(r"\bottomrule", file=tablefile)
            print(r"\end{tabular}", file=tablefile)
            print(r"""\caption{Proportion of the different error types: 
                false positives (\texttt{FP}), boundary errors (\texttt{BE}), 
                incorrect annotations (\texttt{IL}), and false negatives (\texttt{FN}). 
                Numbers are given in percent for the best model on each data set.}""", 
                file=tablefile)
            print(r"\label{tab:antec_error_types}", file=tablefile)
            print(r"\end{table}", file=tablefile)
            tablefile.close()
            rtable.close()

            #Antecedent head evaluation
            tablefile = open(os.path.join(outdir, "tab_F1_heads.tex"), mode="w", encoding="utf-8")
            print(r"\begin{table}[ht]", file=tablefile)
            print(r"\begin{tabular}{l" 
                    + r"".join([r"".join(["c"]*3)]*3)+"}", 
                  file=tablefile)
            print(r"\toprule", file=tablefile)
            print("", " & ".join([r"\multicolumn{3}{c}{\texttt{"+m+"}}" 
                                  for m in ["All", "Right", "Correct"]]), 
                sep=" & ", end=r" \\"+"\n", file=tablefile)
            print("Corpus", " & ".join(["Prec", "Rec", "F1"]*3), 
                sep=" & ", end=r" \\"+"\n", file=tablefile)
            print(r"\midrule", file=tablefile)
            
            #For each corpus
            for corpus, corpusname in corpora:
                best_model = models[0][0]
                best_f1 = 0
                #For each model
                for model, _ in models:
                    try:
                        #Find model with best overall F1right-score
                        table = read_table(os.path.join(evaldir, corpus + "_" + model + ".csv"))
                        table = table["Per file"]
                        f = [float(l[25])*100 for l in table 
                            if l[0] == "overall"][0]
                        if f > best_f1:
                            best_model = model
                            best_f1 = f
                    except:
                        continue
                try:
                    #Get results for best model
                    table = read_table(os.path.join(evaldir, corpus + "_" + best_model + ".csv"))
                    table = table["Head"]
                    res = [float(v)*100
                           for v in reversed([l[-9:] 
                                     for l in table 
                                     if l[0] == "overall"][0])]
                except:
                    res = [0, 0, 0, 0, 0, 0]
                
                #Output corpus, Prec, Rec, and F1
                print(corpusname, 
                    " & ".join(["-"
                                if r == None
                                else "{:04.2f}".format(r) 
                                for i, r in enumerate(res)]), 
                    sep=" & ", end=r" \\"+"\n", file=tablefile)
            print(r"\bottomrule", file=tablefile)
            print(r"\end{tabular}", file=tablefile)
            print(r"""\caption{Precision, recall, and F\textsubscript{1}-scores 
                               (in percent) according to traditional evaluation
                               for the model with the highest 
                               F\textsubscript{1\textit{right}}-score on each data set.
                               Results are given for all antecedents (\texttt{All}),
                               for antecedents that are linked to the correct \texttt{RelC}
                               and have (at least) a correct right boundary (\texttt{Right}),
                               and antecedents that are linked to the correct \texttt{RelC}
                               and have two correct boundaries (\texttt{Correct}).}""", 
                file=tablefile)
            print(r"\label{tab:antec_heads}", file=tablefile)
            print(r"\end{table}", file=tablefile)
            tablefile.close()

    #Store tables in table folder
    outdir = os.path.join(kwargs.get("eval_dir", "eval"), "tables", "data")
    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    #Evaluation results are stored in annotation folders in eval_dir
    evaldir = os.path.join(kwargs.get("eval_dir", "eval"), "stats")

    statfiles = [os.path.join(evaldir, f) for f in os.listdir(evaldir)]

    #Get corpora and their pretty names
    corpora = set([os.path.split(f)[-1].split(".csv")[0] for f in statfiles])
    corpora = [c for c in [("TuebaDZ_train", r"TüBa-D/Z\textsubscript{train}"),
                           ("TuebaDZ_dev", r"TüBa-D/Z\textsubscript{dev}"), 
                           ("TuebaDZ_test", r"TüBa-D/Z\textsubscript{test}"), 
                           ("Tiger_train", r"Tiger\textsubscript{train}"), 
                           ("Tiger_dev", r"Tiger\textsubscript{dev}"), 
                           ("Tiger_test", r"Tiger\textsubscript{test}"), 
                           ("TuebaDS", "Spoken"), ("Modern", "Modern"), 
                           ("Mercurius_train", r"Mercurius\textsubscript{train}"), 
                           ("Mercurius_dev", r"Mercurius\textsubscript{dev}"), 
                           ("Mercurius_test", r"Mercurius\textsubscript{test}"), 
                           ("ReF.UP_train", r"ReF.UP\textsubscript{train}"), 
                           ("ReF.UP_dev", r"ReF.UP\textsubscript{dev}"), 
                           ("ReF.UP_test", r"ReF.UP\textsubscript{test}"), 
                           ("HIPKON", "HIPKON"), ("DTA", "DTA")] 
                if c[0] in corpora]
    
    #Distribution of labels per annotation
    for annotation in kwargs.get("annotations", []):
        tablefile = open(os.path.join(outdir, "tab_"+annotation+"_label_dist.csv"), mode="w", encoding="utf-8")

        #Print header
        print("Corpus", "Label", "Freq", "Perc", sep="\t", file=tablefile)

        #For each corpus (except train/dev sections)
        for corpus, corpusname in corpora:
            if "train" in corpus or "dev" in corpus:
                continue

            #Get label frequencies
            table = read_table(os.path.join(evaldir, corpus + ".csv"))
            table = table.get(annotation.title(), [])
            
            #If annotation does not exist for corpus, skip it
            if not table:
                continue

            for lab in table:
                if lab[0] in ["Label", "overall"]:
                    continue
                print(corpus, lab[0], lab[1], lab[2], sep="\t", file=tablefile)
            
        tablefile.close()

############################

def get_data_stats(doc, **kwargs):
    """
    Count sentences, tokens and annotations in a document.

    The function counts the number of sentences, tokens,
    words, and span annotations in the given document.

    The resulting dictionary has the following structure:

    { 'Docs' : 1,
      'Sents' : number of sentences,
      'Toks' : number of tokens,
      'Words' : number of words (i.e., tokens excluding punctuation),
      'Annotation1' : {'Label1' : count, 'Label2' : count, ...
                       'Docs' : 1/0, 'Sents' : count, ...},
      'Annotation2' : ...
    }

    Input: Document object and additional key-word arguments
           (e.g., 'annotations').
    Output: Stats dictionary.
    """

    ###################

    def get_MovElem_spans(s, labels,
                          exclude_non_attributive_relcs=False, 
                          exclude_unknown_position=False):
        """
        Recursively get spans.

        Only spans whose label is in the label list are
        included in the output. If desired, non-attributive RelCs
        and MovElems with unknown position can be excluded.

        Input: Span object, 
               list of labels
               whether to exclude non-attributive RelCs (default: False),
               whether to exclude MovElems with position 'unknown' (default: False).
        Output: List of spans label-position
        """
        spans = []

        #Token element: stop recursion
        if not isinstance(s, MovElem):
            return spans
        
        #Span with relevant label
        if s.get_label() in [l.split("-")[0] for l in labels]:

            if exclude_unknown_position and "unknown" in s.get_position():
                pass

            elif exclude_non_attributive_relcs \
                and s.get_label() == "RELC" \
                and (s.get_antecedent() == None \
                     or all(h.XPOS.startswith("V") 
                            for h in s.get_antecedent().get_headToks())):
                pass

            else:
                #Concatenate label and position
                label = s.get_label() + "-" + s.get_position()
                spans.append(label)
                
        
        #Recursively repeat for each element in the span
        for e in s.get_elements():
            spans.extend(get_MovElem_spans(e, labels,
                                           exclude_non_attributive_relcs, 
                                           exclude_unknown_position))

        return spans

    ###################

    data_stats = {"Docs" : 1, "Sents" : 0, "Toks" : 0, "Words" : 0}
    for annotation in kwargs.get("annotations", []):
        data_stats[annotation] = {l : 0 
                                  for l in LABELS.get(annotation, [])}
        if annotation == "extrap":
            data_stats[annotation]["Antec"] = 0
            data_stats["relc"] = {"Docs" : 0, "Sents" : set(), 
                                  "Toks" : 0, "Words" : 0,
                                  "RELC-insitu" : 0, "RELC-ambig" : 0, 
                                  "RELC-extrap" : 0, "RELC-unknown" : 0}
        data_stats[annotation].update({"Docs" : 0, "Sents" : set(), 
                                       "Toks" : 0, "Words" : 0})

    #Count sentences
    for sentence in doc.sentences:
        data_stats["Sents"] += 1
        
        #Count tokens and words (not tagged as punctuation)
        for token in sentence.tokens:
            data_stats["Toks"] += 1
            if not token.XPOS.startswith("$"):
                data_stats["Words"] += 1

            for annotation in kwargs.get("annotations", []):
                #Define the target column
                if annotation == "phrases":
                    col = "PHRASE"
                elif annotation == "chunks":
                    col = "CHUNK"
                elif annotation in ["topf", "brackets"]:
                    col = "TOPF"
                elif annotation == "ner":
                    col = "NER"
                else:
                    col = ""

                #Get all annotations with relevant labels
                #Only count the beginning of spans
                annos = [lab.split("-")[1] 
                         for lab in token.__dict__.get(col, "").split("|")
                           if lab 
                              and lab.startswith("B-") 
                              and lab.split("-")[1] in LABELS.get(annotation, [])]
                
                #If there are relevant annotations in the sentence
                #remember sentence
                if annos:
                    data_stats[annotation]["Sents"].add(sentence)
                    
                for anno in annos:
                    data_stats[annotation][anno] += 1

        #For extraposition take Antec and MovElem counts
        if "extrap" in kwargs.get("annotations", []):
            annotation = "extrap"
            annos = []
            #Only count non-verbal Antecs of RelCs
            annos += [antec.get_label()
                        for antec in sentence.__dict__.get("antecedents", [])
                        if antec.get_MovElem() != None
                            and antec.get_MovElem().get_label() == "RELC"
                            and not all(h.XPOS.startswith("V") 
                                        for h in antec.get_headToks())] 
            
            relcs = []
            #Count MovElems and all RelCs
            for s in sentence.__dict__.get("MovElems", []):
                annos.extend(get_MovElem_spans(s, LABELS.get(annotation, []),
                                               exclude_unknown_position=True,
                                               exclude_non_attributive_relcs=True))
                relcs.extend(get_MovElem_spans(s, ["RELC-insitu", "RELC-ambig", 
                                                   "RELC-extrap", "RELC-unknown"]))

            #If there are relevant annotations in the sentence
            #remember sentence
            if annos or relcs:
                data_stats[annotation]["Sents"].add(sentence)
                if relcs:
                    data_stats["relc"]["Sents"].add(sentence)
            
            for anno in annos:
                data_stats[annotation][anno] += 1

            for relc in relcs:
                data_stats["relc"][relc] += 1

    #Count Sentences with relevant annotations
    annotations = [a for a in kwargs.get("annotations", [])]
    if "extrap" in annotations:
        annotations += ["relc"]
    for annotation in annotations:
        if data_stats[annotation]["Sents"]:
            data_stats[annotation]["Docs"] = 1
            for sentence in data_stats[annotation]["Sents"]:
                for token in sentence.tokens:
                    data_stats[annotation]["Toks"] += 1
                    if not token.XPOS.startswith("$"):
                        data_stats[annotation]["Words"] += 1 
            data_stats[annotation]["Sents"] = len(data_stats[annotation]["Sents"])
        else:
            data_stats[annotation]["Sents"] = 0

    return data_stats

############################

def output_data_stats(data_stats, **kwargs):
    """
    Print the data statistics to a file.

    The input dictionary has the following form:

    { 'Docs' : number of documents,
      'Sents' : number of sentences,
      'Toks' : number of tokens,
      'Words' : number of words (i.e., tokens excluding punctuation),
      'Annotation1' : {'Label1' : count, 'Label2' : count, ...
                       'Docs' : 1/0, 'Sents' : count, ...},
      'Annotation2' : ...
    }

    For each corpus, a separate file is created.
    Each output file contains:
    - overall statistics (number of documents, sentences, tokens, words)
    - per-annotation statistics (frequency of each label and overall)

    Input: Data stats dictionary and additional key-word arguments
           (e.g., 'eval_dir', 'annotations', 'corpus')
    """

    outdir = os.path.join(kwargs.get("eval_dir", "eval"), "stats")
    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    #Filename depending on corpus
    filename = kwargs.get("corpus") + ".csv"
    statsfile = open(os.path.join(outdir, filename), mode="w", encoding="utf-8")

    #Print header
    print("# Overall", file=statsfile)
    print(file=statsfile)
    print("Annotation", "Docs", "Sents", "Toks", "Words", sep="\t", file=statsfile)
    
    #Print overall stats
    print("overall",
          "\t".join([str(data_stats.get(c, 0))
                     for c in ["Docs", "Sents", "Toks", "Words"]]), 
         file=statsfile)
    for annotation in kwargs.get("annotations", [])+["relc"]:
        if not data_stats.get(annotation, {}) \
            or data_stats[annotation]["Docs"] == 0:
            data_stats[annotation] = {}
            continue
        print(annotation,
          "\t".join([str(data_stats[annotation].get(c, 0))
                     for c in ["Docs", "Sents", "Toks", "Words"]]), 
         file=statsfile)
        for v in ["Docs", "Sents", "Toks", "Words"]:
            del data_stats[annotation][v]

    #Print each annotation
    for annotation in kwargs.get("annotations", []):
        if not data_stats.get(annotation, {}):
            continue
        print(file=statsfile)
        print("#", annotation.title(), file=statsfile)
        print(file=statsfile)
        
        #For extraposition output MovElems, RelCs, and Antec
        if annotation == "extrap":
            n_antec = data_stats.get(annotation, {}).get("Antec", 0)
            n_movelem = sum(data_stats.get(annotation, {}).values())-n_antec

            print("Label", "Freq", "%", sep="\t", file=statsfile)
            for lab, freq in sorted(data_stats.get(annotation, {}).items()):
                if lab == "Antec": continue
                print(lab, freq, "{:04.2f}".format(freq/n_movelem*100), 
                      sep="\t", file=statsfile)
            print("overall", n_movelem, 100.00, 
                  sep="\t", file=statsfile)

            print(file=statsfile)
            print("# Antec", file=statsfile)
            print(file=statsfile)

            print("Label", "Freq", sep="\t", file=statsfile)
            print("Antec", n_antec, sep="\t", file=statsfile)

            print(file=statsfile)
            print("# RELC", file=statsfile)
            print(file=statsfile)
            n_relc = sum([freq for lab, freq in data_stats.get("relc", {}).items()
                          if lab.startswith("RELC")])
            print("Label", "Freq", sep="\t", file=statsfile)
            for lab, freq in sorted(data_stats.get("relc", {}).items()):
                print(lab, freq, "{:04.2f}".format(freq/n_relc*100), 
                      sep="\t", file=statsfile)
            print("overall", n_relc, 100.00, sep="\t", file=statsfile)

        #For other spans, output frequency per label and overall
        else:
            total_n = sum(data_stats.get(annotation, {}).values())
            print("Label", "Freq", "%", sep="\t", file=statsfile)
            for lab, freq in sorted(data_stats.get(annotation, {}).items()):
                print(lab, freq, "{:04.2f}".format(freq/total_n*100), 
                      sep="\t", file=statsfile)
            print("overall", total_n, 100.00, 
                  sep="\t", file=statsfile)

    statsfile.close()

############################
