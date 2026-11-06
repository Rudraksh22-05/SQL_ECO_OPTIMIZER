
CREATE TABLE IF NOT EXISTS benchmark_results (
    id BIGSERIAL PRIMARY KEY,

    query TEXT NOT NULL,

    table_name VARCHAR(255) NOT NULL,

    column_name VARCHAR(255) NOT NULL,

    baseline_time_ms DOUBLE PRECISION NOT NULL,

    optimized_time_ms DOUBLE PRECISION NOT NULL,

    improvement_percent DOUBLE PRECISION,

    baseline_plan JSONB NOT NULL,

    optimized_plan JSONB NOT NULL,

    benchmark_configuration JSONB NOT NULL,

    environment_metadata JSONB NOT NULL,

    environmental_impact JSONB NOT NULL,

    recommendation JSONB NOT NULL,

    index_information JSONB,

    cleanup_information JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);