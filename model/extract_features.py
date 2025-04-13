import cv2
import numpy as np
import math
import sys
from typing import List, Tuple
import base64

# Constants
DISPLACEMENT = 10

# Structures replacement using simple classes
class CPoint:
    def __init__(self, x: int = 0, y: int = 0):
        x = x
        y = y

class Vertex:
    def __init__(self, x: float = 0.0, y: float = 0.0):
        x = x
        y = y

class RadiusAngle:
    def __init__(self, radius: float = 0.0, angle: float = 0.0):
        radius = radius
        angle = angle

# Helper functions to get neighbors
# P9 P2 P3
# P8 P1 P4
# P7 P6 P5
# Note: OpenCV uses (row, col) which corresponds to (y, x)
def P1(dest, r, c): return dest[r, c]
def P2(dest, r, c): return dest[r-1, c]
def P3(dest, r, c): return dest[r-1, c+1]
def P4(dest, r, c): return dest[r, c+1]
def P5(dest, r, c): return dest[r+1, c+1]
def P6(dest, r, c): return dest[r+1, c]
def P7(dest, r, c): return dest[r+1, c-1]
def P8(dest, r, c): return dest[r, c-1]
def P9(dest, r, c): return dest[r-1, c-1]

def get_features(traced, template):
    img_drawn_color = cv2.imdecode(np.frombuffer(base64.b64decode(traced), dtype=np.uint8), cv2.IMREAD_COLOR)
    img_template_color = cv2.imdecode(np.frombuffer(base64.b64decode(template), dtype=np.uint8), cv2.IMREAD_COLOR)

    # Ensure template image has same dimensions (resize if necessary, or error out)
    # For simplicity, assuming they are the same size as in C++ code
    if img_drawn_color.shape != img_template_color.shape:
        print(f"Warning: Drawn image shape {img_drawn_color.shape} differs from template shape {img_template_color.shape}. Results may be inaccurate.", file=sys.stderr)
        # Consider resizing template to match drawn, or vice-versa if needed.
        # img_template_color = cv2.resize(img_template_color, (img_drawn_color.shape[1], img_drawn_color.shape[0]))

    # Convert to grayscale
    img_drawn_gray = cv2.cvtColor(img_drawn_color, cv2.COLOR_BGR2GRAY)
    img_template_gray = cv2.cvtColor(img_template_color, cv2.COLOR_BGR2GRAY)

    # Threshold (using same values as C++) - Binary Threshold
    _, img_drawn_thresh = cv2.threshold(img_drawn_gray, 220, 255, cv2.THRESH_BINARY)
    _, img_template_thresh = cv2.threshold(img_template_gray, 220, 255, cv2.THRESH_BINARY)

    # Apply Zhang-Suen Thinning (modifies images in-place)
    print("Thinning drawn image...", file=sys.stderr)
    zhang_suen(img_drawn_thresh)
    print("Thinning template image...", file=sys.stderr)
    zhang_suen(img_template_thresh)

    # --- Find Spiral Origin ---
    # Use center as initial guess
    yc_guess = img_drawn_thresh.shape[0] // 2
    xc_guess = img_drawn_thresh.shape[1] // 2

    # Find origin using the template image (as in C++ code: origem(img1_, &yc, &xc))
    # The C++ code uses img1_ which is the *template* image for finding the origin
    print(f"Finding origin near ({xc_guess}, {yc_guess})...", file=sys.stderr)
    yc, xc = find_origen(img_template_thresh, yc_guess, xc_guess) # Pass the thinned template
    print(f"Using origin: ({xc}, {yc})", file=sys.stderr)


    # --- Extract Points ---
    ptosoriginal: List[Vertex] = [] # Points from template spiral
    ptosdesenhada: List[Vertex] = [] # Points from drawn spiral

    # Need copies because line_idda modifies the image by erasing pixels
    img_drawn_copy = img_drawn_thresh.copy()
    img_template_copy = img_template_thresh.copy()

    print("Extracting points...", file=sys.stderr)
    num_turns = 3
    num_angles = 360
    for j in range(num_turns):
        # Start point for rotation (far right, vertically centered at origin)
        # Adjusted starting x to be well outside image bounds based on C++ logic
        vert = Vertex(float(img_drawn_thresh.shape[1] + 350), float(yc))

        rotation(vert, float(yc), float(xc), 1) # Initial small rotation

        for i in range(num_angles):
            rotation(vert, float(yc), float(xc), -1) # Rotate back by 1 degree each step

            # Use copies of the thinned images for extraction
            line_idda(img_template_copy, float(yc), float(xc), vert.y, vert.x, ptosoriginal)
            line_idda(img_drawn_copy, float(yc), float(xc), vert.y, vert.x, ptosdesenhada)

            # Check sizes if needed (debugging)
            # print(f"Angle {i}: Drawn {len(ptosdesenhada)}, Original {len(ptosoriginal)}")

    n_drawn = len(ptosdesenhada)
    n_orig = len(ptosoriginal)
    min_points = min(n_drawn, n_orig)

    if min_points == 0:
        print("Error: Failed to extract any points from one or both spirals. Check images and origin.", file=sys.stderr)
        return None

    print(f"Extracted {n_drawn} points from drawn, {n_orig} from template.", file=sys.stderr)

    # --- Feature Calculation ---
    radiusangle_orig: List[RadiusAngle] = []
    radiusangle_drawn: List[RadiusAngle] = []
    difradial: List[RadiusAngle] = [] # Stores absolute radial differences

    # Transformation to polar coordinates (using origin xc, yc)
    for i in range(n_orig):
        dx = ptosoriginal[i].x - xc
        dy = ptosoriginal[i].y - yc
        radius = math.sqrt(dx*dx + dy*dy)
        angle = math.atan2(dy, dx) # Use atan2 for quadrant safety
        radiusangle_orig.append(RadiusAngle(radius, angle))

    for i in range(n_drawn):
        dx = ptosdesenhada[i].x - xc
        dy = ptosdesenhada[i].y - yc
        radius = math.sqrt(dx*dx + dy*dy)
        angle = math.atan2(dy, dx)
        radiusangle_drawn.append(RadiusAngle(radius, angle))

    # Calculate radial differences and crossings
    dif_rad = 0.0
    prev_rad_diff = 0.0
    count_cross = 0

    # Calculate initial difference for the first point
    if min_points > 0:
        prev_rad_diff = radiusangle_orig[0].radius - radiusangle_drawn[0].radius
        difradial.append(RadiusAngle(abs(prev_rad_diff), 0)) # Angle not used here

    for i in range(1, min_points):
        dif_rad = radiusangle_orig[i].radius - radiusangle_drawn[i].radius
        difradial.append(RadiusAngle(abs(dif_rad), 0)) # Store absolute difference
        if dif_rad * prev_rad_diff < 0: # Check for sign change (crossing)
            count_cross += 1
        prev_rad_diff = dif_rad

    # Calculate Tremor features based on original points' radii
    # C++ uses ptosoriginal radii for tremor calculation
    tremor_radii = [r.radius for r in radiusangle_orig] # Get list of radii from template

    mean_tremor = 0.0
    max_tremor = 0.0
    min_tremor = 1e10 # Initialize min to a large value
    std_tremor = 0.0
    count_tremor = 0

    if len(tremor_radii) > DISPLACEMENT:
        tremor_diffs = []
        for i in range(DISPLACEMENT, len(tremor_radii)):
            # Use absolute difference as in C++
            dif = abs(tremor_radii[i] - tremor_radii[i-DISPLACEMENT])
            tremor_diffs.append(dif)
            # mean_tremor += dif # Sum for mean calculation later
            if dif > max_tremor: max_tremor = dif
            if dif < min_tremor: min_tremor = dif
            # count_tremor += 1

        if tremor_diffs: # Check if list is not empty
            mean_tremor = sum(tremor_diffs) / len(tremor_diffs)
            # Calculate standard deviation
            variance_tremor = sum([(d - mean_tremor)**2 for d in tremor_diffs]) / len(tremor_diffs)
            std_tremor = math.sqrt(variance_tremor)
        else: # Handle case with insufficient points
            mean_tremor = 0.0
            std_tremor = 0.0
            min_tremor = 0.0 # Reset min if no diffs calculated

    else: # Handle case with insufficient points
        mean_tremor = 0.0
        std_tremor = 0.0
        min_tremor = 0.0

    # Calculate RMS and related stats from radial differences (difradial)
    rms = 0.0
    min_rms_val = 1e10
    max_rms_val = 0.0
    std_rms = 0.0

    if difradial: # Check if list is not empty
        sum_sq_diff = 0.0
        sq_diffs = []
        for dr in difradial:
            sq_diff = dr.radius * dr.radius
            sq_diffs.append(sq_diff)
            sum_sq_diff += sq_diff
            if sq_diff > max_rms_val: max_rms_val = sq_diff
            if sq_diff < min_rms_val: min_rms_val = sq_diff

        rms = sum_sq_diff / len(difradial) # Mean of squared differences

        # Calculate Standard Deviation of squared differences
        variance_rms = sum([(sd - rms)**2 for sd in sq_diffs]) / len(difradial)
        std_rms = math.sqrt(variance_rms)
    else: # Handle case with no radial differences calculated
        rms = 0.0
        std_rms = 0.0
        min_rms_val = 0.0


    # Calculate Crossings Rate
    crossings_rate = 0.0
    # Use count_tremor for normalization if it's derived correctly, or len(tremor_diffs)
    # C++ uses 'count' which seems tied to tremor calculation loop
    if len(tremor_diffs) > 0:
        crossings_rate = float(count_cross) / len(tremor_diffs)
    else:
        crossings_rate = 0.0 # Avoid division by zero

    # --- Output ---
    # Print stats to stderr
    print(f"RMS: {rms:.6f} (+/- {std_rms:.6f}) \t "
        f"maxSqDiff: {max_rms_val:.6f} \t minSqDiff: {min_rms_val:.6f} \t " # C++ printed max/min of sq diff
        f"Npoints: {n_drawn}: {n_orig} \n"
        f"MT: {mean_tremor:.6f} MaxT: {max_tremor:.6f} MinT: {min_tremor:.6f} StdT: {std_tremor:.6f} \t"
        f"CrossRate: {crossings_rate:.6f} (Crossings: {count_cross})", file=sys.stderr)
    
    return {
        'RMS': rms,
        'MAX_BETWEEN_ET_HT': max_rms_val,
        'MIN_BETWEEN_ET_HT': min_rms_val,
        'STD_DEVIATION_ET_HT': std_rms,
        'MRT': mean_tremor,
        'MAX_HT': max_tremor,
        'MIN_HT': min_tremor,
        'STD_HT': std_tremor,
        'CHANGES_FROM_NEGATIVE_TO_POSITIVE_BETWEEN_ET_HT': count_cross
    }

