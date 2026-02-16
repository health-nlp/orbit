from datetime import datetime
from fastapi import Response
import lucene
import os

from pybool_ir.experiments.retrieval import AdHocExperiment
from pybool_ir.index.pubmed import PubmedIndexer
from pybool_ir.query.pubmed.parser import PubmedQueryParser
from pybool_ir.index.pubmed import PubmedArticle
from typing import List

import xml.etree.ElementTree as ET

from . import searchresult as sr
from . import ORBIT_PUBMED_INDEX_PATH
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
                indexer = PubmedIndexer(index_path=ORBIT_PUBMED_INDEX_PATH, store_fields=True)

                with AdHocExperiment(indexer, page_start=self.retstart, page_size=self.retmax) as ex:
                    docs = ex.indexer.search(query=query, n_hits=len(uid_list))

                    root = ET.Element("PubmedArticleSet")
                    for d in docs:
                        print("--- DEBUG DUMP START ---")
                        print(d.fields) 
                        print("--- DEBUG DUMP END ---")
                        pubmed_article = ET.SubElement(root, "PubmedArticle")
                        medline_citation = ET.SubElement(pubmed_article, "MedlineCitaiton")
                        pmid = ET.SubElement(medline_citation, "PMID", attrib={"Status": "MEDLINE", "Owner": "NLM", "IndexingMethod": "Automated"})
                        pmid.text = d["id"]

                        date_completed = ET.SubElement(medline_citation, "DateCompleted")
                        raw_date = d["date"]

                        try: 
                            if isinstance(raw_date, (int, float)):
                                dt_obj = datetime.fromtimestamp(raw_date)
                            else: 
                                dt_obj = raw_date

                            ET.SubElement(date_completed, "Year").text = str(dt_obj.year)
                            ET.SubElement(date_completed, "Month").text = str(dt_obj.month).zfill(2)
                            ET.SubElement(date_completed, "Day").text = str(dt_obj.day).zfill(2)

                        except Exception: 
                            ET.SubElement(date_completed, "Year").text = "0000"
                        
                        article = ET.SubElement(medline_citation, "Article")
                        ET.SubElement(article, "ArticleTitle").text = d["title"]

                        abstract = ET.SubElement(article, "Abstract")
                        ET.SubElement(abstract, "AbstractText").text = d["abstract"]

                        publication_type_list = ET.SubElement(article, "PublicationTypeList")
                        for pb_type in d.fields["publication_type"]: 
                            publication_type = ET.SubElement(publication_type_list, "PublicationType")
                            publication_type.text = str(pb_type)

                        keyword_list = ET.SubElement(medline_citation, "KeywordList")
                        for key in d.fields["keyword_list"]:
                            keyword = ET.SubElement(keyword_list, "Keyword")
                            keyword.text = str(key)
                    

                header = """<?xml version="1.0" ?>
<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2025//EN" "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_250101.dtd">
"""
                return Response(header + ET.tostring(root, encoding="unicode"),media_type="application/xml")

            except Exception as e: 
                raise e
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

