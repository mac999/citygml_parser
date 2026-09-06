"""
CityGML JSON conversion.

Author:
	Taewook Kang (laputa99999@gmail.com)

Date:
	2025-01-02
"""
import json, argparse
from citygml_parser3 import *
from xsdata.formats.dataclass.parsers import XmlParser

def convert_citygml_to_json(input_file: str, output_file: str):
	# read CityGML file
	parser = XmlParser()
	model = parser.parse(input_file)

	class CustomEncoder(json.JSONEncoder):
		def default(self, obj):
			if hasattr(obj, '__dict__'):
				return obj.__dict__
			return super().default(obj)

	model_dict = model.__dict__
	model_methods = [method for method in dir(model) if callable(getattr(model, method)) and not method.startswith("__")]
	json_model = json.dumps({"attributes": model_dict, "methods": model_methods}, indent=2, cls=CustomEncoder)

	# save the json_model to a file
	with open(output_file, 'w') as f:
		f.write(json_model)

	return json_model

def main():
	# parse arguments
	parser = argparse.ArgumentParser(description='Convert CityGML file to JSON.')
	parser.add_argument('--input', type=str, default='./sample/CityGML_3.gml', help='Input CityGML file')
	parser.add_argument('--output', type=str, default='./CityGML_3.json', help='Output JSON file')
 
	args = parser.parse_args()

	# convert CityGML to JSON
	convert_citygml_to_json(args.input, args.output)
	print("CityGML file converted to JSON.")


if __name__ == "__main__":
	main()
