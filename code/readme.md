``analysis.py``: can be used to analyze the [arxiv-0623 dataset](../data/) similarly as in the paper
``arxiv_wordcloud.py``: script that loads an excelfile with the top n papers and builds a wordcloud from their titles and abstracts using key word search, lemmatization and pos tagging
``scrape.py``: script that uses the bulk API of Semantic Scholar to query the citation counts of recently released Arxiv papers. The raw data is stored in a separate files. Whenever you want to regenerate, these file needs to be deleted: papers.shelf.\* . Additionally, the script will create an xlsx file from the raw data with one additional row that shows the normalized citation count per week.

When running these scripts, also consider the comments in the files. 
