"""ETH3D reference geometry helpers. Reference data never enters model inference.

THIN_PRISM_FISHEYE equations follow COLMAP 3.11.1 sensor/models.h.
COLMAP pixel coordinates use pixel corners: raster element [y,x] has center
(x+.5,y+.5). ETH3D depth is camera Z, in metres, not ray range.
"""

import numpy as np
from scipy.optimize import root


def camera_project(normal_xy, params):
    fx, fy, cx, cy, k1, k2, p1, p2, k3, k4, sx1, sy1 = params
    xy = np.asarray(normal_xy, dtype=float)
    radius = np.linalg.norm(xy)
    u, v = xy * (np.arctan(radius) / radius if radius > 1e-15 else 1.0)
    r2 = u*u + v*v
    radial = k1*r2 + k2*r2**2 + k3*r2**3 + k4*r2**4
    du = u*radial + 2*p1*u*v + p2*(r2 + 2*u*u) + sx1*r2
    dv = v*radial + 2*p2*u*v + p1*(r2 + 2*v*v) + sy1*r2
    return np.array([fx*(u+du)+cx, fy*(v+dv)+cy])


def camera_ray(pixel_xy, params):
    pixel = np.asarray(pixel_xy, float)
    if len(params) != 12 or not np.isfinite([*params, *pixel]).all():
        raise ValueError("INVALID_CAMERA")
    initial = (pixel - params[2:4]) / params[:2]
    solved = root(lambda xy: camera_project(xy, params) - pixel, initial, tol=1e-11)
    if not solved.success or np.linalg.norm(camera_project(solved.x, params) - pixel) > 1e-6:
        raise ValueError("CAMERA_INVERSE_FAILED")
    return np.array([*solved.x, 1.0])


def grid_to_photo(grid_xy, rect, photo_size):
    left, top, right, bottom = rect
    return (((np.asarray(grid_xy) + .5 - [left, top]) * photo_size
             / [right-left, bottom-top]) - .5).tolist()


def photo_to_grid(photo_xy, rect, photo_size):
    left, top, right, bottom = rect
    return (((np.asarray(photo_xy) + .5) * [right-left, bottom-top]
             / photo_size) + [left, top] - .5).tolist()


def read_depth(path, width, height):
    if path.stat().st_size != width * height * 4:
        raise ValueError("DEPTH_BYTE_COUNT")
    return np.memmap(path, dtype="<f4", mode="r", shape=(height, width))


def reference_point(depth, pixel_xy, params, radius=10, max_shift=3.0, max_spread=.03):
    """Use nearest finite measured depth, rejecting gaps and depth discontinuities.

    The 21x21 neighbourhood needs >=20 measured pixels and <=30 mm depth spread
    (5th--95th percentile). This is a selection guard, not an uncertainty claim.
    The selected Z must also be within30 mm of the local supported-depth median,
    so a single foreground spike cannot hide outside the 5--95% percentiles.
    No depth is inpainted/interpolated. Pixel movement and support are retained.
    """
    pixel = np.asarray(pixel_xy, float)
    height, width = depth.shape
    if pixel.shape != (2,) or not np.isfinite(pixel).all():
        raise ValueError("REFERENCE_OUTSIDE_IMAGE")
    x, y = np.rint(pixel).astype(int)
    if x-radius < 0 or y-radius < 0 or x+radius >= width or y+radius >= height:
        raise ValueError("REFERENCE_OUTSIDE_IMAGE")
    patch = np.asarray(depth[y-radius:y+radius+1, x-radius:x+radius+1])
    valid = np.isfinite(patch) & (patch > 0)
    yy, xx = np.nonzero(valid)
    if len(xx) < 20:
        raise ValueError("INSUFFICIENT_REFERENCE_DEPTH")
    spread = float(np.percentile(patch[valid], 95) - np.percentile(patch[valid], 5))
    if spread > max_spread:
        raise ValueError("DEPTH_DISCONTINUITY")
    candidates = np.column_stack((xx + x-radius, yy + y-radius))
    shifts = np.linalg.norm(candidates-pixel, axis=1)
    best = int(np.argmin(shifts))
    if shifts[best] > max_shift:
        raise ValueError("NO_NEARBY_REFERENCE_DEPTH")
    px, py = candidates[best]
    z = float(depth[py, px])
    selected_deviation = abs(z - float(np.median(patch[valid])))
    if selected_deviation > max_spread:
        raise ValueError("REFERENCE_DEPTH_OUTLIER")
    return {"requested_pixel_xy": pixel.tolist(), "sample_pixel_xy": [int(px), int(py)],
            "sample_shift_px": float(shifts[best]), "depth_z_m": z,
            "support_count": len(xx), "depth_spread_m": spread,
            "selected_depth_deviation_m": selected_deviation,
            "xyz_m": (camera_ray([px+.5, py+.5], params) * z).tolist()}
