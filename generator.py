from faker import Faker
import random
from unidecode import unidecode
from datetime import datetime, timedelta, time
import string


# Create a Faker instance
fake = Faker('pt_PT') 

# List of neighborhoods/districts within Lisbon
lisbon_neighborhoods = [
    "Alfama", "Bairro Alto", "Baixa", "Belém", "Campo de Ourique",
    "Graça", "Mouraria", "Parque das Nações", "Santos", "Lapa",
    "Areeiro", "Estrela", "Marvila", "Carnide", "Lumiar"
]

def clean_text(text):
    text = unidecode(text)  # Remove accents and other diacritics
    text = ''.join(e for e in text if e.isalnum() or e.isspace())  # Keep alphanumeric and space characters only
    return text

# Function to generate random clinic data
def generate_clinic_data(num_entries):
    clinic_data = []
    for _ in range(num_entries):
        nome = fake.company()
        telefone = fake.unique.numerify(text='#########')  
        morada = f'{fake.street_name()}, {fake.building_number()} {fake.postcode()}, {fake.random_element(lisbon_neighborhoods)}, Lisboa'
        clinic_data.append((nome, telefone, morada))
    return clinic_data


# Function to generate random nurse data for a given clinic
def generate_nurse_data(clinic_name, num_nurses):
    nurse_data = []
    for _ in range(num_nurses):
        nif = fake.unique.numerify(text='#########')  # Generates a 9-digit number
        nome = fake.unique.name()
        telefone = fake.unique.numerify(text='#########') 
        morada = f'{fake.street_name()}, {fake.building_number()} {fake.postcode()}, {fake.random_element(lisbon_neighborhoods)},  Lisboa'
        nurse_data.append((nif, nome, telefone, morada, clinic_name))
    return nurse_data


# Function to generate random doctor data
def generate_doctor_data(num_doctors):
    # List of specialities
    specialities = ["cardiologia", "dermatologia", "ortopedia", "pediatria", "ginecologia"]
    doctor_data = []
    for i in range(num_doctors):
        nif = fake.unique.numerify(text='#########')  # Generates a 9-digit number
        nome = fake.unique.name()
        telefone = fake.unique.numerify(text='#########') 
        morada = f'{fake.street_name()}, {fake.building_number()} {fake.postcode()}, {fake.random_element(lisbon_neighborhoods)}, Lisboa'
        if i < 20:
            especialidade = "clínica geral"
        else:
            especialidade = fake.random_element(specialities)
        doctor_data.append((nif, nome, telefone, morada, especialidade))
    return doctor_data

    
# Generate work schedule for doctors in clinics
def generate_works_data(medicos, clinicas):
    trabalha = []

    clinicas_medicos = {clinica[0]: [] for clinica in clinicas}
    medico_clinicas = {medico[0]: set() for medico in medicos}

    # Ensure each doctor works in at least two clinics
    for medico in medicos:
        clinicas_selecionadas = random.sample(clinicas, 2)
        for clinica in clinicas_selecionadas:
            clinicas_medicos[clinica[0]].append(medico[0])
            medico_clinicas[medico[0]].add(clinica[0])

    # Ensure each clinic has at least 8 doctors
    for clinica in clinicas:
        while len(clinicas_medicos[clinica[0]]) < 8:
            medico = random.choice(medicos)[0]
            clinicas_medicos[clinica[0]].append(medico)
            medico_clinicas[medico].add(clinica[0])


    for clinica, medicos_clinica in clinicas_medicos.items():
        for dia in range(1, 8): # monday = 1
            medicos_dia = random.sample(medicos_clinica, 8)  # Select 8 doctors randomly
            for medico in medicos_dia:
                if any(item[0] == medico and item[2] == dia for item in trabalha):
                    continue
                trabalha.append((medico, clinica, dia))
            
    return trabalha

def generate_patient_data(num_entries):
    pacientes = []
    for _ in range(num_entries):
        ssn = fake.unique.bothify(text='###########')
        nif = fake.unique.bothify(text='#########')
        nome = fake.name()
        telefone = fake.unique.bothify(text='###########')
        morada = fake.address().replace('\n', ', ')
        data_nasc = fake.date_of_birth(minimum_age=0, maximum_age=100).strftime('%Y-%m-%d')
        pacientes.append((ssn, nif, clean_text(nome), telefone, clean_text(morada), data_nasc))
    return pacientes


