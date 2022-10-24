# -*- coding: utf-8 -*-

###########################

def annotate(doc, **kwargs):
    """
    Read sentence brackets from topological field annotation.

    Takes annotations from the TOPF column and searches
    for LK and RK fields. Matches are stored in the
    'SentBrckt' attribute of each token (in stacked BIO format).
    The remaining tokens are labeled 'O'.

    Input: Document object
    Output: Document object
    """
    for sent in doc.sentences:

        #If sentence is not annotated with topological fields
        if not any("TOPF" in tok.__dict__ for tok in sent.tokens):
            for tok in sent.tokens:
                tok.SentBrckt = "O"
            continue

        for tok in sent.tokens:

            #Clear existing annotations
            tok.SentBrckt = "O"

            #Read sentence bracket(s) from topofield annotation
            fields = tok.TOPF.split("|")
            brckts = list()
            for f in fields:
                if "RK" in f or "LK" in f:
                    brckts.append(f)
            if brckts:
                tok.SentBrckt = "|".join(brckts)

    return doc

###########################
