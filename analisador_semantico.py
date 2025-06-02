import sys
from antlr4 import *
from LAParser import LAParser
from LALexer import LALexer
from LAListener import LAListener

# Lista de tipos válidos (de acordo com a gramática)
TIPOS_VALIDOS = {'literal', 'inteiro', 'real', 'logico'}

class AnalisadorSemantico(LAListener):
    def __init__(self, token_stream):
        self.simbolos = {}   # dicionário nome -> tipo
        self.erros = []
        self.tokens = token_stream

    # Pega o número da linha do token (para mensagens)
    def linha_token(self, token):
        return token.line

    def tipo_expressao(self, ctx):
        # Importa as classes do parser para usar isinstance
        from LAParser import LAParser

        # 1) Caso raiz: expressao : expressao_logica
        if isinstance(ctx, LAParser.ExpressaoContext):
            return self.tipo_expressao(ctx.expressao_logica())

        # 2) expressao_logica : expressao_relacional ('e' expressao_relacional | 'ou' expressao_relacional)*
        elif isinstance(ctx, LAParser.Expressao_logicaContext):
            # Avalia o tipo de todas as expressao_relacional dentro da expressão lógica
            tipos = [self.tipo_expressao(child) for child in ctx.expressao_relacional()]
            
            # Se só um elemento (sem operadores lógicos)
            if len(tipos) == 1:
                return tipos[0]
            
            # Senão, todos precisam ser 'logico' para o 'e' / 'ou' fazer sentido
            if all(t == 'logico' for t in tipos):
                return 'logico'
            else:
                return None

        # 3) expressao_relacional : expressao_aritmetica ((OP_RELACIONAL | IGUAL) expressao_aritmetica)?
        elif isinstance(ctx, LAParser.Expressao_relacionalContext):
            if ctx.getChildCount() == 1:
                # Só expressao_aritmetica, sem operador relacional
                return self.tipo_expressao(ctx.expressao_aritmetica(0))
            else:
                tipo_esq = self.tipo_expressao(ctx.expressao_aritmetica(0))
                tipo_dir = self.tipo_expressao(ctx.expressao_aritmetica(1))
                # Operadores relacionais retornam 'logico' se os tipos são compatíveis (ex: inteiros, reais)
                if tipo_esq in ('inteiro','real') and tipo_dir in ('inteiro','real'):
                    return 'logico'
                if tipo_esq == tipo_dir:
                    return 'logico'
                return None

        # 4) expressao_aritmetica : termo (( '+' | '-' ) termo)*
        elif isinstance(ctx, LAParser.Expressao_aritmeticaContext):
            tipos = [self.tipo_expressao(term) for term in ctx.termo()]
            tipo_acumulado = tipos[0]
            for t in tipos[1:]:
                if tipo_acumulado in ('inteiro','real') and t in ('inteiro','real'):
                    # promoção numérica
                    tipo_acumulado = 'real' if 'real' in (tipo_acumulado, t) else 'inteiro'
                elif tipo_acumulado == 'literal' and t == 'literal':
                    # concatenação literal
                    tipo_acumulado = 'literal'
                else:
                    return None
            return tipo_acumulado

        # 5) termo : fator (( '*' | '/' | '%' ) fator)*
        elif isinstance(ctx, LAParser.TermoContext):
            tipos = [self.tipo_expressao(fat) for fat in ctx.fator()]
            tipo_acumulado = tipos[0]
            for t in tipos[1:]:
                if tipo_acumulado in ('inteiro','real') and t in ('inteiro','real'):
                    tipo_acumulado = 'real' if 'real' in (tipo_acumulado, t) else 'inteiro'
                else:
                    return None
            return tipo_acumulado

        # 6) fator : vários casos terminais e recursivos
        elif isinstance(ctx, LAParser.FatorContext):
            # Identificador
            if ctx.IDENT():
                nome = ctx.IDENT().getText()
                tipo_var = self.simbolos.get(nome)
                if tipo_var is None:
                    self.erros.append(f"Linha {ctx.start.line}: identificador {nome} nao declarado")
                    return None
                return tipo_var

            # Constantes numéricas
            if ctx.NUM_INT():
                return 'inteiro'
            if ctx.NUM_REAL():
                return 'real'

            # Literal cadeia
            if ctx.CADEIA():
                return 'literal'

            # Verdadeiro ou falso (booleano)
            if ctx.getText() in ('verdadeiro', 'falso'):
                return 'logico'

            # Parênteses: desce para a expressao interna
            if ctx.ABREPAR():
                return self.tipo_expressao(ctx.expressao())

            # Negação unária (- fator)
            if ctx.getChildCount() == 2 and ctx.getChild(0).getText() == '-':
                return self.tipo_expressao(ctx.fator())

            # Negação lógica (nao fator)
            if ctx.getChildCount() == 2 and ctx.getChild(0).getText().lower() == 'nao':
                t = self.tipo_expressao(ctx.fator())
                return 'logico' if t == 'logico' else None

            # Endereçamento (& IDENT ou acesso_campo)
            if ctx.getChildCount() == 2 and ctx.getChild(0).getText() == '&':
                # Endereço: aceita qualquer tipo, retorna 'endereco' ou None conforme sua definição
                return 'endereco'

            # Potência (CIRCUNFLEXO IDENT)
            if ctx.CIRCUNFLEXO():
                # Depende da declaração da variável
                nome = ctx.IDENT().getText()
                return self.simbolos.get(nome)

            # chamada_funcao (implemente se necessário)
            if ctx.chamada_funcao():
                # Deve retornar o tipo do resultado da função
                return self.tipo_funcao(ctx.chamada_funcao())

            # acesso_campo (implemente se necessário)
            if ctx.acesso_campo():
                return self.tipo_expressao(ctx.acesso_campo())

            # Se não reconhecer, retorna None
            return None

        else:
            # Contexto não tratado
            return None

    
    def eh_compatível(self, tipo_var, tipo_exp):
        if tipo_var == tipo_exp:
            return True
        # Permitir atribuir inteiro para real
        if tipo_var == 'real' and tipo_exp == 'inteiro':
            return True
        return False

    def enterAtribuicao(self, ctx:LAParser.AtribuicaoContext):
        # Nome da variável à esquerda
        nome_var = ctx.getChild(0).getText()

        # Tipo da variável à esquerda
        tipo_var = self.simbolos.get(nome_var)

        if tipo_var is None:
            # Variável não declarada — já tem erro disso? Se não, pode colocar
            token_var = ctx.getChild(0).getSymbol()
            self.erros.append(f"Linha {token_var.line}: identificador {nome_var} nao declarado")

        # Verificar tipo da expressão do lado direito
        tipo_exp = self.tipo_expressao(ctx.expressao())

        # Comparar tipos
        if not self.eh_compatível(tipo_var, tipo_exp):
            token_var = ctx.getChild(0).getSymbol()
            self.erros.append(f"Linha {token_var.line}: atribuicao nao compativel para {nome_var}")

    # Captura variáveis declaradas na regra "declaracao"
    def enterDeclaracao(self, ctx:LAParser.DeclaracaoContext):
        tipo_ctx = ctx.lista_variaveis().variavel(0).tipo()
        tipo_texto = tipo_ctx.getText().replace("^", "")
        
        if tipo_texto not in TIPOS_VALIDOS:
            token_tipo = tipo_ctx.start
            self.erros.append(f"Linha {self.linha_token(token_tipo)}: tipo {tipo_texto} nao declarado")
        
        for var_ctx in ctx.lista_variaveis().variavel():
            for i in range(var_ctx.IDENT().__len__()):
                nome_var = var_ctx.IDENT(i).getText()

                if nome_var in self.simbolos:
                    # Variável já declarada, pegar token para linha do erro
                    token_var = var_ctx.IDENT(i).getSymbol()
                    self.erros.append(f"Linha {self.linha_token(token_var)}: identificador {nome_var} ja declarado anteriormente")
                else:
                    self.simbolos[nome_var] = tipo_texto

    def enterComandoenquanto(self, ctx: LAParser.ComandoenquantoContext):
        tipo_condicao = self.tipo_expressao(ctx.expressao())

    # Verificar identificadores usados em 'leia' (leitura)
    def enterLeitura(self, ctx:LAParser.LeituraContext):
        lista_ids = ctx.lista_identificadores()
        for child in lista_ids.children:
            if child.getText() == ',':
                continue
            if isinstance(child, LAParser.Acesso_campoContext):
                continue
            nome = child.getText()
            if nome not in self.simbolos:
                token_id = child.getSymbol()  # <-- corrigido aqui
                self.erros.append(f"Linha {self.linha_token(token_id)}: identificador {nome} nao declarado")


    # Verificar identificadores usados em 'escreva'
    # Pode ser extendido para expressões, mas simplificado aqui (por token de IDENT)
    def enterEscrita(self, ctx:LAParser.EscritaContext):
        for exp in ctx.expressao():
            self.tipo_expressao(exp)

def main():
    if len(sys.argv) != 3:
        print("Uso: python3 analisador_semantico.py entrada.txt saida.txt")
        return

    arquivo_entrada = sys.argv[1]
    arquivo_saida = sys.argv[2]

    input_stream = FileStream(arquivo_entrada, encoding='utf-8')
    lexer = LALexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = LAParser(token_stream)

    tree = parser.programa()

    analisador = AnalisadorSemantico(token_stream)
    walker = ParseTreeWalker()
    walker.walk(analisador, tree)

    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        for erro in analisador.erros:
            f.write(erro + '\n')
        f.write("Fim da compilacao\n")

if __name__ == "__main__":
    main()
