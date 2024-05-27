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
        c.ssn,
        c.data,
        chave AS medicamento
    FROM
        historial_paciente c
    WHERE 
        c.especialidade = 'cardiologia'
        AND c.tipo = 'receita'
), medicamentos_mensais AS (
    SELECT 
        ssn,
        medicamento, 
        DATE_TRUNC('month', data) AS mes_ano,
        COUNT(DISTINCT DATE_TRUNC('month', data)) OVER (PARTITION BY ssn, medicamento ORDER BY DATE_TRUNC('month', data) ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS meses_consecutivos
    FROM
        medicamentos_cardiologia
)
SELECT DISTINCT
    medicamento
FROM 
    medicamentos_mensais
WHERE
    meses_consecutivos = 12;

