'''
Created on 14.10.2019

@author: Katrin Ortmann
'''

############################

class Token:

    def __init__(self, **kwargs):
        for key in kwargs:
            self.add_value(key, kwargs.get(key, "_"))

    ####################

    def __str__(self):
        try:
            return self.FORM
        except:
            return ""

    ####################

    def add_value(self, key, val):
        self.__dict__[key] = val
    
    #############################
    
    def __repr__(self):
        """
        Return the token as string.
        """
        return self.FORM
    
    #############################
    
    def __str__(self):
        """
        Return the token as string.
        """
        return self.FORM
    
    #############################
    
    def __len__(self):
        """
        Return the number of characters.
        """
        return len(self.FORM)
    
    ####################

    def is_punctuation(self):
        """
        If word is tagged as XPOS = $. or $, or $( or if UPOS is PUNCT return True.
        Return False otherwise.
        """
        if self.__dict__.get("XPOS") in ["$.", "$,", "$("]:
            return True
        elif self.__dict__.get("UPOS") == "PUNCT":
            return True
        else:
            return False

############################

class Sentence:

    def __init__(self, tokens=[], **kwargs):
        self.n_toks = 0
        self.tokens = list()
        if tokens:
            for tok in tokens:
                self.add_token(tok)
        for key,val in kwargs.items():
            self.__dict__[key] = val

    #######################

    def __len__(self):
        """
        Return the number of tokens.
        """
        return len(self.tokens)
    
    #######################

    def __iter__(self):
        """
        Return the token objects.
        """
        for tok in self.tokens:
            yield tok
    
    #######################

    def __repr__(self):
        """
        Return the strings of the tokens, joined by spaces.
        """
        return " ".join([str(tok) for tok in self.tokens])

    ##########################

    def __str__(self):
        return " ".join(str(tok) for tok in self.tokens)

    #######################

    def add_token(self, token):
        self.n_toks += 1
        token.INDEX = self.n_toks-1
        if token.__dict__.get("ID", None) in ("_", None):
            token.ID = str(self.n_toks)

        self.tokens.append(token)

############################

class Doc(object):

    def __init__(self, filename, sentences = [], **kwargs):

        self.filename = filename

        for key,val in kwargs.items():
            self.__dict__[key] = val
        
        self.n_sents = 0
        
        self.sentences = []
        if sentences:
            for sent in sentences:
                self.add_sent(sent)
                
    ###################

    def __iter__(self):
        for sentence in self.sentences:
            yield sentence

    ####################

    def __str__(self):
        return "\n".join([str(sent) for sent in self.sentences])

    #######################

    def add_sent(self, sentence):
        self.n_sents += 1

        if sentence.__dict__.get("sent_id", None) in ("_", None):
            sentence.sent_id = str(self.n_sents)

        self.sentences.append(sentence)

########################

class Corpus(object):

    def __init__(self, files = [], **kwargs):

        for key,val in kwargs.items():
            self.__dict__[key] = val

        self.n_files = 0

        self.files = []
        if files:
            for f in files:
                self.add_file(f)

    ###################

    def __iter__(self):
        for file in self.files:
            yield file

    #######################

    def add_file(self, doc):
        self.n_files += 1
        self.files.append(doc)

########################