def generate_time():
    possible_hours_morning = list(range(8, 13))  # 08:00 to 12:30
    possible_hours_afternoon = list(range(14, 19))  # 14:00 to 18:30
    possible_minutes = [0, 30]  # Minutes can be 00 or 30

    if random.choice([True, False]):
        hour = random.choice(possible_hours_morning)
    else:
        hour = random.choice(possible_hours_afternoon)
    
    minute = random.choice(possible_minutes)
    return time(hour, minute, 0)  # Hours, minutes, and seconds set to 00

def generate_codigo_sns():
    return ''.join(random.choices(string.digits, k=12))


def generate_receitas(consultas, prob_receita=0.8):
    receitas = []
    unique_receitas = []

    for consulta in consultas:
        if random.random() < prob_receita:
            num_meds = random.randint(1, 6) 
            for _ in range(num_meds):
                med = f'Medicamento {random.randint(1, 100)}'
                while ((consulta[6], med) in unique_receitas): # (codigo sns, med) is primary key
                    med = f'Medicamento {random.randint(1, 100)}'

                receita = (consulta[6], med, random.randint(1, 3))
                receitas.append(receita)
                unique_receitas.append((consulta[6], med))

    return receitas


def generate_observacoes(consultas):
    observacoes = []
    sintomas = [f'Sintoma{i}' for i in range(1, 51)]
    metricas = [f'Metrica{i}' for i in range(1, 21)]
    
    # Set to keep track of unique observations
    unique_observacoes = set()

    for consulta in consultas:
        num_sintomas = random.randint(1, 5)
        num_metricas = random.randint(0, 3)
        parametros_sintomas = random.sample(sintomas, num_sintomas)
        parametros_metricas = random.sample(metricas, num_metricas)

        for parametro in parametros_sintomas:
            observation = (consulta[0], clean_text(parametro))
            if observation not in unique_observacoes:
                observacoes.append(observation)
                unique_observacoes.add(observation)

        for parametro in parametros_metricas:
            observation = (consulta[0], clean_text(parametro), random.uniform(1.0, 100.0))
            if observation not in unique_observacoes:
                observacoes.append(observation)
                unique_observacoes.add(observation)

    return observacoes


# def generate_consultas(pacientes, medicos, clinicas, trabalha):
#     consultas = []
#     start_date = datetime(2023, 1, 1)
#     end_date = datetime(2024, 12, 31)
#     num_days = (end_date - start_date).days

#     unique_ssn_marcacao = []
#     unique_nif_marcacao = []

#     # Garantir pelo menos 20 consultas por dia por clínica e 2 consultas por médico
#     for day in range(num_days + 1):
#         date = start_date + timedelta(days=day)
#         dia_semana = date.weekday()

#         # por clinica 20 consultas por dia
#         for clinica in clinicas:
#             daily_consultas = []
#             lista_medicos = []

#             for t in trabalha:
#                 if t[1] == clinica[0] and t[2] == dia_semana: # if the doctor is working in this clinic on this day
#                     lista_medicos.append(t[0])

#             while len(daily_consultas) < 20: # 20 consultas por clinica, por dia
#                 medico = None
#                 while medico is None:
#                     medico_candidate = random.choice(medicos)
#                     # Verifica se o médico trabalha no dia da semana atual
#                     for t in trabalha: 
#                         if (t[0] == medico_candidate[0] and t[1] == clinica[0] and t[2] == dia_semana):
#                             medico = medico_candidate

#                 paciente = random.choice(pacientes)
#                 time = generate_time().strftime('%H:%M:%S')
#                 while ((paciente[0], date, time) in unique_ssn_marcacao or (medico[0], date, time) in unique_nif_marcacao):
#                     time = generate_time().strftime('%H:%M:%S')
                
#                 consulta = (len(consultas) + 1, paciente[0], medico[0], clinica[0],
#                             date.strftime('%Y-%m-%d'), time, generate_codigo_sns())
                
#                 consultas.append(consulta)
#                 print("INSERT INTO consulta VALUES ", consulta, ';')
#                 daily_consultas.append(consulta)

#                 unique_nif_marcacao.append((medico[0], date, time))
#                 unique_ssn_marcacao.append((paciente[0], date, time))

#             for medico_nif in lista_medicos: # cada medico tem de ter pelo menos 2 consultas por  dia
#                 medico_consultas = [c for c in daily_consultas if c[2] == medico_nif] # consultas dadas pelo medico

