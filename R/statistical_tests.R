#Import
library(ggplot2)
library(stringr)
library(tidyr)
library(dplyr)
library(car)
library(lsr)

set.seed(42)

##########################
#Read RelC result data
relcs <- read.table(file="eval/relc-extrap/relc_results.csv",
                    sep="\t", 
                    header=FALSE, 
                    na.strings=c("None"),
                    col.names=c("Corpus", "Filename", "Sentence", "RelC_ID", 
                                "Status", "Length", "Dist_left", "Dist_right"))

#Drop unnecessary columns
relcs <- subset(relcs, Status != "unknown", select=c(-Dist_left, -Dist_right), drop=TRUE)
relcs <- droplevels(relcs)
relcs$Status <- factor(relcs$Status, levels=c("insitu", "ambig", "extrap"))

#########################
#Read meta data
meta <- read.table(file="eval/meta.csv",
                   sep="\t",
                   header=TRUE,
                   encoding="utf-8")

#Year as number (not factor)
meta$Year <- as.numeric(as.character(meta$Year))

#Order registers from literal to oral
registers = c("News", "Science", "Non-Fiction", "Fiction", "Religion", "Spoken")
meta$Register <- factor(meta$Register, levels=registers)

#Left join of tables on filenames
#Keep all rows of relcs and add meta info
table <- merge(relcs, meta, by="Filename", all.x=TRUE)

#Remove double corpus column
table <- subset(table, select=-Corpus.y)
table <- rename(table, Corpus = Corpus.x)

##################################
# Tests for Length and Status

#Create a stratified sample with 50 RelCs per position per corpus
#(smallest corpus has about 80)
strat_sample <- table %>%
  group_by(Corpus, Status) %>%
  sample_n(size=50)

#Calculate mean, median and standard deviation
group_by(table, Register) %>%
  summarise(
    count = n(),
    mean = mean(Length, na.rm = TRUE),
    median = median(Length, na.rm = TRUE),
    sd = sd(Length, na.rm = TRUE)
  )

#Requirements for one-way ANOVA are not met
#according to tests below.
res_anova <- aov(Length~Status, strat_sample)
summary(res_anova)
etaSquared(res_anova, anova = T)

#All factor levels are significantly different
TukeyHSD(res_anova)

#Check homogeneity of variance assumption
leveneTest(Length ~ Status, data = strat_sample)

#Check normality assumption
plot(res_anova, 2)

#Non-parametric Kruskal Wallis test
kruskal.test(Length ~ Status, data = strat_sample)

#Pair-wise Wilcox test
pairwise.wilcox.test(strat_sample$Length, strat_sample$Status,
                     p.adjust.method = "bonferroni")

################################
#Test for orality and position

#Read orality data
orality_scaled <- read.table(file="eval/orality/all_result_scaled.csv",
                             sep="\t",
                             header=TRUE,
                             encoding="utf-8")
orality <- read.table(file="eval/orality/all_result.csv",
                      sep="\t",
                      header=TRUE,
                      encoding="utf-8")

#Append scores to unscaled data
orality$SCORE <- orality_scaled$SCORE

#Merge orality and relc data
orality_relc <- merge(table, orality, by.x="Filename", by.y="file")
orality_relc <- subset(orality_relc, select=-corpus)

#Create a stratified sample with 50 RelCs per position per corpus
#(smallest corpus has about 80)
strat_sample <- orality_relc %>%
  group_by(Corpus, Status) %>%
  sample_n(size=50)

#Calculate mean, median and standard deviation
group_by(orality_relc, Status) %>%
  summarise(
    count = n(),
    mean = mean(SCORE, na.rm = TRUE),
    median = median(SCORE, na.rm = TRUE),
    sd = sd(SCORE, na.rm = TRUE)
  )

#Requirements for one-way ANOVA are almost met.
res_anova <- aov(SCORE~Status, strat_sample)
summary(res_anova)
etaSquared(res_anova, anova = T)

TukeyHSD(res_anova)

#Check homogeneity of variance assumption
leveneTest(SCORE ~ Status, data = strat_sample)

#Check normality assumption
plot(res_anova, 2)

#One-way ANOVA on all data 
#(to demonstrate effects of large data sets)
res_anova <- aov(SCORE~Status, orality_relc)
etaSquared(res_anova, anova = T)
summary(res_anova)

TukeyHSD(res_anova)
  
#########################
# Orality and Register

#Merge orality and relc data
orality_register <- merge(meta, orality_scaled, by.x="Filename", by.y="file")
orality_register <- subset(orality_register, select=-corpus)

