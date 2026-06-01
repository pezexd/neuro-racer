import pygame
import math
import sys
import pickle
import os
import random

# TODO: Sonidos de colision
# TODO: Sonido de META (checkpoint final)
# TODO: Evento de colision (explosion)

# Inicialización de Pygame
pygame.init()
pygame.mixer.init()
pygame.font.init()
FONT_UI = pygame.font.SysFont("Consolas", 20)
FONT_MENU = pygame.font.SysFont("Consolas", 24)
FONT_TITLE = pygame.font.SysFont("Consolas", 18, bold=True)

# Constantes de Pantalla
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
COLOR_CHECKPOINT = (0, 255, 150) # Verde neón para visualizar los checkpoints
COLOR_GOLD = (255, 215, 0)

# IA
POPOULATION_SIZE = 15  # Población de agentes concurrentes

# Pistas
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

class NeuralNetwork:
    """Red Neuronal simple (5 Entradas de Sensores -> 2 Salidas de Control)"""
    def __init__(self, weights=None):
         # 5 entradas (radares) y 2 salidas (Acelerar/Frenar, Girar Izq/Der)
        if weights is None:
            # Inicialización aleatoria si es la primera generación
            self.weights = [[random.uniform(-1.0, 1.0) for _ in range(2)] for _ in range(5)]
        else:
            self.weights = weights

    def predict(self, inputs):
        # Multiplicación matricial básica para obtener las salidas (Feedforward)
        outputs = [0.0, 0.0]
        for j in range(2):
            for i in range(5):
                outputs[j] += inputs[i] * self.weights[i][j]
            # Función de activación básica (Tangente hiperbólica aproximada)
            outputs[j] = math.tanh(outputs[j])
        return outputs

    def mutate(self):
        """Aplica una mutación para romper bucles de comportamiento y fomentar la exploración de nuevas estrategias"""
        new_weights = []
        for i in range(5):
            row = []
            for j in range(2):
                w = self.weights[i][j]
                if random.random() < 0.3:           # Porcentaje de mutación (30% de los pesos se mutan)
                    w += random.uniform(-0.3, 0.3)  # Mutación suave para ajustes finos
                row.append(w)
            new_weights.append(row)
        return NeuralNetwork(new_weights)

