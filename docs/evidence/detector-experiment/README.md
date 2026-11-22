# The component detector we tried first

On 21 Nov 2026, before the paper kit existed, we ran Roboflow's hosted object-detection model `component-finder/1` on a picture of our circuit (`roboflow_test.py`; input `circuit.jpg`, output `circuit_detected.jpg`).

What it showed:

- It labelled an empty slot as an **integrated circuit (43%)** and a wire tile as a **transformer (68%)**, and found the printed text more confidently than the parts.
- It found **no wires**, and wires are most of a circuit.
- It returns boxes in camera pixels, not which two dots a part joins, so every box would still need mapping onto the grid. With the webcam looking across the desk at an angle, a box drawn round a part's outline does not land on the dots it sits between.
- It is a cloud call per image, and the live loop must run with the Wi-Fi off.

So we moved to a grid that turns reading the mat into one colour question per dot-to-dot segment, calibrated every frame by colour squares printed on the mat. See the README's "Challenges" section.

Kept for the record. The script is not part of the project and its dependencies are not installed (`pip install inference-sdk opencv-python`, and a `ROBOFLOW_API_KEY`).