# Zhang-Suen Thinning Algorithm
def zhang_suen(dest: np.ndarray):
    """
    Applies the Zhang-Suen thinning algorithm in place.
    Assumes input image is binary (e.g., 0 and 255).
    Modifies the image to have 0 for background and 1 for foreground during processing,
    then converts back to 255 for background and 0 for foreground.
    """
    height, width = dest.shape
    # Invert image: White (255) becomes 0 (background), Black (0) becomes 1 (foreground)
    img_proc = np.where(dest == 255, 0, 1).astype(np.uint8)

    thining_continue = True
    while thining_continue:
        thining_continue = False
        rem_points_sub1 = []
        rem_points_sub2 = []

        # First Sub-Iteration
        for r in range(1, height - 1):
            for c in range(1, width - 1):
                # Pixel must be foreground (1)
                if P1(img_proc, r, c) == 0:
                    continue

                # Connectivity number calculation
                connectivity = 0
                connectivity += (1 if P2(img_proc, r, c) == 0 and P3(img_proc, r, c) == 1 else 0)
                connectivity += (1 if P3(img_proc, r, c) == 0 and P4(img_proc, r, c) == 1 else 0)
                connectivity += (1 if P4(img_proc, r, c) == 0 and P5(img_proc, r, c) == 1 else 0)
                connectivity += (1 if P5(img_proc, r, c) == 0 and P6(img_proc, r, c) == 1 else 0)
                connectivity += (1 if P6(img_proc, r, c) == 0 and P7(img_proc, r, c) == 1 else 0)
                connectivity += (1 if P7(img_proc, r, c) == 0 and P8(img_proc, r, c) == 1 else 0)
                connectivity += (1 if P8(img_proc, r, c) == 0 and P9(img_proc, r, c) == 1 else 0)
                connectivity += (1 if P9(img_proc, r, c) == 0 and P2(img_proc, r, c) == 1 else 0)

                if connectivity != 1:
                    continue

                # Number of black neighbors
                neighbors = (P2(img_proc, r, c) + P3(img_proc, r, c) +
                            P4(img_proc, r, c) + P5(img_proc, r, c) +
                            P6(img_proc, r, c) + P7(img_proc, r, c) +
                            P8(img_proc, r, c) + P9(img_proc, r, c))

                if not (2 <= neighbors <= 6):
                    continue

                # Condition checks (at least one background neighbor)
                if P2(img_proc, r, c) * P4(img_proc, r, c) * P6(img_proc, r, c) != 0:
                    continue # C++ code had P8 here, but later used P6. Assuming P6.

                # Check for P4 * P6 * P8 == 0 (at least one background)
                # C++ code had P2*P6*P8 != 0 here, which seems inconsistent with comments.
                # Let's stick to the conditions common in Zhang-Suen: P2*P4*P6==0 and P4*P6*P8==0
                # First sub-iteration uses P2*P4*P6 == 0
                # (The second check in C++ P2*P6*P8 != 0 seems misplaced for first iter)

                # Check P2 * P4 * P8 == 0 (original C++ check)
                if P2(img_proc, r, c) * P4(img_proc, r, c) * P8(img_proc, r, c) != 0:
                    continue
                # Check P2 * P6 * P8 == 0 (original C++ check) - seems redundant/conflicting? Sticking to standard ZS for now. Let's re-add if needed.
                # if P2(img_proc, r, c) * P6(img_proc, r, c) * P8(img_proc, r, c) != 0:
                #      continue


                # Mark pixel for deletion
                rem_points_sub1.append(CPoint(c, r)) # Note: CPoint stores (x, y)
                thining_continue = True

        # Delete points from first sub-iteration
        for point in rem_points_sub1:
            img_proc[point.y, point.x] = 0 # Set to background

        # Second Sub-Iteration
        for r in range(1, height - 1):
            for c in range(1, width - 1):
                # Pixel must be foreground (1)
                if P1(img_proc, r, c) == 0:
                    continue

                # Connectivity number calculation (same as above)
                connectivity = 0
                connectivity += (1 if P2(img_proc, r, c) == 0 and P3(img_proc, r, c) == 1 else 0)
                connectivity += (1 if P3(img_proc, r, c) == 0 and P4(img_proc, r, c) == 1 else 0)
                connectivity += (1 if P4(img_proc, r, c) == 0 and P5(img_proc, r, c) == 1 else 0)
                connectivity += (1 if P5(img_proc, r, c) == 0 and P6(img_proc, r, c) == 1 else 0)
                connectivity += (1 if P6(img_proc, r, c) == 0 and P7(img_proc, r, c) == 1 else 0)
                connectivity += (1 if P7(img_proc, r, c) == 0 and P8(img_proc, r, c) == 1 else 0)
                connectivity += (1 if P8(img_proc, r, c) == 0 and P9(img_proc, r, c) == 1 else 0)
                connectivity += (1 if P9(img_proc, r, c) == 0 and P2(img_proc, r, c) == 1 else 0)

                if connectivity != 1:
                    continue

                # Number of black neighbors (same as above)
                neighbors = (P2(img_proc, r, c) + P3(img_proc, r, c) +
                            P4(img_proc, r, c) + P5(img_proc, r, c) +
                            P6(img_proc, r, c) + P7(img_proc, r, c) +
                            P8(img_proc, r, c) + P9(img_proc, r, c))

                if not (2 <= neighbors <= 6):
                    continue

                # Condition checks for second sub-iteration (P2*P4*P8==0 and P2*P6*P8==0)
                # C++ has P2*P4*P6 != 0 and P4*P6*P8 != 0
                # Sticking to the C++ code here:
                if P2(img_proc, r, c) * P4(img_proc, r, c) * P6(img_proc, r, c) != 0:
                    continue
                if P4(img_proc, r, c) * P6(img_proc, r, c) * P8(img_proc, r, c) != 0:
                    continue

                # Mark pixel for deletion
                rem_points_sub2.append(CPoint(c, r)) # Note: CPoint stores (x, y)
                thining_continue = True

        # Delete points from second sub-iteration
        for point in rem_points_sub2:
            img_proc[point.y, point.x] = 0 # Set to background

    # Invert back: Background (0) to 255, Foreground (1) to 0
    dest[:, :] = np.where(img_proc == 0, 255, 0).astype(np.uint8)


