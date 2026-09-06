# Wuwa Matrix Reader
# by Dropkick
# 9/5/2026

import numpy as np
import os
from PIL import Image

# PATH for Resonator & buff icon image data
ROUND_AVATAR_PATH = "d:/OtherFiles/WuwaShareReader/round_avatars"

# BUFF ICON are from https://github.com/alt3ri/WW_Asset_Webp/tree/main/UIResources/Common/Image/IconAttribute
BUFF_ICON_PATH = "d:/OtherFiles/WuwaShareReader/BUFFIcon"

# PATH for numbers
NUMBER_PATH = "d:/OtherFiles/WuwaShareReader/number_images"

# --- Hybrid score tuning ---------------------------------------------------
# final_score = STRUCT_WEIGHT * ncc_luma + COLOR_WEIGHT * color_score
#
#   STRUCT_WEIGHT=1.0, COLOR_WEIGHT=0.0  -> pure original copy.py NCC
#                                           (color information ignored).
#   STRUCT_WEIGHT=0.7, COLOR_WEIGHT=0.3  -> keep original NCC ranking as the
#                                           dominant baseline, add 30% color
#                                           influence (user's request).
STRUCT_WEIGHT = 0.70
COLOR_WEIGHT  = 0.30

# Color sub-component blending within color_score: per-pixel RGB threshold match
# vs simple mean-RGB exponential similarity (more robust against JPEG blocks).
PIXEL_RGB_RATIO = 0.7   # 0.7*pixel_rgb + 0.3*avg_rgb
PIXEL_RGB_THRESHOLD = 30
PIXEL_RGB_BG_THRESHOLD = 60


# arrays for data
number_files = sorted([f for f in os.listdir(NUMBER_PATH) if f.lower().endswith((".png"))])
num_data = []

image_files = sorted([f for f in os.listdir(ROUND_AVATAR_PATH) if f.lower().endswith((".webp"))])
img_data = []
img_data1 = []

buff_imgs = sorted([f for f in os.listdir(BUFF_ICON_PATH) if f.lower().endswith((".webp"))])
buff_data = []
buff_data1 = []


#
# Extract team blocks
#
# Detect color
def is_valid_color(r, g, b):
    # Normalization
    r, g, b = r / 255.0, g / 255.0, b / 255.0

    max_val = max(r, g, b)
    min_val = min(r, g, b)
    diff = max_val - min_val

    # Calculate H
    if max_val == min_val:
        h = 0.0
    elif max_val == r:
        h = (60 * ((g - b) / diff) + 360) % 360
    elif max_val == g:
        h = (60 * ((b - r) / diff) + 120) % 360
    elif max_val == b:
        h = (60 * ((r - g) / diff) + 240) % 360

    # Calculate S
    if max_val == 0:
        s = 0.0
    else:
        s = (diff / max_val) * 100

    # Calculate V
    v = max_val * 100

    return (197 < h < 209 and 17 < s < 29 and 25 < v < 37)

# BFS to get color blocks
def get_valid_blocks(img, min_pixel_size=5000):
    width, height = img.size
    pixels = img.load()
    
    visited = set()
    blocks = []
    
    # Directions for 4-connectivity (Up, Down, Left, Right)
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (0, 2), (0, -2), (2, 0), (-2, 0)]
    
    for y in range(height):
        for x in range(width):
            if (x, y) in visited:
                continue
                
            r, g, b = pixels[x, y]
            if is_valid_color(r, g, b):
                # Start BFS to find the continuous block
                block_pixels = []
                queue = [(x, y)]
                visited.add((x, y))
                
                while queue:
                    curr_x, curr_y = queue.pop(0)
                    block_pixels.append((curr_x, curr_y))
                    
                    for dx, dy in directions:
                        nx, ny = curr_x + dx, curr_y + dy
                        
                        if 0 <= nx < width and 0 <= ny < height:
                            if (nx, ny) not in visited:
                                nr, ng, nb = pixels[nx, ny]
                                if is_valid_color(nr, ng, nb):
                                    visited.add((nx, ny))
                                    queue.append((nx, ny))
                
                # Filter out tiny noise blocks
                if len(block_pixels) >= min_pixel_size:
                    # Calculate bounding box (min_x, min_y, max_x, max_y)
                    xs = [p[0] for p in block_pixels]
                    ys = [p[1] for p in block_pixels]
                    bbox = (min(xs), min(ys), max(xs), max(ys))
                    
                    blocks.append({
                        "pixel_count": len(block_pixels),
                        "bbox": bbox,
                        "pixels": block_pixels
                    })

    return blocks

