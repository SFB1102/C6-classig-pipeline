# -*- coding: utf-8 -*-

import os
from copy import deepcopy
from annotations import MovElem, Antecedent

##########################################

def create_variant_corpus(doc, span_labels, distance_file=None):
    """
    Moves spans adjacent to the antecedent.

    For each sentence in the given document, spans with the given
    labels are moved back to their 'original' position next to
    the antecedent (if applicable).

    If distance file is given, the distances (in words, without punctuation) 
    between extraposed spans and their antecedents
    and between in-situ/ambig spans and the end of the sentence are recorded.

    The modifications are performed on a copy of the document.

    Input: Doc object, list of span labels, file object to store distances (or None).
    Output: Modified copy of doc object.
    """
    
    ################################

    def reindex_sentence(sent):
        """
        Re-index tokens and annotations.

        Updates the ID of each token
        and the start and end indices of
        MovElems and antecedents.

        The sentence is modified in place
        and returned with updated indices.

        Input: Sentence object
        Output: Re-indexed sentence object
        """

        #Re-index tokens
        for i, tok in enumerate(sent.tokens):
            tok.ID = str(i+1)

        #Re-index moving elements
        for m in sent.MovElems:
            m.update_start_index()
            m.update_end_index()

        #Re-index antecedents
        for a in sent.antecedents:
            a.update_start_index()
            a.update_end_index()

        return sent

    ################################

    def move_element(movElem):
        """
        Recursively move elements to their original position.

        For extraposed elements with relevant label,
        the original position next to the antecedent is determined
        and the tokens are moved back and re-indexed. The span
        is re-labeled as 'insitu' and the original distance 
        (in words, without punctuation) between span and antecedent 
        is recorded.

        For insitu and ambig elements, the distance between
        the span and the end of sentence is recorded.

        The sentence is modified in-place.

        Input: Moving element
        """
        #Skip irrelevant elements (with another label)
        if not movElem.get_label() in span_labels:

            #But recursively check embedded elements
            for e in reversed(movElem.get_elements()):
                if isinstance(e, MovElem):
                    move_element(e)
            
            return
        
        #If the element is not extraposed or
        #has no antecedent
        if movElem.get_position() != "extrap" \
            or movElem.get_antecedent() == None:

            #Get the number of tokens behind the element
            #until the end of the sentence (ignoring punctuation)
            toks = [t for t in sent.tokens 
                    if int(t.ID)-1 > movElem.get_end_index()
                    and not t.XPOS.startswith("$")]
            
            #Store the distance
            if distance_file:
                store_distance(distance_file,
                                doc.filename, sent.sent_id, 
                                movElem.get_label(), movElem.get_ID(), 
                                movElem.get_position(), len(toks))
            
            #No need to create a variant here
            #But recursively check embedded elements
            for e in reversed(movElem.get_elements()):
                if isinstance(e, MovElem):
                    move_element(e)
            return

        #Get end of antecedent, so movElem is placed behind it
        antec_end = movElem.get_antecedent().get_end_index()+1

        #Get number of tokens between antec and movElem (without punctuation)
        toks = [t for t in sent.tokens 
                if int(t.ID)-1 >= antec_end 
                and int(t.ID)-1 < movElem.get_start_index()
                and not t.XPOS.startswith("$")]

        #Store distance for this element
        if distance_file:
            store_distance(distance_file,
                            doc.filename, sent.sent_id, 
                            movElem.get_label(), movElem.get_ID(), 
                            movElem.get_position(), len(toks))

        #Faulty annotation: do nothing
        if len(toks) == 0:
            #No need to create a variant here
            #But recursively check embedded elements
            for e in reversed(movElem.get_elements()):
                if isinstance(e, MovElem):
                    move_element(e)
            return

        #If antecedent is embedded
        if movElem.get_antecedent().get_parent() != None:
            #And parent is antecedent of something embedded in this MovElem
            if movElem.get_antecedent().get_parent().get_MovElem() in movElem.get_elements():
                #Then movElem should be placed behind parent antecedent
                antec_end = movElem.get_antecedent().get_parent().get_end_index()+1

        #Go from last to first tok of movElem
        tokens = list(reversed(movElem.get_tokens()))

        #If there is punctuation or coordination right before the movElem,
        #e.g., a comma, also move this to the antecedent.
        if sent.tokens[movElem.get_start_index()-1].XPOS.startswith("$") \
            or sent.tokens[movElem.get_start_index()-1].XPOS == "KON":
            tokens.append(sent.tokens[movElem.get_start_index()-1]) 

        #From last to first moving token
        for tok in tokens:

            #Delete token at old position
            del sent.tokens[sent.tokens.index(tok)]

            #Insert at new position
            sent.tokens.insert(antec_end, tok)

            #Re-index tokens, movElems and antecedents
            reindex_sentence(sent)

        #Change position to insitu
        movElem.set_position("insitu")
        
        #Recursively check embedded elements
        for e in reversed(movElem.get_elements()):
            if isinstance(e, MovElem):
                move_element(e)

    ################################

    variant_doc = deepcopy(doc)

    #Go through sentences
    for sent in variant_doc.sentences:

        #Remove BIO annotations that will be corrupted by moving elements
        #so they do not prevent re-import of this file
        for tok in sent.tokens:
            tok.ORIG_ID = tok.ID
            for annotation in ["CHUNK", "PHRASE", "TOPF", "SentBrckt"]:
                if annotation in tok.__dict__:
                    del tok.__dict__[annotation]

        #Re-index tokens, movElems and antecedents
        reindex_sentence(sent)

        #For each moving element
        for movElem in reversed(sent.__dict__.get("MovElems", [])):

            #Check if element has to be moved
            move_element(movElem)

        #Regenerate readable text with new token order
        sent.regenerate_text()

        #Convert MovElems and antecedents to BIO format
        #and store in tokens
        sent = MovElem.span_to_BIO_annotation(sent, "MovElems", "MovElem")
        sent = Antecedent.span_to_BIO_annotation(sent, "antecedents", "Antec")

        #Turn BIO annotations back into spans
        #(easy way to fix all dependencies between spans)
        sent.MovElems = MovElem.span_from_BIO_annotation(sent, "MovElem")

    #Return variant doc
    return variant_doc

####################################################

def create_distance_file(dir, corpus):
    """
    Open a file to record distances between span and antecedent.

    Creates a file for the given corpus, in which the distances 
    between moving elements and their antecedents can be stored. 
    For non-extraposed elements, instead, the distance 
    to the end of the sentence can be recorded.

    The file contains six tab-separated columns,
    that allow to trace back distances to the exact
    file, sentence, and element:
    File   SentID   MovElemType   MovElemID   Position   #Words

    Input: Target directory as string, name of the corpus.
    Output: File object with inserted header.    
    """
    #Open a file to store distances between span and antecedent
    distance_file = open(os.path.join(dir, "distances_"+corpus+".csv"), 
                         mode="w", encoding="utf-8")
                        
    #Print the header
    print("File", "SentID", "MovElemType", "MovElemID", "Position", "#Words", 
          sep="\t", file=distance_file)

    #Return file object
    return distance_file

####################################

def store_distance(distance_file, filename, sent_id, 
                   movElem_label, movElem_id, position, n_words):
    """
    Record distances between element and antecedent.

    Writes the given information to the given distance file.
    """
    print(os.path.splitext(filename)[0], sent_id, movElem_label, 
          movElem_id, position, n_words, 
          sep="\t", file=distance_file)

####################################