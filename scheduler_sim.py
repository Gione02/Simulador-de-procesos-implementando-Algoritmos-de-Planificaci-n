# scheduler_sim.py
from dataclasses import dataclass, field
from typing import List, Optional, Deque, Dict, Tuple
from collections import deque
import itertools, time

TIME_UNIT_SECONDS = 5
_pid_counter = itertools.count(1)

@dataclass(order=True)
class Process:
    sort_index: int = field(init=False, repr=False)
    name: str
    burst_time: int
    arrival_time: int
    quantum: Optional[int] = None
    pid: int = field(default_factory=lambda: next(_pid_counter), compare=False)
    remaining_time: int = field(init=False, compare=False)
    start_time: Optional[int] = field(default=None, compare=False)
    completion_time: Optional[int] = field(default=None, compare=False)
    response_time: Optional[int] = field(default=None, compare=False)
    waiting_time: Optional[int] = field(default=None, compare=False)
    turnaround_time: Optional[int] = field(default=None, compare=False)
    _rr_slice_left: Optional[int] = field(default=None, compare=False)

    def __post_init__(self):
        self.remaining_time = self.burst_time
        self.sort_index = self.arrival_time

    def clone_for_sim(self):
        return Process(
            name=self.name, burst_time=self.burst_time,
            arrival_time=self.arrival_time, quantum=self.quantum
        )

class Scheduler:
    def __init__(self, processes: List[Process], algorithm: str, rr_quantum: Optional[int] = None, real_time: bool = False):
        algo = algorithm.upper()
        if algo not in {"FCFS","SJF","SRTF","RR"}:
            raise ValueError("Algoritmo inválido")
        if algo=="RR" and rr_quantum is None:
            raise ValueError("Round Robin requiere quantum")
        self.processes = sorted([p.clone_for_sim() for p in processes], key=lambda x: x.arrival_time)
        self.algorithm = algo
        self.rr_quantum = rr_quantum
        self.real_time = real_time
        self.time = 0
        self.ready: Deque[Process] = deque()
        self.running: Optional[Process] = None
        self.finished: List[Process] = []
        self.timeline: List[Tuple[int, Optional[int], List[int], List[int]]] = []

    def _select_next_fcfs(self):
        return self.ready.popleft() if self.ready else None
    def _select_next_sjf(self):
        if not self.ready: return None
        best_idx = min(range(len(self.ready)), key=lambda i: self.ready[i].burst_time)
        self.ready.rotate(-best_idx)
        chosen = self.ready.popleft()
        self.ready.rotate(best_idx)
        return chosen
    def _select_next_srtf(self):
        candidates = list(self.ready)
        if self.running: candidates.append(self.running)
        if not candidates: return None
        best = min(candidates, key=lambda p: p.remaining_time)
        if self.running is best: return self.running
        if best in self.ready: self.ready.remove(best)
        if self.running: self.ready.append(self.running)
        return best
    def _select_next_rr(self):
        return self.ready.popleft() if self.ready else None

    def _start_if_needed(self,p):
        if p.start_time is None:
            p.start_time = self.time
            p.response_time = self.time - p.arrival_time
    def _complete(self,p):
        p.completion_time = self.time+1
        p.turnaround_time = p.completion_time - p.arrival_time
        p.waiting_time = p.turnaround_time - p.burst_time
        self.finished.append(p)
        self.running = None
    def _snapshot(self):
        self.timeline.append((self.time, self.running.pid if self.running else None,
                              [p.pid for p in self.ready],
                              [p.pid for p in self.finished]))
    def simulate(self,max_time=None):
        admitted=set()
        while len(self.finished)<len(self.processes) and (max_time is None or self.time<max_time):
            for p in self.processes:
                if p.arrival_time==self.time and p.pid not in admitted:
                    admitted.add(p.pid)
                    self.ready.append(p)
            if self.algorithm=="FCFS" and self.running is None:
                self.running=self._select_next_fcfs()
            elif self.algorithm=="SJF" and self.running is None:
                self.running=self._select_next_sjf()
            elif self.algorithm=="SRTF":
                self.running=self._select_next_srtf()
            elif self.algorithm=="RR" and self.running is None:
                self.running=self._select_next_rr()
                if self.running and self.running._rr_slice_left is None:
                    q=self.running.quantum or self.rr_quantum
                    self.running._rr_slice_left=q
            if self.running:
                self._start_if_needed(self.running)
                self.running.remaining_time-=1
                if self.algorithm=="RR":
                    self.running._rr_slice_left-=1
            self._snapshot()
            if self.real_time: time.sleep(TIME_UNIT_SECONDS)
            if self.running:
                if self.running.remaining_time==0:
                    self._complete(self.running)
                elif self.algorithm=="RR" and self.running._rr_slice_left==0:
                    r=self.running; self.running=None
                    r._rr_slice_left=r.quantum or self.rr_quantum
                    self.ready.append(r)
            self.time+=1
        return self._compute_metrics()
    def _compute_metrics(self):
        n=len(self.processes)
        avg_wait=sum(p.waiting_time for p in self.finished)/n
        avg_turn=sum(p.turnaround_time for p in self.finished)/n
        avg_resp=sum(p.response_time for p in self.finished)/n
        return {"avg_waiting":avg_wait,"avg_turnaround":avg_turn,"avg_response":avg_resp}
