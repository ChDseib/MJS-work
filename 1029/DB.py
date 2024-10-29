import mysql.connector
from mysql.connector import Error

def create_connection(host_name, user_name, user_password, database=None):
    connection = None
    try:
        conn_params = {
            "host": host_name,
            "port": 3306,
            "user": user_name,
            "passwd": user_password,
        }
        if database:
            conn_params["database"] = database
        connection = mysql.connector.connect(**conn_params)
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

# Create a connection to the MySQL server (without specifying the database)
connection = create_connection(host_name, user_name, user_password)

# Create a new database
create_database_query = "CREATE DATABASE IF NOT EXISTS b23015136"
execute_query(connection, create_database_query)

# Close the initial connection
connection.close()

# Connect to the newly created database
connection = create_connection(host_name, user_name, user_password, database="b23015136")

# Define the table creation query
create_table_query = """
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    message_id INT NOT NULL,
    text TEXT,
    role ENUM('user', 'assistant') NOT NULL,
    file_ids JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_message (conversation_id, message_id)
) ENGINE=InnoDB;
"""

# Execute the table creation query
execute_query(connection, create_table_query)

# Close the connection
connection.close()