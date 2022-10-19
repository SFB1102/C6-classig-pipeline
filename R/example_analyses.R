#Import
library(ggplot2)
library(stringr)
library(tidyr)
library(dplyr)

colors_blue_gray_green <- c("#00457eff", "#d9d9d9ff", "#9fce22ff")
colors_blue_black_green <- c("#00457eff", "black", "#9fce22ff")
colors_blue_green <- c("#00457eff", "#9fce22ff")

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

#Order positions from insitu to extraposed
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

#########################
#Join RelC results and meta data

#Left join of tables on filenames
#Keep all rows of relcs and add meta info
table <- merge(relcs, meta, by="Filename", all.x=TRUE)

#Remove double corpus column
table <- subset(table, select=-Corpus.y)
table <- rename(table, Corpus = Corpus.x)

#########################
#########################
#(i) Factor: time

#Get proportion of insitu/ambig/extrap per year
status_by_year <- table %>% group_by(Year) %>% count(Status)
status_by_year <- status_by_year %>% group_by(Year, Status) %>% 
                  summarise(n = sum(n)) %>% mutate(percentage = n / sum(n))

#LOESS plot status by year
ggplot(status_by_year, aes(x=Year, y=percentage, group=Status, color=Status)) +
  labs(y="Proportion of RelCs", x="Year", group="Position", color="Position") +
  theme_minimal() +
  scale_color_manual(values=colors_blue_black_green) +
  scale_y_continuous(labels = scales::percent_format(accuracy=1)) +
  coord_cartesian(ylim = c(0, 0.6)) +
  geom_smooth(method = 'loess', formula = 'y ~ x', size=1.25) +
  theme(legend.position = c(0.9, 0.20),
        legend.background = element_rect(fill="white"),
        axis.title.x = element_text(size = 16, family="serif", margin=margin(t=10)),
        axis.text.x = element_text(size = 14, family="serif"),
        axis.title.y = element_text(size = 16, family="serif", margin=margin(r=10)), 
        axis.text.y = element_text(size = 14, family="serif"),
        legend.title = element_text(size = 16, family="serif"),
        legend.text = element_text(size = 14, family="serif"))

ggsave("eval/plots/plt_position_time.png", 
       device="png", width=20, height=15, units="cm", dpi = 300)

# Only insitu and extrap
subtable <- subset(table, Status != "ambig")

#Get proportion of insitu/extrap per year
status_by_year <- subtable %>% group_by(Year) %>% count(Status)
status_by_year <- status_by_year %>% group_by(Year, Status) %>% 
                  summarise(n = sum(n)) %>% mutate(percentage = n / sum(n))

#LOESS plot status by year
ggplot(status_by_year, aes(x=Year, y=percentage, group=Status, color=Status)) +
  labs(y="Proportion of RelCs", x="Year", group="Position", color="Position") +
  theme_minimal() +
  scale_color_manual(values=colors_blue_green) +
  scale_y_continuous(labels = scales::percent_format(accuracy=1)) +
  geom_smooth(method = 'loess', formula = 'y ~ x', size=1.25) +
  theme(legend.position = c(0.9, 0.20),
        legend.background = element_rect(fill="white"),
        axis.title.x = element_text(size = 16, family="serif", margin=margin(t=10)),
        axis.text.x = element_text(size = 14, family="serif"),
        axis.title.y = element_text(size = 16, family="serif", margin=margin(r=10)), 
        axis.text.y = element_text(size = 14, family="serif"),
        legend.title = element_text(size = 16, family="serif"),
        legend.text = element_text(size = 14, family="serif"))

ggsave("eval/plots/plt_position_time_unambiguous.png", 
       device="png", width=20, height=15, units="cm", dpi = 300)

#Get proportion of insitu/ambig/extrap per year and register
status_by_year_and_register <- table %>% group_by(Year, Register) %>% count(Status)
status_by_year_and_register <- status_by_year_and_register %>% 
                               group_by(Year, Register, Status) %>% 
                               summarise(n = sum(n)) %>% 
                               mutate(percentage = n / sum(n))

