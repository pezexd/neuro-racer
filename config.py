# Dimensiones de Pantalla
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# Colores (RGB)
COLOR_BG = (15, 15, 20)          # Fondo exterior oscuro (Obstáculo/Muerte)
COLOR_TRACK = (30, 30, 40)       # Asfalto seguro (Gris oscuro)
COLOR_WALL = (255, 255, 255)     # Muros de contención (Blanco puro - Detectable)
COLOR_RAY = (0, 255, 255)        # Cian para los sensores activos
COLOR_HIT = (255, 0, 100)        # Rosa para el punto de impacto
COLOR_CAR = (255, 0, 0)          # Rojo para el vehículo (en caso de no cargar sprite)
COLOR_TEXT = (240, 240, 250)     # Blanco para textos e información
COLOR_CHECKPOINT = (0, 255, 0)   # Verde neón para visualizar los checkpoints
COLOR_GOLD = (255, 215, 0)       # Dorado para el mejor tiempo (destacado) / Meta

# Algoritmo Genético
POPOULATION_SIZE = 15            # Población de agentes concurrentes

# Base de Datos de Pistas
TRACK_OVALO = {
    "nombre": "Óvalo de Alta Velocidad",
    "spawn": {"x": 480, "y": 650, "angle": 180},
    "points": [
        (300, 650), (150, 500), (150, 300), (300, 150), (600, 150),
        (900, 150), (1050, 300), (1050, 500), (900, 650), (600, 650), (300, 650)
    ]
}

TRACK_S = {
    "nombre": "Circuito en S",
    "spawn": {"x": 470, "y": 650, "angle": 180},
    "points": [
        (450, 650), (200, 650), (150, 550), (150, 250), (250, 150),
        (550, 150), (600, 250), (600, 350), (750, 450), (1050, 450),
        (1100, 550), (1100, 650), (900, 700), (650, 550), (450, 650)
    ]
}

TRACK_CHICANA = {
    "nombre": "El Sacacorchos (Chicana)",
    "spawn": {"x": 200, "y": 400, "angle": -90},
    "points": [
        (200, 400), (200, 150), (500, 150), (500, 350),
        (700, 450), (700, 200), (1000, 200), (1000, 650),
        (500, 650), (200, 550), (200, 400)
    ]
}