#Create a stratified sample with 75 files per register
#(smallest register has 76)
strat_sample <- orality_register %>%
  group_by(Register) %>%
  sample_n(size=75)

#Calculate mean, median and standard deviation
group_by(orality_register, Register) %>%
  summarise(
    count = n(),
    mean = mean(SCORE, na.rm = TRUE),
    median = median(SCORE, na.rm = TRUE),
    sd = sd(SCORE, na.rm = TRUE)
  )

#One-way ANOVA
res_anova <- aov(SCORE~Register, strat_sample)
summary(res_anova)
etaSquared(res_anova, anova = T)

TukeyHSD(res_anova)

#Check homogeneity of variance assumption
leveneTest(SCORE ~ Register, data = strat_sample)

#Check normality assumption
plot(res_anova, 2)

##########################
##########################
# Tests for surprisal

# Read surprisal data
surpr <- read.table(file="eval/surprisal/relc_results.csv",
                    sep="\t", 
                    header=TRUE, 
                    na.strings=c("NA"))

relc_surpr <- merge(surpr, meta, by="Filename", all.x=TRUE)

#Remove double corpus column
relc_surpr <- subset(relc_surpr, select=-Corpus.y)
relc_surpr <- rename(relc_surpr, Corpus = Corpus.x)

#Order positions from insitu to extraposed
relc_surpr$Position <- factor(relc_surpr$Position, 
                              levels=c("insitu", "extrap"))

corpora <- c("Gutenberg_Fiction", "Gutenberg_Folk_Tales", 
             "Gutenberg_Non-Fiction", "Gutenberg_Speech", 
             "OPUS_Action-Adventure", "OPUS_Comedy", "OPUS_Drama", 
             "SdeWaC", "SermonOnline", "Tiger", 
             "TuebaDS", "TuebaDW", "TuebaDZ", 
             "Anselm", "DTAscience", "GerManC_DRAM", 
             "GerManC_HUMA", "GerManC_LEGA", "GerManC_NARR", 
             "GerManC_NEWS", "GerManC_SCIE", "GerManC_SERM", "ReF.RUB")

#Check normality
for(corpus in corpora)
{
  with(subset(relc_surpr, Corpus == corpus), 
      qqPlot(MeanBiSurprXPOS[Position == "insitu"]))
  with(subset(relc_surpr, Corpus == corpus), 
       qqPlot(MeanBiSurprXPOS[Position == "extrap"]))
}

for(corpus in corpora)
{
  with(subset(relc_surpr, Corpus == corpus), 
       qqPlot(MeanBiSurprWORD[Position == "insitu"]))
  with(subset(relc_surpr, Corpus == corpus), 
       qqPlot(MeanBiSurprWORD[Position == "extrap"]))
}

#Check homogeneity of variances
for(corpus in corpora)
{
  print(var.test(MeanBiSurprXPOS ~ Position, 
                 data = subset(relc_surpr, Corpus == corpus)))
  print(var.test(MeanBiSurprWORD ~ Position, 
                 data = subset(relc_surpr, Corpus == corpus)))
  
}

for(corpus in corpora)
{
  variance <- var.test(MeanBiSurprXPOS ~ Position, 
                       data = subset(relc_surpr, Corpus == corpus))$p.value
  if(variance > 0.05)
  {
    homogen_variance <- "yes"
    test <- t.test(MeanBiSurprXPOS ~ Position, 
                   data = subset(relc_surpr, Corpus == corpus),
                   paired=F,
                   var.equal=T)
  }
  else {
    homogen_variance <- "no"
    test <- t.test(MeanBiSurprXPOS ~ Position, 
                   data = subset(relc_surpr, Corpus == corpus),
                   paired=F,
                   var.equal=F)
  }
  
  effect_size <- round(cohensD(subset(relc_surpr, 
                                      Corpus == corpus & Position == "extrap")$MeanBiSurprXPOS,
                         subset(relc_surpr, 
                                Corpus == corpus & Position == "insitu")$MeanBiSurprXPOS),
                       3)
  if(effect_size >= 0.8)
  {
    effect <- "large"
  } else if(effect_size >= 0.5)
  {
    effect <- "medium"
  } else if(effect_size >= 0.2)
  {
    effect <- "small"
  } else {
    effect <- " "
  }
  
  meanSurprInsitu <- with(subset(relc_surpr, 
                                 Corpus == corpus & Position == "insitu"),
                          mean(MeanBiSurprXPOS))
  
  meanSurprExtrap <- with(subset(relc_surpr, 
                                 Corpus == corpus & Position == "extrap"),
                          mean(MeanBiSurprXPOS))
  surprDiff <- meanSurprInsitu - meanSurprExtrap
  if(surprDiff > 0)
  {
    diff_direction <- "+"
  }
  else {
    diff_direction <- "-"
  }
  
  if(test$p.value < 0.001)
  {
    p <- "< 0.001 & ***"
    
  } else if(test$p.value < 0.01)
  {
    p <- "< 0.01 & **"
  } else if(test$p.value < 0.05)
  {
    p <- "< 0.05 & *"
  } else if(test$p.value < 0.1)
  {
    p <- "< 0.1 & ."
  } 
  else {
    p <- paste(round(test$p.value, 3), " & ", sep="")
  }
  
  if(test$p.value < 0.05 && surprDiff < 0 && effect_size >= 0.2)
  {
    hypothesis <- "\\gruen{\\checkmark}"
  }
  else if(test$p.value < 0.05 && surprDiff > 0 && effect_size >= 0.2) {
    hypothesis <- "\\rot{x}"
  }
  else {
    hypothesis <- " "
  }
  
  print(paste(corpus, 
              " & ",
              diff_direction,
              " & ",
              round(test$parameter),
              " & ",
              round(test$statistic, 3),
              " & ",
              p,
              " & ",
              round(effect_size, 2),
              " & ",
              effect,
              " & ",
              hypothesis,
              " \\",
              sep="")
       )
}

