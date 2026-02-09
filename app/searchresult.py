import json
from typing import Any
import xml.etree.ElementTree as ET
from fastapi import Response

excluded = ["error", "media_type", "content", "status_code", "background", "body", "raw_headers", "retmode"]

class SearchResult(Response): 
    def __init__(self, retmode: str, error: str = None):
        self.retmode = retmode
        self.media_type = "application/json"
        if retmode == "xml":
            self.media_type = "application/xml"
        self.error = error
        self.content = self.render(None)
        super().__init__(None, 200, None, self.media_type, None)

    def to_json(self):
        class_name = self.__class__.__name__.lower().replace("result","")

        data = {
            "header": self.get_header(class_name),
        }

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

            "esearchresult": "eSearchResult"
        }
        class_name = substitutions[self.__class__.__name__.lower()]
        
        root = ET.Element(f"{class_name}")

        if self.error: 
            err_tag = ET.SubElement(root, "ERROR")
            err_tag.text = str(self.error)
        else: 
            for key, value in self.__dict__.items():
                if key not in excluded: 
                    key = substitutions[key]
                    child = ET.SubElement(root, key)
                    if isinstance(value, list):                         # handle list case
                        for item in value: 
                            item_child = ET.SubElement(child, "Id")
                            item_child.text = str(item)
                    elif isinstance(value, dict):                       # handle dictionary case
                        for k, v in value.items(): 
                            sub = ET.SubElement(child, k)
                            sub.text = str(v)
                    else:                                               # handle text string case
                        child.text = str(value)

        return ET.tostring(root, encoding="unicode")
    
    def to_json_response(self):
        return Response(self.to_json(), media_type="application/json")

    def to_xml_response(self):
        return Response(self.to_xml(), media_type="application/xml")

    def render(self, content: Any) -> bytes:
        if self.retmode == "xml":
            return bytes(self.to_xml(), encoding="utf-8")
        if self.retmode == "json":
            return bytes(self.to_json(), encoding="utf-8")
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
                 idlist: str,
                 querytranslation: str,
                 translationset: str = None,
                 error = None):
        self.count = count
        self.retmax = retmax
        self.retstart = retstart
        self.idlist = idlist
        self.querytranslation = querytranslation
        self.translationset = translationset
        super().__init__(retmode, error)


class EFetch(SearchResult):
    def __init__(self, format: str, 
                 retmode: str,
                 article_dicts: list,
                 error = None):
        super().__init__(format, error)

        self.retmode = retmode
        self.article_dicts = article_dicts

class ESummary(SearchResult): 
    def __init__(self, format: str,
                 retstart: str,
                 retmax: str, 
                 retmode: str,  
                 error = None):
        super().__init__(format, error)

        self.retstart = retstart
        self.retmax = retmax
        self.retmode = retmode
        
