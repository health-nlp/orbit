import xml.etree.ElementTree as ET
import json
from searchresult import ESearch  # Angenommen deine Klasse liegt in searchresult.py

# --------------------
# MOCK TESTING ESEARCH:
# --------------------
def test_search_output():
    print("--- Starte Mock-Test für ESearch Response ---\n")

    # 1. simulating data that would come from lucene 
    mock_id_list = ["3829102", "1928374", "5566778"]
    mock_query = "cancer[mesh] AND therapy[title]"
    
    # 2. generate the esearch object
    # testcase: XML
    res_xml = ESearch(
        format="xml",
        count="150",
        retmax="3",
        retstart="0",
        id_list=mock_id_list,
        querytranslation=mock_query,
        translationset={"from": "cancer therapy", "to": mock_query}
    )

    # testcase: JSON
    res_json = ESearch(
        format="json",
        count="150",
        retmax="3",
        retstart="0",
        id_list=mock_id_list,
        querytranslation=mock_query,
        translationset={"from": "cancer therapy", "to": mock_query}
    )

    # expected output structure in json format for esearch
    expected_structure = {
        "header": {
            "type": "esearch",
            "version": "0.3-openpm",
        },
        "querytranslation": mock_query,
        "translationset": {
            "from": "cancer therapy",
            "to": mock_query
        },
        "esearchresult": {
            "count": "150",
            "retmax": "3",
            "retstart": "0",
            "id_list": mock_id_list
        }
    }

    # 3. check JSON-output
    print("TEST 1: JSON OUTPUT")
    json_data = res_json.to_json()
    print(json.dumps(json_data, indent=4))
    assert json_data["header"]["type"] == "esearch"
    assert len(json_data["esearchresult"]["id_list"]) == 3
    assert json_data["esearchresult"]["count"] == "150"
    assert json_data["translationset"]["from"] == "cancer therapy"
    assert json_data["translationset"]["to"] == mock_query
    assert json_data == expected_structure

    print("✅ JSON validation successfull.\n")

    # 4. checking XML structure
    print("TEST 2: XML OUTPUT")
    xml_string = res_xml.to_xml()
    print(xml_string)
    
    # validation: valid XML?
    root = ET.fromstring(xml_string)
    assert root.tag == "esearchResponse"
    assert root.find("count").text == "150"
    
    # check whether IDs are there according to subelements
    ids = root.find("id_list")
    if ids is not None and len(ids) > 0:
        print(f"✅ xml-structure contains {len(ids)} ID-subelements.")
    
    print("✅ XML validation successfull.")


# --------------------
# MOCK TESTING EFETCH:
# --------------------

# TODO to be implemented


if __name__ == "__main__":
    test_search_output()