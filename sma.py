import sys
import yaml

class LCG:
    A = 25214903917
    C = 11
    M = 281474976710656  # 2^48

    def __init__(self, seed: int, limit: int):
        self.x     = seed
        self.limit = limit
        self.count = 0

    def has_next(self) -> bool:
        return self.count < self.limit

    def next(self) -> float:
        if not self.has_next():
            raise StopIteration("Acabou os números aleatórios!")
        self.x = (self.A * self.x + self.C) % self.M
        self.count += 1
        return self.x / self.M

class Queue:
    def __init__(self, qid: str, servers: int, capacity,
                 min_arrival, max_arrival, min_service, max_service):
        self.id          = qid
        self.servers     = servers
        self.capacity    = capacity
        self.min_arrival = min_arrival
        self.max_arrival = max_arrival
        self.min_service = min_service
        self.max_service = max_service

        self.status  = 0
        self.losses  = 0
        self.acc     = [0.0]  # acc[n] = tempo acumulado com n clientes

    def is_full(self) -> bool:
        return self.capacity is not None and self.status >= self.capacity

    def enter(self):
        self.status += 1
        while self.status >= len(self.acc):
            self.acc.append(0.0)

    def leave(self):
        self.status -= 1

    def service_time(self, rng: LCG) -> float:
        return self.min_service + (self.max_service - self.min_service) * rng.next()

    def interarrival(self, rng: LCG) -> float:
        return self.min_arrival + (self.max_arrival - self.min_arrival) * rng.next()

    def label(self) -> str:
        cap = str(self.capacity) if self.capacity is not None else "inf"
        return f"G/G/{self.servers}/{cap}"

def build_routing(network: list, queues: dict) -> dict:
    table = {q: [] for q in queues}
    for entry in (network or []):
        src, tgt, prob = entry["source"], entry["target"], float(entry["probability"])
        table[src].append((tgt, prob))

    result = {}
    for src, destinos in table.items():
        acc, cum = [], 0.0
        for tgt, prob in destinos:
            cum += prob
            acc.append((tgt, cum))
        result[src] = acc
    return result


def route(qid: str, routing: dict, rng: LCG):
    destinos = routing.get(qid, [])
    if not destinos:
        return None
    if len(destinos) == 1 and destinos[0][1] == 1.0:
        return destinos[0][0]
    r = rng.next()
    for tgt, cum in destinos:
        if r < cum:
            return tgt
    return None   # sai do sistema

class Scheduler:
    def __init__(self):
        self._events = []

    def add(self, tipo: str, tempo: float, qid: str, externo: bool = False):
        self._events.append({"tipo": tipo, "tempo": tempo, "qid": qid, "externo": externo})

    def pop_next(self) -> dict:
        ev = min(self._events, key=lambda e: e["tempo"])
        self._events.remove(ev)
        return ev

    def empty(self) -> bool:
        return len(self._events) == 0

def simulate(queues: dict, routing: dict, arrivals: dict,
             rng: LCG) -> float:
    sched = Scheduler()
    tg    = 0.0

    def acumula(novo_t):
        nonlocal tg
        delta = novo_t - tg
        for q in queues.values():
            while q.status >= len(q.acc):
                q.acc.append(0.0)
            q.acc[q.status] += delta
        tg = novo_t

    for qid, t_inicial in arrivals.items():
        sched.add("chegada", t_inicial, qid, externo=True)

    while not sched.empty() and rng.has_next():
        ev = sched.pop_next()
        tipo, tempo, qid = ev["tipo"], ev["tempo"], ev["qid"]
        externo = ev.get("externo", False)
        q = queues[qid]

        acumula(tempo)

        if tipo == "chegada":
            if not q.is_full():
                q.enter()
                if q.status <= q.servers and rng.has_next():
                    sched.add("saida", tg + q.service_time(rng), qid)
            else:
                q.losses += 1
            if externo and rng.has_next():
                sched.add("chegada", tg + q.interarrival(rng), qid, externo=True)

        elif tipo == "saida":
            q.leave()
            if q.status >= q.servers and rng.has_next():
                sched.add("saida", tg + q.service_time(rng), qid)
            if rng.has_next():
                dest = route(qid, routing, rng)
                if dest is not None and rng.has_next():
                    sched.add("chegada", tg, dest, externo=False)

    return tg

