
-- ==========================================
-- SQL ECO-OPTIMIZER
-- INITIAL SEED DATA
-- ==========================================

-- Departments
INSERT INTO departments (dept_name)
VALUES
('Computer Science'),
('Data Science'),
('Information Technology'),
('Human Resources'),
('Finance');

-- Employees
INSERT INTO employees (emp_name, dept_id, salary, joining_date)
VALUES
('Alice', 1, 75000, '2023-01-15'),
('Bob', 1, 65000, '2022-06-10'),
('Charlie', 2, 85000, '2021-03-20'),
('David', 2, 90000, '2020-11-05'),
('Eva', 3, 60000, '2024-02-12'),
('Frank', 3, 70000, '2023-08-18'),
('Grace', 4, 55000, '2022-09-01'),
('Henry', 5, 80000, '2021-07-22');

-- Projects
INSERT INTO projects (project_name, budget, dept_id)
VALUES
('AI Research', 500000, 1),
('Data Analytics Platform', 350000, 2),
('Cloud Migration', 450000, 3),
('Employee Management System', 150000, 4),
('Financial Forecasting', 300000, 5);

-- Employee-Project Assignments
INSERT INTO works_on (emp_id, project_id, hours_worked)
VALUES
(1, 1, 120),
(2, 1, 100),
(3, 2, 150),
(4, 2, 180),
(5, 3, 110),
(6, 3, 130),
(7, 4, 90),
(8, 5, 140);