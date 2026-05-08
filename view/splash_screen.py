"""Splash screen avec animation de chargement"""

from PyQt5.QtWidgets import QSplashScreen, QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QPixmap, QMovie
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from utils.assets import get_asset_path


class LoadingSplashScreen(QSplashScreen):
    """Écran de démarrage avec animation GIF de chargement"""
    
    splash_finished = pyqtSignal()

    def __init__(self, duration_ms: int = 3000):
        """
        Initialise le splash screen
        
        Args:
            duration_ms: Durée d'affichage du splash screen en millisecondes (non utilisée, fermeture au fin du GIF)
        """
        # Charger le GIF
        gif_path = str(get_asset_path("loading.gif"))
        
        # Créer un pixmap initial (première frame du GIF)
        pixmap = QPixmap(gif_path)
        
        super().__init__(pixmap)
        
        # Configurer la fenêtre
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.FramelessWindowHint)
        
        # Définir une taille pour la fenêtre du splash screen
        self.setFixedSize(400, 400)
        
        # Configurer le GIF animé
        self.movie = QMovie(gif_path)
        self.movie.setScaledSize(QSize(400, 400))
        self.movie.frameChanged.connect(self._on_frame_changed)
        self.movie.finished.connect(self._close_splash)
        self.movie.start()

    def _on_frame_changed(self):
        """Met à jour le pixmap du splash screen avec la frame actuelle du GIF"""
        frame_pixmap = self.movie.currentPixmap()
        self.setPixmap(frame_pixmap)

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
