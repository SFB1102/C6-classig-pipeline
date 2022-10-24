# -*- coding: utf-8 -*-

import os
import phrases
from topofields import BerkeleyTopFParser
from annotations import MovElem, Span, Antecedent
from C6C.src.document import Tree, Token
from C6C.src.processor import SimplePTBInitializer

######################

class RelCFinder:
    """
    Class interface for the identification of relative clauses.
    """

    ##############################

    def __init__(self, model):
        """
        Create a relative clause identifier with the given model.

        The following models are supported: 
        - 'news1' (TuebaDZ style)
        - 'news2', 'hist', 'mix' (Tiger style)
        """
        self.model = model

        #Set labels of relative clauses
        #and sentences that could be relative clauses
        #(labels depend on the model)
        if model == "news1":
            self.relc_label = ["R", "R-SIMPX", "R-SIMPX:KONJ"]
            self.sent_label = ["SIMPX", "SIMPX:KONJ"]
        elif model in ["hist", "news2", "mix"]:
            self.relc_label = ["S:RC"]
            self.sent_label = ["S", "AS", "CS"]
        
    ##############################

    def read_RelCs_from_tree(self, sentence):
        """
        Identify relative clauses in a constituency tree.

        The tree is expected to be a sentence attribute 'tree'.
        The function identifies official relative clauses
        (i.e., labeled as such in the tree and 
        containing a relative pronoun) and sentence nodes
        that start with a relative pronoun in the C-field or
        the first constituent.

        The default position of relative clauses is set to 'insitu'.

        Input: Sentence object
        Output: List of relative clauses (MovElem objects)
        """

        relcs = []
        tree = sentence.__dict__.get("tree", None)
        
        #Skip sentences without tree
        if tree is None:
            return relcs
        
        ######################

        def get_relcs(node):
            """
            Recursively check if node is a relative clause.

            Input: Tree node
            Output: List of relative clauses (MovElem objects)
            """
            node_relcs = []
            
            #Take official RelCs from tree
            if node.simple_cat in self.relc_label:
                
                #If they contain coordinated RelCs,
                #skip the joined RelC (only happens for News1)
                if self.model == "news1" \
                and not any(n.simple_cat == "C"
                            for n in node.nodes()) \
                and len([n for n in node.nodes()
                         if isinstance(n, Tree) 
                         and n.simple_cat in self.relc_label]) >= 2:
                    pass

                #If they actually contain a PREL (or ADV to capture ADVRELs; 
                #or another relativizer in custom tagsets)
                elif any(t.token.XPOS.startswith("PREL") 
                       for t in list(node.nodes())[0].terminals()) \
                    or (list(node.nodes())[0].terminals()[0].token.XPOS == "ADV" 
                        and list(node.nodes())[0].terminals()[0].token.FORM in ["ſo", "so"]) \
                    or any(t.token.__dict__.get("POS", "").endswith("REL") 
                           for t in list(node.nodes())[0].terminals()):
                    
                    #Create 'insitu' RELC MovElem
                    relc = MovElem("RELC", [t.token for t in node.terminals()], "insitu")
                    node_relcs.append(relc)
            
            #If there ist nothing but preceding punctuation 
            #-> cannot be RelC
            elif all(t.XPOS.startswith("$") 
                     for t in [tok for tok in sentence.tokens 
                               if int(tok.ID)-1 < node.get_start_index(ignore_punct=True)]):
                pass

            else:
                #Also take sentences that start with C-field including PREL
                #(TuebaDZ style)
                if self.model == "news1" \
                    and node.simple_cat in self.sent_label \
                    and any(n.simple_cat == "C"
                            and any(t.token.XPOS.startswith("PREL") 
                                    or t.token.__dict__.get("POS", "").endswith("REL") 
                                    for t in list(n.nodes())[0].terminals())
                            for n in node.nodes()):
                    
                    #Create 'insitu' RELC MovElem
                    relc = MovElem("RELC", [t.token for t in node.terminals()], "insitu")
                    node_relcs.append(relc)
                
                #And sentences starting with PREL in first constituent
                #(Tiger style)
                elif self.model in ["news2", "hist", "mix"] \
                    and node.simple_cat in self.sent_label \
                    and any(t.__dict__.get("token", None) != None 
                            and (t.token.XPOS.startswith("PREL") 
                                 or t.token.__dict__.get("POS", "").endswith("REL"))
                            for t in [list(node.nodes())[0]]+list(list(node.nodes())[0].nodes())):
                    
                    #Create 'insitu' RELC MovElem
                    relc = MovElem("RELC", [t.token for t in node.terminals()], "insitu")
                    node_relcs.append(relc)

            #Repeat recursively
            if node.is_non_terminal():
                for child in node.nodes():
                    if child.is_non_terminal():
                        node_relcs.extend(get_relcs(child))
            
            #Strip punctuation at start and end
            for relc in node_relcs:
                while relc.get_elements()[0].XPOS.startswith("$"):
                    relc.remove_element(relc.get_elements()[0])
                while relc.get_elements()[-1].XPOS.startswith("$"):
                    relc.remove_element(relc.get_elements()[-1])
        
            #Return list of RelC MovElems
            return node_relcs

        ######################

        #For each tree node, recursively identify RelCs
        for node in tree.nodes():
            relcs.extend(get_relcs(node))
        
        #Return list of RelC MovElems
        return relcs

    ##############################

    def annotate(self, doc, **kwargs):
        """
        Identify relative clauses in a document.

        For each sentence, the function reads the relative clauses
        from the pre-annotated constituency tree. If no tree
        is given, the parser is called first.

        The default position of relative clauses is set to 'insitu'
        and the RelC MovElem objects are stored 
        as sentence attribute 'MovElems'.

        Input: Doc object and key-word arguments ('corpus')
        Output: Annotated Doc object
        """
        myParser = None

        for sent in doc.sentences:

            #No tree available
            if not sent.__dict__.get("tree", None):

                #Read from tree string
                if sent.__dict__.get("PTBstring", ""):
                    sent.tree = Tree.from_PTB_string(sent.__dict__.get("PTBstring", ""))
                    sent = SimplePTBInitializer().process_sentence(sent, "tree", "PTBstring", 
                                                                   kwargs.get("norm", "FORM"))

                #Or parse now
                else: 
                    if myParser == None:
                        myParser = phrases.PhraseParser(self.model)
                    sent = myParser.parse(sent, kwargs.get("corpus", "unknown"))
                    sent = SimplePTBInitializer().process_sentence(sent, "tree", "PTBstring", 
                                                                   kwargs.get("norm", "FORM"))

            #Still no tree available
            if not sent.__dict__.get("tree", None):
                continue

            #Read RelCs from tree
            sent.MovElems.extend(self.read_RelCs_from_tree(sent))

        return doc

    ###################################

    @classmethod
    def get_relcs(cls, movElems):
        """
        Recursively get relative clauses.

        Input: List of MovElems
        Output: List of included relative clauses
        """
        relcs = []
        for me in movElems:
            if not isinstance(me, MovElem):
                continue
            if me.get_label() == "RELC":
                relcs.append(me)
            relcs.extend(RelCFinder.get_relcs(me.get_elements()))
        return relcs