#LOESS plot status by year and register
ggplot(status_by_year_and_register, aes(x=Year, y=percentage, group=Status, color=Status)) +
  facet_wrap( ~ Register, ncol=3, strip.position = "top") +
  labs(y="Proportion of RelCs", x="Year", group="Position", color="Position") +
  theme_minimal() +
  scale_y_continuous(labels = scales::percent_format(accuracy=1))
  coord_cartesian(ylim = c(0, 0.7)) +
  scale_color_manual(values=colors_blue_black_green) +
  geom_smooth(method = 'loess', formula = 'y ~ x', size=1.25) +
  theme(legend.position = "top",
        axis.title.x = element_text(size = 16, family="serif", margin=margin(t=10)),
        axis.text.x = element_text(size = 14, family="serif"),
        axis.title.y = element_text(size = 16, family="serif", margin=margin(r=10)), 
        axis.text.y = element_text(size = 14, family="serif"),
        legend.title = element_text(size = 16, family="serif"),
        legend.text = element_text(size = 14, family="serif"),
        plot.margin = margin(l=10,r=10),
        strip.text = element_text(size = 14, family="serif"),
        strip.background=element_rect(colour="black",
                                      fill="#d9d9d9ff"),
        panel.border=element_rect(fill=NA, color="black"))

ggsave("eval/plots/plt_position_time_register.png", 
       device="png", width=20, height=20, units="cm", dpi = 300)

#########################
#########################
#(ii) Factor: length

#Boxplot length by position
ggplot(table, aes(x=Status, y=Length, fill=Status)) +
  geom_boxplot(outlier.shape=NA) + 
  labs(y="RelC Length (Words)", x="RelC Position", group="Position", color="Position") +
  theme_minimal() +
  scale_fill_manual(values=colors_blue_gray_green) +
  coord_cartesian(ylim = c(0, 30)) +
  stat_summary(fun.y="mean", geom = "point", shape = 21, size = 3, 
               color = "black", fill="white") +
  theme(legend.position = "None",
        axis.title.x = element_text(size = 16, family="serif", margin=margin(t=10)),
        axis.text.x = element_text(size = 14, family="serif"),
        axis.title.y = element_text(size = 16, family="serif", margin=margin(r=10)), 
        axis.text.y = element_text(size = 14, family="serif"),
        legend.title = element_text(size = 16, family="serif"),
        legend.text = element_text(size = 14, family="serif"))

ggsave("eval/plots/plt_position_length.png", 
       device="png", width=15, height=15, units="cm", dpi = 300)

#Calculate mean, median and standard deviation for registers
group_by(table, Register) %>%
  summarise(
    count = n(),
    mean = mean(Length, na.rm = TRUE),
    median = median(Length, na.rm = TRUE),
    sd = sd(Length, na.rm = TRUE)
  )

#Boxplot Length by Register
ggplot(table, aes(x=Register, y=Length, fill=Register)) +
  geom_boxplot(outlier.shape=NA) + 
  labs(y="RelC Length (Words)", x="Register") +
  theme_minimal() +
  coord_cartesian(ylim = c(0, 30)) +
  stat_summary(fun.y="mean", geom = "point", shape = 21, size = 3, 
               color = "black", fill="white") +
  theme(legend.position = "None",
        axis.title.x = element_text(size = 16, family="serif", margin=margin(t=10)),
        axis.text.x = element_text(size = 14, family="serif"),
        axis.title.y = element_text(size = 16, family="serif", margin=margin(r=10)), 
        axis.text.y = element_text(size = 14, family="serif"),
        legend.title = element_text(size = 16, family="serif"),
        legend.text = element_text(size = 14, family="serif"))

ggsave("eval/plots/plt_length_register.png", 
       device="png", width=15, height=15, units="cm", dpi = 300)

