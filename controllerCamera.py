import sys
import cv2
import requests
import numpy as np
import base64
from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtCore import QTimer, Qt
from camera import Ui_MainWindow 
from io import BytesIO
import requests
from PIL import Image
from deepface import DeepFace
import tempfile
from process_img import get_compare_face, file_to_base64

class MainApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # self.arcface_model = DeepFace.build_model("ArcFace")

        
        self.cap_face = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.cap_plate = cv2.VideoCapture(1, cv2.CAP_DSHOW)

        # Kiểm tra camera
        if not self.cap_face.isOpened():
            self.ui.lblKetQua.setText("Camera face không mở được!")
        if not self.cap_plate.isOpened():
            self.ui.lblKetQua.setText("Camera plate không mở được!")

        self.frame_face = None
        self.frame_plate = None

        # Hiển thị thời gian hiện tại
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_frames)
        self.clock_timer.start(1000)  # cập nhật mỗi giây

        # Timer cập nhật video
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frames)
        self.timer.start(30)  # ~33 FPS

        # Kết nối nút SCAN
        self.ui.btnScan.clicked.connect(self.on_scan_clicked)

    def update_frames(self):
        # Cập nhật frame từ 2 camera
        if self.cap_face.isOpened():
            ret_face, frame_face = self.cap_face.read()
            if ret_face:
                self.frame_face = frame_face
                self.display_image(frame_face, self.ui.lblCamera)
                
        if self.cap_plate.isOpened():
            ret_plate, frame_plate = self.cap_plate.read()
            if ret_plate:
                self.frame_plate = frame_plate
                self.display_image(frame_plate, self.ui.lblCamera_2)

    def display_image(self, cv_img, label):
        if cv_img is None:
            label.clear()
            return
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
        pixmap = QtGui.QPixmap.fromImage(qt_image)
        label.setPixmap(pixmap)

    def on_scan_clicked(self):
        # if self.frame_face is None or self.frame_plate is None:
        #     self.ui.lblKetQua.setText("Chưa có hình ảnh camera!")
        #     return

        # Encode ảnh
        # ret_face_encode, face_buf = cv2.imencode('.jpg', self.frame_face)
        # ret_plate_encode, plate_buf = cv2.imencode('.jpg', self.frame_plate)

        # if not ret_face_encode or not ret_plate_encode:
        #     self.ui.lblKetQua.setText("Encode ảnh thất bại!")
        #     return
    
        file_path = r"D:\smart_gate\images\test_17.jpg"
        inRequest = {
            "type": "OUT",
            "plate_image" : file_to_base64(file_path)
        }
    
        try:
            response = requests.post('http://localhost:8000/smart-gate/v1/access-control/request', json=inRequest)
            response.raise_for_status()
            data = response.json()
            print("cook")
            if data["is_success"]:
                b64_string_db = data["face_image"]
                # img_face_path_2= r"D:\faces\img\HoQuangHieu.jpg"
                # b64_string_db=file_to_base64(img_face_path_2)

                img_face_path= r"D:\faces\img\test.jpg"
                b64_string_ui=file_to_base64(img_face_path)

                verification_result=get_compare_face(b64_string_db, b64_string_ui)
                verified = verification_result[0]

                if verified :
                    approveInRequest = {
                        "plate_number":data["plate_number"] ,
                        "face_image": b64_string_ui,
                        "plate_image": file_to_base64(file_path),
                        "approval_type": "OUT"
                    }
                    response = requests.post('http://localhost:8000/smart-gate/v1/access-control/success', json=approveInRequest)
                    response.raise_for_status()
                    data = response.json()
                    print(data)

                else:
                    print("[COMPARE_FACE] - compare failed!")
        except Exception as e:
            self.ui.lblKetQua.setText(f"Lỗi kết nối server: {str(e)}")
            print("Exception:", e)

    def update_image_from_base64(self, b64_string, label):
        try:
            img_data = base64.b64decode(b64_string)
            nparr = np.frombuffer(img_data, np.uint8)
            cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if cv_img is not None:
                self.display_image(cv_img, label)
        except Exception as e:
            print("Lỗi decode ảnh base64:", e)
            label.clear()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = MainApp()
    win.show()
    sys.exit(app.exec())
