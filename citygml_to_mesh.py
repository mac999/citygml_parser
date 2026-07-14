"""
CityGML to mesh conversion.

Author:
	Taewook Kang (laputa99999@gmail.com)

Date:
	2025-02-10, 0.1, Initial version. Support only building geometry's boundary.
	2026-07-14, 0.2, Rewrite geometry extraction:
		- Resolve gml:Polygon geometry for every CityObject (not only buildings),
		  so roads, vegetation, city furniture, terrain, etc. are meshed too.
		- Triangulate arbitrary planar polygons (concave shapes and interior
		  holes) instead of emitting a single n-gon face, which trimesh cannot
		  render correctly.
		- Handle xlink:href surface references (e.g. lodXSolid shells that point
		  to shared boundary polygons) via de-duplication by gml:id, so a
		  polygon is meshed once regardless of how many times it is referenced.

Reference:
	https://trimesh.org/
"""
import argparse
from dataclasses import is_dataclass, fields
import numpy as np, trimesh
from tqdm import tqdm
from shapely.geometry import Polygon as ShapelyPolygon
from citygml_parser3 import Polygon
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.config import ParserConfig


def iter_polygons(root):
	"""Yield every unique gml:Polygon in the parsed CityGML model.

	The model is a tree of xsdata dataclasses. We walk it iteratively and
	collect Polygon instances. Polygons are de-duplicated by their gml:id so
	that a surface referenced from several places (e.g. an inline boundary
	polygon that a solid shell also points to via xlink:href) is meshed once.
	"""
	stack = [root]
	visited = set()          # object ids already expanded (avoid re-walking)
	seen_gml_ids = set()     # gml:id of polygons already yielded

	while stack:
		obj = stack.pop()

		if isinstance(obj, (list, tuple)):
			stack.extend(obj)
			continue
		if not is_dataclass(obj):
			continue

		obj_id = id(obj)
		if obj_id in visited:
			continue
		visited.add(obj_id)

		if isinstance(obj, Polygon):
			if obj.id is None or obj.id not in seen_gml_ids:
				if obj.id is not None:
					seen_gml_ids.add(obj.id)
				yield obj
			continue  # a polygon does not contain other polygons

		# Descend into the dataclass fields.
		for f in fields(obj):
			stack.append(getattr(obj, f.name))


def ring_to_coords(linear_ring):
	"""Return the ring vertices as an (N, 3) array, or None if unavailable.

	The closing vertex (identical to the first one) is removed so the ring is
	an open polygon suitable for triangulation.
	"""
	if linear_ring is None:
		return None

	coords = None
	pos_list = linear_ring.pos_list
	if pos_list is not None and pos_list.value:
		dim = int(pos_list.srs_dimension) if pos_list.srs_dimension else 3
		flat = np.asarray(pos_list.value, dtype=float)
		if dim < 2 or len(flat) < dim:
			return None
		coords = flat[: len(flat) - (len(flat) % dim)].reshape(-1, dim)
	elif linear_ring.pos:
		# Coordinates given as a sequence of individual <gml:pos> elements.
		pts = [p.value for p in linear_ring.pos if p.value]
		if pts:
			coords = np.asarray(pts, dtype=float)

	if coords is None or len(coords) < 3:
		return None

	# Force 3D: keep the first three components, or pad Z with zeros for 2D data.
	if coords.shape[1] >= 3:
		coords = coords[:, :3]
	else:
		coords = np.column_stack([coords, np.zeros(len(coords))])

	# Drop the duplicated closing vertex.
	if len(coords) > 1 and np.allclose(coords[0], coords[-1]):
		coords = coords[:-1]

	return coords if len(coords) >= 3 else None


def newell_normal(points):
	"""Compute a unit normal of a planar polygon (Newell's method).

	Newell's method is robust for non-convex and slightly non-planar rings.
	Returns None for degenerate (collinear/zero-area) rings.
	"""
	normal = np.zeros(3)
	count = len(points)
	for i in range(count):
		cur = points[i]
		nxt = points[(i + 1) % count]
		normal[0] += (cur[1] - nxt[1]) * (cur[2] + nxt[2])
		normal[1] += (cur[2] - nxt[2]) * (cur[0] + nxt[0])
		normal[2] += (cur[0] - nxt[0]) * (cur[1] + nxt[1])
	length = np.linalg.norm(normal)
	return normal / length if length > 0 else None


