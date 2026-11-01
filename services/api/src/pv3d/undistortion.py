"""Calibrated image rectification and explicitly derived subpixel model points.

Raster coordinates use integer centres. COLMAP projection uses corner coordinates
(raster +.5). VGGT's predicted K unprojects model-grid integer centres directly.
"""

import cv2
import numpy as np

from .metric_benchmark import camera_ray


def project_fisheye(normal_xy, params):
    xy = np.asarray(normal_xy, dtype=np.float64)
    radius = np.linalg.norm(xy, axis=-1)
    factor = np.divide(np.arctan(radius), radius, out=np.ones_like(radius), where=radius > 1e-15)
    u, v = (xy*factor[..., None])[..., 0], (xy*factor[..., None])[..., 1]
    fx, fy, cx, cy, k1, k2, p1, p2, k3, k4, sx1, sy1 = params
    r2 = u*u + v*v
    radial = k1*r2 + k2*r2**2 + k3*r2**3 + k4*r2**4
    du = u*radial + 2*p1*u*v + p2*(r2+2*u*u) + sx1*r2
    dv = v*radial + 2*p2*u*v + p1*(r2+2*v*v) + sy1*r2
    return np.stack((fx*(u+du)+cx, fy*(v+dv)+cy), axis=-1)


def project_pinhole(camera_xyz, k):
    homogeneous = np.asarray(camera_xyz) @ np.asarray(k).T
    return homogeneous[..., :2] / homogeneous[..., 2, None] - .5


def pinhole_to_source(pixel_xy, params, k):
    pixel = np.asarray(pixel_xy, dtype=np.float64)
    homogeneous = np.concatenate((pixel+.5, np.ones((*pixel.shape[:-1], 1))), axis=-1)
    ray = homogeneous @ np.linalg.inv(k).T
    return project_fisheye(ray[..., :2] / ray[..., 2, None], params) - .5


def full_field_camera(params, image_size, samples=257, margin=.002):
    """Envelope sampled source pixel-centre boundary rays without a fitted crop."""
    width, height = image_size
    xs, ys = np.linspace(.5, width-.5, samples), np.linspace(.5, height-.5, samples)
    boundary = ([*zip(xs, np.full(samples, .5), strict=True)]
                + [*zip(xs, np.full(samples, height-.5), strict=True)]
                + [*zip(np.full(samples, .5), ys, strict=True)]
                + [*zip(np.full(samples, width-.5), ys, strict=True)])
    rays = np.array([camera_ray(xy, params)[:2] for xy in boundary])
    low, high = rays.min(axis=0), rays.max(axis=0)
    ratio = params[1] / params[0]
    fx = min((width-1)/(high[0]-low[0]), (height-1)/(high[1]-low[1])/ratio) * (1-margin)
    fy = fx*ratio
    cx, cy = np.array([width, height])/2 - [fx, fy]*(low+high)/2
    return np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=float)


def remap_rgb(rgb, map_xy):
    return cv2.remap(rgb, np.asarray(map_xy[..., 0], np.float32),
                     np.asarray(map_xy[..., 1], np.float32), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))


def rectify_rgb(rgb, params, k, chunk_rows=128):
    height, width = rgb.shape[:2]
    output, valid = np.empty_like(rgb), np.empty((height, width), bool)
    for start in range(0, height, chunk_rows):
        stop = min(start+chunk_rows, height)
        yy, xx = np.mgrid[start:stop, 0:width]
        mapped = pinhole_to_source(np.stack((xx, yy), axis=-1), params, k)
        output[start:stop] = remap_rgb(rgb, mapped)
        valid[start:stop] = (np.isfinite(mapped).all(axis=-1)
                             & (mapped[..., 0] >= 0) & (mapped[..., 0] <= width-1)
                             & (mapped[..., 1] >= 0) & (mapped[..., 1] <= height-1))
    return output, valid


