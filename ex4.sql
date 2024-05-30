DROP MATERIALIZED VIEW IF EXISTS historial_paciente;

CREATE MATERIALIZED VIEW historial_paciente AS
    SELECT 
        c.id, 
        c.ssn,
        c.nif, 
        c.nome,
        c.data,
        EXTRACT(YEAR FROM c.data) AS ano,
        EXTRACT(MONTH FROM c.data) AS mes,
        EXTRACT(DAY FROM c.data) AS dia_do_mes,
        SUBSTRING(clinic.morada, '\d{4}-\d{3} (.*)') AS localidade,
        m.especialidade, -- medico 
        'observacao' AS tipo, -- observacao
        o.parametro AS chave, 
        o.valor AS valor
    FROM 
        consulta c 
        JOIN medico m USING(nif)
        JOIN clinica clinic ON c.nome = clinic.nome
        JOIN observacao o USING(id)
    UNION
    SELECT 
        c.id,
        c.ssn,
        c.nif, 
        c.nome,
        c.data,
        EXTRACT(YEAR FROM c.data) AS ano,
        EXTRACT(MONTH FROM c.data) AS mes,
        EXTRACT(DAY FROM c.data) AS dia_do_mes,
        SUBSTRING(clinic.morada, '\d{4}-\d{3} (.*)') AS localidade,
        m.especialidade, -- medico 
        'receita' AS tipo, -- receita
        r.medicamento AS chave, 
        r.quantidade AS valor
    FROM 
        consulta c 
        JOIN medico m USING(nif)
        JOIN clinica clinic ON c.nome = clinic.nome
        JOIN receita r USING(codigo_sns);

