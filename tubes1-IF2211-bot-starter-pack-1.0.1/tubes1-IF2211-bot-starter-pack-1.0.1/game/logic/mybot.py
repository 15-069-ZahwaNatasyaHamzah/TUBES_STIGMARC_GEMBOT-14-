import random
from typing import Optional, List, Tuple
from collections import deque

from game.logic.base import BaseLogic
from game.models import GameObject, Board, Position


class Gembot(BaseLogic):
    def _init_(self):
        self.directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]

    def bfs_path(self, board: Board, start: Position, target: Position) -> Optional[List[Tuple[int, int]]]:
        visited = set()
        queue = deque([(start.x, start.y)])
        parents = {}

        while queue:
            x, y = queue.popleft()
            if (x, y) in visited:
                continue
            visited.add((x, y))

            if (x, y) == (target.x, target.y):
                return self.reconstruct_path(parents, (x, y), (start.x, start.y))

            for dx, dy in self.directions:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < board.width and 0 <= ny < board.height):
                    continue
                if any(obj.position.x == nx and obj.position.y == ny and obj.type == "wall" for obj in board.game_objects):
                    continue
                if (nx, ny) not in parents:
                    parents[(nx, ny)] = (x, y)
                    queue.append((nx, ny))
        return None

    def reconstruct_path(self, parents, goal, start):
        path = []
        current = goal
        while current != start:
            path.append(current)
            current = parents[current]
        path.reverse()
        return path

    def manhattan_distance(self, pos1: Position, pos2: Tuple[int, int]) -> int:
        return abs(pos1.x - pos2[0]) + abs(pos1.y - pos2[1])

    def diamond_priority(self, diamond: GameObject, bot_pos: Position) -> int:
        dist = self.manhattan_distance(bot_pos, (diamond.position.x, diamond.position.y))
        points = getattr(diamond.properties, 'points', 1)
        return dist * 2 - points

    def is_enemy_nearby(self, board: Board, bot_pos: Position, radius: int = 3) -> bool:
        for enemy in board.bots:
            if enemy.position != bot_pos and enemy.properties.diamonds > 0:
                dist = self.manhattan_distance(bot_pos, (enemy.position.x, enemy.position.y))
                if dist <= radius:
                    return True
        return False

    def next_move(self, board_bot: GameObject, board: Board) -> Tuple[int, int]:
        props = board_bot.properties
        current_pos = board_bot.position
        my_x, my_y = current_pos.x, current_pos.y

        target = None

        # Kembali ke base jika penuh atau dalam bahaya
        if props.diamonds >= props.inventory_size or (
            props.diamonds >= max(2, props.inventory_size - 1) and self.is_enemy_nearby(board, current_pos, radius=3)):
            target = props.base

        # Prioritas diamond aman dan bisa diambil
        if not target:
            sisa = props.inventory_size - props.diamonds
            diamonds = [
                d for d in board.game_objects
                if d.type == "DiamondGameObject" and getattr(d.properties, 'weight', 1) <= sisa
            ]
            safe_diamonds = []
            for d in diamonds:
                if all(self.manhattan_distance(Position(d.position.x, d.position.y), (e.position.x, e.position.y)) > 2
                       for e in board.bots if e != board_bot):
                    safe_diamonds.append(d)

            if safe_diamonds:
                safe_diamonds.sort(key=lambda d: self.diamond_priority(d, current_pos))
                target = safe_diamonds[0].position

        # Jika tidak ada diamond aman, cegat musuh terdekat yang bawa diamond
        if not target:
            enemies = [e for e in board.bots if e != board_bot and e.properties.diamonds > 0]
            if enemies:
                enemies.sort(key=lambda e: self.manhattan_distance(current_pos, (e.position.x, e.position.y)))
                nearest_enemy = enemies[0]
                if self.manhattan_distance(current_pos, (nearest_enemy.position.x, nearest_enemy.position.y)) <= 3:
                    target = nearest_enemy.position

        # Jika tidak ada prioritas lain, pulang
        if not target:
            target = props.base

        # Gerak menuju target dengan BFS
        path = self.bfs_path(board, current_pos, target)
        if path and len(path) > 0:
            next_pos = path[0]
            dx = next_pos[0] - my_x
            dy = next_pos[1] - my_y
            if board.is_valid_move(current_pos, dx, dy):
                return dx, dy

        # Fallback move
        for dx, dy in self.directions:
            nx, ny = my_x + dx, my_y + dy
            if board.is_valid_move(current_pos, dx, dy):
                if not any(obj.position.x == nx and obj.position.y == ny and obj.type == "wall"
                           for obj in board.game_objects):
                    return dx, dy

        return 0, -1