import json
import random
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

class SaperGame:
    def __init__(self):
        self.W, self.H, self.MINES = 5, 5, 3
        self.table = []
        self.revealed = []
        self.init_game()
    
    def init_game(self):
        # Создаём поле
        self.table = [[0]*self.W for _ in range(self.H)]
        mines = random.sample([(x,y) for x in range(self.W) for y in range(self.H)], self.MINES)
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
        print("✅ Создано новое поле и сохранено в game.json")
    
    def save_game_json(self):
        with open("game.json", "w", encoding="utf-8") as f:
            json.dump({
                "table": self.table,
                "revealed": self.revealed,
                "width": self.W,
                "height": self.H
            }, f, indent=2)
    
    def process_moves(self, moves_file="moves.json"):
        if not os.path.exists(moves_file):
            return {"error": f"{moves_file} не найден"}
        
        with open(moves_file, "r", encoding="utf-8") as f:
            moves_data = json.load(f)
        
        moves = moves_data.get("moves", [])
        if not moves:
            return {"error": "Нет ходов"}
        
        # Загружаем текущее поле
        with open("game.json", "r") as f:
            saved = json.load(f)
        table = saved["table"]
        revealed = saved["revealed"]
        
        game_over = False
        won = False
        results = []
        
        for i, (x,y) in enumerate(moves, 1):
            if game_over or won:
                break
            if not (0<=x<self.W and 0<=y<self.H):
                results.append(f"Ход {i}: ({x},{y}) - неверные координаты")
                continue
            if revealed[y][x]:
                results.append(f"Ход {i}: ({x},{y}) - уже открыта")
                continue
            if table[y][x] == -1:
                results.append(f"Ход {i}: ({x},{y}) 💥 МИНА! Игра окончена")
                game_over = True
                break
            revealed[y][x] = True
            results.append(f"Ход {i}: ({x},{y}) ✅ открыто, число {table[y][x]}")
            
            # Проверка победы
            unrevealed = sum(1 for yy in range(self.H) for xx in range(self.W) 
                           if table[yy][xx] != -1 and not revealed[yy][xx])
            if unrevealed == 0:
                won = True
                results.append("🎉 ПОБЕДА!")
                break
        
        # Сохраняем результат
        result = {
            "results": results,
            "game_over": game_over,
            "won": won,
            "final_revealed": revealed
        }
        with open("result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        return result

# Создаём игру при запуске
game = SaperGame()

# Кастомный обработчик для API
class MyHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/process_moves':
            result = game.process_moves()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        elif self.path == '/new_game':
            game.init_game()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        return SimpleHTTPRequestHandler.do_GET(self)

# Запуск сервера
if __name__ == '__main__':
    port = 8000
    print(f"""
    ╔══════════════════════════════════════╗
    ║   🚩 Сапер с JSON ходами запущен!    ║
    ╠══════════════════════════════════════╣
    ║  Открой в браузере:                  ║
    ║  http://localhost:{port}              ║
    ╠══════════════════════════════════════╣
    ║  1. Нажимай на клетки                ║
    ║  2. Сохрани ходы в moves.json        ║
    ║  3. Нажми "Обработать ходы"          ║
    ║  4. Смотри результат в result.json   ║
    ╚══════════════════════════════════════╝
    """)
    HTTPServer(('localhost', port), MyHandler).serve_forever()