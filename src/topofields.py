# -*- coding: utf-8 -*-

import os
import subprocess
from C6C.src.document import Tree
from phrases import PhraseParser
from annotations import Span

#############################

class BerkeleyTopFParser:
    """
    Class interface for topological field annotation
    with the Berkeley parser and models from Ortmann (2020).
    """
    
    def __init__(self, model="topfpunct", modelpath = r"./../models/"):
        """
        Initialize the topological field parser with a given model.

        Default is the 'topfpunct' model, which is trained on 
        a modified version of the TuebaDZ corpus with POS as input text
        and punctuation included.
        All possible models are: 
        - 'topfpunct' (default)
        - 'topfnopunct' (with excluded punctuation)
        - 'news1' (complete constituency parser with topofields)

        The constructor starts a subprocess that calls the Java-based parser.
        """
        
        self.model = model

        #Allow for using the constituency model trained on
        #TuebaDZ which also includes topofield annotations
        if model == "news1":
            self.myParser = PhraseParser(model)
        
        else:
            #Select the grammar (with/without punctuation)
            if model == "topfpunct":
                self.grammar = os.path.join(modelpath, 'topfgrammars/topfgrammar_punct.gr')
            elif model == "topfnopunct":
                self.grammar = os.path.join(modelpath, 'topfgrammars/topfgrammar_nopunct.gr')
            else:
                print("Error: Unknown topological field parser model", model)

            #Start a subprocess with the following command to call the parser
            self.command = ['java', \
                            '-Xmx10g', \
                            '-jar', './berkeleyparser/BerkeleyParser-1.7.jar', \
                            '-gr', self.grammar,
                            '-maxLength', '350']
            self.restart_shell()

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

    def parse(self, sentence, corpus):
        """
        Apply the topological field parser to a given sentence.

        Takes the POS tags of a given sentence and feeds them to the parser
        (in the open subprocess). The output tree is then read from the process
        and tokens are reinserted in place of the POS tags.

        If the corpus is 'ReF.UP', additional punctuation 
        with tags "$MK", "$MSBI", "$QL", "$QR" is filtered out before parsing.

        The topofield tree is stored as 'TopFTree' argument in the sentence object.
        In addition a string version of the same tree is stored as 'TopFString'.

        Input: Sentence object, corpus name
        Output: Sentence object
        """

        #Replace POS tags of punctuation and pronominal adverbs
        #to match the tags of the topofield models.
        #For ReF.UP corpus, also remove additional punctuation.
        if corpus == "ReF.UP":
            data = [(tok, tok.XPOS.replace("$.", "PUNCT").replace("$,", "COMMA").replace("$(", "KLAMMER").replace("PROAV", "PAV").replace("PROP", "PAV"))
                    for i, tok in enumerate(sentence.tokens) 
                    if not (tok.XPOS in ["$.", "$,", "$("] 
                            and i < len(sentence.tokens)-1 
                            and sentence.tokens[i+1].POS in ["$MK", "$MSBI", "$QL", "$QR"])]
        else:
            data = [(tok, tok.XPOS.replace("$.", "PUNCT").replace("$,", "COMMA").replace("$(", "KLAMMER").replace("PROAV", "PAV").replace("PROP", "PAV"))
                    for tok in sentence.tokens]

        #Do not parse very long sentences
        if len(data) > 350:
            print("WARNING: Skipping sentence with", len(data), "tokens.")
            sentence.__dict__["TopFString"] = ""
            sentence.__dict__["TopFTree"] = None
            return sentence

        #Send POS sequence to the parser
        self.process.stdin.write(" ".join([t[1] for t in data])+"\n")
        self.process.stdin.flush()

        #Read result tree from subprocess
        self.process.stdout.flush()
        out = self.process.stdout.readline()
        
        #Add missing S node (but only one!)
        out = out.strip().replace("( ", "(S ")     
        while out.startswith("(S (S"):
            out = out[3:-1] 

        #Remove extra whitespace
        out = out.replace(" (", "(").replace(" )", ")")
        
        #Reconstruct tree object from the string
        tree = Tree.from_topf_string(out)
        if tree is None:
            raise ValueError

        #Reinsert tokens into the tree
        for tok,terminal in zip([t[0] for t in data], tree.terminals()):
            terminal.token = tok
            terminal.ID = tok.ID

        #Store tree and its string version as sentence attributes
        sentence.__dict__["TopFString"] = tree.to_string(include_gf=False)
        sentence.__dict__["TopFTree"] = tree

        return sentence

    #########################

    def annotate(self, doc, **kwargs):
        """
        Annotates the given document with topological fields.

        Each sentence is parsed with the topological field parser
        (or a constituency parser, if the model is 'news1').
        The resulting tree is stored in the 'TopFTree' attribute of
        each sentence and the field annotation in the TOPF attribute of 
        each token (in BIO format).

        Per default, the tagset is mapped to the simple tagset from Ortmann (2020)
        with seven tags: 'KOORD', 'LV', 'VF', 'LK', 'MF', 'RK', 'NF'.
        If the original tagset of the parser should be preserved,
        a key-word argument 'tagset' with value 'orig' must be given.

        The kwargs dictionary can also specify the corpus. Currently,
        this only affects the handling of punctuation in the ReF.UP corpus.

        Input: Doc object
        Output: Doc object
        """

        #Get corpus name
        corpus = kwargs.get("corpus", None)
        
        for sent in doc.sentences:

            #Clear existing annotations
            for tok in sent.tokens:
                tok.TOPF = "O"

            #Parse sentence
            if self.model == "news1":
                #With constituency parser
                self.myParser.parse(sent, corpus)
                #And read topofield field tree from constituency tree
                self.topftree_from_parsetree(sent)
            else:
                #Or use the genuine topological field parser
                self.parse(sent, corpus)

            #Transform the tree to BIO annotations
            if sent.TopFTree:
                sent = Span.tree_to_BIO_annotation(sent, "TopFTree", "TOPF")

            #Map tagsets
            if kwargs.get("tagset", None) == "orig":
                continue
            else:
                sent = self.map_tagsets(sent, "TOPF")
            
        return doc

    #########################

    @staticmethod
    def map_tagsets(sentence, annoname="TOPF"):
        """
        Map topological field annotations to the simple tagset from Ortmann (2020)
        with seven tags: 'KOORD', 'LV', 'VF', 'LK', 'MF', 'RK', 'NF'.        

        Mapping rules:
        C -> LK
        VC, VCE -> RK
        MFE -> MF
        PARORD -> KOORD
        FKOORD is KOORD for KON tokens on level 1 (remove otherwise)
        Remove FKONJ
        Keep other labels
        Outside of fields, assign 'O'

        Input: Sentence object and name of topofield attribute (default: TOPF)
        Output: Sentence object
        """
        
        for tok in sentence.tokens:
            #Split multi-level fields
            if tok.__dict__.get(annoname, None) != None:
                annotations = [[anno.split("-")[0], anno.split("-")[-1]] 
                               for anno in tok.__dict__[annoname].split("|")]
            else:
                return sentence
            
            #For each level
            for i in range(len(annotations)):
                label = annotations[i][-1]
                #Outside of fields, assign 'O'
                if not label or label in ["_", "O"]:
                    annotations[i] = "O"
                #C -> LK
                elif label == "C":
                    annotations[i][-1] = "LK"
                #VC, VCE -> RK
                elif label in ["VC", "VCE"]:
                    annotations[i][-1] = "RK"
                #MFE -> MF
                elif label == "MFE":
                    annotations[i][-1] = "MF"
                #FKOORD is KOORD for KON tokens on level 1
                #Otherwise: remove
                elif label == "FKOORD":
                    if tok.XPOS == "KON" and not len(annotations) > i+1:
                        annotations[i][-1] = "KOORD"
                        annotations[i][0] = "B"
                    elif len(annotations) == 1:
                        annotations[i] = "O"
                    else:
                        annotations[i] = "O"
                #Remove FKONJ
                elif label == "FKONJ":
                    annotations[i] = "O"
                #PARORD -> KOORD
                elif label == "PARORD":
                    annotations[i][-1] = "KOORD"
                    annotations[i][0] = "B"
                #Keep all other labels
                else:
                    annotations[i][-1] = label

            #Re-stack the annotations and remove stacked O's
            tok.__dict__[annoname] = "|".join(["-".join(anno) for anno in annotations])
            while "O|" in tok.__dict__[annoname]:
                tok.__dict__[annoname] = tok.__dict__[annoname].replace("O|", "")
            while "|O" in tok.__dict__[annoname]:
                tok.__dict__[annoname] = tok.__dict__[annoname].replace("|O", "")

        return sentence

    #########################
    
    @staticmethod
    def topftree_from_parsetree(sentence, treename="tree", topfname="TopFTree"):
        """
        Read a topological field tree from a constituency tree.

        Takes a constituency tree that includes topological field annotations
        and creates a new tree containing only the topological fields and tokens.

        The following fields are moved over to the new tree:
        "LV", "C", "FKOORD", "KOORD", "LK", "MF", "MFE", "NF", 
        "PARORD", "VC", "VCE", "VF", "FKONJ", "RK"

        Input:
        - Parsed sentence object
        - Name of the constituency tree attribute (default: 'tree')
        - Name of the topofield tree attribute (default: 'TopFTree')

        Output: Sentence object
        """

        #The following labels correspond to fields
        FIELDS = ["LV", "C", "FKOORD", "KOORD", "LK", "MF", "MFE", "NF", 
                  "PARORD", "VC", "VCE", "VF", "FKONJ", "RK"]

        #Get the constituency tree
        tree = sentence.__dict__.get(treename, None)
        if tree == None:
            sentence.__dict__[topfname] = None
            return sentence

        ###############################

        def create_tree(node, tree_node):
            """
            Recursively create a new topofield tree 
            from the given constituency tree node. 
            """
            for n in node.nodes():
                if n.is_terminal():
                    tree_node.add_child(n)
                else:
                    if n.cat() in FIELDS:
                        new_node = Tree(n.ID, n.cat(), n.label(), 
                                        parent=tree_node, **{"simple_cat": n.cat()})
                        tree_node.add_child(new_node)
                        create_tree(n, new_node)
                    else:
                        create_tree(n, tree_node)
            
        ###############################
        
        #Initialize a new tree
        topftree = Tree(tree.ID, tree.cat(), tree.label(), **{"simple_cat": tree.cat()})

        #Recursively move field nodes from the constituency tree
        #to the new topofield tree
        for node in tree.nodes():
            create_tree(node, topftree)

        #Store the new tree and its string version in the sentence
        sentence.__dict__["TopFTree"] = topftree
        sentence.__dict__["TopFString"] = topftree.to_string(include_gf=False)

        #Add S node if necessary
        if sentence.TopFString.startswith("(("):
            sentence.TopFString = "(S" + sentence.TopFString[1:]
        
        return sentence

################################

def initialize(model, **kwargs):
    """
    Instantiates the topological field parser with the given model.

    Possible model names are 'topfpunct', 'topfnopunct', 'news1'.
    If the model is unknown, the default model ('topfpunct') will be used.

    Input: Model name
    Output: Parser object
    """
    if model in ["topfpunct", "topfnopunct", "news1"]:
        myParser = BerkeleyTopFParser(model)
    else:
        myParser = BerkeleyTopFParser()
    return myParser

################################