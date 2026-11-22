# Writes <pack folder>/trees/Conifer_Needles_Grey.png: Conifer_Needles.png with each texel's colour
# made its brightness (linear), alpha kept, so a conifer's needles take their colour from the
# material alone (gen_pack.mjs's `crown`). Prints the mean of the texels a 0.3 cut keeps, linear,
# which `crown` divides by. Run it after foliage.py; a second run changes nothing.
# Needs only Python and ImageMagick (`magick`).
# grey_needles.py <pack folder>
import os, subprocess, sys

LUMA = (0.2126, 0.7152, 0.0722)
CUT = 0.3
TO_LINEAR = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (i / 255 for i in range(256))]


def to_srgb(v):
    v = min(max(v, 0.0), 1.0)
    return round(255 * (v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055))


def main():
    trees = os.path.join(sys.argv[1], 'trees')
    src = os.path.join(trees, 'Conifer_Needles.png')
    w, h = map(int, subprocess.run(['magick', 'identify', '-format', '%w %h', src], capture_output=True,
                                   text=True, check=True).stdout.split())
    rgba = bytearray(subprocess.run(['magick', src, '-depth', '8', 'rgba:-'], capture_output=True,
                                    check=True).stdout)
    grey = {}
    total, kept = 0.0, 0
    for i in range(0, len(rgba), 4):
        key = bytes(rgba[i:i + 3])
        g = grey.get(key)
        if g is None:
            g = grey[key] = to_srgb(sum(TO_LINEAR[c] * k for c, k in zip(key, LUMA)))
        rgba[i] = rgba[i + 1] = rgba[i + 2] = g
        if rgba[i + 3] >= int(CUT * 255):
            total += TO_LINEAR[g]
            kept += 1
    out = os.path.join(trees, 'Conifer_Needles_Grey.png')
    subprocess.run(['magick', '-size', f'{w}x{h}', '-depth', '8', 'rgba:-', f'PNG32:{out}'], input=bytes(rgba),
                   check=True)
    print(f'{out}: mean {total / max(kept, 1):.4f} over {kept} texels')


if __name__ == '__main__':
    main()