#Mean and median length per year
length_by_time <- table %>% group_by(Year) %>% 
                  summarise_at(vars(Length), list(AvgLen = mean, Median = median))

#LOESS plot length over time
ggplot(length_by_time, aes(x=Year)) +
  geom_smooth(aes(y=AvgLen, color="Mean"), method = 'loess', 
              formula = 'y ~ x', size=1.25) +
  geom_smooth(aes(y=Median, color="Median"), method = 'loess', 
              formula = 'y ~ x', size=1.25, linetype=2) +
  ylab("RelC Length (Words)") +
  theme_minimal() +
  coord_cartesian(ylim = c(0, 15)) +
  scale_color_manual(name='',
                     breaks=c('Mean', 'Median'),
                     values=c('Mean'='black', 'Median'='#7e7474')) +
  theme(legend.position = c(0.85, 0.95),
        axis.title.x = element_blank(),
        axis.text.x = element_text(size = 14, family="serif"),
        axis.title.y = element_text(size = 16, family="serif", margin=margin(r=10)), 
        axis.text.y = element_text(size = 14, family="serif"),
        legend.title = element_text(size = 16, family="serif"),
        legend.text = element_text(size = 14, family="serif"))

ggsave("eval/plots/plt_length_time.png", 
       device="png", width=15, height=15, units="cm", dpi = 300)

#Mean and median length per year and register
length_by_time_and_register <- table %>% group_by(Register, Year) %>% 
                               summarise_at(vars(Length), 
                                            list(AvgLen = mean, Median = median))

#LOESS plot length over time with register facets
ggplot(length_by_time_and_register, aes(x=Year)) +
  facet_wrap(. ~ Register) +
  geom_smooth(aes(y=AvgLen, color="Mean"), method = 'loess', 
              formula = 'y ~ x', size=1.25) +
  geom_smooth(aes(y=Median, color="Median"), method = 'loess', 
              formula = 'y ~ x', size=1.25, linetype=2) +
  ylab("RelC Length (Words)") +
  theme_minimal() +
  coord_cartesian(ylim = c(0, 20)) +
  scale_color_manual(name='',
                     breaks=c('Mean', 'Median'),
                     values=c('Mean'='black', 'Median'='#7e7474')) +
  theme(legend.position = "top",
        axis.title.x = element_text(size = 16, family="serif", margin=margin(t=10)),
        axis.text.x = element_text(size = 14, family="serif"),
        axis.title.y = element_text(size = 16, family="serif", margin=margin(r=10)), 
        axis.text.y = element_text(size = 14, family="serif"),
        legend.title = element_text(size = 16, family="serif"),
        legend.text = element_text(size = 14, family="serif"),
        plot.margin = margin(l=10,r=10),
        strip.text = element_text(size = 14, family="serif"),
        strip.background=element_rect(colour="black",
                                      fill="#d9d9d9ff"),
        panel.border=element_rect(fill=NA, color="black"))

ggsave("eval/plots/plt_length_time_register.png", 
       device="png", width=15, height=15, units="cm", dpi = 300)

#Mean and median length by year and position
length_by_time_and_status <- table %>% group_by(Status, Year) %>% 
                             summarise_at(vars(Length), 
                                          list(AvgLen = mean, Median = median))

#LOESS plot length by time and position
ggplot(length_by_time_and_status, aes(x=Year, color=Status)) +
  facet_wrap(.~Status) +
  geom_smooth(aes(y=AvgLen), method = 'loess', 
              formula = 'y ~ x', size=1.25) +
  geom_smooth(aes(y=Median), method = 'loess', 
              formula = 'y ~ x', size=1.25, linetype=2) +
  ylab("RelC Length (Words)") +
  theme_minimal() +
  coord_cartesian(ylim = c(0, 16)) +
  scale_color_manual(values=colors_blue_black_green) +
  geom_text(aes(x=1900, y=6.5, label="Median"), color="black") +
  geom_text(aes(x=1350, y=11, label="Mean"), color="black") +
  theme(legend.position = "None",
        axis.title.x = element_text(size = 16, family="serif", margin=margin(t=10)),
        axis.text.x = element_text(size = 14, family="serif"),
        axis.title.y = element_text(size = 16, family="serif", margin=margin(r=10)), 
        axis.text.y = element_text(size = 14, family="serif"),
        legend.title = element_text(size = 16, family="serif"),
        legend.text = element_text(size = 14, family="serif"),
        plot.margin = margin(l=10,r=10,t=10),
        strip.text = element_text(size = 14, family="serif"),
        strip.background=element_rect(colour="black",
                                      fill="#d9d9d9ff"),
        panel.border=element_rect(fill=NA, color="black"))

