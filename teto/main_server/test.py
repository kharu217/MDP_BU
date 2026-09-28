from ultralytics import YOLO
import cv2
import numpy as np
import os
import glob

model = YOLO(r"C:\Users\kharu217\Documents\teto\yolov26m-600.onnx", task="obb")  # OBB 모델 가중치 경로

def crop_obb(image_path, output_dir, base_name):
    img = cv2.imread(image_path)
    if img is None:
        print(f"[ERROR] 이미지 로드 실패: {image_path}")
        return []

    results = model(img)[0]
    obb = results.obb

    if obb is None or len(obb) == 0:
        print(f"[WARN] 검출 결과 없음: {image_path}")
        return []

    crops = []
    xyxyxyxy = obb.xyxyxyxy.cpu().numpy()

    for i, pts in enumerate(xyxyxyxy):
        pts = pts.astype(np.float32)
        rect = cv2.minAreaRect(pts)
        (cx, cy), (w, h), angle = rect

        if w < h:
            w, h = h, w
            angle += 90

        M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
        rotated = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]))

        x1 = max(0, int(cx - w / 2))
        y1 = max(0, int(cy - h / 2))
        x2 = min(rotated.shape[1], int(cx + w / 2))
        y2 = min(rotated.shape[0], int(cy + h / 2))

        crop = rotated[y1:y2, x1:x2]
        if crop.size == 0:
            continue

        out_path = os.path.join(output_dir, f"{base_name}_{i}.jpg")
        success, buf = cv2.imencode(".jpg", crop)
        if success:
            buf.tofile(out_path)
            crops.append(out_path)

    return crops


def crop_obb_folder(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    exts = ("*.jpg", "*.jpeg", "*.png", "*.bmp")
    image_paths = []
    for ext in exts:
        image_paths.extend(glob.glob(os.path.join(input_dir, ext)))

    total_crops = []
    for path in image_paths:
        base_name = os.path.splitext(os.path.basename(path))[0]
        crops = crop_obb(path, output_dir, base_name)
        total_crops.extend(crops)

    return total_crops

if __name__ == "__main__" :
    crop_obb_folder(input_dir=r"C:\Users\kharu217\Downloads\drive-download-20260903T075055Z-1-001", output_dir="book_crop")