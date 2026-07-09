import tkinter as tk
import time
import math

# Frecuencias (Hz)
FREQS = {
    "up": 9,
    "right": 11,
    "down": 13,
    "left": 15,
    "select": 7
}

class SSVEPApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SSVEP Interface")
        self.root.configure(bg="black")
        self.root.attributes("-fullscreen", True)

        self.start_time = time.time()

        self.canvas = tk.Canvas(root, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.elements = {}
        self.create_elements()

        self.update_loop()

    def create_elements(self):
        w = self.root.winfo_screenwidth()
        h = self.root.winfo_screenheight()

        size = 60   # MÁS CHICAS
        margin = 20 # MÁS PEGADAS AL BORDE

        # Flecha ARRIBA
        self.elements["up"] = self.canvas.create_polygon(
            w/2, margin,
            w/2 - size, margin + size,
            w/2 + size, margin + size,
            fill="white", outline=""
        )

        # Flecha ABAJO
        self.elements["down"] = self.canvas.create_polygon(
            w/2, h - margin,
            w/2 - size, h - margin - size,
            w/2 + size, h - margin - size,
            fill="white", outline=""
        )

        # Flecha IZQUIERDA
        self.elements["left"] = self.canvas.create_polygon(
            margin, h/2,
            margin + size, h/2 - size,
            margin + size, h/2 + size,
            fill="white", outline=""
        )

        # Flecha DERECHA
        self.elements["right"] = self.canvas.create_polygon(
            w - margin, h/2,
            w - margin - size, h/2 - size,
            w - margin - size, h/2 + size,
            fill="white", outline=""
        )

        # BOTÓN SELECT (arriba izquierda)
        self.elements["select"] = self.canvas.create_oval(
            margin, margin,
            margin + 120, margin + 120,
            fill="white", outline=""
        )

        self.text = self.canvas.create_text(
            margin + 60, margin + 60,
            text="OK",
            fill="black",
            font=("Arial", 18, "bold")
        )

    def update_loop(self):
        t = time.time() - self.start_time

        for key, item in self.elements.items():
            freq = FREQS[key]
            visible = math.sin(2 * math.pi * freq * t) > 0

            color = "white" if visible else "black"
            self.canvas.itemconfig(item, fill=color)

        # Texto inverso para visibilidad
        select_visible = math.sin(2 * math.pi * FREQS["select"] * t) > 0
        self.canvas.itemconfig(self.text, fill="black" if select_visible else "white")

        self.root.after(10, self.update_loop)


if __name__ == "__main__":
    root = tk.Tk()
    app = SSVEPApp(root)
    root.mainloop()