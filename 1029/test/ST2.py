import mysql.connector
from mysql.connector import Error

def create_connection(host_name, user_name, user_password):
    connection = None
    try:
        connection = mysql.connector.connect(
            host="10.200.32.179",
            port=3306,
            user="root",
            passwd="111111",
        )
        print("Connection to MySQL DB successful")
    except Error as e:
        print(f"The error '{e}' occurred")
    return connection

def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("Query executed successfully")
    except Error as e:
        print(f"The error '{e}' occurred")

# Connection details
host_name = "10.200.32.179"
user_name = "root"
user_password = "111111"

# Create a connection to the database
connection = create_connection(host_name, user_name, user_password)

# Create a new database
create_database_query = "CREATE DATABASE b23015136"
execute_query(connection, create_database_query)

# Close the connection
connection.close()