#!/usr/bin/python3
# Copyright (c) BDist Development Team
# Distributed under the terms of the Modified BSD License.
import os
from logging.config import dictConfig

import psycopg
from flask import Flask, jsonify, request
from psycopg.rows import namedtuple_row
from datetime import datetime, timedelta, time
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
    ''' Lists all clinics (name and address). '''

    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            clinicas = cur.execute(
                '''
                SELECT nome, morada
                FROM clinica;
                ''',
                (),
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")

    return jsonify(clinicas)



@app.route("/c/<clinica>/", methods=("GET",))
def list_especialidades(clinica):
    """ Lists all specialities in <clinica>."""

    if not check_clinica(clinica):
        return jsonify({'status': 'error', 'message': 'A clinica nao existe.'}), 400

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


    
@app.route("/c/<clinica>/<especialidade>/", methods=("GET",))
def list_medicos(clinica, especialidade):
    ''' Lists all doctors (name) from <especialidade> who work in
    <clinica> and the first 3 available hours for consultation of 
    each of them (date and time). '''

    result = {}
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:

            cur.execute("BEGIN;")
            # Lock the consulta table in SHARE ROW EXCLUSIVE mode
            cur.execute("LOCK TABLE consulta IN SHARE ROW EXCLUSIVE MODE;")
            
            error = []
            if not check_clinica(clinica):
                error.append('Clinica invalida.')

            if not check_especialidade(especialidade):
                error.append('Especialidade invalida.')

            if error:
                cur.execute("COMMIT;")
                return jsonify({'status': 'error', 'message': '  '.join(error)}), 400
            
            # vai buscar medicos que trabalham na clinica com essa especialidade

            if not check_especialidade_em_clinica(clinica, especialidade):
                cur.execute("COMMIT;")
                return jsonify({'status': 'error', 'message': 
                                'Nao existem medicos desta especialidade nesta clinica.'}), 400

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
            cur.execute("COMMIT;")
            
    return jsonify(result)




@app.route('/a/<clinica>/registar/', methods=("POST",))
def register_consulta(clinica):
    ''' Registers new appointment in <clinica>. '''

    paciente = request.args.get("paciente")
    medico = request.args.get("medico")
    data_consulta = request.args.get("data")
    hora_consulta = request.args.get("hora")

    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            try:
                cur.execute("BEGIN;")
                # Lock the consulta table in ACCESS EXCLUSIVE mode
                cur.execute("LOCK TABLE consulta IN ACCESS EXCLUSIVE MODE;")

                error = []
                if not check_clinica(clinica):
                    error.append('Clinica invalida.')

                if not paciente:
                    error.append("Paciente is required.")
                elif not check_paciente(paciente):
                    error.append("Numero de ssn de paciente nao existe.")

                if not medico:
                    error.append("Medico is required.")
                elif not check_medico(medico):
                    error.append('Numero de nif de medico nao existe.')

                if not data_consulta:
                    error.append("Data de consulta is required.")

                elif (not is_valid_date(data_consulta)):
                    error.append("Formato data de consulta incorreto. Data tem de ser da forma YYYY-MM-DD. ")

                if not hora_consulta:
                    error.append("Hora de consulta is required.")

                elif (not is_valid_hour(hora_consulta)):
                    error.append("Formato hora de consulta incorreto. Hora tem de ser da forma HH-mm-ss. ")

                consulta_datetime = datetime.strptime(f"{data_consulta} {hora_consulta}", '%Y-%m-%d %H:%M:%S')
                if consulta_datetime <= datetime.now():
                    cur.execute("COMMIT;")
                    error.append("A consulta deve ser marcada para um momento futuro.")
                    return jsonify({'status': 'error', 'message': '  '.join(error)}), 400

                if not valid_working_time(hora_consulta):
                    error.append("A consulta nao pode ser marcada a estas horas.")

                if consulta_exists(clinica, paciente, medico, data_consulta, hora_consulta):
                    error.append("Esta consulta ja esta marcada. ")

                else:
                    if not medico_available(medico, data_consulta, hora_consulta):
                        error.append("Medico ja tem uma consulta marcada para estas horas. ")

                    if not paciente_available(paciente, data_consulta, hora_consulta):
                        error.append("Paciente ja tem uma consulta marcada para estas horas. ")

                if error:
                    cur.execute("COMMIT;")
                    return jsonify({'status': 'error', 'message': '  '.join(error)}), 400


                id = get_next_consulta_id()
                codigo_sns = generate_codigo_sns()

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
                cur.execute("COMMIT;")
                response = {'status': 'success', 'message': 'Consulta registrada com sucesso.'}

            except Exception as e:
                cur.execute('ROLLBACK')
                response = {'status': 'error', 'message': f'Erro ao registrar consulta: {str(e)}'}

    return jsonify(response)



@app.route('/a/<clinica>/cancelar/', methods=("POST",))
def cancel_consulta(clinica):
    ''' Cancels an appointment that hasn't taken place yet at <clinica>. '''

    paciente = request.args.get("paciente")
    medico = request.args.get("medico")
    data_consulta = request.args.get("data")
    hora_consulta = request.args.get("hora")    

    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            try:
                cur.execute("BEGIN;")
                    
                cur.execute("LOCK TABLE consulta IN ACCESS EXCLUSIVE MODE;")
                cur.execute("LOCK TABLE receita IN ACCESS EXCLUSIVE MODE;")
                cur.execute("LOCK TABLE observacao IN ACCESS EXCLUSIVE MODE;")

                error = []
                if not check_clinica(clinica):
                    error.append('Clinica invalida.')

                if not paciente:
                    error.append("Paciente is required.")
                elif not check_paciente(paciente):
                    error.append("Numero de ssn de paciente nao existe.")

                if not medico:
                    error.append("Medico is required.")
                elif not check_medico(medico):
                    error.append('Numero de nif de medico nao existe.')

                if not data_consulta:
                    error.append("Data de consulta is required.")

                elif (not is_valid_date(data_consulta)):
                    error.append("Formato data de consulta incorreto. Data tem de ser da forma YYYY-MM-DD. ")

                if not hora_consulta:
                    error.append("Hora de consulta is required.")

                elif (not is_valid_hour(hora_consulta)):
                    error.append("Formato hora de consulta incorreto. Hora tem de ser da forma HH-mm-ss. ")

                consulta_datetime = datetime.strptime(f"{data_consulta} {hora_consulta}", '%Y-%m-%d %H:%M:%S')
                if consulta_datetime <= datetime.now():
                    cur.execute("COMMIT;")
                    error.append("A consulta deve estar marcada para um momento futuro.")
                    return jsonify({'status': 'error', 'message': '  '.join(error)}), 400

                if not valid_working_time(hora_consulta):
                    error.append("A consulta nao pode estar marcada para estas horas.")

                if not consulta_exists(clinica, paciente, medico, data_consulta, hora_consulta):
                    error.append("Nao existe nenhuma consulta a estas horas. ")

                if error:
                    cur.execute("COMMIT;")
                    return jsonify({'status': 'error', 'message': '  '.join(error)}), 400

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
                    return jsonify({'status': 'error', 'message': 
                                    'Consulta nao encontrada ou ja cancelada.'}), 404

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
                cur.execute("COMMIT;")
                response = {'status': 'success', 'message': 'Consulta cancelada com sucesso.'}
            except Exception as e:
                cur.execute('ROLLBACK')
                response = {'status': 'error', 'message': f'Erro ao cancelar consulta: {str(e)}'}

    return jsonify(response)



def check_clinica(clinica):
    ''' Checks if the clinic <clinic> exists. '''
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                SELECT 1
                FROM clinica
                WHERE nome = %s;
                """,
                (clinica,),
            )
            if cur.fetchone() is None:
                return False
            return True
        

def check_especialidade(especialidade):
    ''' Checks if the speciality <especialidade> exists. '''
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                SELECT 1
                FROM medico
                WHERE especialidade = %s;
                """,
                (especialidade,),
            )
            if cur.fetchone() is None:
                return False
            return True
        

