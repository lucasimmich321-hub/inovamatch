"""Validação compartilhada entre formulários, testes e armazenamento."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import math
import re
import unicodedata
from zoneinfo import ZoneInfo

STATES = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
          'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']


def today():
    return datetime.now(ZoneInfo('America/Sao_Paulo')).date()


def now_iso():
    return datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(timespec='seconds')


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value).strip().lower())
                   if not unicodedata.combining(c))


def missing(value):
    return value is None or value == '' or value == []


def money(value):
    try:
        n = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('Informe um valor numérico válido.') from exc
    if not math.isfinite(float(n)) or n < 0:
        raise ValueError('Valores financeiros devem ser positivos ou zero.')
    return float(n.quantize(Decimal('.01')))


def valid_cnpj(raw):
    cnpj = re.sub(r'[^0-9A-Za-z]', '', raw).upper()
    # Também contempla o CNPJ alfanumérico, com os dois dígitos finais numéricos.
    if not re.fullmatch(r'[0-9A-Z]{12}[0-9]{2}', cnpj) or len(set(cnpj)) == 1:
        return False
    nums = [ord(c) - 48 for c in cnpj]
    for end, weights in [(12, [5,4,3,2,9,8,7,6,5,4,3,2]), (13, [6,5,4,3,2,9,8,7,6,5,4,3,2])]:
        rem = sum(n * w for n, w in zip(nums[:end], weights)) % 11
        if nums[end] != (0 if rem < 2 else 11 - rem):
            return False
    return True


def validate_startup(record):
    r = dict(record)
    if not r.get('name', '').strip():
        raise ValueError('Informe o nome da startup.')
    if r.get('sem_cnpj') and r.get('cnpj'):
        raise ValueError('Marque "Ainda não tem CNPJ" ou informe o CNPJ, não os dois.')
    if r.get('cnpj') and not valid_cnpj(r['cnpj']):
        raise ValueError('CNPJ inválido. Corrija ou deixe em branco para registrar uma pendência.')
    if r.get('state') and r['state'] not in STATES:
        raise ValueError('Estado inválido.')
    if r.get('opened_on') and date.fromisoformat(r['opened_on']) > today():
        raise ValueError('A data de abertura não pode estar no futuro.')
    if r.get('counterpart') is not None:
        r['counterpart'] = money(r['counterpart'])
    return r


def validate_project(record, startup_ids):
    r = dict(record)
    if not r.get('name', '').strip():
        raise ValueError('Informe o nome do projeto.')
    if r.get('startup_id') not in startup_ids:
        raise ValueError('Selecione uma startup cadastrada.')
    for field in ['requested', 'budget']:
        if r.get(field) is not None:
            r[field] = money(r[field])
    if r.get('requested') is not None and r.get('budget') is not None and r['requested'] > r['budget']:
        raise ValueError('O valor solicitado não pode superar o orçamento total.')
    for field in ['execution_state', 'coordinator_state']:
        if r.get(field) and r[field] not in STATES:
            raise ValueError('Estado inválido no cadastro do projeto.')
    for field, low, high in [('trl', 1, 9), ('duration_months', 1, 1200)]:
        if r.get(field) is not None and (not isinstance(r[field], (int, float)) or not math.isfinite(r[field]) or r[field] != int(r[field]) or not low <= r[field] <= high):
            raise ValueError(f'Valor inválido para {field}.')
    return r


def deadline_info(call, on=None):
    if not call.get('deadline_confirmed') or not call.get('deadline') or not call.get('deadline_evidence'):
        return {'label': 'Prazo não confirmado', 'days': None, 'status': 'unknown'}
    try:
        end = date.fromisoformat(call['deadline'])
    except (ValueError, TypeError):
        return {'label': 'Prazo inválido: revisar', 'days': None, 'status': 'unknown'}
    days = (end - (on or today())).days
    if days < 0:
        label, status = f'Encerrado há {abs(days)} dia(s)', 'expired'
    elif days == 0:
        label, status = 'Encerra hoje · confira o horário no edital', 'soon'
    elif days <= 7:
        label, status = f'{days} dia(s) restante(s)', 'soon'
    else:
        label, status = f'{days} dias restantes', 'open'
    return {'label': label, 'days': days, 'status': status}
