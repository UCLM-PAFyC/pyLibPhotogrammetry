import xmltodict
import pprint
import json

input_filename = "E:\\dev\\python\\qgis_plugins\\PhotogrammetryTools\\docs\\xmltodict\\markers_micasenses_rededge.xml"
# input_filename = "E:\\dev\\python\\qgis_plugins\\PhotogrammetryTools\\docs\\xmltodict\\markers_micasenses_rededge_bad.xml"
output_filename = "E:\\dev\\python\\qgis_plugins\\PhotogrammetryTools\\docs\\xmltodict\\markers_micasenses_rededge.json"
output_filename_str = "E:\\dev\\python\\qgis_plugins\\PhotogrammetryTools\\docs\\xmltodict\\markers_micasenses_rededge.txt"

# Open the file and read the contents
with open(input_filename, 'r', encoding='utf-8') as file:
    my_xml = file.read()

# Use xmltodict to parse and convert 
# the XML document
try:
    my_dict = xmltodict.parse(my_xml)
except xmltodict.expat.ExpatError as e:
    kk = str(e)
    yo = 1

# json_str = json.dumps(my_dict, indent=4)
# json_str = json.dumps(my_dict)
json_str = str(my_dict)
with open(output_filename_str, "w") as f:
    f.write(json_str)

# pp = pprint.PrettyPrinter(indent=4)
# pp.pprint(json.dumps(doc))