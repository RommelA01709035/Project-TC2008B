
# librerias
from flask import Flask, request, jsonify

from mesa import Agent, Model
from mesa.space import MultiGrid
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
plt.rcParams["animation.html"] = "jshtml"
matplotlib.rcParams['animation.embed_limit'] = 2**128

import numpy as np
import pandas as pd
import seaborn as sn

# Clase Cell que nos ayuda a guardar información
class Cell():
    def __init__(self, x, y, wall):
        # posición
        self.pos = (x, y)

        # vida de los muros
        self.wallHealth = [0,0,0,0]

        # valores de los muros
        if wall[0] == '1':
            self.up = True
            self.wallHealth[0] = 2
        else: self.up = False
        if wall[1] == '1':
            self.left = True
            self.wallHealth[1] = 2
        else: self.left = False
        if wall[2] == '1':
            self.down = True
            self.wallHealth[2] = 2
        else: self.down = False
        if wall[3] == '1':
            self.right = True
            self.wallHealth[3] = 2
        else: self.right = False

        # valor de los puntos de interés 1 si es falsa alarma, 2 si es una víctima
        self.poi = 0

        # valor del fuego 1 si es humo, 2 si es fuego
        self.fire = 0

        # arreglo con la posición de la casilla donde se conecta con puerta
        self.door = []

        # True si la casilla es una entrada a la estructura
        self.entrance = False

        # true si la casilla tiene un agente
        self.is_Agent = 0

# Abrimos el archivo txt del mapa de nuestra simulacion
with open('mapa.txt', 'r') as map_file:
    text = map_file.read()

# ===============================================================================================================================================================================
# ===============================================================================================================================================================================
# ===============================================================================================================================================================================

'''
Clase Agente:

Esta clase modela el comportamiento de nuetros agentes, que en este caso serán
los bomberos del juego de mesa Flash Point: fire rescue
'''