class Car:
    def __init__(self, brain=None, spawn_info=None):
        if spawn_info:
            self.x = spawn_info["x"]
            self.y = spawn_info["y"]
            self.angle = spawn_info["angle"]
        else:
            self.x = 520
            self.y = 650
            self.angle = 180

        self.speed = 0
        # Dimensiones del vehículo
        self.width = 64
        self.height = 29

        # Estado del agente
        self.is_alive = True
        self.vuelta_completada = False

        # Lista para almacenar los resultados de los sensores (distancias)
        self.radars = []
        self.sensor_inputs = [0.0, 0.0, 0.0, 0.0, 0.0]

        # Métricas de Fitness
        self.distance_traveled = 0      # Distancia acumulada en píxeles
        self.fitness = 0.0              # Puntuación evolutiva del agente
        self.time_alive = 0             # Contador de frames para evaluar rendimiento
        self.next_checkpoint_id = 0     # Seguimiento de checkpoints

        # Cerebro asignado (Red Neuronal)
        self.brain = brain if brain is not None else NeuralNetwork()

        # Cargar sprite
        try:
            self.sprite = pygame.image.load("car.png").convert_alpha()
            self.sprite = pygame.transform.scale(self.sprite, (self.width, self.height))
        except (pygame.error, FileNotFoundError):
            print("No se encontró 'car.png', usando rectángulo genérico.")
            self.sprite = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            self.sprite.fill(COLOR_CAR)

    def draw(self, screen, is_best=False):
        if not self.is_alive: return

        # Solo mostrar los sensores en pantalla si es el mejor vehículo (RAY CAST)
        if is_best:
            for radar in self.radars:
                position, dist = radar
            # Dibujar línea desde el centro del carro hasta el punto de colisión del rayo
                pygame.draw.line(screen, COLOR_RAY, (int(self.x), int(self.y)), position, 2)
                pygame.draw.circle(screen, COLOR_HIT, position, 4)

        # Dibujar el carro con rotación basada en su ángulo actual
        rotated_sprite = pygame.transform.rotate(self.sprite, -self.angle)
        rect = rotated_sprite.get_rect(center=(self.x, self.y))

        # Si es el líder de la generación actual, lo pintamos con un borde cian brillante
        if is_best:
            pygame.draw.rect(screen, COLOR_RAY, rect.inflate(4, 4), 2, 4)

        screen.blit(rotated_sprite, rect.topleft)

    def update(self, screen, checkpoints):
        if not self.is_alive: return

        # 1. Obtener lecturas de radares y normalizarlas (0.0 a 1.0)
        self.radars.clear()
        angles = [-90, -45, 0, 45, 90]
        for i, phi in enumerate(angles):
            dist = self.cast_rays(phi, screen)
            self.sensor_inputs[i] = dist / 250.0  # Normalizado basado en rango máximo

        # 2. Pensar: La Red Neuronal toma las decisiones de conducción
        ai_decision = self.brain.predict(self.sensor_inputs)

        if ai_decision[0] > 0:
            self.speed = 4.0
        else:
            self.speed = 1.5

        if ai_decision[1] > 0.2:
            self.angle += 4.5
        elif ai_decision[1] < -0.2:
            self.angle -= 4.5

        # 3. Aplicar física de desplazamiento
        self.x += math.cos(math.radians(self.angle)) * self.speed
        self.y += math.sin(math.radians(self.angle)) * self.speed

        # Acumular la distancia recorrida sin haber chocado
        self.distance_traveled += self.speed
        self.time_alive += 1

        # Calcular fitness base temporalmente como la distancia recorrida más un pequeño bono por tiempo vivo
        self.fitness = self.distance_traveled + (self.speed * 2)

        # Validaciones de Checkpoints y Colisiones
        vuelta_completa = self.check_checkpoints(checkpoints)
        self.check_collision(screen)

        # Penalizar autos que se queden atascados dando vueltas sin avanzar de checkpoint
        if self.time_alive > 300 and self.fitness < 200:
            self.is_alive = False

        return vuelta_completa

    def check_checkpoints(self, checkpoints):
        # Tomamos las coordenadas del checkpoint que le toca cruzar al vehículo
        target_cp = checkpoints[self.next_checkpoint_id]
        cp_x, cp_y = target_cp

        # Calculamos la distancia euclidiana entre el centro del carro y el centro del checkpoint
        distance_to_cp = math.sqrt((self.x - cp_x)**2 + (self.y - cp_y)**2)

        # Si la distancia es menor a 55 píxeles (el radio de nuestra calle), significa que lo cruzó
        if distance_to_cp < 55:
            self.fitness += 800.0  # Recompensa por cruzar el checkpoint, más grande que cualquier otra métrica acumulada

            # Guardamos si este checkpoint era el último antes de reiniciar el ciclo
            cruzo_meta = (self.next_checkpoint_id == len(checkpoints) - 1)

            # Avanzamos al siguiente checkpoint de la lista de forma cíclica
            self.next_checkpoint_id = (self.next_checkpoint_id + 1) % len(checkpoints)
            self.time_alive = 0     # Resetear temporizador de estancamiento

            if cruzo_meta:
                print(f"¡Vuelta completa! Fitness actual: {int(self.fitness)} pts")
                return True # Avisa que completó la vuelta completa por la meta

        return False

    def check_collision(self, screen):
        # Calculamos los vectores de dirección basados en el ángulo actual
        cos_a = math.cos(math.radians(self.angle))
        sin_a = math.sin(math.radians(self.angle))

        # Mitad del largo y ancho del vehículo para ubicar las esquinas
        half_w = self.width / 2
        half_h = self.height / 2

        # --- HITBOX DE 4 PUNTOS (Esquinas del vehículo) ---
        # Esto evita que el carro se "salte" el muro blanco a altas velocidades
        corners = [
            # Esquina Delantera Derecha
            (int(self.x + cos_a * half_w - sin_a * half_h), int(self.y + sin_a * half_w + cos_a * half_h)),
            # Esquina Delantera Izquierda
            (int(self.x + cos_a * half_w + sin_a * half_h), int(self.y + sin_a * half_w - cos_a * half_h)),
            # Esquina Trasera Derecha
            (int(self.x - cos_a * half_w - sin_a * half_h), int(self.y - sin_a * half_w + cos_a * half_h)),
            # Esquina Trasera Izquierda
            (int(self.x - cos_a * half_w + sin_a * half_h), int(self.y - sin_a * half_w - cos_a * half_h))
        ]

        for cx, cy in corners:
            if 0 <= cx < SCREEN_WIDTH and 0 <= cy < SCREEN_HEIGHT:
                pixel_color = screen.get_at((cx, cy))

                # Si CUALQUIERA de las 4 esquinas toca el muro blanco (COLOR_WALL)
                # o el fondo exterior (COLOR_BG), el carro se elimina ipso facto.
                if pixel_color[0] == COLOR_WALL[0] or pixel_color[0] == COLOR_BG[0]:
                    self.is_alive = False
                    self.fitness *= 0.40  # Mantener castigo estricto para la IA
                    self.radars.clear()   # Limpiar sensores para que no floten en el aire
                    break
            else:
                # Si el carro se sale completamente de la pantalla, también muere
                self.is_alive = False
                self.fitness *= 0.40  # Castigo radical por salirse de la pantalla
                self.radars.clear()
                break
        pass

    # Lógica de Raycasting: (sensores de distancia)
    def cast_rays(self, degree_offset, screen):
        length = 0

        # El ángulo real del rayo es el ángulo del carro más la desviación del sensor
        target_angle = self.angle + degree_offset

        # Calcular el punto de origen del rayo (el centro del carro)
        start_x = self.x
        start_y = self.y

        # Extender el rayo píxel por píxel hasta un máximo de 300 píxeles de alcance
        while length < 250:
            # Calcular la coordenada (X, Y) actual de la punta del rayo
            check_x = int(start_x + math.cos(math.radians(target_angle)) * length)
            check_y = int(start_y + math.sin(math.radians(target_angle)) * length)

            # Validar que el rayo no se salga de los bordes de la ventana del juego
            if 0 <= check_x < SCREEN_WIDTH and 0 <= check_y < SCREEN_HEIGHT:
                # Leer el color del píxel en esa coordenada
                pixel_color = screen.get_at((check_x, check_y))

                # El rayo detecta impacto si choca con el muro blanco (COLOR_WALL)
                if pixel_color[0] == COLOR_WALL[0] and pixel_color[1] == COLOR_WALL[1] and pixel_color[2] == COLOR_WALL[2]:
                    break
            else:
                break
            length += 1 # Avanzar de 1 en 1 píxeles para optimizar precisión (conforme al rendimiento, se podría aumentar a 2 o 3 píxeles por iteración)

        # Guardar la posición exacta del impacto y la distancia calculada
        self.radars.append(((check_x, check_y), length))
        return length

