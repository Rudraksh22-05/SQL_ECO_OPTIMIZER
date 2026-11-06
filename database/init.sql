
-- ==========================================
-- SQL ECO-OPTIMIZER
-- INITIAL DATABASE SCHEMA
-- ==========================================

-- Departments
CREATE TABLE IF NOT EXISTS departments (
    dept_id SERIAL PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL
);

-- Employees
CREATE TABLE IF NOT EXISTS employees (
    emp_id SERIAL PRIMARY KEY,
    emp_name VARCHAR(100) NOT NULL,
    dept_id INTEGER REFERENCES departments(dept_id),
    salary NUMERIC(10,2),
    joining_date DATE
);

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    project_id SERIAL PRIMARY KEY,
    project_name VARCHAR(150) NOT NULL,
    budget NUMERIC(12,2),
    dept_id INTEGER REFERENCES departments(dept_id)
);

-- Employee-Project assignments
CREATE TABLE IF NOT EXISTS works_on (
    emp_id INTEGER REFERENCES employees(emp_id),
    project_id INTEGER REFERENCES projects(project_id),
    hours_worked INTEGER,
    PRIMARY KEY (emp_id, project_id)
);