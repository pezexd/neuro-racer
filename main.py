import pygame
from simulation import Simulation

def main():
    pygame.init()
    pygame.mixer.init()
    pygame.font.init()

    # Arrancar aplicación
    simulador = Simulation()
    simulador.run()

if __name__ == "__main__":
    main()
