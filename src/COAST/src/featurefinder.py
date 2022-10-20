'''
Created on 23.10.2019

@author: Katrin Ortmann

Module to compute various features of orality.
The feature computation is based on Sentence objects.
'''

import re, os
import statistics

#############################

class FeatureFinder(object):

    available_stats = ["mean_sent", "med_sent", "mean_word", "med_word",
                       "subord", "coordInit", "question", "exclam", "V:N",
                       "lexDens", "PRON1st", "DEM", "DEMshort", "PTC", "INTERJ"]

    default_weights = { "mean_word" : -0.819, 
                        "PRON1st" : 0.717, 
                        "V:N" : 0.528,
                        "DEMshort" : 0.365,
                        "subord" : -0.314, 
                        "INTERJ" : 0.276, 
                        "DEM" : 0.06, 
                        "PTC" : 0.104, 
                        "lexDens" : -0}

    ###################

    def __init__(self, features=[], weights={}):
        if features:
            self.stats = []
            for feat in features:
                if feat in self.available_stats:
                    self.stats.append(feat)
                else:
                    print("WARNING: Feature {0} is not available and will not be considered.".format(feat))
        else:
            self.stats = self.available_stats
            print("Analyzing default features.")
        
        if weights:
            self.weights = {}
            for feat, w in weights.items():
                if feat in self.available_stats:
                    self.weights[feat] = w
                else:
                    print("WARNING: Feature {0} is not available. Weight will not be used.".format(feat))
        else:
            self.weights = self.default_weights
            print("Using default weights.")

        print()
        print("### Settings ###")
        print("Features:")
        print(", ".join(self.stats))
        
        print()
        print("Weights:")
        for feat, weight in sorted(self.weights.items(), key=lambda l : abs(l[1]), reverse=True):
            print(feat, ":", weight)
        print()

    ###################

    
    ####################################
    #COMPLEXITY
    ############

    def sentence_length_without_punctuation(self, sentence):
        """
        Return the number of tokens in the given sentence
        that are not punctuation marks.
        Input: Sentence object.
        Output: List containing number of tokens without punctuation.
        """
        return [len([1 for tok in sentence if not tok.is_punctuation()])]

    ############

    def word_length(self, sentence):
        """
        Return the number of characters of each token
        in a given sentence. Ignore punctuation marks.
        Input: Sentence object.
        Output: List of character counts [charsTok1, charsTok2, ...].
        """
        return [len(tok) for tok in sentence if not tok.is_punctuation()]

    ############

    def sentence_initial_KON(self, sentence):
        """
        Count how often a coordinating conjunction appears sentence initially.
        Only allow for preceding punctuation (e.g. "...", "-", etc.)
        (Coordinating conjunctions have to coordinate sentences - but not relevant now.)
        Input: Sentence object.
        Output: 0 (no initial KON) or 1 (initial KON)
        """
        for tok in sentence:
            #Token is a coordinating conjunction
            if tok.XPOS == "KON":
                #First token or only preceded by punctuation    
                if tok.INDEX == 0 \
                or all(t.XPOS[0] == "$" for t in sentence if t.INDEX < tok.INDEX):
                    return 1
        return 0

    ############

    def coord(self, sentence):
        """
        Count coordinating conjunctions.
        Input: Sentence object.
        Output: Conjunction count
        """
        cons = 0
        for tok in sentence:
            #Token is a coordinating conjunction
            if tok.XPOS == "KON":
                cons += 1
        return cons

    ############

    def subordinating_conj(self, sentence):
        """
        Count subordninating conjunctions.
        Input: Sentence object.
        Output: Conjunction count
        """
        conjs = 0
        for tok in sentence:
            #Token is a subordinating conjunction
            if tok.XPOS in ["KOUS", "KOUI"]:
                conjs += 1
        return conjs

    ############

    def nominal_verbal_style(self, sentence):
        """
        Count nouns and verbs.
        Input: Sentence object.
        Output: Noun count, Verb count
        """
        nouns, verbs = 0, 0
        for tok in sentence:
            if tok.XPOS == "NN":
                nouns += 1
            elif tok.XPOS.startswith("VV"):
                verbs += 1
        return (nouns, verbs)
    
    ####################################
    #Reference/Deixis
    #################

    def first_person_pronouns(self, sentence):
        """
        Count first person pronouns with lemmas 'ich' and 'wir'.
        Input: Sentence object.
        Output: Number of first person pronouns
        """
        ich, wir = 0, 0
        for tok in sentence:
            if tok.LEMMA == "ich":
                ich += 1
            elif tok.LEMMA == "wir":
                wir += 1
        return ich + wir

    ############

    def demonstratives(self, sentence):
        """
        Count demonstrative pronouns and their long and short forms 'dies/e' and 'der/die'.
        Input: Sentence object.
        Output: DEM, DEMlong, DEMshort
        """
        DEM, DEMlong, DEMshort = 0, 0, 0
        for tok in sentence:
            if tok.XPOS == "PDS":
                DEM += 1
                if tok.LEMMA in ["dies", "diese"]:
                    DEMlong += 1
                elif tok.LEMMA in ["der", "die"]:
                    DEMshort += 1
        return DEM, DEMlong, DEMshort

    ####################################
    #Word order
    ############

    def lexical_items(self, sentence):
        """
        Count the lexical items (i.e. content words) in the sentence.
        Counted are adjectives, adverbs, nouns, names and (full) verbs.
        Input: Sentence object.
        Output: Number of lexical items.
        """
        n_lex_items = 0
        for tok in sentence:
            if re.match(r"(ADJ|ADV|NN|NE|VV)\w*", tok.XPOS):
                n_lex_items += 1
        return n_lex_items

    #############

    def sentence_type(self, sentence):
        """
        Count different sentence types.
        To determine the sentence type, check the last token that is tagged as $.
        If it contains a ? it is a question, with a ! it's an exclamation.
        Otherwise it is considered to be a normal sentence.
        Input: Sentence object.
        Output: question, exclamation, normalsent
        """
        question, exclamation, normalsent = 0, 0, 0
    
        tokens = sentence.tokens[:]
        tokens.reverse()
    
        for tok in tokens:
        
            if tok.XPOS == "$.":
                if "?" in str(tok):
                    question = 1
                    break
                elif "!" in str(tok):
                    exclamation = 1
                    break
                elif "." in str(tok) or ":" in str(tok):
                    normalsent = 1
                    break
                else:
                    continue
    
        if not any((question, exclamation, normalsent)):
            normalsent = 1
        
        return question, exclamation, normalsent

    ####################################
    #Lexic
    ############

    def n_interjections(self, sentence):
        """
        Count interjections (XPOS tag 'ITJ') in the sentence.
        Input: Sentence object.
        Output: Number of interjections.
        """
        return len([tok for tok in sentence if tok.XPOS == "ITJ"])

    ############

    def antwortpartikeln(self, sentence):
        """
        Count answer particles (XPOS tag 'PTKANT') in the sentence.
        Input: Sentence object.
        Output: Number of particles
        """
        PTKANT = 0
        for tok in sentence:
            if tok.XPOS == "PTKANT":
                PTKANT += 1
        return PTKANT

    ####################################

    def get_features_sentence(self, sentence, feature_dict=None):
        """
        Calculate the features for a given sentence by calling the corresponding functions.
        The resulting feature table is stored in the sentence object.
        Input: Sentence object and feature dictionary
        Output: Sentence
        """
        if not feature_dict:
            feature_dict = {
                "sent_len_no_punct" : self.sentence_length_without_punctuation,
                "word_len" : self.word_length,
                "coordInit" : self.sentence_initial_KON,
                "subord" : self.subordinating_conj,
                "nominal_verbal_style" : self.nominal_verbal_style,
                "PRON1st" : self.first_person_pronouns,
                "DEM" : self.demonstratives,
                "lexical_items" : self.lexical_items,
                "sent_type" : self.sentence_type,
                "INTERJ" : self.n_interjections,
                "PTC" : self.antwortpartikeln}
        feat_table = dict()
        for feature in feature_dict: 
            feat_table[feature] = feature_dict[feature](sentence)
        sentence.feat_table = feat_table
        return sentence

    ####################################

    def get_features_text(self, doc):
        """
        Add up the results/counts of each feature for all sentences.
        The feature table is stored in the doc object.
        Input: Doc object
        Output: Doc object
        """
        feat_table = dict()
        for sent in doc.sentences:
            for feat,val in sent.feat_table.items():
                if feat in feat_table:
                    if type(val) == tuple:
                        new_tup = list()
                        for o,n in zip(feat_table[feat], sent.feat_table[feat]):
                            new_tup.append(o+n)
                        feat_table[feat] = tuple(new_tup)
                    else:
                        feat_table[feat] += val
                else:
                    feat_table[feat] = val
        doc.feat_table = feat_table
        return doc

    ####################################

    def get_features_corpus(self, corpus):
        """
        Add up the results/counts of each feature for all docs.
        The feature table is stored in the corpus object.
        Input: Corpus object
        Output: Corpus object
        """
        feat_table = dict()
        n_sents = 0
        for doc in corpus.files:
            n_sents += doc.n_sents
            for feat,val in doc.feat_table.items():
                if feat in feat_table:
                    if type(val) == tuple:
                        new_tup = list()
                        for o,n in zip(feat_table[feat], doc.feat_table[feat]):
                            new_tup.append(o+n)
                        feat_table[feat] = tuple(new_tup)
                    else:
                        feat_table[feat] += val
                else:
                    feat_table[feat] = val
        corpus.feat_table = feat_table
        corpus.n_sents = n_sents
        return corpus

    ####################################

    def find_features(self, doc):
        """
        Get values for all features to measure the orality of a given document.
        The result is stored in the doc object.
        Input: Doc object
        Output: Doc object
        """
        for sent in doc.sentences:
            sent = self.get_features_sentence(sent)
    
        doc = self.get_features_text(doc)

        return doc

    ###################################

    def sum_features(self, corpus):
        corpus = self.get_features_corpus(corpus)
        return corpus
    
    ###################################
    
    def compute_stats(self, obj):
        
        stats_table = dict()

        stats_table["mean_sent"] = statistics.mean(obj.feat_table["sent_len_no_punct"])
        stats_table["med_sent"] = statistics.median(obj.feat_table["sent_len_no_punct"])
        stats_table["mean_word"] = statistics.mean(obj.feat_table["word_len"])
        stats_table["med_word"] = statistics.median(obj.feat_table["word_len"])
        
        try:
            stats_table["subord"] = round(obj.feat_table["subord"] / obj.feat_table["nominal_verbal_style"][1], 10)
        except ZeroDivisionError:
            stats_table["subord"] = None

        stats_table["coordInit"] = round(obj.feat_table["coordInit"] / obj.n_sents, 10)
        stats_table["question"] = round(obj.feat_table["sent_type"][0] / obj.n_sents, 10)
        stats_table["exclam"] = round(obj.feat_table["sent_type"][1] / obj.n_sents, 10)

        try:
            stats_table["V:N"] = round(obj.feat_table["nominal_verbal_style"][1] / obj.feat_table["nominal_verbal_style"][0], 10)
        except ZeroDivisionError:
            stats_table["V:N"] = None

        n_words = sum(obj.feat_table["sent_len_no_punct"])
        stats_table["lexDens"] = round(obj.feat_table["lexical_items"] / n_words, 10)
        stats_table["PRON1st"] = round(obj.feat_table["PRON1st"] / n_words, 10)

        stats_table["DEM"] = round(obj.feat_table["DEM"][0] / n_words, 10)
        
        try:
            stats_table["DEMshort"] = round(obj.feat_table["DEM"][2] / (obj.feat_table["DEM"][1] + obj.feat_table["DEM"][2]), 10)
        except ZeroDivisionError:
            stats_table["DEMshort"] = None

        stats_table["PTC"] = round(obj.feat_table["PTC"] / n_words, 10)
        stats_table["INTERJ"] = round(obj.feat_table["INTERJ"] / n_words, 10)

        obj.stats_table = stats_table

        return obj

    ###################################

    def scale_feature_values(self, results):
        scaled_results = dict()

        for filename in results:
            scaled_results[filename] = dict()
            for key in results[filename]:
                if not key in self.stats:
                    scaled_results[filename][key] = results[filename][key]

        for feat in self.stats:
            #Get min and max val for each feature
            vals = [results[f][feat] for f in results if not results[f][feat] == None]
            if vals:
                min_val = min(vals)
                max_val = max(vals)
            else:
                min_val = 0
                max_val = 0
            
            #Transform feature values
            for filename in results:
                if results[filename][feat] == None:
                    scaled_results[filename][feat] = 0.0
                else:
                    try:
                        scaled_results[filename][feat] = (results[filename][feat] - min_val) / (max_val - min_val)
                    except ZeroDivisionError:
                        scaled_results[filename][feat] = 0.0
        
        return scaled_results

    ###################################

    def calculate_score(self, results):
        for _, stats_table in results.items():
            score = 0
            for feat, weight in self.weights.items():
                if stats_table[feat] != None:
                    score += (stats_table[feat] * weight)
            stats_table["orality_score"] = score
        return results

    ###################################

    def kajuk_output(self, results):

        scores = {"overall":   {"Bauernleben" : 35.3,
                                "Guentzer" : 38.6,
                                "Soeldnerleben" : 43.4,
                                "Thomasius" : 2.6,
                                "Zimmer" : 29,
                                "Koralek" : 39,
                                "Briefwechsel" : 39.3,
                                "Nietzsche" : 4.1},
                   "micro" :   {"Bauernleben" : 26.2,
                                "Guentzer" : 28.8,
                                "Soeldnerleben" : 24.2,
                                "Thomasius" : 3.3,
                                "Zimmer" : 14.7,
                                "Koralek" : 14.7,
                                "Briefwechsel" : 41.8,
                                "Nietzsche" : 4.9},
                   "macro" :   {"Bauernleben" : 44.4,
                                "Guentzer" : 48.3,
                                "Soeldnerleben" : 62.7,
                                "Thomasius" : 2.0,
                                "Zimmer" : 43.2,
                                "Koralek" : 63.2,
                                "Briefwechsel" : 36.7,
                                "Nietzsche" : 3.4}}        

        columns = ["file", "subset", "oral", "KaJuK_score", "micro", "macro"]

        for filename, stats_table in sorted(results.items()):
            if os.path.splitext(filename)[0].startswith("Nietzsche") \
                or os.path.splitext(filename)[0].startswith("Thomasius"):
                oral = "lit"
            else:
                oral = "oral"

            stats_table["oral"] = oral
            stats_table["micro"] = scores["micro"].get(os.path.splitext(filename)[0].split("_")[0])
            stats_table["macro"] = scores["macro"].get(os.path.splitext(filename)[0].split("_")[0])
            stats_table["KaJuK_score"] = scores["overall"].get(os.path.splitext(filename)[0].split("_")[0])
            stats_table["file"] = os.path.splitext(filename)[0].split("_")[0]
            stats_table["subset"] = os.path.splitext(filename)[0]

        return columns, results

    #######################################

    def output_stats(self, results, outdir, kajuk_mode=False):

        #Define output columns and add meta values
        if kajuk_mode:
            columns, results = self.kajuk_output(results)
        else:
            columns = ["file"]
            for filename in results:
                results[filename]["file"] = os.path.splitext(filename)[0] 
        columns += self.stats

        #Scale results
        scaled_results = self.scale_feature_values(results)
        #Calculate score based on scaled results
        scaled_results = self.calculate_score(scaled_results)

        outfile_orig = open(outdir + "/results.csv", mode="w", encoding="utf-8")
        outfile_scaled = open(outdir + "/results_scaled.csv", mode="w", encoding="utf-8")

        #Output header
        print("\t".join(columns), file=outfile_orig)
        print("\t".join(columns), "orality_score", sep="\t", file=outfile_scaled)

        #Print original values
        for _, stats_table in sorted(results.items()):
            print("\t".join([str(stats_table[val]) for val in columns]), file=outfile_orig)

        #Print scaled results plus score
        for _, stats_table in sorted(scaled_results.items()):
            print("\t".join([str(stats_table[val]) for val in columns+["orality_score"]]), file=outfile_scaled)

        outfile_orig.close()
        outfile_scaled.close()
