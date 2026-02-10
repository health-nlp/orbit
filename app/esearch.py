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


class ESearch:
    LOCAL_INDEX_PATH = os.getenv("LOCAL_INDEX_PATH", "app/index")
    vm = lucene.getVMEnv()
    lock = threading.Lock()
    parser = PubmedQueryParser()

    def __init__(self, term: str, retstart: int, retmax: int, retmode: str, field: str):
        self.term = term
        self.retstart = retstart
        self.retmax = retmax
        self.retmode = retmode
        self.field = field

    # @lru_cache(maxsize=64)
    def _idlist(self, query: str, retstart: int, retmax: int) -> Tuple[int, List[str]]:
        # Run the ad-hoc experiment using the index at LOCAL_INDEX_PATH
        self.lock.acquire()
        try:
            self.vm.attachCurrentThread()
            with AdHocExperiment(PubmedIndexer(index_path=self.LOCAL_INDEX_PATH), raw_query="test",page_start=retstart, page_size=retmax) as ex:
                results = ex.run
                ids = [str(res.doc_id) for res in results]
                total_count = next(ex.count())
                return (total_count, ids)
        except Exception as e:
            print(f"DEBUG Fehler: {e}")
            raise e
        finally:
            self.lock.release()

    # Helper methods for esearch      
    def set_field_recursively(node, new_field):
        # Atom (= echtes Term-Leaf)
        if hasattr(node, "field"):
            node.field = new_field

        # rekursiv über Kinder (Operatoren etc.)
        if hasattr(node, "children"):
            for child in node.children:
                set_field_recursively(child, new_field)


    def search(self) -> sr.SearchResult:
        print(f"Running esearch for query: {self.term}")
        """
        Docstring for _esearch
        
        :param query: Description
        :type query: str
        :param retmode: Description
        :type retmode: str
        :param retmax: Description
        :type retmax: int
        :param retstart: Description
        :type retstart: int
        :return: Description
        :rtype: SearchResult
        """
        if not self.vm.isCurrentThreadAttached():
            self.vm.attachCurrentThread()

        # Parse and prepare query (will raise on malformed query)
        ast = self.parser.parse_ast(self.term)
        self.parser.parse_lucene(self.term)
        formatted_query = self.parser.format(ast)

        total_count, id_list = self._idlist(formatted_query, self.retstart, self.retmax)

        return sr.ESearchResult(
            retmode=self.retmode,
            count=str(total_count),
            retmax=str(self.retmax),
            retstart=str(self.retstart),
            idlist=id_list,
            querytranslation=formatted_query,
            translationset={"from": self.term, "to": formatted_query}
        )
