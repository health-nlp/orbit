import lucene
import os

from fastapi import Response

from pybool_ir.experiments.retrieval import AdHocExperiment
from pybool_ir.index.pubmed import PubmedIndexer
from pybool_ir.query.pubmed.parser import PubmedQueryParser
from pybool_ir.index.pubmed import PubmedArticle
from typing import List

import xml.etree.ElementTree as ET

from . import searchresult as sr
from . import ORBIT_PUBMED_INDEX_PATH
from . import _lock

class ESummary: 
    """
    Implements the PubMed-like ESummary endpoint. 

    Retrieves the summaries given a list of uids
    Supports paging via retstart/retmax
    """
    vm = lucene.getVMEnv()
    parser = PubmedQueryParser()

    def __init__(self, id: str, retmode: str, retstart: int, retmax: int):
        self.id = id
        self.retmode = retmode
        self.retstart = retstart or 0
        self.retmax = retmax or 20
    
    """
    Initialize an ESummary request
    :param id: Comma separated list of PubMed IDs
    :param retmode: Output format ("json" or "xml")
    :param retstart: Start offset for paging
    :param retmax: Maximum number of documents to return
    """


    # this method is called from main.py -> returns summaries to comma seperated uids
    def summarize(self): 
        """
        Execute an ESummary request for the given UID list.

        Retrieves the specified PubMed articles from the local Lucene index,
        converts them into lightweight summary dictionaries, and returns an
        ESummaryResult response formatted according to the selected retmode
        (json or xml).

        Applies pagination using retstart and retmax before querying.

        :return: Formatted ESummaryResult or SearchResult containing an error
        :rtype: sr.SearchResult
        """

        with _lock:
            try: 
                if not self.vm.isCurrentThreadAttached():
                    self.vm.attachCurrentThread()

                query, uid_list = self.process_input(self.id, self.retstart, self.retmax)
                indexer = PubmedIndexer(index_path=ORBIT_PUBMED_INDEX_PATH, store_fields=True)

                with AdHocExperiment(indexer, page_start=self.retstart, page_size=self.retmax) as ex: 
                    articles: List[PubmedArticle] = ex.indexer.search(query=query, n_hits=len(uid_list))
                    # summaries = [self.to_summary(a) for a in articles]

                    header = """<?xml version="1.0" ?>
<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2025//EN" "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_250101.dtd">
"""

                    root = ET.Element("eSummaryResult")
                    for a in articles: 
                        print("--- DEBUG DUMP START ---")
                        print(a.fields) 
                        print("--- DEBUG DUMP END ---")
                        docsum = ET.SubElement(root, "DocSum")

                        doc_id = ET.SubElement(docsum, "Id")
                        doc_id.text = a["id"]
                        doc_title = ET.SubElement(docsum, "Title")
                        doc_title.text = a["title"]
                        
                        doc_pubtype_list = ET.SubElement(docsum, "PubTypeList")
                        for pubtype in a.fields["publication_type"]:
                            publication_type = ET.SubElement(doc_pubtype_list, "PubType")
                            publication_type.text = str(pubtype)
                    

                    #summary = header + ET.tostring(root, encoding="unicode"), 
                    return Response(header + ET.tostring(root, encoding="unicode"),media_type="application/xml")
                    #return sr.ESummaryResult(retstart=self.retstart,retmax=self.retmax,retmode=self.retmode,summaries=summary)

            except Exception as e: 
                raise e
                return sr.SearchResult(retmode=self.retmode, error=str(e))

    # -----------------------
    # --- ESummary Helper ---
    # -----------------------

    # takes user input and processes it -> returns lucene-query 
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


    # generates a dictionary as summary of PubMed articles
    def to_summary(self, article: PubmedArticle) -> dict: 
        """
        Convert a full PubMedArticle into a lightweight summary dictionary.

        Extracts only the most relevant metadata fields typically returned by
        the ESummary endpoint (ID, title, authors, journal, publication date).

        :param article: PubmedArticle instance retrieved from the index
        :type article: PubmedArticle
        :return: Dictionary containing summarized article metadata
        :rtype: dict
        """

        # d = article.to_dict()

        # return {
        #     "id": d.get("id"),
        #     "title": d.get("title"),
        #     "authors": [a.get("names") for a in d.get("authors", [])][:5],
        #     "journal": d.get("publication_type"),
        #     "pubdate": d.get("date"),
        #     "pubtype": d.get("publication_type")
        # }