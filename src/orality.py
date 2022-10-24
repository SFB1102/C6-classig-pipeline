
import os
from COAST.src.featurefinder import FeatureFinder
from COAST.src.processor import PronounLemmatizer, BracketRemover, EllipsisRemover

def determine_orality(docs, **config):
    """
    Determine orality of input docs with COAST.

    Input documents are lemmatized (and pre-processed) if necessary. 
    Results of COAST implementation are printed to one output file per corpus.

    Input: List of documents,
           config dictionary with 'eval_dir' and 'corpus'.
    """
    corpus = config.get("corpus")

    #Load FeatureFinder
    myFeatureFinder = FeatureFinder()

    #Create output file
    if not os.path.isdir(os.path.join(config.get("eval_dir"), "orality")):
        os.makedirs(os.path.join(config.get("eval_dir"), "orality"))
    outfile = open(os.path.join(config.get("eval_dir"), "orality", config.get("corpus")+"_results.csv"), 
                   mode="w", encoding="utf-8")
    print("file", "\t".join(myFeatureFinder.stats), sep="\t", file=outfile)
    
    #For each document
    for doc in docs:
        filename = os.path.splitext(doc.filename)[0]

        #Remove ellipses from KaJuK
        if corpus == "KaJuK":
            doc = EllipsisRemover().process(doc)

        #Remove brackets from KaJuK and ReF.RUB
        if corpus in ["KaJuK", "ReF.RUB"]:
            doc = BracketRemover().process(doc)

        #Map lemmas of similar analyses

        #ReF.RUB
        # ich + wir already correct
        # change der and dieser
        if corpus in ["ReF.RUB"]:
            for sent in doc.sentences:
                for tok in sent.tokens:
                    if tok.XPOS == "PDS":
                        if tok.LEMMA == "der":
                            tok.LEMMA = "die"
                        elif tok.LEMMA == "dieser":
                            tok.LEMMA = "diese" 
        #Anselm
        # ich + wir already correct
        # change d-, dies, and dirre
        elif corpus == "Anselm":
            for sent in doc.sentences:
                for tok in sent.tokens:
                    if tok.XPOS == "PDS":
                        if tok.LEMMA == "d-":
                            tok.LEMMA = "die"
                        elif tok.LEMMA == "dies" or tok.LEMMA == "dirre":
                            tok.LEMMA = "diese"
        #DTAscience
        # ich + wir already correct
        # change d
        elif corpus == "DTAscience":
            for sent in doc.sentences:
                for tok in sent.tokens:
                    if tok.XPOS == "PDS":
                        if tok.LEMMA == "d":
                            tok.LEMMA = "die"
        #GerManC
        # ich + wir already correct
        # change d, dies
        elif corpus.startswith("GerManC"):
            for sent in doc.sentences:
                for tok in sent.tokens:
                    if tok.XPOS == "PDS":
                        if tok.LEMMA == "d":
                            tok.LEMMA = "die"
                        elif tok.LEMMA == "dies":
                            tok.LEMMA = "diese"            
        #TuebaDW
        # ich + wir already correct
        # change das and dieses
        elif corpus == "TuebaDW" or corpus == "TuebaDZ":
            for sent in doc.sentences:
                for tok in sent.tokens:
                    if tok.XPOS == "PPER":
                        if tok.LEMMA == "das":
                            tok.LEMMA = "die"
                        elif tok.LEMMA == "dieses":
                            tok.LEMMA = "diese"   

        #Create new lemmas for different lemmatizations
        #- KaJuK
        #- RIDGES
        #- SdeWaC
        #- Tiger
        elif corpus in ["KaJuK", "RIDGES", "SdeWaC", "Tiger"]:
            doc = PronounLemmatizer().process(doc)

        #Already lemmatized
        #- OPUS
        #- Gutenberg
        #- SermonOnline
        #- TuebaDS

        for sent in doc.sentences:
            for i, tok in enumerate(sent.tokens):
                tok.INDEX = i

        #Get features for doc
        doc = myFeatureFinder.find_features(doc)

        #Compute statistics
        doc = myFeatureFinder.compute_stats(doc)

        #Output results
        print(filename, 
            "\t".join([str(doc.stats_table[feat]) 
                        for feat in myFeatureFinder.stats]), 
            sep="\t", file=outfile)

    outfile.close()

###################################

def scaled_results_and_scores(**config):
    """
    Scale orality features and calculate orality score.

    Takes the output files of determine_orality() 
    and scales values to 0..1 within each corpus.
    Calculates the orality score with COAST.

    The results are stored in the same folder as the unscaled results.

    Input: Config dictionary with 'eval_dir' and 'corpus'.
    """

    #Load FeatureFinder
    myFeatureFinder = FeatureFinder()

    corpus = config.get("corpus")

    if not os.path.isdir(os.path.join(config.get("eval_dir"), "orality")):
        os.makedirs(os.path.join(config.get("eval_dir"), "orality"))

    #Load unscaled results
    resultfile = open(os.path.join(config.get("eval_dir"), "orality", corpus+"_results.csv"),
                      mode="r", encoding="utf-8").readlines()
    columns = resultfile[0].strip().split("\t")
    results = [l.strip().split("\t") for l in resultfile[1:] if l.strip()]
    
    #Scale results
    scaled_results = []

    for i, col in enumerate(columns):
        
        if col in ["file", "corpus"]:
            if scaled_results == []:
                for l in results:
                    scaled_results.append([l[i]])
            else:
                for j, l in enumerate(results):
                    scaled_results[j].append(l[i])
            continue
        
        values = [0 if l[i] == "None"
                    else float(l[i]) for l in results]
        min_val = min(values)
        max_val = max(values)
        
        for j, v in enumerate(values):
            try:
                scaled_results[j].append((v - min_val) / (max_val - min_val))
            except ZeroDivisionError:
                scaled_results[j].append(0)

    #Calculate score on scaled results
    for i, l in enumerate(scaled_results):
        score = 0
        for feat, w in myFeatureFinder.weights.items():
            col = columns.index(feat)
            score += w * l[col]
        scaled_results[i].append(score)

    #Output scaled results
    scaled_file = open(os.path.join(config.get("eval_dir"), "orality",
                                    config.get("corpus")+"_result_scaled.csv"), 
                       mode="w", encoding="utf-8")
    columns.append("SCORE")
    print("\t".join(columns), file=scaled_file)
    for l in scaled_results:
        print("\t".join([str(v) for v in l]), file=scaled_file)
    scaled_file.close()

######################################

