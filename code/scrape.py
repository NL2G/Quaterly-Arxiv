#!/usr/bin/env python
import types
from collections import defaultdict
from statistics import mean
import shelve

import arxiv
import pandas as pd
import seaborn as sb
from matplotlib import pyplot as plt
from matplotlib import ticker as mtick
from semanticscholar.Paper import Paper
from tqdm import tqdm
from pandas import DataFrame
from datetime import datetime
from itertools import chain
from os.path import basename
from semanticscholar import SemanticScholar


def search(queries=[], field="all", cats=["cs.CL", "cs.LG"]):  # cs.AI, cs.CV
    # Use the arxiv API to query for papers from specified categories
    query_string, client = "", arxiv.Client(num_retries=40, page_size=1000)
    if queries:
        query_string += "(" + " OR ".join(f"{field}:{query}" for query in queries) + ")"
    if cats:
        if query_string:
            query_string += " AND "
        query_string += "(" + " OR ".join(f"cat:{cat}" for cat in cats) + ")"
    print(query_string)
    return client.results(arxiv.Search(
        query=query_string,
        sort_by=arxiv.SortCriterion.SubmittedDate,
    ))


def _get_papers(
        self,
        paper_ids,
        fields: list = None
):
    # Overwriting this method of the python semanticscholar API and allow papers that exist in arxiv but not semantic scholar
    if not fields:
        fields = Paper.SEARCH_FIELDS

    url = f'{self.api_url}/paper/batch'

    fields = ','.join(fields)
    parameters = f'&fields={fields}'

    payload = {"ids": paper_ids}

    data = self._requester.get_data(
        url, parameters, self.auth_header, payload)
    papers = [Paper(item) if item else None for item in data]

    return papers


def get_papers(file="papers.shelf"):
    # Get raw data from arxiv and semantic scholar and save it to papers.shelf
    papers = defaultdict(list)

    try:
        with shelve.open(file, "r") as shelf:
            print("Loading cached papers.")
            for month in shelf:
                papers[int(month)] = shelf[month]
    except:
        print("Downloading papers.")
        results = []
        batch = []
        progress = 0
        print("Progress:", 0)
        for result in search():
            if result.published.year >= 2023:
                if len(batch) < 500:
                    results.append(result)
                    batch.append("arxiv:" + basename(result.entry_id).split("v")[0])
                    progress += 1
                else:
                    for r, cnt in zip(results, get_citations(batch)):
                        r.citationCount = cnt
                        papers[r.published.month].append(r)
                        results = []
                        batch = []
                    print("Progress:", progress)
            else:
                break
        if len(results) > 0:
            for r, cnt in zip(results, get_citations(batch)):
                r.citationCount = cnt
                papers[r.published.month].append(r)
            print("Progress:", progress)

        with shelve.open(file, "n") as shelf:
            for month in papers:
                shelf[str(month)] = papers[month]

    return papers


sch = SemanticScholar(timeout=100)
# Overwrite function with hotfix
sch.get_papers = types.MethodType(_get_papers, sch)


def get_citations(batch):
    # Get citation counts with overwritten semantic scholar batch api
    papers = sch.get_papers(paper_ids=batch)
    citation_counts = []
    for p in papers:
        try:
            citation_counts.append(p.citationCount)
        except:
            citation_counts.append(0)
    return citation_counts


def find_terms(all_papers, terms=['chat', 'gpt'], filename="chatgpt.pdf"):
    title_results, abstract_results = defaultdict(list), defaultdict(list)
    for month, papers in all_papers.items():
        for paper in papers:
            if any(term.lower() in paper.title.lower() for term in terms):
                title_results[month].append(paper)
                abstract_results[month].append(paper)
            elif any(term.lower() in paper.summary.lower() for term in terms):
                abstract_results[month].append(paper)

    ax = sb.lineplot({
        "Title only": [100 * len(title_results[month]) / len(all_papers[month]) for month in sorted(all_papers)],
        "Title & Abstract": [100 * len(abstract_results[month]) / len(all_papers[month]) for month in
                             sorted(all_papers)]
    })
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_xticks(range(4), labels=["January", "February", "March", "April"])
    plt.show()
    # plt.savefig(filename, bbox_inches='tight')


def regression(papers):
    # papers = {key:[paper for paper in ps if paper.citationCount >= 1] for key, ps in papers.items()}
    paper_date = defaultdict(list)
    for paper in [paper for paper in chain.from_iterable(papers.values())]:
        paper_date[paper.published.timetuple().tm_yday].append(paper.citationCount)
    ax = sb.lmplot(DataFrame.from_dict({
        (date_label := "Date"): sorted(paper_date.keys()),
        (citation_label := "Average Citations per Day"): [mean(values) for _, values in
                                                          sorted(paper_date.items(), key=lambda kv: kv[0])]
    }), x=date_label, y=citation_label, order=5, height=5, aspect=16 / 9)  # pyright: ignore

    dates = [datetime.strptime(f"2023-{day}", "%Y-%j").strftime("%d. %m") for day in sorted(paper_date.keys())]
    ticks = list(map(int, ax.ax.get_xticks()[1:-1]))
    ax.ax.set_xticks(ticks, labels=[dates[tick] for tick in ticks])
    plt.savefig("regression.pdf", bbox_inches='tight')

    regline = dict(list(map(lambda a: [round(a[0]), a[1]], ax.ax.get_children()[1].get_path().vertices)))
    for x in range(1, max(regline.keys()) + 1):  # pyright: ignore
        if x not in regline:
            regline[x] = (regline[x - 1] + regline[x + 1]) / 2  # pyright: ignore
    ranking = list()
    for paper in [paper for paper in chain.from_iterable(papers.values())]:
        ranking.append((paper.citationCount / regline[paper.published.timetuple().tm_yday], paper))
    ranking = [x[1] for x in sorted(ranking, key=lambda x: x[0], reverse=True)]

    return ranking[:50]


if __name__ == "__main__":
    sb.set()
    papers = get_papers()
    
    df = pd.DataFrame([vars(a) for a in sum(dict(papers).values(), [])])

    # Currently we set weeks to begin sundays. We group by week and calculate the average per week as a new dataframe column
    df['WeekNumber'] = df['published'].dt.to_period('W-SAT')

    grouped = df.groupby('WeekNumber')
    groups = []
    for name, group in grouped:
        mean = group['citationCount'].mean()
        std = group['citationCount'].std(ddof=0)
        group["z-score"] = (group['citationCount'] - mean) / std

        groups.append(group)

    # Save dataframe with the normalized citation counts as csv file
    df = pd.concat(groups).sort_values('z-score', ascending=False)
    df['published'] = df['published'].dt.tz_localize(None)
    df['updated'] = df['updated'].dt.tz_localize(None)
    df.to_csv("computation.csv", sep="\t")

