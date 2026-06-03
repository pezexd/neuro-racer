import pygame
import sys
import os
import pickle
import math
from config import *
from car import Car

FONT_UI = None
FONT_MENU = None
FONT_TITLE = None
FONT_SPLASH = None

class Simulation:
    def __init__(self):
        global FONT_UI, FONT_MENU, FONT_TITLE, FONT_SPLASH

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Neuro-Racer - Simulación de IA")
        self.clock = pygame.time.Clock()

        # Inicialización de fuentes internas
        FONT_UI = pygame.font.SysFont("Consolas", 20)
        FONT_MENU = pygame.font.SysFont("Consolas", 24, bold=True)
        FONT_TITLE = pygame.font.SysFont("Consolas", 36, bold=True)
        FONT_SPLASH = pygame.font.SysFont("Consolas", 24, bold=True)

        self.musica_menu = "sounds/background.mp3"
        self.musica_carrera = "sounds/race-track.mp3"

        # Musica de fondo
        try:
            pygame.mixer.music.load(self.musica_menu) # Archivo para el fondo
            pygame.mixer.music.set_volume(0.2)        # Volumen bajo (20%) para que no sature
            pygame.mixer.music.play(-1)               # El parámetro -1 hace que se repita en bucle infinito
        except (pygame.error, FileNotFoundError):
            print(f"Advertencia: No se pudo cargar {self.musica_menu}")

        # 2. Efectos de sonido cortos (Sound FX)
        try:
            self.sonido_bonus = pygame.mixer.Sound("sounds/bonus.mp3")
            self.sonido_bonus.set_volume(0.25)
        except (pygame.error, FileNotFoundError):
            self.sonido_bonus = None

        try:
            self.sonido_enter = pygame.mixer.Sound("sounds/start.mp3")
            self.sonido_enter.set_volume(0.25)
        except (pygame.error, FileNotFoundError):
            self.sonido_enter = None

        try:
            self.sonido_count = pygame.mixer.Sound("sounds/count.mp3")
            self.sonido_count.set_volume(0.25)
        except (pygame.error, FileNotFoundError):
            self.sonido_count = None

        # Carga de la Imagen de Presentación (Splash)
        try:
            self.img_presentacion = pygame.image.load("splashscreen.png")
            self.img_presentacion = pygame.transform.scale(self.img_presentacion, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except (pygame.error, FileNotFoundError):
            print("Advertencia: No se pudo encontrar el archivo splashscreen.png. La simulación correrá sin imagen de presentación.")
            self.img_presentacion = None

        try:
            self.img_menu = pygame.image.load("background_menu.png")
            self.img_menu = pygame.transform.scale(self.img_menu, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except (pygame.error, FileNotFoundError):
            print("Advertencia: No se pudo encontrar el archivo background_menu.png. El menú se mostrará sin imagen de fondo.")
            self.img_menu = None

        # Control de Estados
        self.estado = "PANTALLA_PRESENTACION"
        self.mostrar_instrucciones = False
        self.opciones_menu = [
            "INICIAR_SIMULACION",
            "CARGAR_MODELO_GUARDADO" if os.path.exists("mejor_modelo.pickle") else "CARGAR_MODELO_(NO_EXISTE)",
            "BORRAR_MODELO_GUARDADO" if os.path.exists("mejor_modelo.pickle") else "BORRAR_MODELO_(NO_EXISTE)",
            "INSTRUCCIONES_DEL_SISTEMA",
            "SALIR"
        ]
        self.menu_index = 0  # Comienza apuntando a la primera opción

        # Parámetros de control de la simulación
        self.generation = 1
        self.best_historical_fitness = 0.0
        self.best_brain_historical = None
        self.simulation_speed = 60              # Controlar velocidad del juego (FPS)
        self.is_paused = False                  # Estado de pausa

        # SELECCIÓN DE PISTA
        self.pista_activa = TRACK_OVALO
        self.track_points = self.pista_activa["points"]
        self.population = []
        self.usar_guardado_temp = False

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
        pygame.mixer.music.stop()
        try:
            pygame.mixer.music.load(self.musica_carrera)
            pygame.mixer.music.set_volume(0.3) # Volumen al 30% para la carrera
            pygame.mixer.music.play(-1)        # Reproducir en bucle infinito
        except (pygame.error, FileNotFoundError):
            print(f"Advertencia: No se pudo cargar la música de carrera: {self.musica_carrera}")

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

        self.en_conteo = True
        self.conteo_inicio_tiempo = pygame.time.get_ticks()

    def draw_presentacion(self):
        self.screen.fill(COLOR_BG)

        if self.img_presentacion:
            self.screen.blit(self.img_presentacion, (0, 0))

        if pygame.time.get_ticks() % 1000 < 500:
            lbl_continuar = FONT_SPLASH.render("Presione [ ENTER ] para continuar", True, COLOR_GOLD)
            self.screen.blit(lbl_continuar, (SCREEN_WIDTH//2 - lbl_continuar.get_width()//2, 620))

    def draw_menu(self):
        self.screen.fill(COLOR_BG)

        if self.img_presentacion:
            self.screen.blit(self.img_presentacion, (0, 0))

        existe_modelo = os.path.exists("mejor_modelo.pickle")

        for i, opcion in enumerate(self.opciones_menu):
            # Formatear el texto para que sea amigable a la vista
            texto_bonito = opcion.replace("_", " ").title()

            # --- EFECTO DE RESALTE ---
            # Si el índice actual es el seleccionado por las flechas, cambia de color
            if i == self.menu_index:
                color_texto = (255, 215, 0) # Dorado / Oro Neón
                texto_bonito = f"> {texto_bonito} <" # Añade indicadores visuales
            else:
                color_texto = (200, 200, 200) # Gris estándar pasivo

            if (i == 1 or i == 2) and not existe_modelo:
                color_texto = (100, 100, 110) # Gris oscuro para opciones no disponibles

            # Renderizar y dibujar en la pantalla (ajusta el espaciado en Y)
            text_surface = FONT_MENU.render(texto_bonito, True, color_texto)
            rect_texto = text_surface.get_rect(center=(SCREEN_WIDTH // 2, 360 + (i * 60)))
            self.screen.blit(text_surface, rect_texto)

        # Cuadro de instrucciones flotante
        if self.mostrar_instrucciones:
            pygame.draw.rect(self.screen, (10, 10, 15), (60, 480, 1100, 240), 0, 12)
            pygame.draw.rect(self.screen, COLOR_RAY, (60, 480, 1100, 240), 2, 12)

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
                self.screen.blit(lbl_inst, (90, 500 + i * 28))

    def draw_menu_pistas(self):
        self.screen.fill(COLOR_BG)
        lbl_title = FONT_TITLE.render("SELECCIONA UNA PISTA", True, COLOR_GOLD)
        self.screen.blit(lbl_title, (SCREEN_WIDTH//2 - lbl_title.get_width()//2, 150))

        pistas = [
            TRACK_OVALO["nombre"],
            TRACK_S["nombre"],
            TRACK_CHICANA["nombre"],
            "VOLVER"
        ]

        for i, pista in enumerate(pistas):
            if i == self.menu_index:
                pista = f"> {pista} <"
                color = (255, 215, 0)
            else:
                color = (200, 200, 200)

            text_surface = FONT_MENU.render(pista, True, color)
            rect_texto = text_surface.get_rect(center=(SCREEN_WIDTH // 2, 300 + (i * 60)))
            self.screen.blit(text_surface, rect_texto)

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

        tiempo_pulsacion = math.sin(pygame.time.get_ticks() * 0.005) # Oscila entre -1 y 1
        radio_pulso = int(6 + tiempo_pulsacion * 2)                 # El radio varía sutilmente

        for i, point in enumerate(self.track_points):
            px, py = point

            # CASO A: ES EL CHECKPOINT OBJETIVO DEL LÍDER (Nodo Activo Inteligente)
            if i == leader_car.next_checkpoint_id:
                # 1. Sombra base / Brillo exterior difuminado (Glow Effect)
                # Creamos una superficie de soporte transparente para mezclar el canal Alfa
                superficie_brillo = pygame.Surface((40, 40), pygame.SRCALPHA)

                # Capa externa del destello (Muy transparente)
                pygame.draw.circle(superficie_brillo, (0, 255, 150, 45), (20, 20), radio_pulso + 10)
                # Capa media del destello
                pygame.draw.circle(superficie_brillo, (0, 255, 150, 90), (20, 20), radio_pulso + 5)

                # Volcar el brillo centrado sobre la pantalla principal
                self.screen.blit(superficie_brillo, (px - 20, py - 20))

                # 2. Núcleo sólido del Checkpoint Activo
                pygame.draw.circle(self.screen, (255, 255, 255), (px, py), radio_pulso + 2) # Borde blanco interno
                pygame.draw.circle(self.screen, COLOR_CHECKPOINT, (px, py), radio_pulso)    # Centro verde neón

                # 3. Pequeño anillo perimetral decorativo tipo "radar tracking"
                pygame.draw.circle(self.screen, COLOR_CHECKPOINT, (px, py), radio_pulso + 7, 1)

            # CASO B: CHECKPOINTS RESTANTES (Nodos pasivos en espera)
            else:
                # 1. Sombra proyectada sutil de fondo (Color oscuro translúcido)
                sombra_pasiva = pygame.Surface((20, 20), pygame.SRCALPHA)
                pygame.draw.circle(sombra_pasiva, (10, 10, 15, 150), (10, 10), 6)
                self.screen.blit(sombra_pasiva, (px - 8, py - 6)) # Desplazado un poco abajo/derecha para el efecto 3D

                # 2. Nodo estándar estilizado
                pygame.draw.circle(self.screen, (40, 40, 55), (px, py), 5)            # Base oscura
                pygame.draw.circle(self.screen, (100, 100, 120), (px, py), 4)         # Relleno gris metálico
                pygame.draw.circle(self.screen, (160, 160, 180), (px, py), 2)         # Brillo de lente central

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

        # if best_car.fitness > self.best_historical_fitness:
        #     self.best_historical_fitness = best_car.fitness
        #     self.best_brain_historical = best_car.brain

        print(f"Fin Gen {self.generation}. Récord de Ronda: {int(best_car.fitness)}")

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
                # ANTIESTANCAMIENTO: Inyectamos 4 carros con cerebros completamente aleatorios para meter nuevas ideas y trayectorias frescas a la piscina genética.
                new_population.append(Car(None, spawn_info=self.pista_activa["spawn"]))

        self.population = new_population
        self.generation += 1

    def save_current_best(self):
        """Almacena el genoma entrenado localmente en un archivo .pickle para futuras sesiones"""
        if self.best_brain_historical:
            try:
                # Empaquetamos el cerebro y el récord histórico real en una sola estructura
                datos_a_guardar = {"brain": self.best_brain_historical, "fitness": self.best_historical_fitness}

                with open("mejor_modelo.pickle", "wb") as f:
                    pickle.dump(datos_a_guardar, f)
                print(f"¡Progreso guardado! Marcador: {int(self.best_historical_fitness)} pts")
            except Exception as e:
                print(f"Error escribiendo en persistencia: {e}")

    def draw_ui(self):
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

    def draw_countdown(self):
        # Calcular el tiempo transcurrido desde que se abrió la pista
        self.sonido_count.play()
        tiempo_transcurrido = pygame.time.get_ticks() - self.conteo_inicio_tiempo

        texto_conteo = ""
        color_conteo = COLOR_GOLD

        if tiempo_transcurrido < 1000:
            texto_conteo = "3"
        elif tiempo_transcurrido < 2000:
            texto_conteo = "2"
        elif tiempo_transcurrido < 3000:
            texto_conteo = "1"
        elif tiempo_transcurrido < 4000:
            texto_conteo = "¡GO!"
            color_conteo = COLOR_CHECKPOINT # Color verde para la salida
        else:
            # Al pasar los 4 segundos, el conteo termina y los autos arrancan
            self.en_conteo = False
            return

        # Renderizar el texto con una fuente grande (puedes usar FONT_TITLE o crear una más grande)
        fuente_gigante = pygame.font.SysFont("Consolas", 85, bold=True)
        lbl_conteo = fuente_gigante.render(texto_conteo, True, color_conteo)

        # Posicionar exactamente en el centro de la ventana
        cx = SCREEN_WIDTH // 2 - lbl_conteo.get_width() // 2
        cy = SCREEN_HEIGHT // 2 - lbl_conteo.get_height() // 2

        # Dibujar un ligero fondo oscuro detrás del número para que resalte sobre la pista
        pygame.draw.rect(self.screen, (10, 10, 15, 180), (cx - 30, cy - 10, lbl_conteo.get_width() + 60, lbl_conteo.get_height() + 20), 0, 10)

        # Imprimir el texto
        self.screen.blit(lbl_conteo, (cx, cy))

    def run(self):
        running = True
        while running:
            # Control dinámico de velocidad del ciclo principal
            self.clock.tick(self.simulation_speed if self.estado == "SIMULACION" else 60)

            # Gestión de Eventos
            eventos = pygame.event.get()
            for event in eventos:
                if event.type == pygame.QUIT:
                    running = False
                    break

                if event.type == pygame.KEYDOWN:
                    if self.estado == "PANTALLA_PRESENTACION":
                        if event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                            if self.sonido_enter:
                                self.sonido_enter.play()
                            self.estado = "MENU_PRINCIPAL"

                    elif self.estado == "MENU_PRINCIPAL":
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key == pygame.K_DOWN:
                            self.menu_index = (self.menu_index + 1) % len(self.opciones_menu)
                            if self.sonido_enter: self.sonido_enter.play() # Feedback sonoro corto
                        elif event.key == pygame.K_UP:
                            self.menu_index = (self.menu_index - 1) % len(self.opciones_menu)
                            if self.sonido_enter: self.sonido_enter.play()

                        elif event.key == pygame.K_RETURN:
                            if self.menu_index == 0 and self.sonido_enter:
                                self.sonido_enter.play()
                                self.usar_guardado_temp = False
                                self.estado = "MENU_PISTAS"
                            elif self.menu_index == 1 and os.path.exists("mejor_modelo.pickle") and self.sonido_enter:
                                self.sonido_enter.play()
                                self.usar_guardado_temp = True
                                self.estado = "MENU_PISTAS"
                            elif self.menu_index == 2 and os.path.exists("mejor_modelo.pickle"):
                                try:
                                    os.remove("mejor_modelo.pickle")
                                    print("Archivo de guardado eliminado.")
                                    if self.sonido_enter: self.sonido_enter.play()
                                except Exception: pass
                            elif self.menu_index == 3:
                                self.mostrar_instrucciones = not self.mostrar_instrucciones
                                if self.sonido_enter: self.sonido_enter.play()
                            elif self.menu_index == 4:
                                if self.sonido_enter: self.sonido_enter.play()
                                running = False

                    elif self.estado == "MENU_PISTAS":
                        if event.key == pygame.K_ESCAPE:
                            self.estado = "MENU_PRINCIPAL"
                        elif event.key == pygame.K_DOWN:
                            self.menu_index = (self.menu_index + 1) % 4
                            self.draw_menu_pistas()
                            if self.sonido_enter: self.sonido_enter.play()
                        elif event.key == pygame.K_UP:
                            self.menu_index = (self.menu_index - 1) % 4
                            self.draw_menu_pistas()
                            if self.sonido_enter: self.sonido_enter.play()
                        elif event.key == pygame.K_RETURN:
                            if self.menu_index == 0:
                                self.pista_activa = TRACK_OVALO
                                self.iniciar_simulacion(self.usar_guardado_temp)
                            elif self.menu_index == 1:
                                self.pista_activa = TRACK_S
                                self.iniciar_simulacion(self.usar_guardado_temp)
                            elif self.menu_index == 2:
                                self.pista_activa = TRACK_CHICANA
                                self.iniciar_simulacion(self.usar_guardado_temp)
                            elif self.menu_index == 3:
                                self.estado = "MENU_PRINCIPAL"

                    elif self.estado == "SIMULACION":
                        if event.key == pygame.K_ESCAPE:
                            pygame.mixer.music.stop()
                            try:
                                pygame.mixer.music.load(self.musica_menu)
                                pygame.mixer.music.set_volume(0.2)
                                pygame.mixer.music.play(-1)
                            except (pygame.error, FileNotFoundError):
                                pass
                            self.estado = "MENU_PRINCIPAL"
                        elif event.key == pygame.K_p:
                            self.is_paused = not self.is_paused
                        elif event.key == pygame.K_g:
                            self.save_current_best()
                        elif event.key == pygame.K_f:
                            self.simulation_speed = 300 if self.simulation_speed == 60 else 60

            if not running: break

             # Ejecución lógicas de renderizado según estado actual
            if self.estado == "PANTALLA_PRESENTACION":
                self.draw_presentacion()
            elif self.estado == "MENU_PRINCIPAL":
                self.draw_menu()
            elif self.estado == "MENU_PISTAS":
                self.draw_menu_pistas()
            elif self.estado == "SIMULACION":
                if not self.is_paused and not self.en_conteo:
                    any_alive = False
                    for car in self.population:
                        vuelta_completa = car.update(self.screen, self.track_points)
                        if car.is_alive: any_alive = True
                        if vuelta_completa and self.sonido_bonus:
                            # Si cruzó la meta y el sonido se cargó correctamente, se reproduce
                            self.sonido_bonus.play()

                    if not any_alive:
                        self.next_generation()

                # Pintar el fondo antes de dibujar cualquier cosa (FONDO)
                self.screen.fill(COLOR_BG)

                # Encontrar al líder actual (el que tenga mayor fitness) para renderizar sus sensores
                current_leader = max(self.population, key=lambda c: c.fitness)

                if current_leader.fitness > self.best_historical_fitness:
                    self.best_historical_fitness = current_leader.fitness
                    self.best_brain_historical = current_leader.brain

                # Renderizar pista y muros vectoriales
                self.draw_track(current_leader)

                for car in self.population:
                    is_leader = (car == current_leader and car.is_alive)
                    car.draw(self.screen, is_best=is_leader)

                # Renderizar el panel de control
                self.draw_ui()

                if self.en_conteo:
                    self.draw_countdown()

            pygame.display.flip()

        pygame.quit()
        sys.exit()
