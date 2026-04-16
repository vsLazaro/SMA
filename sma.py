
import random

QUEUES = [
    {
        "servidores":    2,
        "capacidade":    3,
        "atend_min":     3.0,
        "atend_max":     4.0,
        "chegada_min":   1.0,
        "chegada_max":   4.0,
        "primeiro_cliente": 1.5,
    },
    {
        "servidores":    1,
        "capacidade":    5,
        "atend_min":     2.0,
        "atend_max":     3.0,
        "chegada_min":   None,
        "chegada_max":   None,
        "primeiro_cliente": None,
    },
]

ROUTING = [
    [0.0, 1.0],
    [0.0, 0.0],
]

MAX_RANDOMS = 100_000   

_lcg_a        = 123
_lcg_c        = 571
_lcg_M        = 59
_lcg_previous = 2378917
_randoms_used = 0


def next_random() -> float:
    global _lcg_previous, _randoms_used
    _randoms_used += 1
    _lcg_previous = ((_lcg_a * _lcg_previous) + _lcg_c) % _lcg_M
    return _lcg_previous / _lcg_M

def uniform(lo: float, hi: float) -> float:
    return lo + (hi - lo) * next_random()

def randoms_exhausted() -> bool:
    return _randoms_used >= MAX_RANDOMS

class Queue:
    def __init__(self, qid: int, cfg: dict):
        self.qid        = qid
        self.servers    = cfg["servidores"]
        self.capacity   = cfg["capacidade"]
        self.atend_min  = cfg["atend_min"]
        self.atend_max  = cfg["atend_max"]
        self.arr_min    = cfg.get("chegada_min")
        self.arr_max    = cfg.get("chegada_max")
        self.first_arr  = cfg.get("primeiro_cliente")

        self.status     = 0
        self.losses     = 0
        self.acc_time   = [0.0] * (self.capacity + 1)

    def is_full(self):
        return self.status >= self.capacity

    def enter(self):
        self.status += 1

    def leave(self):
        self.status -= 1

    def in_service(self):
        return min(self.status, self.servers)

    def service_time(self) -> float:
        return uniform(self.atend_min, self.atend_max)

    def interarrival_time(self) -> float:
        return uniform(self.arr_min, self.arr_max)

scheduler = []

def sched_add(tipo: str, tempo: float, fila: int):
    scheduler.append({"tipo": tipo, "tempo": tempo, "fila": fila})

def sched_next() -> dict:
    ev = min(scheduler, key=lambda e: e["tempo"])
    scheduler.remove(ev)
    return ev

TG = 0.0

def acumula_tempo(queues: list, novo_tempo: float):
    global TG
    delta = novo_tempo - TG
    for q in queues:
        q.acc_time[q.status] += delta
    TG = novo_tempo

def route_client(from_qid: int, queues: list):
    r = next_random()
    if randoms_exhausted():
        return None

    cumulative = 0.0
    row = ROUTING[from_qid]
    for dest, prob in enumerate(row):
        cumulative += prob
        if r < cumulative:
            return dest
    return None

def handle_arrival(ev: dict, queues: list):
    qid = ev["fila"]
    q   = queues[qid]

    acumula_tempo(queues, ev["tempo"])

    if randoms_exhausted():
        return

    if not q.is_full():
        q.enter()
        if q.status <= q.servers:
            if not randoms_exhausted():
                sched_add("saida", TG + q.service_time(), qid)
    else:
        q.losses += 1
    if ev.get("externo", False) and not randoms_exhausted():
        sched_add("chegada_ext", TG + q.interarrival_time(), qid)


def handle_departure(ev: dict, queues: list):
    qid = ev["fila"]
    q   = queues[qid]

    acumula_tempo(queues, ev["tempo"])

    q.leave()

    if q.status >= q.servers and not randoms_exhausted():
        sched_add("saida", TG + q.service_time(), qid)

    if not randoms_exhausted():
        dest = route_client(qid, queues)
        if dest is not None and not randoms_exhausted():
            sched_add("chegada_int", TG, dest)

def run():
    global TG

    queues = [Queue(i, cfg) for i, cfg in enumerate(QUEUES)]

    for q in queues:
        if q.first_arr is not None:
            sched_add("chegada_ext", q.first_arr, q.qid)

    while scheduler and not randoms_exhausted():
        ev = sched_next()

        if ev["tipo"] in ("chegada_ext", "chegada_int"):
            ev["externo"] = (ev["tipo"] == "chegada_ext")
            handle_arrival(ev, queues)
        elif ev["tipo"] == "saida":
            handle_departure(ev, queues)

    print("=" * 60)
    print("  RESULTADO DA SIMULAÇÃO - REDE DE FILAS EM TANDEM")
    print("=" * 60)
    print(f"\nAleatórios utilizados : {_randoms_used}")
    print(f"Tempo global (TG)     : {TG:.4f}\n")

    for q in queues:
        print(f"─── Fila {q.qid + 1}  (G/G/{q.servers}/{q.capacity}) ───")
        print(f"  Perdas : {q.losses}")
        print(f"  {'Estado':<8} {'Tempo Acumulado':>18} {'Probabilidade':>15}")
        for estado, t in enumerate(q.acc_time):
            prob = (t / TG * 100) if TG > 0 else 0.0
            print(f"  {estado:<8} {t:>18.4f} {prob:>14.2f}%")
        print()

    print("=" * 60)


if __name__ == "__main__":
    run()