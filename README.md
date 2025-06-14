<<<<<<< HEAD
# 🔍 Analisador Semântico - Linguagem Algorítmica (LA)

Este projeto implementa um **analisador semântico** para a linguagem algorítmica LA (Linguagem Algorítmica). O analisador realiza verificações semânticas como verificação de declaração de variáveis, verificação de tipos em atribuições, detecção de identificadores duplicados, validação de tipos em expressões e análise de compatibilidade de tipos.

## 👥 Autores

**Disciplina:** Construção de Compiladores  
**Trabalho:** T3 - Analisador Semântico

| Nome | RA |
|------|-----|
| Nataly Cristina da Silva | 812719 |
| Gabriel Cavalca Leite | 813615 |

## 📋 Descrição do Projeto

O analisador semântico processa códigos fonte escritos na linguagem LA e identifica erros semânticos, gerando um relatório com:
- Verificação de declaração de variáveis
- Verificação de tipos em atribuições  
- Detecção de identificadores duplicados
- Validação de tipos em expressões
- Análise de compatibilidade de tipos

## ⚙️ Pré-requisitos e Dependências

### Requisitos do Sistema:
- **Python 3.x** (versão 3.6 ou superior)
- **ANTLR4** (biblioteca Python antlr4-python3-runtime)
- **Java** (para executar corretor automático)
- **Git** (para clonar o repositório)

### Instalação das Dependências:
```bash
# Instalar ANTLR4 para Python
pip install antlr4-python3-runtime

# Verificar instalações
python3 --version
java -version
git --version
```

## 📥 Como Baixar o Projeto

### Passo 1: Clonar o Repositório
```bash
# Clonar o repositório do GitHub
git clone https://github.com/gabrielcavalca/Compiladores.T3.git

# Navegar para o diretório do projeto
cd Compiladores.T3
```

### Passo 2: Verificar Arquivos
```bash
# Listar arquivos do projeto
ls -la

# Verificar se os arquivos necessários estão presentes:
# - analisador_semantico.py
# - LAParser.py
# - LALexer.py  
# - LAListener.py
```

## 🔧 Como Compilar

**✅** Todos os arquivos Python já estão prontos no repositório.

### Passo 1: Instalar Dependências
```bash
# Instalar ANTLR4 para Python (única dependência necessária)
pip install antlr4-python3-runtime
```

### Passo 2: Testar Instalação
```bash
# Verificar se o analisador executa corretamente
python3 analisador_semantico.py
# Deve mostrar a mensagem de uso do programa
```

> **✅ Projeto Pronto:** Todos os arquivos necessários (LAParser.py, LALexer.py, LAListener.py) já estão incluídos no repositório, gerados a partir da gramática ANTLR4.

## 🚀 Como Executar

### Sintaxe Básica:
```bash
python3 analisador_semantico.py <arquivo_entrada> <arquivo_saida>
```

### Passo 1: Teste de Funcionamento (Opcional)
```bash
# Para testar se o programa funciona, você pode criar um arquivo simples
# Exemplo: python3 analisador_semantico.py exemplo.txt saida.txt
```

**Obs:** Este é apenas um teste opcional. Os arquivos de entrada reais estão nos casos de teste fornecidos pelo professor.

### Passo 2: Execução com Corretor Automático (Recomendada)

**O corretor automático e casos de teste são fornecidos pelo professor.**

```bash
java -jar "compiladores-corretor-automatico-1.0-SNAPSHOT-jar-with-dependencies.jar" \
    "python3 /caminho/absoluto/para/analisador_semantico.py" \
    /usr/bin \
    "/caminho/para/pasta/temp" \
    "/caminho/para/casos-de-teste" \
    "813615, 812719" \
    "t3"
```

> **📁 Importante:** Os resultados serão salvos na pasta `/temp` especificada no comando. Substitua os caminhos pelos caminhos reais no seu sistema.

## 📝 Estrutura do Projeto

```
Compiladores.T3/
├── analisador_semantico.py    # Arquivo principal do analisador
├── LAParser.py               # Parser gerado pelo ANTLR4
├── LALexer.py               # Lexer gerado pelo ANTLR4
├── LAListener.py            # Listener gerado pelo ANTLR4
├── README.md                # Este arquivo
└── outros arquivos...
```
=======
# Compiladores.t4
>>>>>>> 22926834f2af7d3c4f5a5c86f7c45dac16e59888
