# -*- coding: utf-8 -*-

import os
from ncrfpp.main import chunk, load_data_model
from annotations import Span

#######################

class NCRFppChunker:
    """
    Class interface for chunking with NCRF++
    and models from Ortmann (2021a).
    """

    def __init__(self, model, modelpath = r"./../models/"):
        """
        Initialize the chunker with the given model.

        Possible models are: news1, news2, mix, hist.
        All models include POS tags as features and were
        trained with pre-trained word-embeddings.

        Input: Model name
        """

        self.model = model
        if model == "hist":
            self.dset_dir = os.path.join(modelpath, "ncrfpp", "lstmcrf_hist_pos_pre-trained.dset")
            self.load_model_dir = os.path.join(modelpath, "ncrfpp", "lstmcrf_hist_pos_pre-trained.0.model")
        elif model == "news1":
            self.dset_dir = os.path.join(modelpath, "ncrfpp", "lstmcrf_tueba_pos_pre-trained.dset")
            self.load_model_dir = os.path.join(modelpath, "ncrfpp", "lstmcrf_tueba_pos_pre-trained.0.model")
        elif model == "news2":
            self.dset_dir = os.path.join(modelpath, "ncrfpp", "lstmcrf_tiger_pos_pre-trained.dset")
            self.load_model_dir = os.path.join(modelpath, "ncrfpp", "lstmcrf_tiger_pos_pre-trained.0.model")
        elif model == "mix":
            self.dset_dir = os.path.join(modelpath, "ncrfpp", "lstmcrf_tigerxml_pos_pre-trained.dset")
            self.load_model_dir = os.path.join(modelpath, "ncrfpp", "lstmcrf_tigerxml_pos_pre-trained.0.model")
        else:
            print("ERROR: Unknown chunker model", model)
        
        #Write config to tmp file
        self.tmp_dir = "./ncrfpp/tmp"
        if not os.path.isdir(self.tmp_dir):
            os.makedirs(self.tmp_dir)
        self.write_tmp_config()

        #Load data and model with NCRF++
        self.data, self.model = load_data_model()

    #################

    def write_tmp_data(self, doc, form="FORM"):
        """
        Writes the given doc object to a temporary file
        as input for the chunker.

        Input: Doc object and token attribute that should be used as word form.
        """

        #Create a tmp file
        tmp_file = open(os.path.join(self.tmp_dir, "raw.bio"), mode="w", encoding="utf-8")

        #Write sentences to file
        #FORM [POS]XPOS O
        for sent in doc.sentences:
            for tok in sent.tokens:
                tok.CHUNK = "O"
                print(tok.__dict__[form], "[POS]"+tok.XPOS, "O", file=tmp_file)
            print(file=tmp_file)
        tmp_file.close()

    #################

    def write_tmp_config(self):
        """
        Write settings for the chunker to a temporary config file.
        """

        #Create tmp file
        tmp_file = open(os.path.join(self.tmp_dir, "decode.config"), 
                        mode="w", encoding="utf-8")

        #Print settings
        print("status=decode", file=tmp_file)
        print("raw_dir=ncrfpp/tmp/raw.bio", file=tmp_file)
        print("nbest=1", file=tmp_file)
        print("decode_dir=ncrfpp/tmp/out.bio", file=tmp_file)
        print("dset_dir="+self.dset_dir, file=tmp_file)
        print("load_model_dir="+self.load_model_dir, file=tmp_file)
        print("data_model_dir="+self.load_model_dir, file=tmp_file)

        tmp_file.close()

    #################

    def read_ncrfpp_output(self, doc):
        """
        Read annotations of the chunker from output file.

        Input: Doc object to store the results in.
        Output: Doc object with added chunk annotation.
        """
        #Open chunker output file
        tmp_file = open(os.path.join(self.tmp_dir, "out.bio"),
                        mode="r", encoding="utf-8")

        #Collect annotations
        annotations = [[]]
        for line in tmp_file:
            if line.startswith("# 1.0000"):
                continue
            elif not line.strip():
                annotations.append([])
            else:
                annotations[-1].append(line.strip().split(" ")[-1])
        tmp_file.close()

        #Insert annotations into doc
        for sent, annos in zip(doc.sentences, annotations):
            for tok, anno in zip(sent.tokens, annos):
                tok.CHUNK = anno
        
        return doc

    #################

    def annotate(self, doc, **kwargs):
        """
        Apply the NCRF++ chunker to the given document.

        If a normalized word form should be used as input,
        this can be specified as key-word argument 'norm'.
        Per default, the 'FORM' value is used.

        Maps tagsets of the models to the tagset from Ortmann (2021a)
        with 6 tags: NC, PC, AC, ADVC, sNC, sPC.

        Tokens outside of these chunks are labeled 'O'.

        Input: Doc object
        Output: Chunked doc object
        """
        #Write doc to tmp file
        self.write_tmp_data(doc, kwargs.get("norm", "FORM"))
        
        #Call chunker
        chunk(self.data, self.model)
        
        #Read output from tmp file
        doc = self.read_ncrfpp_output(doc)

        #Map tagsets
        for sent in doc.sentences:
            self.map_tagsets(sent)

        return doc

    #################

    @staticmethod
    def map_tagsets(sentence):
        """
        Maps tagsets of the chunker models to the tagset from Ortmann (2021a)
        with 6 tags: NC, PC, AC, ADVC, sNC, sPC.

        Tokens outside of these chunks are labeled 'O'.

        Input: Sentence object
        Output: Sentence object with mapped chunk tags
        """
        for tok in sentence.tokens:
            tok.CHUNK = tok.CHUNK.replace("NP", "NC")
            tok.CHUNK = tok.CHUNK.replace("PP", "PC")
            tok.CHUNK = tok.CHUNK.replace("AP", "AC")
            tok.CHUNK = tok.CHUNK.replace("ADVP", "ADVC")
            if not tok.CHUNK.split("-")[-1] in ["NC", "PC", "AC", 
                                                "ADVC", "sNC", "sPC"]:
                tok.CHUNK = "O"

        return sentence

    ###############

    @staticmethod
    def chunks_from_phrases(sentence):
        """
        Turn phrases into chunks.

        Takes phrase spans from sentence.phrases and
        converts them to chunks. The result is stored
        in sentence.chunks.

        Input: Sentence object
        Output: Sentence object
        """

        ########################

        def get_chunk(p):
            """
            Recursively turn input phrase into chunks.

            Input: Phrase span
            Output: List of chunks
            """

            chunks = []
            
            #Phrase contains other phrase
            if p.is_complex():

                #Create a new empty chunk span
                c = Span(p.get_label().replace("NP", "NC").replace("PP", "PC").replace("AP", "AC").replace("ADVP", "ADVC"),
                         elements=[])

                #For each element (span, token) inside the phrase
                for i, e in enumerate(p.get_elements()):
                    
                    #If it is a phrase
                    if isinstance(e, Span):

                        #The phrase continues afterwards -> stranded chunk
                        if c and c.get_elements() \
                           and any(not t.XPOS.startswith("$") for t in c.get_tokens()):
                            if i < len(p.get_elements())-1 \
                                and any(not isinstance(t, Span) for t in p.get_elements()[i:]):
                                if c.get_label() in ["NC", "PC"]:
                                    c.set_label("s" + c.get_label())
                            
                            #The chunk ends here
                            chunks.append(c)
                            c = Span(p.get_label().replace("NP", "NC").replace("PP", "PC").replace("AP", "AC").replace("ADVP", "ADVC"),
                                     elements=[])

                        #Get embedded chunks recursively
                        chunks.extend(get_chunk(e))

                    #If it is a token
                    else:
                        #Add to chunk
                        c.append_element(e)
                
                #If the chunk contains not just punctuation
                #add it to the output.
                if c and c.get_elements() \
                   and any(not t.XPOS.startswith("$") for t in c.get_tokens()):
                    chunks.append(c)
                
            #Non-complex phrase
            else:
                #Convert to chunk
                if p.get_label() in ["NP", "PP", "AP", "ADVP"]:
                    c = Span(p.get_label().replace("NP", "NC").replace("PP", "PC").replace("AP", "AC").replace("ADVP", "ADVC"),
                            p.get_elements())
                    chunks.append(c)
                        
            return chunks

        #######################

        chunks = []

        #For each phrase, recursively get chunks
        for p in sentence.phrases:
            chunks.extend(get_chunk(p))
        
        sentence.chunks = chunks

        return sentence

##########################

def initialize(model, **kwargs):
    """
    Instantiates the chunker with the given model.

    Possible model names are news1, news2, mix, and hist.
    If the model is unknown, returns None.

    Input: Model name
    Output: Chunker object or None
    """
    if model in ["hist", "news1", "news2", "mix"]:
        myChunker = NCRFppChunker(model)
    else:
        return None
    return myChunker

###########################
