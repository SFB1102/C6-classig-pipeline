library(ggplot2)
library(tidyr)
library(stringr)

######################

# Targ/Sys	Lab1	Lab2	Lab3	...	∅ (FN)
# Lab1      count	count	count	... count
# Lab2      count	count	count	... count
# Lab3      count	count	count	... count
# ...       ...   ...   ...   ... ...
# ∅ (FP)    count	count	count	... count

for(annotation in c("brackets", "chunks", "topf", "phrases", "extrap"))
{
  
  #Read data
  mydata <- read.table(file=paste("eval/tables/", 
                                  annotation, "/confmatrix.csv", sep=""), 
                       sep="\t", header=TRUE, encoding="UTF-8")
  
  #Rename FP/FN
  mydata$Target <- str_replace(mydata$Target, "_", "∅ (FP)")
  mydata$System <- str_replace(mydata$System, "_", "∅ (FN)")
  
  #Convert corpus name to factor
  levels = c("TüBa-D/Z", "Tiger", "Spoken", "Modern", 
             "Mercurius", "ReF.UP", "HIPKON", "DTA")
  mydata$Corpus <- factor(mydata$Corpus, levels=levels)
  
  #Remove nonsense bottom right tile
  mydata$Freq[mydata$Target == "∅ (FP)" & mydata$System == "∅ (FN)"] <- ""
  
  #Set labels
  if(annotation=="brackets")
  {
    labels <- c("LK", "RK")
    width <- 25
    height <- 15
    cols <- 3
  }
  else if(annotation == "chunks") 
  {
    labels <- c("NC", "PC", "AC", "ADVC", "sNC", "sPC")
    width <- 25
    height <- 25
    cols <- 2
  }
  else if(annotation == "topf") 
  {
    labels <- c("KOORD", "LV", "VF", "LK", "MF", "RK", "NF")
    width <- 25
    height <- 25
    cols <- 2
  }
  else if(annotation == "phrases") 
  {
    labels <- c("NP", "PP", "AP", "ADVP")
    width <- 20
    height <- 25
    cols <- 2
  }
  else if(annotation == "extrap")
  {
    labels <- c("NP-insitu", "NP-extrap", "PP-insitu", "PP-extrap",
                "AP-insitu", "AP-extrap", "ADVP-insitu", "ADVP-extrap", 
                "RELC-insitu", "RELC-ambig", "RELC-extrap")
    width <- 40
    height <- 50
    cols <- 1
  }
  
  #Turn labels into factors
  mydata$Target <- factor(mydata$Target, levels=append(labels, c("∅ (FP)")))
  mydata$System <- factor(mydata$System, levels=append(labels, c("∅ (FN)")))

  #Create plot
  ggplot(mydata, 
         aes(x=System, 
             #reverse order of y-axis
             y=ordered(Target, levels=rev(append(labels, c("∅ (FP)")))), 
             #Color by proportion
             fill=Perc)) +
    #One facet per corpus with grey box at the bottom
    facet_wrap( ~ Corpus, ncol=cols, strip.position = "bottom") +
    #Heat map
    geom_tile() +
    theme_minimal() +
    ylab("Target label") +
    xlab("System label") +
    scale_x_discrete(position = "top", labels=append(labels, c("∅ (FN)"))) +
    #Reverse order of y-labels, too
    scale_y_discrete(labels=rev(append(labels, c("∅ (FP)")))) +
    theme(legend.position = "none", 
          axis.title.x = element_text(size = 16, family="serif"),
          axis.text.x = element_text(size = 14, family="serif"),
          axis.title.y = element_text(size = 16, family="serif"), 
          axis.text.y = element_text(size = 14, family="serif"),
          strip.text = element_text(size = 12, family="serif"),
          strip.background=element_rect(colour="black",
                                        fill="#d9d9d9ff"),
          panel.border=element_rect(fill=NA, color="black"),
          strip.placement = "outside") +
    #Print frequency on tiles
    geom_text(aes(label = Freq), size=6, family="serif") +
    #From white to red
    scale_fill_gradient(low = "white", high = "red", na.value = NA)
  
  ggsave(paste("eval/plots/plt_", 
               annotation, "_conf.png", sep=""), 
         device="png", width=width, height=height, units="cm", dpi = 300)

}