class FiremanAgent(Agent):
    def __init__(self, unique_id, model, point=None):
        super().__init__(unique_id, model)
        self.point = point
        self.actionPoints = 4
        self.carryState = 1
        self.path = []

    '''
    definimos una funcion "step" que indica que es lo que va a hacer cada agente
    en cada paso de la simulacion. Recibe los atributos del propio agente y no
    tienen valor de retorno, como la mayotia de las funciones siguientes.
    '''

    def step(self):
        self.path = self.dijkstra(self.pos, self.point.pos)[0]
        while self.actionPoints >= 1 and self.pos != self.point.pos:
          self.actionPoints -= self.clearPath(self.pos, self.path[0])
          self.model.grid.move_agent(self, self.path[0])
          self.path.pop(0)
        if self.pos == self.point.pos:
            if self.point.poi == 2:
                self.carryState = 2
                closestExit = None
                minDistance = 100
                for exit in self.model.outSide:
                    distance = self.dijkstra(self.pos, exit.pos)[1]
                    if distance < minDistance:
                        minDistance = distance
                        closestExit = exit
                self.model.cells[self.pos[0]][self.pos[1]].poi = 0
                if self.point in self.model.interestPoints:
                    self.model.interestPoints.remove(self.point)
                self.path = self.dijkstra(self.pos, closestExit.pos)[0]
                self.point = closestExit
            elif self.model.cells[self.pos[0]][self.pos[1]] in self.model.outSide and self.carryState == 2:
                self.carryState = 1
                self.model.savedLifes += 1
                self.point = None
            elif self.point.poi == 1:
                self.model.cells[self.pos[0]][self.pos[1]].poi = 0
                if self.point in self.model.interestPoints:
                    self.model.interestPoints.remove(self.point)
                self.point = None
            elif self.point.fire == 2:
                self.point = None
        self.calculateActionPoints()

    '''
    definimos una funcion "dijkstra" la cual nos proporsiona el camino más corto entre dos puntos,
    y ademas nos regresa el costo en puntos de accion que le tomaria al agente realizar dicha accion.
    La funcion recibe las tuplas de las coordenadas del punto de inicio y del final, para despues
    regresar un arreglo de las posiciones con el camino a seguir y su costo en punto de accion.
    '''

    def dijkstra(self, start, end):
        dijkstraMap = {}
        path = []
        for x in range(self.model.grid.height):
            for y in range(self.model.grid.width):
              dijkstraMap[(y, x)] = {"previousCell": None, "steps": None}
        if start in dijkstraMap and end in dijkstraMap and start != end:
            dijkstraMap[start]["steps"] = 0
            dijkstraMap[start]["previousCell"] = start
            queue = [start]
            while len(queue) > 0:
                for neighbor in self.model.grid.get_neighborhood(queue[0], moore=False):
                    if 0 <= neighbor[0] < self.model.grid.width and 0 <= neighbor[1] < self.model.grid.height:
                        if dijkstraMap[neighbor]["steps"] is None:
                            dijkstraMap[neighbor]["steps"] = self.calculateSteps(queue[0], neighbor) + dijkstraMap[queue[0]]["steps"]
                            dijkstraMap[neighbor]["previousCell"] = queue[0]
                            queue.append(neighbor)
                        elif (dijkstraMap[neighbor]["steps"] > self.calculateSteps(queue[0], neighbor) + dijkstraMap[queue[0]]["steps"]):
                            dijkstraMap[neighbor]["steps"] = (self.calculateSteps(queue[0], neighbor) + dijkstraMap[queue[0]]["steps"])
                            dijkstraMap[neighbor]["previousCell"] = queue[0]
                            queue.append(neighbor)
                queue.pop(0)
            cell = end
            while cell != start:
                path.insert(0, cell)
                cell = dijkstraMap[cell]["previousCell"]
            return path, dijkstraMap[end]["steps"]
        else:
            return [end], 0
            
    '''
    "calculateSteps" es una funcion que calcula el coste en puntos de accion para pasar de una
    celda a otra adyacente. Recibe las tuplas de posiciones de inicio y del final, y ademas
    devuekve el costo en puntos de accion de los pasos calculados    
    '''

    def calculateSteps(self, start, end):
        actionPointsCost = 0
        if 0 <= end[0] < len(self.model.cells) and 0 <= end[1] < len(self.model.cells[0]):
            if start[0] < end[0]:
                if (self.model.cells[end[0]][end[1]].up or self.model.cells[start[0]][start[1]].down) and end not in self.model.cells[start[0]][start[1]].door:
                    actionPointsCost += 4.1
                elif (self.model.cells[end[0]][end[1]].up or self.model.cells[start[0]][start[1]].down) and end in self.model.cells[start[0]][start[1]].door:
                    actionPointsCost += 1
                if self.model.cells[end[0]][end[1]].fire == 2:
                    actionPointsCost += 1
                actionPointsCost = actionPointsCost + 1 * self.carryState
            elif start[0] > end[0]:
                if (self.model.cells[end[0]][end[1]].down or self.model.cells[start[0]][start[1]].up) and end not in self.model.cells[start[0]][start[1]].door:
                    actionPointsCost += 4.1
                elif (self.model.cells[end[0]][end[1]].down or self.model.cells[start[0]][start[1]].up) and end in self.model.cells[start[0]][start[1]].door:
                    actionPointsCost += 1
                if self.model.cells[end[0]][end[1]].fire == 2:
                    actionPointsCost += 1
                actionPointsCost = actionPointsCost + 1 * self.carryState
            elif start[1] < end[1]:
                if (self.model.cells[end[0]][end[1]].left or self.model.cells[start[0]][start[1]].right) and end not in self.model.cells[start[0]][start[1]].door:
                    actionPointsCost += 4.1
                elif (self.model.cells[end[0]][end[1]].left or self.model.cells[start[0]][start[1]].right) and end in self.model.cells[start[0]][start[1]].door:
                    actionPointsCost += 1
                if self.model.cells[end[0]][end[1]].fire == 2:
                    actionPointsCost += 1
                actionPointsCost = actionPointsCost + 1 * self.carryState
            elif start[1] > end[1]:
                if (self.model.cells[end[0]][end[1]].right or self.model.cells[start[0]][start[1]].left) and end not in self.model.cells[start[0]][start[1]].door:
                    actionPointsCost += 4.1
                elif (self.model.cells[end[0]][end[1]].right or self.model.cells[start[0]][start[1]].left) and end in self.model.cells[start[0]][start[1]].door:
                    actionPointsCost += 1
                if self.model.cells[end[0]][end[1]].fire == 2:
                    actionPointsCost += 1
                actionPointsCost = actionPointsCost + 1 * self.carryState
        return actionPointsCost
    
    # esta funcion modifica internamente los puntos de accion de los agentes. Agrega 4, pero estos no pueden superar 8

    def calculateActionPoints(self):
        if self.actionPoints + 4 > 8:
            self.actionPoints = 8
        else:
            self.actionPoints += 4

    '''
    la funcion "remove walls" permite a los agentes romper las paredes del mapa, recibe una celda adyacente
    y modifica internamente el valor del muro en el mapa.
    '''

    def removeWall(self, end):
        if self.pos[0] < end[0]:
            self.model.cells[end[0]][end[1]].up = False
            self.model.cells[self.pos[0]][self.pos[1]].down = False
            self.model.structural_Damage_Left -= 2
        elif self.pos[0] > end[0]:
            self.model.cells[end[0]][end[1]].down = False
            self.model.cells[self.pos[0]][self.pos[1]].up = False
            self.model.structural_Damage_Left -= 2
        elif self.pos[1] < end[1]:
            self.model.cells[end[0]][end[1]].left = False
            self.model.cells[self.pos[0]][self.pos[1]].right = False
            self.model.structural_Damage_Left -= 2
        elif self.pos[1] > end[1]:
            self.model.cells[end[0]][end[1]].right = False
            self.model.cells[self.pos[0]][self.pos[1]].left = False
            self.model.structural_Damage_Left -= 2

    '''
    esta funcion elimina el fuego, las puertas y las paredes de una celda adyacente y paga los puntos de accion
    del agente que le costaria realizar estas acciones. Recibe una celda de inicio, donde esta el agente, y otra
    de final, donde este quiere llegar. Esta funcion modifica directamente los valores del mapa y el agente.
    '''

    def clearPath(self, start, end):
        actionPointsCost = 0
        if 0 <= end[0] < len(self.model.cells) and 0 <= end[1] < len(self.model.cells[0]):
            if start[0] < end[0]:
                if (self.model.cells[end[0]][end[1]].up or self.model.cells[start[0]][start[1]].down) and end not in self.model.cells[start[0]][start[1]].door:
                    actionPointsCost += 4
                    self.removeWall(end)
                elif (self.model.cells[end[0]][end[1]].up or self.model.cells[start[0]][start[1]].down) and end in self.model.cells[start[0]][start[1]].door:
                    actionPointsCost += 1
                    self.model.cells[start[0]][start[1]].door.remove(end)
                    self.model.cells[end[0]][end[1]].door.remove(start)
                    self.removeWall(end)
                if self.model.cells[end[0]][end[1]].fire == 2:
                    actionPointsCost += 1
                    self.model.firePoints.remove(self.model.cells[end[0]][end[1]])
                    self.model.cells[end[0]][end[1]].fire = 0
                actionPointsCost = actionPointsCost + 1 * self.carryState
            elif start[0] > end[0]:
                if (self.model.cells[end[0]][end[1]].down or self.model.cells[start[0]][start[1]].up) and end not in self.model.cells[start[0]][start[1]].door:
                    actionPointsCost += 4
                    self.removeWall(end)
                elif (self.model.cells[end[0]][end[1]].down or self.model.cells[start[0]][start[1]].up) and end in self.model.cells[start[0]][start[1]].door:
                    actionPointsCost += 1
                    self.model.cells[start[0]][start[1]].door.remove(end)
                    self.model.cells[end[0]][end[1]].door.remove(start)
                    self.removeWall(end)
                if self.model.cells[end[0]][end[1]].fire == 2:
                    actionPointsCost += 1
                    self.model.firePoints.remove(self.model.cells[end[0]][end[1]])
                    self.model.cells[end[0]][end[1]].fire = 0
                actionPointsCost = actionPointsCost + 1 * self.carryState
            elif start[1] < end[1]:
                if (self.model.cells[end[0]][end[1]].left or self.model.cells[start[0]][start[1]].right) and end not in self.model.cells[start[0]][start[1]].door:
                    actionPointsCost += 4
                    self.removeWall(end)
                elif (self.model.cells[end[0]][end[1]].left or self.model.cells[start[0]][start[1]].right) and end in self.model.cells[start[0]][start[1]].door:
                    actionPointsCost += 1
                    self.model.cells[start[0]][start[1]].door.remove(end)
                    self.model.cells[end[0]][end[1]].door.remove(start)
                    self.removeWall(end)
                if self.model.cells[end[0]][end[1]].fire == 2:
                    actionPointsCost += 1
                    self.model.firePoints.remove(self.model.cells[end[0]][end[1]])
                    self.model.cells[end[0]][end[1]].fire = 0
                actionPointsCost = actionPointsCost + 1 * self.carryState
            elif start[1] > end[1]:
                if (self.model.cells[end[0]][end[1]].right or self.model.cells[start[0]][start[1]].left) and end not in self.model.cells[start[0]][start[1]].door:
                    actionPointsCost += 4
                    self.removeWall(end)
                elif (self.model.cells[end[0]][end[1]].right or self.model.cells[start[0]][start[1]].left) and end in self.model.cells[start[0]][start[1]].door:
                    self.model.cells[start[0]][start[1]].door.remove(end)
                    self.model.cells[end[0]][end[1]].door.remove(start)
                    self.removeWall(end)
                    actionPointsCost += 1
                if self.model.cells[end[0]][end[1]].fire == 2:
                    actionPointsCost += 1
                    self.model.firePoints.remove(self.model.cells[end[0]][end[1]])
                    self.model.cells[end[0]][end[1]].fire = 0
                actionPointsCost = actionPointsCost + 1 * self.carryState
        return actionPointsCost
    
