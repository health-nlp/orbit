import lucene
import os

from pybool_ir.experiments.retrieval import AdHocExperiment
from pybool_ir.index.pubmed import PubmedIndexer
from pybool_ir.query.pubmed.parser import PubmedQueryParser
from pybool_ir.index.pubmed import PubmedArticle
from typing import List

from . import searchresult as sr
from . import LOCAL_PUBMED_INDEX_PATH
from . import _lock


class EFetch: 
    """
    Implements the PubMed-like EFetch endpoint.

    Retrieves full article documents for a given list of PubMed IDs.
    Supports paging via retstart/retmax and returns structured
    article metadata stored in the Lucene index.
    """

    vm = lucene.getVMEnv()
    parser = PubmedQueryParser()

    def __init__(self, id: str, retmode: str, retstart: int, retmax: int):
        self.id = id
        self.retmode = retmode
        self.retstart = retstart or 0
        self.retmax = retmax or 20

    """
    Initialize an EFetch request.

    :param id: Comma separated list of PubMed IDs
    :param retmode: Output format ("json" or "xml")
    :param retstart: Start offset for paging
    :param retmax: Maximum number of documents to return
    """

    
    def fetch(self):
        """
        Runs the fetch operation

        Steps: 
        1. Parse and slice input IDs
        2. Build Lucene query
        3. Retrieve matching articles from index
        4. Returen EFetchResult

        :return: SearchResult containing full article data
        """

        with _lock:
            try: 
                if not self.vm.isCurrentThreadAttached():
                    self.vm.attachCurrentThread()

                query, uid_list = self.process_input(self.id, self.retstart, self.retmax)
                indexer = PubmedIndexer(index_path=LOCAL_PUBMED_INDEX_PATH, store_fields=True)

                with AdHocExperiment(indexer, page_start=self.retstart, page_size=self.retmax) as ex:
                    articles: List[PubmedArticle] = ex.indexer.search(query=query, n_hits=len(uid_list))
                    article_dicts = [article.to_dict() for article in articles]

                    return sr.EFetchResult(retmode=self.retmode, article_dicts=article_dicts)

            except Exception as e: 
                return sr.SearchResult(error=str(e), retmode=self.retmode)


    # -----------------------
    # --- ESummary Helper ---
    # -----------------------
    def process_input(self, ids: str, retstart: int, retmax: int):
        """
        Internal helper method: Parse ID and create a Lucene query

        :param ids: Raw comma separated IDs
        :param retstart: Start offest for paging 
        :param retmax: Maximum number of documents ot return
        """
        uid_list = [p.strip() for p in self.id.split(",") if p.strip()]
        sliced_list =  self.slice_uid_list(uid_list, retstart, retmax)
        return " OR ".join([f"id:{uid}" for uid in sliced_list]), uid_list


    # restricts the list of uids to given retstart and retmax parameters
    def slice_uid_list(self, uid_list: List, retstart: int, retmax: int):
        """
        Restrict the UID list to the request page.

        :param uid_list: Complete list of IDs
        :param retstart: Start index
        :param retmax: Page size

        :return: Sliced list of IDs
        """
        
        start = max(retstart, 0)
        end = start + retmax
        return uid_list[start:end]

