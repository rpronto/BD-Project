CREATE MATERIALIZED VIEW IF NOT EXISTS historial_paciente AS
    SELECT 
        -- consulta
        c.id, 
        c.ssn,
        c.nif, 
        c.data,
        EXTRACT(YEAR FROM c.data) AS ano,
        EXTRACT(MONTH FROM c.data) AS mes,
        EXTRACT(DAY FROM c.data) AS dia_do_mes,
        EXTRACT(DOW FROM c.data) AS dia_da_semana,
        
        SUBSTRING(clinic.morada FROM POSITION('[0-9]{4}-[0-9]{3},\s' IN clinic.morada)) AS localidade -- clinica 
        m.especialidade, -- medico 
        'observacao' AS tipo, -- observacao
        o.parametro AS chave, 
        o.valor AS valor
    FROM 
        consulta c 
        JOIN medico m USING(nif)
        JOIN clinica clinic ON c.nome = clinic.nome
        JOIN observacao o USING(id)

    UNION ALL 
    
    SELECT 
        -- consulta
        c.id,
        c.ssn,
        c.nif, 
        c.data,
        EXTRACT(YEAR FROM c.data) AS ano,
        EXTRACT(MONTH FROM c.data) AS mes,
        EXTRACT(DAY FROM c.data) AS dia_do_mes,
        EXTRACT(DOW FROM c.data) AS dia_da_semana,

        SUBSTRING(clinic.morada FROM POSITION('[0-9]{4}-[0-9]{3},\s' IN clinic.morada)) AS localidade -- clinica 
        m.especialidade, -- medico 
        'receita' AS tipo, -- receita
        r.medicamento AS chave, 
        r.quantidade AS valor
    FROM 
        consulta c 
        JOIN medico m USING(nif)
        JOIN clinica clinic ON c.nome = clinic.nome
        JOIN receita r USING(codigo_sns)
