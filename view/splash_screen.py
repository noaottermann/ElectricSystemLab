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
        self.setFixedSize(720, 450)
        
        # Track frames to detect when animation loops
        self.previous_frame = 0
        self.animation_finished = False
        
        # Configurer le GIF animé
        self.movie = QMovie(gif_path)
        self.movie.setScaledSize(QSize(720, 450))
        self.movie.frameChanged.connect(self._on_frame_changed)
        self.movie.start()

    def _on_frame_changed(self):
        """Met à jour le pixmap du splash screen avec la frame actuelle du GIF"""
        current_frame = self.movie.currentFrameNumber()
        frame_pixmap = self.movie.currentPixmap()
        self.setPixmap(frame_pixmap)
        
        # Detect when animation loops (frame number goes back to start)
        if current_frame < self.previous_frame and not self.animation_finished:
            # Animation has looped, close the splash screen
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
