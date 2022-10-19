#Import
library(ggplot2)
library(stringr)
library(tidyr)

for(annotation in c("brackets", "chunks", "topf", "phrases"))
{
  
  #Read data
  mydata <- read.table(file=paste("eval/tables/data/tab_", 
                                  annotation, "_label_dist.csv", sep=""), 
                       sep="\t", header=TRUE)
  
  #Rename corpora
  mydata$Corpus <- str_replace(mydata$Corpus, "_test", "")
  mydata$Corpus <- str_replace(mydata$Corpus, "TuebaDZ", "TüBa-D/Z")
  mydata$Corpus <- str_replace(mydata$Corpus, "TuebaDS", "Spoken")
  
  #Convert corpus name to factor
  levels = c("TüBa-D/Z", "Tiger", "Spoken", "Modern", 
             "Mercurius", "ReF.UP", "HIPKON", "DTA")
  mydata$Corpus <- factor(mydata$Corpus, levels=levels)
  
  #Convert labels to factor
  if(annotation=="brackets")
  {
    levels <- c("LK", "RK")
    colors <- c("#00457eff", "#9fce22ff")
  }
  else if(annotation == "chunks") 
  {
    levels <- c("NC", "PC", "AC", "ADVC", "sNC", "sPC")
    colors <- c("#00457eff", "#c5e5ffff", 
                "#548235ff", "#9fce22ff", 
                "#7f7f7fff", "#d9d9d9ff")
  }
  else if(annotation == "topf") 
  {
    levels <- c("KOORD", "LV", "VF", "LK", "MF", "RK", "NF")
    colors <- c("#7f7f7fff", "#0d0d0dff", "#d9d9d9ff",
                "#00457eff", "#c5e5ffff",
                "#548235ff", "#9fce22ff")
  }
  else if(annotation == "phrases") 
  {
    levels <- c("NP", "PP", "AP", "ADVP")
    colors <- c("#00457eff", "#c5e5ffff", 
                "#548235ff", "#9fce22ff")
  }
  mydata$Label <- factor(mydata$Label, levels=levels)
  
  #Create plot
  p <- ggplot(mydata, aes(fill=Label, y=Perc, x=Corpus)) + 
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
  if(annotation == "chunks" | annotation == "phrases") width <- 25
  else width <- 20
  ggsave(paste("eval/plots/plt_", 
               annotation, "_labels.png", sep=""), 
         device="png", width=width, height=20, units="cm", dpi = 300)
}

###############
# EXTRAPOSITION

#Read data
mydata <- read.table(file="eval/tables/data/tab_extrap_label_dist.csv",
                     sep="\t", header=TRUE)

#Rename corpora
mydata$Corpus <- str_replace(mydata$Corpus, "_test", "")
mydata$Corpus <- str_replace(mydata$Corpus, "TuebaDZ", "TüBa-D/Z")
mydata$Corpus <- str_replace(mydata$Corpus, "TuebaDS", "Spoken")

#Convert corpus name to factor
levels = c("TüBa-D/Z", "Tiger", "Spoken", "Modern", 
           "Mercurius", "ReF.UP", "HIPKON", "DTA")
mydata$Corpus <- factor(mydata$Corpus, levels=levels)

#Split label and position
mydata <- separate(data = mydata, col = Label, into = c('Label', 'Position'))

#Convert labels and positions to factor
mydata$Label <- factor(mydata$Label, levels=c("NP", "PP", "AP", "ADVP", "RELC"))
mydata$Position <- factor(mydata$Position, levels=c("insitu", "ambig", "extrap"))

colors <- c("#00457eff", "#d9d9d9ff", "#9fce22ff")

#Create plot
p <- ggplot(mydata, aes(fill=Position, y=Perc, x=Label)) + 
  facet_wrap( ~ Corpus, ncol=2, strip.position = "bottom") +
  ylab("Proportion") +
  theme_minimal() +
  scale_fill_manual(values=colors) +
  scale_x_discrete(position = "top") +
  scale_y_continuous(labels = c("0%", "25%", "50%", "75%", "100%"))+
  geom_bar(position="fill", stat="identity", width=0.5)+
  theme(legend.position = c(0.6, 0.85),
        legend.background = element_rect(fill="white"),
        axis.title.x = element_text(size = 14, family="serif"),
        axis.text.x = element_text(size = 10, family="serif"),
        axis.title.y = element_text(size = 14, family="serif"), 
        axis.text.y = element_text(size = 10, family="serif"),
        legend.title = element_text(size = 14, family="serif"),
        legend.text = element_text(size = 12, family="serif"),
        strip.text = element_text(size = 12, family="serif"),
        strip.background=element_rect(colour="black",
                                      fill="#d9d9d9ff"),
        panel.border=element_rect(fill=NA, color="black"))
p

#Save plot
ggsave(paste("eval/plots/plt_extrap_labels.png", sep=""), 
       device="png", width=20, height=20, units="cm", dpi = 300)
