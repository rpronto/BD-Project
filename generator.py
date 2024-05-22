from faker import Faker
import random
from unidecode import unidecode
from datetime import datetime, timedelta, time


# Create a Faker instance
fake = Faker('pt_PT') 

# List of neighborhoods/districts within Lisbon
lisbon_neighborhoods = [
    "Alfama", "Bairro Alto", "Baixa", "Belém", "Campo de Ourique",
    "Graça", "Mouraria", "Parque das Nações", "Santos", "Lapa",
    "Areeiro", "Estrela", "Marvila", "Carnide", "Lumiar"
]

# Function to generate random clinic data
def generate_clinic_data(num_entries):
    clinic_data = []
    for _ in range(num_entries):
        nome = fake.company()
        telefone = fake.unique.numerify(text='#########')  # Generates an 11-digit number
        morada = f"{fake.street_name()}, {fake.building_number()} {fake.postcode()}, {fake.random_element(lisbon_neighborhoods)}, Lisboa"
        clinic_data.append((nome, telefone, morada))
    return clinic_data


# Function to generate random nurse data for a given clinic
def generate_nurse_data(clinic_name, num_nurses=5):
    nurse_data = []
    for _ in range(num_nurses):
        nif = fake.unique.numerify(text='#########')  # Generates a 9-digit number
        nome = fake.unique.name()
        telefone = fake.unique.numerify(text='#########') 
        morada = f"{fake.street_name()}, {fake.building_number()} {fake.postcode()}, {fake.random_element(lisbon_neighborhoods)},  Lisboa"
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
        morada = f"{fake.street_name()}, {fake.building_number()} {fake.postcode()}, {fake.random_element(lisbon_neighborhoods)}, Lisboa"
        if i < 20:
            especialidade = "clínica geral"
        else:
            especialidade = fake.random_element(specialities)
        doctor_data.append((nif, nome, telefone, morada, especialidade))
    return doctor_data


# Função para garantir que cada clínica tenha pelo menos 8 médicos por dia
def distribuir_medicos(medicos, clinicas):
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
    
    return clinicas_medicos

# Generate work schedule for doctors in clinics
def generate_works_data(medicos, clinicas):
    trabalha = []
    clinicas_medicos = distribuir_medicos(medicos, clinicas)

    for clinica, medicos_clinica in clinicas_medicos.items():
        for dia in range(0, 7):  # de segunda a domingo
            medicos_dia = random.sample(medicos_clinica, 8)  # Select 8 doctors randomly
            for medico in medicos_dia:
                if any(item[0] == medico and item[2] == dia for item in trabalha):
                    continue
                trabalha.append((medico, clinica, dia))
    return trabalha


def generate_patient_data(num_entries):
    patients = []
    for _ in range(num_entries):
        ssn = fake.unique.bothify(text='###########')
        nif = fake.unique.bothify(text='#########')
        nome = fake.name()
        telefone = fake.unique.numerify(text='#########')
        morada = fake.address().replace('\n', ', ')
        data_nasc = fake.date_of_birth(minimum_age=0, maximum_age=100)
        patients.append((ssn, nif, nome, telefone, morada, data_nasc))
    return patients



