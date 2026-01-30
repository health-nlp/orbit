import json
import xml.etree.ElementTree as ET

class searchresult: 
    def __init__(self, format: str, error: str = None):
        self.format = format
        self.error = error

    def to_json(self):
        class_name = self.__class__.__name__.lower()

        data = {
            "header": self.get_header(class_name),
            "translationset": self.translationset,
            "querytranslation": self.querytranslation
        }

        if self.error: 
            data[f"{class_name}results"] = {"ERROR": str(self.error)}
        else: 
            excluded = ["format", "error", "querytranslation", "translationset"]
            result_content = {k: v for k, v in self.__dict__.items() if k not in excluded}
            data[f"{class_name}result"] = result_content

        return data
    
    def to_xml(self): 
        class_name = self.__class__.__name__.lower()
        
        root = ET.Element(f"{class_name}Response")

        if self.error: 
            err_tag = ET.SubElement(root, "ERROR")
            err_tag.text = str(self.error)
        else: 
            for key, value in self.__dict__.items():
                if key not in ["format", "error", "querytranslation", "translationset"]: 
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
    
    def get_header(self, search_type):
        return {
            "type": search_type,
            "version": "0.3-openpm"
        }
    


# Classes for each search-type
class ESearch(searchresult): 
    def __init__(self, format: str,
                 count: str, 
                 retmax: str,
                 retstart: str,
                 id_list: str,
                 querytranslation: str,
                 translationset: str = None,
                 error = None):
        super().__init__(format, error)
        
        self.count = count
        self.retmax = retmax
        self.retstart = retstart
        self.id_list = id_list
        self.querytranslation = querytranslation
        self.translationset = translationset

class EFetch(searchresult):
    def __init__(self, format: str, 
                 retmode: str,
                 article_dicts: list,
                 error = None):
        super().__init__(format, error)

        self.retmode = retmode
        self.article_dicts = article_dicts

class ESummary(searchresult): 
    def __init__(self, format: str,
                 retstart: str,
                 retmax: str, 
                 retmode: str,  
                 error = None):
        super().__init__(format, error)

        self.retstart = retstart
        self.retmax = retmax
        self.retmode = retmode
        
