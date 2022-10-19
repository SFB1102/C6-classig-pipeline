#Import
library(ggplot2)
library(stringr)
library(tidyr)

for(annotation in c("brackets", "chunks", "topf", "phrases", 
                    "extrap", "antec", "relc"))
{
  
  #Read data
  mydata <- read.table(file=paste("eval/tables/", 
                                  annotation, "/tab_error_types.csv", sep=""), 
                       sep="\t", header=TRUE)
  
  #Rename corpora
  mydata$Corpus <- str_replace(mydata$Corpus, "TuebaDZ", "TüBa-D/Z")
  mydata$Corpus <- str_replace(mydata$Corpus, "TuebaDS", "Spoken")
  
  #Convert corpus name to factor
  levels = c("TüBa-D/Z", "Tiger", "Spoken", "Modern", 
             "Mercurius", "ReF.UP", "HIPKON", "DTA")
  mydata$Corpus <- factor(mydata$Corpus, levels=levels)
  
  
  #Convert errors to factor
  if(annotation == "antec")
  {
    levels <- c("FP", "BEright", "BE", "IL", "FN")
    colors <- c("#548235ff", "#9fce22ff", 
                "#7f7f7fff", "#c5e5ffff", "#00457eff")
  }
  else if(annotation == "relc")
  {
    levels <- c("FP", "BEs", "BEl", "BEo", "FN")
    colors <- c("#c5e5ffff", "#00457eff", 
                "#9fce22ff", "#0d0d0dff", "#548235ff")
  }
  else if(annotation == "brackets")
  {
    levels <- c("FP", "LE", "BEs", "BEl", "BEo", "LBE", "FN")
    colors <- c("#9fce22ff", "#548235ff", "#d9d9d9ff", "#7f7f7fff", 
                "#0d0d0dff", "#c5e5ffff", "#00457eff")
  }
  else
  {
    levels <- c("FP", "LE", "BEs", "BEl", "BEo", "LBE", "FN")
    colors <- c("#7f7f7fff", "#d9d9d9ff",
                "#00457eff", "#c5e5ffff", 
                "#0d0d0dff", 
                "#9fce22ff", "#548235ff")
  }
  
  mydata$ErrorType <- factor(mydata$ErrorType, levels=levels)
  
  #Create plot
  p <- ggplot(mydata, aes(fill=ErrorType, y=Perc, x=Corpus)) + 
       ylab("Proportion") +
       theme_minimal() +
       scale_fill_manual(values=colors) +
       scale_y_continuous(labels = c("0%", "25%", "50%", "75%", "100%"))+
       geom_bar(position="fill", stat="identity", width=0.5)+
       theme(axis.title.x = element_text(size = 16, family="serif"),
             axis.text.x = element_text(size = 14, family="serif"),
             axis.title.y = element_text(size = 16, family="serif"), 
             axis.text.y = element_text(size = 14, family="serif"),
             legend.title = element_text(size = 16, family="serif"),
             legend.text = element_text(size = 14, family="serif"))
  p
  
  #Save plot
  if(annotation == "phrases") width <- 25
  else width <- 20
  ggsave(paste("eval/plots/plt_", 
               annotation, "_error_types.png", sep=""), 
         device="png", width=width, height=20, units="cm", dpi = 300)
}