def generate_random_data(medicos, clinicas, pacientes):
    sintomas = [f'Sintoma {i}' for i in range(1, 51)]
    metricas = [f'Métrica {i}' for i in range(1, 21)]

    consultas = []
    receitas = []
    observacoes = []

    data_inicio = datetime.strptime('2023-01-01', '%Y-%m-%d')
    data_fim = datetime.strptime('2024-12-31', '%Y-%m-%d')
    consultas_por_dia_por_clinica = 20
    medicamentos_por_receita = range(1, 7)
    quantidade_por_medicamento = range(1, 4)
    observacoes_sintomas = range(1, 6)
    observacoes_metricas = range(0, 4)

    codigo_sns_counter = 1

    for dia in range((data_fim - data_inicio).days + 1):
        data_consulta = data_inicio + timedelta(days=dia)
        for clinica in clinicas:
            nome_clinica = clinica[0]
            for _ in range(consultas_por_dia_por_clinica):
                ssn_paciente = random.choice(pacientes)[0]
                nif_medico = random.choice(medicos)[0]
                hora_consulta = random_time()

                codigo_sns = f'{codigo_sns_counter:012}'
                codigo_sns_counter += 1

                consulta = (ssn_paciente, nif_medico,nome_clinica, data_consulta.strftime('%Y-%m-%d'), hora_consulta.strftime('%H:%M:%S'), codigo_sns)
    
                consultas.append(consulta)

                if random.random() < 0.8:  # ~80% das consultas têm receita
                    num_medicamentos = random.choice(medicamentos_por_receita)
                    for _ in range(num_medicamentos):
                        medicamento = f'Medicamento {random.randint(1, 100)}'
                        quantidade = random.choice(quantidade_por_medicamento)
                        receita = (codigo_sns, medicamento, quantidade)

                        receitas.append(receita)

                num_sintomas = random.choice(observacoes_sintomas)
                for _ in range(num_sintomas):
                    sintoma = random.choice(sintomas)
                    observacao = (len(consultas), sintoma, None)
                    observacoes.append(observacao)

                num_metricas = random.choice(observacoes_metricas)
                for _ in range(num_metricas):
                    metrica = random.choice(metricas)
                    valor = round(random.uniform(0, 100), 2)
                    observacao = (len(consultas), metrica, valor)
                    observacoes.append(observacao)

    return consultas, receitas, observacoes


# Function to generate a random time within specific ranges
def random_time():
    possible_hours_morning = list(range(8, 13))  # 08:00 to 12:30
    possible_hours_afternoon = list(range(14, 19))  # 14:00 to 18:30
    possible_minutes = [0, 30]  # Minutes can be 00 or 30

    if random.choice([True, False]):
        hour = random.choice(possible_hours_morning)
    else:
        hour = random.choice(possible_hours_afternoon)
    
    minute = random.choice(possible_minutes)
    return time(hour, minute, 0)  # Hours, minutes, and seconds set to 00


# Number of clinics to generate
num_clinics = 5 
# Generate clinic data
clinic_data = generate_clinic_data(num_clinics)

# Print the generated clinic data
for clinic in clinic_data:
    print("INSERT INTO clinica VALUES ", clinic)

# Generate nurse data for each clinic
nurse_data_all = []
for clinic in clinic_data:
    clinic_name = clinic[0]
    num_nurses = fake.random_int(min=5, max=6)
    nurse_data = generate_nurse_data(clinic_name, num_nurses)
    nurse_data_all.extend(nurse_data)

# Print the generated nurse data
for nurse in nurse_data_all:
    print("INSERT INTO enfermeiro VALUES ", nurse)


# Number of doctors to generate
num_doctors = 60  # 20 "Clínica Geral" + 40 distributed among 5 specialities

# Generate doctor data
doctor_data = generate_doctor_data(num_doctors)

# Print the generated doctor data
for doctor in doctor_data:
    print("INSERT INTO medico VALUES ", doctor)


# Generate works data
works_data = generate_works_data(doctor_data, clinic_data)

# Print the generated works data
for work in works_data:
    print("INSERT INTO trabalha VALUES ", work)

num_patients = 5000
patients = generate_patient_data(num_patients)

# Print generated data
for patient in patients:
    print("INSERT INTO paciente VALUES ", patient)


consultas, receitas, observacoes = generate_random_data(doctor_data, clinic_data, patients)

for consulta in consultas:
    print("INSERT INTO consulta VALUES ", consulta)

for receita in receitas:
    print("INSERT INTO receita VALUES ", receita)

for observacao in observacoes:
    print("INSERT INTO observacao VALUES ", observacao)