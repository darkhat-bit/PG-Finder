"""
database.py - Database setup for PGFind
Handles connection, table creation, and sample data
"""

import psycopg
from typing import Optional, List

# DATABASE URL - change this to your PostgreSQL credentials
DATABASE_URL = "postgresql://postgres:124_%40RIsHI@localhost:5432/pgfind"


# CONNECTION
class Database:
    @staticmethod
    def get_connection():
        return psycopg.connect(DATABASE_URL)


def get_db():
    """FastAPI dependency - gives a DB connection for each request"""
    conn = Database.get_connection()
    try:
        yield conn
    finally:
        conn.close()


# DATA CLASSES
class PG:
    def __init__(self, id=None, name="", area="", rent=0, contact="",
                 amenities="", verified=False, gender="Any", created_at=None,
                 owner_id=0, reviews=None):
        self.id = id
        self.name = name
        self.area = area
        self.rent = rent
        self.contact = contact
        self.amenities = amenities
        self.verified = verified
        self.gender = gender
        self.created_at = created_at
        self.owner_id = owner_id
        self.reviews = reviews or []
        self.avg_rating = 0


class Review:
    def __init__(self, id=None, pg_id=0, reviewer_name="Anonymous",
                 rating=0, comment="", created_at=None):
        self.id = id
        self.pg_id = pg_id
        self.reviewer_name = reviewer_name
        self.rating = rating
        self.comment = comment
        self.created_at = created_at


class User:
    def __init__(self, id=None, name="", email="", password="password123",
                 role="user", created_at=None):
        self.id = id
        self.name = name
        self.email = email
        self.password = password
        self.role = role
        self.created_at = created_at


# CREATE TABLES
def create_tables():
    conn = Database.get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_pgs (
                id         SERIAL PRIMARY KEY,
                name       VARCHAR(200) NOT NULL,
                area       VARCHAR(100) NOT NULL,
                rent       INTEGER NOT NULL,
                contact    VARCHAR(15),
                amenities  TEXT,
                verified   BOOLEAN DEFAULT FALSE,
                gender     VARCHAR(10) DEFAULT 'Any',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                owner_id   INTEGER DEFAULT 0
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_reviews (
                id            SERIAL PRIMARY KEY,
                pg_id         INTEGER NOT NULL REFERENCES app_pgs(id) ON DELETE CASCADE,
                reviewer_name VARCHAR(100) DEFAULT 'Anonymous',
                rating        INTEGER NOT NULL,
                comment       TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_users (
                id         SERIAL PRIMARY KEY,
                name       VARCHAR(100) NOT NULL,
                email      VARCHAR(200) UNIQUE NOT NULL,
                password   VARCHAR(100) DEFAULT 'password123',
                role       VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        print("Tables created!")
    except Exception as e:
        conn.rollback()
        print(f"Error creating tables: {e}")
    finally:
        cur.close()
        conn.close()


# SAMPLE DATA
def seed_data():
    conn = Database.get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM app_pgs;")
        if cur.fetchone()[0] > 0:
            print("Data already exists, skipping seed.")
            return

        sample_pgs = [
            ("Sharma PG for Boys",    "Gate No. 1, Phagwara",   5500, "9876543210", "WiFi, Food, Laundry",                    True,  "Boys"),
            ("Gupta Girls PG",        "Gate No. 2, Phagwara",   6000, "9876543211", "WiFi, AC, Food, Parking",                True,  "Girls"),
            ("Royal PG",              "Mehatpur, Jalandhar",    4500, "9876543212", "WiFi, Food",                             False, "Boys"),
            ("Green Valley PG",       "Gate No. 4, Phagwara",   7000, "9876543213", "WiFi, AC, Food, Gym, Laundry",           True,  "Any"),
            ("Student Hub PG",        "Lovely Chowk, Phagwara", 5000, "9876543214", "WiFi, Food, Parking",                   True,  "Boys"),
            ("Comfort Stay PG",       "GT Road, Jalandhar",     6500, "9876543215", "WiFi, AC, Food, Laundry",               True,  "Girls"),
            ("Budget PG",             "Gate No. 1, Phagwara",   3500, "9876543216", "Food",                                  False, "Boys"),
            ("Premium PG",            "Model Town, Jalandhar",  8500, "9876543217", "WiFi, AC, Food, Gym, Laundry, Parking", True,  "Any"),
            ("Sunrise PG",            "Gate No. 2, Phagwara",   5500, "9876543218", "WiFi, Food, Laundry",                   True,  "Boys"),
            ("Lakshmi PG for Girls",  "Lovely Chowk, Phagwara", 6000, "9876543219", "WiFi, AC, Food",                       True,  "Girls"),
        ]
        for pg in sample_pgs:
            cur.execute("INSERT INTO app_pgs (name, area, rent, contact, amenities, verified, gender) VALUES (%s, %s, %s, %s, %s, %s, %s);", pg)

        sample_reviews = [
            (1, "Rahul",   4, "Good food and WiFi. Rooms are clean."),
            (1, "Amit",    3, "Decent place but noisy sometimes."),
            (2, "Priya",   5, "Best PG near LPU! Highly recommended."),
            (2, "Sneha",   4, "Nice rooms, good food quality."),
            (3, "Vikram",  3, "Okay for the price. Basic amenities."),
            (4, "Ananya",  5, "Amazing PG with all facilities!"),
            (4, "Rohan",   4, "Gym is great. Food could be better."),
            (5, "Karan",   4, "Close to campus, good WiFi."),
            (6, "Megha",   5, "Very safe for girls. Great staff."),
            (7, "Ajay",    2, "Too basic. No WiFi."),
            (8, "Neha",    5, "Worth every penny. Premium experience."),
            (9, "Saurabh", 4, "Good place near Gate 2."),
            (10, "Pooja",  4, "Clean and safe. Recommended."),
        ]
        for review in sample_reviews:
            cur.execute("INSERT INTO app_reviews (pg_id, reviewer_name, rating, comment) VALUES (%s, %s, %s, %s);", review)

        sample_users = [
            ("Rahul Kumar", "rahul@lpu.in", "password123", "user"),
            ("Priya Singh",  "priya@lpu.in",  "password123", "user"),
            ("Amit Sharma",  "amit@lpu.in",   "password123", "user"),
        ]
        for user in sample_users:
            cur.execute("INSERT INTO app_users (name, email, password, role) VALUES (%s, %s, %s, %s);", user)

        conn.commit()
        print("Sample data added!")
    except Exception as e:
        conn.rollback()
        print(f"Error seeding data: {e}")
    finally:
        cur.close()
        conn.close()