from __future__ import annotations

import random
from collections.abc import Iterable
from itertools import islice
from typing import TypeVar

import datasets

from mteb.abstasks.AbsTaskClustering import AbsTaskClustering
from mteb.abstasks.TaskMetadata import TaskMetadata

T = TypeVar("T")


def batched(iterable: Iterable[T], n: int) -> Iterable[tuple[T, ...]]:
    # batched('ABCDEFG', 3) --> ABC DEF G
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


class SwednClustering(AbsTaskClustering):
    superseded_by = "SwednClusteringP2P"

    metadata = TaskMetadata(
        name="SwednClustering",
        dataset={
            "path": "sbx/superlim-2",
            "revision": "ef1661775d746e0844b299164773db733bdc0bf6",
            "name": "swedn",
            "trust_remote_code": True,
        },
        description="The SWE-DN corpus is based on 1,963,576 news articles from the Swedish newspaper Dagens Nyheter (DN) during the years 2000--2020. The articles are filtered to resemble the CNN/DailyMail dataset both regarding textual structure. This dataset uses the category labels as clusters.",
        reference="https://spraakbanken.gu.se/en/resources/swedn",
        type="Clustering",
        category="p2p",
        modalities=["text"],
        eval_splits=["all"],
        eval_langs=["swe-Latn"],
        main_score="v_measure",
        date=("2000-01-01", "2020-12-31"),  # best guess
        domains=["News", "Non-fiction", "Written"],
        license=None,
        annotations_creators="derived",
        dialect=[],
        task_subtypes=["Thematic clustering"],
        sample_creation="found",
        bibtex_citation=r"""
@inproceedings{monsen2021method,
  author = {Monsen, Julius and J{\"o}nsson, Arne},
  booktitle = {Proceedings of CLARIN Annual Conference},
  title = {A method for building non-english corpora for abstractive text summarization},
  year = {2021},
}
""",
    )

    def dataset_transform(self):
        """The article_category clusters differ between the splits (with the test set only having 1 cluster). Therefore we combine it all into one
        cluster.
        """
        splits = ["train", "validation"]
        # performance of sample models with test set: 8.74, 2.43 -removing test-> 11.26, 4.27
        # this is due to the test set only having 1 cluster which is "other"

        headlines = []
        summaries = []
        articles = []
        headline_labels = []
        sammary_labels = []
        article_labels = []
        label_col = "article_category"

        for split in splits:
            ds_split = self.dataset[split]
            headlines.extend(ds_split["headline"])
            headline_labels.extend(ds_split[label_col])

            summaries.extend(ds_split["summary"])
            sammary_labels.extend(ds_split[label_col])

            articles.extend(ds_split["article"])
            article_labels.extend(ds_split[label_col])

        rng = random.Random(42)  # local only seed

        clusters_text = []
        clusters_labels = []
        doc_types = [(summaries, sammary_labels), (articles, article_labels)]
        # Note that headlines is excluded:
        # Scores of sample models with headlines: 11.26, 4.27 -removing headlines-> 16.43, 4.31
        # as headlines are soo short it is hard to meaningfully cluster them even for humans.
        for text, labels in doc_types:
            pairs = list(zip(text, labels))
            rng.shuffle(pairs)
            # reduce size of dataset to not have too large datasets in the clustering task
            pairs_batched = list(batched(pairs, 512))
            texts1, labels2 = list(zip(*pairs_batched[0]))
            texts2, labels2 = list(zip(*pairs_batched[1]))

            clusters_text.extend([texts1, texts2])
            clusters_labels.extend([labels2, labels2])
        ds = datasets.Dataset.from_dict(
            {"sentences": clusters_text, "labels": clusters_labels}
        )
        self.dataset = datasets.DatasetDict({"all": ds})
