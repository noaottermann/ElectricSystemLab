from PyQt5.QtWidgets import QSplashScreen, QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QPixmap, QMovie
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from utils.assets import get_asset_path


class LoadingSplashScreen(QSplashScreen):
    """Écran de démarrage avec animation GIF de chargement"""
    
    splash_finished = pyqtSignal()

    def __init__(self, duration_ms: int = 3000):
        """Initialise le splash screen"""
        gif_path = str(get_asset_path("loading.gif"))
        
        # Créer un pixmap initial
        pixmap = QPixmap(gif_path)
        
        super().__init__(pixmap)
        
        # Configurations
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.FramelessWindowHint)
        
        # Taille
        self.setFixedSize(720, 450)
        
        # Variables d'animation
        self.previous_frame = 0
        self.animation_finished = False
        
        # Configurations GIF animé
        self.movie = QMovie(gif_path)
        self.movie.setScaledSize(QSize(720, 450))
        self.movie.frameChanged.connect(self._on_frame_changed)
        self.movie.start()

    def _on_frame_changed(self):
        """Met à jour le pixmap du splash screen avec la frame actuelle du GIF"""
        current_frame = self.movie.currentFrameNumber()
        frame_pixmap = self.movie.currentPixmap()
        self.setPixmap(frame_pixmap)
        # Animation a fait une boucle
        if current_frame < self.previous_frame and not self.animation_finished:
            # Stopper
            self.animation_finished = True
            self._close_splash()
        self.previous_frame = current_frame

    def _close_splash(self):
        """Ferme le splash screen"""
        self.movie.stop()
        self.splash_finished.emit()
        self.close()

    def closeEvent(self, event):
        """Arrête l'animation avant de fermer"""
        self.movie.stop()
        self.splash_finished.emit()
        super().closeEvent(event)
