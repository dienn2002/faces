import sys
import cv2
import requests
import numpy as np
import base64
from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QHeaderView
from camera import Ui_MainWindow 
from datetime import datetime

from process_img import get_compare_face, file_to_base64,frame_to_base64

# biến toàn cục
mode = "IN"
plate_number=""
user_mode = "ADD" 
doi = False
class MainApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.mode = "IN" 
        self.plate_number=""
        self.doi = False
        self.ui.btnVao.setStyleSheet("background-color: green;")
        self.ui.btnThem.setStyleSheet("background-color: green;")
        self.ui.btnSua.setStyleSheet("background-color: red;")
        self.ui.btnXoa.setStyleSheet("background-color: red;")
        self.hide_check_buttons()
        # self.arcface_model = DeepFace.build_model("ArcFace")

        
        self.cap_face = cv2.VideoCapture(1, cv2.CAP_DSHOW)
        self.cap_plate = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        # Kiểm tra camera
        if not self.cap_face.isOpened():
            self.ui.lineEditCheck.setText("Camera face không mở được!")
        if not self.cap_plate.isOpened():
            self.ui.lineEditCheck.setText("Camera plate không mở được!")

        self.frame_face = None
        self.frame_plate = None

        # Hiển thị thời gian hiện tại
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_frames)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)  # cập nhật mỗi giây

        # Timer cập nhật video
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frames)
        self.timer.start(30)  # ~33 FPS

        # Kết nối nút Vào / Ra
        self.ui.btnVao.clicked.connect(self.set_mode_in)
        self.ui.btnRa.clicked.connect(self.set_mode_out)

        # Kết nối nút SCAN
        self.ui.btnScan.clicked.connect(self.on_scan_clicked)
        self.ui.btnKiemTra.clicked.connect(self.handle_check)
        self.ui.btnConfirm.clicked.connect(self.verify_backup)
        self.ui.btnThem.clicked.connect(self.change_user_mode_them)
        self.ui.btnSua.clicked.connect(self.change_user_mode_sua)
        self.ui.btnXoa.clicked.connect(self.change_user_mode_xoa)
        self.ui.btnSearch.clicked.connect(self.handle_timkiem)
        self.ui.btnXacNhanDangKy.clicked.connect(self.submit_form)
        self.ui.checkBox.stateChanged.connect(self.handle_checkbox_change)

    def handle_checkbox_change(self, state):
        if state == Qt.CheckState.Checked:
            self.doi = False
        else:
            self.doi = True
    
    def set_mode_in(self):
        self.mode = "IN" 
        self.ui.btnVao.setStyleSheet("background-color: green;")
        self.ui.btnRa.setStyleSheet("background-color: red;")

    def set_mode_out(self):
        self.mode = "OUT" 
        self.ui.btnRa.setStyleSheet("background-color: green;")
        self.ui.btnVao.setStyleSheet("background-color: red;")


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
        
        try:
            # 1. Chuyển đổi màu từ BGR (OpenCV) sang RGB (Qt)
            rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            
            # 2. Tạo QImage
            qt_image = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
            pixmap = QtGui.QPixmap.fromImage(qt_image)
            
            # 3. Tính toán kích thước Label
            target_w = label.width() if label.width() > 0 else w
            target_h = label.height() if label.height() > 0 else h

            # 4. Scale ảnh về kích thước Label, giữ tỷ lệ khung hình
            scaled_pixmap = pixmap.scaled(
                target_w, 
                target_h, 
                Qt.AspectRatioMode.KeepAspectRatio,       # Giữ tỷ lệ khung hình (KHÔNG BỊ MÉO/CẮT)
                Qt.TransformationMode.SmoothTransformation # Làm mịn ảnh
            )
            
            # 5. Gán vào Label và căn giữa (căn giữa là tùy chọn để ảnh trông đẹp hơn)
            label.setPixmap(scaled_pixmap)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        except Exception as e:
            print(f"Lỗi hiển thị ảnh: {e}")
            label.clear()

    def on_scan_clicked(self):
        
        print("[AUTO] [START_PROCESS] [" + self.mode + "] time: " + str(datetime.now()))

        if self.frame_face is None or self.frame_plate is None:
            self.ui.lineEditCheck.setText("Không có ảnh từ camera!!!!")
            return
        
         # Hiển thị ảnh từ camera lên QLabel crop/preview
        self.display_image(self.frame_face, self.ui.lblFaceImage)
        self.display_image(self.frame_plate, self.ui.lblPlateImage)
        # _________Encode plate_______
        try:
            ok_p, buf_p = cv2.imencode('.jpg', self.frame_plate)
            if not ok_p:
                raise Exception("Encode plate failed")

            plate_b64 = base64.b64encode(buf_p).decode()

        except Exception as e:
            self.ui.lineEditCheck.setText(f"Lỗi encode plate: {str(e)}")
            print("Encode plate exception:", e)
            return
        
        inRequest = {
            "type": self.mode,  # IN / OUT
            "plate_image": plate_b64
        }
        
        try:
            response = requests.post('http://localhost:8000/smart-gate/v1/access-control/request', json=inRequest)
        
            response.raise_for_status()
            data = response.json()
            print("Call API access-control request type: " + inRequest["type"] + " successfully!")

            if data["is_success"]:
               self.compare_face_and_update_DB(data)
            else: 
                code = data.get("error_code")
                plate = data.get("plate_number", "")
                self.ui.lineEditPlate_2.setText(plate)
                
                if code == "DETECT_PLATE_NUMBER_ERROR":
                    self.ui.lineEditCheck.setText("Đọc biển số lỗi")

                elif code == "STATUS_INVALID":
                    self.ui.lineEditCheck.setText("Trạng thái xe không hợp lệ")

                elif code == "NOT_FOUND":
                    self.ui.lineEditCheck.setText("Không tìm thấy xe") # Có thể doc đọc sai biển, chần check lại 
                else:
                    self.ui.lineEditCheck.setText("Không xác định lỗi")
                
        except Exception as e:
            self.ui.lineEditCheck.setText(f"Lỗi kết nối server: {str(e)}")
            print("Exception:", e)
    def handle_check(self):
        print("[MANUAL] [START_PROCESS] [" + self.mode + "] time: " + str(datetime.now()))
        try:
            inRequest = {
                "request_type": self.mode,  
                "plate_number": self.ui.lineEditPlate_2.text()
            }

            response = requests.post('http://localhost:8000/smart-gate/v1/access-control/check-plate-number', json=inRequest)
        
            response.raise_for_status()
            data = response.json()
            print("Call API check-plate-number request type: " + inRequest["request_type"] + " successfully!")
            
            if data["is_success"]:
                self.compare_face_and_update_DB(data)
            else: 
                code = data.get("error_code")
                plate = data.get("plate_number", "")
                self.ui.lineEditPlate_2.setText(plate)
                
                if code == "STATUS_INVALID":
                    self.ui.lineEditCheck.setText("Trạng thái xe không hợp lệ")

                elif code == "NOT_FOUND":
                    self.ui.lineEditCheck.setText("Xe chưa được đăng ký") # Nhập tay nên chắc chắn biển số là đúng
                else:
                    self.ui.lineEditCheck.setText("Không xác định lỗi")
        except Exception as ex:
            self.ui.lineEditCheck.setText(f"Lỗi kết nối server: {str(ex)}")
            print("Exception:", ex)
    
    def verify_backup(self):
        try:
            approveInRequest = {
                "plate_number":  self.plate_number,
                "plate_image": frame_to_base64(self.frame_plate),
                "approval_type": self.mode
            }
            response = requests.post('http://localhost:8000/smart-gate/v1/access-control/verify-backup', json=approveInRequest)
            response.raise_for_status()
            data = response.json()

            print("Call API verify-backup  request type: " + self.mode + " successfully!")

            if data["is_success"]:
                if self.mode == "IN":
                    self.ui.lineEditCheck.setText("Mời xe Vào")
                else:
                    self.ui.lineEditCheck.setText("Mời xe Ra")
                print("[PROCESS] [" + self.mode + "] time: " + str(datetime.now()) + "[DONE]")
            else: 
                self.ui.lineEditCheck.setText("Lỗi hệ thống")
        
        except Exception as ex:
            self.ui.lineEditCheck.setText(f"Lỗi kết nối server: {str(ex)}")
            print("Exception:", ex)

    def change_user_mode_them(self):
        global user_mode
        user_mode = "ADD"
        self.ui.btnThem.setStyleSheet("background-color: green;")
        self.ui.btnSua.setStyleSheet("background-color: red;")
        self.ui.btnXoa.setStyleSheet("background-color: red;")
        self.hide_check_buttons()
        self.clear_form()

    def change_user_mode_sua(self):
        global user_mode
        user_mode = "EDIT"      
        self.ui.btnThem.setStyleSheet("background-color: red;")
        self.ui.btnSua.setStyleSheet("background-color: green;")
        self.ui.btnXoa.setStyleSheet("background-color: red;")
        self.show_check_buttons()
        self.clear_form()
        self.doi = False

    def change_user_mode_xoa(self):
        global user_mode
        user_mode = "DELETE"
        self.ui.btnThem.setStyleSheet("background-color: red;")
        self.ui.btnSua.setStyleSheet("background-color: red;")
        self.ui.btnXoa.setStyleSheet("background-color: green;")
        self.hide_check_buttons()
        self.clear_form()

    def submit_form(self):
        global user_mode
        if user_mode == "ADD":
            self.handle_them()
        elif user_mode == "EDIT":
            self.handle_sua()
        elif user_mode == "DELETE":
            self.handle_xoa()
        else:
            self.ui.lineEditCheck.setText("Chưa chọn chế độ thao tác người dùng")

    def handle_them(self):
        full_name = self.ui.editFullName.text()
        email = self.ui.editEmail.text()
        phone_number = self.ui.editSdt.text()
        plate_image_b64 = frame_to_base64(self.frame_plate) if self.frame_plate is not None else None
        face_image_b64 = frame_to_base64(self.frame_face) if self.frame_face is not None else None
        plate_number = self.ui.plateNumber.text()
    
        inRequest = {
            "full_name": full_name,
            "email": email,
            "phone_number": phone_number,
            "plate_number": plate_number,
            "plate_image": plate_image_b64,
            "face_image": face_image_b64
        }

        response = requests.post('http://localhost:8000/smart-gate/v1/users/register', json=inRequest)
        response.raise_for_status()
        data = response.json()

        if data["is_success"]:
            self.ui.lineEditCheck.setText("Thêm người dùng thành công")
        else:
            self.ui.lineEditCheck.setText("Lỗi khi thêm người dùng")

    def handle_sua(self):
        # lấy dữ liệu từ form
        plate_number = self.ui.plateNumber.text()
        full_name = self.ui.editFullName.text()
        email = self.ui.editEmail.text()
        phone_number = self.ui.editSdt.text()
        if self.doi:
            plate_image_b64 = frame_to_base64(self.frame_plate) 
            face_image_b64 = frame_to_base64(self.frame_face)
        else:
            plate_image_b64 = None
            face_image_b64 = None

        updateRequest = {
            "plate_number": plate_number,
            "full_name": full_name,
            "email": email,
            "phone_number": phone_number,
            "plate_image": plate_image_b64,
            "face_image": face_image_b64
        }

        try:
            response = requests.put('http://localhost:8000/smart-gate/v1/users/update', json=updateRequest)
            response.raise_for_status()
            data = response.json()

            if data["is_success"]:
                self.ui.lineEditCheck.setText("Cập nhật người dùng thành công")

                # hiển thị ảnh mới trên form
                # if plate_image_b64:
                #     self.update_image_from_base64(plate_image_b64, self.ui.lblPlateImage)
                # if face_image_b64:
                #     self.update_image_from_base64(face_image_b64, self.ui.lblFaceImage)
            else:
                self.ui.lineEditCheck.setText("Cập nhật người dùng thất bại")
        except Exception as e:
            print("Lỗi khi gọi API cập nhật người dùng:", e)
            self.ui.lineEditCheck.setText("Lỗi khi cập nhật người dùng")
            return

    def handle_xoa(self):
        plate_number = self.ui.plateNumber.text()  #dùng ô nhập biển số hiện có để xóa 
        if not plate_number:
            self.ui.lineEditCheck.setText("Vui lòng nhập biển số để xóa")
            return
        
        reply = QtWidgets.QMessageBox.question(
            self,
            'Xác nhận xóa', 
            f'Bạn có chắc chắn muốn xóa xe với biển số {plate_number} không?',
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)

        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return  # Người dùng hủy xóa
        
        try:
            response = requests.delete('http://localhost:8000/smart-gate/v1/users/delete', json={"plate_number": plate_number})
            response.raise_for_status()
            data = response.json()

            if data["is_success"]:
                self.ui.lineEditCheck.setText(f"Xóa người dùng có biển số xe {plate_number} thành công")

                self.ui.editFullName.clear()
                self.ui.editEmail.clear()
                self.ui.editSdt.clear()
                self.ui.lineEditPlate_2.clear()
                self.ui.lblPlateImage.clear()
                self.ui.lblFaceImage.clear()
            else:
                self.ui.lineEditCheck.setText("Xóa người dùng thất bại")
        except Exception as e:
            print("Lỗi khi gọi API xóa người dùng:", e)
            self.ui.lineEditCheck.setText("Lỗi khi xóa người dùng")
            return
        
    def handle_timkiem(self):
        plate_number = self.ui.plateNumber.text().strip()
        if not plate_number:
            self.ui.lineEditCheck.setText("Vui lòng nhập biển số để tìm kiếm")
            return
        
        try:
            inRequest = {"plate_number": plate_number}
            response = requests.post('http://localhost:8000/smart-gate/v1/users/search', json=inRequest)
            response.raise_for_status()
            data = response.json()

            if data["is_success"]:
                user_data = data["user"]
                history_list = data.get("history", [])

                # hiển thị thông tin người dùng
                if user_data:
                    self.ui.editFullName.setText(user_data.get("full_name", ""))
                    self.ui.editEmail.setText(user_data.get("email", ""))
                    self.ui.editSdt.setText(user_data.get("phone_number", ""))
            

                # hiển thị ảnh người dùng và biển số
                plate_image_b64 = user_data.get("plate_image")
                face_image_b64 = user_data.get("face_image")
                if plate_image_b64:
                    self.update_image_from_base64(plate_image_b64, self.ui.lblPlateImage)
                else:
                    self.ui.lblPlateImage.clear()
                if face_image_b64:
                    self.update_image_from_base64(face_image_b64, self.ui.lblFaceImage)
                else:
                    self.ui.lblFaceImage.clear()

                        
                # hiển thị lịch sử lên tableWidget
                table = self.ui.tableWidget
                table.setRowCount(len(history_list))
                table.setColumnCount(4)
                table.setHorizontalHeaderLabels(["BIỂN SỐ", "THỜI GIAN", "LƯỢT", "TT"])
                table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

                total_width = table.viewport().width()
                table.setColumnWidth(0, int(total_width * 0.30)) # Biển số: 30%
                table.setColumnWidth(1, int(total_width * 0.50)) # Thời gian: 50%
                table.setColumnWidth(2, int(total_width * 0.10)) # Lượt: 10%
                table.setColumnWidth(3, int(total_width * 0.10)) # TT: 10%
              
                for row_idx, h in enumerate(history_list):
                    table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(h.get("plate_number", "")))
                    table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(h.get("created_at", "")))
                    table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(str(h.get("count", ""))))
                    table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(h.get("status", "")))
                # table.resizeColumnsToContents()
                table.resizeRowsToContents()

                self.ui.lineEditCheck.setText("Tìm kiếm thành công")
            else:
                # Không tìm thấy dữ liệu hoặc lỗi
                self.ui.lineEditCheck.setText(data.get("error_message", "Không tìm thấy dữ liệu"))
                # Xóa các trường hiển thị
                self.ui.editFullName.clear()
                self.ui.editEmail.clear()
                self.ui.editSdt.clear()
                self.ui.lblFaceImage.clear()
                self.ui.lblPlateImage.clear()
        except Exception as ex:
            self.ui.lineEditCheck.setText(f"Lỗi kết nối server")
            print("Exception:", ex)


    def compare_face_and_update_DB(self, data):
        self.plate_number=data["plate_number"]
        self.ui.lineEditName.setText(data["full_name"])
        self.ui.lineEditPlate.setText(data["plate_number"])
        self.ui.lineEditRecently.setText(data["update_time"])
        self.ui.lineEditCount.setText(str(data["count"]))

        b64_string_db = data["face_image"] 

        b64_string_ui = frame_to_base64(self.frame_face)

        verification_result=get_compare_face(b64_string_db, b64_string_ui)
        
        verified = verification_result[0]

        if verified:
            approveInRequest = {
                "plate_number":data["plate_number"] ,
                "face_image": b64_string_ui,
                "plate_image": frame_to_base64(self.frame_plate),
                "approval_type": self.mode
            }
            response = requests.post('http://localhost:8000/smart-gate/v1/access-control/success', json=approveInRequest)
            response.raise_for_status()
            data = response.json()

            print("Call API handle-success request type: " + self.mode + " successfully!")

            if data["is_success"]:
                if self.mode == "IN":
                    self.ui.lineEditCheck.setText("Mời xe Vào")
                else:
                    self.ui.lineEditCheck.setText("Mời xe Ra")
                print("[PROCESS] [" + self.mode + "] time: " + str(datetime.now()) + "[DONE]")
            else: 
                self.ui.lineEditCheck.setText("Lỗi hệ thống")

        else:
            self.ui.lineEditCheck.setText("So khớp khuôn mặt lỗi")
            # Show ảnh DB ra
            img_data = base64.b64decode(b64_string_db)
            nparr = np.frombuffer(img_data, np.uint8)
            cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if cv_img is not None:
                print("[GET_FACE_IMAGE] - success!")
                self.frame_face = cv_img
                self.display_image(self.frame_face, self.ui.lblFaceImage)
            print("[COMPARE_FACE] - compare failed!")
            return False 

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
    
    def update_clock(self):
        # Lấy thời gian hiện tại
        now = datetime.now()
        # Định dạng chuỗi: Giờ:Phút:Giây Ngày/Tháng/Năm
        time_str = now.strftime("%H:%M:%S %d/%m/%Y")
        
        self.ui.time.setText(time_str)

    def clear_form(self):
        self.ui.editFullName.clear()
        self.ui.editEmail.clear()
        self.ui.editSdt.clear()
       
    def hide_check_buttons(self):
        self.ui.checkBox.hide()
        self.ui.btnDoi.hide()

    def show_check_buttons(self):
        self.ui.checkBox.show()
        self.ui.btnDoi.show()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = MainApp()
    win.show()
    sys.exit(app.exec())
