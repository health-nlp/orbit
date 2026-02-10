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

class EFetch: 
    LOCAL_INDEX_PATH = os.getenv("LOCAL_INDEX_PATH", "app/index")
    vm = lucene.getVMEnv()
    lock = threading.Lock()
    parser = PubmedQueryParser()

    def __init__(self, id: str, retmode: str, retstart: int, retmax: int):
        self.id = id
        self.retmode = retmode
        self.retstart = retstart or 0
        self.retmax = retmax or 20

    
    def fetch(self):
        self.lock.acquire()
        try: 
            self.vm.attachCurrentThread()
            uid_list = [p.strip() for p in self.id.split(",") if p.strip()]
            start = max(self.retstart, 0)
            end = start + self.retmax
            uid_list = uid_list[start:end]

            query = " OR ".join([f"id:{uid}" for uid in uid_list])

            with AdHocExperiment(PubmedIndexer(index_path=self.LOCAL_INDEX_PATH, store_fields=True), page_start=self.retstart, page_size=self.retmax) as ex:
                articles: List[PubmedArticle] = ex.indexer.search(query=query, n_hits=len(uid_list))
                article_dicts = [article.to_dict() for article in articles]

                return sr.EFetchResult(retmode=self.retmode, article_dicts=article_dicts)

        except Exception as e: 
            return sr.SearchResult(error=str(e), retmode=self.retmode)
        finally: 
            self.lock.release()
