import json
from typing import Any, List
import xml.etree.ElementTree as ET
from fastapi import Response

excluded = ["error", "media_type", "content", "status_code", "background", "body", "raw_headers", "retmode", "trecqid", "trectag"]

class SearchResult(Response): 
    def __init__(self, retmode: str, error: str = None):
        self.retmode = retmode
        self.media_type = "application/json"
        if retmode == "xml":
            self.media_type = "application/xml"
        else:
            self.media_type = "text/plain"
        self.error = error
        self.content = self.render(None)
        super().__init__(None, 200, None, self.media_type, None)

    def to_json(self):
        class_name = self.__class__.__name__.lower().replace("result","")

        data = {"header": self.get_header(class_name)}

        if self.error: 
            data[f"{class_name}"] = {"ERROR": str(self.error)}
        else: 
            result_content = {k: v for k, v in self.__dict__.items() if k not in excluded}
            data[f"{class_name}"] = result_content

        return json.dumps(data)

    def to_xml(self): 
        substitutions = {
            "count": "Count",
            "retmax": "RetMax",
            "retstart": "RetStart",
            "idlist": "IdList",
            "translationset": "TranslationSet",
            "querytranslation": "QueryTranslation",
            "efetchresult": "eFetchResult",
            "esummaryresult": "eSummaryResult",
            "esearchresult": "eSearchResult",
            "searchresult": "SearchResult",
            "summaries": "DocSum"
        }

        class_name = substitutions.get(self.__class__.__name__.lower(), self.__class__.__name__)
        root = ET.Element(class_name)

        if self.error: 
            err_tag = ET.SubElement(root, "ERROR")
            err_tag.text = str(self.error)
        else: 
            for key, value in self.__dict__.items():
                if key in excluded:
                    continue 

                xml_key = substitutions.get(key, key)
                child = ET.SubElement(root, key)
                self._append_value_to_xml(child, value)
        
        return ET.tostring(root, encoding="unicode")

    # recursive helper function for clustered dict/lists
    def _append_value_to_xml(self, parent, value): 
        if isinstance(value, dict):                         # handle list case
            for k, v in value.items():
                sub = ET.SubElement(parent, k)
                self._append_value_to_xml(sub, v)
        elif isinstance(value, list):
            for item in value: 
                item_tag = ET.SubElement(parent, "Article")
                self._append_value_to_xml(item_tag, item)
        else: 
            parent.text = str(value)

    
    def to_json_response(self):
        return Response(self.to_json(), media_type="application/json")

    def to_xml_response(self):
        return Response(self.to_xml(), media_type="application/xml")

    def render(self, content: Any) -> bytes:
        if self.retmode == "xml":
            return bytes(self.to_xml(), encoding="utf-8")
        if self.retmode == "json":
            return bytes(self.to_json(), encoding="utf-8")
        if self.__class__.__name__ == "ESearchResult" and self.retmode == "trec":
            return bytes(self.to_trec(), encoding="utf-8")
        return bytes(self.to_json(), encoding="utf-8")

    def get_header(self, search_type):
        return {
            "type": search_type,
            "version": "0.3-openpm"
        }
    


# Classes for each search-type
class ESearchResult(SearchResult): 
    def __init__(self, retmode: str,
                 count: str, 
                 retmax: str,
                 retstart: str,
                 idlist: List[str],
                 querytranslation: str,
                 translationset: str = None,
                 trecqid: str = "0",
                 trectag: str = "orbit",
                 error = None):
        self.count = count
        self.retmax = retmax
        self.retstart = retstart
        self.idlist = idlist
        self.querytranslation = querytranslation
        self.translationset = translationset
        self.trecqid = trecqid
        self.trectag = trectag
        super().__init__(retmode, error)

    def to_trec(self):
        buff = []
        for i, pmid in enumerate(self.idlist):
            buff.append(f"{self.trecqid} Q0 {pmid} {i} {len(self.idlist)-i} {self.trectag}")
        return "\n".join(buff)



class EFetchResult(SearchResult):
    def __init__(self, 
                 retmode: str,
                 article_dicts: list,
                 error = None):
        self.retmode = retmode
        self.article_dicts = article_dicts
        super().__init__(retmode, error)


class ESummaryResult(SearchResult): 
    def __init__(self, 
                 retstart: str,
                 retmax: str, 
                 retmode: str,  
                 summaries: list,
                 error = None):
        self.retstart = retstart
        self.retmax = retmax
        self.retmode = retmode
        self.summaries = summaries
        super().__init__(format, error)