# ---------------------------------------------------------------------------
# Image-mode helpers
# ---------------------------------------------------------------------------
def _pil_to_rgb_on_black(img):
    """Composite any PIL image onto black background and return RGB mode."""
    if img.mode not in ("RGBA", "RGB", "LA", "P", "L"):
        img = img.convert("RGBA")
    if img.mode == "P":
        img = img.convert("RGBA")
    if img.mode == "LA":
        img = img.convert("RGBA")
    if img.mode == "L":
        return img.convert("RGB")
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (0, 0, 0))
        bg.paste(img, mask=img.split()[3])
        return bg
    return img.convert("RGB")


def _rgb_to_luma_np_uint8(rgb_pil):
    """
    Return uint8 numpy array representing ITU-R BT.601 luminance.
    This matches PIL's default .convert("L") formula exactly, so the grayscale
    representation here is identical to what the original copy.py's init
    produced (LA composite on black -> convert L -> np).
    """
    arr = np.array(rgb_pil).astype(np.float64)
    luma = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2])
    return np.clip(luma, 0.0, 255.0).astype(np.uint8)

#
# Initialization function
#
def init():
    # Read number files
    for i, img_name in enumerate(number_files):
        img_ava = Image.open(os.path.join(NUMBER_PATH, img_name))

        rgb = _pil_to_rgb_on_black(img_ava).resize((32, 43), Image.Resampling.LANCZOS)
        arr = np.array(rgb)
        luma_np = _rgb_to_luma_np_uint8(rgb)          # uint8, shape==compare_size
        mean_rgb = arr.reshape(-1, 3).mean(axis=0).astype(np.float64)
        num_data.append((rgb, luma_np, mean_rgb))

    # Read resonator icons
    for i, img_name in enumerate(image_files):
        img_ava = Image.open(os.path.join(ROUND_AVATAR_PATH, img_name))

        rgb = _pil_to_rgb_on_black(img_ava).resize((128, 128), Image.Resampling.LANCZOS)
        arr = np.array(rgb)[2:124, 0:127]
        rgb = Image.fromarray(arr)
        luma_np = _rgb_to_luma_np_uint8(rgb)          # uint8, shape==compare_size
        mean_rgb = arr.reshape(-1, 3).mean(axis=0).astype(np.float64)
        img_data.append((rgb, luma_np, mean_rgb))

        rgb1 = _pil_to_rgb_on_black(img_ava).resize((128, 128), Image.Resampling.LANCZOS)
        arr1 = np.array(rgb1)[3:121, 0:127]
        rgb1 = Image.fromarray(arr1)
        luma_np1 = _rgb_to_luma_np_uint8(rgb1)          # uint8, shape==compare_size
        mean_rgb1 = arr1.reshape(-1, 3).mean(axis=0).astype(np.float64)
        img_data1.append((rgb1, luma_np1, mean_rgb1))

    # Read BUFF icons
    for i, img_name in enumerate(buff_imgs):
        img_ava = Image.open(os.path.join(BUFF_ICON_PATH, img_name))

        rgb = _pil_to_rgb_on_black(img_ava).resize((75, 75), Image.Resampling.LANCZOS)
        arr = np.array(rgb)
        luma_np = _rgb_to_luma_np_uint8(rgb)          # uint8, shape==compare_size
        mean_rgb = arr.reshape(-1, 3).mean(axis=0).astype(np.float64)
        buff_data.append((rgb, luma_np, mean_rgb))

        rgb1 = _pil_to_rgb_on_black(img_ava).resize((79, 79), Image.Resampling.LANCZOS)
        arr1 = np.array(rgb1)
        luma_np1 = _rgb_to_luma_np_uint8(rgb1)          # uint8, shape==compare_size
        mean_rgb1 = arr1.reshape(-1, 3).mean(axis=0).astype(np.float64)
        buff_data1.append((rgb1, luma_np1, mean_rgb1))

