import pygame
import math
from config import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_CAR, COLOR_RAY, COLOR_HIT, COLOR_WALL, COLOR_BG, COLOR_GOLD
from brain import NeuralNetwork

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
        self.is_human = False  # Bandera para identificar si este carro es controlado por el jugador

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
        self.next_checkpoint_id = 0     # Índice del próximo checkpoint a alcanzar

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

        # Si es el líder de la generación actual, lo pintamos con un borde cian
        if is_best:
            pygame.draw.rect(screen, COLOR_RAY, rect.inflate(4, 4), 2, 4)

        screen.blit(rotated_sprite, rect.topleft)

    def update(self, screen, checkpoints):
        if not self.is_alive:
            return False

        MAX_SPEED = 8.0  # Tope de velocidad
        MIN_SPEED = 2.0  # Velocidad mínima para que NUNCA se queden completamente parados

        # 1. Obtener lecturas de radares y normalizarlas (0.0 a 1.0)
        self.radars.clear()
        angles = [-90, -45, 0, 45, 90]
        for i, phi in enumerate(angles):
            dist = self.cast_rays(phi, screen)
            self.sensor_inputs[i] = dist / 250.0    # Normalizado basado en rango máximo

        # --- SEPARACIÓN DE CONTROL: IA VS HUMANO ---
        if self.is_human:
            # CONTROL MANUAL POR TECLADO
            self.speed = 3 # Velocidad constante para el modo humano, para que sea más fácil de controlar

            keys = pygame.key.get_pressed()

            # Giro manual
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.angle -= 4.5
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.angle += 4.5
        else:
            # CONTROL POR RED NEURONAL
            ai_decision = self.brain.predict(self.sensor_inputs)

            # --- FÍSICA PROGRESIVA DE VELOCIDAD (Aceleración y Frenado) ---
            # ai_decision[0] ahora controlará de forma gradual el motor.
            # Si es mayor a 0: Acelera. Si es menor o igual a 0: Desacelera/Frena.
            if ai_decision[0] > 0:
                self.speed += 0.2  # Incrementa la velocidad poco a poco (Aceleración)
            else:
                self.speed -= 0.3  # Disminuye la velocidad más rápido de lo que acelera (Frenado)

            if self.speed > MAX_SPEED: self.speed = MAX_SPEED
            if self.speed < MIN_SPEED: self.speed = MIN_SPEED

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

        # Al multiplicar la distancia por la velocidad actual, un auto que cruza
        # las rectas a máxima velocidad ganará muchísimo más fitness que uno lento.
        self.fitness = self.distance_traveled * (1.0 + (self.speed / MAX_SPEED))

        # Validaciones de Checkpoints y Colisiones
        meta_alcanzada = self.check_checkpoints(checkpoints)
        self.check_collision(screen)

        # Penalizar autos que se queden atascados dando vueltas sin avanzar de checkpoint
        if self.time_alive > 300 and self.fitness < 200:
            self.is_alive = False

        return meta_alcanzada

    def check_checkpoints(self, checkpoints):
        # Tomamos las coordenadas del checkpoint que le toca cruzar al vehículo
        target_cp = checkpoints[self.next_checkpoint_id]
        cp_x, cp_y = target_cp

        # Calculamos la distancia euclidiana entre el centro del carro y el centro del checkpoint
        distance_to_cp = math.sqrt((self.x - cp_x)**2 + (self.y - cp_y)**2)

        # Si la distancia es menor a 90 píxeles (el radio de nuestra calle), significa que lo cruzó
        if distance_to_cp < 90:
            self.fitness += 800.0   # Recompensa por cruzar el checkpoint, más grande que cualquier otra métrica acumulada

            # Guardamos si este checkpoint era el último antes de reiniciar el ciclo
            cruzo_meta = (self.next_checkpoint_id == len(checkpoints) - 1)

            # Avanzamos al siguiente checkpoint de la lista de forma cíclica
            self.next_checkpoint_id = (self.next_checkpoint_id + 1) % len(checkpoints)
            self.time_alive = 0 # Resetear temporizador de estancamiento

            if cruzo_meta:
                print(f"¡Vuelta completa! Fitness actual: {int(self.fitness)} pts")
                return True # Resetear temporizador de estancamiento

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

                is_wall = (pixel_color[0] == COLOR_WALL[0] and pixel_color[1] == COLOR_WALL[1] and pixel_color[2] == COLOR_WALL[2])
                is_bg = (pixel_color[0] == COLOR_BG[0] and pixel_color[1] == COLOR_BG[1] and pixel_color[2] == COLOR_BG[2])

                # Si CUALQUIERA de las 4 esquinas toca el muro blanco (COLOR_WALL)
                # o el fondo exterior (COLOR_BG), el carro se elimina ipso facto.
                if is_wall or is_bg:
                    self.is_alive = False
                    self.fitness *= 0.40    # Mantener castigo estricto para la IA
                    self.radars.clear()     # Limpiar sensores para que no floten en el aire
                    break
            else:
                # Si el carro se sale completamente de la pantalla, también muere
                self.is_alive = False
                self.fitness *= 0.40    # Mantener castigo estricto para la IA
                self.radars.clear()     # Limpiar sensores para que no floten en el aire
                break

    # Lógica de Raycasting: (sensores de distancia)
    def cast_rays(self, degree_offset, screen):
        length = 0

        # El ángulo real del rayo es el ángulo del carro más la desviación del sensor
        target_angle = self.angle + degree_offset

        # Calcular el punto de origen del rayo (el centro del carro)
        start_x = self.x
        start_y = self.y

        # Extender el rayo píxel por píxel hasta un máximo de 250 píxeles de alcance
        while length < 250:
            # Calcular la coordenada (X, Y) actual de la punta del rayo
            check_x = int(start_x + math.cos(math.radians(target_angle)) * length)
            check_y = int(start_y + math.sin(math.radians(target_angle)) * length)

            # Validar que el rayo no se salga de los bordes de la ventana del juego
            if 0 <= check_x < SCREEN_WIDTH and 0 <= check_y < SCREEN_HEIGHT:
                # Leer el color del píxel en esa coordenada
                pixel_color = screen.get_at((check_x, check_y))
                is_wall = (pixel_color[0] == COLOR_WALL[0] and pixel_color[1] == COLOR_WALL[1] and pixel_color[2] == COLOR_WALL[2])
                is_bg = (pixel_color[0] == COLOR_BG[0] and pixel_color[1] == COLOR_BG[1] and pixel_color[2] == COLOR_BG[2])

                # El rayo detecta impacto si choca con el muro blanco (COLOR_WALL)
                if is_wall or is_bg:
                    break
            else:
                break
            length += 1 # Avanzar de 1 en 1 píxeles para optimizar precisión (conforme al rendimiento, se podría aumentar a 2 o 3 píxeles por iteración)

        # Guardar la posición exacta del impacto y la distancia calculada
        self.radars.append(((check_x, check_y), length))
        return length