# ===============================================================================================================================================================================
# ===============================================================================================================================================================================
# ===============================================================================================================================================================================

# Esta clase modela el entorno de nuestra simulación.
class MapModel(Model):
    def __init__(self, num_agents):
        super().__init__()
        self.steps = 0
        self.smokes = []
        self.savedLifes = 0
        self.deathLifes = 0
        self.deadAgents = 0
        self.width = 10
        self.height = 8
        self.structural_Damage_Left = 24
        self.num_agents = num_agents
        self.grid = MultiGrid(self.height, self.width, False)
        self.cells, self.outSide = self.read_map_data()
        self.inside = [cell for row in self.cells for cell in row if cell not in self.outSide]
        self.putEntranceDoors()
        self.interestPoints = [cell for row in self.cells for cell in row if cell.poi != 0]
        self.firePoints = [cell for row in self.cells for cell in row if cell.fire == 2]
        self.schedule = RandomActivation(self)
        self.running = True
        for i in range(self.num_agents):
          agent = FiremanAgent(i, self)
          self.schedule.add(agent)
          self.grid.place_agent(agent, (0,0))
          self.positionAgent(agent)

# Esta función posiciona a los agentes en una celda aleatoria fuera de la casa
    def positionAgent(self, agent):
          random_pos = self.random.choice(self.outSide)
          self.grid.move_agent(agent, random_pos.pos)