#                 while len(medico_consultas) < 2:
#                     paciente = random.choice(pacientes)
#                     time = generate_time().strftime('%H:%M:%S')
#                     while ((paciente[0], date, time) in unique_ssn_marcacao or (medico[0], date, time) in unique_nif_marcacao):
#                         time = generate_time().strftime('%H:%M:%S')

#                     consulta = (len(consultas) + 1, paciente[0], medico_nif, clinica[0],
#                                 date.strftime('%Y-%m-%d'), time, generate_codigo_sns())
#                     consultas.append(consulta)
#                     print("INSERT INTO consulta VALUES ", consulta, ';')
#                     daily_consultas.append(consulta)
#                     medico_consultas.append(consulta)

#                     unique_nif_marcacao.append((medico[0], date, time))
#                     unique_ssn_marcacao.append((paciente[0], date, time))


#     # Pacientes devem ter pelo menos uma consulta
#     for paciente in pacientes:
#         if not any(paciente[0] == consulta[1] for consulta in consultas): # if paciente doesnt have any consulta yet
#             consulta_date = start_date + timedelta(days=random.randint(0, num_days))
#             dia_semana = consulta_date.weekday()

#             # Filtra trabalha por dia da semana
#             trabalha_dia = []
#             for item in trabalha:
#                 if item[2] == dia_semana and item not in trabalha_dia:
#                     trabalha_dia.append(item)
            
#             # Seleciona um trabalha aleatório
#             trabalha_item = random.choice(trabalha_dia)
#             # Filtra medicos por nif correspondente
#             medico = random.choice([m for m in medicos if trabalha_item[0] == m[0]])

#             time = generate_time().strftime('%H:%M:%S')
#             while ((paciente[0], date, time) in unique_ssn_marcacao or (medico[0], date, time) in unique_nif_marcacao):
#                 time = generate_time().strftime('%H:%M:%S')

#             consulta = (len(consultas) + 1, paciente[0], medico[0], trabalha_item[1],
#                         consulta_date.strftime('%Y-%m-%d'), time, generate_codigo_sns())
                
#             consultas.append(consulta)
#             print("INSERT INTO consulta VALUES ", consulta, ';')

#             unique_nif_marcacao.append((medico[0], date, time))
#             unique_ssn_marcacao.append((paciente[0], date, time))

#     return consultas


# Function to generate consultations and prescriptions
def gerar_consultas_receitas(pacientes, medicos, clinicas, start_date, end_date, trabalha):
    consultas = []
    receitas = []
    consulta_id = 1

    delta_days = (end_date - start_date).days
    patient_schedule = {p[0]: set() for p in pacientes}  # Dictionary to track each patient's schedule
    doctor_schedule = {m[0]: set() for m in medicos}  # Dictionary to track each doctor's schedule
    unique_receitas = set()
    
    for day_offset in range(delta_days):
        data = (start_date + timedelta(days=day_offset)).date()

        # weekday --> monday = 0, sunday = 6
        # isoweekday --> monday = 1, sunday = 7
        # we want sunday = 1, monday = 2, ... saturday = 7
        
        day_of_week = (data.isoweekday() + 1) % 7
        for clinica in clinicas:
            consultas_por_clinica = 0
            
            # Seleciona médicos disponíveis para a clínica e o dia da semana
            medicos_disponiveis = [t[0] for t in trabalha if t[1] == clinica[0] and t[2] == day_of_week]
            if not medicos_disponiveis:
                continue  # Continue para a próxima clínica se não houver médicos disponíveis

            while consultas_por_clinica < 20:
                for medico in medicos_disponiveis:
                    consultas_por_medico = 0

                    while consultas_por_medico < 2:

                        hora = generate_time()  # Gera um horário dentro dos intervalos especificados
                        paciente_disponiveis = [p for p in pacientes if (data, hora) not in patient_schedule[p[0]]]

                        if not paciente_disponiveis:
                            break  # Interrompe se não houver pacientes disponíveis

                        paciente = random.choice(paciente_disponiveis)
                        if paciente[0] == medico[0]:  # Pula se o paciente for o mesmo que o médico
                            continue

                        if (data, hora) in doctor_schedule[medico]:
                            continue  # Pula se o médico já tiver uma consulta neste horário

                        # Adiciona a nova consulta aos agendamentos
                        patient_schedule[paciente[0]].add((data, hora))
                        doctor_schedule[medico].add((data, hora))

                        codigo_sns = fake.unique.bothify(text='############')
                        consultas.append((consulta_id, paciente[0], medico, clinica[0], data.strftime('%Y-%m-%d'), hora.strftime('%H:%M:%S'), codigo_sns))

                        # ~80% das consultas têm receita
                        if random.random() < 0.8:
                            num_meds = random.randint(1, 6)
                            for _ in range(num_meds):
                                med = f'Medicamento {random.randint(1, 100)}'
                                while ((codigo_sns, med) in unique_receitas): # (codigo sns, med) is primary key
                                    med = f'Medicamento {random.randint(1, 100)}'
                                quantidade = random.randint(1, 3)
                                # Verifica se a receita já foi prescrita para este paciente nesta consulta
                                if (codigo_sns, med) not in unique_receitas:
                                    unique_receitas.add((codigo_sns, med))
                                    receitas.append((codigo_sns, med, quantidade))

                        consulta_id += 1
                        consultas_por_clinica += 1
                        consultas_por_medico += 1

                        if consultas_por_medico >= 2:
                            break

                if consultas_por_clinica >= 20:
                    break

    return consultas, receitas


