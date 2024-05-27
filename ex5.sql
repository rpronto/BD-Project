-- 1

WITH dados_ortopedicos AS (
    SELECT
        c.ssn,
        c.data,
        LEAD(c.data) OVER (PARTITION BY c.ssn, c.chave ORDER BY c.data) AS proxima_data
    FROM
        historial_paciente c
    WHERE
        c.especialidade = 'ortopedia' -- Filtra apenas consultas de cardiologia
        AND c.tipo = 'observacao' -- Filtra apenas observações
        AND c.valor IS NULL -- Filtra observações com valor NULL
),
intervalos AS (
    SELECT
        ssn,
        proxima_data - data AS intervalo
    FROM
        dados_ortopedicos
    WHERE
        proxima_data IS NOT NULL
),
max_intervalos AS (
    SELECT
        ssn,
        MAX(intervalo) AS max_intervalo
    FROM
        intervalos
    GROUP BY
        ssn
),
valor_maximo AS (
    SELECT
        MAX(max_intervalo) AS valor_max
    FROM
        max_intervalos
)

SELECT
    m.ssn
FROM
    max_intervalos m
JOIN
    valor_maximo v
ON
    m.max_intervalo = v.valor_max
ORDER BY
    m.max_intervalo DESC;

-- 2

WITH medicamentos_cardiologia AS (
    SELECT 
        ssn,
        DATE_TRUNC('month', data) AS mes_ano,
        chave AS medicamento
    FROM
        historial_paciente
    WHERE 
        especialidade = 'cardiologia'
        AND tipo = 'receita'
), meses_consecutivos AS (
    SELECT
        ssn,
        medicamento,
        mes_ano,
        ROW_NUMBER() OVER (PARTITION BY ssn, medicamento ORDER BY mes_ano) AS mes_seq,
        DATE_TRUNC('month', mes_ano) AS mes_trunc
    FROM
        medicamentos_cardiologia
), diferencas AS (
    SELECT
        ssn,
        medicamento,
        mes_trunc,
        mes_seq,
        mes_trunc - INTERVAL '1 month' * (mes_seq - 1) AS diff
    FROM
        meses_consecutivos
), consecutivos AS (
    SELECT
        ssn,
        medicamento,
        COUNT(*) AS total_consecutivos
    FROM
        diferencas
    GROUP BY
        ssn,
        medicamento,
        diff
    HAVING
        COUNT(*) >= 12
)
SELECT DISTINCT
    medicamento
FROM 
    consecutivos;

-- 3
-- global vs localidade vs clinica
SELECT
    localidade,
    c.nome AS view_nome_clinica,
    SUM(valor) AS total_medicamentos
FROM
    historial_paciente c
JOIN
    clinica USING(nome)
WHERE
    EXTRACT(YEAR FROM data) = 2023
    AND tipo = 'receita'
GROUP BY
    GROUPING SETS ((localidade), (view_nome_clinica), ());

-- global vs mes vs dia_do_mes
SELECT
    mes,
    dia_do_mes,
    SUM(valor) AS total_medicamentos
FROM
    historial_paciente
WHERE
    EXTRACT(YEAR FROM data) = 2023
    AND tipo = 'receita'
GROUP BY
    GROUPING SETS ((mes), (dia_do_mes), ())
ORDER BY
    CASE WHEN mes IS NULL THEN 1 ELSE 0 END, mes,
    CASE WHEN dia_do_mes IS NULL THEN 1 ELSE 0 END, dia_do_mes;

-- global vs especialidade vs nome_do_medico
SELECT
    c.especialidade AS view_especialidade,
    medico.nome AS nome_medico,
    SUM(valor) AS total_medicamentos
FROM
    historial_paciente c
JOIN
    medico USING(nif)
WHERE
    EXTRACT(YEAR FROM data) = 2023
    AND tipo = 'receita'
GROUP BY
    GROUPING SETS ((view_especialidade), (nome_medico), ());

-- 4