# ---------------------------------------------------------------------------
# Structural: NCC (original copy.py method, zero-mean normalized xcorr)
# ---------------------------------------------------------------------------
def ncc_score(a_uint8, b_uint8):
    """
    Zero-mean normalized cross correlation in [-1.0, +1.0].
    Mathematically equivalent to the NCC the original copy.py used for
    structural ranking. Both inputs must be 2D uint8 arrays of equal shape
    (luminance channel).

    Returns 0.0 if either input is perfectly flat (zero variance).
    """
    a = a_uint8.astype(np.float64)
    b = b_uint8.astype(np.float64)
    a_mean = np.mean(a)
    b_mean = np.mean(b)
    a_centered = a - a_mean
    b_centered = b - b_mean

    denom_a = np.sqrt(np.sum(a_centered * a_centered))
    denom_b = np.sqrt(np.sum(b_centered * b_centered))
    if denom_a < 1e-9 or denom_b < 1e-9:
        return 0.0

    ncc_val = np.sum(a_centered * b_centered) / (denom_a * denom_b)
    # Guard against tiny floating-point drift beyond [-1, 1]
    return float(max(-1.0, min(1.0, ncc_val)))


def _align_shapes_uint8(a_np, b_np, target_size_wh):
    """
    Ensure two 2D uint8 luma arrays match target_size_wh exactly.
    target_size_wh is (width, height) -- PIL convention.
    Returns (a_aligned, b_aligned) both shape (height, width) as uint8.
    """
    tw, th = target_size_wh

    def _to_size(src_np):
        if src_np.shape == (th, tw):
            return src_np
        return np.array(
            Image.fromarray(src_np).resize((tw, th), Image.Resampling.LANCZOS),
            dtype=np.uint8,
        )

    return _to_size(a_np), _to_size(b_np)
# ---------------------------------------------------------------------------
# Color similarity sub-routines (vectorized numpy)
# ---------------------------------------------------------------------------
def _diff_int(a, b):
    """Absolute difference (int32) to avoid uint8 wrap-around."""
    return np.abs(a.astype(np.int32) - b.astype(np.int32))


def _pixel_rgb_similarity(arr1, arr2, thr=PIXEL_RGB_THRESHOLD, bthr=PIXEL_RGB_BG_THRESHOLD):
    """
    Per-pixel RGB match, inspired by the user-supplied reference color matcher.
    Very dark pixels (R,G,B all < bthr) are treated as background and ignored.
    Returns the fraction of non-background pixels whose per-channel differences
    are ALL below thr.
    """
    r1, g1, b1 = arr1[:, :, 0], arr1[:, :, 1], arr1[:, :, 2]
    bg_mask = (r1 < bthr) & (g1 < bthr) & (b1 < bthr)
    fg_mask = ~bg_mask
    if not np.any(fg_mask):
        return 0.0

    r2, g2, b2 = arr2[:, :, 0], arr2[:, :, 1], arr2[:, :, 2]
    dr = _diff_int(r1, r2)
    dg = _diff_int(g1, g2)
    db = _diff_int(b1, b2)

    matches = (dr < thr) & (dg < thr) & (db < thr)
    fg_matches = matches & fg_mask

    n_match = int(np.sum(fg_matches))
    n_tot   = int(np.sum(fg_mask))
    if n_tot == 0:
        return 0.0
    return float(n_match) / float(n_tot)


def _avg_rgb_similarity(mean1, mean2):
    """
    Robust global-RGB similarity in [0,1] (against JPEG blocks / compression).
    Mean abs channel diff of 128/255 -> similarity ~0.5; 0 diff -> 1.0.
    """
    diff_norm = float(np.mean(np.abs(mean1 - mean2))) / 255.0
    return float(np.exp(-diff_norm * 4.0))


def _is_slot_empty(rgb_arr_resized, black_thr=50, empty_pct_thr=80):
    """Return True if more than empty_pct_thr % of pixels are nearly black."""
    is_black = np.all(rgb_arr_resized < black_thr, axis=2)
    tot = rgb_arr_resized.shape[0] * rgb_arr_resized.shape[1]
    pct = 100.0 * float(np.sum(is_black)) / float(tot)
    return pct > empty_pct_thr


