import pandas as pd

# Carrega o arquivo Excel
df = pd.read_excel("04. Farol.xlsx")

# Exibe o nome de todas as colunas
print("Colunas disponíveis na planilha:\n")
for col in df.columns:
    print(f"- '{col}'")