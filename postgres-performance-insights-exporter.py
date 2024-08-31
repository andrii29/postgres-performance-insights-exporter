import time
import re
import os
import argparse
import psycopg2
from psycopg2 import pool
from prometheus_client import start_http_server, Counter
import logging

# Configure logging
# Configure logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# Prometheus metric as a Counter
pi_metric = Counter('performance_insights',
                    'PostgreSQL query statistics',
                    ['usename', 'application_name', 'client_addr', 'wait_event_type', 'wait_event', 'state', 'query_shape'])

def extract_query_shape(query):
    """Simplifies the query to its shape by removing literals, values, unnecessary quotes, and normalizing spaces."""
    query_shape = re.sub(r'\"([^\"]+)\"', r'\1', query)       # Remove quotes around identifiers
    query_shape = re.sub(r'\b\d+\b', '?', query_shape)        # Replace numbers with placeholders
    query_shape = re.sub(r"'[^']*'", '?', query_shape)        # Replace string literals with placeholders
    query_shape = query_shape.replace('\n', ' ')              # Remove newline characters
    query_shape = re.sub(r'\s+', ' ', query_shape)            # Replace multiple spaces with a single space
    query_shape = query_shape.strip()                         # Remove leading and trailing spaces
    return query_shape

def collect_metrics():
    """Collect metrics from PostgreSQL and expose them to Prometheus."""
    conn = None
    try:
        # Get a connection from the pool
        conn = connection_pool.getconn()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT usename, application_name, client_addr, wait_event_type, wait_event, state, query
                FROM pg_stat_activity
                WHERE query IS NOT NULL
                AND query NOT ILIKE '%pg_stat_activity%'  -- Exclude queries on pg_stat_activity table
                AND state != 'idle';
            """)
            rows = cursor.fetchall()
            for row in rows:
                usename, application_name, client_addr, wait_event_type, wait_event, state, query = row
                query_shape = extract_query_shape(query)
                pi_metric.labels(usename, application_name, client_addr, wait_event_type, wait_event, state, query_shape[:max_string_size]).inc()
    except Exception as e:
        logging.error(f"Error executing query: {e}")
    finally:
        # Return the connection to the pool
        if conn:
            connection_pool.putconn(conn)

def main():
    logging.info('Starting Postgres Performance Insights Exporter')
    parser = argparse.ArgumentParser(description="PostgreSQL Performance Insights Exporter for Prometheus", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--port', type=int, default=9153, help='Port to start the Prometheus metrics server on')
    parser.add_argument('--db-name', default=os.getenv('DBNAME', 'test'), help='PostgreSQL database name')
    parser.add_argument('--db-user', default=os.getenv('DBUSER', 'postgres'), help='PostgreSQL user')
    parser.add_argument('--db-password', default=os.getenv('DBPASSWORD', 'pass'), help='PostgreSQL password')
    parser.add_argument('--db-host', default=os.getenv('DBHOST', '127.0.0.1'), help='PostgreSQL host')
    parser.add_argument('--db-port', type=int, default=int(os.getenv('DBPORT', '5432')), help='PostgreSQL port')
    parser.add_argument('--max-string-size', type=int, default=int(os.getenv('MAX_STRING_SIZE', '1000')), help='Maximum size of query string to store')
    parser.add_argument('--interval', type=int, default=int(os.getenv('INTERVAL', '1')), help='This determines how frequently the script will fetch data from PostgreSQL')

    args = parser.parse_args()

    global max_string_size
    max_string_size = args.max_string_size

    # Initialize the connection pool
    global connection_pool
    connection_pool = psycopg2.pool.SimpleConnectionPool(
        1,  # Minimum number of connections
        10, # Maximum number of connections
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password,
        host=args.db_host,
        port=args.db_port
    )

    # Start Prometheus metrics server
    start_http_server(args.port)
    logging.info(f'Started Prometheus metrics server on port {args.port}')

    # Log useful information
    logging.info(f'Configuration:')
    logging.info(f'DBNAME={args.db_name}, DBUSER={args.db_user}, DBHOST={args.db_host}, DBPORT={args.db_port}')
    logging.info(f'MAX_STRING_SIZE={max_string_size}')

    # Continuously collect metrics every second
    while True:
        loop_start = time.time()
        collect_metrics()
        # Calculate the time taken to execute the command
        elapsed = time.time() - loop_start
        time.sleep(max(0, args.interval - elapsed - 0.0005)) # try to keep loop at interval by extracting actual execution time

if __name__ == '__main__':
    main()
