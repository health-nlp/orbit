import io
import csv
import json
from typing import Any
import xml.etree.ElementTree as ET
from fastapi import Response
import lucene

from pybool_ir.index.ctgov import ClinicalTrialsGovIndexer, ClinicalTrialsGovArticle
from pybool_ir.query.essie.parser import EssieQueryParser

from . import ORBIT_CTGOV_INDEX_PATH
from . import _lock
from .metadata import _metadata
from .searchareas import _searchareas

vm = lucene.getVMEnv()
parser = EssieQueryParser()

class SearchResult(Response):
    def __init__(
            self, 
            rformat: str, 
            data: Any):
        self.rformat = rformat
        self.data = data
        self.trecqid = data["trecqid"] if "trecqid" in data else "0"
        self.trectag = data["trectag"] if "trectag" in data else "orbit"
        if rformat == "json":
            self.media_type = "application/json"
        elif rformat == "xml":
            self.media_type = "application/xml"
        elif rformat == "csv":
            self.media_type = "text/csv"
        else:
            self.media_type = "text/plain"
        self.content = self.render(None)
        super().__init__(None, 200, None, self.media_type, None)

    def render(self, content: Any) -> bytes:
        if self.rformat == "json":
            return json.dumps(self.data).encode("utf-8")
        elif self.rformat == "xml":
            return self.to_xml(self.data, "root").encode("utf-8")
        elif self.rformat == "csv":
            return self.to_csv(self.data).encode("utf-8")
        elif self.rformat == "trec":
            return self.to_trec(self.data).encode("utf-8")
        else:
            return self.to_text(self.data).encode("utf-8")

    def to_xml(self, data: Any, tag: str) -> str:
        elem = ET.Element(tag)
        if isinstance(data, dict):
            for key, value in data.items():
                child_tag = key if key.isidentifier() else "item"
                elem.append(ET.fromstring(self.to_xml(value, child_tag)))
        elif isinstance(data, list):
            for item in data:
                elem.append(ET.fromstring(self.to_xml(item, "item")))
        else:
            elem.text = str(data) if data is not None else ""
        return ET.tostring(elem, encoding="unicode")

    def to_csv(self, data: Any) -> str:
        if isinstance(data, dict) and "studies" in data:
            rows = data["studies"]
        elif isinstance(data, list):
            rows = data
        else:
            rows = [data]
        flat_rows = [self._flatten(row) for row in rows]
        if not flat_rows:
            return ""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=flat_rows[0].keys())
        writer.writeheader()
        writer.writerows(flat_rows)
        return buf.getvalue()

    def _flatten(self, data: Any, prefix: str = "") -> dict:
        result = {}
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                result.update(self._flatten(value, full_key))
        elif isinstance(data, list):
            result[prefix] = "|".join(str(v) for v in data)
        else:
            result[prefix] = data
        return result
    
    def to_trec(self, data: Any) -> str:
        trec_output = ""
        print("trecqid:", self.trecqid)
        print("trectag:", self.trectag)
        if isinstance(data, dict) and "studies" in data:
            for rank, study in enumerate(data["studies"]):
                nct_id = study["protocolSection"]["identificationModule"]["nctId"]
                trec_output += f"{self.trecqid} Q0 {nct_id} {rank} {1-(rank/len(data['studies'])):.4f} {self.trectag}\n"
        return trec_output
        


# 1. for a single study (via nct_id)
def study(rformat: str, nct_id: str) -> SearchResult:
    with _lock:
        try:
            if not vm.isCurrentThreadAttached():
                vm.attachCurrentThread()

            with ClinicalTrialsGovIndexer(index_path=ORBIT_CTGOV_INDEX_PATH) as ix:
                # --- DEBUGGING START ---
                print(f"DEBUG: Index geladen von {ORBIT_CTGOV_INDEX_PATH}")
                print(f"DEBUG: Anzahl der Dokumente im Index: {ix.index.count()}")
                
                safe_nct_id = nct_id.strip().upper()
                query_string = f'nct_id:{safe_nct_id}'
                print(f"DEBUG: Führe Lucene-Suche aus: {query_string}")
                # --- DEBUGGING END ---
                
                hits = ix.index.search(ntct_id=safe_nct_id)
                
                if len(hits) == 0:
                    return Response(content="Parameter `nctId` has incorrect format or NCT number not found", media_type="text/plain")
    
                for hit in hits:
                    d = ClinicalTrialsGovArticle.from_hit(hit)
                    return SearchResult(rformat, {
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


def studies(rformat: str, query_term: str, page_start: int, page_size: int, trecqid: str, trectag: str) -> SearchResult:
    with _lock:
        try:
            if not vm.isCurrentThreadAttached():
                vm.attachCurrentThread()

            with ClinicalTrialsGovIndexer(index_path=ORBIT_CTGOV_INDEX_PATH) as ix:
                lucene_query = parser.parse_lucene(query_term)
                hits = ix.index.search(lucene_query)
                hitsize = len(hits)
                
                if page_size > hitsize:
                    page_size = hitsize
                
                studies_list = []
                for hit in hits[page_start:page_start + page_size]:
                    d = ClinicalTrialsGovArticle.from_hit(hit)
                    studies_list.append({
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
                    "studies": studies_list
                })

            return SearchResult(rformat, {
                "totalCount": hitsize,
                "studies":studies,
                "trecqid": trecqid,
                "trectag": trectag
            })
        except Exception as e:
            raise e


def metadata():
    return Response(json.dumps(_metadata), media_type="application/json")

def searchareas():
    return Response(json.dumps(_searchareas), media_type="application/json")