# Function to swap values (Python returns tuples)
def invert(ini: float, fim: float) -> Tuple[float, float]:
    return fim, ini

# Line drawing algorithm (DDA variant) to find first foreground pixel
def line_idda(img_: np.ndarray, yi: float, xi: float, yf: float, xf: float, v: List[Vertex]):
    """
    Traces a line from (xi, yi) to (xf, yf). Finds the first foreground pixel (0)
    encountered along the path, adds its coordinates to list v, and marks the
    traced path pixels as background (255) to avoid re-processing.
    """
    height, width = img_.shape
    xi, yi, xf, yf = int(round(xi)), int(round(yi)), int(round(xf)), int(round(yf))

    deltax = xf - xi
    deltay = yf - yi

    # When yi>yf the line is diagonal to down.
    # When Deltax= 0 and Deltay < 0, the line is vertical down.
    # Invert points for consistent octant processing if needed.
    if (yi > yf) or ((deltax == 0) and (deltay < 0)):
        xi, xf = invert(xi, xf)
        yi, yf = invert(yi, yf)
        deltax = xf - xi
        deltay = yf - yi

    x = xi
    y = yi
    erro = 0
    q = 0

    # "quant" denotes the maximum number of plotted points
    if abs(deltax) > abs(deltay):
        quant = abs(deltax)
    else:
        quant = abs(deltay)

    get_point = True
    entered = False
    walk = 1000  # Limit steps after finding the first point

    while q <= quant and walk > 0:
        # Check bounds before accessing pixel
        if 0 <= y < height and 0 <= x < width:
            if not entered and img_[y, x] == 0: # Found a foreground pixel (0)
                entered = True
                if get_point:
                    get_point = False
                    vert = Vertex(float(x), float(y))
                    v.append(vert)
                img_[y, x] = 255 # Mark as background to avoid reprocessing

        if entered:
            walk -= 1
            if 0 <= y < height and 0 <= x < width:
                img_[y, x] = 255 # Continue marking path as background

        # DDA/Bresenham style octant logic
        if (deltax >= 0) and (deltay >= 0) and (deltax >= deltay): # 1st oct
            if (erro < 0) or (deltay == 0):
                x += 1
                erro += deltay
            else:
                x += 1
                y += 1
                erro += deltay - deltax
        elif (deltax >= 0) and (deltay >= 0) and (deltay > deltax): # 2nd oct
            if erro < 0:
                x += 1
                y += 1
                erro += deltay - deltax
            else:
                y += 1
                erro -= deltax
        elif (deltay >= 0) and (deltax < 0) and (-deltax >= deltay): # 4th oct (using C++ convention)
            if (erro < 0) or (deltay == 0):
                x -= 1
                erro += deltay
            else:
                x -= 1
                y += 1
                erro += deltax + deltay # Note: C++ had +deltax here too
        elif (deltay > 0) and (deltax < 0) and (deltay > -deltax): # 3rd oct (using C++ convention)
            if erro < 0:
                x -= 1
                y += 1
                erro += deltax + deltay # Note: C++ had +deltax here too
            else:
                y += 1
                erro += deltax # Note: C++ had +deltax here
        elif (deltax >= 0) and (deltay < 0) and (deltax >= -deltay): # 8th oct
            if erro < 0:
                x += 1
                erro -= deltay
            else:
                x += 1
                y -= 1
                erro += -deltay - deltax # Adjusted for negative deltay
        elif (deltax >= 0) and (deltay < 0) and (-deltay > deltax): # 7th oct
            if erro < 0:
                x += 1
                y -= 1
                erro += -deltay - deltax # Adjusted for negative deltay
            else:
                y -= 1
                erro -= deltax
        elif (deltay < 0) and (deltax < 0) and (-deltay > -deltax): # 6th oct (C++ called it 3rd?)
            if erro < 0:
                x -= 1
                y -= 1
                erro += deltax - deltay # Adjusted for negative deltay
            else:
                y -= 1
                erro += deltax # Note: C++ had +deltax here
        elif (deltay < 0) and (deltax < 0) and (-deltax >= -deltay): # 5th oct (C++ called it 4th?)
            if erro < 0:
                x -= 1
                erro -= deltay
            else:
                x -= 1
                y -= 1
                erro += deltax - deltay # Adjusted for negative deltay
        q += 1

