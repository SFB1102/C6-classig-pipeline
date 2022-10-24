# -*- coding: utf-8 -*-

from C6C.src.document import Token, Tree

###############################

class Span(object):

    def __init__(self, label, elements=[], parent_span = None, **kwargs):
        """
        Initialize a span object with a given label.

        Input:
        - Label of the span (e.g., RelC, NP or MF)
        - Elements that are included in the span, e.g., tokens or other spans
        - A parent span for nested spans (or None)
        - Additional attributes as key-word arguments
        """

        #Set label
        self.lab = label

        #Set parent span
        self.set_parent(parent_span)

        #Set included elements
        self.elems = []
        for element in elements:
            self.append_element(element)

        #Set additional attributes
        for key in kwargs:
            self.add_attrib(key, kwargs.get(key, "_"))

    ######################

    def add_attrib(self, key, val):
        """
        Add attribute value to the span.

        Input: Attribute name and value.
        """
        self.__dict__[key] = val

    ######################

    def __len__(self):
        """
        Return length of the span as number of included tokens.
        """
        l = 0
        for elem in self.elems:
            if isinstance(elem, Span) or issubclass(type(elem), Span):
                l += len(elem)
            elif type(elem) == Token:
                l += 1                
        return l
    
    ######################

    def __str__(self):
        """
        Return string representation of the span.

        Spans are represented in bracket form as:
        [Label elements]

        e.g. [S [NP This] [VP is] [NP an example]]
        """
        return "[{0} {1}]".format(self.lab, " ".join([str(elem) for elem in self.elems]))

    ########################

    def __iter__(self):
        """
        Yield included elements (spans and/or tokens).
        """
        for elem in self.elems:
            yield elem

    ########################

    def get_label(self):
        """
        Return the span label.
        """
        return self.lab

    ########################

    def set_label(self, label):
        """
        Set the span label to the given string.
        """
        self.lab = label

    ########################

    def get_elements(self):
        """
        Return the list of included elements (spans and/or tokens).
        """
        return self.elems

    ########################

    def get_tokens(self):
        """
        Return the list of included tokens.

        Also includes tokens from dominated spans.
        """
        tokens = []
        for elem in self.get_elements():
            if type(elem) == Token:
                tokens.append(elem)
            elif isinstance(elem, Span) or issubclass(type(elem), Span):
                tokens.extend(elem.get_tokens())
        return tokens

    #######################

    def remove_element(self, element):
        """
        Deletes the given element from the span.

        Return True, if element was included in the span.
        False, otherwise.

        Updates start and end index of self.
        """
        if element in self.elems:
            del self.elems[self.elems.index(element)]
            self.update_start_index()
            self.update_end_index()
            return True
        else:
            return False

    ########################

    def set_elements(self, elements):
        """
        Sets the elements of the span.

        Input should be an iterable, e.g. a list of tokens.

        Sets start and end index of the span.
        """
        #Reset elements
        self.elems = []

        #Add elements to span
        for elem in elements:

            #Inform elements about parent
            if isinstance(elem, Span) or issubclass(type(elem), Span):
                elem.set_parent(self)
            
            self.elems.append(elem)

        #Set start and end index
        self.update_start_index()
        self.update_end_index()
    
    ########################

    def insert_element(self, index, element):
        """
        Inserts a given element at the given index in the span.

        Indices are zero-based. If the index equals the length of the span,
        the element is appended to the span. Updates start and end of the span.

        If the index is outside of the span, prints a warning and returns None.
        """
        
        #Index inside of span
        if index < len(self.elems):
            #Set parent of element to self
            if isinstance(element, Span) or issubclass(type(element), Span):
                element.set_parent(self)

            #Insert element at index
            self.elems.insert(index, element)

            #Update start and end index
            self.update_start_index()
            self.update_end_index()

        #Append at end of span
        elif index == len(self.elems):
            self.append_element(element)

            #Update start and end index
            self.update_start_index()
            self.update_end_index()

        #Index outside of span
        else:
            print("Error: Cannot add element '{0}' at index {1} of span '{2}' with length {3}.".format(str(element), 
                  index, len(self.elems), str(self)))
            return None

    ########################

    def append_element(self, element):
        """
        Appends a given element to the span.

        Updates start and end of the span.
        """
        #This is the first element
        if not self.elems:
            if isinstance(element, Span) or issubclass(type(element), Span):
                element.set_parent(self)
            self.set_elements([element])
            self.update_start_index()
            self.update_start_index()

        #This is an additional element    
        else:
            #Inform element about parent
            if isinstance(element, Span) or issubclass(type(element), Span):
                element.set_parent(self)

            #Add to elements
            self.elems.append(element)

            #Update end ID
            self.update_end_index()
    
    ########################

    def get_start_index(self, ignore_punct=False):
        """
        Return start index of the span.

        Start index is the zero-based index of the first included token.
        If punctuation should be ignored, index of the first word token is used.

        Returns None, if no token exists, the token has no ID, 
        or (in case punctuation should be ignored) there are
        no tokens that are not punctuation.
        """
        if ignore_punct == False:
            if self.start == None:
                self.update_start_index()
            return self.start
        else:
            if self.elems:
                tokens = self.get_tokens()
                if tokens:
                    for t in tokens:
                        if not t.XPOS.startswith("$"):
                            return int(t.ID)-1
                    return None
                else:
                    return None
            else: 
                return None

    ########################

    def get_end_index(self, ignore_punct=False):
        """
        Return end index of the span.

        End index is the zero-based index of the last included token.
        If punctuation should be ignored, index of the last word token is used.

        Returns None, if no token exists, the token has no ID, 
        or (in case punctuation should be ignored) there are
        no tokens that are not punctuation.
        """
        if ignore_punct == False:
            if self.end == None:
                self.update_end_index()
            return self.end
        else:
            if self.elems:
                tokens = self.get_tokens()
                if tokens:
                    for t in reversed(tokens):
                        if not t.XPOS.startswith("$"):
                            return int(t.ID)-1
                    return None
                else:
                    return None
            else: 
                return None

    ########################

    def update_start_index(self):
        """
        Set the start index of the span.

        Index is set to zero-based index of first included token
        or None, if not applicable.

        The function is recursively applied to all included spans.
        """
        if self.elems:
            tokens = self.get_tokens()
            if tokens:
                self.start = tokens[0].__dict__.get("ID", None)
                if self.start: self.start = int(self.start)-1
            else:
                self.start = None
            for e in self.elems:
                if not isinstance(e, Token):
                    e.update_start_index()
        else:
            self.start = None

    ########################

    def update_end_index(self):
        """
        Set the end index of the span.

        Index is set to zero-based index of last included token
        or None, if not applicable.

        The function is recursively applied to all included spans.
        """
        if isinstance(self, Token):
            return 

        if self.elems:
            tokens = self.get_tokens()
            if tokens:
                self.end = tokens[-1].__dict__.get("ID", None)
                if self.end: self.end = int(self.end)-1
            else:
                self.end = None
            for e in self.elems:
                if not isinstance(e, Token):
                    e.update_end_index()
        else:
            self.end = None

    ########################

    def get_parent(self):
        """
        Return parent span (or None).
        """
        return self.parent

    ########################

    def set_parent(self, parent_span):
        """
        Set parent span.
        """
        self.parent = parent_span

    ########################

    def is_complex(self):
        """
        Return True, if self is complex. False, otherwise.

        A span is complex if it contains ano other span object(s).
        """
        if any(isinstance(e, Span) or issubclass(type(e), Span) 
               for e in self.get_elements()):
            return True
        else:
            return False

    ########################

    def includes_span(self, span):
        """
        Return True, if the given span object is included
        in self. False, otherwise.

        Compares start and end indices of both spans
        (ignoring punctuation) to determine if the given span
        lies within self or is identical to it.
        """

        #Get start and end indices (without punctuation)
        start_s1 = self.get_start_index(ignore_punct=True)
        end_s1 = self.get_end_index(ignore_punct=True)
        start_s2 = span.get_start_index(ignore_punct=True)
        end_s2 = span.get_end_index(ignore_punct=True)

        #If span starts at the same or a greater index
        #and ends at the same or a smaller index
        #it is included.
        if start_s1 <= start_s2 and end_s1 >= end_s2:
            return True
        else:
            return False
            
    ########################

    @classmethod
    def span_from_BIO_annotation(cls, sentence, annoname):
        """
        Read span objects from BIO annotations.

        BIO annotations must be attributes of tokens in the sentence.
        Annotations may be complex, i.e., stacked with pipes.

        Example annotations:
        B-NP
        I-NF|I-MF|B-LK

        Input: Sentence object and attribute name of annotations.
        Output: List of span objects.
        """

        spans = []
        span_stack = []

        #For each token
        for tok in sentence.tokens:

            #Token not annotated
            if tok.__dict__.get(annoname, "O") in ["O", "_"]:
                #Add previous stack to span list
                while span_stack:
                    spans.append(span_stack[0])
                    span_stack = []
                continue
                                
            #Token is annotated
            #Get list of (stacked) annotation(s)
            annotations = tok.__dict__.get(annoname, "O").strip().split("|")

            #Cut stack to length of this token's annotations
            while len(span_stack) > len(annotations):
                span_stack.pop()

            #For each annotation level
            for i, annotation in enumerate(annotations):
                
                #New span
                if annotation.startswith("B-"):
                    
                    #On level one
                    if i == 0 and span_stack:
                        #Move existing spans from stack to span list
                        spans.append(span_stack.pop())

                    else:
                        #Cut stack to one level below this annotation
                        while len(span_stack) > i:
                            span_stack.pop()
                    
                    #Get label
                    label = annotation.split("-")[1]

                    #Dominating span: create span that
                    #will include dominated spans
                    if i < len(annotations)-1:
                        p = Span(label, [])
                    #Non-dominating span: include token
                    else:
                        p = Span(label, [tok])

                    #If there are spans on the stack
                    if span_stack:
                        #Make the last one parent
                        #and this one its child
                        p.set_parent(span_stack[-1])
                        span_stack[-1].append_element(p)
                    
                    #Append to the stack
                    span_stack.append(p)

                #Span continues
                elif annotation.startswith("I-"):
                    #Add token to the last span on the stack
                    span_stack[i].append_element(tok)    

        #Add sentence final span from stack to list
        if span_stack:
            spans.append(span_stack[0])
        
        for span in spans:
            span.update_start_index()
            span.update_end_index()

        #Return list of spans
        return spans

    ########################

    @classmethod
    def span_to_BIO_annotation(cls, sentence, spanname, annoname):
        """
        Turn span objects into BIO annotations.

        Spans must be included as attribute of the sentence (list of span objects).
        BIO annotations are stored as attribute of the tokens.
        Complex annotations are stacked with pipes.

        Example annotations:
        B-NP
        I-NF|I-MF|B-LK

        Tokens outside of spans are annotated with 'O'.

        Input: Sentence object, name of the spans, attribute name of annotations.
        Output: Modified sentence object.
        """

        ##########################

        def get_bio_spans(span):
            """
            Recursively get span tuples.

            Input: Span object
            Output: List of span tuples (label, startIndex, endIndex)
            """
            spans = []

            #Make sure that indices are correct
            span.update_end_index()
            span.update_start_index()

            #Add tuple of this span
            spans.append((span.get_label(), span.get_start_index(), span.get_end_index()))

            #For each included span, repeat recursively
            for elem in span.get_elements():
                if isinstance(elem, Span) or issubclass(type(elem), Span):
                    spans.extend(get_bio_spans(elem))
            
            return spans

        ##########################
        
        #Create list with empty annotation for all tokens
        bio_annotations = ["" for _ in sentence.tokens]

        #For each span
        for span_obj in sentence.__dict__.get(spanname, []):
            
            #Recursively get span tuples with label, start, and end
            bio_spans = get_bio_spans(span_obj)

            #Add spans to annotation of the respective tokens
            for span in sorted(bio_spans, key=lambda l: (l[1], 0-l[2])):
                if bio_annotations[span[1]]:
                    bio_annotations[span[1]] += "|" + "B-"+span[0]
                else:
                    bio_annotations[span[1]] += "B-"+span[0]
                for i in range(span[1]+1, span[2]+1):
                    if bio_annotations[i]:
                        bio_annotations[i] += "|" + "I-"+span[0]
                    else:
                        bio_annotations[i] += "I-"+span[0]
           
        #Add O for tokens outside spans
        for t in range(len(bio_annotations)):
            if not bio_annotations[t]:
                bio_annotations[t] = "O"
        
        #Move annotations from list to token attributes
        for tok, bio in zip(sentence.tokens, bio_annotations):
            tok.__dict__[annoname] = bio
        
        return sentence

    ########################

    @classmethod
    def tree_to_BIO_annotation(cls, sentence, treename, annoname):
        """
        Turn a tree object into BIO annotations.

        BIO annotations are stored as attribute of the tokens.
        Hierarchical annotations are stacked with pipes.

        Example annotations:
        I-S|I-NF|I-MF|B-LK

        Tokens outside of the tree are annotated with 'O'.

        Input: Sentence object, name of the tree attribute, attribute name of annotations.
        Output: Modified sentence object.
        """

        ##########################

        def get_bio_spans(node):
            """
            Recursively get node tuples.

            Input: Tree object
            Output: List of node tuples (cat, startIndex, endIndex)
            """
            if node.is_terminal():
                return []

            spans = []

            #Add tuple of this node
            spans.append((node.cat(), node.get_start_index(), node.get_end_index()))

            #Recursively repeat
            for child in node:
                if not child.is_terminal():
                    spans.extend(get_bio_spans(child))

            return spans

        ##########################
        
        #Create list with empty annotation for all tokens
        bio_annotations = ["" for _ in sentence.tokens]

        bio_spans = []
        
        #Recursively get tuples of cat, start and end
        for node in sentence.__dict__.get(treename, []):
            bio_spans.extend(get_bio_spans(node))
            
        #Add spans to annotation of the respective tokens
        for span in sorted(bio_spans, key=lambda l: (l[1], 0-l[2])):
            
            if bio_annotations[span[1]]:
                bio_annotations[span[1]] += "|" + "B-"+span[0]
            else:
                bio_annotations[span[1]] += "B-"+span[0]
            for i in range(span[1]+1, span[2]+1):
                if bio_annotations[i]:
                    bio_annotations[i] += "|" + "I-"+span[0]
                else:
                    bio_annotations[i] += "I-"+span[0]
        
        #Add O for tokens outside spans
        for t in range(len(bio_annotations)):
            if not bio_annotations[t]:
                bio_annotations[t] = "O"
        
        #Move annotations from list to token attributes
        for tok, bio in zip(sentence.tokens, bio_annotations):
            tok.__dict__[annoname] = bio
        
        return sentence

    ########################

    @classmethod
    def span_from_tueba_fields(cls, sentence, sep="-", annoname="TopoField"):
        """
        Turn topological field annotations from the TuebaDZ corpus into spans.

        Annotations are expected to be stored as token attribute, e.g.
        NF-MF-LK

        The resulting span list is stored as sentence attribute.
        Tokens outside of fields are annotated with 'O'.

        Input:
        - Sentence object
        - Separator between BIO tags (default '-')
        - Attribute name of annotations
        Output: List of span objects.
        """

        spans = []
        span_stack = []

        #For each token
        for tok in sentence.tokens:

            #Token not annotated
            if tok.__dict__.get(annoname, "O") in ["_", "O", ""]:
                #Add previous stack to span list
                if span_stack:
                    spans.append(span_stack[0])
                    span_stack = []
                continue
                                
            #Token is annotated
            #Get list of (stacked) annotation(s)
            annotations = tok.__dict__.get(annoname, "O").strip().split(sep)

            #Cut stack to length of this token's annotations
            while len(span_stack) > len(annotations):
                span_stack.pop()
            
            #Remove differing annotations from stack
            for s in range(len(span_stack)):
                if span_stack[s].get_label() != annotations[s]:
                    if s == 0:
                        spans.append(span_stack[0])
                        span_stack = []
                    else:
                        span_stack = span_stack[:s]
                    break

            #For each annotation level
            for i, label in enumerate(annotations):
                
                #New span
                if len(span_stack) <= i:

                    #Dominating span: create span that
                    #will include dominated spans
                    if i < len(annotations)-1:
                        p = Span(label, [])
                    #Non-dominating span: include token
                    else:
                        p = Span(label, [tok])
                    
                    #If there are spans on the stack
                    if span_stack:
                        #Make the last one parent
                        #and this one its child
                        p.set_parent(span_stack[-1])
                        span_stack[-1].append_element(p)
                    
                    #Append to the stack
                    span_stack.append(p)

                #Span continues
                elif i == len(annotations)-1:
                    #Add token to the last span on the stack
                    span_stack[i].append_element(tok)

        #Add sentence final span from stack to list
        if span_stack:
            spans.append(span_stack[0])

        for span in spans:
            span.update_start_index()
            span.update_end_index()

        #Return list of spans
        return spans

    ########################

    def has_subordinate_XP(self, label):
        """
        Return True if span dominates a span with the given label.
        Considers direct and indirect dominance.
        """
        has_xp = False

        #For complex spans
        if self.is_complex():

            #Recursively check each element
            for element in self.get_elements():
                if type(element) == Span:

                    #If any element has the desired label
                    #return True
                    if element.get_label() == label:
                        has_xp = True
                        break
                    else:
                        if element.has_subordinate_XP(label):
                            has_xp = True         
        return has_xp

    ########################

    @classmethod
    def read_phrases_from_simplified_tiger(cls, sentence, treename="tree"):
        """
        Function to read phrase spans from a Tiger-style constituency tree.
        Trees must be linearized and simplified according to the descriptions
        in Ortmann (2021b).

        Input: Sentence object and name of the tree attribute.
        Output: List of phrase spans.
        """    

        #Without tree cannot identify any phrases
        if not sentence.__dict__[treename]:
            return [] 

        ############################

        def tree_to_phrase(tree):
            
            phrases = []

            for node in tree.nodes():
                
                if node.is_terminal():

                    if tree.simple_cat.split(":")[0].lstrip("C") not in ["NP", "PP", "PN", 
                                                                         "NM", "AP", "AVP", "AA"]:
                        if node.token.XPOS in ["PRELS", "PDS", "PIS", "PPER", "PPOSS", "PRELS", 
                                               "PRF", "PWS", "NN", "NE", "CARD"]:
                            p = Span("NP", elements=[node.token])
                            phrases.append(p)
                        elif node.token.XPOS in ["ADV", "PTKNEG"]:
                            p = Span("ADVP", elements=[node.token])
                            phrases.append(p)
                        elif node.token.XPOS.startswith("ADJ"):
                            p = Span("AP", elements=[node.token])
                            phrases.append(p)
                        elif node.token.XPOS in ["PROP", "PROAV", "PAV"]:
                            p = Span("PP", elements=[node.token])
                            phrases.append(p)
                        else:
                            phrases.append(node.token)
                    else:
                        phrases.append(node.token)
                else:
                    category = node.simple_cat.split(":")[0]
                    if category.lstrip("C") in ["NP", "PP", "PN", "NM", 
                                                "AP", "AVP", "AA"]:
                        p = Span(category, elements=[])
                        if category == "AA":
                            p.set_label("AP")
                        for subphrase in tree_to_phrase(node):
                            p.append_element(subphrase)
                        phrases.append(p)
                    else:
                        phrases.extend(tree_to_phrase(node))

            return phrases

        ############################

        #Analyze sentences without VROOT
        if not sentence.__dict__[treename].cat() == "VROOT":
            sentence.__dict__[treename] = Tree("DUMMY", "VROOT", "DUMMY", 
                                               nodes=[sentence.__dict__[treename]])
        
        #Recursiveley read phrases from tree
        phrases = tree_to_phrase(sentence.__dict__[treename])

        #Remove tokens outside of phrases
        phrases = [p for p in phrases if type(p) == Span]
        
        ################################
        #Rename AVPs
        def rename_AVPs(phrase):
            if type(phrase) == Span:
                if "AVP" in phrase.get_label():
                    phrase.set_label(phrase.get_label().replace("AVP", "ADVP"))
                for e in phrase.get_elements():
                    rename_AVPs(e)
        
        for phrase in phrases:
            rename_AVPs(phrase)
        
        ################################
        #Remove NMs
        def remove_NMs(phrase):
            if type(phrase) == Span:

                if phrase.get_label() == "NM":
                    #Replace NM phrase with its content
                    if phrase.get_parent() != None: 
                        i = phrase.get_parent().get_elements().index(phrase)
                        phrase.get_parent().remove_element(phrase)
                        for e, element in enumerate(phrase.get_elements()):
                            phrase.get_parent().insert_element(i+e, element)
                        phrase = phrase.get_parent()
                    #Or rename to NP if phrase has no parent
                    else:
                        phrase.set_label("NP")

                #Add NPs for cardinal numbers if they follow a noun
                elif phrase.get_label() in ["NP", "PP"]:
                    noun = [e for e in phrase.get_elements() 
                            if type(e) == Token and e.XPOS in ["NN"]]
                    card = [e for e in phrase.get_elements() 
                            if type(e) == Token and e.XPOS == "CARD"]
                    if card and noun:
                        while card and noun:
                            if phrase.get_elements().index(noun[0]) == phrase.get_elements().index(card[0])-1:
                                phrase.elems[phrase.get_elements().index(card[0])] = Span("NP", [card[0]], parent=phrase)
                                del card[0]
                                del noun[0]
                            else:
                                del card[0]

                #Recursively repeat
                for e, element in enumerate(phrase.get_elements()):
                    remove_NMs(element)

        for p in range(len(phrases)):
            remove_NMs(phrases[p])

        ###############################
        #Replace PN phrases with NPs
        def replace_PN_phrases(phrase):

            if type(phrase) == Span:

                if phrase.get_label() == "PN":

                    #Identical with subphrase
                    if len(phrase.get_elements()) == 1 \
                       and type(phrase.get_elements()[0]) == Span:

                        #Remove PN entirely
                        if phrase.get_parent() != None:
                            i = phrase.get_parent().get_elements().index(phrase)
                            phrase.get_parent().remove_element(phrase)
                            if not any(type(t) == Token and t.XPOS in ["PRELS", "PDS", "PIS", "PPER", "PPOSS", 
                                                                       "PRELS", "PRF", "PWS", "NN", "NE"] 
                                       for t in phrase.get_parent().get_elements()):
                                for elem in reversed(phrase.get_elements()[0].get_elements()):
                                    phrase.get_parent().insert_element(i, elem)
                            else:
                                phrase.get_parent().insert_element(i, phrase.get_elements()[0])
                            phrase = phrase.get_parent()
                        else:
                            phrase = phrase.get_elements()[0]
                            phrase.set_parent(None)

                    #PN in NP without Nouns
                    elif phrase.get_parent() != None \
                        and phrase.get_parent().get_label() != "CNP" \
                        and not any(type(e) == Token and e.XPOS in ["PRELS", "PDS", "PIS", "PPER", "PPOSS", 
                                                                    "PRELS", "PRF", "PWS", "NN", "NE"]
                                    for e in phrase.get_parent().get_elements()) \
                        and not any(type(e) == Span and e.get_label() == "CNP"
                                    for e in phrase.get_parent().get_elements()[:phrase.get_parent().get_elements().index(phrase)]):
                        #Remove PN
                        i = phrase.get_parent().get_elements().index(phrase)
                        phrase.get_parent().remove_element(phrase)
                        for e, element in enumerate(phrase.get_elements()):
                            phrase.get_parent().insert_element(i+e, element)
                        phrase = phrase.get_parent()

                    #Rename other PNs
                    else:
                        phrase.set_label("NP")
                    
                #Recursively repeat
                for e in range(len(phrase.get_elements())):
                    replace_PN_phrases(phrase.get_elements()[e])

            return phrase   

        for p in range(len(phrases)):
            phrases[p] = replace_PN_phrases(phrases[p])

        #####################################
        #Add VPs inside phrases for chunking
        def add_VPs(phrase):
            e = 0
            while e < len(phrase.get_elements()):
                element = phrase.get_elements()[e]
                if type(element) == Token \
                    and (element.XPOS.startswith("V") or element.XPOS in ["PTKVZ", "PTKZU"]):
                    if e > 0 and type(phrase.get_elements()[e-1]) == Span \
                        and phrase.get_elements()[e-1].get_label() == "VP":
                        phrase.get_elements()[e-1].append_element(element)
                        phrase.remove_element(element)
                    else:   
                        phrase.get_elements()[e] = Span("VP", [element], parent=phrase)
                        e += 1
                elif type(element) == Span:
                    add_VPs(element)
                    e += 1
                else:
                    e += 1
        
        for p in phrases:
            add_VPs(p)

        #####################################
        #Remove non-complex APs inside NPs and PPs
        def remove_non_complex_APs(phrase):
            for e, element in enumerate(phrase.get_elements()):
                if type(element) == Span:

                    #Non-complex AP
                    #inside an NP or PP
                    #not followed by a phrase or something other than a noun/name
                    if element.get_label() == "AP" and not element.is_complex() \
                    and phrase.get_label() in ["NP", "PP", "ADVP", "AP"] \
                    and not (e == len(phrase.get_elements())-1 
                             or (e < len(phrase.get_elements())-1 and \
                                (type(phrase.get_elements()[e+1]) == Span))):

                        #Remove the AP
                        phrase.remove_element(element)
                        for a, adj in enumerate(element.get_elements()):
                            phrase.insert_element(e+a, adj)
                        
                    #Other phrase: enter recursion
                    else:
                        element = remove_non_complex_APs(element)

            return phrase   

        for p in phrases:
            #Remove non-complex APs two times
            #to deal with APs inside APs
            remove_non_complex_APs(p)
            remove_non_complex_APs(p)
        
        #####################################
        #Correct APs without adjectives
        #Non-complex AP without any adjective
        def correct_APs(phrase):
            if type(phrase) == Span:
                if phrase.get_label() == "AP" and not phrase.is_complex():
                    if not any(e.XPOS.startswith("ADJ") for e in phrase.get_elements()):
                        if any(e.XPOS.startswith("APP") for e in phrase.get_elements()):
                            phrase.set_label("PP")
                        elif any(e.XPOS in ["PRELS", "PDS", "PIS", "PPER", "PPOSS", 
                                            "PRELS", "PRF", "PWS", "NN", "NE"] 
                                    for e in phrase.get_elements()):
                            phrase.set_label("NP")
                        elif any(e.XPOS in ["ADV", "PTKNEG"] for e in phrase.get_elements()):
                            phrase.set_label("ADVP")
                        elif any(e.XPOS in ["PROP", "PROAV", "PAV"] for e in phrase.get_elements()):
                            phrase.set_label("PP")
                else:
                    for e in phrase.get_elements():
                        correct_APs(e)

        for p in phrases:
            correct_APs(p)

        ################################
        #Remove pseudo complex APs (including coordinated ones)
        #inside of NP or PP phrases
        def remove_pseudo_complex_APs(phrase):
            i = 0
            while i < len(phrase.get_elements()):
                e = phrase.get_elements()[i]
                if type(e) == Span:
                    if e.get_label().lstrip("C") == "AP" and phrase.get_label() in ["NP", "PP"]:
                        if not any(e.has_subordinate_XP(p) for p in ["NP", "PP", "ADVP"]) \
                           and i < len(phrase.get_elements())-1 \
                           and type(phrase.get_elements()[i+1]) == Token:
                            phrase.remove_element(e)
                            for j, se in enumerate(e.get_elements()):
                                phrase.elems.insert(i+j, se)
                        else:
                            for se in phrase.get_elements():
                                if type(se) == Span:
                                    remove_pseudo_complex_APs(se)
                                i += 1
                    else:
                        remove_pseudo_complex_APs(e)
                        i += 1
                else:
                    i += 1

        for p in phrases:
            remove_pseudo_complex_APs(p)

        #####################################
        #Correct coordinations
        def correct_coordinations(phrases):
            
            p = 0
            while p < len(phrases):
                phrase = phrases[p]
            
                if type(phrase) == Token:
                    p += 1
                    continue
                
                #Coordination phrase
                if phrase.get_label().startswith("C"):
                    
                    #Coordinated AP
                    if phrase.get_label() == "CAP":
                        aps = [e for e in phrase.get_elements() 
                               if type(e) == Span and e.get_label() == "AP"]

                        #Coordination of adjectives instead of phrases
                        if not aps or len(aps) < 2:
                            tok_conjuncts = []
                            for e in phrase.get_elements():
                                if type(e) == Token and e.XPOS.startswith("ADJ"):
                                    tok_conjuncts.append(e)
                            for conj in tok_conjuncts:
                                phrase.elems[phrase.get_elements().index(conj)] = Span("AP", 
                                                                                       elements=[conj], 
                                                                                       parent=phrase)

                        aps = [e for e in phrase.get_elements() 
                               if type(e) == Span and e.get_label() == "AP"]

                        #Non-complex in NP/PP
                        if phrase.get_parent() != None and phrase.get_parent().get_label() in ["NP", "PP"] \
                        and all(not ap.is_complex() for ap in aps) \
                        and not any(type(t) == Token and t.XPOS in ["PRELS", "PDS", "PIS", "PPER", "PPOSS", 
                                                                    "PRELS", "PRF", "PWS", "NN", "NE"]
                                    for t in phrase.get_parent().get_elements()[:phrase.get_parent().get_elements().index(phrase)]) \
                        and p < len(phrase.get_parent().get_elements())-1 \
                        and any((type(t) == Token and t.XPOS in ["PRELS", "PDS", "PIS", "PPER", "PPOSS", 
                                                                "PRELS", "PRF", "PWS", "NN", "NE"])
                                or (type(t) == Span and t.get_label() in ["CNP"])
                                for t in phrase.get_parent().get_elements()[phrase.get_parent().get_elements().index(phrase)+1:]):
                            #Remove AP
                            phrase.get_parent().remove_element(phrase)
                            for i, t in enumerate(phrase.get_tokens()):
                                phrase.get_parent().insert_element(p+i, t)

                        #Otherwise
                        else:
                            #Rename to AP
                            phrase.set_label("AP")
                    
                    #Less than two phrases
                    elif len([e for e in phrase.get_elements() if type(e) == Span]) < 2:

                        tok_conjuncts = []

                        if phrase.get_label() == "CNP":
                            #Get nouns/names/pronouns
                            for e in phrase.get_elements():
                                if type(e) == Token \
                                   and e.XPOS in ["PRELS", "PDS", "PIS", "PPER", "PPOSS", 
                                                  "PRELS", "PRF", "PWS", "NN", "NE", "TRUNC", "CARD"]:
                                    tok_conjuncts.append(e)

                        elif phrase.get_label() == "CPP":
                            #Get nouns/names/pronouns
                            for e in phrase.get_elements():
                                if type(e) == Token \
                                   and e.XPOS in ["PRELS", "PDS", "PIS", "PPER", "PPOSS", 
                                                  "PRELS", "PRF", "PWS", "NN", "NE", "TRUNC", "CARD"]:
                                    tok_conjuncts.append(e)

                        elif phrase.get_label() == "CAVP":
                            #Get adverbs
                            for e in phrase.get_elements():
                                if type(e) == Token and e.XPOS == "ADV":
                                    tok_conjuncts.append(e)
                        
                        #Coordination of words instead of phrases
                        if tok_conjuncts:
                            for conj in tok_conjuncts:
                                phrase.elems[phrase.get_elements().index(conj)] = Span(phrase.get_label().lstrip("C"), 
                                                                                    elements=[conj], parent=phrase)
                            phrase.set_label(phrase.get_label().lstrip("C"))
                    
                        #Only coordination and a single phrase
                        elif any(e for e in phrase.get_elements() if type(e) == Span):
                            #Remove coordination
                            phrases[p] = [e for e in phrase.get_elements() if type(e) == Span][0]
                        
                        else:
                            phrase.set_label(phrase.get_label().lstrip("C"))

                    #Other coordinations
                    else:
                        #Rename
                        phrase.set_label(phrase.get_label().lstrip("C"))
                
                #Recursively repeat for all sub-phrases
                phrase.set_elements(correct_coordinations(phrase.get_elements()))

                p += 1

            return phrases 

        phrases = correct_coordinations(phrases)

        ################################
        #Add ADVPs
        def add_ADVPs(phrase):
            for i, element in enumerate(phrase.get_elements()):
                if type(element) == Token:
                    #For adverbs whose parents are not ADVPs
                    if element.XPOS == "ADV" and not phrase.get_label() == "ADVP":
                        if i < len(phrase.get_elements())-1:
                            #If next element is a phrase
                            if type(phrase.get_elements()[i+1]) == Span:
                                #Add an ADVP for this adverb
                                p = Span("ADVP", elements=[element])
                                phrase.elems[i] = p
                else:
                    for j, e in enumerate(reversed(element.get_elements())):
                        if type(e) == Span:
                            add_ADVPs(e)
                        elif e.XPOS == "ADV" and not element.get_label() == "ADVP":
                            if j > 0:
                                if type(element.get_elements()[j-1]) == Span:
                                    p = Span("ADVP", elements=[e])
                                    element.elems[element.get_elements().index(e)] = p

        for phrase in phrases:
            add_ADVPs(phrase)

        ##########################################
        #Remove phrases which only contain phrases
        def remove_phrases_without_tokens(phrases):
            p = 0
            while p < len(phrases):
                phrase = phrases[p]
                if type(phrase) == Span:
                    if all(type(e) == Span 
                           or (type(e) == Token and e.XPOS.startswith("$")) 
                           for e in phrase.get_elements()):
                        phrases[p:p+1] = [e for e in phrase.get_elements() if type(e) == Span]
                    elif any(type(e) == Span for e in phrase.get_elements()):
                        phrase.set_elements(remove_phrases_without_tokens(phrase.get_elements()))
                        p += 1
                    else:
                        p += 1
                else:   
                    p += 1
            return phrases

        phrases = remove_phrases_without_tokens(phrases)

        ###############################################
        #Recursively update indices and parents
        def update_dependencies_and_indices(phrase):
            #Update indices of elements
            phrase.update_start_index()
            phrase.update_end_index()
            if type(phrase) == Span:
                for element in phrase.get_elements():
                    if type(element) == Span:
                        #Update parent of element
                        element.set_parent(phrase)
                        update_dependencies_and_indices(element)

        for phrase in phrases:
            update_dependencies_and_indices(phrase)

        ##################################################
        #Recursively sort phrases according to start index
        def sort_phrases_by_start_index(phrases):

            def calculate_start_index(element):
                if type(element) == Token:
                    return int(element.ID)-1
                elif type(element) == Span:
                    return element.get_start_index()

            phrases.sort(key=lambda p: calculate_start_index(p))

            for p in phrases:
                if type(p) == Span:
                    sort_phrases_by_start_index(p.get_elements())

        sort_phrases_by_start_index(phrases)
        
        return phrases

    #######################

    @classmethod
    def read_phrases_from_simplified_tueba(cls, sentence, treename="tree"):
        """
        Function to read phrase spans from a TueBa-style constituency tree.
        Trees must be simplified according to the descriptions in Ortmann (2021b).

        Input: Sentence object and name of the tree attribute.
        Output: List of phrase spans.
        """

        phrases = []
        if not sentence.__dict__[treename]:
            return phrases

        ############################

        def tree_to_phrase(tree):
            
            phrases = []

            for node in tree.nodes():
                
                if node.is_terminal():
                    phrases.append(node.token)
                else:
                    category = node.simple_cat.split(":")[0]
                    if ":" in node.simple_cat:
                        label = node.simple_cat.split(":")[1]
                    else:
                        label = "--"
                    if category in ["NX", "PX", "ADJX", "ADVX"]:
                        p = Span(category.replace("X", "P"), elements=[])
                        if p.get_label() == "ADJP":
                            p.set_label("AP")
                        if label == "HD":
                           p.HEAD = True
                        elif label == "APP" \
                            and not any("HD" in n.simple_cat for n in tree.nodes()) \
                            and node == [n for n in tree.nodes() if "APP" in n.simple_cat][0]:
                            p.HEAD = True
                        else: p.HEAD = False
                        for subphrase in tree_to_phrase(node):     
                            p.append_element(subphrase)
                        phrases.append(p)
                    else:
                        phrases.extend(tree_to_phrase(node))

            return phrases

        ############################
        
        #Recursiveley read phrases from tree
        phrases = tree_to_phrase(sentence.__dict__[treename])

        #Remove tokens outside of phrases
        phrases = [p for p in phrases if type(p) == Span]
        
        #####################################
        #Remove non-complex APs inside NPs and PPs
        def remove_non_complex_APs(phrase):

            for e, element in enumerate(phrase.get_elements()):
                if type(element) == Span:

                    #Non-complex AP
                    #inside an NP or PP
                    #not followed by a phrase or something other than a noun/name
                    if element.get_label() == "AP" \
                    and (not element.is_complex() \
                         or not any(element.has_subordinate_XP(p) for p in ["NP", "PP"])) \
                    and phrase.get_label() in ["NP", "PP", "ADVP", "AP"] \
                    and not (e == len(phrase.get_elements())-1 
                             or (e < len(phrase.get_elements())-1 and \
                                (type(phrase.get_elements()[e+1]) == Span))):

                        #Remove the AP
                        i = 0
                        phrase.remove_element(element)
                        for adj in element.get_elements():
                            if type(adj) == Span:
                                for sp in adj.get_elements():
                                    phrase.insert_element(e+i, sp)
                                    i += 1
                            else:
                                phrase.insert_element(e+i, adj)
                                i += 1
                        
                    #Other phrase: enter recursion
                    else:
                        element = remove_non_complex_APs(element)

            return phrase   

        for p in phrases:
            #Remove non-complex APs two times
            #to deal with APs inside APs
            remove_non_complex_APs(p)
            remove_non_complex_APs(p)

        #####################################
        #Correct PPs whose only token is a preposition
        #or without any preposition at all
        def correct_PPs(phrase):
            if type(phrase) != Span:
                return

            while any(type(e) == Span and e.HEAD 
                      for e in phrase.get_elements()):

                head = [e for e in phrase.get_elements() 
                        if type(e) == Span and e.HEAD][0]
                
                i = phrase.get_elements().index(head)
                phrase.remove_element(head)

                for e in head.get_elements():
                    phrase.insert_element(i, e)
                    i += 1

            for p in phrase.get_elements():
                correct_PPs(p)

        ###############################

        for p in phrases:
            correct_PPs(p)

        ###############################

        def remove_phrases(phrases):
            p = 0
            while p < len(phrases):
                phrase = phrases[p]
                if all(type(e) == Token and e.XPOS in ["PWAV"] 
                       for e in phrase.get_elements()):
                    del phrases[p]
                else:
                    p += 1
            return phrases

        ##############################

        phrases = remove_phrases(phrases)

        ##############################

        def remove_subphrases(phrase):
            if type(phrase) != Span:
                return
            else:
                e = 0
                while e < len(phrase.get_elements()):
                    elem = phrase.get_elements()[e]
                    if type(elem) == Span:
                        if (elem.get_label() == "ADVP" \
                           and all(type(t) == Token and t.XPOS in ["PWAV"] 
                                   for t in elem.get_elements())) \
                           or all(type(t) == Token and t.XPOS.startswith("$") 
                                  for t in elem.get_elements()):
                            i = 0
                            phrase.remove_element(elem)
                            for subelem in elem.get_elements():
                                phrase.insert_element(e+i, subelem)
                        else:
                            remove_subphrases(elem)
                            e += 1
                    else:
                        e += 1
        
        ############################

        for p in phrases:
            remove_subphrases(p)

        for span in phrases:
            span.update_start_index()
            span.update_end_index()

        return phrases

