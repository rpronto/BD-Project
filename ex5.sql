-- 1

SELECT ssn
FROM (
    -- obtem ssn e max intervalos
    SELECT 
        ssn,
        MAX(proxima_data - data) AS max_intervalo
    FROM
        (SELECT 
            c.ssn,
            c.data,
            LEAD(c.data) OVER (PARTITION BY c.ssn, c.chave ORDER BY c.data) AS proxima_data
        FROM 
            historial_paciente c
        WHERE
            c.especialidade = 'ortopedia' AND c.tipo = 'observacao' AND c.valor IS NULL
        )
    WHERE
        proxima_data IS NOT NULL
    GROUP BY
        ssn
)
GROUP BY ssn HAVING MAX(max_intervalo) >= ALL(
    SELECT MAX(max_intervalo)
    FROM (
        SELECT 
            MAX(proxima_data - data) AS max_intervalo
        FROM
            (SELECT 
                c.ssn,
                c.data,
                LEAD(c.data) OVER (PARTITION BY c.ssn, c.chave ORDER BY c.data) AS proxima_data
            FROM 
                historial_paciente c
            WHERE
                c.especialidade = 'ortopedia' AND c.tipo = 'observacao' AND c.valor IS NULL
            )
        WHERE
            proxima_data IS NOT NULL
        GROUP BY
            ssn
    )
);

-- WITH max_intervalos AS (
--     SELECT 
--         ssn,
--         MAX(proxima_data - data) AS max_intervalo
--     FROM
--         (SELECT 
--             c.ssn,
--             c.data,
--             LEAD(c.data) OVER (PARTITION BY c.ssn, c.chave ORDER BY c.data) AS proxima_data
--         FROM 
--             historial_paciente c
--         WHERE
--             c.especialidade = 'ortopedia' AND c.tipo = 'observacao' AND c.valor IS NULL
--         )
--     WHERE
--         proxima_data IS NOT NULL
--     GROUP BY
--         ssn
--     ORDER BY    
--         max_intervalo DESC
-- ),
-- valor_maximo AS(
--     SELECT 
--         MAX(max_intervalo) AS valor_max
--     FROM 
--         max_intervalos
-- )
-- SELECT
--     m.ssn, max_intervalo
-- FROM
--     max_intervalos m JOIN valor_maximo v ON m.max_intervalo = v.valor_max;



-- 2
-- ver teorica
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
        AND data >= DATE_TRUNC('month', NOW()) - INTERVAL '11 months'
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


--SELECT * FROM
--    (SELECT
--        chave,
--        localidade,
--        c.nome AS nome_clinica,
--        SUM(valor) AS total_medicamentos
--    FROM historial_paciente c JOIN clinica USING(nome)
--    WHERE
--        ano = 2023 AND tipo = 'receita'
--    GROUP BY
--        GROUPING SETS ((chave), (chave, localidade), (chave, localidade, nome_clinica), ())
--    ) AS localidade_clinica
--FULL JOIN
--    (SELECT
--        chave,
--        mes,
--        dia_do_mes,
--        SUM(valor) AS total_medicamentos
--    FROM
--        historial_paciente
--    WHERE
--        ano = 2023 AND tipo = 'receita'
--    GROUP BY
--        GROUPING SETS ((chave), (chave, mes), (chave, mes, dia_do_mes), ())
--    ) AS mes_dia_do_mes
--USING(chave)   
--FULL JOIN
--    (SELECT
--        chave,
--        c.especialidade AS esp,
--        medico.nome AS nome_m,
--        SUM(valor) AS total_medicamentos
--    FROM 
--        historial_paciente c JOIN medico USING(nif)
--    WHERE 
--        ano = 2023 AND tipo = 'receita'
--    GROUP BY
--        GROUPING SETS ((chave), (chave, esp), (chave, esp, nome_m), ())
--    ) AS especialidade_nome_medico
--USING(chave);


--WITH quantidades_receitadas AS (
--    SELECT
--        c.localidade,
--        c.nome AS view_nome_clinica,
--        SUM(c.valor) AS total_medicamentos,
--        EXTRACT(MONTH FROM c.data) AS mes,
--        EXTRACT(DAY FROM c.data) AS dia_do_mes,
--        c.especialidade AS view_especialidade,
--        m.nome AS nome_medico
--    FROM 
--        historial_paciente c
--    JOIN
--        clinica cl ON c.nome = cl.nome
--    JOIN
--        medico m ON c.nif = m.nif
--    WHERE
--        EXTRACT(YEAR FROM c.data) = 2023
--        AND c.tipo = 'receita'
--    GROUP BY
--        c.localidade, c.nome, c.especialidade, m.nome, EXTRACT(MONTH FROM c.data), EXTRACT(DAY FROM c.data)
--)
--SELECT
--    localidade,
--    view_nome_clinica,
--    mes,
--    dia_do_mes,
--    view_especialidade,
--    nome_medico,
--    SUM(total_medicamentos) AS total_medicamentos
--FROM
--    quantidades_receitadas
--GROUP BY
--    GROUPING SETS (
--        (),
--        (localidade),
--        (localidade, view_nome_clinica),
--        (mes),
--        (mes, dia_do_mes),
--        (view_especialidade),
--        (view_especialidade, nome_medico)
--    )
--ORDER BY
--    CASE WHEN mes IS NULL THEN 1 ELSE 0 END, mes,
--    CASE WHEN dia_do_mes IS NULL THEN 1 ELSE 0 END, dia_do_mes;


    -- global vs localidade vs clinica
--SELECT
--    localidade,
--    c.nome AS view_nome_clinica,
--    SUM(valor) AS total_medicamentos
--FROM
--    historial_paciente c
--JOIN
--    clinica USING(nome)
--WHERE
--    EXTRACT(YEAR FROM data) = 2023
--    AND tipo = 'receita'
--GROUP BY
--    GROUPING SETS ((localidade), (view_nome_clinica), ());
--
---- global vs mes vs dia_do_mes
--
---- mudado para ter mes e dias por mes 
--
--SELECT
--    mes,
--    dia_do_mes,
--    SUM(valor) AS total_medicamentos
--FROM
--    historial_paciente
--WHERE
--    EXTRACT(YEAR FROM data) = 2023
--    AND tipo = 'receita'
--GROUP BY
--    GROUPING SETS (
--        (mes),
--        (mes, dia_do_mes), ())
--ORDER BY
--    CASE WHEN mes IS NULL THEN 1 ELSE 0 END, mes,
--    CASE WHEN dia_do_mes IS NULL THEN 1 ELSE 0 END, dia_do_mes;
--
---- global vs especialidade vs nome_do_medico
--SELECT
--    c.especialidade AS view_especialidade,
--    medico.nome AS nome_medico,
--    SUM(valor) AS total_medicamentos
--FROM
--    historial_paciente c
--JOIN
--    medico USING(nif)
--WHERE
--    EXTRACT(YEAR FROM data) = 2023
--    AND tipo = 'receita'
--GROUP BY
--    GROUPING SETS ((view_especialidade), (nome_medico), ());



-- 4  

-- mudado com drill down
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
    GROUPING SETS (
        (parametro),
        (parametro, especialidade_medico),
        (parametro, especialidade_medico,nome_medico),
        (parametro, especialidade_medico, nome_medico, nome_clinica)
    )
ORDER BY 
    parametro,
    especialidade_medico,
    nome_medico,
    nome_clinica;