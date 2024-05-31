-- 1
SELECT ssn
FROM historial_paciente
WHERE
    especialidade = 'ortopedia' 
    AND tipo = 'observacao' 
    AND valor IS NULL

GROUP BY ssn , chave HAVING (MAX(data) - MIN(data)) >= ALL(
    SELECT MAX(data) - MIN(data)
    FROM historial_paciente
    WHERE
        especialidade = 'ortopedia' 
        AND tipo = 'observacao' 
        AND valor IS NULL
    GROUP BY ssn, chave

);


-- 2
SELECT DISTINCT medicamento
FROM (
    SELECT 
        ssn,
        chave AS medicamento,
        COUNT(DISTINCT DATE_TRUNC('month', data)) AS meses_receitados
    FROM
        historial_paciente
    WHERE 
        especialidade = 'cardiologia'
        AND tipo = 'receita'
        AND data >= DATE_TRUNC('day', NOW()) - INTERVAL '1 year'
    GROUP BY 
        ssn, medicamento
)
WHERE 
    meses_receitados = 12
ORDER BY 
    medicamento;
    
-- 3

WITH medicamento_total AS (
    SELECT 
        chave AS medicamento,
        valor AS quantidade,
        localidade,
        c.nome AS nome_clinica,
        mes, 
        dia_do_mes,
        c.especialidade AS esp,
        medico.nome AS nome_m
    FROM 
        historial_paciente c JOIN medico USING(nif)
    WHERE 
        ano = 2023 AND tipo = 'receita'
)
SELECT 
    medicamento,
    localidade, 
    nome_clinica,
    mes,
    dia_do_mes,
    esp,
    nome_m,
    SUM(quantidade) AS total_quantidade
FROM 
    medicamento_total
GROUP BY 
    GROUPING SETS (
        (medicamento),
        (medicamento, localidade),
        (medicamento, localidade, nome_clinica),
        (medicamento, mes),
        (medicamento, mes, dia_do_mes),
        (medicamento, esp),
        (medicamento, esp, nome_m),
        ()
    )
ORDER BY 
    medicamento, mes, dia_do_mes;



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
    parametro,
    especialidade_medico,
    nome_medico,
    nome_clinica,
    AVG(valor) AS media_valor,
    STDDEV(valor) AS desvio_padrao_valor
FROM 
    metricas
GROUP BY
    ROLLUP (parametro, especialidade_medico, nome_medico, nome_clinica)
ORDER BY 
    parametro,
    especialidade_medico,
    nome_medico,
    nome_clinica;