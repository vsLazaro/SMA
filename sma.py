a = 1664525
c = 1013904223
M = 4294967296
previous = 12345

count = 100000
tipo_chegada = "chegada"
tipo_saida = "saida"

TG = 0
status_fila = 0
capacidade_fila = 5
servidores_fila = 1 //altera aqui o número de servidores
perdas_fila = 0
escalonador = []
tempos_acumulados = [0.0] * (capacidade_fila + 1)

def NextRandom():
    global previous, count
    count -= 1
    previous = ((a * previous) + c) % M
    return previous / M

def NextEvent():
    evento_proximo = min(escalonador, key=lambda e: e["tempo"])
    escalonador.remove(evento_proximo)
    return evento_proximo
    
def AcumulaTempo(ev):
    global TG
    tempo_decorrido = ev - TG
    tempos_acumulados[status_fila] += tempo_decorrido
    TG = ev

def Fila_Status():
    return status_fila

def Fila_Capacity():
    return capacidade_fila

def Fila_In():
    global status_fila
    status_fila += 1

def Fila_Servers():
    return servidores_fila

def Fila_Loss():
    global perdas_fila
    perdas_fila += 1

def Escalonador_Add(tipo, tempo):
    escalonador.append({"tipo": tipo, "tempo": tempo})

def SA(min_val, max_val):
    return min_val + (max_val - min_val) * NextRandom()

def CH(min_val, max_val):
    return min_val + (max_val - min_val) * NextRandom()

def CHEGADA(ev):
    AcumulaTempo(ev)
    
    if Fila_Status() < Fila_Capacity():
        Fila_In()
        
        if Fila_Status() <= Fila_Servers():
            Escalonador_Add(tipo_saida, TG + SA(3, 5))
    else:
        Fila_Loss()
        
    Escalonador_Add(tipo_chegada, TG + CH(2, 5))

def Fila_Out():
    global status_fila
    status_fila -= 1

def SAIDA(ev):
    AcumulaTempo(ev)
    Fila_Out()
    
    if Fila_Status() >= Fila_Servers():
        Escalonador_Add(tipo_saida, TG + SA(3, 5))

Escalonador_Add(tipo_chegada, 2.0)

while count > 0:
    evento = NextEvent()

    if evento["tipo"] == tipo_chegada:
        CHEGADA(evento["tempo"])
    elif evento["tipo"] == tipo_saida:
        SAIDA(evento["tempo"])

for i in range(capacidade_fila + 1):
    probabilidade = (tempos_acumulados[i] / TG) * 100
    print(f"Estado {i}: {tempos_acumulados[i]:.4f} ({probabilidade:.2f}%)")

print(f"Perdas: {perdas_fila}")
print(f"Tempo Global: {TG:.4f}")