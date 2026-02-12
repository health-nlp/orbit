import lucene
import os

from pybool_ir.experiments.retrieval import AdHocExperiment
from pybool_ir.index.pubmed import PubmedIndexer
from pybool_ir.query.pubmed.parser import PubmedQueryParser
from typing import List, Tuple

from . import searchresult as sr
from . import LOCAL_PUBMED_INDEX_PATH
from . import _lock

class ESearch:
    """
    Implements the Pubmed-like ESearch endpoint
    
    Parses a boolean query, executes it against the Lucene index
    and returns matching document IDs with paging support (retstart/retmax)
    """

    LOCAL_INDEX_PATH = os.getenv("LOCAL_INDEX_PATH", "/app/index")
    vm = lucene.getVMEnv()
    parser = PubmedQueryParser()

    def __init__(self, term: str, retstart: int, retmax: int, retmode: str, field: str, trecqid: str, trectag: str):
        self.term = term
        self.retstart = retstart
        self.retmax = retmax
        self.retmode = retmode
        self.field = field
        self.trecqid = trecqid
        self.trectag = trectag
    
    """
    Initialization of an ESearch request.

    :param term: Boolean query (e.g. "cancer AND therapy")
    :param retstart: Start offset for paging
    :param retmax: Maximum number of results to return
    :param retmode: Output format ("json" or "xml")
    :param field: Optional field restriction (e.g., ti, ab)
    """

    def search(self) -> sr.SearchResult:
        """
        Runs the search against the index.

        Steps: 
        1. Parse query -> AST
        2. Format Lucene query
        3. Retrieve matching document IDs
        4. Return ESearchResult

        : return SearchResult containing IDs and metadata
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
            translationset={"from": self.term, "to": formatted_query},
            trecqid=self.trecqid,
            trectag=self.trectag
        )


    
    # -----------------------
    # --- ESummary Helper ---
    # -----------------------

    # @lru_cache(maxsize=64)
    def _idlist(self, query: str, retstart: int, retmax: int) -> Tuple[int, List[str]]:
        """
        Internal helper method: runs lucene query and returns list of matching IDs.

        :param query: Formatted Lucene query
        :param retstart: Paging start index
        :param retmax: Paging size
        
        : return: (total_count, list_of_ids)
        """

        with _lock:
            try:
                if not self.vm.isCurrentThreadAttached():
                    self.vm.attachCurrentThread()

                indexer = PubmedIndexer(index_path=LOCAL_PUBMED_INDEX_PATH)    
                with AdHocExperiment(indexer, raw_query="test",page_start=retstart, page_size=retmax) as ex:
                    results = ex.run
                    ids = [str(res.doc_id) for res in results]
                    total_count = next(ex.count())
                    return (total_count, ids)
            except Exception as e:
                print(f"DEBUG Fehler: {e}")
                raise e


    def set_field_recursively(self, node, new_field):
        """
        Recursively assign a field to all AST atom nodes.
        """
        # Atom (= echtes Term-Leaf)
        if hasattr(node, "field"):
            node.field = new_field

        # rekursiv über Kinder (Operatoren etc.)
        if hasattr(node, "children"):
            for child in node.children:
                self.set_field_recursively(child, new_field)

