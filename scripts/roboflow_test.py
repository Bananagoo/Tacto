"""
Run the Roboflow "component-finder/1" model on a photo of a circuit.

What it does:
  1. Sends your image to Roboflow's cloud API.
  2. Prints every component it found (type, confidence, position).
  3. Saves a copy of the image with boxes drawn on it: <name>_detected.jpg

Setup (once):
  pip install inference-sdk opencv-python

  Set your API key as an environment variable (never paste it into code):
    macOS / Linux:        export ROBOFLOW_API_KEY="your_key_here"
    Windows PowerShell:   $env:ROBOFLOW_API_KEY="your_key_here"

Run:
  python roboflow_test.py my_circuit_photo.jpg
  python roboflow_test.py my_circuit_photo.jpg --min-confidence 0.5
"""

import argparse
import os
import sys

import cv2
from inference_sdk import InferenceConfiguration, InferenceHTTPClient

MODEL_ID = "component-finder/1"


def run_model(image_path: str) -> dict:
    api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        sys.exit(
            "No API key found. Set the ROBOFLOW_API_KEY environment variable first "
            "(see the instructions at the top of this file)."
        )

    client = InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key=api_key,
    ).configure(InferenceConfiguration(api_key_transport="header"))

    return client.infer(image_path, model_id=MODEL_ID)


def draw_boxes(image_path: str, predictions: list, out_path: str) -> None:
    img = cv2.imread(image_path)
    if img is None:
        print(f"Could not open {image_path} to draw boxes (the detection list above is still valid).")
        return

    for p in predictions:
        # Roboflow gives the CENTRE of the box (x, y) plus its width and height.
        x0 = int(p["x"] - p["width"] / 2)
        y0 = int(p["y"] - p["height"] / 2)
        x1 = int(p["x"] + p["width"] / 2)
        y1 = int(p["y"] + p["height"] / 2)
        label = f'{p["class"]} {p["confidence"]:.0%}'

        cv2.rectangle(img, (x0, y0), (x1, y1), (0, 200, 0), 2)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(img, (x0, max(0, y0 - th - 8)), (x0 + tw + 6, y0), (0, 200, 0), -1)
        cv2.putText(img, label, (x0 + 3, y0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    cv2.imwrite(out_path, img)
    print(f"\nSaved annotated image: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect circuit components in a photo.")
    parser.add_argument("image", help="Path to a photo of your circuit (jpg or png)")
    parser.add_argument("--min-confidence", type=float, default=0.4,
                        help="Ignore detections below this confidence (0 to 1, default 0.4)")
    args = parser.parse_args()

    print(f"Running Roboflow model {MODEL_ID} on {args.image} ...")

    if not os.path.exists(args.image):
        sys.exit(f"File not found: {args.image}")

    print(f"Sending {args.image} to {MODEL_ID} ...")
    result = run_model(args.image)

    predictions = [p for p in result.get("predictions", [])
                   if p["confidence"] >= args.min_confidence]
    predictions.sort(key=lambda p: (p["y"], p["x"]))  # top-to-bottom, left-to-right

    print(f"\nFound {len(predictions)} component(s) "
          f"(confidence >= {args.min_confidence:.0%}):\n")
    print(f'{"type":<22}{"confidence":>11}{"centre x":>10}{"centre y":>10}')
    for p in predictions:
        print(f'{p["class"]:<22}{p["confidence"]:>10.0%}{p["x"]:>10.0f}{p["y"]:>10.0f}')

    base, _ = os.path.splitext(args.image)
    draw_boxes(args.image, predictions, f"{base}_detected.jpg")


if __name__ == "__main__":
    main()