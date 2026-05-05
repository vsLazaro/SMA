# SMA — Simulador de Rede de Filas

## Requisitos

- Python 3.8+
- PyYAML

```bash
pip install pyyaml
```

---

## Como rodar

```bash
python sma.py run model.yml
```

---

## Estrutura do `model.yml`

```yaml
arrivals:
  Q1: 2.0          # tempo da primeira chegada externa

queues:
  Q1:
    servers: 1
    minArrival: 2.0
    maxArrival: 4.0
    minService: 1.0
    maxService: 2.0
  Q2:
    servers: 2
    capacity: 5     # omitir = capacidade infinita
    minService: 4.0
    maxService: 6.0

network:
- source: Q1
  target: Q2
  probability: 0.8  # 20% restante sai do sistema
- source: Q2
  target: Q2
  probability: 0.3  # self-loop

rndnumbersPerSeed: 100000
seeds:
- 1
```

---

## Saída

Para cada fila é reportado:

- Tipo (G/G/servidores/capacidade)
- Tempo acumulado e probabilidade por estado
- Número de perdas
- Tempo global da simulação (TG)