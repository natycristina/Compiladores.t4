# Generated from LA.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .LAParser import LAParser
else:
    from LAParser import LAParser

# This class defines a complete generic visitor for a parse tree produced by LAParser.

class LAVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by LAParser#programa.
    def visitPrograma(self, ctx:LAParser.ProgramaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#declaracoes_preliminares.
    def visitDeclaracoes_preliminares(self, ctx:LAParser.Declaracoes_preliminaresContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#bloco_algoritmo.
    def visitBloco_algoritmo(self, ctx:LAParser.Bloco_algoritmoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#corpo_algoritmo.
    def visitCorpo_algoritmo(self, ctx:LAParser.Corpo_algoritmoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#declaracao.
    def visitDeclaracao(self, ctx:LAParser.DeclaracaoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#declaracao_funcao.
    def visitDeclaracao_funcao(self, ctx:LAParser.Declaracao_funcaoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#declaracao_constante.
    def visitDeclaracao_constante(self, ctx:LAParser.Declaracao_constanteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#valor_constante.
    def visitValor_constante(self, ctx:LAParser.Valor_constanteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#declaracao_procedimento.
    def visitDeclaracao_procedimento(self, ctx:LAParser.Declaracao_procedimentoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#parametros.
    def visitParametros(self, ctx:LAParser.ParametrosContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#parametro.
    def visitParametro(self, ctx:LAParser.ParametroContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#declaracoes_locais.
    def visitDeclaracoes_locais(self, ctx:LAParser.Declaracoes_locaisContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#declaracao_tipo.
    def visitDeclaracao_tipo(self, ctx:LAParser.Declaracao_tipoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#lista_variaveis.
    def visitLista_variaveis(self, ctx:LAParser.Lista_variaveisContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#variavel.
    def visitVariavel(self, ctx:LAParser.VariavelContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#tipoPrimitivo.
    def visitTipoPrimitivo(self, ctx:LAParser.TipoPrimitivoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#tipoIdentificado.
    def visitTipoIdentificado(self, ctx:LAParser.TipoIdentificadoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#tipoRegistro.
    def visitTipoRegistro(self, ctx:LAParser.TipoRegistroContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#tipo_identificado.
    def visitTipo_identificado(self, ctx:LAParser.Tipo_identificadoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#tipo_base.
    def visitTipo_base(self, ctx:LAParser.Tipo_baseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#tipo_registro.
    def visitTipo_registro(self, ctx:LAParser.Tipo_registroContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#lista_campos.
    def visitLista_campos(self, ctx:LAParser.Lista_camposContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#campo.
    def visitCampo(self, ctx:LAParser.CampoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#acesso_campo.
    def visitAcesso_campo(self, ctx:LAParser.Acesso_campoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#comando.
    def visitComando(self, ctx:LAParser.ComandoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#retorne.
    def visitRetorne(self, ctx:LAParser.RetorneContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#chamada_procedimento.
    def visitChamada_procedimento(self, ctx:LAParser.Chamada_procedimentoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#comandofaca.
    def visitComandofaca(self, ctx:LAParser.ComandofacaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#comandoenquanto.
    def visitComandoenquanto(self, ctx:LAParser.ComandoenquantoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#comandopara.
    def visitComandopara(self, ctx:LAParser.ComandoparaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#comandocaso.
    def visitComandocaso(self, ctx:LAParser.ComandocasoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#selecao.
    def visitSelecao(self, ctx:LAParser.SelecaoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#constantes.
    def visitConstantes(self, ctx:LAParser.ConstantesContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#constante.
    def visitConstante(self, ctx:LAParser.ConstanteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#comandose.
    def visitComandose(self, ctx:LAParser.ComandoseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#comandos.
    def visitComandos(self, ctx:LAParser.ComandosContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#leitura.
    def visitLeitura(self, ctx:LAParser.LeituraContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#lista_identificadores.
    def visitLista_identificadores(self, ctx:LAParser.Lista_identificadoresContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#atribuicao.
    def visitAtribuicao(self, ctx:LAParser.AtribuicaoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#escrita.
    def visitEscrita(self, ctx:LAParser.EscritaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#subliteral.
    def visitSubliteral(self, ctx:LAParser.SubliteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#potencia.
    def visitPotencia(self, ctx:LAParser.PotenciaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#expressao.
    def visitExpressao(self, ctx:LAParser.ExpressaoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#expressao_logica.
    def visitExpressao_logica(self, ctx:LAParser.Expressao_logicaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#expressao_relacional.
    def visitExpressao_relacional(self, ctx:LAParser.Expressao_relacionalContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#expressao_aritmetica.
    def visitExpressao_aritmetica(self, ctx:LAParser.Expressao_aritmeticaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#termo.
    def visitTermo(self, ctx:LAParser.TermoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#fator.
    def visitFator(self, ctx:LAParser.FatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#chamada_funcao.
    def visitChamada_funcao(self, ctx:LAParser.Chamada_funcaoContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by LAParser#lista_expressao.
    def visitLista_expressao(self, ctx:LAParser.Lista_expressaoContext):
        return self.visitChildren(ctx)



del LAParser