#!/usr/bin/env python3
"""Make the window portraits for Jaildle Desk: one small pixel-art figure per person in data/portraits/.

For each photo it cuts the person out of the background (rembg), finds the face (OpenCV) so every head ends
up the same size and position, and reduces the figure to a few flat colours. The person's own clothes and body are kept.

Needs: pip install rembg onnxruntime opencv-python-headless   (the face model downloads itself on first run)
Usage: python3 tools/portraits.py [--force] [id ...]      (run build.py first so docs/i/ exists)
"""
import pathlib, sys
import cv2, numpy as np
from PIL import Image, ImageEnhance
from rembg import new_session, remove

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "docs" / "i", ROOT / "data" / "portraits"
W, H = 54, 64                  # canvas in art pixels; shown 4x
FACE_W, FACE_CX, CHIN_Y = 19, 27, 36
INK = (26, 24, 30)
session = new_session("isnet-general-use")    # cleaner than u2net_human_seg when other people stand behind the subject
MODEL = pathlib.Path.home() / ".cache" / "jaildle" / "yunet.onnx"
MODEL_URL = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
if not MODEL.exists():
    import subprocess
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-sSL", "-m", "120", "-o", str(MODEL), MODEL_URL], check=True)
detector = cv2.FaceDetectorYN.create(str(MODEL), "", (320, 320), 0.45, 0.3, 50)


def find_face(rgb, alpha):
    """(x, y, w, h) of the face in photo pixels, and how it was found."""
    h, w = alpha.shape
    detector.setInputSize((w, h))
    found = detector.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))[1]
    best = None
    for f in (found if found is not None else []):
        x, y, fw, fh = [int(v) for v in f[:4]]
        x, y = max(0, x), max(0, y)
        inside = alpha[y:y + fh, x:x + fw].mean() / 255 if fw > 0 and fh > 0 else 0   # a real face sits on the cut-out person
        score = fw * f[-1] * (0.5 + inside) * (1.3 - abs((x + fw / 2) / w - 0.5))
        if fw >= w * 0.06 and (best is None or score > best[0]):
            best = (score, (x, y, fw, fh))
    if best:
        return best[1], "face"
    ys, xs = np.nonzero(alpha > 128)                                  # no face found: guess from the silhouette
    if len(ys) < 50:
        return (int(w * 0.3), int(h * 0.1), int(w * 0.4), int(w * 0.4)), "guess"
    top = ys.min()
    band = alpha[top:top + max(8, int((ys.max() - top) * 0.22))] > 128
    cols = np.nonzero(band.any(axis=0))[0]
    head_w = max(12, cols.max() - cols.min())
    fw = int(head_w * 0.72)
    cx = (cols.max() + cols.min()) // 2
    return (int(cx - fw / 2), int(top + head_w * 0.22), fw, fw), "guess"