# Number of clinics to generate
num_clinics = 5 
# Generate clinic data
clinic_data = generate_clinic_data(num_clinics)
# Print the generated clinic data
for clinic in clinic_data:
    print("INSERT INTO clinica VALUES ", clinic, ';')


num_patients = 5000
patients = generate_patient_data(num_patients)
# Print generated data
for patient in patients:
    print("INSERT INTO paciente VALUES ", patient, ';')
    
# Generate nurse data for each clinic
nurse_data_all = []
for clinic in clinic_data:
    clinic_name = clinic[0]
    num_nurses = fake.random_int(min=5, max=6)
    nurse_data = generate_nurse_data(clinic_name, num_nurses)
    nurse_data_all.extend(nurse_data)#
# Print the generated nurse data
for nurse in nurse_data_all:
    print("INSERT INTO enfermeiro VALUES ", nurse, ';')


# Number of doctors to generate
num_doctors = 60  # 20 "Clínica Geral" + 40 distributed among 5 specialities
# Generate doctor data
doctor_data = generate_doctor_data(num_doctors)
# Print the generated doctor data
for doctor in doctor_data:
    print("INSERT INTO medico VALUES ", doctor, ';')


# Generate works data
works_data = generate_works_data(doctor_data, clinic_data)
# Print the generated works data
for work in works_data:
    print("INSERT INTO trabalha VALUES ", work, ';')





start_date = datetime(2023, 1, 1)
end_date = datetime(2024, 12, 31)
consultas, receitas =  gerar_consultas_receitas(patients, doctor_data, clinic_data, start_date, end_date, works_data)
for consulta in consultas:
    print("INSERT INTO consulta VALUES ", consulta, ';')

# receitas = generate_receitas(consultas)
for receita in receitas:
    print("INSERT INTO receita VALUES ", receita, ';')


observacoes = generate_observacoes(consultas)
for observacao in observacoes:
    print("INSERT INTO observacao VALUES ", observacao, ';')



# # Function to generate consultations and prescriptions
# def gerar_consultas_receitas(pacientes, medicos, clinicas, start_date, end_date, trabalha):
#     consultas = []
#     receitas = []
#     consulta_id = 1

#     delta_days = (end_date - start_date).days
#     patient_schedule = {p[0]: set() for p in pacientes}  # Dictionary to track each patient's schedule
#     doctor_schedule = {m[0]: set() for m in medicos}  # Dictionary to track each doctor's schedule
#     unique_receitas = set()
    
#     for day_offset in range(delta_days):
#         data = (start_date + timedelta(days=day_offset)).date()
#         day_of_week = (data.weekday() + 1) % 7  # Convert to 0 = Sunday, ..., 6 = Saturday

#         for clinica in clinicas:
#             consultas_por_clinica = 0
            
#             # Seleciona médicos disponíveis para a clínica e o dia da semana
#             medicos_disponiveis = [t[0] for t in trabalha if t[1] == clinica[0] and t[2] == day_of_week]
#             if not medicos_disponiveis:
#                 continue  # Continue para a próxima clínica se não houver médicos disponíveis

#             while consultas_por_clinica < 20:
#                 medico = random.choice(medicos_disponiveis)
#                 consultas_por_medico = 0