for(corpus in corpora)
{
  variance <- var.test(MeanBiSurprWORD ~ Position, 
                       data = subset(relc_surpr, Corpus == corpus))$p.value
  if(variance > 0.05)
  {
    homogen_variance <- "yes"
    test <- t.test(MeanBiSurprWORD ~ Position, 
                   data = subset(relc_surpr, Corpus == corpus),
                   paired=F,
                   var.equal=T)
  }
  else {
    homogen_variance <- "no"
    test <- t.test(MeanBiSurprWORD ~ Position, 
                   data = subset(relc_surpr, Corpus == corpus),
                   paired=F,
                   var.equal=F)
  }
  
  effect_size <- round(cohensD(subset(relc_surpr, 
                                      Corpus == corpus & Position == "extrap")$MeanBiSurprWORD,
                               subset(relc_surpr, 
                                      Corpus == corpus & Position == "insitu")$MeanBiSurprWORD),
                       3)
  if(effect_size >= 0.8)
  {
    effect <- "large"
  } else if(effect_size >= 0.5)
  {
    effect <- "medium"
  } else if(effect_size >= 0.2)
  {
    effect <- "small"
  } else {
    effect <- " "
  }
  
  meanSurprInsitu <- with(subset(relc_surpr, 
                                 Corpus == corpus & Position == "insitu"),
                          mean(MeanBiSurprWORD))
  
  meanSurprExtrap <- with(subset(relc_surpr, 
                                 Corpus == corpus & Position == "extrap"),
                          mean(MeanBiSurprWORD))
  surprDiff <- meanSurprInsitu - meanSurprExtrap
  if(surprDiff > 0)
  {
    diff_direction <- "+"
  }
  else {
    diff_direction <- "-"
  }
  
  if(test$p.value < 0.001)
  {
    p <- "< 0.001 & ***"
    
  } else if(test$p.value < 0.01)
  {
    p <- "< 0.01 & **"
  } else if(test$p.value < 0.05)
  {
    p <- "< 0.05 & *"
  } else if(test$p.value < 0.1)
  {
    p <- "< 0.1 & ."
  } 
  else {
    p <- paste(round(test$p.value, 3), " & ", sep="")
  }
  
  if(test$p.value < 0.05 && surprDiff < 0 && effect_size >= 0.2)
  {
    hypothesis <- "\\gruen{\\checkmark}"
  }
  else if(test$p.value < 0.05 && surprDiff > 0 && effect_size >= 0.2) {
    hypothesis <- "\\rot{x}"
  }
  else {
    hypothesis <- " "
  }
  
  print(paste(corpus, 
              " & ",
              diff_direction,
              " & ",
              round(test$parameter),
              " & ",
              round(test$statistic, 3),
              " & ",
              p,
              " & ",
              round(effect_size, 2),
              " & ",
              effect,
              " & ",
              hypothesis,
              " \\",
              sep="")
  )
}


##########################
##########################
# Tests for DORM words

# Read dorm data
dorm <- read.table(file="eval/dorm/dorm_results.csv",
                    sep="\t", 
                    header=TRUE, 
                    na.strings=c("NA"))

dorm <- merge(dorm, meta, by="Filename", all.x=TRUE)

