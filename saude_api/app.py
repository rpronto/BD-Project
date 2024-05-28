#!/usr/bin/python3
# Copyright (c) BDist Development Team
# Distributed under the terms of the Modified BSD License.
import os
from logging.config import dictConfig

import psycopg
from flask import Flask, jsonify, request
from psycopg.rows import namedtuple_row
from datetime import datetime
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
    res = []
    for e in especialidades:
        res.append(e[0])

    return jsonify(res)



#### agr ta a retornar as 3as consultas do medico
#### fazer current date? e obter 3 proximos horarios disponiveis
@app.route("/c/<clinica>/<especialidade>/", methods=("GET",))
def list_medicos(clinica, especialidade):
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            medicos = cur.execute(
                """
                SELECT m.nome, c.data, c.hora 
                FROM medico m
                JOIN trabalha t ON m.nif = t.nif
                LEFT JOIN consulta c ON m.nif = c.nif
                WHERE t.nome = %s AND m.especialidade = %s AND (c.data IS NULL OR c.data > CURRENT_DATE)
                ORDER BY c.data, c.hora;
                """,

                (clinica, especialidade),
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")

    result = {}
    for row in medicos:
        nome_medico = row[0]  # Acessando pelo índice da tupla
        if nome_medico not in result:
            result[nome_medico] = []

        # Adicionar apenas os primeiros três horários disponíveis
        if len(result[nome_medico]) < 3 and row[1] and row[2]:  # Acessando pelo índice da tupla
            result[nome_medico].append({
                'data': str(row[1]),  # Acessando pelo índice da tupla
                'hora': str(row[2])   # Acessando pelo índice da tupla
            })

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



@app.route('/a/<clinica>/cancelar/', methods=("POST",))
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
