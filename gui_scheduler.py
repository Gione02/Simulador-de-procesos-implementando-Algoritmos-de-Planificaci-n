# Create a dark-themed version of the GUI as a complete, ready-to-run file.
from textwrap import dedent


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI (tema oscuro) para el Simulador de Planificación de Procesos
Algoritmos: FCFS, SJF, SRTF y Round Robin
Requiere: scheduler_sim.py en el mismo directorio.
"""

import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List
from scheduler_sim import Process, Scheduler, TIME_UNIT_SECONDS

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulador de Planificación de Procesos")
        self.geometry("1150x700")
        self.minsize(1000, 650)

        # ---- PALETA / ESTILOS OSCUROS ----
        self.colors = {
            "bg_main": "#1e1e1e",   # fondo ventana
            "bg_frame": "#2b2b2b",  # contenedores/canvas/text
            "fg_text": "#f5f5f5",   # texto
            "muted":   "#cfcfcf",   # texto secundario
            "accent":  "#10a37f",   # verde estilo ChatGPT
            "line":    "#3a3a3a"    # líneas/bordes
        }

        self.configure(bg=self.colors["bg_main"])

        style = ttk.Style(self)
        # usar 'clam' para permitir personalización de colores
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Estilos base ttk
        style.configure("TFrame", background=self.colors["bg_main"])
        style.configure("TLabel", background=self.colors["bg_main"], foreground=self.colors["fg_text"])
        style.configure("TButton", background=self.colors["bg_frame"], foreground=self.colors["fg_text"])
        style.map("TButton", background=[("active", self.colors["accent"])], foreground=[("active", "#ffffff")])
        style.configure("TRadiobutton", background=self.colors["bg_main"], foreground=self.colors["fg_text"])
        style.configure("TCheckbutton", background=self.colors["bg_main"], foreground=self.colors["fg_text"])

        # LabelFrame
        style.configure("TLabelframe", background=self.colors["bg_main"], bordercolor=self.colors["line"])
        style.configure("TLabelframe.Label", background=self.colors["bg_main"], foreground=self.colors["fg_text"])

        # Entry (ttk)
        style.configure("TEntry", fieldbackground=self.colors["bg_frame"], foreground=self.colors["fg_text"])
        # Combobox/Spinbox (si se usaran)
        style.configure("TCombobox", fieldbackground=self.colors["bg_frame"], foreground=self.colors["fg_text"])

        # Treeview (tablas)
        style.configure("Treeview",
                        background=self.colors["bg_frame"],
                        fieldbackground=self.colors["bg_frame"],
                        foreground=self.colors["fg_text"],
                        bordercolor=self.colors["line"])
        style.configure("Treeview.Heading",
                        background=self.colors["bg_main"],
                        foreground=self.colors["fg_text"],
                        bordercolor=self.colors["line"])
        style.map("Treeview",
                  background=[("selected", self.colors["accent"])],
                  foreground=[("selected", "#ffffff")])

        # Widgets clásicos (tk.*)
        self.option_add("*Entry.Background", self.colors["bg_frame"])
        self.option_add("*Entry.Foreground", self.colors["fg_text"])
        self.option_add("*Text.Background", self.colors["bg_frame"])
        self.option_add("*Text.Foreground", self.colors["fg_text"])
        self.option_add("*Text.InsertBackground", self.colors["fg_text"])
        self.option_add("*Text.SelectBackground", self.colors["accent"])
        self.option_add("*Text.SelectForeground", "#ffffff")
        self.option_add("*Canvas.Background", self.colors["bg_frame"])

        # Estado
        self.processes: List[Process] = []
        self.algorithm = tk.StringVar(value="FCFS")
        self.rr_quantum = tk.StringVar(value="2")
        self.real_time = tk.BooleanVar(value=False)

        # --- UI
        self._build_input_frame()
        self._build_table_frame()
        self._build_actions_frame()
        self._build_output_frame()

        self._update_rr_state()

    def _build_input_frame(self):
        frm = ttk.LabelFrame(self, text="Crear proceso")
        frm.pack(side=tk.TOP, fill=tk.X, padx=10, pady=8)

        ttk.Label(frm, text="Nombre:").grid(row=0, column=0, padx=6, pady=6, sticky="e")
        self.ent_name = ttk.Entry(frm, width=18)
        self.ent_name.grid(row=0, column=1, padx=6, pady=6)

        ttk.Label(frm, text="Tiempo CPU:").grid(row=0, column=2, padx=6, pady=6, sticky="e")
        self.ent_burst = ttk.Entry(frm, width=8)
        self.ent_burst.grid(row=0, column=3, padx=6, pady=6)

        ttk.Label(frm, text="Llegada:").grid(row=0, column=4, padx=6, pady=6, sticky="e")
        self.ent_arrival = ttk.Entry(frm, width=8)
        self.ent_arrival.grid(row=0, column=5, padx=6, pady=6)

        ttk.Label(frm, text="Quantum (opcional, solo RR):").grid(row=0, column=6, padx=6, pady=6, sticky="e")
        self.ent_quantum = ttk.Entry(frm, width=8)
        self.ent_quantum.grid(row=0, column=7, padx=6, pady=6)

        btn_add = ttk.Button(frm, text="Agregar proceso", command=self.add_process)
        btn_add.grid(row=0, column=8, padx=8, pady=6)

        for i in range(9):
            frm.grid_columnconfigure(i, weight=0)

    def _build_table_frame(self):
        frm = ttk.LabelFrame(self, text="Cola de procesos (pendientes)")
        frm.pack(side=tk.TOP, fill=tk.X, padx=10, pady=8)

        cols = ("pid", "name", "arrival", "burst", "qproc")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=6)
        self.tree.heading("pid", text="PID")
        self.tree.heading("name", text="Nombre")
        self.tree.heading("arrival", text="Llegada")
        self.tree.heading("burst", text="CPU")
        self.tree.heading("qproc", text="Quantum propio")
        for c in cols:
            self.tree.column(c, width=120 if c != "name" else 180, anchor="center")
        self.tree.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8,0), pady=6)

        sb = ttk.Scrollbar(frm, orient="vertical", command=self.tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscroll=sb.set)

    def _build_actions_frame(self):
        frm = ttk.LabelFrame(self, text="Algoritmo y simulación")
        frm.pack(side=tk.TOP, fill=tk.X, padx=10, pady=8)

        # Algoritmos
        algof = ttk.Frame(frm)
        algof.pack(side=tk.LEFT, padx=8, pady=6)
        ttk.Label(algof, text="Algoritmo:").grid(row=0, column=0, padx=4, pady=2, sticky="w")
        ttk.Radiobutton(algof, text="FCFS", variable=self.algorithm, value="FCFS", command=self._update_rr_state).grid(row=0, column=1, padx=4, pady=2)
        ttk.Radiobutton(algof, text="SJF (no expropiativo)", variable=self.algorithm, value="SJF", command=self._update_rr_state).grid(row=0, column=2, padx=4, pady=2)
        ttk.Radiobutton(algof, text="SRTF (expropiativo)", variable=self.algorithm, value="SRTF", command=self._update_rr_state).grid(row=0, column=3, padx=4, pady=2)
        ttk.Radiobutton(algof, text="Round Robin", variable=self.algorithm, value="RR", command=self._update_rr_state).grid(row=0, column=4, padx=4, pady=2)

        # Quantum global (solo RR)
        qf = ttk.Frame(frm)
        qf.pack(side=tk.LEFT, padx=18, pady=6)
        ttk.Label(qf, text="Quantum global (RR):").grid(row=0, column=0, padx=6, pady=2, sticky="e")
        self.ent_rr_quantum = ttk.Entry(qf, width=6, textvariable=self.rr_quantum)
        self.ent_rr_quantum.grid(row=0, column=1, padx=6, pady=2)

        # Tiempo real
        tf = ttk.Frame(frm)
        tf.pack(side=tk.LEFT, padx=18, pady=6)
        ttk.Checkbutton(tf, text=f"Tiempo real ({TIME_UNIT_SECONDS}s por unidad)", variable=self.real_time).grid(row=0, column=0, padx=6, pady=2)

        # Botones
        bf = ttk.Frame(frm)
        bf.pack(side=tk.RIGHT, padx=8, pady=6)
        ttk.Button(bf, text="Limpiar", command=self.clear_all).grid(row=0, column=0, padx=6)
        ttk.Button(bf, text="Iniciar simulación", command=self.start_simulation).grid(row=0, column=1, padx=6)

    def _build_output_frame(self):
        frm = ttk.LabelFrame(self, text="Ejecución y resultados")
        frm.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=8)

        # Panel izquierdo: Timeline (texto) + Resultados (tabla)
        left = ttk.Frame(frm)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6,3), pady=6)

        ttk.Label(left, text="Línea de tiempo:").pack(anchor="w")
        self.txt_timeline = tk.Text(left, height=14, relief="flat",
                                    bg=self.colors["bg_frame"], fg=self.colors["fg_text"],
                                    insertbackground=self.colors["fg_text"],
                                    selectbackground=self.colors["accent"])
        self.txt_timeline.pack(fill=tk.BOTH, expand=False, pady=(0,8))

        ttk.Label(left, text="Procesos terminados:").pack(anchor="w")
        cols = ("pid","name","arrival","burst","start","finish","wait","turn","resp")
        self.tree_done = ttk.Treeview(left, columns=cols, show="headings", height=8)
        headers = ["PID","Nombre","Llegada","CPU","Inicio","Fin","Espera","Retorno","Respuesta"]
        for c,h in zip(cols,headers):
            self.tree_done.heading(c, text=h)
            self.tree_done.column(c, width=90 if c!="name" else 140, anchor="center")
        self.tree_done.pack(fill=tk.BOTH, expand=True)

        # Panel derecho: Gantt (canvas) + métricas
        right = ttk.Frame(frm)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(3,6), pady=6)

        ttk.Label(right, text="Gantt:").pack(anchor="w")
        self.canvas = tk.Canvas(right, bg=self.colors["bg_frame"], height=240, highlightthickness=0)
        self.canvas.pack(fill=tk.X, expand=False, pady=(0,8))

        self.lbl_metrics = ttk.Label(right, text="Métricas:")
        self.lbl_metrics.pack(anchor="w")

    # ----------------- Lógica de UI -----------------
    def _update_rr_state(self):
        is_rr = self.algorithm.get() == "RR"
        state = "normal" if is_rr else "disabled"
        self.ent_rr_quantum.config(state=state)

    def add_process(self):
        name = self.ent_name.get().strip()
        if not name:
            messagebox.showwarning("Validación", "Indique un nombre.")
            return
        try:
            burst = int(self.ent_burst.get().strip())
            arrival = int(self.ent_arrival.get().strip())
        except ValueError:
            messagebox.showwarning("Validación", "CPU y Llegada deben ser enteros.")
            return
        q_text = self.ent_quantum.get().strip()
        qproc = int(q_text) if q_text else None

        try:
            p = Process(name=name, burst_time=burst, arrival_time=arrival, quantum=qproc)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self.processes.append(p)
        self.tree.insert("", "end", values=(p.pid, p.name, p.arrival_time, p.burst_time, p.quantum if p.quantum is not None else ""))

        # Limpiar inputs
        self.ent_name.delete(0, tk.END)
        self.ent_burst.delete(0, tk.END)
        self.ent_arrival.delete(0, tk.END)
        self.ent_quantum.delete(0, tk.END)

    def clear_all(self):
        self.processes.clear()
        for t in (self.tree, self.tree_done):
            for item in t.get_children():
                t.delete(item)
        self.txt_timeline.delete("1.0", tk.END)
        self.canvas.delete("all")
        self.lbl_metrics.config(text="Métricas:")

    def start_simulation(self):
        if not self.processes:
            messagebox.showwarning("Validación", "Agregue al menos un proceso.")
            return
        algo = self.algorithm.get()
        rr_q = None
        if algo == "RR":
            try:
                rr_q = int(self.rr_quantum.get().strip())
                if rr_q <= 0:
                    raise ValueError
            except Exception:
                messagebox.showwarning("Validación", "Quantum global (RR) debe ser entero > 0.")
                return

        # Preparar simulador
        sim = Scheduler(self.processes, algorithm=algo, rr_quantum=rr_q, real_time=self.real_time.get())

        # Si es tiempo real, corremos en hilo para no bloquear la GUI
        if self.real_time.get():
            q = queue.Queue()

            def run_rt():
                sim.simulate()  # dormirá 5s por unidad
                q.put("done")

            def poll_queue():
                self._render_timeline(sim)
                if not q.empty():
                    _ = q.get()
                    self._render_all(sim)
                else:
                    self.after(500, poll_queue)

            threading.Thread(target=run_rt, daemon=True).start()
            poll_queue()
        else:
            sim.simulate()
            self._render_all(sim)

    # ---- Renderizado en UI ----
    def _render_all(self, sim: Scheduler):
        self._render_timeline(sim)
        self._render_results(sim)
        self._render_metrics(sim)
        self._render_gantt(sim)

    def _render_timeline(self, sim: Scheduler):
        self.txt_timeline.delete("1.0", tk.END)
        self.txt_timeline.insert(tk.END, "t  | RUN | READY       | DONE\n")
        self.txt_timeline.insert(tk.END, "---+-----+------------+-----------------\n")
        for t, run, ready, done in sim.timeline:
            self.txt_timeline.insert(tk.END, f"{t:>2} | {str(run) if run is not None else '-':>3} | {ready!r:<10} | {done!r}\n")

    def _render_results(self, sim: Scheduler):
        for item in self.tree_done.get_children():
            self.tree_done.delete(item)
        by_pid = sorted(sim.finished, key=lambda p: p.pid)
        for p in by_pid:
            self.tree_done.insert("", "end", values=(
                p.pid, p.name, p.arrival_time, p.burst_time,
                p.start_time, p.completion_time, p.waiting_time, p.turnaround_time, p.response_time
            ))

    def _render_metrics(self, sim: Scheduler):
        m = sim._compute_metrics()
        txt = (f"Métricas:\n"
               f"  - Espera promedio: {m['avg_waiting']:.2f} unidades\n"
               f"  - Retorno promedio: {m['avg_turnaround']:.2f} unidades\n"
               f"  - Respuesta promedio: {m['avg_response']:.2f} unidades\n"
               f"  - Unidad de tiempo = {TIME_UNIT_SECONDS} s")
        self.lbl_metrics.config(text=txt)

    def _render_gantt(self, sim: Scheduler):
        self.canvas.delete("all")
        timeline = sim.timeline
        if not timeline:
            return
        # Parámetros
        h = 40
        pad = 10
        w_unit = 28  # ancho por tick
        y = 20
        x = pad
        # Bloques
        for idx, (t, run, *_ ) in enumerate(timeline):
            self.canvas.create_rectangle(x, y, x+w_unit, y+h, outline=self.colors["line"], width=1, fill=self.colors["bg_main"])
            self.canvas.create_text(x+w_unit/2, y+h/2, text=str(run) if run is not None else "-", font=("Arial", 10), fill=self.colors["fg_text"])
            # marca de tiempo
            self.canvas.create_text(x+w_unit/2, y+h+12, text=str(t), font=("Arial", 9), fill=self.colors["muted"])
            x += w_unit
        # título
        self.canvas.create_text(10, 10, anchor="w", text="PID ejecutado por unidad de tiempo", font=("Arial", 10, "bold"), fill=self.colors["fg_text"])

if __name__ == "__main__":
    app = App()
    app.mainloop()