#Remove double corpus column
dorm <- subset(dorm, select=-Corpus.y)
dorm <- rename(dorm, Corpus = Corpus.x)

#Check normality
for(corpus in corpora)
{
  with(subset(dorm, Corpus == corpus), qqPlot(DORMdiffXPOS))
}

for(corpus in corpora)
{
  with(subset(dorm, Corpus == corpus), qqPlot(DORMdiffWORD))
}

for(corpus in corpora)
{
  test <- t.test(subset(dorm, Corpus == corpus)$DORMdiffXPOS,
                 mu = 0,
                 alternative = "two.sided")
  
  effect_size <- round(cohensD(subset(dorm, 
                                      Corpus == corpus)$DORMdiffXPOS,
                               mu = 0),
                       3)
  if(effect_size >= 0.8)
  {
    effect <- "large"
  } else if(effect_size >= 0.5)
  {
    effect <- "medium"
  } else if(effect_size >= 0.2)
  {
    effect <- "small"
  } else {
    effect <- " "
  }
  
  meanDORMdiff <- with(subset(dorm, Corpus == corpus),
                          mean(DORMdiffXPOS))
  if(meanDORMdiff > 0)
  {
    diff_direction <- "+"
  }
  else {
    diff_direction <- "-"
  }
  
  if(test$p.value < 0.001)
  {
    p <- "< 0.001 & ***"
    
  } else if(test$p.value < 0.01)
  {
    p <- "< 0.01 & **"
  } else if(test$p.value < 0.05)
  {
    p <- "< 0.05 & *"
  } else if(test$p.value < 0.1)
  {
    p <- "< 0.1 & ."
  } 
  else {
    p <- paste(round(test$p.value, 3), " & ", sep="")
  }
  
  if(test$p.value < 0.05 && meanDORMdiff < 0 && effect_size >= 0.2)
  {
    hypothesis <- "\\gruen{\\checkmark}"
  }
  else if(test$p.value < 0.05 && meanDORMdiff > 0 && effect_size >= 0.2) {
    hypothesis <- "\\rot{x}"
  } else {
    hypothesis <- " "
  }
  
  print(paste(corpus, 
              " & ",
              diff_direction,
              " & ",
              round(test$parameter),
              " & ",
              round(test$statistic, 3),
              " & ",
              p,
              " & ",
              round(effect_size, 2),
              " & ",
              effect,
              " & ",
              hypothesis,
              " \\",
              sep="")
  )
}

for(corpus in corpora)
{
  test <- t.test(subset(dorm, Corpus == corpus)$DORMdiffWORD,
                 mu = 0,
                 alternative = "two.sided")
  
  effect_size <- round(cohensD(subset(dorm, 
                                      Corpus == corpus)$DORMdiffWORD,
                               mu = 0),
                       3)
  if(effect_size >= 0.8)
  {
    effect <- "large"
  } else if(effect_size >= 0.5)
  {
    effect <- "medium"
  } else if(effect_size >= 0.2)
  {
    effect <- "small"
  } else {
    effect <- " "
  }
  
  meanDORMdiff <- with(subset(dorm, Corpus == corpus),
                       mean(DORMdiffWORD))
  if(meanDORMdiff > 0)
  {
    diff_direction <- "+"
  }
  else {
    diff_direction <- "-"
  }
  
  if(test$p.value < 0.001)
  {
    p <- "< 0.001 & ***"
    
  } else if(test$p.value < 0.01)
  {
    p <- "< 0.01 & **"
  } else if(test$p.value < 0.05)
  {
    p <- "< 0.05 & *"
  } else if(test$p.value < 0.1)
  {
    p <- "< 0.1 & ."
  } 
  else {
    p <- paste(round(test$p.value, 3), " & ", sep="")
  }
  
  if(test$p.value < 0.05 && meanDORMdiff < 0 && effect_size >= 0.2)
  {
    hypothesis <- "\\gruen{\\checkmark}"
  }
  else if(test$p.value < 0.05 && meanDORMdiff > 0 && effect_size >= 0.2) {
    hypothesis <- "\\rot{x}"
  } else {
    hypothesis <- " "
  }
  
  print(paste(corpus, 
              " & ",
              diff_direction,
              " & ",
              round(test$parameter),
              " & ",
              round(test$statistic, 3),
              " & ",
              p,
              " & ",
              round(effect_size, 2),
              " & ",
              effect,
              " & ",
              hypothesis,
              " \\",
              sep="")
  )
}

##########################
##########################
# Tests for DORM constituents

# Read dorm data
dorm <- read.table(file="eval/dorm/dorm_results_constituents_relc.csv",
                   sep="\t", 
                   header=TRUE, 
                   na.strings=c("NA"))

