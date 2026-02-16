
import json
from typing import Any
from fastapi import Response
import lucene

from pybool_ir.index.ctgov import ClinicalTrialsGovIndexer, ClinicalTrialsGovArticle
from pybool_ir.query.essie.parser import EssieQueryParser

from . import ORBIT_CTGOV_INDEX_PATH
from . import _lock

vm = lucene.getVMEnv()
parser = EssieQueryParser()

class SearchResult(Response): 
    def __init__(self, rformat: str, data: Any):
        self.media_type = "text/plain"        
        if rformat == "json":
            self.media_type = "application/json"
        self.data = data
        self.content = self.render(None)
        super().__init__(None, 200, None, self.media_type, None)

    def render(self, content: Any) -> bytes:
        return bytes(json.dumps(self.data), encoding="utf-8")

def study(rformat: str, nct_id: str) -> SearchResult:
    with _lock:
        try:
            if not vm.isCurrentThreadAttached():
                vm.attachCurrentThread()

            with ClinicalTrialsGovIndexer(index_path=ORBIT_CTGOV_INDEX_PATH) as ix:
                hits = ix.index.search(f'nct_id:{nct_id}')

            if len(hits) == 0:
                return Response(content="Parameter `nctId` has incorrect format or NCT number not found", media_type="text/plain")

            for hit in hits:
                d = ClinicalTrialsGovArticle.from_hit(hit)
                return SearchResult(rformat,
                {
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": d["nct_id"][0],
                            "briefTitle": d["brief_title"][0],
                            "officialTitle": d["official_title"][0]
                        },
                        "statusModule": {
                            "overallStatus": d["overall_status"][0]
                        },
                        "descriptionModule": {
                            "briefSummary": d["brief_summary"][0]
                        }
                    },
                    "hasResults": None
                })


        except Exception as e:
            raise e


def studies(rformat: str, query_term: str, page_start: int, page_size: int) -> SearchResult:
    with _lock:
        try:
            if not vm.isCurrentThreadAttached():
                vm.attachCurrentThread()

            with ClinicalTrialsGovIndexer(index_path=ORBIT_CTGOV_INDEX_PATH) as ix:
                lucene_query = parser.parse_lucene(query_term)
                hits = ix.index.search(lucene_query)
            page_size = page_size
            hitsize = len(hits)
            if page_size > hitsize:
                page_size = hitsize
            
            page_start = page_start
            if page_start > hitsize:
                page_start = -1
            
            page_end = -1
            if (page_start+page_size) < hitsize:
                page_end = page_start+page_size     
            
            studies = []
            for hit in hits[page_start:page_end]:
                # d = hit.dict("nctid","brief_title","overall_status", "has_results")
                d = ClinicalTrialsGovArticle.from_hit(hit)
                studies.append({
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": d["nct_id"][0],
                            "briefTitle": d["brief_title"][0]
                        },
                        "statusModule": {
                            "overallStatus": d["overall_status"][0]
                        }
                    },
                    "hasResults": None
                })

            return SearchResult(rformat, {
                "totalCount": hitsize,
                "studies":studies
            })
        except Exception as e:
            raise e