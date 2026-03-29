# 🫀 Analisador de Velocidade da Onda de Pulso

Aplicação Streamlit para organizar exames de VOP/PWV e estruturar o quadro clínico do paciente.

## O que o app faz

- recebe planilhas em `CSV`, `XLSX` ou `XLS`;
- aceita também quadro clínico em texto livre;
- permite preenchimento manual de idade, sexo, hipertensão, diabetes, VOP, PAS e PAD;
- padroniza automaticamente colunas como `VOP`, `idade`, `sexo`, `hipertensão` e `diabetes`;
- preenche dados faltantes da planilha com base no quadro clínico/manual, quando desejado;
- identifica valores ausentes por coluna;
- calcula média e desvio-padrão da VOP;
- mostra distribuição por sexo;
- compara VOP entre hipertensos e não hipertensos;
- compara VOP entre diabéticos e não diabéticos;
- calcula a correlação entre VOP e idade;
- gera gráfico de dispersão entre VOP e idade;
- gera gráfico de barras por faixa etária;
- permite editar a tabela padronizada antes de baixar o CSV final.

## Como usar

1. Envie a planilha de exames, se tiver.
2. Cole o quadro clínico no campo de texto, por exemplo: `Paciente feminina, 58 anos, hipertensa, não diabética, VOP 10,2 m/s, PAS 148, PAD 92`.
3. Se faltar alguma informação, preencha manualmente na barra lateral.
4. Revise a tabela padronizada editável.
5. Baixe o CSV final com os dados preenchidos.

## Como executar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Colunas reconhecidas automaticamente

O app tenta localizar sinônimos como:

- `VOP`, `PWV`, `pulse_wave_velocity`;
- `idade`, `age`;
- `sexo`, `gender`;
- `hipertenso`, `hypertension`, `HAS`;
- `diabetes`, `diabetic`, `DM`;
- `PAS/SBP` e `PAD/DBP`.


## Script alternativo (pandas/matplotlib)

Se preferir uma execução em script (sem Streamlit), use:

```bash
python vop_analysis.py vop_dados.xlsx
# ou
python vop_analysis.py vop_dados.csv
```

O script executa:
- média e desvio-padrão da VOP;
- distribuição por sexo;
- comparação entre hipertensos e não hipertensos;
- comparação entre diabéticos e não diabéticos;
- correlação entre VOP e idade;
- gráfico de dispersão VOP x idade;
- gráfico de barras por faixa etária.
