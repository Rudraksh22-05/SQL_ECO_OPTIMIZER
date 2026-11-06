
import re
import uuid

from psycopg2 import sql

from app.database import get_benchmark_connection


_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def get_existing_index_columns(connection, table: str | None = None):
    """
    Retrieve single-column indexes from the provided database connection.
    """

    if table is not None:
        SafeIndexManager.validate_identifier(
            table,
            "table name"
        )

    query = """
        SELECT
            t.relname AS table_name,
            a.attname AS column_name
        FROM pg_index i
        JOIN pg_class t
            ON t.oid = i.indrelid
        JOIN pg_namespace n
            ON n.oid = t.relnamespace
        JOIN pg_attribute a
            ON a.attrelid = t.oid
           AND a.attnum = ANY(i.indkey)
        WHERE n.nspname = 'public'
          AND i.indisvalid = TRUE
          AND i.indnkeyatts = 1
    """

    params = ()

    if table is not None:
        query += " AND t.relname = %s"
        params = (table,)

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    return [
        {
            "table": table_name,
            "column": column_name
        }
        for table_name, column_name in rows
    ]

class SafeIndexManager:
    """
    Manages test indexes exclusively in the benchmark database.

    Only indexes created by this manager instance are eligible
    for automatic cleanup.
    """

    TEST_INDEX_PREFIX = "eco_test_idx_"

    def __init__(self):
        self.created_indexes = set()

    @staticmethod
    def validate_identifier(identifier: str, label: str):
        if not isinstance(identifier, str):
            raise ValueError(f"{label} must be a string.")

        if not _IDENTIFIER_PATTERN.fullmatch(identifier):
            raise ValueError(
                f"Invalid {label}: {identifier}"
            )

    def validate_table_and_column(
        self,
        connection,
        table: str,
        column: str
    ):
        self.validate_identifier(table, "table name")
        self.validate_identifier(column, "column name")

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                  AND column_name = %s
                """,
                (table, column)
            )

            if cursor.fetchone() is None:
                raise ValueError(
                    f"Table '{table}' or column '{column}' "
                    "does not exist in the public schema."
                )

    def generate_test_index_name(self, table: str, column: str):
        self.validate_identifier(table, "table name")
        self.validate_identifier(column, "column name")

        unique_id = uuid.uuid4().hex[:12]

        return (
            f"{self.TEST_INDEX_PREFIX}"
            f"{table}_{column}_{unique_id}"
        )

    
    def get_existing_indexes(self, table: str | None = None):
        """
        Retrieve existing indexes from the benchmark database.

        Returns:
            A list of dictionaries containing index name,
            table name, and indexed column.
        """

        if table is not None:
            self.validate_identifier(table, "table name")

        connection = get_benchmark_connection()

        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT
                        indexname,
                        tablename,
                        indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                """

                params = ()

                if table is not None:
                    query += " AND tablename = %s"
                    params = (table,)

                query += " ORDER BY tablename, indexname"

                cursor.execute(query, params)
                rows = cursor.fetchall()

                indexes = []

                for index_name, table_name, index_definition in rows:
                    indexes.append({
                        "index_name": index_name,
                        "table": table_name,
                        "definition": index_definition
                    })

                return indexes

        finally:
            connection.close()

    def create_test_index(
        self,
        table: str,
        column: str
    ):
        connection = get_benchmark_connection()

        index_name = self.generate_test_index_name(
            table,
            column
        )

        try:
            connection.autocommit = False

            self.validate_table_and_column(
                connection,
                table,
                column
            )

            with connection.cursor() as cursor:
                create_statement = sql.SQL(
                    "CREATE INDEX {index_name} "
                    "ON {table} ({column})"
                ).format(
                    index_name=sql.Identifier(index_name),
                    table=sql.Identifier(table),
                    column=sql.Identifier(column)
                )

                cursor.execute(create_statement)

            connection.commit()

            self.created_indexes.add(index_name)

            return {
                "index_name": index_name,
                "table": table,
                "column": column,
                "created": True
            }

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def drop_test_index(self, index_name: str):
        if index_name not in self.created_indexes:
            raise ValueError(
                "Refusing to drop an index that was not "
                "created by this manager instance."
            )

        self.validate_identifier(index_name, "index name")

        connection = get_benchmark_connection()

        try:
            connection.autocommit = False

            with connection.cursor() as cursor:
                drop_statement = sql.SQL(
                    "DROP INDEX IF EXISTS {index_name}"
                ).format(
                    index_name=sql.Identifier(index_name)
                )

                cursor.execute(drop_statement)

            connection.commit()

            self.created_indexes.remove(index_name)

            return {
                "index_name": index_name,
                "dropped": True
            }

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def cleanup(self):
        """
        Attempt to remove all indexes created by this manager.

        Cleanup attempts continue even if one index removal fails.
        """
        cleanup_results = []

        for index_name in list(self.created_indexes):
            try:
                result = self.drop_test_index(index_name)

                cleanup_results.append({
                    **result,
                    "success": True
                })

            except Exception as error:
                cleanup_results.append({
                    "index_name": index_name,
                    "success": False,
                    "error": str(error)
                })

        return cleanup_results