def model_support_mask(photo_valid, rect, input_size, *, mapping_rect=None):
    """Conservative PIL-bicubic resize footprint, not nearest-mask interpolation.

    The bicubic downsampling radius is2 source pixels times the reduction factor.
    An additional2-pixel guard covers rounding/nearest lookup. Erode before sampling.
    """
    left, top, right, bottom = map(int, rect)
    height, width = photo_valid.shape
    ml, mt, mr, mb = np.asarray(rect if mapping_rect is None else mapping_rect, dtype=float)
    if not (0 <= left <= ml < mr <= right <= input_size and 0 <= top <= mt < mb <= bottom <= input_size):
        raise ValueError("INVALID_CONTINUOUS_IMAGE_MAPPING")
    radius = int(np.ceil(2*max(width/(mr-ml), height/(mb-mt))))+2
    kernel = np.ones((2*radius+1, 2*radius+1), np.uint8)
    safe = cv2.erode(np.asarray(photo_valid, np.uint8), kernel,
                     borderType=cv2.BORDER_CONSTANT, borderValue=0).astype(bool)
    yy, xx = np.indices((bottom-top, right-left))
    px = np.rint((xx+left+.5-ml)*width/(mr-ml)-.5).astype(int)
    py = np.rint((yy+top+.5-mt)*height/(mb-mt)-.5).astype(int)
    inside = (px >= 0) & (px < width) & (py >= 0) & (py < height)
    mask = np.zeros((input_size, input_size), bool)
    mask[top:bottom, left:right] = inside & safe[np.clip(py, 0, height-1), np.clip(px, 0, width-1)]
    return mask


def bilinear_footprint(grid_xy, rect, support_mask):
    point = np.asarray(grid_xy, dtype=float)
    left, top, right, bottom = rect
    if point.shape != (2,) or not np.isfinite(point).all():
        raise ValueError("SAMPLING_OUTSIDE_CONTENT")
    x, y = point
    if not (left <= x <= right-1 and top <= y <= bottom-1):
        raise ValueError("SAMPLING_OUTSIDE_CONTENT")
    x0, y0 = np.floor(point).astype(int)
    x1, y1 = min(x0+1, int(right)-1), min(y0+1, int(bottom)-1)
    dx, dy = x-x0, y-y0
    positions = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
    weights = [(1-dx)*(1-dy), dx*(1-dy), (1-dx)*dy, dx*dy]
    if any(not support_mask[py, px] for px, py in positions):
        raise ValueError("SAMPLING_INVALID_IMAGE_SUPPORT")
    return positions, np.asarray(weights)


def unproject_depth(grid_xy, depth_z, k, extrinsic):
    # No +.5 here: VGGT unprojects meshgrid arange(width/height).
    camera_xyz = np.linalg.solve(k, [*grid_xy, 1]) * depth_z
    rotation, translation = extrinsic[:, :3], extrinsic[:, 3]
    world_xyz = rotation.T @ (camera_xyz-translation)
    return camera_xyz, world_xyz


def grid_camera_matrix(photo_k, rect, photo_size):
    left, top, right, bottom = rect
    sx, sy = np.array([right-left, bottom-top])/photo_size
    # COLMAP corner-origin photo K -> VGGT integer-centre grid K.
    transform = np.array([[sx, 0, left-.5], [0, sy, top-.5], [0, 0, 1]])
    return transform @ photo_k


def sample_camera_depth(geometry, grid_xy, support_mask, view=0):
    positions, weights = bilinear_footprint(grid_xy, geometry["rects"][view], support_mask)
    values = np.array([geometry["depth"][view, y, x] for x, y in positions], dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("SAMPLING_INVALID_PREDICTED_DEPTH")
    z = float(values @ weights)
    k, extrinsic = geometry["intrinsics"][view], geometry["extrinsics"][view]
    camera_xyz, world_xyz = unproject_depth(grid_xy, z, k, extrinsic)
    if not np.isfinite(world_xyz).all():
        raise ValueError("SAMPLING_INVALID_CAMERA")
    neighbours = []
    for (x, y), weight, depth in zip(positions, weights, values, strict=True):
        confidence = float(geometry["confidence"][view, y, x])
        neighbours.append({"x": int(x), "y": int(y), "weight": float(weight), "depth_z": float(depth),
                           "confidence_raw": confidence if np.isfinite(confidence) else None})
    return {"sampling": "bilinear_camera_Z_then_predicted_camera_unprojection", "grid_xy": list(grid_xy),
            "depth_z": z, "relative_neighbour_depth_spread": float(np.ptp(values)/z),
            "camera_xyz": camera_xyz.tolist(), "world_xyz": world_xyz.tolist(), "neighbours": neighbours,
            "intrinsics": k.tolist(), "extrinsics": extrinsic.tolist()}
