# CLASSIG Pipeline (Computational Linguistic Analysis of Syntactic Structures In German)

This repository contains the code and documentation for the CLASSIG pipeline. The pipeline can be used to automatically annotate, evaluate, and analyze syntactic structures in modern and historical German texts.  

The pipeline was created for my dissertation *"Computational Methods for Investigating Syntactic Change: Automatic Identification of Extraposition in Modern and Historical German"*.
It is accompanied by data sets, results, and models in [the CLASSIG Data repository](https://github.com/rubcompling/classig-data).  

In this repository, the following resources are provided:  
- The `models` folder contains parser [models](#models) for automatic annotation. Due to space constraints, the chunker models cannot be stored in this repository. If you want to use the chunker, the models are available for download at [Zenodo](https://doi.org/10.5281/zenodo.7180973).  
- The `src` folder contains all scripts to use the pipeline. That includes modified versions of the [C6C Converter Pipeline](https://github.com/rubcompling/C6C), the [COAST implementation](https://github.com/rubcompling/COAST) for orality analysis, the [NCRF++ Chunker](https://github.com/jiesutd/NCRFpp), the Java-based [Berkeley Parser](https://github.com/slavpetrov/berkeleyparser) for topological field parsing and constituency analysis, [FairEval](https://github.com/rubcompling/FairEval) for evaluation, and the code to run the pipeline.  
- The `R` folder contains the [scripts](#r-code) used to produce the plots and statistics in the thesis.
- An example [configuration file](#config) is provided in the `config` folder.

## Contents of this Documentation

1. [Requirements](#requirements)  
2. [Basic Usage](#basic-usage)  
3. [Configuration](#config)  
4. [Supported Functions](#actions)  
    4.1 [Annotate](#annotate)  
    4.2 [Evaluate](#evaluate)  
    4.3 [Calculate Data Statistics](#data-statistics)  
    4.4 [Create a Variant Corpus](#variant-corpus)  
    4.5 [Create Language Models](#create-language-models)  
    4.6 [Surprisal Calculation](#surprisal-calculation)  
    4.7 [DORM](#dorm)  
    4.8 [Orality Analysis](#orality-analysis)  
    4.9 [RelC Analysis](#relc-analysis)  
    4.10 [Create Tables](#tables)  
5. [Models](#models)  
6. [License](#license)  

## Requirements

- [Python 3](https://www.python.org/) to execute the scripts in the `src` folder
- [R](https://www.r-project.org/) to execute the scripts in the `R` folder

To use the [NCRF++ chunker](https://github.com/jiesutd/NCRFpp), the required Python packages must be installed (torch, numpy, etc.).  

To invoke the [Berkeley parser](https://github.com/slavpetrov/berkeleyparser), you must be able to run the [Java](https://www.java.com/) code.  

## Basic Usage

The pipeline is called via the command line with a [configuration file](#config) that specifies the required parameters:

> py CLASSIG.py --config ./../config/example.config

## Config

The configuration file consists of key-value pairs `key = value` with one pair per line.  
Multiple values for one key can be added with commas, e.g., `annotations = chunks, phrases`.  

Empty lines and lines starting with a hash sign `#` are ignored.  

The following keys are recognized:

| Key           | Function                                   |
|:--------------|:-------------------------------------------|
| `action`      | Determines what the pipeline will do, see supported [actions](#actions). |
| `annotations` | If `action` includes the value `annotate`, the given annotations are created. `all` will create all [supported annotations](#annotate). |
| `models`      | If `action` includes the value `annotate`, the given models are used for annotation. `all` will apply all [models](#models). |
| `format_gold` | The input format (`conllup` or `conll2000`). The output format is always `conllup`. |
| `format_in`   | Format of the gold data (`conllup` or `conll2000`) |
| `corpus`      | Name of the corpus to analyze. |
| `in_dir`      | Folder with input files. |
| `out_dir`     | Folder where system annotations will be stored. |
| `gold_dir`    | Folder with gold standard data. |
| `eval_dir`    | Folder where [evaluation results](#evaluate) will be stored. |
| `variant_dir` | Folder in which the [variant corpus](#variant-corpus) should be generated. |
| `train_dir`   | Folder with training files for [language model](#create-language-models) creation. |
| `lm_dir`      | Folder where [language models](#create-language-models) are stored. |
| `lm_models_n` | N-gram size of [language models](#create-language-models) (`1` and/or `2`). |
| `lm_models`   | Type of [language models](#create-language-models) (`FORM`, `LEMMA`, `WORD`, `XPOS`). |
| `model_dir`   | Folder with parser/chunker [models](#models) (default: `./../models/`). |
| `norm`        | Input column to use as normalization (e.g., `NORM`; if `None`, defaults to `FORM`). |

The `config` folder contains an example configuration file, which would execute all possible actions with all supported models on an example corpus.

## Actions

The pipeline can be used for different purposes. The following actions are currently supported:

| Action        | Function                                     |
|:--------------|:---------------------------------------------|
| [annotate](#annotate)                | Creates the annotations listed under `annotations` with the models listed under `models`. |
| [evaluate](#evaluate)                | Evaluates the annotations listed under `annotations` for each model listed under `models`. Annotations in `out_dir` are compared to those in `gold_dir` with traditional and fair evaluation. |
| [data_stats](#data-statistics)       | Counts documents, sentences, tokens, words, and labels for each annotation in the given `corpus`. |
| [create_lm](#create-language-models) | Creates n-gram language model(s) with size `lm_models_n`. Models are generated for each annotation given in `lm_models`. |
| [variants](#variant-corpus)          | Generates a variant corpus by undoing the extraposition of relative clauses. |
| [surprisal](#surprisal-calculation)  | Calculates n-gram surprisal for original and variant sentences with the given language models. Also calculates mean surprisal for each RelC in the original data. |
| [dorm](#dorm)                        | Calculates DORM from n-gram surprisal values of original and variant files. |
| [orality](#orality-analysis)         | Calculates orality scores with [COAST](https://github.com/rubcompling/COAST). |
| [analyze_relcs](#relc-analysis)      | Collects length, position, and additional information for each annotated relative clause. |
| [tables](#tables)                    | Creates LaTeX tables and input for scripts in the `R` folder from `evaluate` and `data_stats` results  |
| `all`                                | Executes everything listed above. |

The actions are performed in the given order, so they can build on each other (i.e., the data is annotated before evaluation, etc.).  

Different parameters must be set depending on the desired action:

| Action        | Input from                    | Output to         | Parameters                                                               |
|:--------------|:------------------------------|:------------------|:-------------------------------------------------------------------------|
| annotate      | in_dir                        | out_dir           | annotations, models, corpus, format_in, model_dir, res_dir, tagger, norm |
| evaluate      | out_dir, gold_dir             | eval_dir          | annotations, models, corpus, format_in, format_gold                      |
| data_stats    | gold_dir                      | eval_dir          | annotations, corpus, format_gold                                         |
| create_lm     | train_dir                     | lm_dir            | corpus, lm_models, lm_models_n, format_gold, norm                        |
| variants      | gold_dir                      | variant_dir       | corpus, format_gold                                                      |
| surprisal     | gold_dir, variant_dir, lm_dir | out_dir, eval_dir | corpus, lm_models, lm_models_n, format_gold, norm                        |
| dorm          | out_dir                       | eval_dir          | corpus, format_gold, models                                              |
| orality       | gold_dir						| eval_dir          | corpus, format_gold                                                      |
| analyze_relcs | gold_dir                      | eval_dir          | corpus, format_gold                                                      |
| tables        | eval_dir                      | eval_dir          | annotations                                                              |

If you do not have gold data, set `gold_dir` to the folder where your automatic annotations are stored (usually a sub-directory of `out_dir`).

- - - - - - - - - - - - - - - - 

### Annotate

The action `annotate` creates all annotations listed under `annotations` with the models listed under `models`.  
As input, it takes the data from `in_dir` and stores the annotated data in `out_dir`.  

The following annotations are currently supported with the specified [models](#models):  

| Value      | Annotation             | Tool                             | Models                           |
|:-----------|:-----------------------|:---------------------------------|:---------------------------------|
| `brackets` | Sentence brackets      | [Berkeley parser](https://github.com/slavpetrov/berkeleyparser)                  | `Punct`, `News1`                 |
| `topf`     | Topological fields     | [Berkeley parser](https://github.com/slavpetrov/berkeleyparser)                  | `Punct`, `News1`                 |
| `chunks`   | Chunks                 | [NCRF++](https://github.com/jiesutd/NCRFpp)                           | `News1`, `News2`, `Hist`, `Mix`  |
| `phrases`  | Phrases                | [Berkeley parser](https://github.com/slavpetrov/berkeleyparser)                  | `News1`, `News2`, `Hist`, `Mix`  |
| `extrap`   | Extraposition candidates (including relative clauses and their antecedents) | [Berkeley parser](https://github.com/slavpetrov/berkeleyparser) | `News1`, `News2`, `Hist`, `Mix` (always uses `Punct`, too) |

A documentation of tagsets and output formats can be found in the [CLASSIG Data repository](https://github.com/rubcompling/classig-data).

**Additional remarks:**  
During annotation, the Berkeley parser often outputs *"ROOT has more than one child!"* This message can be ignored.  

- - - - - - - - - - - - - - - - 

### Evaluate

The action `evaluate` applies traditional and fair evaluation to the annotations listed under `annotations` for each model listed under `models`. 
Annotations in `out_dir` are compared to those in `gold_dir` and the results are stored in `eval_dir`.

The action outputs the numbers of true positives and error types and the calculated metrics (precision, recall, F-score) for the given `corpus`. Results are created for individual files and labels and overall. Fair evaluation is performed with [FairEval](https://github.com/rubcompling/FairEval).

The output can be used by the `table` action to produce LaTeX tables and input for plotting and statistics with [R](#r-code).

- - - - - - - - - - - - - - - - 

### Data Statistics

The action `data_stats` counts documents, sentences, tokens, words, and labels for each annotation in the given `corpus` from `gold_dir`.
Statistics are stored in the `eval_dir` and can be used by the `table` action to produce input for plotting with [R](#r-code).

- - - - - - - - - - - - - - - - 

### Create Language Models

The action `create_lm` creates n-gram language model(s) with n of size `lm_models_n`, e.g., `2`.
Models are generated for each annotation given in `lm_models`, e.g., `FORM, POS`. 

Training data is taken from `train_dir` and the models are stored in `lm_dir`. Models are named after n-gram size and annotation, e.g., `1-gram_XPOS` for a unigram model based on POS tags. The model files contain two tab-separated columns with n-gram and frequency. n-grams (first column) are separated with spaces for n > 1. #S and #E are used as padding elements.

The models from the thesis can be downloaded from [Zenodo](https://doi.org/10.5281/zenodo.7180973).

- - - - - - - - - - - - - - - - 

### Variant Corpus

The action `variants` generates a variant corpus by undoing the extraposition of relative clauses.  

For each input file from `gold_dir`, a variant file with the same name is created in `variant_dir`. The variant file contains all sentences from the original file but extraposed relative clauses (labeled as `RELC-extrap`) are moved adjacent to their antecedent and re-labeled as `RELC-insitu`. Tokens are re-indexed and the sentence attribute `#text` is regenerated. If relative clauses were preceded by punctuation or coordination, those are moved, too.

- - - - - - - - - - - - - - - - 

### Surprisal Calculation

The action `surprisal` calculates n-gram surprisal for original (`gold_dir`) and variant sentences (`variant_dir`) with the given language models. Currently, always calculates unigram and bigram surprisal with models for the annotations listed in `lm_models`. The output is stored in `out_dir` with surprisal values in columns 'UnigramSurpr' and 'BigramSurpr' followed by the annotation name, e.g., `BigramSurprXPOS`.

The action also calculates mean surprisal for each RelC in the original data. The results are output to `eval_dir`.

**Caution:** Every time the action is performed, the output of the RelC surprisal analysis is appended to the result file! This allows to add the results from different corpora to the same file. If you want to recalculate the results, you must use another output file or remove the old results beforehand.

- - - - - - - - - - - - - - - - 

### DORM

The action `dorm` calculates DORM from n-gram surprisal values of original and variant files (taken from the output of the `surprisal` action in `out_dir`). 
Calculations are performed for word form and POS bigram surprisal and stored in two output files for token-based and constituent-based analysis in `eval_dir`.

To determine constituents, the files must contain a constituency analysis (`PTBstring`) and the model must be given as `models`. For TüBa-style trees, the model `News1` should be specified. For Tiger-style trees, any other model can be given. If the model cannot be determined, only a token-based analysis is performed.

**Caution:** Every time the action is performed, the output is appended to the result file! This allows to add the results from different corpora to the same file. If you want to recalculate the results, you must use another output file or remove the old results beforehand.

- - - - - - - - - - - - - - - - 

### Orality Analysis

The action `orality` calculates orality scores with the integrated version of [COAST](https://github.com/rubcompling/COAST). 

For the given input files from `gold_dir`, two files are created in `eval_dir`: one with the raw feature values (`_results.csv`) and one with scaled results and the orality score for each text (`_results_scaled.csv`).

Files are expected to contain the lemmas required by the [orality analysis](https://github.com/rubcompling/COAST).

- - - - - - - - - - - - - - - - 

### RelC Analysis

The action `analyze_relcs` collects length (in words), position (insitu/ambig/extrap), the distance to the antecedent (in words) and the distance to the end of the sentence (in words) for each annotated relative clause in the input data (`gold_dir`). The results are output to `eval_dir`.

**Caution:** Every time the action is performed, the output is appended to the result file! This allows to add the results from different corpora to the same file. If you want to recalculate the results, you must use another output file or remove the old results beforehand.

- - - - - - - - - - - - - - - - 

### Tables

The action `tables` creates LaTeX tables and input for scripts in the `R` folder from the results of the actions `evaluate` and `data_stats` in the `eval_dir`.
The output is stored in `eval_dir`, too.

## Models

The `models` folder contains parser models for automatic annotation. For usage with the pipeline, the models must be placed in the specified `model_dir`.  
The following models are available:  

**Constituency grammars:**

- `News1` : constituency_grammars/grammar_tueba_simple.gr
- `News2` : constituency_grammars/grammar_tiger_simple.gr
- `Hist` : constituency_grammars/grammar_hist_simple.gr
- `Mix` : constituency_grammars/grammar_mix_simple.gr

**Chunker models [(Zenodo)](https://doi.org/10.5281/zenodo.7180973):**

- `News1` : ncrfpp/lstmcrf_tueba_pos_pre-trained
- `News2` : ncrfpp/lstmcrf_tiger_pos_pre-trained
- `Hist` : ncrfpp/lstmcrf_hist_pos_pre-trained
- `Mix` : ncrfpp/lstmcrf_tigerxml_pos_pre-trained

Due to space constraints, the chunker models cannot be stored in this repository. If you want to use the chunker, all models are available for download at [Zenodo](https://doi.org/10.5281/zenodo.7180973).  

**Topological field grammars:**  

- `Punct` : topfgrammars/topfgrammar_punct.gr
- `NoPunct` : topfgrammars/topfgrammar_nopunct.gr (Currently not supported by the pipeline.)

## R Code

The `R` folder contains the scripts used to produce the plots and statistics in the thesis:

- `conf_matrix.R`: Builds confusion matrices from output files created by the `tables` action (see [above](#tables)).
- `error_types.R`: Creates plots of the error distribution based on output files created by the `tables` action (see [above](#tables)).
- `example_analyses.R`: Creates plots for the example analyses based on output created by the [RelC analysis](#relc-analysis), [surprisal calculation](#surprisal-calculation), [DORM calculation](#dorm), and [orality analysis](#orality-analysis). The script requires the metadata from [the CLASSIG Data repository](https://github.com/rubcompling/classig-data).
- `label_distribution.R`: Creates plots of the label distribution in the gold data for the different annotations. Requires output files created by the `tables` action (see [above](#tables)).
- `statistical_tests.R`: Contains the statistical tests from the example analysis. The tests are based on output created by the [RelC analysis](#relc-analysis), [surprisal calculation](#surprisal-calculation), [DORM calculation](#dorm), and [orality analysis](#orality-analysis). The script requires the metadata from [the CLASSIG Data repository](https://github.com/rubcompling/classig-data).

## License

- The Berkeley parser is licensed under [GPL 2.0](https://opensource.org/licenses/gpl-2.0.php)  
- NCRF++ is licensed under [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0.html)  
- COAST, C6C, and the remaining code are provided under the [MIT license](https://mit-license.org/)  
