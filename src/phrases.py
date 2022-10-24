# -*- coding: utf-8 -*-

import subprocess
from annotations import Span
from C6C.src.document import Tree, Token
from C6C.src.processor import SimplePTBInitializer

#######################

class PhraseParser:
    """
    Class interface for phrase annotation with
    the Berkeley parser and models from Ortmann (2021).
    """

    #Characters that the parser cannot handle
    #even in utf-8 (for some reason)
    CHAR_MAPPING = {
            "(" : "LBR",
            ")" : "RBR",
            "ō" : "o",
            "ā" : "a",
            "ī́" : "i",
            "č" : "c",
            "ꝙ́" : "q",
            "ꝛ" : "r",
            "ď" : "d",
            "ꝰ" : "9",
            "q́" : "q"
        }

    #####################

    def __init__(self, model, modelpath=r"./../models/"):
        """
        Initialize the Berkeley parser with the given model.

        Available models are: news1, news2, mix, hist.
        The parser is invoked in interactive mode in a subprocess.

        Except for the news1 model, this constructor also 
        instantiates a topological field parser 
        to split phrases at field boundaries.
        """
        self.model = model

        #Model trained on TuebaDZ
        if self.model == "news1":
            self.grammar = modelpath + r'constituency_grammars/grammar_tueba_simple.gr'

        #For models trained on Tiger-style corpora
        #also instantiate a topological field parser.
        else:
            from topofields import BerkeleyTopFParser
            self.topf_parser = BerkeleyTopFParser()
            if self.model == "hist":
                self.grammar = modelpath + r'constituency_grammars/grammar_hist_simple.gr'
            elif self.model == "news2":
                self.grammar = modelpath + r'constituency_grammars/grammar_tiger_simple.gr'
            elif self.model == "mix":
                self.grammar = modelpath + r'constituency_grammars/grammar_mix_simple.gr'
            else:
                print("Error: Unknown model", model)

        #Command for calling the parser
        self.command = ['java', \
                        '-Xmx10g', \
                        '-jar', './berkeleyparser/BerkeleyParser-1.7.jar', \
                        '-gr', self.grammar,
                        '-maxLength', '350',
                        '-useGoldPOS']

        #Start the subprocess
        self.restart_shell()

        #Initialize a processor to create full-fledged
        #trees from the parser output in PTB style.
        self.ptb_initializer = SimplePTBInitializer()

    ################################

    def restart_shell(self):
        """
        Start a subprocess for calling the Java-based parser.
        The process is stored in the parser object.
        """
        self.process = subprocess.Popen(self.command, #cwd="./berkeleyparser/",
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                                   universal_newlines=True, bufsize=0, encoding="utf-8")

    ###############################

    def parse(self, sentence, corpus, form="FORM"):
        """
        Apply the constituency parser to a given sentence.

        Takes the word forms and gold POS tags of a given sentence 
        and feeds them to the parser (in the open subprocess).
        The output tree is then read from the process.

        If the corpus is 'ReF.UP' or 'Mercurius', additional punctuation 
        with tags "$MK", "$MSBI", "$QL", "$QR" is filtered out before parsing.

        If a normalized word form should be used as input,
        this can be specified with 'form'. Per default, the 'FORM' value is used.

        The tree is stored as 'tree' argument in the sentence object.
        In addition a string version of the same tree is stored as 'PTBstring'.

        Input: Sentence object, corpus name, attribute name of word form
        Output: Sentence object
        """

        #Create
        #1) data list with tuples of (mapped word form, mapped POS tag)
        #2) ascii data list with the same tuples 
        #   but words are replaced by 'wID' dummy tokens
        #3) token dictionary to map output that is based on 2) 
        #   back to token forms
        #Replace characters that the parser cannot handle (even in utf-8).
        #Replace POS tags of punctuation to match the tags of the parser models.
        #For historical corpora, also remove additional punctuation
        #and turn sentence final comma tags into full stops.
        if corpus in ["ReF.UP", "Mercurius"]:
            data = []
            for tok in sentence.tokens:
                if not tok.POS in ["$MK", "$MSBI", "$QL", "$QR"]:
                    mapped_form = tok.__dict__[form]
                    for char, repl in self.CHAR_MAPPING.items():
                        mapped_form = mapped_form.replace(char, repl)
                    data.append((mapped_form, 
                                 tok.XPOS.replace("$.", "PUNKT").replace("$,", "KOMMA").replace("$(", "KLAMMER")))
            ascii_data = [("w"+tok.ID, 
                           tok.XPOS.replace("$.", "PUNKT").replace("$,", "KOMMA").replace("$(", "KLAMMER"))
                          for tok in sentence.tokens 
                              if not tok.POS in ["$MK", "$MSBI", "$QL", "$QR"]]
            tokens = {int(tok.ID) : tok.__dict__[form].replace("(", "LBR").replace(")", "RBR") 
                      for tok in sentence.tokens 
                          if not tok.POS in ["$MK", "$MSBI", "$QL", "$QR"]}
            if data[-1][1] == "KOMMA":
                data[-1] = (data[-1][0], "PUNKT")
            if ascii_data[-1][1] == "KOMMA":
                ascii_data[-1] = (ascii_data[-1][0], "PUNKT")
        else:
            data = []
            for tok in sentence.tokens:
                mapped_form = tok.__dict__[form]
                for char, repl in self.CHAR_MAPPING.items():
                    mapped_form = mapped_form.replace(char, repl)
                data.append((mapped_form, 
                             tok.XPOS.replace("$.", "PUNKT").replace("$,", "KOMMA").replace("$(", "KLAMMER")))
            ascii_data = [("w"+tok.ID, 
                           tok.XPOS.replace("$.", "PUNKT").replace("$,", "KOMMA").replace("$(", "KLAMMER"))
                    for tok in sentence.tokens]
            tokens = {int(tok.ID) : tok.__dict__[form].replace("(", "LBR").replace(")", "RBR") 
                      for tok in sentence.tokens}
        
        if len(data) > 350:
            print("WARNING: Skipping sentence with", len(data), "tokens.")
            sentence.__dict__["PTBstring"] = ""
            sentence.__dict__["tree"] = None
            return sentence

        #Write the word-POS tuples to the subprocess
        try:
            for tup in data:
                self.process.stdin.write(tup[0] + "\t" + tup[1] + "\n")
            self.process.stdin.write("\n")
            self.process.stdin.flush()

            #Read the result from the subprocess
            self.process.stdout.flush()
            out = self.process.stdout.readline()

        #If the parser could not handle the input despite mapping
        #re-try with dummy tokens
        except UnicodeDecodeError:
            print("UnicodeDecodeError in sentence", sentence.sent_id)
            for tup in ascii_data:
                self.process.stdin.write(tup[0] + "\t" + tup[1] + "\n")
            self.process.stdin.write("\n")
            self.process.stdin.flush()

            self.process.stdout.flush()
            out = self.process.stdout.readline()

            #Map dummy tokens back to words
            for wid, form in sorted(tokens.items(), reverse=True):
                out = out.replace("w"+str(wid), form)

        #Add missing VROOT node (but only one!)
        out = out.strip().replace("( ", "(VROOT ")     
        while out.startswith("(VROOT (VROOT"):
            out = out[7:-1] 
        
        #Remove extra whitespace
        out = out.replace(" (", "(").replace(" )", ")")
        
        #Reconstruct tree
        try:
            tree = Tree.from_PTB_string(out)
            if tree is None:
                raise ValueError

            #Store tree object and string version in sentence
            sentence.__dict__["PTBstring"] = out
            sentence.__dict__["tree"] = tree
            SimplePTBInitializer().process_sentence(sentence, 
                                                    "tree", "PTBstring", 
                                                    form=form)
            
        except:
            print("No valid tree for sentence", sentence.sent_id)
            try:
                print(out)
            except:
                pass
            sentence.__dict__["PTBstring"] = "(VROOT)"
            sentence.__dict__["tree"] = None
            self.restart_shell()     

        return sentence

    #####################

    def get_top_level_phrases(self, sent, annoname="PHRASE"):
        """
        Read phrases as defined in Ortmann (2021b) from
        nested phrase annotations as output by the parser.

        For example, I-NP|B-PP is turned into I-NP.
        Also removes VP annotations.

        Tokens outside of phrases are labeled 'O'.

        Input: Sentence, attribute name of phrase annotation
        Output: Sentence object
        """
        for tok in sent.tokens:
            phrase = tok.__dict__.get(annoname, "_")
            if phrase != "_":
                phrase = phrase.split("|")[0]
                if phrase in ["B-VP", "I-VP"]:
                    tok.__dict__[annoname] = "O"
                else:
                    tok.__dict__[annoname] = phrase
            else:
                tok.__dict__[annoname] = "O"
        return sent

    #####################

    def read_phrases_from_parse(self, sent, **kwargs):
        """
        Identify phrases in constituency trees.

        The constituency tree is expected to be stored in the 'tree'
        attribute of the given sentence. The result is stored as
        'phrases' attribute.

        For Tiger-style trees, the topological field parser is used
        to split phrases at field boundaries.

        Input: Parsed sentence object and additional key-word args
               (e.g. 'corpus')
        Output: Sentence object with phrase list
        """
        
        #Read phrases from tree (depending on parser model)
        #For Tueba-style trees, simply get the phrases
        if self.model == "news1":
            sent.phrases = Span.read_phrases_from_simplified_tueba(sent)
        
        #For Tiger-style trees
        else:
            sent.phrases = Span.read_phrases_from_simplified_tiger(sent)
            
            #Annotate topological fields if not already done
            if not sent.__dict__.get("TopFTree", None):
                if not sent.__dict__.get("TopFString", ""):
                    self.topf_parser.parse(sent, kwargs.get("corpus", None))
                else:
                    sent.TopFTree = Tree.from_PTB_string(sent.TopFString)
                    sent = SimplePTBInitializer().process_sentence(sent, 
                                                                   "TopFTree", 
                                                                   "TopFString")

            #Split phrases at field boundaries
            if any(tok.XPOS.startswith("V") for tok in sent.tokens):
                sent.phrases = PhraseParser.split_phrases_at_field_boundaries(sent.phrases, 
                                                                              sent.TopFTree)

        return sent

    #####################

    def get_phrases(self, sent, **kwargs):
        """
        Parse the input sentence to identify phrases.

        Applies the constituency parser to the given sentence.
        Then, reads phrases from the output tree.

        If a normalized word form should be used as input,
        this can be specified as key-word argument 'norm'.
        Per default, the 'FORM' value is used.

        Input: Sentence object and additional key-word args
               (e.g., 'corpus', 'norm')
        Output: Parsed sentence with phrase annotation
        """
        
        #Parse sentence
        self.parse(sent, kwargs.get("corpus", None), kwargs.get("norm", "FORM"))
        
        #Sentences without tree don't get phrases
        if not sent.tree:
            sent.phrases = []
            return sent

        #Reconnect parse with tokens
        self.ptb_initializer.process_sentence(sent, "tree", "PTBstring")
        
        #Read phrases from tree
        sent = self.read_phrases_from_parse(sent, **kwargs)

        return sent

    #####################

    def annotate(self, doc, **kwargs):
        """
        Annotate the document with phrases.

        The annotation result is stored twice:
        1) as (nested) phrase span objects in the sentence
        2) as top-level phrases in BIO format in the tokens.

        If a normalized word form should be used as input,
        this can be specified as key-word argument 'norm'.
        Per default, the 'FORM' value is used.

        Tokens outside of phrases are labeled 'O'.

        Input: Doc object
        Output: Annotated doc object
        """

        for sent in doc.sentences:

            #Clear existing annotations
            for tok in sent.tokens:
                tok.PHRASE = "O"

            #Get phrases
            sent = self.get_phrases(sent, **kwargs)

            #Transform to BIO annotation
            sent = Span.span_to_BIO_annotation(sent, "phrases", "PHRASE")
            
            #Top-level phrases only
            sent = self.get_top_level_phrases(sent)

        return doc

    ###########################
    
    @staticmethod
    def split_phrases_at_field_boundaries(phrases, topftree):
        """
        Split phrases at topological field boundaries.

        Takes a list of input phrases and a topological field tree
        and separates phrases at field boundaries.

        Input: List of phrases and topological field tree.
        Output: Corrected list of phrases.
        """
        
        ######################

        def find_lowest_parent(node, tree):
            """
            Return the lowest possible parent of node in tree.
            """
            parent = None
            for n in tree.nodes():
                #Possible parent
                if n.get_start_index(ignore_punct=True) <= node.get_start_index(ignore_punct=True) \
                    and n.get_end_index(ignore_punct=True) >= node.get_end_index(ignore_punct=True):
                    #If non-terminal
                    if n.is_non_terminal():
                        #Recursively continue
                        possible_parent = find_lowest_parent(node, n)
                        #If a child is returned, make it the parent
                        if possible_parent != None:
                            parent = possible_parent
                        #Otherwise, this node is the parent
                        else:
                            parent = n
                        break
                    #Terminals can't be parents
                    else:
                        continue
                #Boundaries don't match
                else:
                    continue
            #No parent was found
            if parent == None:
                #If tree can be parent, return tree
                if tree.get_start_index(ignore_punct=True) <= node.get_start_index(ignore_punct=True) \
                    and tree.get_end_index(ignore_punct=True) >= node.get_end_index(ignore_punct=True):
                    return tree
            
            return parent

        ######################

        def crosses_field_boundary(phrase, topftree):
            """
            Check if phrase crosses a field boundary in topftree.
            If not, return False or None.
            Otherwise, output list of non-terminal nodes that 
            cross the phrase boundaries.
            """
            #Skip phrases without start index
            #e.g. when they only contain punctuation
            if phrase.get_start_index(ignore_punct=True) == None:
                print("no start index", str(phrase))
                return False

            #Find lowest possible parent in the tree
            parent = find_lowest_parent(phrase, topftree)

            #No parent found
            if parent == None:
                return None

            #No terminal within phrase
            elif not any(c.is_terminal() and not c.simple_cat in ["PUNKT", "KOMMA", "KLAMMER"]
                        and c.get_start_index(ignore_punct=True) >= phrase.get_start_index(ignore_punct=True)
                        and c.get_end_index(ignore_punct=True) <= phrase.get_end_index(ignore_punct=True)
                        for c in parent.nodes()):
                return None

            #Parent contains non-terminals
            elif any(c.is_non_terminal() for c in parent.nodes()):
                non_terminals = [c for c in parent.nodes() if c.is_non_terminal()]
                fitting_non_terminals = [nt for nt in non_terminals 
                                        if nt.get_end_index(ignore_punct=True) < phrase.get_start_index(ignore_punct=True)
                                            or nt.get_start_index(ignore_punct=True) > phrase.get_end_index(ignore_punct=True)
                                            or (nt.get_start_index(ignore_punct=True) >= phrase.get_start_index(ignore_punct=True) 
                                                and nt.get_end_index(ignore_punct=True) <= phrase.get_end_index(ignore_punct=True))]
                #All non-terminals are either outside or inside of phrase
                if len(non_terminals) == len(fitting_non_terminals):
                    return False
                #A non-terminal crosses the phrase boundary
                else:
                    return [nt for nt in non_terminals if not nt in fitting_non_terminals]
            
            #All is fine
            else:
                return False

        ######################

        #For each (top-level) phrase
        p = 0
        while p < len(phrases):
            phrase = phrases[p]
            
            #Skip irrelevant phrases
            if not phrase.get_label() in ["NP", "PP", "AP", "ADVP"]:
                del phrases[p]
                continue

            #Check if it crosses field boundary
            across_fields = crosses_field_boundary(phrase, topftree)

            #If it doesn't: continue
            if across_fields == False:
                p += 1
                continue

            #Otherwise
            #If no parent or no terminal was found
            elif across_fields == None:
                
                #Build sub-phrases
                subphrases = []
                new_phrase = None
                for child in phrase.get_elements():
                    #Phrasal children are sub-phrases
                    if type(child) == Span:
                        if new_phrase != None:
                            subphrases.append(new_phrase)
                            new_phrase = None
                        #But ignore VPs
                        if child.get_label() in ["NP", "PP", "AP", "ADVP"]:
                            subphrases.append(child)
                    #Token children
                    elif type(child) == Token:
                        #If there is a consecutive phrase
                        #add to new phrase of same type as phrase
                        if new_phrase != None \
                            and not(child.XPOS.startswith("V") 
                                    or child.XPOS in ["ITJ","KOUS", "KON", "KOUI", 
                                                      "PWAV", "PTKANT", "PTKVZ", "PTKZU"]):
                            new_phrase.append_element(child)
                        #Otherwise skip punctuation and everything that
                        #is not part of NPs, PPs, APs, or ADVPs
                        elif child.XPOS.startswith("$") or child.XPOS.startswith("V") \
                            or child.XPOS in ["ITJ","KOUS", "KON", "KOUI", 
                                              "PWAV", "PTKANT", "PTKVZ", "PTKZU"]:
                            continue
                        #Build new phrase of same type
                        else:
                            new_phrase = Span(phrase.get_label(), elements=[child])                    
                if new_phrase != None:
                    subphrases.append(new_phrase)
                
                #Re-try with subphrases  
                if subphrases:
                    if len(subphrases) > 1 \
                    or subphrases[0].get_label() != phrase.get_label() \
                    or len(subphrases[0].get_elements()) != len(phrase.get_elements()):
                        subphrases = PhraseParser.split_phrases_at_field_boundaries(subphrases, topftree)

                #If successful: replace phrase with corrected sub-phrases
                if subphrases:
                    phrases[p:p+1] = subphrases

                    #Increase p to continue after sub-phrases
                    p += len(subphrases)
                
                #Otherwise remove the phrase
                else:
                    del phrases[p]

            #If field(s) cross(es) phrase boundary
            #Split at end of first field and re-try
            elif type(across_fields) == list:
                
                #Get end index of first crossing field
                split_at = across_fields[0].get_end_index(ignore_punct=True)

                #If end index is outside of phrase
                if split_at > phrase.get_end_index(ignore_punct=True):
                    #Get start index of first crossing field
                    split_at = across_fields[0].get_start_index(ignore_punct=True)

                    #Split at start index
                    part1 = [c for c in phrase.get_elements() 
                             if type(c) == Span and c.get_end_index() < split_at 
                                or type(c) == Token and int(c.ID)-1 < split_at]
                    part2 = [c for c in phrase.get_elements() 
                             if type(c) == Span and c.get_start_index() >= split_at
                                or type(c) == Token and int(c.ID)-1 >= split_at]
                else:
                    #Split at end index
                    part1 = [c for c in phrase.get_elements() 
                             if type(c) == Span and c.get_end_index() <= split_at 
                                or type(c) == Token and int(c.ID)-1 <= split_at]
                    part2 = [c for c in phrase.get_elements() 
                             if type(c) == Span and c.get_start_index() > split_at
                                or type(c) == Token and int(c.ID)-1 > split_at]
                
                #Build sub-phrases
                subphrases = []

                #Make sub-phrases from both parts
                for part in (part1, part2):
                    new_phrase = None
                    for child in part:
                        #Phrasal children are sub-phrases
                        if type(child) == Span:
                            if new_phrase:
                                subphrases.append(new_phrase)
                                new_phrase = None
                            #But ignore VPs
                            if child.get_label() in ["NP", "PP", "AP", "ADVP"]:
                                subphrases.append(child)
                        elif type(child) == Token:
                            #If there is a consecutive phrase
                            #add to new phrase of same type as phrase
                            if new_phrase != None \
                                and not(child.XPOS.startswith("V") 
                                        or child.XPOS in ["ITJ","KOUS", "KON", "KOUI", 
                                                          "PWAV", "PTKANT", "PTKVZ", "PTKZU"]):
                                new_phrase.append_element(child)
                            #Otherwise skip punctuation and everything that
                            #is not part of NPs, PPs, APs, or ADVPs
                            elif child.XPOS.startswith("$") or child.XPOS.startswith("V") \
                                or child.XPOS in ["ITJ","KOUS", "KON", "KOUI", 
                                                  "PWAV", "PTKANT", "PTKVZ", "PTKZU"]:
                                continue
                            #Build new phrase of same type
                            else:
                                new_phrase = Span(phrase.get_label(), elements=[child])                    
                    if new_phrase != None:
                        subphrases.append(new_phrase)

                #Re-try with subphrases  
                if subphrases:
                    if len(subphrases) > 1 \
                    or subphrases[0].get_label() != phrase.get_label() \
                    or len(subphrases[0].get_elements()) != len(phrase.get_elements()):
                        subphrases = PhraseParser.split_phrases_at_field_boundaries(subphrases, topftree)
                
                #If successful: replace phrase with corrected sub-phrases
                if subphrases:
                    phrases[p:p+1] = subphrases
                
                    #Increase p to continue after sub-phrases
                    p += len(subphrases)
                
                #Otherwise remove phrase
                else:
                    del phrases[p]
                
        return phrases
    
##########################

def initialize(model, **kwargs):
    """
    Instantiates the phrase parser with the given model.

    Possible model names are news1, news2, mix, and hist.
    If the model is unknown, returns None.

    Input: Model name
    Output: Parser object or None
    """
    if model in ["hist", "news1", "news2", "mix"]:
        myParser = PhraseParser(model)
    else:
        return None
    return myParser

##############################