# Esta función lee el archivo de texto de entrada y coloca la información en una matriz y un arreglo (cells y outSide)
    def read_map_data(self):
      with open('mapa.txt', 'r') as map:
        text = map.read()

        walls = []
        for i in range(8):
            for j in range(6):
                new_wall = text[:4]
                walls.append(new_wall)
                text = text[5:]

        alerts = []
        for i in range(3):
            pos_alert_x = text[0]
            pos_alert_y = text[2]
            pos_alert_state = text[4]
            text = text[6:]
            alerts.append( (pos_alert_x, pos_alert_y, pos_alert_state) )

        fires = []
        for i in range(10):
            pos_fire_x = text[0]
            pos_fire_y = text[2]
            text = text[4:]
            fires.append( (pos_fire_x, pos_fire_y) )

        doors = []
        for i in range(8):
            pos_doorA_x = text[0]
            pos_doorA_y = text[2]
            pos_doorB_x = text[4]
            pos_doorB_y = text[6]
            text = text[8:]
            doors.append( ( (pos_doorA_x, pos_doorA_y), (pos_doorB_x, pos_doorB_y) ) )

        exits = []
        for i in range(4):
            pos_exit_x = text[0]
            pos_exit_y = text[2]
            text = text[4:]
            exits.append( (pos_exit_x, pos_exit_y) )

        cells = []
        for i in range(6):
            for j in range(8):
                w = walls[0]
                del walls[0]

                c = Cell(i + 1,j + 1,w)
                cells.append(c)

                if (str(i + 1), str(j + 1), 'v') in alerts:
                    c.poi = 2
                elif (str(i + 1), str(j + 1), 'f') in alerts:
                    c.poi = 1

                if (str(i + 1), str(j + 1)) in fires:
                    c.fire = 2

                for d in doors:
                  if (str(i + 1), str(j + 1)) == d[0]:
                    c.door.append((int(d[1][0]), int(d[1][1])))
                  elif (str(i + 1), str(j + 1)) == d[1]:
                    c.door.append((int(d[0][0]), int(d[0][1])))

                if (str(i + 1), str(j + 1)) in exits:
                    c.entrance = True

        new_cells = [
            Cell(0, 0, "0000"),
            Cell(0, 1, "0010"),
            Cell(0, 2, "0010"),
            Cell(0, 3, "0010"),
            Cell(0, 4, "0010"),
            Cell(0, 5, "0010"),
            Cell(0, 6, "0010"),
            Cell(0, 7, "0010"),
            Cell(0, 8, "0010"),
            Cell(0, 9, "0000"),
        ]
        outSide = new_cells
        cells = new_cells + cells
        for i in range (1, 7):
          c = Cell(i, 0, "0001")
          cells.insert(i * 10, c)
          outSide.append(c)
          c = Cell(i, 9, "0100")
          cells.insert((i * 10) + 9, c)
          outSide.append(c)
        new_cells = [
            Cell(7, 0, "0000"),
            Cell(7, 1, "1000"),
            Cell(7, 2, "1000"),
            Cell(7, 3, "1000"),
            Cell(7, 4, "1000"),
            Cell(7, 5, "1000"),
            Cell(7, 6, "1000"),
            Cell(7, 7, "1000"),
            Cell(7, 8, "1000"),
            Cell(7, 9, "0000"),
        ]
        outSide = outSide + new_cells
        cells = cells + new_cells
        map = [[None for _ in range(10)] for _ in range(8)]
        for cell in cells:
          y, x = cell.pos
          map[y][x] = cell
          #print(f"{map[y][x].pos}: {map[y][x].up} - {map[y][x].left} - {map[y][x].down} - {map[y][x].right}   A: {map[y][x].alert}   F: {map[y][x].fire}   D: {map[y][x].door}    E: {map[y][x].entrance}")
        return map, outSide