###########################

class MovElemIdentifier:
    """
    Class interface for the identification of MovingElements.
    """
    
    #####################################

    def __init__(self, model, **kwargs):
        """
        Initialize MovElem identifier with the given model.

        Supported models are: 'news1', 'news2', 'hist', and 'mix'.
        """
        self.model = model
        self.myRelCFinder = RelCFinder(model)
        self.topfParser = None
        self.phraseParser = None
        
    ##########################

    def get_head_of_antecedent(self, antec, phrases):
        """
        Determine the head token(s) of the given antecedent.

        First, identifies the phrase from the given phrase list
        that matches the antecendent. Then, identifies the head token(s) 
        of the phrase and, thus, the head of the antecedent.

        Head tokens are selected based on the hierarchical structure
        of the phrase and POS tags. POS tags are checked in the following
        order and the first match is considered the head:
        1. Nouns (NN, TRUNC)
        2. Names (NE)
        3. Pronouns (substituting pronouns only)
        4. Numbers (CARD)
        5. Adjectives (ADJA)
        6. Foreign words (FM)
        If a phrase contains more than one token with the given POS,
        the last one is returned.

        Input: Antecedent object and list of phrase spans
        Output: List of head tokens (or None)
        """

        #Only one token -> must be the head
        if len(antec.get_elements()) == 1:
            return [antec.get_elements()[0]]

        #More than one token
        #Get the matching phrase
        phrase = self.get_matching_phrase(antec, phrases)

        #If there is none, cannot determine the head
        if not phrase:
            return None

        #Get direct token children of the phrase
        tokens = [e for e in phrase.get_elements() 
                  if isinstance(e, Token)]

        #If there are no direct token children
        #that could be heads, check dominated phrases
        while not tokens \
            or not any(t.XPOS in ["NN", "NE", "TRUNC", 
                                  "PDS", "PIS", "PPOSS", "PRELS", "PWS", 
                                  "CARD", "ADJA", "FM"]
                       for t in tokens):
            phrase = [p for p in phrase.get_elements() 
                      if isinstance(p, Span)]
            if phrase:
                #Take the last dominated phrase
                phrase = phrase[-1]
                tokens = [e for e in phrase.get_elements() 
                          if isinstance(e, Token)]
            else:
                return None

        #Get nouns
        nouns = [t for t in tokens if t.XPOS in ["NN", "TRUNC"]]
        if len(nouns) == 1:
            #One noun -> return it as head
            return [nouns[-1]]
        #Otherwise, return last one
        elif len(nouns) > 1:
            return [nouns[-1]]
        
        #Get names
        names = [t for t in tokens if t.XPOS == "NE"]
        #One name -> return it as head
        if len(names) == 1:
            return [names[-1]]
        #Otherwise, return last one
        elif len(names) > 1:
            return [names[-1]]

        #Get substituting pronouns
        pronouns = [t for t in tokens 
                    if t.XPOS[:2] in ["PD", "PI", "PP", "PR", "PW"] 
                    and t.XPOS.endswith("S")]
        if len(pronouns) == 1:
            #One pronoun -> return it
            return [pronouns[-1]]
        #Otherwise, return last one
        elif len(pronouns) > 1:
            return [pronouns[-1]]

        #Get numbers
        numbers = [t for t in tokens if t.XPOS == "CARD"]
        if len(numbers) == 1:
            #One number -> return it
            return [numbers[-1]]
        #Otherwise, return last one
        elif len(numbers) > 1:
            return [numbers[-1]]

        #Get adjectives
        adj = [t for t in tokens if t.XPOS == "ADJA"]
        if len(adj) == 1:
            #One adj -> return it
            return [adj[-1]]
        #Otherwise, return last one
        elif len(adj) > 1:
            return [adj[-1]]

        #Get foreign words
        fm = [t for t in tokens if t.XPOS == "FM"]
        if len(fm) == 1:
            #One fm -> return it
            return [fm[-1]]
        #Otherwise, return last one
        elif len(fm) > 1:
            return [fm[-1]]

        #No head found
        return None

    ##########################

    def get_matching_field(self, span, topftree):
        """
        Recursively identify the field in the topological
        field tree that contains the given span object.
        
        Compares start and end indices of span and tree node
        (ignoring punctuation) to determine if the given span
        is dominated by the tree node.
        The lowest matching field node in the tree is returned.
        
        Input: Span object and topological field tree
        Output: Field node from the tree
        """
        field = None
        
        #For each field
        for node in topftree:

            #Is non-terminal and includes the span
            if not node.is_terminal() and node.includes_span(span):
                field = node

                #If field contains other fields
                if node.is_non_terminal():
                    
                    #Check if any of them are a better match
                    closer_field = self.get_matching_field(span, node)
                    if closer_field != None:
                        field = closer_field
        
        return field

    ##########################

    def get_previous_field(self, span, topftree):
        """
        Recursively identify the field in the topological
        field tree that ends before the given span object.
        
        Compares start and end indices of span and tree node
        (ignoring punctuation) to determine if the given span
        is dominated by the tree node.
        The lowest matching field node in the tree is returned.
        
        Input: Span object and topological field tree
        Output: Field node from the tree
        """
        field = None
        
        #For each field
        for node in reversed(list(topftree.nodes())):
            
            #Is non-terminal and includes the span
            if node.is_non_terminal() \
                and node.get_end_index(ignore_punct=True) < span.get_start_index(ignore_punct=True):
                field = node
                    
                #Check if any of them are a better match
                closer_field = self.get_matching_field(span, node)
                if closer_field != None:
                    field = closer_field

                break

        return field

    ##########################

    def get_matching_phrase(self, span, phrases):
        """
        Recursively identify the phrase in the phrase list
        that contains the given span object.
        
        Compares start and end indices of span and phrase
        (ignoring punctuation) to determine if the given span
        is included in the phrase.
        The lowest matching phrase is returned.
        
        Input: Span object and list of phrase spans
        Output: Phrase span
        """
        match = None

        #For each phrase
        for phrase in phrases:

            #Check, if it includes the span
            if phrase.includes_span(span):
                match = phrase

                #If the phrase contains other spans
                #check if they are a closer match
                if phrase.get_elements():
                    closer_match = self.get_matching_phrase(span, 
                                          [e for e in phrase.get_elements() 
                                           if isinstance(e, Span)])
                    if closer_match != None:
                        match = closer_match

        return match
    
    ##########################

    def get_previous_phrases(self, span, phrases):
        """
        Get phrases that are located to the left of the given span.

        Returns all phrases from the given phrase list
        that end before the first token of the given span
        (ignoring punctuation).

        Input: Span object and list of phrase spans
        Output: List of preceding phrases
        """
        return [p for p in phrases 
                if isinstance(p, Span) 
                and p.get_end_index(ignore_punct=True) 
                    < span.get_start_index(ignore_punct=True)]
 
    ##########################

    def get_phrase_positions(self, sent):
        """
        Determine the position of phrases in a given sentence.

        Based on a constituency and a topological field parse,
        each phrase in the sentence is labeled as 'insitu' or 'extrap'.

        The parse trees are expected to be stored in the sentence
        as 'tree' and 'TopFTree' attributes. Phrases
        are taken from the 'phrases' list of the sentence.

        Input: Sentence object
        Output: Annotated Sentence object
        """
        #Without topofields add top-level phrases as insitu MovElems
        if sent.__dict__.get("TopFTree", None) == None:
            for phrase in sent.phrases:
                #Skip VPs
                if phrase.get_label() == "VP":
                    continue
                new_MovElem = MovElem(phrase.get_label(), 
                                      elements=phrase.get_tokens(), 
                                      position="insitu")
                sent.MovElems.append(new_MovElem)
            return sent

        ############################

        def get_phrase_position(phrase):
            """
            Recursively determine the position of a given phrase.

            The position is determined based on the topological field
            analysis of the sentence. Possible positions are 
            'insitu' or 'extrap'. For each phrase, a MovElem is created
            and stored in the 'MovElems' list of the sentence.

            Input: Phrase span
            """
            #Skip VPs and non-sense phrases without tokens
            if phrase.get_label() == "VP" \
                or not any(not t.XPOS.startswith("$") 
                           for t in phrase.get_tokens()):
                return

            #Find matching topofield in TopFTree
            field = self.get_matching_field(phrase, sent.TopFTree)
            
            #If no field is found, 
            #find a field for the first included token.
            if field == None:
                first_tok = [t for t in phrase.get_tokens() 
                             if not t.XPOS.startswith("$")]
                if first_tok:
                    first_tok = first_tok[0]
                    field = self.get_matching_field(Span("DUMMY",
                                                         elements=[first_tok]),
                                                    sent.TopFTree)
                    
            #If field is NF
            if field != None and field.cat() == "NF":

                #Top-level phrase
                if phrase.get_parent() == None:
                    #Add as extrap MovElem
                    new_MovElem = MovElem(phrase.get_label(), 
                                          elements=phrase.get_tokens(), 
                                          position="extrap")
                    sent.MovElems.append(new_MovElem)

                #Dominated phrase
                else:
                    #Check if parent is between phrase and field
                    if field.includes_span(phrase.get_parent()) == False:
                        #If not, add as extrap MovElem
                        new_MovElem = MovElem(phrase.get_label(), 
                                              elements=phrase.get_tokens(), 
                                              parent_span=phrase.get_parent(),
                                              position="extrap")
                        sent.MovElems.append(new_MovElem)
                    #Else, skip

            #Other field or no field
            else:
                #Top-level phrase
                if phrase.get_parent() == None:
                    #Add as in-situ MovElem
                    new_MovElem = MovElem(phrase.get_label(), 
                                          elements=phrase.get_tokens(), 
                                          position="insitu")
                    sent.MovElems.append(new_MovElem)

                #Dominated phrase
                else:
                    #If field is between parent and phrase
                    if field != None \
                        and field.includes_span(phrase.get_parent()) == False:
                        #Add as in-situ MovElem
                        new_MovElem = MovElem(phrase.get_label(), 
                                              elements=phrase.get_tokens(), 
                                              parent_span=phrase.get_parent(),
                                              position="insitu")
                        sent.MovElems.append(new_MovElem)
                    #Else, skip

            #Recursively repeat for dominated phrases
            for elem in phrase.get_elements():
                if isinstance(elem, Span):
                    get_phrase_position(elem)
            
        ########################

        #For each phrase (except VPs)
        for phrase in sent.phrases:
            if phrase.get_label() == "VP":
                continue

            #Determine the position
            get_phrase_position(phrase)

        return sent

    ##########################

    def get_relc_positions(self, sent):
        """
        Determine the position of all relative clauses
        in a given sentence.

        Based on a constituency and a topological field parse,
        each relative clause in the sentence is labeled
        as 'insitu', 'ambig', 'extrap', or 'unknown'.
        Also, the antecedent for each RelC is identified
        and stored in the sentence object.

        The parse trees are expected to be stored in the sentence
        as 'tree' and 'TopFTree' attributes. Relative clauses
        are taken from the 'MovElems' list of the sentence.

        Input: Sentence object
        Output: Annotated Sentence object
        """
        #Without topofields all relcs remain insitu
        if sent.__dict__.get("TopFTree", None) == None:
            return sent

        #####################

        def get_relc_position(relc, phrases):
            """
            Determine the position of a given relative clause.

            The position is determined based on the topological field
            analysis of the sentence. Possible positions are 'insitu', 
            'ambig', 'extrap', or 'unknown'.
            
            The list of unmodified, nested input phrases is used 
            to identify position and antecedent of the RelC.
            
            The RelC is modified in-place and its antecedent is
            added to the 'antecedent' list of the sentence.

            Input: RelC MovElem and list of phrase spans
            """
            #Find matching topofield in TopFTree
            field = self.get_matching_field(relc, sent.TopFTree)

            #If no field is found, find field for first token instead
            if field == None:
                first_tok = [t for t in relc.get_tokens() 
                             if not t.XPOS.startswith("$")]
                if first_tok:
                    first_tok = first_tok[0]
                    field = self.get_matching_field(Span("DUMMY",
                                                         elements=[first_tok]),
                                                    sent.TopFTree)
                    if field and field.get_parent() != None:
                        field = field.get_parent()
                    else:
                        field = None

            #Get the previous field 
            #to check whether it is a right bracket
            if field != None \
                and field.parent_node != None \
                and list(field.parent_node.nodes()).index(field) > 0:

                field_index = list(field.parent_node.nodes()).index(field)
                previous_fields = list(reversed([f for f 
                                                 in field.parent_node.nodes()][:field_index]))
                i = 0
                while i < len(previous_fields)-1 \
                    and previous_fields[i].cat() in ["COMMA", "KOMMA", "PUNCT", 
                                                     "PUNKT", "KLAMMER"]:
                    i += 1
                if i < len(previous_fields):
                    previous_field = previous_fields[i]
                else:
                    previous_field = None
            else:
                previous_field = None

            #Get the parent phrase in phrase list
            parent_phrase = self.get_matching_phrase(relc, phrases)
            
            #RelC is part of a phrase
            if parent_phrase != None:

                #Preceding tokens are most likely the antecedent    
                tokens = [t for t in parent_phrase.get_tokens() 
                            if int(t.ID)-1 < relc.get_start_index(ignore_punct=True)]
                
                #If there are no preceding tokens, position is unknown
                if not tokens or all(tok.XPOS.startswith("$") for tok in tokens):
                    relc.set_position("unknown")
                    return

                #Strip off punctuation
                while tokens[0].XPOS.startswith("$"):
                    tokens = tokens[1:]
                while tokens[-1].XPOS.startswith("$"):
                    tokens = tokens[:-1]

                #Create antecedent, determine its head
                #and link it to RelC
                if tokens:
                    antec = Antecedent(elements=tokens, MovElemID=relc.get_ID())
                    head_toks = self.get_head_of_antecedent(antec, phrases)
                    if head_toks != None:
                        antec.set_headToks(head_toks)
                    sent.antecedents.append(antec)
                    relc.set_antecedent(antec) 
                    antec.set_MovElem(relc)
                else:
                    relc.set_position("unknown")
                    return
                
                #If there is no NF between RelC and antec,
                #RelC stays insitu. Otherwise, if NF 
                #is between RelC and antec, can be extrap or ambig
                if field != None and field.cat() == "NF" \
                    and field.includes_span(antec) == False:

                    #After RK -> extrap
                    if previous_field != None \
                        and previous_field.cat() in ["RK", "VC", "VCE"] \
                        and previous_field.get_start_index(ignore_punct=True) >= antec.get_start_index(ignore_punct=True):
                        relc.set_position("extrap")
                        
                    #Otherwise ambig
                    else:
                        relc.set_position("ambig")
                
                #Actually unnecessary if relcs are insitu per default
                else:
                    relc.set_position("insitu")

            #RelC is not part of any phrase
            else:
                
                #Get previous phrases
                previous_phrases = self.get_previous_phrases(relc, phrases)

                #Antecedent is most likely the previous NP/PP
                antec_phrase = [p for p in previous_phrases 
                                if p.get_label() in ["NP", "PP"]]
                
                #No candidate antec?
                if not antec_phrase:
                    relc.set_position("unknown")
                    return
                
                #Otherwise, set antec to previous NP/PP
                antec_phrase = antec_phrase[-1]
                
                #Check if there are previous RelCs
                prev_relcs = [m for m in sent.MovElems
                              if m.get_label() == "RELC" 
                              and m.get_end_index(ignore_punct=True) 
                                 < relc.get_start_index(ignore_punct=True)]
                if prev_relcs:
                    r = prev_relcs[-1]
                    #If the previous RelC contains the possible antecedent
                    if r.includes_span(antec_phrase):
                        #Then they are likely coordinated and 
                        #have the same position and antecedent
                        relc.set_position(r.get_position())
                        shared_antec = r.get_antecedent()
                        if shared_antec != None:
                            antec = Antecedent(elements=shared_antec.get_tokens(), 
                                               MovElemID=relc.get_ID())
                            antec.set_headToks(shared_antec.get_headToks())
                            sent.antecedents.append(antec)
                            relc.set_antecedent(antec)
                            antec.set_MovElem(relc)
                        return

                #Get tokens of antecedent
                tokens = antec_phrase.get_tokens()

                #Strip off punctuation
                while tokens[0].XPOS.startswith("$"):
                    tokens = tokens[1:]
                while tokens[-1].XPOS.startswith("$"):
                    tokens = tokens[:-1]
                
                #Create antecedent, determine its head
                #and link it to RelC
                if tokens:
                    antec = Antecedent(elements=tokens, MovElemID=relc.get_ID())
                    head_toks = self.get_head_of_antecedent(antec, phrases)
                    if head_toks != None:
                        antec.set_headToks(head_toks)
                    sent.antecedents.append(antec)
                    relc.set_antecedent(antec)   
                    antec.set_MovElem(relc)
                else:
                    relc.set_position("unknown")
                    return

                #If an antecedent was identified
                #and RelC is in NF
                if field != None and field.cat() == "NF":

                    #Antec is in NF, too
                    if field.includes_span(antec_phrase) == True:
                        #Something other than punct between both -> extrap
                        if any(not t.XPOS.startswith("$") 
                                for t in sent.tokens[antec_phrase.get_end_index(ignore_punct=True)+1
                                                     :relc.get_start_index(ignore_punct=True)]):
                            relc.set_position("extrap")
                        #Otherwise, stays insitu
                        else:
                            relc.set_position("insitu")
                            
                    #Antec is not in NF
                    else:
                        #Only punctuation between both -> ambig
                        if all(t.XPOS.startswith("$") 
                                for t in sent.tokens[antec_phrase.get_end_index(ignore_punct=True)+1
                                                     :relc.get_start_index(ignore_punct=True)]):
                            relc.set_position("ambig")
                        #Something else between -> extrap
                        else:
                            relc.set_position("extrap")
                        
                #Antecedent was identified, 
                #but RelC is not in NF
                else:
                    #Not only punct in between -> extrap
                    if any(not t.XPOS.startswith("$") 
                            for t in sent.tokens[antec_phrase.get_end_index(ignore_punct=True)+1
                                                 :relc.get_start_index(ignore_punct=True)]):
                        relc.set_position("extrap")
                    #Otherwise, stays insitu
                    else:
                        relc.set_position("insitu")
            
        #####################

        #Get unmodified phrases (i.e., possible parents/antecedents)
        #by reading the phrases directly from the constituency tree
        if self.model == "news1":
            phrases = Span.read_phrases_from_simplified_tueba(sent)
        else:
            phrases = Span.read_phrases_from_simplified_tiger(sent)

        #Ignore VPs and phrases without word tokens
        phrases = [p for p in phrases 
                   if p.get_label() != "VP" 
                      and any(not t.XPOS.startswith("$") 
                              for t in p.get_tokens())]

        sent.antecedents = []
        
        #########################

        def get_relcs(movElems):
            """
            Recursively get relative clauses.
            """
            relcs = []
            for me in movElems:
                if not isinstance(me, MovElem):
                    continue
                if me.get_label() == "RELC":
                    relcs.append(me)
                relcs.extend(get_relcs(me.get_elements()))
            return relcs
        
        ########################

        #For each RelC in the MovElems list
        relcID = 1
        for relc in get_relcs(sent.MovElems):

            #Assign the RelC a number
            #(used for linking it to the antecedent)
            relc.set_ID(relcID)

            #Get position of the RelC
            get_relc_position(relc, phrases)
            relcID += 1
        
        return sent

    ##########################

    def annotate(self, doc, **kwargs):
        """
        Annotate the input document with Moving Elements.

        First, identifies relative clauses and phrases in the sentences.
        Then, determines the position of each element as 
        insitu, ambig, or extrap and sets the antecedents of RelCs.

        If available, pre-annotated constituency trees and phrases
        are used for the identification. Otherwise, the necessary
        annotations are created first.

        The resulting span objects are stored as sentence attributes 
        'MovElems' and 'antecedents' and as token attributes in BIO format.
        
        Input: Doc object and additional key-word arguments 
               ('annotations', 'corpus')
        Output: Annotated Doc object
        """
        #Clear existing annotations
        #to not accidentally use gold annotations
        for sent in doc.sentences:

            sent.MovElems = []
            if not "phrases" in kwargs.get("annotations", []):
                sent.phrases = []
                sent.tree = None
                sent.PTBstring = ""
                sent.PTBstring_simple = ""
                for tok in sent.tokens:
                    tok.PHRASE = "_"

            #Also clear TopFTree, because it is likely
            #created with the wrong model - we want to use topfpunct
            sent.TopFTree = None
            sent.TopFString = ""
            for tok in sent.tokens:
                tok.TOPF = "_"
        
        for sent in doc.sentences: 

            #Annotate topological fields
            if not sent.__dict__.get("TopFTree", None):
                if not sent.__dict__.get("TopFString", ""):
                    if not self.topfParser:
                        self.topfParser = BerkeleyTopFParser()
                    self.topfParser.parse(sent, kwargs.get("corpus", None))
                    if sent.TopFTree != None:
                        sent = Span.tree_to_BIO_annotation(sent, "TopFTree", "TOPF")
                        sent = BerkeleyTopFParser.map_tagsets(sent, "TOPF")
                else:
                    sent.TopFTree = Tree.from_PTB_string(sent.TopFString)
                    sent = SimplePTBInitializer().process_sentence(sent, "TopFTree", "TopFString")
                    sent = Span.tree_to_BIO_annotation(sent, "TopFTree", "TOPF")
                    sent = BerkeleyTopFParser.map_tagsets(sent, "TOPF")
            else:
                if sent.tokens and not "TOPF" in sent.tokens[0].__dict__:
                    sent = Span.tree_to_BIO_annotation(sent, "TopFTree", "TOPF")
                    sent = BerkeleyTopFParser.map_tagsets(sent, "TOPF")
            
            #Get phrases from existing annotation
            #or create them first
            if not sent.__dict__.get("phrases", []):
                if self.phraseParser == None:
                    self.phraseParser = phrases.PhraseParser(self.model)
                if not sent.__dict__.get("tree", None):
                    sent = self.phraseParser.get_phrases(sent, **kwargs)
                else:
                    sent = self.phraseParser.read_phrases_from_parse(sent, **kwargs)
            #Remove non-sense phrases without word tokens
            sent.phrases = [p for p in sent.phrases 
                            if any(not t.XPOS.startswith("$") 
                                   for t in p.get_tokens())]

        #Get RelCs
        doc = self.myRelCFinder.annotate(doc, **kwargs)

        for sent in doc.sentences:

            #Determine position of phrases 
            #and add the relevant ones to MovElems
            if sent.phrases:
                sent = self.get_phrase_positions(sent)

            #Determine position of RelCs
            sent = self.get_relc_positions(sent)
            
            #If the topf parse does not contain any brackets,
            #there can't be anything extraposed or embedded
            if sent.__dict__.get("TopFTree", None) != None \
               and not any("LK" in tok.TOPF 
                           or "RK" in tok.TOPF 
                           or "VC" in tok.TOPF 
                           for tok in sent.tokens):
                i = 0
                while i < len(sent.MovElems):
                    #Remove embedded MovElems
                    if sent.MovElems[i].get_parent() != None:
                        del sent.MovElems[i]
                    else:
                        #Switch extrap back to insitu
                        sent.MovElems[i].set_position("insitu")
                        i += 1
            
            #Convert MovElems and antecedents to BIO format
            #and store in tokens
            sent = MovElem.span_to_BIO_annotation(sent, "MovElems", "MovElem")
            sent = Antecedent.span_to_BIO_annotation(sent, "antecedents", "Antec")

            #Turn BIO annotations back into spans
            #(easy way to fix all dependencies between spans)
            sent.MovElems = MovElem.span_from_BIO_annotation(sent, "MovElem")

        return doc

    #############################

    @classmethod
    def identify_MovElems_in_Tueba(cls, sentence, corpus="TuebaDZ", tree="tree"):
        """
        Identify Moving Elements in TuebaDZ-style corpora.

        Using the official constituency and topological field annotation 
        and automatic dependency annotations, the phrases and relative clauses
        are identified and labeled with their position as 
        'insitu', 'ambig', 'extrap', or 'unknown'.

        Annotations are stored in sentence attributes 'MovElems' and 'antecedents'.
        
        Input: Sentence object, corpus name, tree name.
        Output: Annotated Sentence object.
        """
        sentence.MovElems = []
        
        #Get phrases
        sentence.phrases = Span.read_phrases_from_simplified_tueba(sentence, tree)

        #Get relative clauses
        sentence.MovElems.extend(RelCFinder("news1").read_RelCs_from_tree(sentence))

        ########################

        def get_phrase_position(phrase, tree):
            """
            Recursively determine the position of a given phrase span
            based on the given constituency tree (including 
            topological fields).

            For each relevant phrase, a Moving Element is created
            and added to the sentence list 'MovElems'.

            Input: Phrase Span object, 
                   constituency tree in TuebaDZ style.
            """
            #Find node in tree
            node = MovElemIdentifier("news1").get_matching_field(phrase, tree)
            
            #Get next dominating field
            field = node.parent_node
            while field != None and not field.is_root() \
                and not field.cat() in ["LV", "C", "LK", "VF", "FKOORD", "KOORD", "MF", 
                                        "MFE", "NF", "PARORD", "VC", "VCE", "FKONJ"]:
                field = field.parent_node
            
            #NF
            if field != None and field.cat() == "NF":

                #If top-level phrase
                if phrase.get_parent() == None:
                    #Add as extrap MovElem
                    new_MovElem = MovElem(phrase.get_label(), 
                                          elements=phrase.get_tokens(), 
                                          position="extrap")
                    sentence.MovElems.append(new_MovElem)

                #Dominated phrase
                else:
                    #Check if parent is between phrase and field
                    if field.includes_span(phrase.get_parent()) == False:
                        #If not, add as extrap MovElem
                        new_MovElem = MovElem(phrase.get_label(), 
                                              elements=phrase.get_tokens(), 
                                              position="extrap")
                        sentence.MovElems.append(new_MovElem)
                    #Else, skip
            
            #Not NF
            else:
                #If top-level phrase
                if phrase.get_parent() == None:
                    #Add as in-situ MovElem
                    new_MovElem = MovElem(phrase.get_label(), 
                                          elements=phrase.get_tokens(), 
                                          position="insitu")
                    sentence.MovElems.append(new_MovElem)

                #Dominated phrase
                else:
                    #If field is between parent and phrase
                    if field != None \
                        and field.includes_span(phrase.get_parent()) == False:
                        #Add as in-situ MovElem
                        new_MovElem = MovElem(phrase.get_label(), 
                                              elements=phrase.get_tokens(), 
                                              position="insitu")
                        sentence.MovElems.append(new_MovElem)

            #Recursively repeat for dominated phrases
            for elem in phrase.get_elements():
                if isinstance(elem, Span):
                    get_phrase_position(elem, tree)
            
        ######################

        def get_relc_position(relc, tree):
            """
            Determine the position of a given relative clause
            based on the given constituency tree (including 
            topological fields).

            Dependency annotations are used to identify the antecedent.
            The spaCy dependency parser is expected to be the DepParser
            attribute of the class.
            Only if the automatic annotation does not find a suitable
            antecedent, the official (automatic) dependencies are used.

            The relative clause is modified in-place. The antecedent
            is added to the 'antecedents' list of the sentence.

            Input: RelC MovElem object, 
                   constituency tree in TuebaDZ style.
            """
            #Find node in tree
            node = MovElemIdentifier("news1").get_matching_field(relc, tree)

            #Get next dominating field
            field = node.parent_node
            while field != None and not field.is_root() \
                and not field.cat() in ["LV", "C", "LK", "VF", "FKOORD", "KOORD", "MF", 
                                        "MFE", "NF", "PARORD", "VC", "VCE", "FKONJ"]:
                field = field.parent_node

            #Create dependency parse
            doc = cls.DepParser(str(sentence))

            #If head token of the relative clause can be identified
            dep_head = [tok for tok in relc.get_tokens()
                        if doc[sentence.tokens.index(tok)].dep_ == "rc"]
            if dep_head:
                dep_head = dep_head[0]
                t = doc[sentence.tokens.index(dep_head)]
                #Get head token of the RelC
                relc_head = sentence.tokens[t.head.i]

                #Identify the matching node in the tree
                node = [t for t in tree.terminals() 
                        if t.token == relc_head]
                if not node:
                    relc.set_position("unknown")
                    return
                else:
                    node = node[0]

            #Check if RelC is a conjunct
            else:
                dep_head = [tok for tok in relc.get_tokens()
                            if doc[sentence.tokens.index(tok)].dep_ == "cj"
                            and doc[sentence.tokens.index(tok)].head.dep_ == "rc"]
                if dep_head:
                    dep_head = dep_head[0]
                    t = doc[sentence.tokens.index(dep_head)].head
                    #Get head token of the conjunct
                    relc_head = sentence.tokens[t.head.i]

                    #Identify the matching node in the tree
                    node = [t for t in tree.terminals() 
                            if t.token == relc_head]
                    if not node:
                        relc.set_position("unknown")
                        return
                    else:
                        node = node[0]

                #If no head of the relative clause is found
                #take the pre-annotated dependencies and try again
                else:

                    #Identify antecedent via dependencies
                    #Either directly connected via 'relc' link
                    #(and not inside the RelC!)
                    dep_head = [tok for tok in relc.get_tokens() 
                                if "relc" in tok.DEPREL 
                                and tok.head_tok != None 
                                and not tok.head_tok in relc.get_tokens()]
                    #Or connected via a conjunct of RelC
                    #(not inside the RelC)
                    if not dep_head:
                        dep_head = [tok for tok in relc.get_tokens()
                                    if tok.DEPREL == "conj" 
                                    and tok.head_tok != None 
                                    and "relc" in tok.head_tok.DEPREL 
                                    and tok.head_tok.head_tok != None 
                                    and not tok.head_tok.head_tok in relc.get_tokens()]
                        
                        #If dep_head is found here,
                        #then RelC is coordinated and shares its
                        #position and antecedent with the previous RelC
                        if dep_head:
                            dep_head = dep_head[0].head_tok
                            relc_conj = [m for m in sentence.MovElems
                                        if m.get_label() == "RELC"
                                        and dep_head in m.get_tokens()]
                            if relc_conj:
                                relc_conj = relc_conj[-1]
                                relc.set_position(relc_conj.get_position())
                                shared_antec = relc_conj.get_antecedent()
                                if shared_antec != None:
                                    antec = Antecedent(elements=shared_antec.get_tokens(), 
                                                       MovElemID=relc.get_ID())
                                    antec.set_headToks(shared_antec.get_headToks())
                                    sentence.antecedents.append(antec)
                                    relc.set_antecedent(antec)
                                    antec.set_MovElem(relc)
                            return

                        #If head is not found, position is unknown
                        else:
                            relc.set_position("unknown")
                            return 
                    
                    #Get head of antecedent
                    dep_head = dep_head[0]
                    if "relc" in dep_head.DEPREL:
                        relc_head = dep_head.head_tok
                    else:
                        relc_head = dep_head.head_tok.head_tok
                    if relc_head == None:
                        relc.set_position("unknown")
                        return

                    #Identify matching antecedent node in the tree
                    node = [t for t in tree.terminals() 
                            if t.token == relc_head]
                    if not node:
                        relc.set_position("unknown")
                        return
                    else:
                        node = node[0]

            #If an antecedent node was found,
            #take its parent to get the whole phrase
            if node.get_parent() != None:
                node = node.get_parent()
            while node != None \
                    and (node.simple_cat in ["NX:APP", "NX:KONJ"] 
                        or (node.simple_cat == "NX:HD" 
                            and node.get_parent().simple_cat.startswith("PX"))):
                node = node.get_parent()
            
            #Get tokens of the antecedent
            #(located before the relative clause)
            antec_tokens = [c.token for c in node.terminals() 
                            if int(c.token.ID)-1 < relc.get_start_index()]
            if not antec_tokens:
                relc.set_position("unknown")
                return
            
            #Strip off punctuation at begin and end
            while antec_tokens[0].XPOS.startswith("$"):
                antec_tokens = antec_tokens[1:]
            while antec_tokens[-1].XPOS.startswith("$"):
                antec_tokens = antec_tokens[:-1]

            #Create antecedent and link to RelC
            antec = Antecedent(elements=antec_tokens, MovElemID=relc.get_ID())
            antec.set_headToks([relc_head])
            sentence.antecedents.append(antec)
            relc.set_antecedent(antec)   
            
            #Coordinated RelCs (same antecedent with identical tokens)
            #share their position.
            relc_conj = [me for me in sentence.MovElems
                         if me != relc
                         and me.get_label() == "RELC"
                         and me.get_antecedent() != None
                         and me.get_antecedent().get_tokens() == antec.get_tokens()]
            if relc_conj:
                relc_conj = relc_conj[-1]
                relc.set_position(relc_conj.get_position())
                return

            #Otherwise determine position of the RelC
            #based on antecedent and field

            #Relc is in NF
            if field != None and field.cat() == "NF":

                #Antec is in NF, too
                if field.includes_span(antec) == True:
                    
                    #Something other than punct between both -> extrap
                    if any(not t.XPOS.startswith("$") 
                            for t in sentence.tokens[antec.get_end_index(ignore_punct=True)+1
                                                     :relc.get_start_index(ignore_punct=True)]):
                        relc.set_position("extrap")
                    #Otherwise, stays insitu
                        
                #Antec is not in NF
                else:

                    #Only punctuation between both -> ambig
                    if all(t.XPOS.startswith("$") 
                            for t in sentence.tokens[antec.get_end_index(ignore_punct=True)+1
                                                     :relc.get_start_index(ignore_punct=True)]):
                        relc.set_position("ambig")
                    #Something else between -> extrap
                    else:
                        relc.set_position("extrap")
                    
            #Relc is not in NF
            else:

                #Not only punct in between -> extrap
                if any(not t.XPOS.startswith("$") 
                        for t in sentence.tokens[antec.get_end_index(ignore_punct=True)+1:
                                                 relc.get_start_index(ignore_punct=True)]):
                    relc.set_position("extrap")
                #Otherwise -> stays insitu

        ######################
        
        #Determine position of phrases 
        #and add the relevant ones to MovElems
        for phrase in sentence.phrases:
            get_phrase_position(phrase, sentence.__dict__[tree])
        
        #Determine position of RelCs
        sentence.antecedents = []
        
        #For TuebaDS, determine position via field annotation
        #(because dependencies are not pre-annotated and not
        # accurate enough with automatic annotation; also the
        # sentences are not complex, i.e. the simple heuristics
        # of taking the previous phrase work very well.)
        if corpus == "TuebaDS":
            BerkeleyTopFParser.topftree_from_parsetree(sentence)
            MovElemIdentifier("news1").get_relc_positions(sentence)

        #For TuebaDZ, determine position via dependencies
        elif corpus == "TuebaDZ":
            relcID = 1
            for relc in [me for me in sentence.MovElems 
                            if me.get_label() == "RELC"]:
                relc.set_ID(relcID)
                get_relc_position(relc, sentence.__dict__[tree])
                relcID += 1

        #Store MovElems and antecedents in tokens
        sentence = MovElem.span_to_BIO_annotation(sentence, "MovElems", "MovElem")
        sentence = Antecedent.span_to_BIO_annotation(sentence, "antecedents", "Antec")

        return sentence

    ######################

    @classmethod
    def identify_MovElems_in_Tiger(cls, sentence, corpus="Tiger", tree="tree"):
        """
        Identify Moving Elements in Tiger-style corpora.

        Currently, only relative clauses in the Tiger corpus are annotated.
        Using the official constituency parse, dependency annotation,
        and a quite accurate topological field analysis, the relative clauses
        are identified and labeled with their position as 
        'insitu', 'ambig', 'extrap', or 'unknown'.

        Annotations are stored in sentence attributes 'MovElems' and 'antecedents'.

        Input: Sentence object, corpus name, tree name.
        Output: Annotated Sentence object.
        """
        sentence.MovElems = []

        #Get relative clauses
        if corpus == "Tiger":
            model = "news2"
        else:
            model = "hist"
        sentence.MovElems.extend(RelCFinder(model).read_RelCs_from_tree(sentence))

        ###############################

        def get_relc_position(relc, tree, topftree):
            """
            Determine the position of a given relative clause
            based on the given constituency and topological field tree.

            The relative clause is modified in-place. The antecedent
            is added to the 'antecedents' list of the sentence.

            Input: RelC MovElem object, 
                   constituency tree in Tiger style,
                   topological field tree.
            """
            #Find node and field for this relative clause in the trees
            node = MovElemIdentifier("news2").get_matching_field(relc, tree)
            field = MovElemIdentifier("news1").get_matching_field(relc, topftree)

            #Identify antecedent via dependencies
            #Either they are connected via 'rc' relation
            #(and the antecedent is not inside the RelC!)
            dep_head = [tok for tok in relc.get_tokens() 
                        if tok.DEPREL == "rc"
                        and tok.head_tok != None 
                        and not tok.head_tok in relc.get_tokens()]
            #Or the conjunct of the RelC is connected to the antecedent
            #(which is not inside the RelC)
            if not dep_head:
                dep_head = [tok for tok in relc.get_tokens()
                            if tok.DEPREL == "cj" 
                            and tok.head_tok != None 
                            and tok.head_tok.DEPREL == "cd" 
                            and tok.head_tok.head_tok != None 
                            and tok.head_tok.head_tok.DEPREL == "rc" 
                            and tok.head_tok.head_tok.head_tok != None 
                            and not tok.head_tok.head_tok.head_tok in relc.get_tokens()]
                #If no head is found, 
                #cannot determine the position
                if not dep_head:
                    relc.set_position("unknown")
                    return 

            #Set head of the antecedent
            dep_head = dep_head[0]
            if dep_head.DEPREL == "rc":
                relc_head = dep_head.head_tok
            else:
                relc_head = dep_head.head_tok.head_tok.head_tok
            
            #If no head exists, cannot determine position
            if relc_head == None:
                relc.set_position("unknown")
                return

            #Get the tree node that corresponds
            #to the antecedent head
            node = [t for t in tree.terminals() 
                    if t.token == relc_head]
            if not node:
                relc.set_position("unknown")
                return
            else:
                node = node[0]
                if node.get_parent() != None:
                    node = node.get_parent()
            
            #Get tokens of the antecedent
            #(i.e., children of the antecedent node
            # that are placed before the RelC)
            antec_tokens = [c.token for c in node.terminals() 
                            if int(c.token.ID)-1 < relc.get_start_index()]

            #Empty antecedent                
            if not antec_tokens:
                relc.set_position("unknown")
                return

            #Remove punctuation at begin and end
            while antec_tokens[0].XPOS.startswith("$"):
                antec_tokens = antec_tokens[1:]
            while antec_tokens[-1].XPOS.startswith("$"):
                antec_tokens = antec_tokens[:-1]

            #Create antecedent object and link it to the RelC
            antec = Antecedent(elements=antec_tokens, MovElemID=relc.get_ID())
            antec.set_headToks([relc_head])
            sentence.antecedents.append(antec)
            relc.set_antecedent(antec)   
            
            #RelC is in NF
            if field != None and field.cat() == "NF":

                #Antec is in NF, too
                if field.includes_span(antec) == True:
                    #Something other than punct between both -> extrap
                    if any(not t.XPOS.startswith("$") 
                            for t in sentence.tokens[antec.get_end_index(ignore_punct=True)+1
                                                     :relc.get_start_index(ignore_punct=True)]):
                        relc.set_position("extrap")
                        
                #Antec is not in NF
                else:
                    #Only punctuation between both -> ambig
                    if all(t.XPOS.startswith("$") 
                            for t in sentence.tokens[antec.get_end_index(ignore_punct=True)+1
                                                     :relc.get_start_index(ignore_punct=True)]):
                        relc.set_position("ambig")
                    #Something else between -> extrap
                    else:
                        relc.set_position("extrap")
                    
            #Relc is not in NF
            else:
                #Not only punct in between
                if any(not t.XPOS.startswith("$") 
                        for t in sentence.tokens[antec.get_end_index(ignore_punct=True)+1
                                                 :relc.get_start_index(ignore_punct=True)]):
                    relc.set_position("extrap")

        ###############################

        #Determine position of RelCs
        sentence.antecedents = []

        #Cannot reliably determine position for Mercurius/ReF.UP
        if corpus != "Tiger":
            pass

        elif corpus == "Tiger":
            #Initialize the topological field tree
            sentence.topftree = Tree.from_PTB_string(sentence.__dict__.get("TopFString"))
            sentence = SimplePTBInitializer().process_sentence(sentence, "topftree", "TopFString")

            relcID = 1
            for relc in [me for me in sentence.MovElems 
                         if me.get_label() == "RELC"]:
                #Assign a number to each RelC
                #(used to link it to the antecedent)
                relc.set_ID(relcID)
                #Determine the position (and antecedent)
                get_relc_position(relc, sentence.__dict__[tree], sentence.topftree)
                relcID += 1

        #Store MovElems and antecedents in tokens
        sentence = MovElem.span_to_BIO_annotation(sentence, "MovElems", "MovElem")
        sentence = Antecedent.span_to_BIO_annotation(sentence, "antecedents", "Antec")

        return sentence

