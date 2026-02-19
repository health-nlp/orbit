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

class EInfo: 
    """
    Implements the PubMed-like EInfo endpoint

    Provides statistics for a single database,
    including lists of indexing fields and available link names
    """
    vm = lucene.getVMEnv()
    parser = PubmedQueryParser()
    fields = [
        {"Name":"ALL", "FullName":"All Fields", "Description":"All terms from all searchable fields", "IsDate":"N", "IsNumerical":"N", "SingleToken":"N", "Hierarchy":"N", "IsHidden":"N"},
        {"Name":"UID", "FullName":"UID", "Description": "Unique number assigned to publication", "IsDate":"N", "IsNumerical":"Y", "SingleToken":"N", "Hierarchy":"N", "IsHidden":"N"},
        {"Name":"TITL", "FullName":"Title", "Description":"Words in title of publication", "IsDate":"N", "IsNumerical":"N", "SingleToken":"N", "Hierarchy":"N", "IsHidden":"N"},
        {"Name":"MESH", "FullName":"MeSH Terms", "Description":"Medical Subject Headings assigned to publication", "IsDate":"N", "IsNumerical":"N", "SingleToken":"Y", "Hierarchy":"Y", "IsHidden":"N"},
        {"Name":"MAJR", "FullName":"MeSH Major Topic", "Description":"MeSH terms of major importance to publication", "IsDate":"N", "IsNumerical":"N", "SingleToken":"Y", "Hierarchy":"Y", "IsHidden":"N"},
        {"Name":"PDAT", "FullName":"Date - Publication", "Description":"Date of publication", "IsDate":"Y", "IsNumerical":"N", "SingleToken":"Y", "Hierarchy":"N", "IsHidden":"N"},
        {"Name":"PTYP", "FullName":"Publication Type", "Description":"Type of publication (e.g., review)", "IsDate":"N", "IsNumerical":"N", "SingleToken":"Y", "Hierarchy":"Y", "IsHidden":"N"},
        {"Name":"SUBH", "FullName":"MeSH Subheading", "Description":"Additional specificity for MeSH term", "IsDate":"N", "IsNumerical":"N", "SingleToken":"Y", "Hierarchy":"Y", "IsHidden":"N"},
        {"Name":"TIAB", "FullName":"Title/Abstract", "Description":"Free text associated with Abstract/Title", "IsDate":"N", "IsNumerical":"N", "SingleToken":"N", "Hierarchy":"N", "IsHidden":"N"},
        {"Name":"SUBH", "FullName":"MeSH Subheading", "Description":"Additional specificity for MeSH term", "IsDate":"N", "IsNumerical":"N", "SingleToken":"Y", "Hierarchy":"Y", "IsHidden":"N"},
    ]    
    
    def get_info(self): 
        """
        Return statistics for the pubmed database"
        """

        with _lock: 
            try: 
                if not self.vm.isCurrentThreadAttached():
                    self.vm.attachCurrentThread()

                header =  """<?xml version="1.0" ?>
                <!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2025//EN" "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_250101.dtd">
                """

                root = ET.Element("eInfoResult")
                db_info = ET.SubElement(root, "DbInfo")
                
                # --- general statistics ---
                db_name = ET.SubElement(db_info, "DbName")
                db_name.text = "pubmed"
                menu_name = ET.SubElement(db_info, "MenuName")
                menu_name.text = "PubMed"
                description = ET.SubElement(db_info, "Description")
                description.text = "PubMed bibliographic record"
                db_build = ET.SubElement(db_info, "DbBuild")
                db_build.text = "Build-2026.02.19.01.50"
                count = ET.SubElement(db_info, "Count")
                count.text = "40131104"
                lastupdate = ET.SubElement(db_info, "LastUpdate")
                lastupdate.text = "2026/02/19 01:50"

                field_list = ET.SubElement(db_info, "FieldList")
                for field in self.fields: 
                    self.add_field(field_list, **field)

                return Response(header + ET.tostring(root, encoding="unicode"),media_type="application/xml")

            
            except Exception as e: 
                raise e
                return f"<?xml version='1.0'?><error>{str(e)}</error>"
            



    def add_field(self, parent, Name: str, FullName: str, Description: str, IsDate: str, 
              IsNumerical: str, SingleToken: str, Hierarchy: str, IsHidden: str): 
    
        field = ET.SubElement(parent, "Field")

        ET.SubElement(field, "Name").text = Name
        ET.SubElement(field, "FullName").text = FullName
        ET.SubElement(field, "Description").text = Description
        ET.SubElement(field, "TermCount").text = ""
        ET.SubElement(field, "IsDate").text = IsDate
        ET.SubElement(field, "IsNumerical").text = IsNumerical
        ET.SubElement(field, "SingleToken").text = SingleToken
        ET.SubElement(field, "Hierarchy").text = Hierarchy
        ET.SubElement(field, "IsHidden").text = IsHidden