# Esta función indica las acciones que se toman en cada paso de la simulación
    def step(self):
      self.endSim()
      print(f"Vidas salvadas: {self.savedLifes}, Muertes: {self.deathLifes}, Danio Estructural Restante: {self.structural_Damage_Left}, Agentes muertos: {model.deadAgents}")
      if self.running == True:
        if self.steps > 0:
          self.spark()
        self.smokes = [cell for row in self.cells for cell in row if cell.fire == 1]
        self.firePoints = [cell for row in self.cells for cell in row if cell.fire == 2]
        smokesChecked = False
        while smokesChecked == False:
          smokesChecked = self.checkSmokes()
        for agent in self.schedule.agents:
          if self.cells[agent.pos[0]][agent.pos[1]] in self.firePoints:
            if agent.carryState == 2:
              agent.carryState = 1
              self.deathLifes += 1
              self.deadAgents += 1
              self.positionAgent(agent)
              print(f"Agente {agent.unique_id} quemado mientras rescataba en {agent.pos}")
            else:
              self.deadAgents += 1
              self.positionAgent(agent)
              print(f"Agente {agent.unique_id} ha muerto quemado en {agent.pos}")
        if len(self.interestPoints) > 0:
          for interestPoint in self.interestPoints:
            if interestPoint in self.firePoints:
              if interestPoint.poi == 2:
                self.deathLifes += 1
                print(f"Persona revelada y muerta en {interestPoint.pos} por chispa")
              elif interestPoint.poi == 1:
                print(f"Falsa alarma revelada en {interestPoint.pos} por fuego")
              self.interestPoints.remove(interestPoint)
        self.asignPoints()
        # self.plot_grid()
        for puntoInteres in self.interestPoints:
          print(f"Puntos de interés en: {puntoInteres.pos}")
        print("\n")
        for puntoFuego in self.firePoints:
          print(f"Puntos de fuego en: {puntoFuego.pos}")
        print("\n")
        for agent in model.schedule.agents:
          print(f"Agente: {agent.unique_id} Posición: {agent.pos} Yendo a: {agent.point.pos}")
        print("\n")
        self.schedule.step()

