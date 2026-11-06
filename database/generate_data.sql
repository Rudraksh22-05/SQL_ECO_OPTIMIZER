-- Generate 10,000 employees
INSERT INTO employees (
    emp_name,
    dept_id,
    salary,
    joining_date
)
SELECT
    'Employee_' || generate_series,
    (random() * 4 + 1)::INTEGER,
    (30000 + random() * 100000)::NUMERIC(10,2),
    DATE '2015-01-01' + (random() * 3650)::INTEGER
FROM generate_series(1, 10000);