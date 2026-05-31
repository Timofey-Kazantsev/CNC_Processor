import sys
import os
import pygame
import requests
import subprocess
import re

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt, QUrl, QDir, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QDrag
from PyQt5.QtCore import QMimeData
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QMainWindow, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QAction

from Processor import Processor
from visual import ViewerContainer


APP_NAME = "CNC_Processor"
CURRENT_VERSION = "1.0.0"
GITHUB_REPO = "Timofey-Kazantsev/CNC_Processor"


def version_tuple(v):
    parts = v.strip().lstrip("v").split(".")
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])


class UpdateCheckThread(QThread):
    found_update = pyqtSignal(dict)
    status = pyqtSignal(str)

    def run(self):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()

            latest_version = data.get("tag_name", "").lstrip("v").strip()

            if version_tuple(latest_version) > version_tuple(CURRENT_VERSION):
                self.found_update.emit({
                    "version": latest_version,
                    "body": data.get("body", ""),
                    "assets": data.get("assets", [])
                })
            else:
                self.status.emit("Установлена последняя версия")
        except Exception as e:
            self.status.emit(f"Проверка обновлений не удалась: {e}")


class DownloadUpdateThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path

    def run(self):
        try:
            with requests.get(self.url, stream=True, timeout=60) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                done = 0
                with open(self.save_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            done += len(chunk)
                            if total:
                                self.progress.emit(int(done * 100 / total))
            self.finished.emit(self.save_path)
        except Exception as e:
            self.error.emit(str(e))


class UpdateDialog(QDialog):
    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.info = info
        self.worker = None
        self.setWindowTitle(f"{APP_NAME} — доступно обновление")
        self.setMinimumSize(460, 300)
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel(f"Найдена новая версия: {self.info['version']}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        body = QLabel(self.info.get("body", "") or "Без описания")
        body.setWordWrap(True)
        layout.addWidget(body)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        row = QHBoxLayout()

        self.btn_download = QPushButton("Скачать установщик")
        self.btn_download.clicked.connect(self.download)
        row.addWidget(self.btn_download)

        btn_close = QPushButton("Позже")
        btn_close.clicked.connect(self.reject)
        row.addWidget(btn_close)

        layout.addLayout(row)

    def download(self):
        asset = None
        for a in self.info.get("assets", []):
            name = a.get("name", "").lower()
            if name.endswith(".exe"):
                asset = a
                break

        if not asset:
            QMessageBox.warning(self, "Ошибка", "В релизе не найден .exe файл.")
            return

        url = asset["browser_download_url"]
        save_path = os.path.join(os.environ.get("TEMP", "."), asset["name"])

        self.progress.setVisible(True)
        self.btn_download.setEnabled(False)

        self.worker = DownloadUpdateThread(url, save_path)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.on_done)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_done(self, path):
        QMessageBox.information(self, "Готово", f"Установщик скачан:\n{path}")
        self.accept()
        try:
            subprocess.Popen([path], creationflags=subprocess.CREATE_NEW_CONSOLE)
        except Exception:
            subprocess.Popen([path])

    def on_error(self, msg):
        QMessageBox.critical(self, "Ошибка", msg)
        self.btn_download.setEnabled(True)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")

        screen = QtWidgets.QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        window_width = screen_width // 2
        window_height = screen_height - 30

        x_position = screen_width // 2
        y_position = 30

        MainWindow.setGeometry(x_position, y_position, window_width, window_height)
        MainWindow.setMinimumSize(QtCore.QSize(window_width, window_height))
        MainWindow.setMaximumSize(QtCore.QSize(window_width, window_height))

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        widget_scale_x = window_width / 876
        widget_scale_y = window_height / 1000

        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(
            int(670 * widget_scale_x), int(20 * widget_scale_y),
            int(131 * widget_scale_x), int(23 * widget_scale_y)
        ))
        self.pushButton.setObjectName("pushButton")

        self.pushButton_2 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_2.setGeometry(QtCore.QRect(
            int(670 * widget_scale_x), int(50 * widget_scale_y),
            int(131 * widget_scale_x), int(23 * widget_scale_y)
        ))
        self.pushButton_2.setObjectName("pushButton_2")

        self.pushButton_3 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_3.setGeometry(QtCore.QRect(
            int(670 * widget_scale_x), int(80 * widget_scale_y),
            int(131 * widget_scale_x), int(23 * widget_scale_y)
        ))
        self.pushButton_3.setObjectName("pushButton_3")

        self.textBrowser = QtWidgets.QTextBrowser(self.centralwidget)
        self.textBrowser.setGeometry(QtCore.QRect(
            int(10 * widget_scale_x), int(20 * widget_scale_y),
            int(321 * widget_scale_x), int(531 * widget_scale_y)
        ))
        self.textBrowser.setObjectName("textBrowser")

        self.textBrowser_2 = QtWidgets.QTextBrowser(self.centralwidget)
        self.textBrowser_2.setGeometry(QtCore.QRect(
            int(340 * widget_scale_x), int(20 * widget_scale_y),
            int(321 * widget_scale_x), int(531 * widget_scale_y)
        ))
        self.textBrowser_2.setObjectName("textBrowser_2")

        self.dropLabel = QtWidgets.QLabel(self.centralwidget)
        self.dropLabel.setGeometry(QtCore.QRect(
            int(670 * widget_scale_x), int(120 * widget_scale_y),
            int(131 * widget_scale_x), int(100 * widget_scale_y)
        ))
        self.dropLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.dropLabel.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                padding: 10px;
            }
            QLabel:hover {
                border: 2px dashed #555;
                background: #f0f0f0;
            }
        """)
        self.dropLabel.setObjectName("dropLabel")

        self.saveLabel = QtWidgets.QLabel(self.centralwidget)
        self.saveLabel.setGeometry(QtCore.QRect(
            int(670 * widget_scale_x), int(230 * widget_scale_y),
            int(131 * widget_scale_x), int(100 * widget_scale_y)
        ))
        self.saveLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.saveLabel.setStyleSheet("""
            QLabel {
                border: 2px dashed #4CAF50;
                padding: 10px;
                background: #f8fff8;
            }
            QLabel:hover {
                border: 2px dashed #2E7D32;
                background: #e8f5e9;
            }
        """)
        self.saveLabel.setObjectName("saveLabel")

        self.visualFrame = QtWidgets.QFrame(self.centralwidget)
        self.visualFrame.setGeometry(QtCore.QRect(
            int(10 * widget_scale_x), int(560 * widget_scale_y),
            int(851 * widget_scale_x), int(380 * widget_scale_y)
        ))
        self.visualFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.visualFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.visualFrame.setObjectName("visualFrame")

        self.visualLayout = QtWidgets.QVBoxLayout(self.visualFrame)
        self.visualLayout.setContentsMargins(0, 0, 0, 0)
        self.visualLayout.setSpacing(0)

        self.visualizationWidget = ViewerContainer(self.visualFrame)
        self.visualLayout.addWidget(self.visualizationWidget)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, window_width, int(21 * widget_scale_y)))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)

        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "CNC Processor"))
        self.pushButton.setText(_translate("MainWindow", "Загрузить файл"))
        self.pushButton_2.setText(_translate("MainWindow", "Скачать файл"))
        self.pushButton_3.setText(_translate("MainWindow", "Удалить файл"))
        self.dropLabel.setText(_translate("MainWindow", "Перетащите\nфайл\nсюда"))
        self.saveLabel.setText(_translate("MainWindow", "Перетащите\nдля\nсохранения"))


class MyWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.pushButton.clicked.connect(self.load_file)
        self.ui.pushButton_2.clicked.connect(self.download_file)
        self.ui.pushButton_3.clicked.connect(self.delete_file)

        self.setAcceptDrops(True)
        self.ui.dropLabel.setAcceptDrops(True)
        self.ui.dropLabel.dragEnterEvent = self.dragEnterEvent
        self.ui.dropLabel.dropEvent = self.dropEvent

        self.ui.saveLabel.setAcceptDrops(False)
        self.ui.saveLabel.mousePressEvent = self.startDragSave
        self.ui.saveLabel.setEnabled(False)

        self.processor = None
        self.current_file = None
        self.output_content = ""

        self.add_update_menu()
        QTimer.singleShot(3000, self.check_updates)

        try:
            pygame.mixer.init()
            sound_path = os.path.join(os.path.dirname(__file__), "Error Sound.mp3")
            if os.path.exists(sound_path):
                self.error_sound = pygame.mixer.Sound(sound_path)
                self.error_sound.set_volume(1.0)
            else:
                self.error_sound = None
                print("WARNING: Error Sound.mp3 не найден")
        except Exception as e:
            self.error_sound = None
            print(f"WARNING: Не удалось инициализировать звук: {e}")

    def add_update_menu(self):
        self.menu_help = self.ui.menubar.addMenu("Помощь")
        self.action_check_updates = QAction("Проверить обновления", self)
        self.action_check_updates.triggered.connect(self.check_updates)
        self.menu_help.addAction(self.action_check_updates)

    def check_updates(self):
        self.ui.statusbar.showMessage("Проверка обновлений...", 3000)
        self.upd_thread = UpdateCheckThread()
        self.upd_thread.found_update.connect(self.on_update_found)
        self.upd_thread.status.connect(self.on_update_status)
        self.upd_thread.start()

    def on_update_found(self, info):
        self.ui.statusbar.showMessage(f"Доступна версия {info['version']}", 5000)
        dlg = UpdateDialog(info, self)
        dlg.exec_()

    def on_update_status(self, msg):
        self.ui.statusbar.showMessage(msg, 5000)

    def play_error_sound(self):
        if self.error_sound:
            try:
                self.error_sound.play()
            except Exception as e:
                print(f"WARNING: Не удалось воспроизвести звук: {e}")

    def validate_file(self, file_path, content):
        valid_extensions = ['.cnc', '.txt']
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in valid_extensions:
            return False, f"<b>Неверное расширение файла!</b><br>Допустимые расширения: {', '.join(valid_extensions)}"

        if not content.strip():
            return False, "<b>Файл пустой!</b><br>Загрузите файл с G-кодом."

        file_name = os.path.basename(file_path)
        if '=' not in file_name:
            self.play_error_sound()
            return False, f"<b>Неверное имя файла!</b><br><br>В имени файла должен быть знак '='<br><br>Пример правильного имени:<br><b>Фронтальная=2790x375_ДСП_16_-_Trends_.CNC</b>"

        size_pattern = r'=(\d+)x(\d+)'
        if not re.search(size_pattern, file_name):
            self.play_error_sound()
            return False, f"<b>Неверный формат имени файла!</b><br><br>После '=' должны быть размеры в формате WIDTHxHEIGHT<br><br>Пример:<br><b>Фронтальная=2790x375_ДСП_16_-_Trends_.CNC</b>"

        g_code_pattern = r'\b[Gg][0-3]|[Tt][0-9]+|[XxYyZz][-]?\d+'
        if not re.search(g_code_pattern, content):
            return False, "<b>Неверный формат G-кода!</b><br>В файле не обнаружены команды CNC (G0, G1, T и т.д.)."

        return True, ""

    def check_y_coordinates(self, content):
        errors = []
        found_top = False
        found_bottom = False

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith(';'):
                continue

            new_y = None
            clean_line = re.sub(r'N\d+', '', line).upper().strip()
            parts = clean_line.split()

            for part in parts:
                if part.startswith('Y'):
                    try:
                        new_y = float(re.sub(r'[^0-9.-]', '', part[1:]))
                    except:
                        pass

            if new_y is not None:
                if new_y <= 36 and not found_top:
                    errors.append(("top", new_y))
                    found_top = True
                elif abs(new_y - (-10)) < 0.01 and not found_bottom:
                    errors.append(("bottom", new_y))
                    found_bottom = True

        return errors

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self.load_dragged_file(file_path)

    def load_dragged_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.play_error_sound()
            QMessageBox.critical(self, "Ошибка чтения файла",
                                 f"<b>Не удалось прочитать файл!</b><br><br>{str(e)}")
            return

        self.ui.textBrowser.setText(content)

        is_valid, error_msg = self.validate_file(file_path, content)
        if not is_valid:
            self.play_error_sound()
            QMessageBox.warning(self, "Ошибка загрузки файла", error_msg)
            self.ui.statusbar.showMessage("Ошибка: Неверный файл", 5000)
            return

        errors = self.check_y_coordinates(content)

        error_messages = []
        for error_type, y_value in errors:
            if error_type == "top":
                error_messages.append(f"<b>Обнаружено отверстие Y<={36}</b><br>"
                                      f"Найдена точка с Y = {y_value:.2f} мм<br><br>")
                self.play_error_sound()
            elif error_type == "bottom":
                error_messages.append(f"<b>Обнаружено нижнее торцевое отверстие</b><br>"
                                      f"Найдена точка с Y = {y_value:.2f} мм<br><br>")
                self.play_error_sound()

        if error_messages:
            msg = "<br>".join(error_messages) + "Файл будет обработан и отрисован."

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("Обнаружены ошибки координат Y")
            msg_box.setText(msg)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()

            self.ui.statusbar.showMessage(f"Обнаружены ошибки Y: {len(errors)}", 5000)

        try:
            self.processor = Processor(content, self)
            self.current_file = file_path
            self.processor.nameFile = file_path
            self.ui.statusbar.showMessage(f"Загружен файл: {file_path}", 3000)
            self.ui.saveLabel.setEnabled(True)
            self.do_file()
        except Exception as e:
            self.play_error_sound()
            QMessageBox.critical(self, "Ошибка компиляции",
                                 f"<b>Ошибка при компиляции G-кода!</b><br><br>{str(e)}")
            self.ui.statusbar.showMessage("Ошибка компиляции", 5000)

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл",
            "",
            "CNC файлы (*.CNC);;Текстовые файлы (*.txt);;Все файлы (*)",
            options=QFileDialog.Options()
        )
        if file_path:
            self.load_dragged_file(file_path)

    def do_file(self):
        if self.processor:
            try:
                self.processor.process()
                self.output_content = self.ui.textBrowser_2.toPlainText()
                if self.output_content:
                    self.ui.saveLabel.setEnabled(True)
                    filename = self.current_file or ""
                    self.ui.visualizationWidget.load_from_text(self.output_content, filename)
            except Exception as e:
                self.play_error_sound()
                QMessageBox.critical(self, "Ошибка обработки",
                                     f"<b>Ошибка при обработке G-кода!</b><br><br>{str(e)}")

    def delete_file(self):
        self.ui.textBrowser.clear()
        self.ui.textBrowser_2.clear()
        self.ui.visualizationWidget.viewer.scene.clear()
        self.ui.visualizationWidget.legend_label.setText("")
        self.processor = None
        self.current_file = None
        self.ui.saveLabel.setEnabled(False)

    def startDragSave(self, event):
        if not self.ui.textBrowser_2.toPlainText():
            return

        content = self.ui.textBrowser_2.toPlainText()

        if self.current_file:
            file_name = "ДонМебель_" + os.path.basename(self.current_file)
            if file_name.endswith('.CNC.CNC'):
                file_name = file_name[:-4]
        else:
            file_name = "ДонМебель_output.CNC"

        temp_path = os.path.join(QDir.tempPath(), file_name)

        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать временный файл:\n{str(e)}")
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(temp_path)])
        drag.setMimeData(mime_data)

        if drag.exec_(Qt.CopyAction) == Qt.CopyAction:
            self.ui.statusbar.showMessage(f"Файл {file_name} успешно сохранен", 3000)
        else:
            self.ui.statusbar.showMessage("Сохранение отменено", 2000)

        if os.path.exists(temp_path):
            os.remove(temp_path)

    def download_file(self):
        if not self.ui.textBrowser_2.toPlainText():
            return

        if self.current_file:
            dir_path = os.path.dirname(self.current_file)
            file_name = "ДонМебель_" + os.path.basename(self.current_file)
            default_path = os.path.join(dir_path, file_name)
        else:
            default_path = "ДонМебель_output.CNC"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить файл",
            default_path,
            "CNC файлы (*.CNC);;Текстовые файлы (*.txt);;Все файлы (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.ui.textBrowser_2.toPlainText())
                self.ui.statusbar.showMessage(f"Файл сохранен: {file_path}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{str(e)}")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyWidget()
    window.show()
    sys.exit(app.exec_())