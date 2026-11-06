from app.database import get_connection


def main():
    connection = None

    try:
        connection = get_connection()

        cursor = connection.cursor()
        cursor.execute("SELECT version();")

        version = cursor.fetchone()[0]

        print("Successfully connected to PostgreSQL!")
        print(version)

        cursor.close()

    except Exception as error:
        print("Connection failed!")
        print(error)

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    main()