def report(queues: dict, tg: float, rng: LCG):
    sep = "=" * 62
    print(sep)
    print("   QUEUEING NETWORK SIMULATOR — RESULTADO")
    print(sep)
    print(f"\n  Aleatórios utilizados : {rng.count}")
    print(f"  Tempo global (TG)     : {tg:.4f}\n")

    for qid, q in queues.items():
        print(f"  {'*'*58}")
        arr = ""
        if q.min_arrival is not None:
            arr = f"\n  Chegadas: {q.min_arrival} ... {q.max_arrival}"
        print(f"  Fila: {qid} ({q.label()}){arr}")
        print(f"  Atendimento: {q.min_service} ... {q.max_service}")
        print(f"  {'*'*58}")
        print(f"  {'Estado':>7}   {'Tempo Acumulado':>18}   {'Probabilidade':>13}")
        for estado, t in enumerate(q.acc):
            prob = (t / tg * 100) if tg > 0 else 0.0
            print(f"  {estado:>7}   {t:>18.4f}   {prob:>12.2f}%")
        print(f"\n  Perdas: {q.losses}\n")

    print(sep)
    print(f"  Simulation average time: {tg:.4f}")
    print(sep)


def load_model(path: str):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    # Remove a diretiva !PARAMETERS do JAR (não é YAML padrão)
    raw = "\n".join(l for l in raw.splitlines() if not l.startswith("!"))
    cfg = yaml.safe_load(raw)

    queues_cfg = cfg.get("queues", {})
    arrivals   = {k: float(v) for k, v in (cfg.get("arrivals") or {}).items()}
    network    = cfg.get("network") or []
    seeds      = cfg.get("seeds") or []
    limit      = int(cfg.get("rndnumbersPerSeed") or 100000)

    queues = {}
    for qid, qcfg in queues_cfg.items():
        cap = qcfg.get("capacity") or qcfg.get("populacaoMax")
        queues[qid] = Queue(
            qid       = qid,
            servers   = int(qcfg.get("servers", 1)),
            capacity  = int(cap) if cap else None,
            min_arrival = float(qcfg["minArrival"]) if "minArrival" in qcfg else None,
            max_arrival = float(qcfg["maxArrival"]) if "maxArrival" in qcfg else None,
            min_service = float(qcfg["minService"]),
            max_service = float(qcfg["maxService"]),
        )

    routing = build_routing(network, queues)
    return queues, routing, arrivals, seeds, limit

def help_msg():
    print("Uso:   python simulator.py run <model.yml>")
    print("       python simulator.py example")

def main():
    args = sys.argv[1:]
    if not args:
        help_msg(); return

    if args[0] == "example":
        example = """# Exemplo: rede de 3 filas (modelo da etapa 3)
arrivals:
  Q1: 2.0

queues:
  Q1:
    servers: 1
    minArrival: 2.0
    maxArrival: 4.0
    minService: 1.0
    maxService: 2.0
  Q2:
    servers: 2
    capacity: 5
    minService: 4.0
    maxService: 6.0
  Q3:
    servers: 2
    capacity: 10
    minService: 5.0
    maxService: 15.0

network:
- source: Q1
  target: Q2
  probability: 0.8
- source: Q1
  target: Q3
  probability: 0.2
- source: Q2
  target: Q2
  probability: 0.3
- source: Q2
  target: Q3
  probability: 0.5
- source: Q3
  target: Q1
  probability: 0.7

rndnumbersPerSeed: 100000
seeds:
- 1
"""
        with open("model.yml", "w") as f:
            f.write(example)
        print("Arquivo 'model.yml' criado com sucesso!")
        return

    if args[0] == "run" and len(args) >= 2:
        path = args[1]
        try:
            queues, routing, arrivals, seeds, limit = load_model(path)
        except FileNotFoundError:
            print(f"ERRO: arquivo '{path}' não encontrado.")
            sys.exit(1)

        seed_list = seeds if seeds else [1]
        for i, seed in enumerate(seed_list, 1):
            print(f"\nSimulation: #{i}")
            print(f"...simulating with random numbers (seed '{seed}')...")
            # Reinicia estado das filas para cada seed
            for q in queues.values():
                q.status = 0
                q.losses = 0
                q.acc    = [0.0]
            rng = LCG(seed=int(seed), limit=limit)
            tg  = simulate(queues, routing, arrivals, rng)
            report(queues, tg, rng)
        return

    help_msg()


if __name__ == "__main__":
    main()