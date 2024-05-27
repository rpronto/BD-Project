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

WITH consultas_cardiologia AS (
    SELECT 
        ssn,
        DATE_TRUNC('month', data) AS mes_ano,
        chave AS medicamento
    FROM
        historial_paciente c
    WHERE 
        especialidade = 'cardiologia'
        AND tipo = 'receita'
        AND c.data >= DATE_TRUNC('month', NOW()) - INTERVAL '11 months'
), medicamentos_mensais AS (
    SELECT 
        ssn, 
        medicamento, 
        COUNT(DISTINCT mes_ano) AS meses_receitados
    FROM 
        consultas_cardiologia
    GROUP BY 
        ssn, medicamento
)
SELECT 
    DISTINCT medicamento
FROM 
    medicamentos_mensais
WHERE 
    meses_receitados = 12
ORDER BY 
    medicamento;
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
WITH metricas AS (
    SELECT 
        c.nome AS nome_clinica,
        c.especialidade AS especialidade_medico,
        medico.nome AS nome_medico,
        chave AS parametro,
        valor
    FROM 
        historial_paciente c
    JOIN 
        medico USING(nif)
    WHERE 
        c.valor IS NOT NULL
        AND tipo = 'observacao'
)
SELECT 
    especialidade_medico,
    nome_medico,
    nome_clinica,
    parametro,
    AVG(valor) AS media_valor,
    STDDEV(valor) AS desvio_padrao_valor
FROM 
    metricas
GROUP BY 
    GROUPING SETS (
        (parametro, especialidade_medico, nome_medico),
        (parametro, especialidade_medico, nome_clinica)
    )
ORDER BY 
    especialidade_medico,
    nome_medico,
    nome_clinica,
    parametro;