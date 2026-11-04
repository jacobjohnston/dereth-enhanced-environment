# The colour a client without depth mapping draws for each material that keeps the player's own
# picture (`keep_retail_picture`): that picture's average colour, as a small picture of one colour.
# A client with depth mapping draws the player's picture under the material's relief instead.
# fallback.py <pack folder> <the player's pictures, as PNGs named by id>
import os, re, subprocess, sys
import numpy as np

# The fallback picture's side, in pixels: one colour, so any size draws the same.
SIZE = 4


def average(path):
    """The average colour of the picture at `path`, over its pixels that are not see-through."""
    raw = subprocess.run(['magick', path, '-depth', '8', 'rgba:-'], capture_output=True, check=True).stdout
    px = np.frombuffer(raw, np.uint8).reshape(-1, 4).astype(np.float32) / 255
    solid = px[px[:, 3] >= 0.5]
    return (solid if len(solid) else px)[:, :3].mean(0)


def write(path, colour):
    a = np.tile(np.append(colour, 1.0), (SIZE * SIZE, 1))
    subprocess.run(['magick', '-define', 'png:exclude-chunks=date,time', '-size', f'{SIZE}x{SIZE}', '-depth', '8',
                    'rgba:-', path], input=(np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes(), check=True)


if __name__ == '__main__':
    pack, pictures = sys.argv[1:3]
    text = open(os.path.join(pack, 'manifest.toml')).read()
    count = 0
    for block in re.split(r'\n(?=\[\[)', text):
        if not re.search(r'^keep_retail_picture = true$', block, re.M):
            continue
        id = re.search(r'^texture = "(0x[0-9A-F]+)"', block, re.M)[1]
        base = re.search(r'^base_color = "([^"]+)"', block, re.M)[1]
        write(os.path.join(pack, base), average(os.path.join(pictures, f'{id}.png')))
        count += 1
    print(count, 'fallback colours')
