import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QRadioButton, QProgressBar, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from pytube import YouTube, Playlist
import os
import time

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    speed = pyqtSignal(float)
    completed = pyqtSignal(str)

    def __init__(self, url, save_path, quality):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.quality = quality
        self._running = True

    def run(self):
        try:
            yt = YouTube(self.url, on_progress_callback=self.on_progress)
            if self.quality == "Best":
                stream = yt.streams.get_highest_resolution()
            elif self.quality == "Normal":
                stream = yt.streams.get_lowest_resolution()
            else:
                stream = yt.streams.first()

            self.start_time = time.time()
            self.total_size = stream.filesize
            stream.download(output_path=self.save_path)
            self.completed.emit(yt.title)
        except Exception as e:
            print(f"Error: {e}")

    def on_progress(self, stream, chunk, bytes_remaining):
        if not self._running:
            self.terminate()
        downloaded = self.total_size - bytes_remaining
        progress_percentage = int((downloaded / self.total_size) * 100)

        elapsed_time = time.time() - self.start_time
        speed = downloaded / elapsed_time if elapsed_time > 0 else 0
        self.progress.emit(progress_percentage)
        self.speed.emit(speed / 1024)  # Speed in KB/s

    def stop(self):
        self._running = False

class YouTubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Downloader")
        self.setGeometry(100, 100, 800, 600)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        
        # URL input
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Enter YouTube URL or Playlist URL")
        download_button = QPushButton("Download", self)
        download_button.clicked.connect(self.start_download)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(download_button)
        
        # Quality selection
        quality_group = QGroupBox("Select Quality")
        quality_layout = QHBoxLayout()
        self.best_quality = QRadioButton("Best")
        self.normal_quality = QRadioButton("Normal")
        self.custom_quality = QRadioButton("Custom")
        self.best_quality.setChecked(True)
        quality_layout.addWidget(self.best_quality)
        quality_layout.addWidget(self.normal_quality)
        quality_layout.addWidget(self.custom_quality)
        quality_group.setLayout(quality_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.speed_label = QLabel("Speed: 0 KB/s", self)
        
        # Table for downloads
        self.download_table = QTableWidget(0, 3, self)
        self.download_table.setHorizontalHeaderLabels(["Video", "Progress", "Speed"])
        self.download_table.horizontalHeader().setStretchLastSection(True)

        # Add widgets to main layout
        main_layout.addLayout(url_layout)
        main_layout.addWidget(quality_group)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.speed_label)
        main_layout.addWidget(self.download_table)

        # Container widget
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Input Error", "Please enter a valid YouTube URL or Playlist URL.")
            return

        save_path = QFileDialog.getExistingDirectory(self, "Select Save Folder")
        if not save_path:
            return

        quality = "Best" if self.best_quality.isChecked() else "Normal" if self.normal_quality.isChecked() else "Custom"

        if "playlist" in url:
            try:
                playlist = Playlist(url)
                for video_url in playlist.video_urls:
                    self.download_video(video_url, save_path, quality)
            except Exception as e:
                QMessageBox.critical(self, "Playlist Error", f"Failed to process playlist: {e}")
        else:
            self.download_video(url, save_path, quality)

    def download_video(self, url, save_path, quality):
        row_position = self.download_table.rowCount()
        self.download_table.insertRow(row_position)
        self.download_table.setItem(row_position, 0, QTableWidgetItem("Initializing..."))
        self.download_table.setItem(row_position, 1, QTableWidgetItem("0%"))
        self.download_table.setItem(row_position, 2, QTableWidgetItem("0 KB/s"))

        thread = DownloadThread(url, save_path, quality)
        thread.progress.connect(lambda progress: self.update_progress(row_position, progress))
        thread.speed.connect(lambda speed: self.update_speed(row_position, speed))
        thread.completed.connect(lambda title: self.mark_completed(row_position, title))
        thread.start()

    def update_progress(self, row, progress):
        self.download_table.setItem(row, 1, QTableWidgetItem(f"{progress}%"))
        self.progress_bar.setValue(progress)

    def update_speed(self, row, speed):
        self.download_table.setItem(row, 2, QTableWidgetItem(f"{speed:.2f} KB/s"))
        self.speed_label.setText(f"Speed: {speed:.2f} KB/s")

    def mark_completed(self, row, title):
        self.download_table.setItem(row, 0, QTableWidgetItem(title))
        self.download_table.setItem(row, 1, QTableWidgetItem("Completed"))
        self.download_table.setItem(row, 2, QTableWidgetItem(""))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    downloader = YouTubeDownloader()
    downloader.show()
    sys.exit(app.exec_())
