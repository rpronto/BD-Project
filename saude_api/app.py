#!/usr/bin/python3
# Copyright (c) BDist Development Team
# Distributed under the terms of the Modified BSD License.
import os
from logging.config import dictConfig

import psycopg
from flask import Flask, jsonify, request
from psycopg.rows import namedtuple_row
from datetime import datetime, timedelta
import random
import string

# Use the DATABASE_URL environment variable if it exists, otherwise use the default.
# Use the format postgres://username:password@hostname/database_name to connect to the database.
DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://saude:saude@postgres/saude")

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s:%(lineno)s - %(funcName)20s(): %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["wsgi"]},
    }
)

app = Flask(__name__)
app.config.from_prefixed_env()
log = app.logger



@app.route("/", methods=("GET",))
@app.route("/clinicas", methods=("GET",))
def list_clinicas():
    ''' Show all clinics '''

    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            clinicas = cur.execute(
                '''
                SELECT nome, morada
                FROM clinica;
                ''',
                {},
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")

    return jsonify(clinicas)


@app.route("/c/<clinica>/", methods=("GET",))
def list_especialidades(clinica):
    """Show specialities in clinica."""

    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            especialidades = cur.execute(
                """
                SELECT DISTINCT m.especialidade 
                FROM medico m 
                JOIN trabalha t ON m.nif = t.nif 
                WHERE t.nome = %s
                """,
                (clinica,),
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")

    return jsonify(especialidades)



### problema: temos de verificar qual o proximo dia em que o medico trabalha neste dia
def round_up_to_next_half_hour(dt):
    # Se os minutos são 0-29, arredonda para a meia hora seguinte
    # Se os minutos são 30-59, arredonda para a próxima hora
    if dt.minute < 30:
        dt = dt.replace(minute=30, second=0, microsecond=0)
    else:
        dt = dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    # Ajuste para fora do horário de trabalho
    if dt.hour >= 19:
        dt = dt.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1)
    elif dt.hour >= 13:
        dt = dt.replace(hour=14, minute=0, second=0, microsecond=0)

    return dt

def get_next_day(dt):
    return dt.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1)