ggsave("eval/plots/plt_length_time_status_facet.png", 
       device="png", width=20, height=15, units="cm", dpi = 300)

#########################
#########################
#(iii) Factor: orality

#Read orality data
orality_scaled <- read.table(file="eval/orality/all_result_scaled.csv",
                             sep="\t",
                             header=TRUE,
                             encoding="utf-8")
orality <- read.table(file="eval/orality/all_result.csv",
                      sep="\t",
                      header=TRUE,
                      encoding="utf-8")

#Append scores to unscaled data for plotting
orality$SCORE <- orality_scaled$SCORE

#Merge orality and meta data
orality_time <- merge(meta, orality, by.x="Filename", by.y="file")
orality_time <- subset(orality_time, select=-corpus)

#Jitter plot orality score by register
ggplot(orality_time, aes(color=Register, x=Register, y=SCORE)) +
  geom_jitter(size=3, alpha=0.5) +
  labs(y="Orality Score", x="Register") +
  theme_minimal() +
  theme(legend.position = "None",
        axis.title.x = element_text(size = 16, family="serif", margin=margin(t=10)),
        axis.text.x = element_text(size = 14, family="serif"),
        axis.title.y = element_text(size = 16, family="serif", margin=margin(r=10)), 
        axis.text.y = element_text(size = 14, family="serif"))

ggsave("eval/plots/plt_orality_register.png", 
       device="png", width=20, height=15, units="cm", dpi = 300)

#Scatter plot orality over time with LOESS line per Register
ggplot(orality_time, aes(x=Year, y=SCORE, color=Register, fill=Register)) +
  geom_point(alpha=0.3, size=3) +
  geom_smooth(method = 'loess', formula = 'y ~ x', span=0.9, se=F, 
              color="black", alpha=0.7) +
  facet_wrap(.~Register) +
  labs(y="Orality Score", x="Year") +
  theme_minimal() +
  theme(legend.position = "None",
        axis.title.x = element_text(size = 16, family="serif", margin=margin(t=10)),
        axis.text.x = element_text(size = 14, family="serif"),
        axis.title.y = element_text(size = 16, family="serif", margin=margin(r=10)), 
        axis.text.y = element_text(size = 14, family="serif"),
        legend.title = element_text(size = 16, family="serif"),
        legend.text = element_text(size = 14, family="serif"),
        strip.text = element_text(size = 14, family="serif"),
        strip.background=element_rect(colour="black",
                                      fill="#d9d9d9ff"),
        panel.border=element_rect(fill=NA, color="black"))

ggsave("eval/plots/plt_orality_time_register.png", 
       device="png", width=15, height=15, units="cm", dpi = 300)

#Merge orality and relc data
orality_relc <- merge(relcs, orality, by.x="Filename", by.y="file")
orality_relc <- subset(orality_relc, select=-corpus)

#Boxplot orality by position
ggplot(orality_relc, aes(x=Status, y=SCORE, fill=Status)) +
  geom_boxplot(outlier.shape=NA) + 
  labs(y="Orality Score", x="RelC Position", group="Position", color="Position") +
  theme_minimal() +
  scale_fill_manual(values=colors_blue_gray_green) +
  coord_cartesian(ylim = c(-0.5, 1)) +
  stat_summary(fun.y="mean", geom = "point", shape = 21, size = 3, 
               color = "black", fill="white") +
  theme(legend.position = "None",
        axis.title.x = element_text(size = 16, family="serif", margin=margin(t=10)),
        axis.text.x = element_text(size = 14, family="serif"),
        axis.title.y = element_text(size = 16, family="serif", margin=margin(r=10)), 
        axis.text.y = element_text(size = 14, family="serif"),
        legend.title = element_text(size = 16, family="serif"),
        legend.text = element_text(size = 14, family="serif"))

