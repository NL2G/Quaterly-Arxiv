import sys,numpy as np


# does analysis on extracted arxiv papers as described in the paper: https://arxiv.org/pdf/2308.04889.pdf

# SAMPLE usage:
# python3 analysis.py < arxiv-0623.tsv |less

cits,papers,lens = {},{},{}

#         entry_id        updated published       title   authors summary comment journal_ref     doi     primary_category        categories      links   pdf_url _raw    citationCount   WeekNumber      z-score

cats = {}
prim = {}
weeks = {}
weeks_cits = {}
weeks_cits_cat = {}

freq = {} #{"chatgpt":0,"llms":0}
chatgpt = 0
llms = 0
total = 0

for iline,line in enumerate(sys.stdin):
    line = line.strip()
    x = line.split("\t")
    lens[len(x)] = lens.get(len(x),0)+1
    if iline>0:
        index,entry_id,updated,published,title,authors,abstract,comment,journal_ref,doi,primary,categories,links,pdf_url_raw,_,cit_count,week,zscore = x
        if week not in freq: freq[week] = {"chatgpt":0,"llms":0,"total":0}
        freq[week]["total"] += 1
        foundChat,foundLLM = False,False
        for text in [title,abstract]:
          tt = text.lower().split()
          if "chatgpt" in tt or "chat-gpt" in tt and not foundChat: #chatgpt+=1
            freq[week]["chatgpt"] += 1
            foundChat = True
          if "llms" in tt or "large language models" in tt or "llm" in tt or "large language model" in tt and not foundLLM:
            freq[week]["llms"] += 1
            foundLLM = True
        prim[primary] = prim.get(primary,0)+1
        cit_count = int(cit_count)
        weeks_cits[week] = weeks_cits.get(week,[])+[cit_count]
        if primary not in ["cs.CL","cs.LG"]: pp = "other"
        else: pp = primary
        if pp in weeks_cits_cat:
            weeks_cits_cat[pp][week] = weeks_cits_cat[pp].get(week,[])+[cit_count]
        else:
            weeks_cits_cat[pp] = {week:[cit_count]}
    
        if week in weeks:
            weeks[week][primary] = weeks[week].get(primary,0)+1
        else:
            weeks[week] = {primary:1}


        for cat in categories[1:-1].split(","):
            try: u,v = cat.split(".")
            except ValueError:
                continue
            cat = cat.strip()[1:-1] #,title)
            cats[cat] = cats.get(cat,0)+1


print("\n## Frequency of ChatGPT and LLMs")
for week in sorted(freq):
    total = freq[week]["total"]
    start,end = week.split("/")
    start = "-".join(start.split("-")[1:])
    end = "-".join(end.split("-")[1:])
    week_simple = start+"/"+end
    print(week_simple,"%.05f"%(freq[week]["chatgpt"]/total*100),"%.05f"%(freq[week]["llms"]/total*100))


print("\n## Weekly Citation Counts")


print("\t".join(["Week","Mean","Std","Mean-CL","Mean-LG","Mean-Rest"]))
index = 0
for week in sorted(weeks_cits):
    c = weeks_cits[week]
    lst = []
    index += 1
    start,end = week.split("/")
    start = "-".join(start.split("-")[1:])
    end = "-".join(end.split("-")[1:])
    week_simple = start+"/"+end
    for cc in sorted(weeks_cits_cat):
        lst.append("%.03f"%np.mean(weeks_cits_cat[cc][week]))
    print("&\t".join([str(index),week_simple,"%.03f"%np.mean(c),"%.03f"%np.std(c)]+lst)+"\\\\")


for cat in sorted(cats, key=cats.get, reverse=True):
    size = cats[cat]
    if size>2:
        pass; #print(cat,cats[cat])

main={}

print("\n## All arxiv categories involved")
for pr in sorted(prim,key=prim.get,reverse=True):
    c = prim[pr]
    if pr in ["cs.LG","cs.CL","cs.CV","stat.ML","cs.AI"]:
        main[pr] = c
    else:
        ccc = "other"
        main[ccc] = main.get(ccc,0)+c
    if c>0:
        pass
        # comment in to print all involved categories
        #print(pr,c)

print("\n## Main arxiv categories involved")

for ccc in main:
    print(ccc,main[ccc])



#for week in sorted(weeks):
#    cl = weeks[week].get("cs.CL",0)
#    lg = weeks[week].get("cs.LG",0)
#    rest = 0
#    for r in weeks[week]:
#        if r!="cs.CL" and r!="cs.LG":
#            rest += 1
#    total = cl+lg+rest
#    print(week,"%.03f"%(cl/total),"%.03f"%(lg/total),"%.03f"%(rest/total))

