import cv2
import re
import base64
import os
import sys
from scipy.spatial.distance import cosine
import numpy as np
from deepface import DeepFace



# face_detector = MTCNN()

def get_compare_face(face_ui_base64: str, face_db_base64: str):

    try:

        MIME_PREFIX = "data:image/jpeg;base64,"
        
        # Kiểm tra và thêm tiền tố (để đảm bảo tính an toàn)
        if not face_ui_base64.startswith(MIME_PREFIX):
            img1_processed = MIME_PREFIX + face_ui_base64
        else:
            img1_processed = face_ui_base64 # Dùng nếu đã có tiền tố (an toàn)
            
        if not face_db_base64.startswith(MIME_PREFIX):
            img2_processed = MIME_PREFIX + face_db_base64
        else:
            img2_processed = face_db_base64

        print("START")
    
        verification_result = DeepFace.verify(
            img1_path=img1_processed,
            img2_path=img2_processed     # Chọn metric phù hợp với mô hình
        )
        
        verified = verification_result["verified"]
        distance = verification_result["distance"]
        
        return verified, distance


    except Exception as e:
        print("Lỗi trong get_compare_face:", e)
        return False, 0.0
    
def file_to_base64(file_path: str) -> str:
    if not os.path.exists(file_path):
        print(f"Lỗi: Tệp không tồn tại tại đường dẫn: {file_path}", file=sys.stderr)
        return ""
        
    try:
        with open(file_path, "rb") as image_file:
            binary_data = image_file.read()
            base64_encoded_data = base64.b64encode(binary_data)
            return base64_encoded_data.decode('utf-8')
    except Exception as e:
        print(f"Lỗi khi xử lý file: {e}", file=sys.stderr)
        return ""

def get_embedding(img_base64: str, model):
    if model is None: return None
        
    embeddings_list = DeepFace.represent(
        img_path=img_base64,
        model=model,                 # <-- Truyền đối tượng mô hình đã load
        enforce_detection=True,      # Bắt buộc phát hiện khuôn mặt
        detector_backend="opencv",   # Detector nhanh và ổn định
        align=True
    )
    
    if embeddings_list:
        return np.array(embeddings_list[0]["embedding"])
    return None





# Load ảnh test
img_ui = cv2.imread(r"D:\face\images\cs_Emily.jpg")
with open(r"D:\face\images\emily2.jpg", "rb") as f:
    db_b64 = base64.b64encode(f.read()).decode("utf-8")

# match, conf = get_compare_face(img_ui, db_b64)
# print("Match:", match, "Confidence:", conf)