ggsave("eval/plots/plt_position_orality_boxplot.png", 
       device="png", width=15, height=15, units="cm", dpi = 300)

#Bin orality (size 0.1)
breaks_orality <- seq(-1, 1.3, by=0.1)
bins_orality <- seq(-1, 1.2, by=0.1)
orality_relc <- orality_relc %>% 
                mutate(Orality_Bin = cut(SCORE, 
                                         breaks=breaks_orality,
                                         labels=bins_orality,
                                         right=FALSE))
orality_relc$Orality_Bin <- as.numeric(as.character(orality_relc$Orality_Bin))

#Proportion of positions by orality bin
status_by_orality <- orality_relc %>% group_by(Orality_Bin) %>% count(Status)
status_by_orality <- status_by_orality %>% group_by(Orality_Bin, Status) %>% 
                     summarise(n = sum(n)) %>% mutate(percentage = n / sum(n))

#LOESS plot position by orality bin
ggplot(status_by_orality, aes(x=Orality_Bin, y=percentage, group=Status, color=Status)) +
  labs(y="Proportion of RelCs", x="Orality Score (Bin Size 0.1)", 
       group="Position", color="Position") +
  theme_minimal() +
  geom_smooth(method = 'loess', formula = 'y ~ x', size=1.25) +
  scale_color_manual(values=colors_blue_black_green) +
  scale_y_continuous(labels = scales::percent_format(accuracy=1)) +
  coord_cartesian(ylim = c(0.2, 0.5)) +
  theme(legend.position = "top",
        axis.title.x = element_text(size = 16, family="serif", margin=margin(t=10)),
        axis.text.x = element_text(size = 14, family="serif"),
        axis.title.y = element_text(size = 16, family="serif", margin=margin(r=10)), 
        axis.text.y = element_text(size = 14, family="serif"),
        legend.title = element_text(size = 16, family="serif"),
        legend.text = element_text(size = 14, family="serif"))

ggsave("eval/plots/plt_position_orality.png", 
       device="png", width=20, height=15, units="cm", dpi = 300)

#Mean and median length by orality
length_by_orality <- orality_relc %>% group_by(Orality_Bin) %>% 
                     summarise_at(vars(Length), list(AvgLen=mean, Median=median))

#LOESS plot length by orality bin
ggplot(length_by_orality, aes(x=Orality_Bin)) +
  geom_smooth(aes(y=AvgLen, color="Mean"), method = 'loess', 
              formula = 'y ~ x', size=1.25) +
  geom_smooth(aes(y=Median, color="Median"), method = 'loess', 
              formula = 'y ~ x', size=1.25, linetype=2) +
  labs(y="RelC Length (Words)", x="Orality Score (Bin Size 0.1)") +
  theme_minimal() +
  scale_color_manual(name='',
                     breaks=c('Mean', 'Median'),
                     values=c('Mean'='black', 'Median'='#7e7474')) +
  theme(legend.position = c("0.85", "0.9"),
        axis.title.x = element_text(size = 16, family="serif", margin=margin(t=10)),
        axis.text.x = element_text(size = 14, family="serif"),
        axis.title.y = element_text(size = 16, family="serif", margin=margin(r=10)), 
        axis.text.y = element_text(size = 14, family="serif"),
        legend.title = element_text(size = 16, family="serif"),
        legend.text = element_text(size = 14, family="serif"))

ggsave("eval/plots/plt_length_orality.png", 
       device="png", width=15, height=15, units="cm", dpi = 300)
