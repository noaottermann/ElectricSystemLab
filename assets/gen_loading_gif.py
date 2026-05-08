"""Génère un GIF de chargement animé pour le splash screen"""

from PIL import Image, ImageDraw
import os

def create_loading_gif():
    """Crée un GIF d'animation de chargement"""
    width, height = 400, 400
    num_frames = 12
    frames = []
    
    # Paramètres du design
    bg_color = (240, 240, 240)
    primary_color = (100, 150, 200)
    secondary_color = (200, 220, 240)
    text_color = (60, 60, 60)
    
    for frame_idx in range(num_frames):
        # Créer une nouvelle image
        img = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Dessiner un cercle de chargement
        center_x, center_y = width // 2, height // 2
        radius = 80
        
        # Cercle de fond (gris)
        draw.ellipse(
            [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
            outline=secondary_color,
            width=8
        )
        
        # Arc de chargement (couleur primaire)
        start_angle = (frame_idx / num_frames) * 360
        draw.arc(
            [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
            start=start_angle,
            end=start_angle + 90,
            fill=primary_color,
            width=8
        )
        
        # Texte "Chargement..."
        text = "Chargement"
        draw.text(
            (center_x, center_y + 120),
            text,
            fill=text_color,
            anchor="mm"
        )
        
        # Petits points animés
        num_dots = (frame_idx % 4) + 1
        dot_y = center_y + 150
        for i in range(num_dots):
            dot_x = center_x - 30 + (i * 20)
            draw.ellipse(
                [dot_x - 4, dot_y - 4, dot_x + 4, dot_y + 4],
                fill=primary_color
            )
        
        frames.append(img)
    
    # Sauvegarder le GIF
    output_path = os.path.join(os.path.dirname(__file__), 'loading.gif')
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=100,  # 100ms par frame
        loop=1  # Se joue une seule fois (pas de boucle)
    )
    
    print(f"GIF de chargement créé: {output_path}")

if __name__ == "__main__":
    create_loading_gif()