def check_especialidade_em_clinica(clinica, especialidade):
    ''' Checks if there are any doctors with speciality <especialidade> 
    working at <clinica>.'''
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                SELECT 1
                FROM medico m
                JOIN trabalha t USING(nif)
                WHERE m.especialidade = %s
                AND t.nome = %s;
                """,
                (especialidade, clinica),
            )
            if cur.fetchone() is None:
                return False
            return True
        

def check_paciente(paciente):
    ''' Checks if the patient's ssn exists. '''
    if len(paciente) != 11:
        return False
    
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                SELECT 1
                FROM paciente
                WHERE ssn = %s
                """,
                (paciente, ),
            )
            if cur.fetchone() is None:
                return False
            return True


def check_medico(medico):
    ''' Checks if the doctor's nif exists. '''

    if len(medico) != 9:
        return False
    
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                SELECT 1
                FROM medico
                WHERE nif = %s
                """,
                (medico, ),
            )
            if cur.fetchone() is None:
                return False
            return True


def valid_working_time(hora):
    ''' Checks if it's a valid time for an appointment to be made. '''

    # Define os intervalos de trabalho
    manha_inicio = time(8, 0, 0)
    manha_fim = time(12, 30, 0)
    tarde_inicio = time(14, 0, 0)
    tarde_fim = time(18, 30, 0)
    
    hora_obj = datetime.strptime(hora, "%H:%M:%S").time()

    # Verifica se a hora está dentro dos intervalos de trabalho
    if (manha_inicio <= hora_obj <= manha_fim) or (tarde_inicio <= hora_obj <= tarde_fim):
        # Verifica se a hora é uma hora exata ou meia hora
        if hora_obj.minute == 0 or hora_obj.minute == 30:
            if hora_obj.second == 0:
                return True
        
    return False

def consulta_exists(clinica, paciente, medico, data_consulta, hora_consulta):
    ''' Checks if an appointment exists. '''
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute("BEGIN;")
            
            res = cur.execute(
                """
                SELECT 1
                FROM consulta 
                WHERE nome = %s
                AND ssn = %s
                AND nif = %s
                AND data = %s
                AND hora = %s
                """,
                (clinica, paciente, medico, data_consulta, hora_consulta,),
            ).fetchone()
            cur.execute("COMMIT;")
            return res is not None



def round_up_to_next_half_hour(dt):
    ''' Gets the next valid time to schedule an appointment. '''
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
    ''' Gets the next day. '''
    return dt.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1)


def check_medico_trabalha_em_clinica(clinica, nif, data):
    ''' Checks if the doctor with <nif> is working at <clinic> on <data>. '''
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
        

def medico_available(medico, data, hora):
    ''' Checks if the doctor doesn't have any appointments scheduled. '''
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute("BEGIN;")

            cur.execute(
                """
                SELECT 1
                FROM consulta
                WHERE nif = %s
                AND data = %s
                AND hora = %s;
                """,
                (medico, data, hora),
            )
            if cur.fetchone() is not None:
                cur.execute("COMMIT;")
                return False
            cur.execute("COMMIT;")
            return True


def paciente_available(paciente, data, hora):
    ''' Checks if the patient doesn't have any appointments scheduled.'''
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute("BEGIN;")

            cur.execute(
                """
                SELECT 1
                FROM consulta
                WHERE ssn = %s
                AND data = %s
                AND hora = %s;
                """,
                (paciente, data, hora),
            )
            if cur.fetchone() is not None:
                cur.execute("COMMIT;")
                return False
            cur.execute("COMMIT;")
            return True


def is_valid_hour(hora):
    try:
        # Converte a string de hora para um objeto datetime
        hora_obj = datetime.strptime(hora, "%H:%M:%S")
        return True
    except ValueError:
        return False

def is_valid_date(data):
    try:
        data_obj = datetime.strptime(data, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def generate_codigo_sns():
    ''' Generates a unique codigo_sns for consulta. '''    
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute("BEGIN;")
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
            cur.execute("COMMIT;")
        log.debug(f"Found {cur.rowcount} rows.")
        
    return codigo_sns
                    

def get_next_consulta_id():
    ''' Gets the next consulta_id. '''
    with psycopg.connect(conninfo=DATABASE_URL) as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute("BEGIN;")
            max_id = cur.execute(
                """
                SELECT MAX(id) 
                FROM consulta;
                """,
                (),
            ).fetchone()
            cur.execute("COMMIT;")
            log.debug(f"Found {cur.rowcount} rows.")
    for id in max_id:
        return id + 1



if __name__ == "__main__":
    app.run()
