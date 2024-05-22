-- RI 1
ALTER TABLE consulta
ADD CONSTRAINT hora_consulta 
CHECK (
	(
    EXTRACT(HOUR FROM hora) BETWEEN 8 AND 12
    OR EXTRACT(HOUR FROM hora) BETWEEN 14 AND 18
    )
    AND EXTRACT(MINUTE FROM hora) IN (0, 30)
);



-- RI 2
CREATE OR REPLACE FUNCTION paciente_diff_medico() RETURNS TRIGGER AS $$
	BEGIN 
		IF (NEW.nif = (SELECT nif FROM paciente WHERE ssn = NEW.ssn)) THEN
			RAISE EXCEPTION 'Um médico não pode ter uma consulta consigo mesmo';
		END IF;
		RETURN NEW;
    END;
$$LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER paciente_diff_medico_trigger BEFORE INSERT OR UPDATE ON consulta
	FOR EACH ROW EXECUTE FUNCTION paciente_diff_medico();





-- RI 3

CREATE OR REPLACE FUNCTION medico_em_clinica() RETURNS TRIGGER AS $$
    DECLARE dia_semana_consulta SMALLINT;
    DECLARE dia_semana_trabalho SMALLINT;

    BEGIN 
        -- gets weekday of the appointment date
        SELECT EXTRACT(DOW FROM NEW.data) INTO dia_semana_consulta; 
        
        -- Extract the weekday name from the appointment date
        SELECT dia_da_semana INTO dia_semana_trabalho
            FROM trabalha 
            WHERE nif = NEW.nif AND nome = NEW.nome 
                AND dia_da_semana = dia_semana_consulta;

        -- If no matching record is found, raise an exception
        IF NOT FOUND THEN 
            RAISE EXCEPTION 'O médico não trabalha nesta clínica neste dia';
        END IF;

        RETURN NEW;
    END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER medico_em_clinica_trigger BEFORE INSERT OR UPDATE ON consulta
    FOR EACH ROW EXECUTE FUNCTION medico_em_clinica();



CREATE OR REPLACE FUNCTION medico_em_clinica1() RETURNS TRIGGER AS $$
BEGIN
    -- Check if the doctor works at the clinic on the given day
    IF NOT EXISTS (
        SELECT 1 -- or SELECT * ???
        FROM trabalha
        WHERE nif = NEW.nif  -- certifica que e o mm medico
        AND nome = NEW.nome -- certifica que e a mm clinica
        AND dia_da_semana = WEEKDAY(NEW.data)
    ) THEN
        RAISE EXCEPTION 'O médico não trabalha nesta clínica neste dia';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER medico_em_clinica_trigger1 BEFORE INSERT OR UPDATE ON consulta
    FOR EACH ROW EXECUTE FUNCTION medico_em_clinica1();


