"""
Sistema de Pagamento PIX
Módulo para geração de PIX, QR Code e verificação de pagamentos
"""

import qrcode
import sqlite3
import uuid
import hashlib
from datetime import datetime, timedelta
from io import BytesIO
import base64
import json

class SistemaPIX:
    def __init__(self, db_path='transacoes.db'):
        self.db_path = db_path
        self.init_database()
        
        # Configurações PIX (substitua pelos dados reais)
        self.chave_pix = "despede.ai@hotmail.com"  # Chave PIX da empresa
        self.nome_recebedor = "DESPEDE AI"
        self.cidade = "SAO PAULO"
        
    def init_database(self):
        """Inicializa o banco de dados SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transacoes (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                valor REAL NOT NULL,
                status TEXT DEFAULT 'pendente',
                txid TEXT UNIQUE,
                qr_code TEXT,
                dados_usuario TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                paid_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def gerar_txid(self):
        """Gera um TXID único para a transação"""
        return str(uuid.uuid4()).replace('-', '').upper()[:32]
    
    def gerar_payload_pix(self, valor, txid, descricao="Kit Rescisao Premium"):
        """
        Gera payload PIX conforme padrão EMV
        """
        # Função auxiliar para formatar campos EMV
        def format_emv(tag, value):
            return f"{tag:02d}{len(str(value)):02d}{value}"
        
        # Merchant Account Information (chave PIX)
        merchant_info = format_emv(0, "BR.GOV.BCB.PIX")
        merchant_info += format_emv(1, self.chave_pix)
        
        # Payload principal
        payload = ""
        payload += format_emv(0, "01")  # Payload Format Indicator
        payload += format_emv(1, "12")  # Point of Initiation Method (dinâmico)
        payload += format_emv(26, merchant_info)  # Merchant Account Information
        payload += format_emv(52, "0000")  # Merchant Category Code
        payload += format_emv(53, "986")   # Transaction Currency (BRL)
        payload += format_emv(54, f"{valor:.2f}")  # Transaction Amount
        payload += format_emv(58, "BR")    # Country Code
        payload += format_emv(59, self.nome_recebedor)  # Merchant Name
        payload += format_emv(60, self.cidade)  # Merchant City
        
        # Additional Data Field (TXID)
        additional_data = format_emv(5, txid)
        payload += format_emv(62, additional_data)
        
        # CRC16 (será calculado)
        payload += "6304"
        
        # Calcula CRC16
        crc = self.calcular_crc16(payload)
        payload = payload[:-4] + f"{crc:04X}"
        
        return payload
    
    def calcular_crc16(self, payload):
        """Calcula CRC16 para o payload PIX"""
        crc = 0xFFFF
        for byte in payload.encode('utf-8'):
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc
    
    def gerar_qr_code(self, payload):
        """Gera QR Code do PIX"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        
        # Gera imagem
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converte para base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return qr_base64
    
    def criar_transacao(self, email, valor, dados_usuario):
        """Cria uma nova transação PIX"""
        
        # Gera TXID único
        txid = self.gerar_txid()
        
        # Gera payload PIX
        payload = self.gerar_payload_pix(valor, txid)
        
        # Gera QR Code
        qr_code = self.gerar_qr_code(payload)
        
        # Data de expiração (1 hora)
        expires_at = datetime.now() + timedelta(hours=1)
        
        # Salva no banco
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        transacao_id = str(uuid.uuid4())
        
        cursor.execute('''
            INSERT INTO transacoes 
            (id, email, valor, txid, qr_code, dados_usuario, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            transacao_id,
            email,
            valor,
            txid,
            qr_code,
            json.dumps(dados_usuario),
            expires_at
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'transacao_id': transacao_id,
            'txid': txid,
            'payload': payload,
            'qr_code': qr_code,
            'valor': valor,
            'expires_at': expires_at.isoformat()
        }
    
    def verificar_pagamento(self, txid):
        """
        Verifica se o pagamento foi realizado
        Em produção, isso seria feito via webhook do banco
        Para demonstração, simula a verificação
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, status, expires_at FROM transacoes 
            WHERE txid = ?
        ''', (txid,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return {'status': 'nao_encontrado'}
        
        transacao_id, status, expires_at = result
        
        # Verifica se expirou
        if datetime.now() > datetime.fromisoformat(expires_at):
            self.atualizar_status_transacao(transacao_id, 'expirado')
            return {'status': 'expirado'}
        
        # Em produção, aqui seria feita a consulta real ao banco
        # Para demonstração, retorna o status atual
        return {'status': status, 'transacao_id': transacao_id}
    
    def confirmar_pagamento(self, txid):
        """
        Confirma o pagamento (simulação para testes)
        Em produção, seria chamado pelo webhook do banco
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE transacoes 
            SET status = 'pago', paid_at = CURRENT_TIMESTAMP
            WHERE txid = ? AND status = 'pendente'
        ''', (txid,))
        
        conn.commit()
        conn.close()
        
        return cursor.rowcount > 0
    
    def atualizar_status_transacao(self, transacao_id, novo_status):
        """Atualiza o status de uma transação"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE transacoes 
            SET status = ?
            WHERE id = ?
        ''', (novo_status, transacao_id))
        
        conn.commit()
        conn.close()
    
    def obter_transacao(self, transacao_id):
        """Obtém dados completos de uma transação"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM transacoes WHERE id = ?
        ''', (transacao_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            columns = ['id', 'email', 'valor', 'status', 'txid', 'qr_code', 
                      'dados_usuario', 'created_at', 'expires_at', 'paid_at']
            
            transacao = dict(zip(columns, result))
            
            # Parse JSON dos dados do usuário
            if transacao['dados_usuario']:
                transacao['dados_usuario'] = json.loads(transacao['dados_usuario'])
            
            return transacao
        
        return None
    
    def listar_transacoes_pendentes(self):
        """Lista transações pendentes não expiradas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, txid, email, valor, created_at 
            FROM transacoes 
            WHERE status = 'pendente' 
            AND expires_at > CURRENT_TIMESTAMP
            ORDER BY created_at DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def limpar_transacoes_expiradas(self):
        """Remove transações expiradas do banco"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM transacoes 
            WHERE expires_at < CURRENT_TIMESTAMP 
            AND status IN ('pendente', 'expirado')
        ''')
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count

# Classe para webhook (simulação)
class WebhookPIX:
    def __init__(self, sistema_pix):
        self.sistema_pix = sistema_pix
    
    def processar_webhook(self, dados_webhook):
        """
        Processa webhook de confirmação de pagamento
        Em produção, seria chamado pelo banco
        """
        try:
            txid = dados_webhook.get('txid')
            status = dados_webhook.get('status')
            
            if status == 'CONCLUIDA':
                return self.sistema_pix.confirmar_pagamento(txid)
            
            return False
            
        except Exception as e:
            print(f"Erro ao processar webhook: {e}")
            return False