# ---------------------------------------------------------------------------
# Core comparison: NCC(luma) * STRUCT_WEIGHT + COLOR_WEIGHT * color_score
# ---------------------------------------------------------------------------
def _compare_slot(sub_rgb_pil, template_tuple, target_size_wh):
    """
    Hybrid comparison matching v3.4 design:
      1. Structural score -> NCC on luminance (original copy.py method).
      2. Color score      -> pixel_rgb * PIXEL_RGB_RATIO
                            + avg_rgb   * (1 - PIXEL_RGB_RATIO).
      3. Final            -> STRUCT_WEIGHT * ncc + COLOR_WEIGHT * color_score.

    Returns (final, ncc, color_pixel, color_avg).
    """
    tpl_rgb_pil, tpl_luma_np, tpl_mean_rgb = template_tuple

    # 1) Resize slot crop to compare size; build RGB + luma arrays.
    if sub_rgb_pil.size != target_size_wh:
        sub_rgb_pil = sub_rgb_pil.resize(target_size_wh, Image.Resampling.LANCZOS)
    sub_rgb_arr  = np.array(sub_rgb_pil)
    sub_luma_np  = _rgb_to_luma_np_uint8(sub_rgb_pil)
    sub_mean_rgb = sub_rgb_arr.reshape(-1, 3).mean(axis=0).astype(np.float64)
    tpl_rgb_arr  = np.array(tpl_rgb_pil)

    # 2) Structural: NCC on luminance (shapes must match target_size exactly).
    sub_luma_aligned, tpl_luma_aligned = _align_shapes_uint8(
        sub_luma_np, tpl_luma_np, target_size_wh
    )
    structural_ncc = ncc_score(sub_luma_aligned, tpl_luma_aligned)
    # Shift raw NCC from [-1, 1] into [0, 1] so it blends with color score cleanly.
    structural_ncc_01 = 0.5 * (structural_ncc + 1.0)

    # 3) Color sub-scores (both naturally in [0, 1]).
    color_pixel = _pixel_rgb_similarity(sub_rgb_arr, tpl_rgb_arr)
    color_avg   = _avg_rgb_similarity(sub_mean_rgb, tpl_mean_rgb)
    color_score = PIXEL_RGB_RATIO * color_pixel + (1.0 - PIXEL_RGB_RATIO) * color_avg

    # 4) Weighted sum blending.
    final = STRUCT_WEIGHT * structural_ncc_01 + COLOR_WEIGHT * color_score

    return float(final), structural_ncc, color_pixel, color_avg

