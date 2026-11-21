# Paper kit

The printable mat and parts sheet. Owned by the vision lane.

To build in phase 1: `make_kit.py`, which renders an A4 PDF of the dot-grid mat (ArUco marker in each corner) and a parts sheet (battery, bulb, resistor, switch; each spans two dots and carries its own marker), using `cv2.aruco.generateImageMarker` and Pillow.

The grid geometry (dot spacing in mm, columns, rows, marker size, which marker ids mean which part) must live in one module that both this script and `server/tacto/vision/` import, so the printed kit and the reader cannot disagree.

Print at 100% scale. Check the dot spacing with a ruler.