dorm <- merge(dorm, meta, by="Filename", all.x=TRUE)

#Remove double corpus column
dorm <- subset(dorm, select=-Corpus.y)
dorm <- rename(dorm, Corpus = Corpus.x)

#Check normality
for(corpus in corpora)
{
  with(subset(dorm, Corpus == corpus), qqPlot(DORMdiffXPOS))
}

for(corpus in corpora)
{
  with(subset(dorm, Corpus == corpus), qqPlot(DORMdiffWORD))
}


for(corpus in corpora)
{
  test <- t.test(subset(dorm, Corpus == corpus)$DORMdiffXPOS,
                 mu = 0,
                 alternative = "two.sided")
  
  effect_size <- round(cohensD(subset(dorm, 
                                      Corpus == corpus)$DORMdiffXPOS,
                               mu = 0),
                       3)
  if(effect_size >= 0.8)
  {
    effect <- "large"
  } else if(effect_size >= 0.5)
  {
    effect <- "medium"
  } else if(effect_size >= 0.2)
  {
    effect <- "small"
  } else {
    effect <- " "
  }
  
  meanDORMdiff <- with(subset(dorm, Corpus == corpus),
                       mean(DORMdiffXPOS))
  if(meanDORMdiff > 0)
  {
    diff_direction <- "+"
  }
  else {
    diff_direction <- "-"
  }
  
  if(test$p.value < 0.001)
  {
    p <- "< 0.001 & ***"
    
  } else if(test$p.value < 0.01)
  {
    p <- "< 0.01 & **"
  } else if(test$p.value < 0.05)
  {
    p <- "< 0.05 & *"
  } else if(test$p.value < 0.1)
  {
    p <- "< 0.1 & ."
  } 
  else {
    p <- paste(round(test$p.value, 3), " & ", sep="")
  }
  
  if(test$p.value < 0.05 && meanDORMdiff < 0 && effect_size >= 0.2)
  {
    hypothesis <- "\\gruen{\\checkmark}"
  }
  else if(test$p.value < 0.05 && meanDORMdiff > 0 && effect_size >= 0.2) {
    hypothesis <- "\\rot{x}"
  } else {
    hypothesis <- " "
  }
  
  print(paste(corpus, 
              " & ",
              diff_direction,
              " & ",
              round(test$parameter),
              " & ",
              round(test$statistic, 3),
              " & ",
              p,
              " & ",
              round(effect_size, 2),
              " & ",
              effect,
              " & ",
              hypothesis,
              " \\",
              sep="")
  )
}

for(corpus in corpora)
{
  test <- t.test(subset(dorm, Corpus == corpus)$DORMdiffWORD,
                 mu = 0,
                 alternative = "two.sided")
  
  effect_size <- round(cohensD(subset(dorm, 
                                      Corpus == corpus)$DORMdiffWORD,
                               mu = 0),
                       3)
  if(effect_size >= 0.8)
  {
    effect <- "large"
  } else if(effect_size >= 0.5)
  {
    effect <- "medium"
  } else if(effect_size >= 0.2)
  {
    effect <- "small"
  } else {
    effect <- " "
  }
  
  meanDORMdiff <- with(subset(dorm, Corpus == corpus),
                       mean(DORMdiffWORD))
  if(meanDORMdiff > 0)
  {
    diff_direction <- "+"
  }
  else {
    diff_direction <- "-"
  }
  
  if(test$p.value < 0.001)
  {
    p <- "< 0.001 & ***"
    
  } else if(test$p.value < 0.01)
  {
    p <- "< 0.01 & **"
  } else if(test$p.value < 0.05)
  {
    p <- "< 0.05 & *"
  } else if(test$p.value < 0.1)
  {
    p <- "< 0.1 & ."
  } 
  else {
    p <- paste(round(test$p.value, 3), " & ", sep="")
  }
  
  if(test$p.value < 0.05 && meanDORMdiff < 0 && effect_size >= 0.2)
  {
    hypothesis <- "\\gruen{\\checkmark}"
  }
  else if(test$p.value < 0.05 && meanDORMdiff > 0 && effect_size >= 0.2) {
    hypothesis <- "\\rot{x}"
  } else {
    hypothesis <- " "
  }
  
  print(paste(corpus, 
              " & ",
              diff_direction,
              " & ",
              round(test$parameter),
              " & ",
              round(test$statistic, 3),
              " & ",
              p,
              " & ",
              round(effect_size, 2),
              " & ",
              effect,
              " & ",
              hypothesis,
              " \\",
              sep="")
  )
}