#
# Function to get info
# Input: PATH to image
# Output: list of [6][3], teams of ToA Resonators, each content is the name of image
#
def ReadMatrixImg(Matrix_Img_PATH):
    img = Image.open(Matrix_Img_PATH).convert("RGB")
    hsv_img = img.convert("HSV")
    hsv_data = np.array(hsv_img)
    rgb_data = np.array(img)

    # Light gray -> gray
    lower = np.array([203 * 255 / 360, 21 * 255 / 100, 48 * 255 / 100])
    upper = np.array([207 * 255 / 360, 25 * 255 / 100, 52 * 255 / 100])
    mask = np.all((hsv_data >= lower) & (hsv_data <= upper), axis=-1)
    rgb_data[mask] = np.array([61, 72, 80])
    img = Image.fromarray(rgb_data)

    res = get_valid_blocks(img)

    res_img = []

    BUFF_POS = (568, 22)
    BUFF_W, BUFF_H = 75, 75
    BUFF_COMPARE_SIZE = (75, 75)

    NUMBER_POS = [(35, 39),(70, 39)]
    NUMBER_W, NUMBER_H = 33, 43
    NUMBER_COMPARE_SIZE = (32, 43)

    for index, one_team in enumerate(res):
        team_to_test = np.array(img)[res[index]['bbox'][1]:res[index]['bbox'][3], res[index]['bbox'][0]:res[index]['bbox'][2]]

        # remove blocks that are not valid / change constant parameters
        if 10.5 < team_to_test.shape[1] / team_to_test.shape[0] < 11:
            team_rect = Image.fromarray(team_to_test)
            team_to_test = np.array((team_rect.resize((1290, 122), Image.Resampling.LANCZOS)))

            RESONATOR_POS = [(161, 0), (280, 0), (399, 0)]
            RESONATOR_W, RESONATOR_H = 128, 122
            AVATAR_COMPARE_SIZE = (127, 122)

            BUFF_POS = (568, 22)
            BUFF_W, BUFF_H = 75, 75
            BUFF_COMPARE_SIZE = (75, 75)

            NUMBER_POS = [(33, 39),(67, 39)]
            NUMBER_W, NUMBER_H = 33, 43
            NUMBER_COMPARE_SIZE = (32, 43)
            
            res_data = img_data
            buff_res_data = buff_data


        elif 11.28 < team_to_test.shape[1] / team_to_test.shape[0] < 11.5:
            team_rect = Image.fromarray(team_to_test)
            team_to_test = np.array((team_rect.resize((1320, 117), Image.Resampling.LANCZOS)))
            
            RESONATOR_POS = [(164, 0), (287, 0), (410, 0)]
            RESONATOR_W, RESONATOR_H = 128, 118
            AVATAR_COMPARE_SIZE = (127, 118)

            BUFF_POS = (580, 18)
            BUFF_W, BUFF_H = 79, 79
            BUFF_COMPARE_SIZE = (79, 79)

            NUMBER_POS = [(33, 37),(68, 37)]
            NUMBER_W, NUMBER_H = 33, 43
            NUMBER_COMPARE_SIZE = (32, 43)

            res_data = img_data1
            buff_res_data = buff_data1

        elif 10.54 < team_to_test.shape[1] / team_to_test.shape[0] < 10.55:
            team_rect = Image.fromarray(team_to_test)
            team_to_test = np.array((team_rect.resize((1320, 117), Image.Resampling.LANCZOS)))

            RESONATOR_POS = [(168, 0), (291, 0), (414, 0)]
            RESONATOR_W, RESONATOR_H = 128, 118
            AVATAR_COMPARE_SIZE = (127, 118)

            BUFF_POS = (584, 18)
            BUFF_W, BUFF_H = 79, 79
            BUFF_COMPARE_SIZE = (79, 79)

            NUMBER_POS = [(33, 37),(68, 37)]
            NUMBER_W, NUMBER_H = 33, 43
            NUMBER_COMPARE_SIZE = (32, 43)

            res_data = img_data1
            buff_res_data = buff_data1

        else :
            continue

        # Identify team ID
        team_number_img = []
        
        for i, (x, y) in enumerate(NUMBER_POS):
            sub_image = team_to_test[y:y+NUMBER_H, x:x+NUMBER_W]
            team_number_img.append(sub_image)

        res_numbers = 0
        for i, num_img in enumerate(team_number_img):
                num_arr = Image.fromarray(num_img)
                best_score = -1.0
                best_idx   = 0
                for idx, tpl in enumerate(num_data):
                    final, _, _, _ = _compare_slot(num_arr, tpl, NUMBER_COMPARE_SIZE)
                    if final > best_score:
                        best_score = final
                        best_idx   = idx

                res_numbers = res_numbers * 10 + int(number_files[best_idx].split(".")[0])

        # Identify resonator
        resonator_in_team = []

        for i, (x, y) in enumerate(RESONATOR_POS):
            sub_image = team_to_test[y:y+RESONATOR_H, x:x+RESONATOR_W]
            resonator_in_team.append(sub_image)

        res_resonator = []
        for i, avatar in enumerate(resonator_in_team):
                ava_arr = Image.fromarray(avatar)
                best_score = -1.0
                best_idx   = 0
                for idx, tpl in enumerate(res_data):
                    final, _, _, _ = _compare_slot(ava_arr, tpl, AVATAR_COMPARE_SIZE)
                    if final > best_score:
                        best_score = final
                        best_idx   = idx

                res_resonator.append(image_files[best_idx])

        # Identify BUFF
        buff_slot = team_to_test[BUFF_POS[1]:BUFF_POS[1]+BUFF_H, BUFF_POS[0]:BUFF_POS[0]+BUFF_W]
        buff_arr = Image.fromarray(buff_slot)

        best_score = -1.0
        best_idx = 0
        for idx, tpl in enumerate(buff_res_data):
            final, _, _, _ = _compare_slot(buff_arr, tpl, BUFF_COMPARE_SIZE)
            if final > best_score:
                best_score = final
                best_idx   = idx
                
        res_img.append({
            "Team #": res_numbers,
            "Resonators": res_resonator, 
            "BUFF": buff_imgs[best_idx],
        })

    return res_img

#
# sample run:
#
if __name__ == "__main__":
    init()
    paht = "d:/OtherFiles/WuwaShareReader/MatrixTest05.png"
    res = ReadMatrixImg(paht)
    for ele in res:
        print(ele)