###########################

def initialize(model, **kwargs):
    """
    Instantiates the MovElem identifier with the given model.

    Possible model names are 'news1', 'news2', 'hist' ,and 'mix'.

    Input: Model name
    Output: MovElemIdentifier object
    """
    if model in ["news1", "news2", "hist", "mix"]:
        myAnnotator = MovElemIdentifier(model, **kwargs)
    else:
        return None
    return myAnnotator

###########################

def analyze_relcs(docs, **kwargs):
    """
    Analyze relative clauses.

    For each relative clause in the input data,
    gets length, position, and distance to antecedent.
    The results are printed to an output file:
    - Corpus name,
    - Filename,
    - Sentence ID, 
    - RelC ID,
    - Position (insitu, ambig, extrap),
    - Length in words,
    - Distance to antecedent,
    - Distance to end of sentence.

    Input: List of doc objects
    """

    #Create evaluation file
    if not os.path.isdir(os.path.join(kwargs.get("eval_dir"), "relc-extrap")):
        os.makedirs(os.path.join(kwargs.get("eval_dir"), "relc-extrap"))
    resultfile = open(os.path.join(kwargs.get("eval_dir"), "relc-extrap", "relc_results.csv"), 
                      mode="a", encoding="utf-8")

    #For each doc object
    for doc in docs:
        filename = os.path.splitext(doc.filename)[0]

        for sent in doc.sentences:

            #Skip sentences without RelC
            if not any("B-RELC" in tok.__dict__.get("MovElem", "_") 
                       for tok in sent.tokens):
                continue

            #For each RelC
            for relc in RelCFinder.get_relcs(sent.MovElems):

                #Get length in words
                length = len([t for t in relc.get_tokens() 
                              if not t.XPOS.startswith("$")])

                #Get distance to antecedent
                if relc.get_antecedent() != None:
                    dist = relc.get_antecedent().get_distance(sent)
                else:
                    dist = None
                
                #Get distance to end of sentence
                dist_right = len([t for t in sent.tokens 
                                    if int(t.ID)-1 > relc.get_end_index(ignore_punct=True)
                                    and not t.XPOS.startswith("$")])

                #Print corpus, filename, sentence, RelC ID,
                #position, length, distance to antecedent,
                #and distance to end of sentence
                print(kwargs.get("corpus"), filename, sent.sent_id, 
                      relc.get_ID(), relc.get_position(), length, 
                      dist, dist_right, sep="\t", file=resultfile)
                    
    resultfile.close()

###############################