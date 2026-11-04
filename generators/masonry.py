# masonry.py: finds the joints of a retail picture and shapes each piece as a solid block.
import numpy as np
def blur(a, s):
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (np.pi * s) ** 2 * (fx * fx + fy * fy)), s=a.shape)
def joints_of(L, px):
    """The dark lines between pieces: darker than what is round them, thin."""
    d = blur(L, 5 * px) - blur(L, 0.6 * px)
    d = d / (d.std() + 1e-6)
    j = d > 0.55
    # Specks are not joints: a joint keeps company with more of itself along its line.
    keep = blur(j.astype(np.float32), 1.1 * px) > 0.34
    j = j & keep
    # A pit in a stone is no joint: a joint runs on, a pit is a little patch to itself.
    patches = cells_of(~j)
    ids = np.where(patches >= 0, patches, patches.max() + 1)
    areas = np.bincount(ids.ravel())
    areas[-1] = 0
    return j & (areas[ids] > 90 * px * px)
def cells_of(joint):
    """Each connected piece between the joints, wrapping as the picture repeats; -1 on a joint."""
    h, w = joint.shape
    lab = np.arange(h * w).reshape(h, w)
    lab[joint] = h * w + 1
    for _ in range(600):
        best = lab
        for ax, sh in ((0, 1), (0, -1), (1, 1), (1, -1)):
            best = np.minimum(best, np.where(joint, lab, np.roll(lab, sh, ax)))
        best = np.where(joint, h * w + 1, best)
        # Jump along chains so this converges in tens of passes.
        flat = best[~joint]
        best2 = best.copy()
        best2[~joint] = best.ravel()[np.minimum(flat, h * w - 1)]
        if (best2 == lab).all():
            break
        lab = best2
    lab[joint] = -1
    return lab
def survey(L, px):
    """How much the picture reads as pieces between joints: 0 not at all, 1 wholly."""
    j = joints_of(L, px)
    cov = float(j.mean())
    if not 0.05 <= cov <= 0.42:
        return 0.0, cov, 0
    lab = cells_of(j)
    ids, areas = np.unique(lab[lab >= 0], return_counts=True)
    if len(ids) == 0:
        return 0.0, cov, 0
    frac = areas / lab.size
    good = (frac > 0.003) & (frac < 0.4)
    covered = float(frac[good].sum()) / max(1e-6, 1 - cov)
    return covered, cov, int(good.sum())
def block_height(L, px, rng, depth_detail=0.2):
    """The picture as solid blocks: a recess at each joint, each block's face a little its own."""
    j = joints_of(L, px)
    lab = cells_of(j)
    h, w = L.shape
    solid = (~j).astype(np.float32)
    # A bevel: flat on the face, falling to the joint within about a retail texel and a half.
    b = blur(solid, 1.5 * px)
    bevel = np.clip((b - 0.5) / 0.42, 0, 1)
    bevel = bevel * bevel * (3 - 2 * bevel)
    ids = np.unique(lab[lab >= 0])
    n = int(lab.max()) + 2
    offset = np.zeros(n, np.float32); tx = np.zeros(n, np.float32); ty = np.zeros(n, np.float32)
    offset[ids] = rng.uniform(-0.09, 0.09, len(ids))
    tx[ids] = rng.uniform(-1, 1, len(ids)); ty[ids] = rng.uniform(-1, 1, len(ids))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    idx = np.where(lab >= 0, lab, n - 1)
    # A block's own lean, about its middle; wrapped pieces take the lean of their nearer half.
    area = np.bincount(idx.ravel(), minlength=n).astype(np.float32) + 1e-6
    cx = np.bincount(idx.ravel(), xx.ravel(), minlength=n) / area
    cy = np.bincount(idx.ravel(), yy.ravel(), minlength=n) / area
    radius = np.sqrt(area / np.pi) + 1
    lean = ((xx - cx[idx]) * tx[idx] + (yy - cy[idx]) * ty[idx]) / radius[idx]
    lean = np.clip(lean, -1.2, 1.2) * 0.05
    # Its own surface, from the picture's finer detail.
    detail = blur(L, 0.5 * px) - blur(L, 2.4 * px)
    detail = np.clip(detail / (detail.std() + 1e-6), -2.5, 2.5) * depth_detail / 2.5
    face = 0.62 + offset[idx] + lean + detail
    hgt = np.where(j, 0.0, 1.0) * bevel * np.clip(face, 0.2, 1.0)
    return blur(hgt.astype(np.float32), 0.35 * px), j
def thatch_height(L, px):
    """Straw: rolled bundles along the grain, each strand standing out of them."""
    gx = np.roll(L, -1, 1) - np.roll(L, 1, 1)
    gy = np.roll(L, -1, 0) - np.roll(L, 1, 0)
    # The grain runs the way the picture changes least.
    across_x = float((gx * gx).mean()) >= float((gy * gy).mean())
    def along(a, s):
        h, w = a.shape
        fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
        f = fy if across_x else fx
        return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (np.pi * s * f) ** 2), s=a.shape)
    def across(a, s):
        h, w = a.shape
        fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
        f = fx if across_x else fy
        return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (np.pi * s * f) ** 2), s=a.shape)
    g = along(L, 3 * px)
    strand = across(g, 0.35 * px) - across(g, 1.6 * px)
    bundle = across(g, 1.6 * px) - across(g, 7 * px)
    strand = strand / (strand.std() + 1e-6)
    bundle = bundle / (bundle.std() + 1e-6)
    return np.clip(0.55 + 0.14 * strand + 0.22 * bundle, 0, 1)