def make(src, dst):
    im = Image.open(src).convert("RGB")
    cut = remove(im, session=session)
    rgb, alpha = np.array(im), np.array(cut)[:, :, 3]
    (fx, fy, fw, fh), how = find_face(rgb, alpha)
    s = FACE_W / fw                                                   # photo pixel -> art pixel
    cx, chin = fx + fw / 2, fy + fh
    # art (x, y) -> photo (px, py)
    coeffs = (1 / s, 0, cx - FACE_CX / s, 0, 1 / s, chin - CHIN_Y / s)
    big = 4                                                           # sample at 4x, then box down: cleaner pixels
    coeffs_big = (1 / (s * big), 0, cx - FACE_CX / s, 0, 1 / (s * big), chin - CHIN_Y / s)
    head = im.transform((W * big, H * big), Image.AFFINE, coeffs_big, Image.BILINEAR).resize((W, H), Image.BOX)
    mask = Image.fromarray(alpha).transform((W * big, H * big), Image.AFFINE, coeffs_big, Image.BILINEAR).resize((W, H), Image.BOX)
    head = ImageEnhance.Contrast(ImageEnhance.Color(head).enhance(0.8)).enhance(1.25)
    hp, mp = np.array(head), np.array(mask)
    yy, xx = np.mgrid[0:H, 0:W]
    face_cy = CHIN_Y - FACE_W * 0.62                                   # rough centre of the face in art pixels
    face_oval = ((xx - FACE_CX) / (FACE_W * 0.56)) ** 2 + ((yy - face_cy) / (FACE_W * 0.74)) ** 2 <= 1
    keep = (mp > 128) | face_oval                                     # the whole cut-out figure; the face is kept even if the cut-out missed it
    # Above the chin only the head counts (with room for hair); this drops cameras, hands and people behind them.
    head_zone = ((xx - FACE_CX) / (FACE_W * 0.96)) ** 2 + ((yy - (face_cy - 1)) / (FACE_W * 1.32)) ** 2 <= 1
    above = yy < CHIN_Y - 1
    keep &= ~above | head_zone
    # Below the chin, keep the body but not anything far out to the sides.
    keep &= above | (np.abs(xx - FACE_CX) <= FACE_W * 0.62 + (yy - CHIN_Y + 1) * 2.2)
    # keep only the figure the face belongs to (drops other people and stray background)
    n, labels = cv2.connectedComponents(keep.astype(np.uint8), connectivity=4)
    keep = labels == labels[int(face_cy), FACE_CX]
    if keep.sum() < 40:
        return "empty"
    low = np.nonzero(keep.any(axis=1))[0].max()
    extend = None
    if low < H - 1:                                                   # the photo stops above the sill: continue the body downward
        cols = np.nonzero(keep[low])[0]
        l, r = int(cols.min()), int(cols.max())
        plain = low < CHIN_Y + 8                                      # cut at the neck: nothing to continue, so draw a plain grey top
        base = (96, 100, 108) if plain else tuple(int(v) for v in np.median(hp[max(0, low - 1):low + 1][keep[max(0, low - 1):low + 1]], axis=0))
        dark = tuple(int(v * 0.72) for v in base)
        lite = tuple(min(255, int(v * 1.18)) for v in base)
        extend = []
        cx, half, target = (l + r) / 2, (r - l) / 2, FACE_W * 1.3
        mid = hp[low, int(cx) - 2:int(cx) + 3].reshape(-1, 3)
        skin = tuple(int(v) for v in np.median(mid, axis=0))
        for i, y in enumerate(range(low + 1, H)):
            if half < target:
                half = min(target, half + 2.5)                        # shoulders slope out from the neck
            x0, x1 = max(0, int(round(cx - half))), min(W - 1, int(round(cx + half)))
            for x in range(x0, x1 + 1):
                col = dark if x < x0 + 3 else base
                if plain and abs(x - cx) < 6 - 2 * i:                 # a scoop neckline, so it reads as a T-shirt
                    col = skin
                elif plain and abs(x - cx) < 7 - 2 * i:
                    col = dark
                extend.append((y, x, col))
    # flat colours: reduce the figure to 10 tones
    pix = hp[keep]
    pal = Image.fromarray(pix.reshape(-1, 1, 3)).quantize(colors=10, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB")
    flat = np.array(pal).reshape(-1, 3)
    out = np.zeros((H, W, 4), np.uint8)
    out[keep] = np.concatenate([flat, np.full((len(flat), 1), 255, np.uint8)], axis=1)
    for y, x, col in (extend or []):
        out[y, x] = (*[int(v) for v in col], 255)
    # a dark outline so the figure reads against the wall
    solid = out[:, :, 3] > 0
    edge = np.zeros_like(solid)
    edge[1:, :] |= solid[:-1, :]; edge[:-1, :] |= solid[1:, :]; edge[:, 1:] |= solid[:, :-1]; edge[:, :-1] |= solid[:, 1:]
    out[edge & ~solid] = (*INK, 255)
    Image.fromarray(out, "RGBA").save(dst, optimize=True)
    return how


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    guessed = []
    for src in sorted(SRC.glob("*.jpg")):
        if args and src.stem not in args:
            continue
        dst = OUT / (src.stem + ".png")
        if dst.exists() and not force and not args:
            continue
        how = make(src, dst)
        if how != "face":
            guessed.append(f"{src.stem}:{how}")
    print("done. No face found (placed by silhouette):", " ".join(guessed) or "none")


if __name__ == "__main__":
    main()
