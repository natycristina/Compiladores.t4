<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>README - Analisador Semântico</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #2c3e50, #3498db);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        .header p {
            margin: 10px 0 0 0;
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .content {
            padding: 40px;
        }
        
        .section {
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(255, 255, 255, 0.7);
            border-radius: 15px;
            border-left: 5px solid #3498db;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .section:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.1);
        }
        
        .section h2 {
            color: #2c3e50;
            margin-top: 0;
            font-size: 1.8em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .icon {
            font-size: 1.2em;
        }
        
        .code-block {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 10px;
            margin: 15px 0;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            overflow-x: auto;
            border: 1px solid #333;
        }
        
        .highlight {
            background: linear-gradient(90deg, #ff6b6b, #ee5a24);
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            font-weight: bold;
            text-align: center;
        }
        
        .requirements {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .req-item {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            transition: transform 0.3s ease;
        }
        
        .req-item:hover {
            transform: scale(1.05);
        }
        
        .step {
            background: #f8f9fa;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            padding: 20px;
            margin: 15px 0;
            position: relative;
        }
        
        .step-number {
            background: #3498db;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            position: absolute;
            top: -15px;
            left: 20px;
            font-weight: bold;
        }
        
        .step h3 {
            margin-left: 40px;
            color: #2c3e50;
        }
        
        .warning {
            background: #fff3cd;
            border: 2px solid #ffeb3b;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            border-left: 5px solid #ff9800;
        }
        
        .footer {
            background: #2c3e50;
            color: white;
            text-align: center;
            padding: 30px;
            margin-top: 40px;
        }
        
        ul {
            list-style: none;
            padding: 0;
        }
        
        li {
            background: rgba(52, 152, 219, 0.1);
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }
        
        @media (max-width: 768px) {
            .container {
                margin: 10px;
                border-radius: 10px;
            }
            
            .content {
                padding: 20px;
            }
            
            .section {
                padding: 20px;
            }
            
            .header {
                padding: 30px 20px;
            }
            
            .header h1 {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Analisador Semântico</h1>
            <p>Compilador para Linguagem Algorítmica (LA)</p>
        </div>
        
        <div class="content">
            <div class="section">
                <h2><span class="icon">📋</span>Descrição do Projeto</h2>
                <p>Este projeto implementa um <strong>analisador semântico</strong> para a linguagem algorítmica LA (Linguagem Algorítmica). O analisador realiza verificações semânticas como:</p>
                <ul>
                    <li>Verificação de declaração de variáveis</li>
                    <li>Verificação de tipos em atribuições</li>
                    <li>Detecção de identificadores duplicados</li>
                    <li>Validação de tipos em expressões</li>
                    <li>Análise de compatibilidade de tipos</li>
                </ul>
            </div>

            <div class="section">
                <h2><span class="icon">⚙️</span>Pré-requisitos e Dependências</h2>
                <div class="requirements">
                    <div class="req-item">
                        <strong>Python 3.x</strong><br>
                        Versão 3.6 ou superior
                    </div>
                    <div class="req-item">
                        <strong>ANTLR4</strong><br>
                        Biblioteca Python antlr4-python3-runtime
                    </div>
                    <div class="req-item">
                        <strong>Java</strong><br>
                        Para executar corretor automático
                    </div>
                    <div class="req-item">
                        <strong>Git</strong><br>
                        Para clonar o repositório
                    </div>
                </div>
                
                <h3>Instalação das Dependências</h3>
                <div class="code-block">
# Instalar ANTLR4 para Python
pip install antlr4-python3-runtime

# Verificar instalação do Python
python3 --version

# Verificar instalação do Java
java -version

# Verificar instalação do Git
git --version
                </div>
            </div>

            <div class="section">
                <h2><span class="icon">📁</span>Estrutura do Projeto</h2>
                <p>Após clonar o repositório, você encontrará os seguintes arquivos:</p>
                <ul>
                    <li><strong>analisador_semantico.py</strong> - Arquivo principal do analisador</li>
                    <li><strong>LAParser.py</strong> - Parser gerado pelo ANTLR4 (já incluído)</li>
                    <li><strong>LALexer.py</strong> - Lexer gerado pelo ANTLR4 (já incluído)</li>
                    <li><strong>LAListener.py</strong> - Listener gerado pelo ANTLR4 (já incluído)</li>
                    <li><strong>README.md</strong> - Este arquivo de documentação</li>
                </ul>
                
                <div class="highlight">
                    ✅ Todos os arquivos necessários já estão prontos no repositório!
                </div>
            </div>

            <div class="section">
                <h2><span class="icon">📥</span>Como Baixar o Projeto</h2>
                
                <div class="step">
                    <div class="step-number">1</div>
                    <h3>Clonar o Repositório</h3>
                    <div class="code-block">
# Clonar o repositório do GitHub
git clone https://github.com/gabrielcavalca/Compiladores.T3.git

# Navegar para o diretório do projeto
cd Compiladores.T3
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-number">2</div>
                    <h3>Verificar Arquivos</h3>
                    <div class="code-block">
# Listar arquivos do projeto
ls -la

# Verificar se os arquivos necessários estão presentes:
# - analisador_semantico.py
# - LAParser.py
# - LALexer.py  
# - LAListener.py
                    </div>
                </div>
            </div>

            <div class="section">
                <h2><span class="icon">🔧</span>Como Compilar</h2>
                <p><strong>Não é necessário compilar!</strong> Todos os arquivos Python já estão prontos no repositório.</p>
                
                <div class="step">
                    <div class="step-number">1</div>
                    <h3>Instalar Dependências</h3>
                    <div class="code-block">
# Verificar se o analisador executa corretamente
python3 analisador_semantico.py
# Deve mostrar: "Uso: python3 analisador_semantico.py entrada.txt saida.txt"
                    </div>
                </div>
                
                <div class="warning">
                    <strong>✅ Projeto Pronto:</strong> Todos os arquivos necessários (LAParser.py, LALexer.py, LAListener.py) já estão incluídos no repositório, gerados a partir da gramática ANTLR4.
                </div>
            </div>

            <div class="section">
                <h2><span class="icon">🚀</span>Como Executar</h2>
                
                <div class="highlight">
                    Sintaxe: python3 analisador_semantico.py &lt;arquivo_entrada&gt; &lt;arquivo_saida&gt;
                </div>
                
                <div class="step">
                    <div class="step-number">1</div>
                    <h3>Execução Básica</h3>
                    <div class="code-block">
# Executar o analisador semântico
python3 analisador_semantico.py programa.txt resultado.txt
                    </div>
                    <p><strong>Onde:</strong></p>
                    <ul>
                        <li><code>programa.txt</code> - Arquivo contendo o código fonte em LA</li>
                        <li><code>resultado.txt</code> - Arquivo onde serão escritos os erros encontrados</li>
                    </ul>
                </div>

                <div class="step">
                    <div class="step-number">2</div>
                    <h3>Execução com Corretor Automático (Recomendada)</h3>
                    <p><strong>O corretor automático e casos de teste são fornecidos pelo professor.</strong></p>
                    <div class="code-block">
java -jar "compiladores-corretor-automatico-1.0-SNAPSHOT-jar-with-dependencies.jar" \
    "python3 /caminho/absoluto/para/analisador_semantico.py" \
    /usr/bin \
    "/caminho/para/pasta/temp" \
    "/caminho/para/casos-de-teste" \
    "813615, 812719" \
    "t3"
                    </div>
                    <div class="warning">
                        <strong>📁 Importante:</strong> Os resultados serão salvos na pasta <code>/temp</code> especificada no comando. Substitua os caminhos pelos caminhos reais no seu sistema.
                    </div>
                </div>

                
    </div>
</body>
</html>
