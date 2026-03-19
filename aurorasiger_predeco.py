import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import IsolationForest


def carregar_dataset(caminho_csv):
    return pd.read_csv(caminho_csv)


def linha_para_telemetria(row):
    return {
        "timestamp": row["timestamp"],
        "temperatura_interna": row["internal_temp_c"],
        "temperatura_externa": row["external_temp_c"],
        "tensao_bateria": row["battery_voltage_v"],
        "corrente_bateria": row["battery_current_a"],
        "nivel_energia": row["battery_soc_percent"],
        "capacidade_bateria_ah": row["battery_capacity_ah"],
        "energia_disponivel_kwh": row["energy_available_kwh"],
        "carga_kw": row["power_load_kw"],
        "perdas_energeticas": row["energy_loss_percent"],
        "pressao_tanques": row["tank_pressure_bar"],
        "integridade_estrutural": row["structural_integrity"],
        "status_modulos_criticos": row["critical_modules_status"],
        "status_link_telemetria": row["telemetry_link_status"],
        "autonomia_estimada_dataset_min": row["estimated_autonomy_min"],
        "decisao_dataset": row["launch_decision"],
    }


def verificar_decolagem(dados):
    falhas = []

    if not (20 <= dados["temperatura_interna"] <= 32):
        falhas.append("Temperatura interna fora da faixa segura.")

    if not (0 <= dados["temperatura_externa"] <= 28):
        falhas.append("Temperatura externa fora da faixa segura.")

    if not (47 <= dados["tensao_bateria"] <= 51.5):
        falhas.append("Tensão da bateria fora da faixa segura.")

    if not (25 <= dados["corrente_bateria"] <= 100):
        falhas.append("Corrente da bateria fora da faixa segura.")

    if dados["nivel_energia"] < 70:
        falhas.append("Nível de energia insuficiente.")

    if dados["perdas_energeticas"] > 7:
        falhas.append("Perdas energéticas acima do limite.")

    if not (100 <= dados["pressao_tanques"] <= 140):
        falhas.append("Pressão dos tanques fora da faixa segura.")

    if dados["integridade_estrutural"] != 1:
        falhas.append("Integridade estrutural comprometida.")

    if dados["status_modulos_criticos"] != 1:
        falhas.append("Falha nos módulos críticos.")

    if dados["status_link_telemetria"] != 1:
        falhas.append("Falha no link de telemetria.")

    if len(falhas) == 0:
        return "PRONTO PARA DECOLAR", falhas

    return "DECOLAGEM ABORTADA", falhas


def classificar_risco_por_probabilidade(prob_ready):
    if prob_ready >= 0.80:
        return "RISCO_BAIXO"
    elif prob_ready >= 0.50:
        return "RISCO_MODERADO"
    return "RISCO_ALTO"


def calcular_analise_energetica(energia_disponivel_kwh, perdas_percentual, carga_kw):
    energia_util = energia_disponivel_kwh * (1 - perdas_percentual / 100)

    consumo_estimado_decolagem_kwh = carga_kw / 60

    energia_restante_apos_decolagem = max(
        energia_util - consumo_estimado_decolagem_kwh, 0
    )

    autonomia_estimada_min = (energia_util / carga_kw) * 60 if carga_kw > 0 else 0

    return (
        energia_util,
        consumo_estimado_decolagem_kwh,
        energia_restante_apos_decolagem,
        autonomia_estimada_min,
    )


# CONFIGURAÇÃO INICIAL

CAMINHO_CSV = "telemetria_sintetica.csv"

df = carregar_dataset(CAMINHO_CSV)

colunas_features = [
    "internal_temp_c",
    "external_temp_c",
    "battery_voltage_v",
    "battery_current_a",
    "battery_soc_percent",
    "energy_available_kwh",
    "power_load_kw",
    "energy_loss_percent",
    "tank_pressure_bar",
    "estimated_autonomy_min",
]

# TREINAMENTO DOS MODELOS

modelo_decisao = DecisionTreeClassifier(random_state=42)
modelo_decisao.fit(df[colunas_features], df["launch_decision"])

modelo_anomalia = IsolationForest(random_state=42, contamination=0.1)
modelo_anomalia.fit(df[colunas_features])

# ESCOLHA DA AMOSTRA ATUAL

indices_ready = df.index[df["launch_decision"] == "READY"].tolist()
INDICE_AMOSTRA = indices_ready[0] if indices_ready else 0

row_atual = df.iloc[INDICE_AMOSTRA]
telemetria = linha_para_telemetria(row_atual)
features_atual = df.loc[[INDICE_AMOSTRA], colunas_features]

# EXECUÇÃO DAS REGRAS

status, falhas = verificar_decolagem(telemetria)

# APOIO DA IA

probs = modelo_decisao.predict_proba(features_atual)[0]
classes = list(modelo_decisao.classes_)

if "READY" in classes:
    prob_ready = probs[classes.index("READY")]
else:
    prob_ready = 0.0

risco_ia = classificar_risco_por_probabilidade(prob_ready)

anomalia = modelo_anomalia.predict(features_atual)[0]

if anomalia == -1:
    mensagem_ia = "comportamento anômalo detectado."
else:
    mensagem_ia = "nenhuma anomalia detectada."

# RELATÓRIO FINAL

print("=== RELATÓRIO DE PRÉ-DECOLAGEM ===")
for chave, valor in telemetria.items():
    print(f"{chave}: {valor}")

print("\nResultado final:", status)
print("Nível de risco estimado pela IA:", risco_ia)
print("IA:", mensagem_ia)

if falhas:
    print("Motivos da abortagem:")
    for falha in falhas:
        print("-", falha)

# ANÁLISE ENERGÉTICA

energia_util, consumo_estimado_decolagem_kwh, energia_restante_apos_decolagem, autonomia_estimada_min = calcular_analise_energetica(
    telemetria["energia_disponivel_kwh"],
    telemetria["perdas_energeticas"],
    telemetria["carga_kw"],
)

print("\n=== ANÁLISE ENERGÉTICA ===")
print(f"Energia disponível antes das perdas: {telemetria['energia_disponivel_kwh']:.3f} kWh")
print(f"Energia útil após perdas: {energia_util:.3f} kWh")
print(f"Consumo estimado da decolagem (1 min): {consumo_estimado_decolagem_kwh:.3f} kWh")
print(f"Energia restante após decolagem: {energia_restante_apos_decolagem:.3f} kWh")
print(f"Autonomia estimada após perdas: {autonomia_estimada_min:.2f} min")
print(f"Autonomia registrada no dataset: {telemetria['autonomia_estimada_dataset_min']} min")