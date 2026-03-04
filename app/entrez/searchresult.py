import json
from typing import Any, List
import xml.etree.ElementTree as ET
from fastapi import Response
from datetime import datetime

excluded = ["error", "media_type", "content", "status_code", "background", "body", "raw_headers", "retmode", "trecqid", "trectag", "translationset"]
HEADER = """<?xml version="1.0" ?>
         <!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2025//EN" "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_250101.dtd">
         """

class SearchResult(Response): 
    def __init__(self, retmode: str, error: str = None):
        self.retmode = retmode
        self.media_type = "text/plain"        
        if retmode == "xml":
            self.media_type = "application/xml"
        if retmode == "json":
            self.media_type = "application/json"
        if retmode == "txt":
            self.media_type = "text/plain"

        self.error = error
        self.content = self.render(None)
        super().__init__(self.content, 200, None, self.media_type, None)
    

    def to_json(self):
        class_name = self.__class__.__name__.lower().replace("result","")
        data = {"header": self.get_header(class_name)}

        if self.error: 
            data[f"{class_name}"] = {"ERROR": str(self.error)}
        else: 
            result_content = {k: v for k, v in self.__dict__.items() if k not in excluded}
            data[f"{class_name}"] = result_content

        return json.dumps(data, default=lambda o: o.isoformat() if isinstance(o, datetime) else str(o))

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
                child = ET.SubElement(root, xml_key)
                self._append_value_to_xml(child, value)

        return HEADER + "\n" + ET.tostring(root, encoding="unicode")



    # recursive helper function for clustered dict/lists
    def _append_value_to_xml(self, parent, value): 
        if isinstance(value, dict):                         # handle list case
            for k, v in value.items():
                sub = ET.SubElement(parent, k)
                self._append_value_to_xml(sub, v)
        elif isinstance(value, list):
            for item in value: 
                item_tag = ET.SubElement(parent, "Id")
                self._append_value_to_xml(item_tag, item)
        else: 
            if parent.tag == "from" or parent.tag == "to":
                parent.tag = parent.tag.capitalize()
            parent.text = str(value)

    
    def to_json_response(self):
        return Response(self.to_json(), media_type="application/json")

    def to_xml_response(self):
        return Response(self.to_xml(), media_type="application/xml")

    def to_txt(self):
        """Fallback method, if subclass does not implement to_txt"""
        return "Text output is not implemented for this endpoint"

    def render(self, content: Any) -> bytes:
        if self.retmode == "xml":
            return bytes(self.to_xml(), encoding="utf-8")
        if self.retmode == "json":
            return bytes(self.to_json(), encoding="utf-8")
        if self.retmode == "txt": 
            return bytes(self.to_txt(), encoding="utf-8")
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
            buff.append(f"{self.trecqid} Q0 {pmid} {i} {1-(i/len(self.idlist))} {self.trectag}")
        return "\n".join(buff)

    # used when retmode is set to "count", returns only count-value
    def return_count(self):
        root = ET.Element("eSearchResult")
        count_tag = ET.SubElement(root, "Count")
        count_tag.text = str(self.count)
        
        return Response(
            content= HEADER+ET.tostring(root, encoding="unicode"),
            media_type="application/xml"
        )

        

class ESummaryResult(SearchResult): 
    def __init__(self, 
                 retmode: str,  
                 summaries: list,
                 error = None):
        self.retmode = retmode
        self.summaries = summaries
        super().__init__(retmode, error)

    def to_xml(self):
        root = ET.Element("eSummaryResult")

        if self.error: 
            ET.SubElement(root, "ERROR").text = str(self.error)
            return self._finalize_xml(root)

        for a in self.summaries: 
            docsum = ET.SubElement(root, "DocSum")

            doc_id = ET.SubElement(docsum, "Id")
            doc_id.text = a.get("id", "N/A")

            doc_title = ET.SubElement(docsum, "Title")
            doc_title.text = a.get("title", "No Title")

            pub_types = a.get("publication_type", [])
            doc_pubtype_list = ET.SubElement(docsum, "PubTypeList")
            for pubtype in a.get("publication_type"):
                publication_type = ET.SubElement(doc_pubtype_list, "PubType")
                publication_type.text = str(pubtype)
            
        return self._finalize_xml(root)

    def _finalize_xml(self, root):
        return HEADER+ET.tostring(root, encoding="unicode")

# TODO fix root while returning to_xml() -> "eFetchResult" instead of "PubmedArticleSet"
class EFetchResult(SearchResult):
    def __init__(self, 
                articles: List[dict], 
                retmode: str, 
                error: str = None):
        self.articles = articles
        super().__init__(retmode, error)

    
    def to_xml(self): 
        if self.error:
            root = ET.Element("eFetchResult")
            ET.SubElement(root, "ERROR").text = str(self.error)
            return self._finalize_xml(root)

        root = ET.Element("PubmedArticleSet")
        for data in self.articles: 
            pubmed_article = ET.SubElement(root, "PubmedArticle")
            medline_citation = ET.SubElement(pubmed_article, "MedlineCitaiton")
            pmid = ET.SubElement(medline_citation, "PMID", attrib={"Status": "MEDLINE", "Owner": "NLM", "IndexingMethod": "Automated"})
            pmid.text = data["id"]

            self._add_date_xml(medline_citation, data.get("date"))

            article = ET.SubElement(medline_citation, "Article")
            ET.SubElement(article, "ArticleTitle").text = data["title"]

            abstract = ET.SubElement(article, "Abstract")
            ET.SubElement(abstract, "AbstractText").text = data["abstract"]

            publication_type_list = ET.SubElement(article, "PublicationTypeList")
            self._add_list_xml(publication_type_list, "PublicationType", data["publication_type"])

            keyword_list = ET.SubElement(medline_citation, "KeywordList")
            self._add_list_xml(keyword_list, "Keyword", data["keyword_list"])

        return self._finalize_xml(root)

    def to_txt(self):
        if self.error: 
            return f"ERROR: {self.error}"

        output = []
        
        for data in self.articles: 
            pmid = data.get("id", "N/A")
            title = data.get("title", "No Title")
            date = data.get("date", "No Date")
            abstract = data.get("abstract", "No Abstract")

            output.append(f"Title: {title}\n")
            output.append(f"Abstract: {abstract}\n")
            output.append(f"DOI: {date}")
            output.append(f"PMID: {pmid}")

            output.append("-".repeat(30))

        return "\n".join(output)


    def _add_date_xml(self, parent, raw_date): 
        try: 
            if isinstance(raw_date, (int, float)): 
                dt_obj = datetime.fromtimestamp(raw_date)
            else: 
                dt_obj = raw_date

            ET.SubElement(parent, "Year").text = str(dt_obj.year)
            ET.SubElement(parent, "Month").text = str(dt_obj.month).zfill(2)
            ET.SubElement(parent, "Day").text = str(dt_obj.day).zfill(2)

        except Exception: 
            ET.SubElement(parent, "Year").text = "0000"          


    def _add_list_xml(self, parent, item_label, items): 
        for item in items: 
            child_node = ET.SubElement(parent, item_label)
            child_node.text = str(item)

    def _finalize_xml(self, root):
        return HEADER+ET.tostring(root, encoding="unicode")

