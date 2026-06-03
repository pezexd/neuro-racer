import math
import random

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
        """Multiplicación matricial básica para obtener las salidas (Feedforward)"""
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