class Simulation:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Neuro-Racer - Simulación de IA")
        self.clock = pygame.time.Clock()

        try:
            self.sonido_bonus = pygame.mixer.Sound("bonus.mp3")
            self.sonido_bonus.set_volume(0.4) # Volumen entre 0.0 y 1.0 (40% en este caso)
        except (pygame.error, FileNotFoundError):
            print("Advertencia: No se pudo encontrar el archivo bonus.mp3. La simulación correrá sin sonido.")
            self.sonido_bonus = None

        # Control de Estados
        self.estado = "MENU_PRINCIPAL"
        self.mostrar_instrucciones = False

        # Parámetros de control de la simulación
        self.generation = 1
        self.best_historical_fitness = 0.0
        self.best_brain_historical = None
        self.simulation_speed = 60              # Controlar velocidad del juego (FPS)
        self.is_paused = False                  # Estado de pausa

        # SELECCIÓN DE PISTA
        self.pista_activa = TRACK_CHICANA
        self.track_points = self.pista_activa["points"]
        self.population = []

        for _ in range(POPOULATION_SIZE):
            # Si tenemos un cerebro guardado del pasado, lo usamos de base para toda la población inicial
            brain = self.best_brain_historical.mutate() if self.best_brain_historical else None
            self.population.append(Car(brain, spawn_info=self.pista_activa["spawn"]))

    def cargar_modelo(self):
        if os.path.exists("mejor_modelo.pickle"):
            try:
                with open("mejor_modelo.pickle", "rb") as f:
                    datos = pickle.load(f)

                if isinstance(datos, dict):
                    self.best_brain_historical = datos["brain"]
                    self.best_historical_fitness = datos["fitness"]
                else:
                    self.best_brain_historical = datos
                    self.best_historical_fitness = 0.0

                print(f"¡Modelo cargado con éxito! Récord actual: {int(self.best_historical_fitness)} pts")
                return True
            except Exception:
                print("No se pudo leer el archivo de guardado, iniciando nueva población.")
                return False
        return False

    def iniciar_simulacion(self, usar_guardado):
        self.generation = 1
        if usar_guardado:
            self.cargar_modelo()
        else:
            self.best_brain_historical = None
            self.best_historical_fitness = 0.0

        self.track_points = self.pista_activa["points"]
        self.population = []

        for _ in range(POPOULATION_SIZE):
            # Si tenemos un cerebro guardado del pasado, lo usamos de base para toda la población inicial
            brain = self.best_brain_historical.mutate() if self.best_brain_historical else None
            self.population.append(Car(brain, spawn_info=self.pista_activa["spawn"]))

        self.estado = "SIMULACION"

    def draw_menu(self):
        self.screen.fill(COLOR_BG)

        # Título
        lbl_title = FONT_TITLE.render("NEURO-RACER", True, COLOR_RAY)
        self.screen.blit(lbl_title, (SCREEN_WIDTH//2 - lbl_title.get_width()//2, 80))

        existe_modelo = os.path.exists("mejor_modelo.pickle")

        # Opciones
        opciones = [
            "[1] Iniciar Nueva Población (Desde cero)",
            "[2] Cargar Mejor Modelo Guardado" if existe_modelo else "[2] Cargar Modelo (No existe archivo)",
            "[3] Borrar Modelo Guardado" if existe_modelo else "[3] Borrar Modelo (No existe archivo)",
            "[4] Instrucciones del Sistema",
            "[ESC] Salir"
        ]

        for i, opcion in enumerate(opciones):
            color = COLOR_TEXT
            if i == 1 or i == 2:
                if not existe_modelo: color = (100, 100, 110) # Gris oscuro si está deshabilitado

            lbl_opc = FONT_MENU.render(opcion, True, color)
            self.screen.blit(lbl_opc, (200, 220 + i * 50))

        # Cuadro de instrucciones flotante
        if self.mostrar_instrucciones:
            pygame.draw.rect(self.screen, (10, 10, 15), (150, 480, 900, 240), 0, 12)
            pygame.draw.rect(self.screen, COLOR_RAY, (150, 480, 900, 240), 2, 12)

            instrucciones = [
                "• Los vehículos se controlan de manera autónoma usando Redes Neuronales Artificiales.",
                "• El algoritmo genético selecciona los mejores ejemplares mediante Elitismo Duro.",
                "• Controles en simulación:",
                "  [F] Alternar velocidad de entrenamiento (60 FPS / 300 FPS rápido).",
                "  [P] Pausar o reanudar la carrera en cualquier momento.",
                "  [G] Guardar el genoma del líder actual en el almacenamiento local.",
                "  [ESC] Regresar al menú de inicio."
            ]
            for i, inst in enumerate(instrucciones):
                lbl_inst = FONT_UI.render(inst, True, (200, 220, 240))
                self.screen.blit(lbl_inst, (180, 500 + i * 28))

    def draw_menu_pistas(self):
        self.screen.fill(COLOR_BG)
        lbl_title = FONT_TITLE.render("SELECCIONA UNA PISTA", True, COLOR_GOLD)
        self.screen.blit(lbl_title, (SCREEN_WIDTH//2 - lbl_title.get_width()//2, 150))

        pistas = [
            "[1] " + TRACK_OVALO["nombre"],
            "[2] " + TRACK_S["nombre"],
            "[3] " + TRACK_CHICANA["nombre"],
            "[ESC] Volver atrás"
        ]

        for i, pista in enumerate(pistas):
            lbl_p = FONT_MENU.render(pista, True, COLOR_TEXT)
            self.screen.blit(lbl_p, (350, 300 + i * 60))

    def draw_track(self, leader_car):
        # Capa de asfalto
        for point in self.track_points:
            pygame.draw.circle(self.screen, COLOR_TRACK, point, 50)
        pygame.draw.lines(self.screen, COLOR_TRACK, False, self.track_points, 100)

        # Capa de muros blancos
        for point in self.track_points:
            pygame.draw.circle(self.screen, COLOR_WALL, point, 52)
        pygame.draw.lines(self.screen, COLOR_WALL, False, self.track_points, 104)

        # Capa interna de limpieza del asfalto
        for point in self.track_points:
            pygame.draw.circle(self.screen, COLOR_TRACK, point, 48)
        pygame.draw.lines(self.screen, COLOR_TRACK, False, self.track_points, 96)

        # Dibujamos los puntos de control en la pista
        for i, point in enumerate(self.track_points):
            # Pintamos de verde neón el checkpoint que el carro DEBE buscar ahora mismo
            if i == leader_car.next_checkpoint_id:
                pygame.draw.circle(self.screen, COLOR_CHECKPOINT, point, 8)
            else:
                pygame.draw.circle(self.screen, (100, 100, 120), point, 5)

        # Línea de Meta Dinámica y Adaptativa al Ángulo del Spawn
        spawn_x = self.pista_activa["spawn"]["x"]
        spawn_y = self.pista_activa["spawn"]["y"]
        spawn_angle = self.pista_activa["spawn"]["angle"]

        # Si el carro empieza moviéndose de forma horizontal (Óvalo y pista S)
        if spawn_angle in [0, 180, -180]:
            p1 = (int(spawn_x), int(spawn_y - 50))
            p2 = (int(spawn_x), int(spawn_y + 50))
        # Si el carro empieza moviéndose de forma vertical (Chicana)
        else:
            p1 = (int(spawn_x - 50), int(spawn_y))
            p2 = (int(spawn_x + 50), int(spawn_y))

        # Dibujar la línea dorada exactamente cruzando el punto de salida
        pygame.draw.line(self.screen, COLOR_GOLD, p1, p2, 5)

    def next_generation(self):
        """Aplica la función de Selección Artificial para avanzar la población"""
        # Ordenar por mejores puntuaciones (Función de Selección)
        self.population.sort(key=lambda car: car.fitness, reverse=True)

        best_car = self.population[0]
        if best_car.fitness > self.best_historical_fitness:
            self.best_historical_fitness = best_car.fitness
            self.best_brain_historical = best_car.brain

        print(f"Fin Gen {self.generation}. Mejor Fitness de la ronda: {int(best_car.fitness)}")

        # Cruce y Selección de Elite: Tomar el cerebro del mejor carro y clonarlo con mutaciones
        new_population = []
        new_population.append(Car(best_car.brain, spawn_info=self.pista_activa["spawn"])) # Pasar al campeón intacto (Elitismo)

        # Rellenamos el resto de la población mezclando clones mutados y mutaciones radicales
        for i in range(POPOULATION_SIZE - 1):
            if i < 10:
                # Clones del campeón con mutación para ajustar detalles
                mutated_brain = best_car.brain.mutate()
                new_population.append(Car(mutated_brain, spawn_info=self.pista_activa["spawn"]))
            else:
                # ANTIESTANCAMIENTO: Inyectamos 4 carros con cerebros completamente
                # aleatorios para meter nuevas ideas y trayectorias frescas a la piscina genética.
                new_population.append(Car(None, spawn_info=self.pista_activa["spawn"]))

        self.population = new_population
        self.generation += 1

    def save_current_best(self):
        """Almacena el genoma entrenado localmente en un archivo .pickle para futuras sesiones"""
        if self.best_brain_historical:
            try:
                # Empaquetamos el cerebro y el récord histórico real en una sola estructura
                datos_a_guardar = {
                    "brain": self.best_brain_historical,
                    "fitness": self.best_historical_fitness
                }

                with open("mejor_modelo.pickle", "wb") as f:
                    pickle.dump(datos_a_guardar, f)
                print(f"¡Progreso guardado! Récord asegurado en: {int(self.best_historical_fitness)} pts")
            except Exception as e:
                print(f"Error al escribir en el disco local: {e}")

    def draw_ui(self, best_car):
        # Renderizar datos en tiempo real en la pantalla
        text_gen = f"Generación Actual: {self.generation}"
        text_hist = f"Récord Histórico: {int(self.best_historical_fitness)} pts"

        alive_count = sum(1 for c in self.population if c.is_alive)
        text_alive = f"Agentes Vivos: {alive_count} / {POPOULATION_SIZE}"

        text_pista = f"Pista: {self.pista_activa['nombre']}"

        # Mensajes informativos de controles de simulación
        mode_str = f"VEL: {self.simulation_speed} FPS (F) | PAUSA: {self.is_paused} (P) | MENU: (ESC)"

        surface_gen = FONT_UI.render(text_gen, True, COLOR_TEXT)
        surface_hist = FONT_UI.render(text_hist, True, (255, 215, 0))
        surface_alive = FONT_UI.render(text_alive, True, COLOR_TEXT)
        surface_pista = FONT_UI.render(text_pista, True, COLOR_RAY)

        # Dibujar un pequeño panel negro transparente de fondo para el texto
        pygame.draw.rect(self.screen, (5, 5, 10), (750, 20, 430, 130), 0, 8)
        pygame.draw.rect(self.screen, COLOR_TRACK, (750, 20, 430, 130), 2, 8)

        self.screen.blit(surface_gen, (760, 30))
        self.screen.blit(surface_hist, (760, 60))
        self.screen.blit(surface_alive, (760, 90))
        self.screen.blit(surface_pista, (760, 120))

        surface_mode = FONT_UI.render(mode_str, True, (255, 150, 0))
        self.screen.blit(surface_mode, (10, 10))

    def run(self):
        running = True
        while running:
            # Control dinámico de velocidad del ciclo principal
            self.clock.tick(self.simulation_speed if self.estado == "SIMULACION" else 60)

            # Gestión de Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

                if event.type == pygame.KEYDOWN:
                    if self.estado == "MENU_PRINCIPAL":
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key == pygame.K_1:
                            self.usar_guardado_temp = False
                            self.estado = "MENU_PISTAS"
                        elif event.key == pygame.K_2 and os.path.exists("mejor_modelo.pickle"):
                            self.usar_guardado_temp = True
                            self.estado = "MENU_PISTAS"
                        elif event.key == pygame.K_3 and os.path.exists("mejor_modelo.pickle"):
                            try:
                                os.remove("mejor_modelo.pickle")
                                print("Archivo de guardado eliminado de la memoria local.")
                            except Exception: pass
                        elif event.key == pygame.K_4:
                            self.mostrar_instrucciones = not self.mostrar_instrucciones

                    elif self.estado == "MENU_PISTAS":
                        if event.key == pygame.K_ESCAPE:
                            self.estado = "MENU_PRINCIPAL"
                        elif event.key == pygame.K_1:
                            self.pista_activa = TRACK_OVALO
                            self.iniciar_simulacion(self.usar_guardado_temp)
                        elif event.key == pygame.K_2:
                            self.pista_activa = TRACK_S
                            self.iniciar_simulacion(self.usar_guardado_temp)
                        elif event.key == pygame.K_3:
                            self.pista_activa = TRACK_CHICANA
                            self.iniciar_simulacion(self.usar_guardado_temp)

                    elif self.estado == "SIMULACION":
                        if event.key == pygame.K_ESCAPE:
                            self.estado = "MENU_PRINCIPAL"
                        elif event.key == pygame.K_p:
                            self.is_paused = not self.is_paused
                        elif event.key == pygame.K_g:
                            self.save_current_best()
                        elif event.key == pygame.K_f:
                            self.simulation_speed = 300 if self.simulation_speed == 60 else 60

            if not running: break

            # Ejecución lógicas de renderizado según estado actual
            if self.estado == "MENU_PRINCIPAL":
                self.draw_menu()
            elif self.estado == "MENU_PISTAS":
                self.draw_menu_pistas()
            elif self.estado == "SIMULACION":
                if not self.is_paused:
                    any_alive = False
                    for car in self.population:
                        # Al actualizar, revisamos si completó una vuelta
                        vuelta_completa = car.update(self.screen, self.track_points)

                        if car.is_alive:
                            any_alive = True

                        if vuelta_completa:
                            print(f"¡Vuelta completa por la meta en SIMULACION! Fitness actual: {int(car.fitness)} pts")
                            # Si cruzó la meta y el sonido se cargó correctamente, se reproduce
                            self.sonido_bonus.play()

                    if not any_alive:
                        self.next_generation()

                # Pintar el fondo antes de dibujar cualquier cosa (FONDO)
                self.screen.fill(COLOR_BG)

                # Encontrar al líder actual (el que tenga mayor fitness) para renderizar sus sensores
                current_leader = max(self.population, key=lambda c: c.fitness)

                # Renderizar pista y muros vectoriales
                self.draw_track(current_leader)

                for car in self.population:
                    is_leader = (car == current_leader and car.is_alive)
                    car.draw(self.screen, is_best=is_leader)

                # Renderizar el panel de control
                self.draw_ui(current_leader)

            pygame.display.flip()

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    sim = Simulation()
    sim.run()