###############################

class MovElem(Span):

    def __init__(self, label, elements, position, MovElemID = None, Antecedent = None, 
                 parent_span = None, headToks = [], vposition = None, **kwargs):
        """
        Initialize a moving element as a special type of span.

        A moving element can have:
        - a label (e.g., RelC, NP)
        - a list of included elements
        - a position (e.g., insitu, ambig or extrap)
        - an ID (to be connected to an antecedent)
        - an antecedent, if applicable (or None)
        - a parent span
        - a list of head tokens (verb(s) of adverbial clauses)
        - a verb position (V2 or VL for adverbial clauses)
        - additional attributes as key-word arguments
        """
        
        #Call span constructor
        super().__init__(label, elements, parent_span=parent_span, **kwargs)

        #Set attributes specific to moving elements
        self.set_ID(MovElemID)
        self.heads = []

        self.set_position(position)
        self.set_vposition(vposition)

        self.set_headToks(headToks)

        #Connect to antecedent
        self.set_antecedent(Antecedent)

        #Set additional attributes
        for key in kwargs:
            self.add_attrib(key, kwargs.get(key, "_"))

    ########################

    def get_ID(self):
        """
        Return integer ID.
        """
        if type(self.ID) == int:
            return self.ID
        else:
            try:
                return int(self.ID)
            except TypeError:
                return None
    
    ########################

    def set_ID(self, MovElemID):
        """
        Set ID. Must be an integer.
        Otherwise None.
        """
        try:
            self.ID = int(MovElemID)
        except:
            self.ID = None

    ########################

    def set_antecedent(self, antecedent):
        """
        Connect to the antecedent.
        """
        self.antec = antecedent

    ########################

    def get_antecedent(self):
        """
        Return the antecedent object (or None).
        """
        return self.antec

    ########################
    
    def set_headToks(self, headToks):
        """
        Set the list of head tokens.
        """
        self.heads = headToks

    ########################

    def get_headToks(self):
        """
        Return the list of head tokens.
        """
        return self.heads

    ########################

    def add_headTok(self, headTok):
        """
        Add a head token.
        """
        self.heads.append(headTok)

    ########################

    def set_position(self, position):
        """
        Set position of the moving element, 
        e.g., insitu, ambig, or extrap.
        """
        self.pos = position

    ########################

    def get_position(self):
        """
        Return position of the moving element,
        e.g., insitu, ambig, or extrap.
        """
        return self.pos

    ########################

    def set_vposition(self, vposition):
        """
        Set position of the verb (for adverbial clauses),
        e.g. V2 or VL.
        """
        self.vpos = vposition

    ########################

    def get_vposition(self):
        """
        Return position of the verb (for adverbial clauses),
        e.g. V2 or VL.
        """
        return self.vpos

    ########################

    @classmethod
    def span_from_BIO_annotation(cls, sentence, annoname="MovElem"):
        """
        Read moving elements from BIO annotations.

        BIO annotations must be attributes of tokens in the sentence.
        Annotations may be complex, i.e., stacked with pipes.

        Example annotations:
        B-NP-insitu
        I-RELC-extrap-2|B-PP-insitu

        Also reads antecedents from the sentence and connects
        them to the respective moving elements.

        Input: Sentence object and attribute name of annotations.
        Output: List of MovElem objects.
        """
        
        #Read Antecedents and store in sentence
        sentence.antecedents = Antecedent().span_from_BIO_annotation(sentence)
        
        #Read MovElems
        spans = []
        span_stack = []

        #For each token
        for tok in sentence.tokens:
            
            #Token not annotated
            if tok.__dict__.get(annoname, "_") == "_":
                #Add previous stack to span list
                if span_stack:
                    spans.append(span_stack[0])
                    span_stack = []
                continue
                                
            #Token is annotated
            #Get list of (stacked) annotation(s)
            annotations = tok.__dict__.get(annoname, "_").strip().split("|")
            
            #Cut stack to length of this token's annotations
            while len(span_stack) > len(annotations):
                span_stack.pop()

            #For each annotation level
            for i, annotation in enumerate(annotations):
                
                #New span
                if annotation.startswith("B-"):
                    
                    #On level one
                    if i == 0 and span_stack:
                        #Move existing spans from stack to span list
                        spans.append(span_stack[0])
                        span_stack = []
                    else:
                        #Cut stack to one level below this annotation
                        while len(span_stack) > i:
                            span_stack.pop()
                    
                    #Get label
                    label = annotation.split("-")[1]

                    #Not an adverbial clause
                    if label != "ADVC":

                        #Does not have a verb position or heads
                        vposition = None
                        heads = []

                        #Get position
                        position = annotation.split("-")[2]

                        #Link to antecedent via ID if applicable
                        try:
                            ID = int(annotation.split("-")[-1])
                            antec = [a for a in sentence.antecedents 
                                     if a.get_MovElemID() == ID]
                            if antec: antec = antec[0]
                            else: antec = None
                        except:
                            ID = None
                            antec = None

                    #Adverbial clause    
                    else:
                        #No position, ID or antecedent
                        position = None
                        ID = None
                        antec = None

                        #Get verb position
                        vposition = annotation.split("-")[2]

                        #Check if this token is ADVC head
                        if "Head" in annotation:
                            heads = [tok]
                        else:
                            heads = []

                    #Create Moving Element
                    #Dominating: create span that will include dominated spans
                    if i < len(annotations)-1:
                        p = MovElem(label, [], position, ID, antec, 
                                    headToks=heads, vposition=vposition)
                    #Non-dominating: include token
                    else:
                        p = MovElem(label, [tok], position, ID, antec, headToks=heads, vposition=vposition)
                    
                    #Tell antecedent who is its MovElem
                    if antec != None:
                        antec.set_MovElem(p)

                    #If there are spans on the stack
                    if span_stack:
                        #Make the last one parent
                        #and this one its child
                        p.set_parent(span_stack[-1])
                        span_stack[-1].append_element(p)
                    
                    #Append to the stack
                    span_stack.append(p)

                #Span continues
                elif annotation.startswith("I-"):
                    #Add token to the last span on the stack
                    if i == len(annotations)-1:
                        span_stack[i].append_element(tok)

                    #If it is a head token, add it to head tokens
                    if "Head" in annotation:
                        span_stack[i].add_headTok(tok)
                        
        #Add sentence final span from stack to list
        if span_stack:
            spans.append(span_stack[0])

        for span in spans:
            span.update_start_index()
            span.update_end_index()
                    
        #Return list of moving elements
        return spans

    #######################

    @classmethod
    def span_to_BIO_annotation(cls, sentence, spanname, annoname):
        """
        Turn MovElem objects into BIO annotations.

        Spans must be included as attribute of the sentence (list of MovElem objects).
        BIO annotations are stored as attribute of the tokens.
        Complex annotations are stacked with pipes.

        Example annotations:
        B-NP-insitu
        I-RELC-extrap-2|B-PP-insitu

        Tokens outside of spans are annotated with '_'.

        Input: Sentence object, name of the spans, attribute name of annotations.
        Output: Modified sentence object.
        """

        ##########################

        def get_bio_spans(span):
            """
            Recursively get span tuples.

            Input: Span object
            Output: List of span tuples 
                    (label, startIndex, endIndex, position, 
                     vposition, ID, headTokens, antecedent)
            """
            spans = []

            #Make sure that indices are correct
            span.update_end_index()
            span.update_start_index()

            #Add tuple of this span
            spans.append((span.get_label(), span.get_start_index(ignore_punct=True), 
                          span.get_end_index(ignore_punct=True), 
                          span.get_position(), span.get_vposition(), span.get_ID(), 
                          span.get_headToks(), span.get_antecedent()))
            
            #For each included span, repeat recursively
            for elem in span.get_elements():
                if isinstance(elem, Span) or issubclass(type(elem), Span):
                    spans.extend(get_bio_spans(elem))
            
            return spans

        ##########################
        
        #Create list with empty annotation for all tokens
        bio_annotations = ["" for _ in sentence.tokens]

        #For each span
        for span in sorted(sentence.__dict__.get(spanname, []), 
                           key=lambda l: (l.get_start_index(), 0-l.get_end_index())):
            
            #Recursively get span tuples
            bio_spans = get_bio_spans(span)
            
            #Add spans to annotation of the respective tokens
            for span in sorted(bio_spans, key=lambda l: (l[1], 0-l[2])):

                #Stack with pipes
                if bio_annotations[span[1]]:
                    bio_annotations[span[1]] += "|"
                
                #First token in span
                #Span is not ADVC
                if span[0] != "ADVC":

                    #Set label (B-Label)
                    bio_annotations[span[1]] += "B-"+span[0]

                    #Add position (B-Label-Position)
                    if span[3]:
                        bio_annotations[span[1]] += "-"+span[3]

                    #Output ID for spans with antecedent 
                    #(B-Label-Position-ID)
                    if span[0] in ["RELC", "CMPP"] and span[5]:
                        bio_annotations[span[1]] += "-"+str(span[5])

                #Span is ADVC
                else:
                    #Set label (B-ADVC)
                    bio_annotations[span[1]] += "B-"+span[0]

                    #Add verb position (B-ADVC-V2 or B-ADVC-VL)
                    if span[4]: bio_annotations[span[1]] += "-"+span[4]

                    #Mark head token
                    if span[6] and span[1] in [int(t.ID)-1 for t in span[6] 
                                               if type(t) == Token]:
                        bio_annotations[span[1]] += "-Head"

                #Rest of span
                for i in range(span[1]+1, span[2]+1):

                    #Stack with pipes
                    if bio_annotations[i]:
                        bio_annotations[i] += "|" 

                    #Add label (I-Label)
                    bio_annotations[i] += "I-"+span[0]

                    #Mark head token(s) for ADVC (I-ADVC-Head)
                    if span[0] == "ADVC" \
                       and i in [int(t.ID)-1 for t in span[6] 
                                 if type(t) == Token]:
                        bio_annotations[i] += "-Head"
           
        #Add _ for tokens outside spans
        for t in range(len(bio_annotations)):
            if not bio_annotations[t]:
                bio_annotations[t] = "_"
        
        #Move annotations from list to token attributes
        for tok, bio in zip(sentence.tokens, bio_annotations):
            tok.__dict__[annoname] = bio
        
        return sentence