def check_medico_trabalha_em_clinica(clinica, nif, data):

    dia_semana = (data.isoweekday()) % 7

    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                SELECT 1
                FROM medico m
                JOIN trabalha t USING(nif)
                WHERE m.nif = %s
                AND t.nome = %s
                AND t.dia_da_semana = %s;
                """,
                (nif, clinica, dia_semana),
            )
            if cur.fetchone() is None:
                return False
            return True
        



@app.route("/c/<clinica>/<especialidade>/", methods=("GET",))
def list_medicos(clinica, especialidade):

    result = {}
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            # vai buscar medicos que trabalham na clinica com essa especialidade
            medicos = cur.execute(
                """
                SELECT DISTINCT m.nome, m.nif
                FROM medico m
                JOIN trabalha t ON m.nif = t.nif
                JOIN consulta c ON m.nif = c.nif
                WHERE t.nome = %s 
                AND m.especialidade = %s;
                """,
                (clinica, especialidade),
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")

            for medico in medicos:
                hora_atual = datetime.now()
                rounded_time = round_up_to_next_half_hour(hora_atual)

                medico_nome = medico[0]
                medico_nif = medico[1]
                count = 3

                while count > 0:
                    hora = rounded_time.time()
                    data = rounded_time.date()
                    
                    while not check_medico_trabalha_em_clinica(clinica, medico_nif, data):
                        rounded_time = get_next_day(rounded_time)
                        hora = rounded_time.time()
                        data = rounded_time.date()

                    cur.execute(
                        """
                        SELECT 1
                        FROM consulta c
                        WHERE c.nif = %s
                        AND c.data = %s
                        AND c.hora = %s;
                        """,
                        (medico_nif, data, hora),
                    )
                    # se n houver consulta nessa hora 
                    if cur.fetchone() is None:
                        count -= 1
                        if medico_nome not in result:
                            result[medico_nome] = []
                        result[medico_nome].append({'data': str(data), 'hora': str(hora)})
                    # update hora
                    rounded_time = round_up_to_next_half_hour(rounded_time)

    return jsonify(result)

    
def is_valid_hour(hora):
    try:
        # Converte a string de hora para um objeto datetime
        hora_obj = datetime.strptime(hora, "%H:%M:%S")
        return True
    except ValueError:
        # Se a conversão falhar, a hora é inválida
        return False


def is_valid_date(data):
    try:
        data_obj = datetime.strptime(data, "%Y-%m-%d")
        if data_obj.year in [2023, 2024]:
            return True
        else:
            return False
    except ValueError:
        return False


def generate_codigo_sns():
    ''' Generates a unique codigo_sns for consulta. '''    
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            while True:
                codigo_sns = ''.join(random.choices(string.digits, k=12))
                cur.execute(
                    """
                    SELECT 1
                    FROM consulta c 
                    WHERE c.codigo_sns = %(codigo)s;
                    """,
                    {"codigo": codigo_sns}
                )
                if cur.fetchone() is None:
                    break
        log.debug(f"Found {cur.rowcount} rows.")

    return codigo_sns
                    

def get_next_consulta_id():
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            max_id = cur.execute(
                """
                SELECT MAX(id) 
                FROM consulta;
                """,
                (),
            ).fetchone()
            log.debug(f"Found {cur.rowcount} rows.")
    for id in max_id:
        return id + 1



@app.route('/a/<clinica>/registar/', methods=("POST",))
def register_consulta(clinica):
    ''' Registers new appointment. '''

    paciente = request.json.get("paciente")
    medico = request.json.get("medico")
    data_consulta = request.json.get("data")
    hora_consulta = request.json.get("hora")

    error = None
    if not paciente:
         error = "Paciente is required."
    elif not medico:
         error = "Medico is required."
    elif not data_consulta:
        error = "Data de consulta is required."
    elif not hora_consulta:
        error = "Hora de consulta is required."

    if (not is_valid_hour(hora_consulta)):
        error = "Formato hora de consulta incorreto."

    if (not is_valid_date(data_consulta)):
        error = "Formato data de consulta incorreto."

    consulta_datetime = datetime.strptime(f"{data_consulta} {hora_consulta}", '%Y-%m-%d %H:%M:%S')
    if consulta_datetime <= datetime.now():
        error = "A consulta deve ser marcada para um momento futuro."

    if error is not None:
        return jsonify({'status': 'error', 'message': error}), 400
    else:
        id = get_next_consulta_id()
        codigo_sns = generate_codigo_sns()

        with psycopg.connect(conninfo=DATABASE_URL) as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                try:
                    cur.execute(
                        """
                        INSERT INTO consulta (id, ssn, nif, nome, data, hora, codigo_sns)
                        VALUES (%(id)s, %(paciente)s, %(medico)s, %(clinica)s, 
                        %(data_consulta)s, %(hora_consulta)s, %(codigo_sns)s);
                        """,
                        {"id": id, 
                        "paciente": paciente, 
                        "medico": medico, 
                        "clinica": clinica, 
                        "data_consulta": data_consulta, 
                        "hora_consulta": hora_consulta, 
                        "codigo_sns": codigo_sns},
                    )
                    conn.commit()
                    response = {'status': 'success', 'message': 'Consulta registrada com sucesso.'}
                except Exception as e:
                    cur.execute('ROLLBACK')
                    response = {'status': 'error', 'message': f'Erro ao registrar consulta: {str(e)}'}
        return jsonify(response)



@app.route('/a/<clinica>/cancelar/', methods=("DELETE",))
def cancel_consulta(clinica):

    paciente = request.json.get("paciente")
    medico = request.json.get("medico")
    data_consulta = request.json.get("data")
    hora_consulta = request.json.get("hora")

    error = None
    
    if not paciente:
         error = "Paciente is required."
    elif not medico:
         error = "Medico is required."
    elif not data_consulta:
        error = "Data de consulta is required."
    elif not hora_consulta:
        error = "Hora de consulta is required."

    if (not is_valid_hour(hora_consulta)):
        error = "Formato hora de consulta incorreto."

    if (not is_valid_date(data_consulta)):
        error = "Formato data de consulta incorreto."

    consulta_datetime = datetime.strptime(f"{data_consulta} {hora_consulta}", '%Y-%m-%d %H:%M:%S')
    if consulta_datetime <= datetime.now():
        error = "A consulta deve ser marcada para um momento futuro."

    if error is not None:
        return jsonify({'status': 'error', 'message': error}), 400
    
    else:
        with psycopg.connect(conninfo=DATABASE_URL) as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                try:
                    codigo_sns, id = cur.execute(
                        '''
                        SELECT codigo_sns, id
                        FROM consulta 
                        WHERE ssn = %s 
                        AND nif = %s 
                        AND nome = %s
                        AND data = %s 
                        AND hora = %s
                        ''', 
                        (paciente, medico, clinica, data_consulta, hora_consulta)
                    ).fetchone()
                    if codigo_sns is None or id is None:
                        return jsonify({'status': 'error', 'message': 'Consulta não encontrada ou já cancelada.'}), 404

                    cur.execute(
                        '''
                        DELETE FROM receita 
                        WHERE codigo_sns = %s
                        ''', 
                        (codigo_sns,)
                    )
                    cur.execute(
                        '''
                        DELETE FROM observacao 
                        WHERE id = %s
                        ''', 
                        (id,)
                    )
                    cur.execute(
                        '''
                        DELETE FROM consulta 
                        WHERE ssn = %s 
                        AND nif = %s 
                        AND nome = %s
                        AND data = %s 
                        AND hora = %s
                        ''', 
                        (paciente, medico, clinica, data_consulta, hora_consulta)
                    )
                    conn.commit()
                    response = {'status': 'success', 'message': 'Consulta cancelada com sucesso.'}
                except Exception as e:
                    cur.execute('ROLLBACK')
                    response = {'status': 'error', 'message': f'Erro ao cancelar consulta: {str(e)}'}

    return jsonify(response)


if __name__ == "__main__":
    app.run()
