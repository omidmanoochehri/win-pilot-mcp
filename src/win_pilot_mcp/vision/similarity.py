from __future__ import annotations

from pathlib import Path


def compare_screenshots(before: Path, after: Path, threshold: int = 25) -> dict[str, object]:
    try:
        import cv2

        before_img = cv2.imread(str(before), cv2.IMREAD_GRAYSCALE)
        after_img = cv2.imread(str(after), cv2.IMREAD_GRAYSCALE)
        if before_img is None or after_img is None:
            raise FileNotFoundError("Could not read one or both screenshots")
        if before_img.shape != after_img.shape:
            after_img = cv2.resize(after_img, (before_img.shape[1], before_img.shape[0]))
        diff = cv2.absdiff(before_img, after_img)
        changed = diff > threshold
        changed_pixels = int(changed.sum())
        total_pixels = int(diff.shape[0] * diff.shape[1])
        boxes = _regions_cv2(changed)
    except ModuleNotFoundError:
        from PIL import Image, ImageChops

        before_image = Image.open(before).convert("L")
        after_image = Image.open(after).convert("L").resize(before_image.size)
        diff_image = ImageChops.difference(before_image, after_image)
        thresholded = diff_image.point(lambda pixel: 255 if pixel > threshold else 0)
        histogram = thresholded.histogram()
        changed_pixels = int(histogram[255])
        total_pixels = before_image.width * before_image.height
        boxes = _regions_pillow(thresholded)
    return {
        "changed": changed_pixels > 0,
        "changedPixels": changed_pixels,
        "totalPixels": total_pixels,
        "changeRatio": changed_pixels / max(1, total_pixels),
        "regions": boxes,
    }


def _regions_cv2(changed) -> list[dict[str, int]]:
    import cv2

    contours, _ = cv2.findContours(
        changed.astype("uint8") * 255,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w * h >= 64:
            boxes.append({"x": int(x), "y": int(y), "width": int(w), "height": int(h)})
    return boxes


def _regions_pillow(thresholded) -> list[dict[str, int]]:
    bbox = thresholded.getbbox()
    if not bbox:
        return []
    x1, y1, x2, y2 = bbox
    if (x2 - x1) * (y2 - y1) < 64:
        return []
    return [{"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}]
