import numpy as np
from cartopy import crs as ccrs
from shapely.geometry import (MultiLineString, LineString,
                              MultiPolygon, Polygon)

from .element import RGB


def wrap_lons(lons, base, period):
    """
    Wrap longitude values into the range between base and base+period.
    """
    lons = lons.astype(np.float64)
    return ((lons - base + period * 2) % period) + base


def project_extents(extents, src_proj, dest_proj, tol=1e-6):
    x1, y1, x2, y2 = extents

    # Limit latitudes
    cy1, cy2 = src_proj.y_limits
    if y1 < cy1: y1 = cy1
    if y2 > cy2:  y2 = cy2

    # Wrap longitudes
    cx1, cx2 = src_proj.x_limits
    if isinstance(src_proj, ccrs._CylindricalProjection):
        lons = wrap_lons(np.linspace(x1, x2, 10000), -180., 360.)
        x1, x2 = lons.min(), lons.max()
    else:
        if x1 < cx1: x1 = cx1
        if x2 > cx2: x2 = cx2

    # Offset with tolerances
    x1 += tol
    x2 -= tol
    y1 += tol
    y2 -= tol

    domain_in_src_proj = Polygon([[x1, y1], [x2, y1],
                                  [x2, y2], [x1, y2],
                                  [x1, y1]])
    boundary_poly = Polygon(src_proj.boundary)
    if src_proj != dest_proj:
        # Erode boundary by threshold to avoid transform issues.
        # This is a workaround for numerical issues at the boundary.
        eroded_boundary = boundary_poly.buffer(-src_proj.threshold)
        geom_in_src_proj = eroded_boundary.intersection(
            domain_in_src_proj)
        geom_in_crs = dest_proj.project_geometry(geom_in_src_proj, src_proj)
    else:
        geom_in_crs = boundary_poly.intersection(domain_in_src_proj)
    return geom_in_crs.bounds


def path_to_geom(path):
    lines = []
    for path in path.data:
        lines.append(LineString(path))
    return MultiLineString(lines)


def polygon_to_geom(polygon):
    polys = []
    for poly in polygon.data:
        polys.append(Polygon(poly))
    return MultiPolygon(polys)


def geom_to_array(geoms):
    xs, ys = [], []
    for geom in geoms:
        if hasattr(geom, 'exterior'):
            xs.append(np.array(geom.exterior.coords.xy[0]))
            ys.append(np.array(geom.exterior.coords.xy[1]))
        else:
            geom_data = geom.array_interface()
            arr = np.array(geom_data['data']).reshape(geom_data['shape'])
            xs.append(arr[:, 0])
            ys.append(arr[:, 1])
    return xs, ys


def geo_mesh(element):
    """
    Get mesh data from a 2D Element ensuring that if the data is
    on a cylindrical coordinate system and wraps globally that data
    actually wraps around.
    """
    if isinstance(element, RGB):
        xs, ys = (element.dimension_values(i, False, False)
                  for i in range(2))
        zs = np.dstack([element.dimension_values(i, False, False) for i in range(2, 2+len(element.vdims))])
    else:
        xs, ys, zs = (element.dimension_values(i, False, False)
                      for i in range(3))
    lon0, lon1 = element.range(0)
    if isinstance(element.crs, ccrs._CylindricalProjection) and (lon1 - lon0) == 360:
        xs = np.append(xs, xs[0:1] + 360, axis=0)
        zs = np.ma.concatenate([zs, zs[:, 0:1]], axis=1)
    return xs, ys, zs

