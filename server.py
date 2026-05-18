import json
import random
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

class SaperGame:
    def __init__(self, width=5, height=5, mines=3):
        self.W = width
        self.H = height
        self.MINES = mines
        self.table = []
        self.revealed = []
        self.flags = []  # Флажки игрока
        self.init_game()
    
    def init_game(self):
        # Проверка, чтобы бомб не было больше чем клеток
        max_mines = self.W * self.H - 1
        if self.MINES > max_mines:
            self.MINES = max_mines
            print(f"⚠️ Бомб не может быть больше {max_mines}, установлено {self.MINES}")
        
        # Создаём поле
        self.table = [[0]*self.W for _ in range(self.H)]
        self.flags = [[False]*self.W for _ in range(self.H)]
        
        # Размещаем бомбы
        all_cells = [(x,y) for x in range(self.W) for y in range(self.H)]
        mines = random.sample(all_cells, self.MINES)
        for x,y in mines:
            self.table[y][x] = -1
        
        # Считаем цифры
        for y in range(self.H):
            for x in range(self.W):
                if self.table[y][x] == -1:
                    continue
                count = 0
                for dy in (-1,0,1):
                    for dx in (-1,0,1):
                        nx, ny = x+dx, y+dy
                        if 0<=nx<self.W and 0<=ny<self.H and self.table[ny][nx]==-1:
                            count += 1
                self.table[y][x] = count
        
        self.revealed = [[False]*self.W for _ in range(self.H)]
        self.save_game_json()
        print(f"✅ Создано поле {self.W}x{self.H} с {self.MINES} бомбами")
    
    def save_game_json(self):
        with open("game.json", "w", encoding="utf-8") as f:
            json.dump({
                "table": self.table,
                "revealed": self.revealed,
                "flags": self.flags,
                "width": self.W,
                "height": self.H,
                "mines": self.MINES
            }, f, indent=2)
    
    def toggle_flag(self, x, y):
        """Установить/снять флажок"""
        if self.revealed[y][x]:
            return False  # Нельзя ставить флаг на открытую клетку
        self.flags[y][x] = not self.flags[y][x]
        self.save_game_json()
        return self.flags[y][x]
    
    def reveal_cell(self, x, y):
        """Открыть клетку (только если нет флажка)"""
        if self.flags[y][x]:
            return {"error": "На клетке стоит флажок! Снимите его сначала."}
        if self.revealed[y][x]:
            return {"error": "Клетка уже открыта"}
        
        if self.table[y][x] == -1:
            self.revealed[y][x] = True
            self.save_game_json()
            return {"game_over": True, "won": False}
        
        self._reveal_recursive(x, y)
        
        # Проверка победы
        won = self.check_win()
        self.save_game_json()
        return {"game_over": False, "won": won}
    
    def _reveal_recursive(self, x, y):
        if not (0 <= x < self.W and 0 <= y < self.H):
            return
        if self.revealed[y][x]:
            return
        if self.flags[y][x]:
            return
        if self.table[y][x] == -1:
            return
        
        self.revealed[y][x] = True
        
        if self.table[y][x] == 0:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    self._reveal_recursive(x + dx, y + dy)
    
    def check_win(self):
        all_safe_revealed = True
        for y in range(self.H):
            for x in range(self.W):
                if self.table[y][x] != -1 and not self.revealed[y][x]:
                    all_safe_revealed = False
                    break
        return all_safe_revealed
    
    def process_moves(self, moves_file="moves.json"):
        if not os.path.exists(moves_file):
            return {"error": f"{moves_file} не найден"}
        
        with open(moves_file, "r", encoding="utf-8") as f:
            moves_data = json.load(f)
        
        moves = moves_data.get("moves", [])
        if not moves:
            return {"error": "Нет ходов"}
        
        results = []
        game_over = False
        won = False
        
        for i, move in enumerate(moves, 1):
            if game_over or won:
                break
            
            action = move.get("action", "reveal")
            x = move.get("x")
            y = move.get("y")
            
            if action == "flag":
                result = self.toggle_flag(x, y)
                results.append(f"Ход {i}: {'🚩 Флаг установлен' if result else '🚩 Флаг снят'} на ({x},{y})")
            else:  # reveal
                if self.flags[y][x]:
                    results.append(f"Ход {i}: ({x},{y}) ⛔ НЕЛЬЗЯ - на клетке флажок!")
                    continue
                
                if self.table[y][x] == -1:
                    results.append(f"Ход {i}: ({x},{y}) 💥 МИНА! Игра окончена")
                    game_over = True
                    break
                
                self.reveal_cell(x, y)
                results.append(f"Ход {i}: ({x},{y}) ✅ открыто, число {self.table[y][x]}")
                
                if self.check_win():
                    won = True
                    results.append("🎉 ПОБЕДА!")
                    break
        
        result = {
            "results": results,
            "game_over": game_over,
            "won": won
        }
        with open("result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        return result

# Создаём игру
game = SaperGame(5, 5, 3)

class MyHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        
        if self.path == '/reveal':
            result = game.reveal_cell(data['x'], data['y'])
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        
        elif self.path == '/toggle_flag':
            result = game.toggle_flag(data['x'], data['y'])
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"flag_set": result}).encode())
        
        elif self.path == '/new_game':
            width = data.get('width', 5)
            height = data.get('height', 5)
            mines = data.get('mines', 3)
            game.__init__(width, height, mines)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        
        elif self.path == '/process_moves':
            result = game.process_moves()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        elif self.path == '/game.json':
            with open('game.json', 'rb') as f:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(f.read())
            return
        return SimpleHTTPRequestHandler.do_GET(self)

if __name__ == '__main__':
    port = 8000
    print(f"""
    ╔══════════════════════════════════════════════════╗
    ║      🚩 Сапер с JSON ходами (правый клик - флаг)      ║
    ╠══════════════════════════════════════════════════╣
    ║  Открой в браузере: http://localhost:{port}       ║
    ╠══════════════════════════════════════════════════╣
    ║  🖱️ Левый клик - открыть клетку                   ║
    ║  🖱️ Правый клик - поставить/снять флажок 🚩       ║
    ║  ⛔ Клетку с флажком нельзя открыть!              ║
    ╚══════════════════════════════════════════════════╝
    """)
    HTTPServer(('localhost', port), MyHandler).serve_forever()