def plane_basis(normal):
	"""Return two orthonormal in-plane axes (u, v) for the given normal."""
	helper = np.array([1.0, 0.0, 0.0]) if abs(normal[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
	u = np.cross(helper, normal)
	u /= np.linalg.norm(u)
	v = np.cross(normal, u)
	return u, v


def polygon_to_trimesh(polygon):
	"""Triangulate one gml:Polygon (with optional holes) into a trimesh.Trimesh.

	The polygon is assumed planar: we project its 3D vertices onto the polygon
	plane, triangulate in 2D (earcut handles concave shapes and holes), then
	lift the 2D vertices back to 3D. Returns None on degenerate input.
	"""
	if polygon.exterior is None:
		return None
	exterior = ring_to_coords(polygon.exterior.linear_ring)
	if exterior is None:
		return None

	normal = newell_normal(exterior)
	if normal is None:
		return None

	u, v = plane_basis(normal)
	origin = exterior[0]

	def to_2d(coords):
		delta = coords - origin
		return np.column_stack([delta @ u, delta @ v])

	shell_2d = to_2d(exterior)
	holes_2d = []
	for interior in polygon.interior:
		hole = ring_to_coords(interior.linear_ring)
		if hole is not None and len(hole) >= 3:
			holes_2d.append(to_2d(hole))

	try:
		shapely_poly = ShapelyPolygon(shell_2d, holes_2d)
		vertices_2d, faces = trimesh.creation.triangulate_polygon(shapely_poly, engine="earcut")
	except Exception:
		return None
	if faces is None or len(faces) == 0:
		return None

	# Lift the 2D triangulation back onto the polygon plane: p = origin + x*u + y*v.
	vertices_3d = origin + np.outer(vertices_2d[:, 0], u) + np.outer(vertices_2d[:, 1], v)
	return trimesh.Trimesh(vertices=vertices_3d, faces=faces, process=False)


def parse_citygml(input_file):
	"""Parse a CityGML file and return a flat list of triangulated meshes."""
	config = ParserConfig(
		load_dtd=True,
		process_xinclude=True,
		fail_on_unknown_properties=False,
		fail_on_unknown_attributes=False,
		fail_on_converter_warnings=True,
	)
	model = XmlParser(config).parse(input_file)

	mesh_list = []
	for polygon in tqdm(list(iter_polygons(model))):
		mesh = polygon_to_trimesh(polygon)
		if mesh is not None and len(mesh.faces) > 0:
			mesh_list.append(mesh)
	return mesh_list


def convert_mesh(input_gml_fname, output_mesh_fname):
	mesh = None
	try:
		mesh_list = parse_citygml(input_gml_fname)
		if not mesh_list:
			print("No polygon geometry found in the CityGML file.")
			return mesh
		mesh = trimesh.util.concatenate(mesh_list)
		mesh.export(output_mesh_fname)	# STL, binary PLY, ASCII OFF, OBJ, GLTF/GLB 2.0, COLLADA, etc.
		print(f"Meshed {len(mesh_list)} polygons ({len(mesh.faces)} triangles).")
	except Exception as e:
		print(f'Error: {e}')
		return mesh
	return mesh


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='CityGML example to convert to mesh.')
	parser.add_argument('--input', type=str, default='./sample/ManhattanSmall.gml', help='Input CityGML file')
	parser.add_argument('--output', type=str, default='./mesh/ManhattanSmall.glb', help='Output mesh file. STL, binary PLY, ASCII OFF, OBJ, GLTF/GLB 2.0, COLLADA')
	parser.add_argument('--show', type=int, default=0, help='Show mesh file. 0=No, 1=Yes')
	args = parser.parse_args()

	try:
		mesh = convert_mesh(args.input, args.output)
		if args.show == 1 and mesh is not None:
			mesh.show()
		print("CityGML file converted to mesh.")
	except Exception as e:
		print("CityGML file conversion failed.")
		print(e)
