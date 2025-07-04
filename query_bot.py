from neo4j import GraphDatabase
import re
from difflib import get_close_matches

# === Neo4j Database Config ===
URI = "neo4j+s://ba865ded.databases.neo4j.io"
USER = "neo4j"
PASSWORD = "j-NsTY4fgYzYzNBabTwpZYepeUZvx2T-D_viAXpt0Ks"  # Replace with your actual password

# === Connect to Neo4j ===
try:
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    driver.verify_connectivity()
    print("✅ Successfully connected to Neo4j database.")
except Exception as e:
    print(f"❌ Failed to connect to Neo4j: {e}")
    exit()

# === Helper Functions ===

def extract_product_name(query):
    patterns = [
        r"(?:features|specs|price|cost|about)\s+of\s+(.+)",
        r"what is the (?:price|cost)\s+of\s+(.+)",
        r"tell me about\s+(.+)",
        r"(.+)\s+features",
        r"(.+)\s+price",
    ]
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return query.strip()

# === Neo4j Query Functions ===

def get_product_features(product_name):
    query = """
    MATCH (p:Product)-[:hasFeature]->(f:Feature)
    WHERE toLower(p.name) =~ ('.*\\b' + toLower($name) + '\\b.*')
    RETURN p.name AS product, collect(f.name) AS features
    """
    try:
        with driver.session() as session:
            result = session.run(query, name=product_name)
            records = result.data()

            if not records:
                return f"No features found for a product matching '{product_name}'."

            responses = []
            for r in records:
                features = ", ".join(r['features'])
                responses.append(f"🛒 Product: {r['product']} has features: {features}")
            return "\n".join(responses)
    except Exception as e:
        return f"An error occurred while fetching features: {e}"

def get_product_price(product_name):
    query = """
    MATCH (p:Product)
    WHERE toLower(p.name) CONTAINS toLower($name)
    RETURN p.name AS product, p.price AS price
    """
    try:
        with driver.session() as session:
            result = session.run(query, name=product_name)
            records = result.data()

            if not records:
                return f"No price found for a product matching '{product_name}'."

            responses = []
            for r in records:
                responses.append(f"💰 The price of {r['product']} is ₹{r['price']:.2f}.")
            return "\n".join(responses)
    except Exception as e:
        return f"An error occurred while fetching the price: {e}"

def list_products_in_category(category_name):
    query = """
    MATCH (p:Product)-[:belongsTo]->(c:Category)
    WHERE toLower(c.name) CONTAINS toLower($category)
    RETURN c.name AS category, collect(p.name) AS products
    """
    try:
        with driver.session() as session:
            result = session.run(query, category=category_name)
            records = result.data()

            if not records:
                return f"No products found in a category matching '{category_name}'."

            responses = []
            for r in records:
                products = ", ".join(r['products'])
                responses.append(f"📦 Products in the '{r['category']}' category: {products}")
            return "\n".join(responses)
    except Exception as e:
        return f"An error occurred while listing products: {e}"

# === Improved FAQ Matching with Fuzzy Logic ===

def get_faq_answer(user_question):
    query = """
    MATCH (q:FAQ)-[:hasAnswer]->(a:Answer)
    RETURN q.question AS question, a.text AS answer
    """
    try:
        with driver.session() as session:
            result = session.run(query)
            records = result.data()

            if not records:
                return None

            questions = [r['question'] for r in records]
            match = get_close_matches(user_question, questions, n=1, cutoff=0.6)

            if match:
                for r in records:
                    if r['question'] == match[0]:
                        return f"🔹 Q: {r['question']} \n📄 A: {r['answer']}"
            return None
    except Exception as e:
        return f"An error occurred while fetching FAQ: {e}"

# === Chatbot Logic ===

def main():
    print("\n🛍️ Welcome to the E-commerce Chatbot!")
    print("You can ask about product features, prices, categories, or FAQs.")
    print("Try: 'What are the features of Laptop X?', 'List products in Electronics', or 'How do I return an item?'\n")

    while True:
        q = input("You: ").strip()
        q_lower = q.lower()

        if q_lower == "exit":
            print("Bot: Goodbye! 👋")
            break
        elif any(word in q_lower for word in ["hi", "hello", "hey", "greetings"]):
            print("Bot: Hello! How can I help you today?")
        elif any(word in q_lower for word in ["thank", "thanks", "okay", "ok"]):
            print("Bot: You're welcome! 😊")
        elif "feature" in q_lower or "spec" in q_lower:
            product_name = extract_product_name(q_lower)
            print("Bot:", get_product_features(product_name))
        elif "price" in q_lower or "cost" in q_lower or "how much" in q_lower:
            product_name = extract_product_name(q_lower)
            print("Bot:", get_product_price(product_name))
        elif "product" in q_lower and ("category" in q_lower or "in" in q_lower):
            match = re.search(r"in\s+(.+)", q_lower)
            category_name = match.group(1).strip() if match else ""
            if category_name:
                print("Bot:", list_products_in_category(category_name))
            else:
                print("Bot: Please specify a category (e.g., 'List products in Electronics').")
        else:
            answer = get_faq_answer(q)
            if answer:
                print("Bot:", answer)
            else:
                print("Bot: 🤖 Sorry, I didn't understand. Try asking about a product, price, or a common question.")

if __name__ == "__main__":
    main()