# Esta función genera un nuevo punto de interés
# Retorna una instancia de la clase Cell con toda la información
    def generateNewInterestPoint(self):
      flat_cells = [cell for row in self.cells for cell in row]
      randomCell = self.random.choice(list(filter(lambda cell: cell not in self.outSide
                                                  and cell not in self.interestPoints
                                                  and cell not in self.smokes
                                                  and cell not in self.firePoints, flat_cells)))
      randomCell.poi = self.random.randint(1, 2)
      return randomCell

# Esta función indica las puertas de entrada en la matriz cells
    def putEntranceDoors(self):
      for row in self.cells:
        for cell in row:
          if cell.entrance:
            if cell.pos[0] == 1:
              cell.up = False
              self.cells[cell.pos[0] - 1][cell.pos[1]].down = False
            elif cell.pos[0] == 6:
              cell.down = False
              self.cells[cell.pos[0] + 1][cell.pos[1]].up = False
            elif cell.pos[1] == 1:
              cell.left = False
              self.cells[cell.pos[0]][cell.pos[1] - 1].right = False
            elif cell.pos[1] == 8:
              cell.right = False
              self.cells[cell.pos[0]][cell.pos[1] + 1].left = False

# Esta función asigna los puntos de interés o fuegos a cada agente
    def asignPoints(self):
      while len(self.interestPoints) < 3:
        self.interestPoints.append(self.generateNewInterestPoint())
      minSteps = 100
      closestAgent = None
      interestPoints = self.interestPoints.copy()
      for agent in self.schedule.agents:
        if agent.point in interestPoints:
          interestPoints.remove(agent.point)
      for interestPoint in interestPoints:
        closestAgent = None
        for agent in self.schedule.agents:
          if agent.point is None:
            steps = agent.dijkstra(agent.pos, interestPoint.pos)[1]
            if steps < minSteps:
              minSteps = steps
              closestAgent = agent.unique_id
        for agent in self.schedule.agents:
          if closestAgent == agent.unique_id:
            agent.point = interestPoint
            minSteps = 100
      minSteps = 100
      if len(self.firePoints) > 3:
        leftFirePoints = self.firePoints.copy()
        for agent in self.schedule.agents:
          if agent.point is None:
            for fire in leftFirePoints:
              steps = agent.dijkstra(agent.pos, fire.pos)[1]
              if steps < minSteps:
                minSteps = steps
                agent.point = fire
            leftFirePoints.remove(agent.point)
            minSteps = 100
      else:
        for agent in self.schedule.agents:
          if agent.point is None:
            agent.point = agent.point

# Esta función indica en que celda del mapa cae la chispa y que pasa de acuerdo al estado de la celda
    def spark(self):
      flat_cells = [cell for row in self.cells for cell in row]
      randomCell = self.random.choice(list(filter(lambda cell: cell not in self.outSide, flat_cells)))
      if randomCell.fire == 0:
        randomCell.fire = 1
        print(f"Chispa en: {randomCell.pos}, humo generado")
      elif randomCell.fire == 1:
        randomCell.fire = 2
        print(f"Chispa en: {randomCell.pos}, fuego generado")
      elif randomCell.fire == 2:
        for i in range(4):
          self.explodeDir(i, randomCell)
        print(f"Chispa en: {randomCell.pos}, explosion generada")

