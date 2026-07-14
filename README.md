# CityGML Parser

**CityGML 3.0** (Python version) parser for reading, writing, and converting CityGML files into JSON using Python. Since there is no suitable, easy-to-use, Python-based CityGML 3.0 parser available, I developed this. In the future, this parser is planned to be used to physically implement [ISO/TS 19166 BIM-GIS conceptual mapping](https://github.com/mac999/ISO19166-B2GM). In addition, if you need landxml parser (python version), refer to [landxml parser](https://github.com/mac999/landxml_parser). The parser function will be further updated.</br>
<img src="https://github.com/mac999/citygml_parser/blob/main/docs/img12.png" height="250"></img>

## **🚀 Features**
Version 0.1 
- Parse **CityGML 3.0** files into Python objects. 
- Modify CityGML objects and write back to XML format.
- Convert **CityGML to JSON** for easier data processing and integration.
- Convert **CityGML to MESH** (triangulated geometry for all city objects, interior holes and `xlink:href` surface references supported).
</br>[Download CityGML 3.0_parser class with members HTML document](https://raw.githubusercontent.com/mac999/citygml_parser/refs/heads/main/docs/citygml_parser3.html)
---
<img src="https://github.com/mac999/citygml_parser/blob/main/docs/img1.PNG" height="250"></img>
<img src="https://github.com/mac999/citygml_parser/blob/main/docs/img2.png" height="250"></br>house</img></br>
<img src="https://github.com/mac999/citygml_parser/blob/main/docs/img3.png" width="650"></br>building</img></br>
<img src="https://github.com/mac999/citygml_parser/blob/main/docs/img5.PNG" width="650"></br>building</img></br>
<img src="https://github.com/mac999/citygml_parser/blob/main/docs/img4.PNG" width="650"></br>road</img></br>
<img src="https://github.com/mac999/citygml_parser/blob/main/docs/img10.PNG" width="330"></img>
<img src="https://github.com/mac999/citygml_parser/blob/main/docs/img11.PNG" width="320"></br>city</img></br>
<img src="https://github.com/mac999/citygml_parser/blob/main/docs/img6.PNG" width="650"></br>difference between input and output citygml</img>
## Next Plan 
- Support **CityGML 2.0**. In addition, there is [citygml2 to citygml3 convertor](https://github.com/tum-gis/citygml2-to-citygml3). It's working.
- Fix name space problem
---

## **📂 Installation and usage**
To install the required dependencies, run:

```bash
pip install numpy xsdata lxml pdoc trimesh shapely
```
Converter usage
```bash
python citygml_json --input ./sample/CityGML_3.gml --output ./CityGML_3.json
python citygml_converter --input ./sample/CityGML_3.gml --output ./output.gml
```

---

## **📄 Usage**
### **📍 1. Read a CityGML File**
```python
from citygml_parser3 import *
from xsdata.formats.dataclass.parsers import XmlParser

# Initialize parser
parser = XmlParser()

# Parse CityGML file
model = parser.parse("./sample/1_SimpleBuilding/CityGML_3.gml")

# Print parsed model
print(model)
```

---

### **📍 2. List CityGML buliding and surface information**
```python
city_objects = model.city_object_member

for city_object in city_objects:
	building = city_object.building

	print(f'building id: {building.id}')
	print(f'building name: {building.name}')

	try:
		for bound in building.boundary:
			wall = bound.wall_surface
			if wall:
				print(f'wall id: {wall.id}')
			roof = bound.roof_surface
			if roof:
				print(f'roof id: {roof.id}')
			floor = bound.floor_surface
			if floor:
				print(f'floor id: {floor.id}')
			ground = bound.ground_surface
			if ground:
				print(f'ground id: {ground.id}')
			
		if building.lod1_solid:
			print(f'building lod1_solid')
			for sf in building.lod2_solid.solid.exterior.shell.surface_member:
				print(f'surface: {sf.href}')			
		if building.lod2_solid:
			print(f'building lod2_solid')
			for sf in building.lod2_solid.solid.exterior.shell.surface_member:
				print(f'surface: {sf.href}')
		if building.lod3_solid:
			print(f'building lod3_solid')
			for sf in building.lod2_solid.solid.exterior.shell.surface_member:
				print(f'surface: {sf.href}')
		if building.lod4_solid:
			print(f'building lod4_solid')
			for sf in building.lod2_solid.solid.exterior.shell.surface_member:
				print(f'surface: {sf.href}')
	except Exception as e:
		pass
```
<img src="https://github.com/mac999/citygml_parser/blob/main/docs/img8.PNG" width="300"></br>result</img></br>

---

### **📍 3. Modify and Write CityGML File**
```python
from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig
from pathlib import Path

config = SerializerConfig(indent="  ")
context = XmlContext()
serializer = XmlSerializer(context=context, config=config)

# Output file path
path = Path("CityGML_3_output.gml")

# Write back to CityGML format
with path.open("w") as fp:
    serializer.write(fp, model)
```

---

### **📍 4. Convert CityGML to JSON**
You can convert CityGML files to JSON format using the included `citygml_json.py` script.

#### **📌 Convert via Command Line**
```bash
python citygml_json.py --input_file ./sample/CityGML_3.gml --output_file ./CityGML_3.json
```

#### **📌 Convert using Python**
```python
from citygml_json import convert_citygml_to_json

input_gml = "./sample/CityGML_3.gml"
output_json = "./CityGML_3.json"

convert_citygml_to_json(input_gml, output_json)
print("CityGML successfully converted to JSON.")
```

### **📍 5. Convert CityGML to MESH**
You can convert CityGML to MESH format. Every `gml:Polygon` in the model is triangulated, so any CityObject (buildings, roads, vegetation, city furniture, terrain, etc.) is meshed - not only buildings. Concave surfaces and interior rings (holes) are triangulated with earcut, and surfaces referenced through `xlink:href` (e.g. a `lodXSolid` shell pointing to shared boundary polygons) are de-duplicated by `gml:id` so each polygon is meshed once.
```bash
python citygml_to_mesh.py --input ./sample/CityGML_3.gml --output ./mesh/CityGML_3.glb
```
<img src="https://github.com/mac999/citygml_parser/blob/main/docs/citygml_mesh2.gif" width="600"></img>

---

## **📂 Project Structure**
```
citygml_parser/
│── citygml_parser3/       # CityGML parsing module
│── sample/                # Sample CityGML files
│── docs/                  # manual
│── citygml_parser_example.py  # Example 
│── citygml_converter.py  # CityGML conversion 
│── citygml_json.py       # CityGML to JSON conversion
│── citygml_to_mesh.py    # CityGML to Mesh conversion 
│── README.md             # Project documentation
```

---

## **👤 Author**
- **Name:** Taewook Kang  
- **Email:** [laputa99999@gmail.com](mailto:laputa99999@gmail.com)

---

## **📜 License**
This project is licensed under the **MIT License**.

---

## **🙌 Acknowledgments**
This project is inspired by **CityGML 3.0**, an OGC standard for 3D city modeling.
- 🔗 [https://www.ogc.org/standards/citygml](https://www.ogc.org/standards/citygml)
- 🔗 [https://github.com/tudelft3d/CityGML-schema-validation](https://github.com/tudelft3d/CityGML-schema-validation/tree/master)
- 🔗 [CityGML2-to-CityGML3](https://github.com/tum-gis/citygml2-to-citygml3)
- 🔗 [ISO/TS 19166 BIM-GIS conceptual mapping](https://github.com/mac999/ISO19166-B2GM)
