#!/usr/bin/python3
# Copyright (c) BDist Development Team
# Distributed under the terms of the Modified BSD License.
import os
from logging.config import dictConfig

import psycopg
from flask import Flask, jsonify, request
from psycopg.rows import namedtuple_row

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





@app.route('/a/<clinica>/registar/', methods=['POST'])
def register_consulta(clinica):
    data = request.get_json()
    paciente = data['paciente']
    medico = data['medico']
    data_consulta = data['data']
    hora_consulta = data['hora']

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('BEGIN')
        cur.execute('''
            INSERT INTO consulta (ssn, nif, nome, data, hora)
            VALUES (%s, %s, %s, %s, %s)
        ''', (paciente, medico, clinica, data_consulta, hora_consulta))
        cur.execute('COMMIT')
        response = {'status': 'success', 'message': 'Consulta registrada com sucesso.'}
    except Exception as e:
        cur.execute('ROLLBACK')
        response = {'status': 'error', 'message': f'Erro ao registrar consulta: {str(e)}'}
    finally:
        cur.close()
        conn.close()
    
    return jsonify(response)

@app.route('/a/<clinica>/cancelar/', methods=['POST'])
def cancel_consulta(clinica):
    data = request.get_json()
    paciente = data['paciente']
    medico = data['medico']
    data_consulta = data['data']
    hora_consulta = data['hora']

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('BEGIN')
        cur.execute('''
            DELETE FROM consulta 
            WHERE ssn = %s AND nif = %s AND nome = %s AND data = %s AND hora = %s
        ''', (paciente, medico, clinica, data_consulta, hora_consulta))
        cur.execute('COMMIT')
        response = {'status': 'success', 'message': 'Consulta cancelada com sucesso.'}
    except Exception as e:
        cur.execute('ROLLBACK')
        response = {'status': 'error', 'message': f'Erro ao cancelar consulta: {str(e)}'}
    finally:
        cur.close()
        conn.close()
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