# Esta función modela el comportamiento de las explosiones
# Recibe la dirección de hacia dónde se expande la explosión y dónde inicia
    def explodeDir(self, dir, cell):
        if cell in self.inside:
          if dir == 0:
            if cell.fire == 2:
              if self.cells[cell.pos[0] - 1][cell.pos[1]].pos in cell.door:
                self.removeDoor(cell, self.cells[cell.pos[0] - 1][cell.pos[1]], dir)
              elif cell.up == True:
                self.cells[cell.pos[0]][cell.pos[1]].wallHealth[0] -= 1
                self.cells[cell.pos[0] - 1][cell.pos[1]].wallHealth[2] -= 1
                if cell.wallHealth[0] == 0:
                  self.cells[cell.pos[0]][cell.pos[1]].up = False
                  self.cells[cell.pos[0] - 1][cell.pos[1]].down = False
                  self.structural_Damage_Left -= 2
                  print(f"Pared removida por explosion en {cell.pos}")
              else:
                self.explodeDir(0, self.cells[cell.pos[0] - 1][cell.pos[1]])
            else:
              self.asignFire(self.cells[cell.pos[0]][cell.pos[1]])

          elif dir == 1:
            if cell.fire == 2:
              if self.cells[cell.pos[0]][cell.pos[1] - 1].pos in cell.door:
                self.removeDoor(cell, self.cells[cell.pos[0]][cell.pos[1] - 1], dir)
              elif cell.left == True:
                self.cells[cell.pos[0]][cell.pos[1]].wallHealth[1] -= 1
                self.cells[cell.pos[0]][cell.pos[1] - 1].wallHealth[3] -= 1
                if cell.wallHealth[1] == 0:
                  self.cells[cell.pos[0]][cell.pos[1]].left = False
                  self.cells[cell.pos[0]][cell.pos[1] - 1].right = False
                  self.structural_Damage_Left -= 2
                  print(f"Pared removida por explosion en {cell.pos}")
              else:
                self.explodeDir(1, self.cells[cell.pos[0]][cell.pos[1] - 1])
            else:
              self.asignFire(self.cells[cell.pos[0]][cell.pos[1]])

          elif dir == 2:
            if cell.fire == 2:
              if self.cells[cell.pos[0] + 1][cell.pos[1]].pos in cell.door:
                self.removeDoor(cell, self.cells[cell.pos[0] + 1][cell.pos[1]], dir)
              elif cell.down == True:
                self.cells[cell.pos[0]][cell.pos[1]].wallHealth[2] -= 1
                self.cells[cell.pos[0] + 1][cell.pos[1]].wallHealth[0] -= 1
                if cell.wallHealth[2] == 0:
                  self.cells[cell.pos[0]][cell.pos[1]].down = False
                  self.cells[cell.pos[0] + 1][cell.pos[1]].up = False
                  self.structural_Damage_Left -= 2
                  print(f"Pared removida por explosion en {cell.pos}")
              else:
                self.explodeDir(2, self.cells[cell.pos[0] + 1][cell.pos[1]])
            else:
              self.asignFire(self.cells[cell.pos[0]][cell.pos[1]])

          elif dir == 3:
            if cell.fire == 2:
              if self.cells[cell.pos[0]][cell.pos[1] + 1].pos in cell.door:
                self.removeDoor(cell, self.cells[cell.pos[0]][cell.pos[1] + 1], dir)
              elif cell.right == True:
                self.cells[cell.pos[0]][cell.pos[1]].wallHealth[3] -= 1
                self.cells[cell.pos[0]][cell.pos[1] + 1].wallHealth[1] -= 1
                if cell.wallHealth[3] == 0:
                  self.cells[cell.pos[0]][cell.pos[1]].right = False
                  self.cells[cell.pos[0]][cell.pos[1] + 1].left = False
                  self.structural_Damage_Left -= 2
                  print(f"Pared removida por explosion en {cell.pos}")
              else:
                self.explodeDir(3, self.cells[cell.pos[0]][cell.pos[1] + 1])
            else:
              self.asignFire(self.cells[cell.pos[0]][cell.pos[1]])

# Esta función quita las puertas del mapa debido a una explosión
# Recibe las celdas que contienen la puerta y la dirección en que iba la explosión
    def removeDoor(self, cell1, cell2, dir):
      self.cells[cell1.pos[0]][cell1.pos[1]].door.remove(cell2.pos)
      self.cells[cell2.pos[0]][cell2.pos[1]].door.remove(cell1.pos)
      if dir == 0:
        self.cells[cell1.pos[0]][cell1.pos[1]].up = False
        self.cells[cell2.pos[0]][cell2.pos[1]].down = False
      elif dir == 1:
        self.cells[cell1.pos[0]][cell1.pos[1]].left = False
        self.cells[cell2.pos[0]][cell2.pos[1]].right = False
      elif dir == 2:
        self.cells[cell1.pos[0]][cell1.pos[1]].down = False
        self.cells[cell2.pos[0]][cell2.pos[1]].up = False
      elif dir == 3:
        self.cells[cell1.pos[0]][cell1.pos[1]].right = False
        self.cells[cell2.pos[0]][cell2.pos[1]].left = False
      print(f"Puerta removida por explosion en {cell1.pos}")

# Esta función asigna el estado de fuego a una celda
# Recibe la celda que queremos incendiar
    def asignFire(self, cell):
      self.cells[cell.pos[0]][cell.pos[1]].fire = 2