#                 while consultas_por_medico < 2:
#                     if consultas_por_clinica >= 20:
#                         break

#                     hora = generate_random_time()  # Gera um horário dentro dos intervalos especificados
#                     paciente_disponiveis = [p for p in pacientes if (data, hora) not in patient_schedule[p[0]]]

#                     if not paciente_disponiveis:
#                         break  # Interrompe se não houver pacientes disponíveis

#                     paciente = random.choice(paciente_disponiveis)
#                     if paciente[0] == medico[0]:  # Pula se o paciente for o mesmo que o médico
#                         continue

#                     if (data, hora) in doctor_schedule[medico]:
#                         continue  # Pula se o médico já tiver uma consulta neste horário

#                     # Adiciona a nova consulta aos agendamentos
#                     patient_schedule[paciente[0]].add((data, hora))
#                     doctor_schedule[medico].add((data, hora))

#                     codigo_sns = fake.unique.bothify(text='############')
#                     consultas.append((consulta_id, paciente[0], medico, clinica[0], data, hora, codigo_sns))

#                     # ~80% das consultas têm receita
#                     if random.random() < 0.8:
#                         num_meds = random.randint(1, 6)
#                         for _ in range(num_meds):
#                             medicamento = fake.word()
#                             quantidade = random.randint(1, 3)
#                             # Verifica se a receita já foi prescrita para este paciente nesta consulta
#                             if (codigo_sns, clean_text(medicamento)) not in unique_receitas:
#                                 unique_receitas.add((codigo_sns, clean_text(medicamento)))
#                                 receitas.append((codigo_sns, clean_text(medicamento), quantidade))

#                     consulta_id += 1
#                     consultas_por_clinica += 1
#                     consultas_por_medico += 1

#                     if consultas_por_medico >= 2:
#                         break

#                 if consultas_por_clinica >= 20:
#                     break

#     return consultas, receitas



# def generate_random_data(medicos, clinicas, pacientes):
#     sintomas = [f'Sintoma {i}' for i in range(1, 51)]
#     metricas = [f'Métrica {i}' for i in range(1, 21)]

#     consultas = []
#     receitas = []
#     observacoes = []

#     data_inicio = datetime.strptime('2023-01-01', '%Y-%m-%d')
#     data_fim = datetime.strptime('2024-12-31', '%Y-%m-%d')
#     consultas_por_dia_por_clinica = 20
#     medicamentos_por_receita = range(1, 7)
#     quantidade_por_medicamento = range(1, 4)
#     observacoes_sintomas = range(1, 6)
#     observacoes_metricas = range(0, 4)

#     codigo_sns_counter = 1
#     id = 1
#     for dia in range((data_fim - data_inicio).days + 1):
#         data_consulta = data_inicio + timedelta(days=dia)
#         for clinica in clinicas:
#             nome_clinica = clinica[0]
#             for _ in range(consultas_por_dia_por_clinica):
#                 ssn_paciente = random.choice(pacientes)[0]
#                 nif_medico = random.choice(medicos)[0]
#                 hora_consulta = random_time()

#                 codigo_sns = f'{codigo_sns_counter:012}'
#                 codigo_sns_counter += 1

#                 consulta = (id, ssn_paciente, nif_medico, nome_clinica, data_consulta.strftime('%Y-%m-%d'), hora_consulta.strftime('%H:%M:%S'), codigo_sns)
    
#                 consultas.append(consulta)

#                 if random.random() < 0.8:  # ~80% das consultas têm receita
#                     num_medicamentos = random.choice(medicamentos_por_receita)
#                     for _ in range(num_medicamentos):
#                         medicamento = f'Medicamento {random.randint(1, 100)}'
#                         quantidade = random.choice(quantidade_por_medicamento)
#                         receita = (codigo_sns, medicamento, quantidade)

#                         receitas.append(receita)

                # num_sintomas = random.choice(observacoes_sintomas)
                # for _ in range(num_sintomas):
                #     sintoma = random.choice(sintomas)
                #     observacao = (len(consultas), sintoma, None)
                #     observacoes.append(observacao)

                # num_metricas = random.choice(observacoes_metricas)
                # for _ in range(num_metricas):
                #     metrica = random.choice(metricas)
                #     valor = round(random.uniform(0, 100), 2)
                #     observacao = (len(consultas), metrica, valor)
                #     observacoes.append(observacao)
                # id += 1

    # return consultas, receitas, observacoes


