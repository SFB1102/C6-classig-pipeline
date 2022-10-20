import re, os

##############################

def normalize_filename(filename, remove=[]):

    #Replace spaces, slash and backslash with underscore
    filename = re.sub(r"[\s\t\n\\/]", "_", filename)

    #Replace umlaut chars
    filename = re.sub(r"ä", "ae", filename)
    filename = re.sub(r"ö", "oe", filename)
    filename = re.sub(r"ü", "ue", filename)
    filename = re.sub(r"Ä", "Ae", filename)
    filename = re.sub(r"Ö", "Oe", filename)
    filename = re.sub(r"Ü", "ue", filename)
    filename = re.sub(r"ß", "ss", filename)

    filename = re.sub(r"ć", "c", filename)
    filename = re.sub(r"ñ", "n", filename)
    filename = re.sub(r"ç", "c", filename)
    filename = re.sub(r"é", "e", filename)
    filename = re.sub(r"è", "e", filename)
    filename = re.sub(r"ë", "e", filename)
    filename = re.sub(r"š", "s", filename)
    filename = re.sub(r"à", "a", filename)
    filename = re.sub(r"á", "a", filename)
    filename = re.sub(r"ó", "o", filename)
    filename = re.sub(r"ò", "o", filename)
    filename = re.sub(r"û", "u", filename)
    filename = re.sub(r"ô", "o", filename)
    filename = re.sub(r"É", "E", filename)

    filename = re.sub(r"&", "-", filename)

    #Remove quotes
    filename = re.sub(r"['\"„“`´]", "", filename)

    #Replace all longer dashes
    filename = re.sub(r"[–⸺]", "-", filename)

    #Remove some punctuation
    filename = re.sub(r"[!\(\)\|\?<>›‹]", "", filename)

    filename = re.sub(r"(\s+|[:;,/])", "_", filename)

    #Remove custom strings
    for rem in remove:
        filename = re.sub(rem, "", filename)

    return filename


##################################

def get_DTA_context(sample_folder, complete_folder, targetdir):

    samplefiles = sorted([os.path.join(sample_folder, f) for f in os.listdir(sample_folder)])
    completefiles = sorted([os.path.join(complete_folder, f) for f in os.listdir(complete_folder) if f in os.listdir(sample_folder)])

    myImporter = CoNLLUPlusImporter()

    for samplefile, completefile in zip(samplefiles, completefiles):
        sampledoc = myImporter.import_file(samplefile)
        completedoc = myImporter.import_file(completefile)

        contextfile = open(os.path.join(targetdir, sampledoc.filename), mode="w", encoding="utf-8")

        for sent in sampledoc.sentences:
            sent_index = int(sent.sent_id)-1

            if sent_index > 5: start = sent_index-5
            else: start = 0

            if sent_index < len(completedoc.sentences)-1-6: end = sent_index+6
            else: end = len(completedoc.sentences)-1

            context = completedoc.sentences[start:end]

            for sent in context:
                print(sent.sent_id, " ".join([tok.FORM for tok in sent.tokens]), file=contextfile)

            print(file=contextfile)

        contextfile.close

def create_DTA_samples():

    years = ["1950", "1900", "1850", "1800", "1750", "1700", "1650", "1600", "1550", "1500", "1450"]
    samples = [os.path.join(r"C:\Users\Katrin\Documents\Promotion\Daten\Korpora\DTA\POS\conlluplus", year) for year in years]
    tardirs = [os.path.join(r"C:\Users\Katrin\Documents\Promotion\Daten\Korpora\DTA\POS\context", year) for year in years]
    for sample, tardir in zip(samples, tardirs):
        get_DTA_context(sample, r"C:\Users\Katrin\Documents\Promotion\Daten\Korpora\DTA\conlluplus", tardir)

############################################

def TigerXMLtoFolders(file, outdir):

    import xml.etree.ElementTree as ET
    import xml.dom.minidom as minidom

    #######################

    #Function for pretty output.
    def prettify(elem): 
        """Return a pretty-printed XML string for the Element."""
        rough_string = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="", newl="")

    #######################

    def read_metadocs(metadocs, filename):
        """
        Read info from metadocuments into dictionary.
        Input: path of directory which includes all metadocuments, filename
        Output: Dictionary with meta info
        """

        #filename
        metainfo = dict()
        name = filename.split(".")[0]
        metainfo["filename"] = name

        #{sentID : docID}
        sentences = dict()
        sentence_file= open(os.path.join(metadocs, "sentences.tsv"), mode="r", encoding="utf-8")
        for line in sentence_file:
            line = line.strip().split("\t")
            sentences[line[1]] = line[0]
        sentence_file.close()
        metainfo["sentences"] = sentences

        #{folder : [docIDs]}
        train_files, dev_files, test_files = [], [], []
        train = open(os.path.join(metadocs, "documents_train.tsv"), mode="r", encoding="utf-8")
        dev = open(os.path.join(metadocs, "documents_dev.tsv"), mode="r", encoding="utf-8")
        test = open(os.path.join(metadocs, "documents_test.tsv"), mode="r", encoding="utf-8")
        for folder, filelist in [(train, train_files), (dev, dev_files), (test, test_files)]:
            for line in folder:
                filelist.append(line.strip())
        test.close()
        dev.close()
        train.close()
        metainfo["folders"] = {"train" : train_files, "dev" : dev_files, "test" : test_files}

        return metainfo

    ####################

    path, filename = os.path.split(file)

    metadocs = os.path.join(path, "TIGER2.2.doc")
    metainfo = read_metadocs(metadocs, filename)

    #Read xml tree
    tree = ET.parse(file)
    root = tree.getroot()
    body = root.find("body")
    
    doc = None
    for sentence in body:
        if sentence.attrib.get("id")[1:] in metainfo["sentences"]:
            doc_name = metainfo["sentences"][sentence.attrib.get("id")[1:]]
        else:
            doc_name = "unknown"

        if doc:
            if doc and doc.attrib["filename"] != doc_name:
                outfile = open(os.path.join(outdir, doc.attrib["folder"], doc.attrib["filename"]+".xml"), mode="w", encoding='utf-8')
                print(prettify(doc), file=outfile)
                outfile.close()   
                doc = ET.Element("doc", {"filename" : doc_name})     
        else:
            doc = ET.Element("doc", {"filename" : doc_name})
        doc.append(sentence)
        
        #ET.SubElement(doc, sentence)

        if doc_name in metainfo["folders"]["train"]:
            doc.attrib["folder"] = "train"
        elif doc_name in metainfo["folders"]["dev"]:
            doc.attrib["folder"] = "dev"
        elif doc_name in metainfo["folders"]["test"]:
            doc.attrib["folder"] = "test"
        else:
            doc.attrib["folder"] = "unknown"

    if doc:
        outfile = open(os.path.join(outdir, doc.attrib["folder"], doc_name+".xml"), mode="w", encoding="utf-8")
        print(prettify(doc), file=outfile)
        outfile.close()