# Esta función verifica si los humos tienen fuegos alrededor para convertirse en fuegos
    def checkSmokes(self):
      for smoke in self.smokes:
        if self.cells[smoke.pos[0] - 1][smoke.pos[1]].fire == 2 and smoke.up == False:
          self.cells[smoke.pos[0]][smoke.pos[1]].fire = 2
          self.firePoints.append(self.cells[smoke.pos[0]][smoke.pos[1]])
          self.smokes.remove(smoke)
          return False
        elif self.cells[smoke.pos[0] + 1][smoke.pos[1]].fire == 2 and smoke.down == False:
          self.cells[smoke.pos[0]][smoke.pos[1]].fire = 2
          self.firePoints.append(self.cells[smoke.pos[0]][smoke.pos[1]])
          self.smokes.remove(smoke)
          return False
        elif self.cells[smoke.pos[0]][smoke.pos[1] - 1].fire == 2 and smoke.left == False:
          self.cells[smoke.pos[0]][smoke.pos[1]].fire = 2
          self.firePoints.append(self.cells[smoke.pos[0]][smoke.pos[1]])
          self.smokes.remove(smoke)
          return False
        elif self.cells[smoke.pos[0]][smoke.pos[1] + 1].fire == 2 and smoke.right == False:
          self.cells[smoke.pos[0]][smoke.pos[1]].fire = 2
          self.firePoints.append(self.cells[smoke.pos[0]][smoke.pos[1]])
          self.smokes.remove(smoke)
          return False
      return True

# Esta función determina el final de la simulación
    def endSim(self):
      if self.structural_Damage_Left < 0:
        print("Derrota: Demasiado danio estructural")
        self.running = False
      elif self.deathLifes >= 4:
        print("Derrota: Demasiados muertos")
        self.running = False
      elif self.savedLifes >= 7:
        print("Victoria: Personas rescatadas ")
        self.running = False

# Esta función hace un gráfico del estado del mapa y los agentes
    def plot_grid(self):
      grid = np.zeros((self.grid.width, self.grid.height))
      for cell in self.grid.coord_iter():
          contents = cell[0]
          y, x = cell[1]
          if contents:
              grid[y][x] = 1 # negro donde están los agentes
          elif self.cells[y][x].fire == 2:
              grid[y][x] = 2 # rojo donde hay fuego
          elif self.cells[y][x].fire == 1:
              grid[y][x] = 3 # gris donde hay humo
          elif self.cells[y][x].poi != 0:
              grid[y][x] = 4 # azul donde hay puntos de interés

      from matplotlib.colors import ListedColormap
      cmap = ListedColormap(['white', 'black', 'red', 'gray', 'blue'])
      plt.imshow(grid, cmap=cmap)
      plt.title(f"Paso: {self.steps}")
      plt.show()
      self.steps += 1

total_steps = []

import copy

model = MapModel(6)
while model.running:

    for cell in model.grid.coord_iter():
       contents = cell[0]
       x, y = cell[1]

       for _ in contents:
          model.cells[x][y].is_Agent += 1

    total_steps.append(copy.deepcopy(model.cells))
    model.step()
    
    for cell in model.grid.coord_iter():
       contents = cell[0]
       x, y = cell[1]
       model.cells[x][y].is_Agent = 0

map = {}

for step in range(len(total_steps)):
  for row in range(len(total_steps[step])):
    for cell in range(len(total_steps[step][row])):
      map[f"{step ,total_steps[step][row][cell].pos[0], total_steps[step][row][cell].pos[1]}"] = {
        "pos":          f"{total_steps[step][row][cell].pos}",
        "up":           f"{total_steps[step][row][cell].up}",
        "left":         f"{total_steps[step][row][cell].left}",
        "down":         f"{total_steps[step][row][cell].down}",
        "right":        f"{total_steps[step][row][cell].right}",
        "alert":        f"{total_steps[step][row][cell].poi}",
        "fire":         f"{total_steps[step][row][cell].fire}",
        "door":         f"{total_steps[step][row][cell].door}" ,
        "entrance":     f"{total_steps[step][row][cell].entrance}",
        "is agent":     f"{total_steps[step][row][cell].is_Agent}",
        "step":         f"{step}"
      }     

      if total_steps[step][row][cell].is_Agent > 0: print(f"{total_steps[step][row][cell].is_Agent} {step}")

# API que envía los datos a Unity
app = Flask(__name__)
@app.route("/", methods=['GET'])
def get_data():
    return jsonify(map)

if __name__ == '__main__':
    app.run(debug=True)