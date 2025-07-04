import json
import os
from neo4j import GraphDatabase # Assuming neo4j is installed: pip install neo4j

# === Neo4j Database Config ===
URI = "neo4j+s://ba865ded.databases.neo4j.io"  # Use Neo4j Aura bolt URL if cloud
USER = "neo4j"
PASSWORD = "j-NsTY4fgYzYzNBabTwpZYepeUZvx2T-D_viAXpt0Ks"  # <- Replace with your actual password for Neo4j

# === Connect to Neo4j ===
driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def load_product(tx, product, category_cache):
    category = product["category"]

    # Create Category node (if not already created)
    if category not in category_cache:
        tx.run("MERGE (:Category {name: $name})", name=category)
        category_cache.add(category)

    # Create Product node + link to Category
    tx.run("""
        MERGE (p:Product {id: $id})
        SET p.name = $name, p.price = $price
        MERGE (c:Category {name: $category})
        WITH p,c
        MERGE (p)-[:belongsTo]->(c)
    """, id=product["id"], name=product["name"], price=product["price"], category=category)

    # Create Feature nodes + relationships
    for feature in product["features"]:
        tx.run("""
            MERGE (f:Feature {name: $feature})
            WITH f
            MATCH (p:Product {id: $id})
            MERGE (p)-[:hasFeature]->(f)
        """, feature=feature, id=product["id"])


def load_faq(tx, faq):
    # Create FAQ question and answer nodes + link
    tx.run("""
        MERGE (q:FAQ {question: $question})
        MERGE (a:Answer {text: $answer})
        MERGE (q)-[:hasAnswer]->(a)
    """, question=faq["question"], answer=faq["answer"])


def main():
    # Open Neo4j session
    with driver.session() as session:

        # === Load Product Data ===
        print("📦 Loading products...")
        # --- CHANGE THIS LINE ---
        # If 'data' folder is sibling to 'graph' folder, and script is run from 'ecom-help-bot'
        # with open(os.path.join("data", "large_sample_products.json")) as f:
        # If 'data' folder is inside 'graph' folder
        # with open(os.path.join(os.path.dirname(__file__), "..", "data", "large_sample_products.json")) as f:
        # If 'data' folder is sibling to 'graph' folder, and script is run from 'graph' folder
        with open(os.path.join("..", "data", "ecommerce_products_1000.json")) as f: # <--- Try this first based on common project structure
            products = json.load(f)
        category_cache = set()
        for product in products:
            session.execute_write(load_product, product, category_cache)

        # === Load FAQ Data ===
        print("📄 Loading FAQs...")
        # --- CHANGE THIS LINE ---
        # If 'data' folder is sibling to 'graph' folder, and script is run from 'ecom-help-bot'
        # with open(os.path.join("data", "large_sample_faqs.json")) as f:
        # If 'data' folder is inside 'graph' folder
        # with open(os.path.join(os.path.dirname(__file__), "..", "data", "large_sample_faqs.json")) as f:
        # If 'data' folder is sibling to 'graph' folder, and script is run from 'graph' folder
        with open(os.path.join("..", "data", "realistic_ecommerce_faqs_1000.json")) as f: # <--- Try this first based on common project structure
            faqs = json.load(f)
        for faq in faqs:
            session.execute_write(load_faq, faq)

    print("✅ All data loaded successfully into Neo4j!")


if __name__ == "__main__":
    main()