##########################

class Antecedent(Span):

    def __init__(self, headTokens = [], label = "Antec", elements = [], 
                 MovElemID = None, parent_span = None, **kwargs):
        """
        Initialize an antecedent as a special type of span.

        An antecedent can have:
        - head token(s)
        - a label (Antec)
        - a list of included elements
        - the ID of the corresponding MovElem
        - a parent span
        - a moving element (as key-word argument 'MovElem')
        - additional attributes (as key-word arguments)
        """
        #Call span constructor
        super().__init__(label, elements, parent_span=parent_span, **kwargs)

        #Set attributes specific to antecedents
        self.heads = []
        self.set_headToks(headTokens)
        self.set_MovElemID(MovElemID)
        self.movElem = self.set_MovElem(kwargs.get("MovElem", None))

        #Set additional attributes
        for key in kwargs:
            self.add_attrib(key, kwargs.get(key, "_"))

    ######################

    def set_headToks(self, headTokens):
        """
        Set the list of head tokens.
        """
        self.heads = headTokens

    ######################

    def get_headToks(self):
        """
        Return the list of head tokens.
        """
        return self.heads

    ######################

    def add_headTok(self, headToken):
        """
        Add a head token.
        """
        self.heads.append(headToken)

    ######################

    def remove_headTok(self, headToken):
        """
        Remove the given head token if it exists.
        Otherwise, do nothing.
        """
        if headToken in self.heads:
            del self.heads[self.heads.index(headToken)]
    
    ######################

    def get_MovElemID(self):
        """
        Return ID of the corresponding moving element.
        """
        return self.movElemID

    ######################

    def set_MovElemID(self, MovElemID):
        """
        Set ID of the corresponding moving element.
        """
        self.movElemID = MovElemID

    ######################

    def get_MovElem(self):
        """
        Return the corresponding moving element (or None).
        """
        return self.movElem

    ######################

    def set_MovElem(self, MovElem):
        """
        Set the corresponding moving element.
        """
        self.movElem = MovElem

    ######################

    def get_distance(self, sentence):
        """
        Return the distance to the moving element 
        in tokens (without punctuation).
        In case of missing MovElem, return None.

        Input: Sentence object.
        Output: Distance (int) or None.
        """
        if self.get_MovElem() == None:
            return None

        #If distance was calculated already, 
        #return it right away.
        if self.__dict__.get("distance", None):
            return self.distance

        #Get end of antecedent and start of MovElem
        a_end = self.get_end_index(ignore_punct=True)
        m_start = self.get_MovElem().get_start_index(ignore_punct=True)
        
        #Collect tokens between antecedent and MovElem
        #that are not tagged as punctuation
        between = [tok for tok in sentence.tokens
                   if int(tok.ID)-1 > a_end
                      and int(tok.ID)-1 < m_start
                      and not tok.XPOS.startswith("$")]

        #Store and return the number of collected tokens
        self.distance = len(between)
        return self.distance

    ######################

    @classmethod
    def span_from_BIO_annotation(cls, sentence, annoname="Antec"):
        """
        Read antecedents from BIO annotations.

        BIO annotations must be attributes of tokens in the sentence.
        Annotations may be complex, i.e., stacked with pipes.

        Example annotations:
        B-Antec-2
        I-Antec-Head|B-Antec-3

        Input: Sentence object and attribute name of annotations.
        Output: List of antecedent objects.
        """

        spans = []
        span_stack = []

        #For each token
        for tok in sentence.tokens:

            #Token not annotated
            if tok.__dict__.get(annoname, "_") == "_":
                #Add previous stack to span list
                while span_stack:
                    spans.append(span_stack.pop())
                continue
                                
            #Token is annotated
            #Get list of (stacked) annotation(s)
            annotations = tok.__dict__.get(annoname, "_").strip().split("|")
            
            #Cut stack to length of this token's annotations
            while len(span_stack) > len(annotations):
                spans.append(span_stack.pop())

            #For each annotation level
            for i, annotation in enumerate(annotations):
                
                #New Antec
                if annotation.startswith("B-"):
                    
                    #Cut stack to one level below this annotation
                    while len(span_stack) > i:
                        spans.append(span_stack.pop())

                    #Head of the antecedent
                    if "Head" in annotation.split("-"):
                        if len(annotation.split("-")) == 3:
                            #B-Antec-Head
                            p = Antecedent(headTokens=[tok], elements=[tok])
                        else:
                            #B-Antec-1-Head
                            p = Antecedent(MovElemID=int(annotation.split("-")[2]), 
                                           headTokens=[tok], elements=[tok])
                    
                    #Not head of the antecedent
                    else:    
                        if len(annotation.split("-")) == 2:
                            #B-Antec
                            p = Antecedent(headTokens=[], elements=[tok])
                        else:
                            #B-Antec-1
                            p = Antecedent(MovElemID=int(annotation.split("-")[2]), 
                                           headTokens=[], elements=[tok])
                    
                    #If there are spans on the stack
                    if span_stack:
                        #Make the last one parent
                        #and this one its child
                        p.set_parent(span_stack[-1])
                        span_stack[-1].append_element(p)

                    #Append to the stack
                    span_stack.append(p)

                #Continued Antec
                elif annotation.startswith("I-"):
                    #Add element to last span on the stack
                    span_stack[i].append_element(tok)

                    #I-Antec-Head
                    if "Head" in annotation:
                        span_stack[i].add_headTok(tok)

        #Add remaining spans from stack to list
        while span_stack:
            spans.append(span_stack.pop())
        
        for span in spans:
            span.update_start_index()
            span.update_end_index()

        #Return list of antecedents
        return spans

    #######################

    @classmethod
    def span_to_BIO_annotation(cls, sentence, spanname, annoname):
        """
        Turn antecedents into BIO annotations.

        Spans must be included as attribute of the sentence (list of antecedent objects).
        BIO annotations are stored as attribute of the tokens.
        Complex annotations are stacked with pipes.

        Example annotations:
        B-Antec-2
        I-Antec-Head|B-Antec-3

        Tokens outside of spans are annotated with '_'.

        Input: Sentence object, name of the spans, attribute name of annotations.
        Output: Modified sentence object.
        """

        ##########################

        def get_bio_spans(span):
            """
            Recursively get span tuples.

            Input: Span object
            Output: List of span tuples 
                    (label, startIndex, endIndex, movElemID, headTokens)
            """
            spans = []

            #Make sure that indices are correct
            span.update_end_index()
            span.update_start_index()

            #Add tuple of this span
            spans.append((span.get_label(), span.get_start_index(), span.get_end_index(), 
                          span.get_MovElemID(), span.get_headToks()))

            #For each included span, repeat recursively
            for elem in span.get_elements():
                if isinstance(elem, Span) or issubclass(type(elem), Span):
                    spans.extend(get_bio_spans(elem))

            return spans

        ##########################

        #Create list with empty annotation for all tokens
        bio_annotations = ["" for _ in sentence.tokens]

        #Recursively get span tuples
        bio_spans = []
        for span in sentence.__dict__.get(spanname, []):
            bio_spans.extend(get_bio_spans(span))
        
        #Add spans to annotation of the respective tokens
        for span in sorted(bio_spans, key=lambda l: (l[1], 0-l[2], l[3])):

            #Stack with pipes
            if bio_annotations[span[1]]:
                bio_annotations[span[1]] += "|"

            #First token of antecedent (B-Antec)
            bio_annotations[span[1]] += "B-"+span[0]

            #Add MovElem ID (B-Antec-ID)
            if span[3]:
                bio_annotations[span[1]] += "-"+str(span[3])

            #Mark head token (B-Antec-ID-Head)
            if span[4] and span[1] in [int(t.ID)-1 for t in span[4] 
                                       if type(t) == Token]:
                bio_annotations[span[1]] += "-Head"

            #Rest of antecedent
            for i in range(span[1]+1, span[2]+1):

                #Stack with pipes
                if bio_annotations[i]:
                    bio_annotations[i] += "|" 
                
                #I-Antec
                bio_annotations[i] += "I-"+span[0]

                #Mark head token(s) (I-Antec-Head)
                if i in [int(t.ID)-1 for t in span[4] if type(t) == Token]:
                    bio_annotations[i] += "-Head"
           
        #Add _ for tokens outside antecedents
        for t in range(len(bio_annotations)):
            if not bio_annotations[t]:
                bio_annotations[t] = "_"
        
        #Move annotations from list to token attributes
        for tok, bio in zip(sentence.tokens, bio_annotations):
            tok.__dict__[annoname] = bio
        
        return sentence

###########################
