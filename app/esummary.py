from functools import lru_cache
from fastapi import FastAPI, HTTPException, Query, Response

from pybool_ir.experiments.retrieval import AdHocExperiment
from pybool_ir.index.pubmed import PubmedIndexer
from pybool_ir.query.pubmed.parser import PubmedQueryParser
from pybool_ir.index.pubmed import PubmedArticle
from pybool_ir.query.ast import AtomNode, OperatorNode
from typing import List, Dict, Any, Tuple

import searchresult as sr

import threading
import lucene
import os
import pathlib

class ESummary: 
    LOCAL_INDEX_PATH = os.getenv("LOCAL_INDEX_PATH", "app/index")
    vm = lucene.getVMEnv()
    lock = threading.Lock()
    parser = PubmedQueryParser()

    def __init__(self, id: str, retmode: str, retstart: int, retmax: int):
        self.id = id
        self.retmode = retmode
        self.retstart = retstart or 0
        self.retmax = retmax or 20

    

    def summarize(self): 
        uid_list = [p.strip() for p in self.id.split(",") if p.strip()]

        start = max(self.retstart, 0)
        end = start + self.retmax
        uid_list = uid_list[start:end]

        self.lock.acquire()
        try: 
            self.vm.attachCurrentThread()
            query = " OR ".join([f"id:{uid}" for uid in uid_list])

            with AdHocExperiment(PubmedIndexer(index_path=self.LOCAL_INDEX_PATH, store_fields=True), page_start=self.retstart, page_size=self.retmax) as experiment: 
                articles: List[PubmedArticle] = experiment.indexer.search(query=query, n_hits=len(uid_list))

                summaries = [self.to_summary(a) for a in articles]

                return sr.ESummaryResult(
                    retstart=self.retstart,
                    retmax=self.retmax,
                    retmode=self.retmode,
                    summaries=summaries
                )

        except Exception as e: 
            return sr.SearchResult(retmode=self.retmode, error=str(e))

        finally: 
            self.lock.release()

    # ESummary Helper
    def to_summary(self, article: PubmedArticle) -> dict: 
        d = article.to_dict()

        return {
            "id": d.get("id"),
            "title": d.get("title"),
            "authors": [a.get("names") for a in d.get("authors", [])][:5],
            "journal": d.get("publication_type"),
            "pubdate": d.get("date"),
            "pubtype": d.get("publication_type")
        }


    