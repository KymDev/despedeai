"""
Calculadora Trabalhista Completa
Módulo para cálculo de verbas rescisórias conforme legislação brasileira 2025
"""

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import calendar

class CalculadoraTrabalhista:
    def __init__(self):
        # Alíquotas INSS 2025
        self.inss_faixas = [
            (Decimal('1412.00'), Decimal('0.075')),  # 7.5%
            (Decimal('2666.68'), Decimal('0.09')),   # 9%
            (Decimal('4000.03'), Decimal('0.12')),   # 12%
            (Decimal('7786.02'), Decimal('0.14'))    # 14%
        ]
        
        # Alíquotas IRRF 2025
        self.irrf_faixas = [
            (Decimal('2259.20'), Decimal('0.00'), Decimal('0.00')),      # Isento
            (Decimal('2826.65'), Decimal('0.075'), Decimal('169.44')),   # 7.5%
            (Decimal('3751.05'), Decimal('0.15'), Decimal('381.44')),    # 15%
            (Decimal('4664.68'), Decimal('0.225'), Decimal('662.77')),   # 22.5%
            (float('inf'), Decimal('0.275'), Decimal('896.00'))          # 27.5%
        ]
        
        # Salário mínimo 2025
        self.salario_minimo = Decimal('1412.00')
        
    def calcular_inss(self, salario_base):
        """Calcula o desconto do INSS"""
        salario = Decimal(str(salario_base))
        desconto_total = Decimal('0')
        salario_restante = salario
        
        for i, (teto, aliquota) in enumerate(self.inss_faixas):
            if salario_restante <= 0:
                break
                
            if i == 0:
                base_calculo = min(salario_restante, teto)
            else:
                faixa_anterior = self.inss_faixas[i-1][0]
                base_calculo = min(salario_restante, teto - faixa_anterior)
            
            desconto_faixa = base_calculo * aliquota
            desconto_total += desconto_faixa
            salario_restante -= base_calculo
            
        return desconto_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def calcular_irrf(self, base_calculo, dependentes=0):
        """Calcula o desconto do IRRF"""
        base = Decimal(str(base_calculo))
        deducao_dependentes = Decimal('189.59') * dependentes
        base_tributavel = base - deducao_dependentes
        
        if base_tributavel <= 0:
            return Decimal('0')
        
        for teto, aliquota, deducao in self.irrf_faixas:
            if base_tributavel <= teto:
                imposto = (base_tributavel * aliquota) - deducao
                return max(Decimal('0'), imposto).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return Decimal('0')
    
    def calcular_dias_uteis(self, data_inicio, data_fim):
        """Calcula dias úteis entre duas datas"""
        dias_uteis = 0
        data_atual = data_inicio
        
        while data_atual <= data_fim:
            if data_atual.weekday() < 5:  # Segunda a sexta
                dias_uteis += 1
            data_atual += timedelta(days=1)
            
        return dias_uteis
    
    def calcular_ferias_proporcionais(self, salario, data_admissao, data_demissao, ferias_vencidas=0):
        """Calcula férias proporcionais + 1/3 constitucional"""
        salario = Decimal(str(salario))
        
        # Calcula meses trabalhados no período aquisitivo atual
        anos_trabalhados = (data_demissao - data_admissao).days // 365
        data_inicio_periodo = data_admissao + timedelta(days=365 * anos_trabalhados)
        
        meses_trabalhados = 0
        data_atual = data_inicio_periodo
        
        while data_atual < data_demissao:
            if data_atual.month == 12:
                proximo_mes = data_atual.replace(year=data_atual.year + 1, month=1, day=1)
            else:
                proximo_mes = data_atual.replace(month=data_atual.month + 1, day=1)
            
            if proximo_mes <= data_demissao:
                meses_trabalhados += 1
            elif (data_demissao - data_atual).days >= 15:
                meses_trabalhados += 1
                
            data_atual = proximo_mes
        
        # Calcula valor proporcional
        valor_ferias = (salario * meses_trabalhados) / 12
        um_terco = valor_ferias / 3
        
        return {
            'meses_trabalhados': meses_trabalhados,
            'valor_ferias': valor_ferias.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'um_terco': um_terco.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'total': (valor_ferias + um_terco).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }
    
    def calcular_decimo_terceiro(self, salario, data_admissao, data_demissao):
        """Calcula 13º salário proporcional"""
        salario = Decimal(str(salario))
        
        # Meses trabalhados no ano da demissão
        meses_trabalhados = data_demissao.month
        
        # Se trabalhou mais de 15 dias no mês da demissão, conta o mês
        if data_demissao.day >= 15:
            meses_trabalhados = data_demissao.month
        else:
            meses_trabalhados = data_demissao.month - 1
        
        # Se foi admitido no ano atual, ajusta o cálculo
        if data_admissao.year == data_demissao.year:
            meses_desde_admissao = data_demissao.month - data_admissao.month
            if data_admissao.day <= 15:
                meses_desde_admissao += 1
            meses_trabalhados = min(meses_trabalhados, meses_desde_admissao)
        
        valor_decimo = (salario * meses_trabalhados) / 12
        
        return {
            'meses_trabalhados': meses_trabalhados,
            'valor': valor_decimo.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }
    
    def calcular_aviso_previo(self, salario, tempo_servico_anos, tipo_demissao, trabalhado=False):
        """Calcula aviso prévio (30 dias + 3 dias por ano)"""
        salario = Decimal(str(salario))
        
        if tipo_demissao in ['justa_causa', 'pedido_demissao']:
            return {
                'dias': 0,
                'valor': Decimal('0'),
                'tipo': 'Não aplicável'
            }
        
        # 30 dias base + 3 dias por ano trabalhado
        dias_aviso = 30 + (tempo_servico_anos * 3)
        dias_aviso = min(dias_aviso, 90)  # Máximo 90 dias
        
        valor_aviso = (salario * dias_aviso) / 30
        
        tipo_aviso = 'Trabalhado' if trabalhado else 'Indenizado'
        
        return {
            'dias': dias_aviso,
            'valor': valor_aviso.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'tipo': tipo_aviso
        }
    
    def calcular_multa_fgts(self, saldo_fgts, tipo_demissao):
        """Calcula multa de 40% do FGTS"""
        saldo = Decimal(str(saldo_fgts))
        
        if tipo_demissao != 'sem_justa_causa':
            return {
                'percentual': 0,
                'valor': Decimal('0'),
                'aplicavel': False
            }
        
        multa = saldo * Decimal('0.40')
        
        return {
            'percentual': 40,
            'valor': multa.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'aplicavel': True
        }
    
    def calcular_saldo_salario(self, salario, data_demissao, dias_trabalhados_mes):
        """Calcula saldo de salário do mês"""
        salario = Decimal(str(salario))
        dias_mes = calendar.monthrange(data_demissao.year, data_demissao.month)[1]
        
        valor_saldo = (salario * dias_trabalhados_mes) / dias_mes
        
        return {
            'dias_trabalhados': dias_trabalhados_mes,
            'dias_mes': dias_mes,
            'valor': valor_saldo.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }
    
    def calcular_rescisao_completa(self, dados):
        """
        Calcula todas as verbas rescisórias
        
        dados = {
            'salario': float,
            'data_admissao': datetime,
            'data_demissao': datetime,
            'tipo_demissao': 'sem_justa_causa' | 'justa_causa' | 'pedido_demissao',
            'saldo_fgts': float,
            'horas_extras_mes': float (opcional),
            'adicional_noturno': float (opcional),
            'adicional_periculosidade': float (opcional),
            'dependentes_ir': int (opcional),
            'aviso_trabalhado': bool (opcional)
        }
        """
        
        # Dados básicos
        salario = Decimal(str(dados['salario']))
        data_admissao = dados['data_admissao']
        data_demissao = dados['data_demissao']
        tipo_demissao = dados['tipo_demissao']
        
        # Calcula tempo de serviço
        tempo_servico = data_demissao - data_admissao
        tempo_servico_anos = tempo_servico.days // 365
        
        # Dias trabalhados no mês da demissão
        dias_trabalhados_mes = data_demissao.day
        
        # Cálculos individuais
        saldo_salario = self.calcular_saldo_salario(salario, data_demissao, dias_trabalhados_mes)
        ferias = self.calcular_ferias_proporcionais(salario, data_admissao, data_demissao)
        decimo_terceiro = self.calcular_decimo_terceiro(salario, data_admissao, data_demissao)
        aviso_previo = self.calcular_aviso_previo(
            salario, 
            tempo_servico_anos, 
            tipo_demissao, 
            dados.get('aviso_trabalhado', False)
        )
        multa_fgts = self.calcular_multa_fgts(dados.get('saldo_fgts', 0), tipo_demissao)
        
        # Verbas adicionais
        horas_extras = Decimal(str(dados.get('horas_extras_mes', 0)))
        adicional_noturno = Decimal(str(dados.get('adicional_noturno', 0)))
        adicional_periculosidade = Decimal(str(dados.get('adicional_periculosidade', 0)))
        
        # Total bruto
        total_bruto = (
            saldo_salario['valor'] +
            ferias['total'] +
            decimo_terceiro['valor'] +
            aviso_previo['valor'] +
            horas_extras +
            adicional_noturno +
            adicional_periculosidade
        )
        
        # Descontos
        base_inss = total_bruto
        desconto_inss = self.calcular_inss(base_inss)
        
        base_irrf = total_bruto - desconto_inss
        desconto_irrf = self.calcular_irrf(base_irrf, dados.get('dependentes_ir', 0))
        
        total_descontos = desconto_inss + desconto_irrf
        total_liquido = total_bruto - total_descontos
        
        return {
            'verbas': {
                'saldo_salario': saldo_salario,
                'ferias_proporcionais': ferias,
                'decimo_terceiro': decimo_terceiro,
                'aviso_previo': aviso_previo,
                'horas_extras': horas_extras,
                'adicional_noturno': adicional_noturno,
                'adicional_periculosidade': adicional_periculosidade,
                'multa_fgts': multa_fgts
            },
            'resumo': {
                'total_bruto': total_bruto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'desconto_inss': desconto_inss,
                'desconto_irrf': desconto_irrf,
                'total_descontos': total_descontos.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'total_liquido': total_liquido.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            },
            'tempo_servico': {
                'anos': tempo_servico_anos,
                'dias_totais': tempo_servico.days
            }
        }