# Point rotation
def rotation(vert: Vertex, yp: float, xp: float, teta: float):
    """ Rotates a Vertex object in place around (xp, yp) by teta degrees. """
    angle_rad = math.radians(teta) # Convert degrees to radians
    cos_t = math.cos(angle_rad)
    sin_t = math.sin(angle_rad)

    x_rel = vert.x - xp
    y_rel = vert.y - yp

    x_new = (x_rel * cos_t - y_rel * sin_t) + xp
    y_new = (x_rel * sin_t + y_rel * cos_t) + yp

    vert.x = x_new
    vert.y = y_new

# Verify if a pixel is a potential spiral origin (endpoint in skeleton)
def verify(img_: np.ndarray, y: int, x: int) -> bool:
    """ Checks if the pixel (y, x) has exactly 1 foreground neighbor in 3x3 grid. """
    height, width = img_.shape
    cont = 0
    # Check 3x3 neighborhood
    for i in range(max(0, y - 1), min(height, y + 2)):
        for j in range(max(0, x - 1), min(width, x + 2)):
            if i == y and j == x: # Skip center pixel
                continue
            if img_[i, j] == 0: # Count foreground neighbors (0)
                cont += 1
    # An endpoint in a skeleton typically has only one neighbor
    return cont == 1 # C++ used cont == 2, maybe checking non-skeletonized? Using 1 for skeleton endpoint. Adjust if needed.

# Find the spiral origin
def find_origen(img_: np.ndarray, oy_guess: int, ox_guess: int) -> Tuple[int, int]:
    """ Searches near the guess coordinates for a potential origin point. """
    height, width = img_.shape
    search_radius = 100 # Same as C++ code implies

    oy_best, ox_best = oy_guess, ox_guess # Default to guess if none found

    min_r = max(0, oy_guess - search_radius)
    max_r = min(height, oy_guess + search_radius)
    min_c = max(0, ox_guess - search_radius)
    max_c = min(width, ox_guess + search_radius)

    found = False
    for i in range(min_r, max_r):
        for j in range(min_c, max_c):
            if img_[i, j] == 0: # If it's a foreground pixel
                if verify(img_, i, j):
                    oy_best = i
                    ox_best = j
                    # print(f"Found potential origin at: ({ox_best}, {oy_best})")
                    found = True
                    break # Take the first one found in scan order
        if found:
            break

    if not found:
        print("Warning: Could not find a suitable origin point near the center using verify(). Using center guess.", file=sys.stderr)

    return oy_best, ox_best